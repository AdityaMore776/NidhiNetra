"""The site video job: read every uploaded visit once, keep the readings, delete the video.

For each site visit with status 'uploaded' (migration 014), oldest first:
  1. fetch its video from storage (none -> 'rejected', with the reason)
  2. compare it with this work's earlier read visits (their kept viewpoint frames) and with every
     other work's read visits (fingerprints of all their frames; viewpoint frames of works whose
     site is within NEAR_M of this one, for the same-place check)
  3. visit.read(): the readings and the kept frames (faces blurred)
  4. store the kept frames, write the readings, mark it 'read', delete the video

The claim reader is optional (the Gemini reader on the owner's free key, T501); without it the
claims stay "not judged" and every other reading is still made.
"""

from __future__ import annotations

import tempfile
from collections.abc import Callable
from pathlib import Path

from psycopg.types.json import Jsonb

from drishti import capture, reference
from drishti.agents.site_progress import sitemap
from drishti.video import visit as vv

NEAR_M = 1000.0


def _form(con, work_id: str) -> dict | None:
    if not con.execute("SELECT to_regclass('cost_forms') IS NOT NULL AS ok").fetchone()["ok"]:
        return None
    r = con.execute("SELECT form FROM cost_forms WHERE work_id = %s AND status = 'submitted'",
                    (work_id,)).fetchone()
    return r["form"] if r else None


def _frames(store, part: dict) -> dict[str, bytes]:
    out = {}
    for vid, v in (part or {}).items():
        try:
            out[vid] = store.get(v["path"])
        except Exception:              # a missing frame only makes that viewpoint unmatched
            continue
    return out


def _earlier(row: dict, store, with_frames: bool) -> vv.Earlier:
    kept = row.get("kept") or {}
    views = kept.get("viewpoints") or {}
    spots = {vid: {"spot": v.get("spot"), "facing": v.get("facing")} for vid, v in views.items()
             if isinstance(v, dict)}
    return vv.Earlier(row["work_id"], row["visit_id"], row["kind"],
                      _frames(store, views) if with_frames else {},
                      list(kept.get("hashes") or []), row.get("readings") or {}, spots,
                      _frames(store, kept.get("stretches")) if with_frames else {})


def _asked(site, visit_id: str) -> list[str] | None:
    """The stretches of a linear work this visit was asked to film (T158)."""
    if site is None or site.kind != "linear":
        return None
    try:
        return sitemap.stretches_asked(site, capture.seed(visit_id))
    except capture.NotSetUp:
        return None


def process(con, store, judge: Callable | None = None, limit: int | None = None) -> list[dict]:
    """Read the uploaded visits; returns [{visit_id, work_id, status, note}]."""
    rows = con.execute("SELECT * FROM site_visits WHERE status = 'uploaded' "
                       "ORDER BY uploaded_at LIMIT %s", (limit or 1000,)).fetchall()
    done = []
    for row in rows:
        work = con.execute("SELECT work_id, work_type_code, district_lgd FROM works "
                           "WHERE work_id = %s", (row["work_id"],)).fetchone()
        form = _form(con, row["work_id"])
        site = sitemap.site_of(form, work["work_type_code"])
        try:
            data = store.get(row["video_path"]) if row["video_path"] else None
        except Exception:
            data = None
        if not data:
            note = "no video reached storage: film the visit again"
            con.execute("UPDATE site_visits SET status = 'rejected', note = %s, read_at = now() "
                        "WHERE visit_id = %s", (note, row["visit_id"]))
            con.commit()
            done.append({"visit_id": row["visit_id"], "work_id": row["work_id"],
                         "status": "rejected", "note": note})
            continue
        earlier = [_earlier(r, store, True) for r in con.execute(
            "SELECT * FROM site_visits WHERE work_id = %s AND status = 'read' "
            "ORDER BY captured_at", (row["work_id"],)).fetchall()]
        others = []
        for r in con.execute("SELECT v.*, w.district_lgd FROM site_visits v JOIN works w "
                             "USING (work_id) WHERE v.status = 'read' AND v.work_id <> %s",
                             (row["work_id"],)).fetchall():
            other_site = sitemap.site_of(_form(con, r["work_id"]))
            near = bool(site and other_site and sitemap.metres(
                site.lat, site.lon, other_site.lat, other_site.lon) <= NEAR_M)
            others.append(_earlier(r, store, near))
        asset = f"the {reference.work_type_name(work['work_type_code']).lower()}"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "visit.video"
            path.write_bytes(data)
            readings, kept = vv.read(path, row["log"] or {}, site, earlier, others, row["kind"],
                                     claim=row["claim"], asset=asset, judge=judge,
                                     spots_needed=sitemap.spots_needed(site, form),
                                     stretches_asked=_asked(site, row["visit_id"]))
        stored = {"viewpoints": {}, "stretches": {}, "hashes": kept["hashes"]}
        for vid, v in kept["viewpoints"].items():
            p = f"frames/{row['visit_id']}/{vid}.jpg"
            store.put(p, v["jpeg"], "image/jpeg")
            pans = []
            for i, jpg in enumerate(v.get("pans") or []):
                pans.append(f"frames/{row['visit_id']}/{vid}-pan{i + 1}.jpg")
                store.put(pans[-1], jpg, "image/jpeg")
            stored["viewpoints"][vid] = {"path": p, "hash": v["hash"], "t": v["t"],
                                         "faces": v["faces"], "spot": v.get("spot"),
                                         "facing": v.get("facing"), "pans": pans}
        for sid, v in kept["stretches"].items():
            p = f"frames/{row['visit_id']}/{sid}.jpg"
            store.put(p, v["jpeg"], "image/jpeg")
            stored["stretches"][sid] = {"path": p, "hash": v["hash"], "t": v["t"],
                                        "faces": v["faces"]}
        con.execute("UPDATE site_visits SET status = 'read', readings = %s, kept = %s, "
                    "read_at = now(), video_path = NULL WHERE visit_id = %s",
                    (Jsonb(readings), Jsonb(stored), row["visit_id"]))
        con.commit()
        try:
            store.delete(row["video_path"])
        except Exception:              # the readings are kept; a later run can retry the delete
            pass
        done.append({"visit_id": row["visit_id"], "work_id": row["work_id"], "status": "read",
                     "note": None})
    return done
