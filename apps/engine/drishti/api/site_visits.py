"""Site visits: start filming, upload, read back (T123 and T124; plan T120 §9; migration 014).

    GET  /api/v1/site-visits/{work_id}          the site map, the visits so far, the viewpoints of
                                                the last read visit (with their frames, for the
                                                capture page's faint overlay), each with its
                                                anchor, facing and 3 pan pictures (T158), and how
                                                many spots the work needs
    POST /api/v1/site-visits/start              {work_id, kind} -> a visit id and a capture token,
                                                issued when filming starts, and the stretches of
                                                a long linear work this visit is asked to film
    POST /api/v1/site-visits/{visit_id}/upload  {token} -> a one-time storage URL for the video
    POST /api/v1/site-visits/{visit_id}/done    {token, sha256, captured_at, claim, log} -> the
                                                visit waits for the video job

District scoping as everywhere: a district officer reaches only their district's works. A setting
the feature needs (migration 014, the capture secret, storage) missing answers 503, never a guess.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from psycopg.types.json import Jsonb
from pydantic import BaseModel, Field

from drishti import capture
from drishti.agents.site_progress import sitemap, spots
from drishti.api.routes import _work_in_area
from drishti.auth import Principal, current_user
from drishti.db import connect

router = APIRouter(prefix="/api/v1")
KINDS = ("baseline", "monthly", "check", "final")
LOG_MAX_BYTES = 1_000_000        # a capture log is points and marks, never pictures (T158: the
                                 # compass at 4 a second over a long road walk)


class Start(BaseModel):
    work_id: str = Field(min_length=1, max_length=120)
    kind: str


class Upload(BaseModel):
    token: str = Field(min_length=10, max_length=2000)


class Done(BaseModel):
    token: str = Field(min_length=10, max_length=2000)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    captured_at: datetime
    claim: str | None = Field(default=None, max_length=500)
    log: dict


def _ready(con) -> None:
    if not con.execute("SELECT to_regclass('site_visits') IS NOT NULL AS ok").fetchone()["ok"]:
        raise HTTPException(503, "site visits are not set up on this database yet "
                                 "(migration 014_site_visits.sql)")


def _form(con, work_id: str) -> dict | None:
    if not con.execute("SELECT to_regclass('cost_forms') IS NOT NULL AS ok").fetchone()["ok"]:
        return None
    row = con.execute("SELECT form FROM cost_forms WHERE work_id = %s AND status = 'submitted'",
                      (work_id,)).fetchone()
    return row["form"] if row else None


def _frame_url(path: str | None) -> str | None:
    if not path:
        return None
    try:
        return capture.signed_download(path)
    except (capture.NotSetUp, Exception):     # no storage: the page films without an overlay
        return None


def _viewpoints(con, work_id: str) -> list[dict]:
    """Every viewpoint the site has had, each with its newest frame and pan pictures from a visit
    that matched the site (T136: a viewpoint missed one month is still asked for the next), and
    its anchor: where to stand and which way to face (T158, spots.anchors)."""
    rows = con.execute("SELECT visit_id, kept, readings FROM site_visits WHERE work_id = %s AND "
                       "status = 'read' AND kept IS NOT NULL ORDER BY captured_at DESC",
                       (work_id,)).fetchall()
    newest: dict[str, dict] = {}
    history = []
    for row in rows:
        r = row.get("readings") or {}
        views = {vid: v for vid, v in ((row.get("kept") or {}).get("viewpoints") or {}).items()
                 if isinstance(v, dict)}
        history.append({"readings": r, "spots": views})
        if r.get("views_match_site") is False or r.get("gps_inside") is False \
                or r.get("mock_location") is True:
            continue
        for vid, v in views.items():
            newest.setdefault(vid, v)
    anchors = spots.anchors(list(reversed(history)))          # oldest first
    out = []
    for vid, v in sorted(newest.items()):
        a = anchors.get(vid)
        out.append({"id": vid, "frame_url": _frame_url(v.get("path")),
                    "pan_urls": [u for u in (_frame_url(p) for p in v.get("pans") or []) if u],
                    "anchor": {k: a[k] for k in ("lat", "lon", "acc", "box_m")} if a else None,
                    "facing": a.get("facing") if a else None})
    return out


def _token(token: str, visit_id: str, user: Principal) -> capture.Claims:
    try:
        claims = capture.check(token)
    except capture.NotSetUp as exc:
        raise HTTPException(503, str(exc)) from exc
    if claims is None or claims.visit_id != visit_id or claims.user_id != user.user_id:
        raise HTTPException(403, "the capture token is not valid for this visit")
    return claims


@router.get("/site-visits/{work_id:path}")
def site_visits_read(work_id: str, user: Principal = Depends(current_user)) -> dict:
    with connect() as con:
        _ready(con)
        w = _work_in_area(con, work_id, user)
        form = _form(con, work_id)
        site = sitemap.site_of(form, w.get("work_type_code"))
        rows = con.execute("SELECT visit_id, kind, status, claim, captured_at, readings, note "
                           "FROM site_visits WHERE work_id = %s ORDER BY captured_at NULLS LAST, "
                           "started_at", (work_id,)).fetchall()
        viewpoints = _viewpoints(con, work_id)
    return {"work_id": work_id, "site": site.to_json() if site else None,
            "next_kind": "baseline" if not any(r["kind"] == "baseline" and r["status"] != "rejected"
                                               for r in rows) else "monthly",
            "viewpoints": viewpoints, "spots_needed": sitemap.spots_needed(site, form),
            "visits": [{"visit_id": r["visit_id"], "kind": r["kind"], "status": r["status"],
                        "claim": r["claim"], "note": r["note"],
                        "captured_at": r["captured_at"].isoformat() if r["captured_at"] else None,
                        "readings": r["readings"]} for r in rows]}


@router.post("/site-visits/start")
def site_visit_start(body: Start, user: Principal = Depends(current_user)) -> dict:
    if body.kind not in KINDS:
        raise HTTPException(422, f"kind must be one of {', '.join(KINDS)}")
    with connect() as con:
        _ready(con)
        w = _work_in_area(con, body.work_id, user)
        visit_id = uuid.uuid4().hex
        try:
            token = capture.issue(visit_id, body.work_id, body.kind, user.user_id)
        except capture.NotSetUp as exc:
            raise HTTPException(503, str(exc)) from exc
        con.execute("INSERT INTO site_visits (visit_id, work_id, kind, saved_by) "
                    "VALUES (%s, %s, %s, %s)", (visit_id, body.work_id, body.kind, user.user_id))
        con.commit()
        form = _form(con, body.work_id)
        site = sitemap.site_of(form, w.get("work_type_code"))
        viewpoints = _viewpoints(con, body.work_id)
    return {"visit_id": visit_id, "token": token, "kind": body.kind,
            "site": site.to_json() if site else None, "viewpoints": viewpoints,
            "spots_needed": sitemap.spots_needed(site, form),
            # drawn now, from a seed only the server knows: nobody can prepare just these
            "stretches_asked": sitemap.stretches_asked(site, capture.seed(visit_id))}


def _visit(con, visit_id: str) -> dict:
    row = con.execute("SELECT * FROM site_visits WHERE visit_id = %s", (visit_id,)).fetchone()
    if row is None:
        raise HTTPException(404, "no such visit")
    return row


@router.post("/site-visits/{visit_id}/upload")
def site_visit_upload(visit_id: str, body: Upload, user: Principal = Depends(current_user)) -> dict:
    with connect() as con:
        _ready(con)
        _token(body.token, visit_id, user)
        v = _visit(con, visit_id)
        _work_in_area(con, v["work_id"], user)
        if v["status"] != "started":
            raise HTTPException(409, "this visit is already uploaded")
        path = f"videos/{visit_id}.webm"
        try:
            url = capture.signed_upload(path)
        except capture.NotSetUp as exc:
            raise HTTPException(503, str(exc)) from exc
        con.execute("UPDATE site_visits SET video_path = %s WHERE visit_id = %s", (path, visit_id))
        con.commit()
    return {"visit_id": visit_id, "upload_url": url, "path": path}


@router.post("/site-visits/{visit_id}/done")
def site_visit_done(visit_id: str, body: Done, user: Principal = Depends(current_user)) -> dict:
    if len(json.dumps(body.log)) > LOG_MAX_BYTES:
        raise HTTPException(413, "the capture log is too large")
    with connect() as con:
        _ready(con)
        claims = _token(body.token, visit_id, user)
        v = _visit(con, visit_id)
        _work_in_area(con, v["work_id"], user)
        if claims.work_id != v["work_id"] or claims.kind != v["kind"]:
            raise HTTPException(403, "the capture token is not valid for this visit")
        if v["status"] != "started":
            raise HTTPException(409, "this visit is already uploaded")
        log = {**body.log, "sealed_sha256": body.sha256}
        con.execute("UPDATE site_visits SET status = 'uploaded', uploaded_at = now(), "
                    "captured_at = %s, claim = %s, video_sha256 = %s, log = %s "
                    "WHERE visit_id = %s",
                    (body.captured_at, (body.claim or "").strip() or None, body.sha256,
                     Jsonb(log), visit_id))
        con.commit()
    return {"visit_id": visit_id, "status": "uploaded"}
