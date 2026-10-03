"""The engine's HTTP API, all under /api/v1.

Every route except the health checks needs a signed-in user, and every query
is scoped to that user's district when their role has one.
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import date
from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException, Query
from psycopg.types.json import Jsonb
from pydantic import BaseModel, Field

from drishti import audit, config, reference
from drishti.agents import registry
from drishti.agents.office_patterns.index import OfficeIndex
from drishti.agents.statistical.cohort import StatsStore
from drishti.auth import Principal, current_user
from drishti.batch import (
    SIGNALS_COLUMNS,
    SIGNALS_JOIN,
    WORK_COLUMNS,
    _normalise,
    assess_one,
    office_national,
    with_index,
)
from drishti.db import connect
from drishti.explain import explain as explain_work
from drishti.pipeline.orchestrator import Context, assess_work
from drishti.presanction import judge as presanction_judge
from drishti.validation import pii

router = APIRouter(prefix="/api/v1")

PAGE = 25
# Saved dashboard answers are keyed by the scoring version: a preview deployment of new
# scoring shares the live database, and must never overwrite the live site's answers.
CACHE_VERSION = "risk-v3"


@lru_cache(maxsize=1)
def _stats() -> StatsStore:
    return StatsStore.load(config.database_url())


def _scope(user: Principal, alias: str = "w") -> tuple[str, tuple]:
    """The WHERE clause that confines a query to what this user may see.

    MINISTRY sees all districts. STATE is confined to one state, DISTRICT and
    FIELD to one district. A narrower scope always wins, so a mis-set profile
    can widen nobody's view.
    """
    d = user.scope_district()
    if d is not None:
        return f"{alias}.district_lgd = %s", (d,)
    st = user.scope_state()
    if st is not None:
        return f"{alias}.state_lgd = %s", (st,)
    return "TRUE", ()


def _rows_jsonable(rows: list[dict]) -> list[dict]:
    """The same as _jsonable, for a list. Free-text an officer typed is masked like
    every other free text: a note can name a place or a person by accident."""
    return [{**r,
             "note": pii.mask(r["note"]) if r.get("note") else r.get("note"),
             "at": r["at"].isoformat() if hasattr(r.get("at"), "isoformat") else r.get("at")}
            for r in rows]


def _jsonable(row: dict) -> dict:
    out = {}
    for k, v in row.items():
        if k in ("description", "headline"):
            out[k] = pii.mask(v)          # the site shows the work, not the people
        elif isinstance(v, date):
            out[k] = v.isoformat()
        elif v is not None and type(v).__name__ == "Decimal":
            out[k] = float(v)
        else:
            out[k] = v
    return out


@router.get("/health")
def health() -> dict:
    return {"ok": True, "service": "drishti-engine"}


@router.get("/health/keepalive")
def keepalive() -> dict:
    """Hit daily by a Vercel cron so the free database is never paused for inactivity."""
    with connect() as con:
        n = con.execute("SELECT count(*) AS n FROM works").fetchone()["n"]
    return {"ok": True, "works": n}


@router.get("/me")
def me(user: Principal = Depends(current_user)) -> dict:
    """Who is asking and what they may see. Every screen shows the snapshot date
    next to its numbers, so it travels with the principal."""
    return {"user_id": user.user_id, "role": user.role, "district_lgd": user.district_lgd,
            "state_lgd": user.state_lgd, "name": user.name,
            "snapshot_date": config.snapshot_date().isoformat()}


def _cached(key: str, compute):
    """Serve a saved dashboard answer; compute and save it on a miss (migration 005).

    Aggregating all works took 4-9 s per request on the hosted database. The cache is
    emptied whenever works are re-assessed, so it never shows stale scores.
    """
    with connect() as con:
        row = con.execute("SELECT payload FROM dashboard_cache WHERE key = %s", (key,)).fetchone()
    if row is not None:
        return row["payload"]
    payload = compute()
    with connect() as con:
        con.execute("INSERT INTO dashboard_cache (key, payload) VALUES (%s, %s) "
                    "ON CONFLICT (key) DO UPDATE "
                    "SET payload = EXCLUDED.payload, computed_at = now()",
                    (key, Jsonb(payload)))
        con.commit()
    return payload


@router.get("/dashboard/summary")
def summary(user: Principal = Depends(current_user)) -> dict:
    key = f"{CACHE_VERSION}:summary:{user.scope_district() or 'ALL'}"
    return _cached(key, lambda: _summary(user))


def _summary(user: Principal) -> dict:
    where, params = _scope(user)
    with connect() as con:
        totals = con.execute(f"SELECT count(*) AS works, coalesce(sum(amount), 0) AS amount "
                             f"FROM works w WHERE {where}", params).fetchone()
        bands = con.execute(
            f"SELECT a.band, count(*) AS n FROM assessments a JOIN works w USING (work_id) "
            f"WHERE {where} GROUP BY a.band", params).fetchall()
        alerts = con.execute(
            f"SELECT unnest(a.alerts) AS agent, count(*) AS n FROM assessments a "
            f"JOIN works w USING (work_id) WHERE {where} GROUP BY 1", params).fetchall()
    alert_n: dict[str, int] = {}
    for r in alerts:
        key = registry.canonical_id(r["agent"])
        alert_n[key] = alert_n.get(key, 0) + r["n"]
    return {
        "works": totals["works"], "amount": float(totals["amount"]),
        "bands": {b: 0 for b in ("CRITICAL", "HIGH", "MEDIUM", "LOW")}
        | {r["band"]: r["n"] for r in bands},
        "agents": [{"id": e.id, "name": e.name, "question": e.question,
                    "built": e.assess is not None, "weight": e.weight,
                    "weight_note": e.weight_note,
                    "alerts": alert_n.get(e.id, 0)} for e in registry.engines()],
        "snapshot_date": config.snapshot_date().isoformat(),
    }


@router.get("/dashboard/assessment")
def assessment(user: Principal = Depends(current_user)) -> dict:
    """How much of the corpus each check could actually read.

    "Couldn't check" is a status, not a low score. These counts say how many works
    a check had nothing to look at, and how many works have any attached paper or
    photo at all. None of it carries risk, and none of it is a judgement about a
    work; it is the honest denominator behind every band on this site.
    """
    key = f"{CACHE_VERSION}:assessment:{user.scope_district() or user.scope_state() or 'ALL'}"
    return _cached(key, lambda: _assessment(user))


def _assessment(user: Principal) -> dict:
    where, params = _scope(user)
    with connect() as con:
        totals = con.execute(
            f"SELECT count(*) AS works, "
            f"count(a.work_id) AS assessed, "
            f"count(*) FILTER (WHERE a.limited) AS not_assessable, "
            f"count(*) FILTER (WHERE e.work_id IS NOT NULL) AS with_evidence, "
            f"coalesce(sum(w.amount) FILTER (WHERE a.limited), 0) AS not_assessable_amount "
            f"FROM works w LEFT JOIN assessments a USING (work_id) "
            f"LEFT JOIN evidence_facts e USING (work_id) WHERE {where}",
            params).fetchone()
        by_band = con.execute(
            f"SELECT a.band, count(*) AS n, count(*) FILTER (WHERE a.limited) AS limited "
            f"FROM works w JOIN assessments a USING (work_id) WHERE {where} "
            f"GROUP BY a.band", params).fetchall()
        evidence_by_band = con.execute(
            f"SELECT a.band, count(*) AS n, count(e.work_id) AS with_evidence "
            f"FROM works w JOIN assessments a USING (work_id) "
            f"LEFT JOIN evidence_facts e USING (work_id) WHERE {where} "
            f"GROUP BY a.band", params).fetchall()
    t = dict(totals)
    return {
        "works": t["works"],
        "assessed": t["assessed"],
        "not_assessable": t["not_assessable"],
        "not_assessable_amount": float(t["not_assessable_amount"]),
        "with_evidence": t["with_evidence"],
        "without_evidence": t["works"] - t["with_evidence"],
        "bands": {r["band"]: {"works": r["n"], "not_assessable": r["limited"],
                              "with_evidence": 0}
                  for r in by_band},
        "evidence_by_band": {r["band"]: r["with_evidence"] for r in evidence_by_band},
        "snapshot_date": config.snapshot_date().isoformat(),
        "note": "A check that had nothing to read reports NOT_ASSESSABLE. "
                "That carries no risk and is never shown as a low score.",
    }


@router.get("/dashboard/findings")
def findings(user: Principal = Depends(current_user)) -> list[dict]:
    """Every finding the engines raised on works now in the review queue, by code.

    Scoped to the queue on purpose: a LOW work keeps only its summary in the
    database (migration 003), so its detail is not stored and must not be counted.
    The queue always stores its full detail, so these numbers are complete.
    """
    key = f"{CACHE_VERSION}:findings:{user.scope_district() or user.scope_state() or 'ALL'}"
    return _cached(key, lambda: _findings(user))


def _findings(user: Principal) -> list[dict]:
    where, params = _scope(user)
    with connect() as con:
        rows = con.execute(
            f"SELECT ag->>'agent' AS agent, f->>'code' AS code, "
            f"max(f->>'text') AS text, bool_or(coalesce((f->>'hard')::boolean, false)) AS hard, "
            f"count(DISTINCT w.work_id) AS works, coalesce(sum(w.amount), 0) AS amount "
            f"FROM assessments a JOIN works w USING (work_id) "
            f"CROSS JOIN LATERAL jsonb_array_elements(coalesce(a.agents, '[]'::jsonb)) ag "
            f"CROSS JOIN LATERAL jsonb_array_elements(coalesce(ag->'findings', '[]'::jsonb)) f "
            f"WHERE {where} AND a.band IN ('CRITICAL', 'HIGH') "
            f"GROUP BY 1, 2 ORDER BY works DESC, 2", params).fetchall()
    specs = registry.by_id()
    out = []
    for r in rows:
        spec = specs.get(r["agent"])
        out.append({"agent": r["agent"], "code": r["code"], "text": r["text"],
                    "hard": r["hard"], "works": r["works"], "amount": float(r["amount"]),
                    "name": spec.name if spec else r["agent"],
                    "question": spec.question if spec else ""})
    return out


@router.get("/dashboard/districts")
def districts(user: Principal = Depends(current_user)) -> list[dict]:
    key = f"{CACHE_VERSION}:districts:{user.scope_district() or 'ALL'}"
    return _cached(key, lambda: _districts(user))


def _districts(user: Principal) -> list[dict]:
    where, params = _scope(user)
    with connect() as con:
        rows = con.execute(
            f"SELECT w.district_lgd, max(w.district_name) AS name, max(w.state_name) AS state, "
            f"count(*) AS works, coalesce(sum(w.amount), 0) AS amount, "
            f"count(*) FILTER (WHERE a.band IN ('CRITICAL', 'HIGH')) AS review "
            f"FROM works w LEFT JOIN assessments a USING (work_id) "
            f"WHERE {where} AND w.district_lgd IS NOT NULL GROUP BY w.district_lgd", params
        ).fetchall()
    return [{**_jsonable(r), "share": (r["review"] / r["works"]) if r["works"] else 0.0}
            for r in rows]


@router.get("/dashboard/offices")
def offices(user: Principal = Depends(current_user)) -> list[dict]:
    """Implementing offices whose completion dates need checking as a whole.

    An office that records many works as completed before they were recommended has a
    recording practice, not many separate problems (validation/timeline.py), so it is
    listed here once instead of flooding the review queue.
    """
    timeline = _stats().timeline
    rows = timeline.concentrated_offices() if timeline else []
    if not rows:
        return []
    where, params = _scope(user)
    with connect() as con:
        places = con.execute(
            f"SELECT w.agency_name, max(w.district_lgd) AS district_lgd, "
            f"max(w.district_name) AS district_name, max(w.state_name) AS state_name "
            f"FROM works w WHERE w.agency_name = ANY(%s) AND {where} GROUP BY w.agency_name",
            ([r["agency_name"] for r in rows], *params)).fetchall()
    place = {p["agency_name"]: p for p in places}
    return [{**r, "district_lgd": place[r["agency_name"]]["district_lgd"],
             "district_name": place[r["agency_name"]]["district_name"],
             "state_name": place[r["agency_name"]]["state_name"]}
            for r in rows if r["agency_name"] in place]


@router.get("/dashboard/office-habits")
def office_habits(user: Principal = Depends(current_user)) -> list[dict]:
    """Offices with a routine habit (Office Patterns, 2 Oct 2026): pricing most works just under
    a limit, or recording constructions complete within a week of sanction. A habit of an
    office is listed here once, never one queue item per work; never an MP."""
    key = f"{CACHE_VERSION}:office_habits:{user.scope_district() or 'ALL'}"
    return _cached(key, lambda: _office_habits(user))


def _office_habits(user: Principal) -> list[dict]:
    where, params = _scope(user)
    with connect() as con:
        national = office_national(con)
        rows = con.execute(
            f"SELECT w.district_lgd, w.agency_name, w.amount, w.work_type_code, w.status, "
            f"w.sanction_date, w.completed_date, w.district_name, w.state_name, "
            f"CASE WHEN w.sanction_date IS NOT NULL THEN w.description END AS description "
            f"FROM works w WHERE {where} AND w.agency_name IS NOT NULL", params).fetchall()
    idx = OfficeIndex.build(dict(r) for r in rows)
    idx.national = national
    place = {(str(r["district_lgd"] or "NA"), r["agency_name"]): (r["district_name"],
                                                                  r["state_name"])
             for r in rows}
    out = []
    for o in idx.routine_offices()[:50]:
        name, state = place.get((o["district_lgd"], o["office"]), (None, None))
        out.append({**o, "district_name": name, "state_name": state})
    return out


def _list(user: Principal, *, q: str | None, district: str | None, wtype: str | None,
          band: str | None, status: str | None, finding: str | None,
          assess: str | None, evidence: str | None, review_only: bool, page: int) -> dict:
    """One page of works, filtered.

    Every filter below is a column the officer can see, so the count shown next to
    a filter always matches the rows under it. `assess` and `evidence` are the two
    that say "a check could not look at this" without touching the risk score.
    """
    where, params = _scope(user)
    clauses, args = [where], list(params)
    if q:
        clauses.append("(w.description ILIKE %s OR w.work_id ILIKE %s)")
        args += [f"%{q}%", f"%{q}%"]
    if district:
        clauses.append("w.district_lgd = %s")
        args.append(district)
    if wtype:
        clauses.append("w.work_type_code = %s")
        args.append(wtype)
    if band:
        clauses.append("a.band = %s")
        args.append(band)
    if status:
        clauses.append("w.status = %s")
        args.append(status)
    if finding:
        clauses.append("EXISTS (SELECT 1 "
                       "FROM jsonb_array_elements(coalesce(a.agents, '[]'::jsonb)) ag, "
                       "jsonb_array_elements(coalesce(ag->'findings', '[]'::jsonb)) f "
                       "WHERE f->>'code' = %s)")
        args.append(finding)
    if assess == "not_assessable":
        clauses.append("a.limited IS TRUE")
    elif assess == "assessable":
        clauses.append("a.limited IS NOT TRUE")
    if evidence == "with":
        clauses.append("EXISTS (SELECT 1 FROM evidence_facts e WHERE e.work_id = w.work_id)")
    elif evidence == "without":
        clauses.append("NOT EXISTS (SELECT 1 FROM evidence_facts e WHERE e.work_id = w.work_id)")
    if review_only:
        clauses.append("a.band IN ('CRITICAL', 'HIGH')")
    cond = " AND ".join(clauses)
    cols = ("w.work_id, w.source, w.district_lgd, w.district_name, w.state_name, "
            "w.work_type_code, w.description, w.amount, w.status, w.recommended_date, "
            "w.agency_name, w.completed_date, "
            "a.band, a.score, a.priority, a.limited, a.alerts, a.headline, a.case_id, "
            "a.case_size, "
            "EXISTS (SELECT 1 FROM evidence_facts e WHERE e.work_id = w.work_id) AS has_evidence")
    with connect() as con:
        if review_only:
            # one row per case (migration 012): a purchase filed as 11 works is one question;
            # the case is shown by its highest-priority work, with how many works it holds
            case = "coalesce(a.case_id, w.work_id)"
            total = con.execute(f"SELECT count(DISTINCT {case}) AS n FROM works w LEFT JOIN "
                                f"assessments a USING (work_id) WHERE {cond}",
                                args).fetchone()["n"]
            rows = con.execute(
                f"SELECT * FROM (SELECT DISTINCT ON ({case}) {cols} FROM works w "
                f"LEFT JOIN assessments a USING (work_id) WHERE {cond} "
                f"ORDER BY {case}, a.priority DESC NULLS LAST, w.work_id) one_per_case "
                f"ORDER BY priority DESC NULLS LAST, work_id LIMIT %s OFFSET %s",
                args + [PAGE, (page - 1) * PAGE]).fetchall()
        else:
            total = con.execute(f"SELECT count(*) AS n FROM works w LEFT JOIN assessments a "
                                f"USING (work_id) WHERE {cond}", args).fetchone()["n"]
            rows = con.execute(
                f"SELECT {cols} FROM works w LEFT JOIN assessments a USING (work_id) "
                f"WHERE {cond} ORDER BY a.priority DESC NULLS LAST, w.work_id "
                f"LIMIT %s OFFSET %s", args + [PAGE, (page - 1) * PAGE]).fetchall()
    return {"total": total, "page": page, "page_size": PAGE,
            "filters": {"q": q, "district": district, "type": wtype, "band": band,
                        "status": status, "finding": finding, "assess": assess,
                        "evidence": evidence},
            "items": [_jsonable(r) for r in rows]}


@router.get("/works")
def works(q: str | None = None, district: str | None = None,
          type: str | None = Query(default=None), band: str | None = None,
          status: str | None = None, finding: str | None = None,
          assess: str | None = Query(default=None, pattern="^(assessable|not_assessable)$"),
          evidence: str | None = Query(default=None, pattern="^(with|without)$"),
          page: int = Query(default=1, ge=1), user: Principal = Depends(current_user)) -> dict:
    return _list(user, q=q, district=district, wtype=type, band=band, status=status,
                 finding=finding, assess=assess, evidence=evidence, review_only=False,
                 page=page)


@router.get("/queue")
def queue(district: str | None = None, band: str | None = None, status: str | None = None,
          finding: str | None = None,
          assess: str | None = Query(default=None, pattern="^(assessable|not_assessable)$"),
          evidence: str | None = Query(default=None, pattern="^(with|without)$"),
          page: int = Query(default=1, ge=1), user: Principal = Depends(current_user)) -> dict:
    return _list(user, q=None, district=district, wtype=None, band=band, status=status,
                 finding=finding, assess=assess, evidence=evidence, review_only=True,
                 page=page)


@router.get("/search")
def search(q: str = Query(min_length=2, max_length=80), page: int = Query(default=1, ge=1),
           user: Principal = Depends(current_user)) -> dict:
    """One box for the whole site: works, their districts, offices and checks.

    Grouped so an officer sees where each result lives, and scoped to what this
    user may see. Text in works is masked on the way out, as everywhere else.
    """
    where, params = _scope(user)
    like = f"%{q}%"
    with connect() as con:
        works_ = con.execute(
            f"SELECT w.work_id, w.district_name, w.state_name, w.work_type_code, "
            f"w.description, w.amount, a.band, a.headline "
            f"FROM works w LEFT JOIN assessments a USING (work_id) WHERE {where} "
            f"AND (w.work_id ILIKE %s OR w.description ILIKE %s OR w.agency_name ILIKE %s) "
            f"ORDER BY a.priority DESC NULLS LAST, w.work_id LIMIT 25 OFFSET %s",
            (*params, like, like, like, (page - 1) * 25)).fetchall()
        total_works = con.execute(
            f"SELECT count(*) AS n FROM works w WHERE {where} "
            f"AND (w.work_id ILIKE %s OR w.description ILIKE %s OR w.agency_name ILIKE %s)",
            (*params, like, like, like)).fetchone()["n"]
        districts_ = con.execute(
            f"SELECT w.district_lgd, max(w.district_name) AS name, max(w.state_name) AS state, "
            f"count(*) AS works FROM works w WHERE {where} "
            f"AND (w.district_name ILIKE %s OR w.district_lgd = %s) "
            f"GROUP BY w.district_lgd ORDER BY works DESC LIMIT 8",
            (*params, like, q.strip())).fetchall()
        offices_ = con.execute(
            f"SELECT w.agency_name, max(w.district_name) AS district_name, "
            f"max(w.state_name) AS state_name, count(*) AS works FROM works w "
            f"WHERE {where} AND w.agency_name ILIKE %s GROUP BY w.agency_name "
            f"ORDER BY works DESC LIMIT 8", (*params, like)).fetchall()
    # A check's link has to carry a finding *code*, because that is what /works
    # filters on; the code list comes from the same cached findings the dashboard
    # reads, so search and dashboard can never disagree about what a check raises.
    raised: dict[str, list[str]] = {}
    for f in findings(user):
        raised.setdefault(f["agent"], []).append(f["code"])
    checks = [{"id": e.id, "name": e.name, "question": e.question, "built": e.assess is not None,
               "codes": sorted(set(raised.get(e.id, [])))}
              for e in registry.engines()
              if q.lower() in e.name.lower() or q.lower() in e.question.lower()
              or q.lower() in e.id.lower()]
    return {
        "q": q,
        "works": {"total": total_works, "items": [_jsonable(r) for r in works_]},
        "districts": [_jsonable(r) for r in districts_],
        "offices": [_jsonable(r) for r in offices_],
        "checks": checks,
    }


@router.get("/audit/verify")
def verify_audit(user: Principal = Depends(current_user)) -> dict:
    """Does the trail still verify? Any officer can ask, and the answer says how
    many entries were walked. A broken chain names the entry where it broke."""
    with connect() as con:
        return audit.verify_chain(con)


@router.get("/works/{work_id:path}/case")
def work_case(work_id: str, user: Principal = Depends(current_user)) -> dict:
    """The other works in this work's case.

    A purchase filed as eleven works is one question for an officer, so the work
    page links to all of them instead of making the officer search again.
    """
    where, params = _scope(user, alias="works")
    with connect() as con:
        row = con.execute("SELECT case_id, case_size FROM assessments WHERE work_id = %s",
                          (work_id,)).fetchone()
        if row is None:
            raise HTTPException(404, "this work has not been assessed")
        case_id = row["case_id"]
        if not case_id:
            return {"case_id": None, "size": 1, "items": []}
        items = con.execute(
            f"SELECT w.work_id, w.source, w.district_lgd, w.district_name, w.state_name, "
            f"w.work_type_code, w.description, w.amount, w.status, w.recommended_date, "
            f"a.band, a.score, a.priority, a.limited, a.alerts, a.headline "
            f"FROM works w JOIN assessments a USING (work_id) "
            f"WHERE a.case_id = %s AND {where} ORDER BY a.priority DESC NULLS LAST, w.work_id",
            (case_id, *params)).fetchall()
    return {"case_id": case_id, "size": row["case_size"], "items": [_jsonable(r) for r in items]}


@router.get("/works/{work_id:path}")
def work(work_id: str, user: Principal = Depends(current_user)) -> dict:
    where, params = _scope(user, alias="works")     # the signals join needs the bare name
    with connect() as con:
        row = con.execute(f"SELECT {WORK_COLUMNS}, {SIGNALS_COLUMNS} FROM works "
                          f"{SIGNALS_JOIN} WHERE works.work_id = %s AND {where}",
                          (work_id, *params)).fetchone()
        if row is None:
            raise HTTPException(404, "no such work in your area")
        a = con.execute("SELECT * FROM assessments WHERE work_id = %s", (work_id,)).fetchone()
        if a is None:
            assess_one(con, work_id, Context(stats=_stats(), as_of=config.snapshot_date()))
            a = con.execute("SELECT * FROM assessments WHERE work_id = %s",
                            (work_id,)).fetchone()
        ctx = None
        if a["compact"]:
            w = _normalise(dict(row))
            ctx = with_index(Context(stats=_stats(), as_of=config.snapshot_date()), con, w)
        # read the officer's side of the story while the connection is still open
        review = _review(con, work_id, dict(row), a)
    assessment = _jsonable(dict(a))
    assessment["assessed_at"] = str(a["assessed_at"])
    if a["compact"]:
        full = assess_work(w, ctx).to_row()
        for k in ("parts", "validation", "agents"):
            assessment[k] = full[k]
    assessment["agents"] = _described(assessment.get("agents") or [])
    # the raw evidence facts stay on the server: a certificate's place line is OCR text that can
    # name a person ("near <name> house"), and the page shows the engines' findings instead
    # (found by tests/api/test_api_at_scale.py, T056)
    work_row = {k: v for k, v in dict(row).items() if k not in ("signals", "evidence")}
    return {"work": _jsonable(work_row), "assessment": assessment, "review": review}


def _review(con, work_id: str, w: dict, a) -> dict:
    """What an officer has already done about this work, and when.

    Every date here is one we stored: the eSAKSHI record's own dates, or a moment a
    step was reached. Nothing is inferred, and a step that has not happened has no
    date at all rather than a guessed one.
    """
    alert = con.execute(
        "SELECT alert_id, code, engine, state, opened_at, updated_at, closed_at, actor, note "
        "FROM alerts WHERE work_id = %s ORDER BY opened_at DESC LIMIT 1",
        (work_id,)).fetchone()
    insp = con.execute(
        "SELECT i.inspection_id, i.alert_id, i.state, i.assigned_to, i.assigned_by, "
        "i.requested_by, "
        "i.requested_at, i.assigned_at, i.verified_at, i.recorded_at, i.closed_at, "
        "i.due_date, i.note, i.history, "
        "(SELECT jsonb_build_object('outcome', r.outcome, 'observed', r.observed, "
        " 'recorded_by', r.recorded_by, 'recorded_at', r.recorded_at, "
        " 'gps_source', r.gps_source) FROM inspection_results r "
        "  WHERE r.inspection_id = i.inspection_id ORDER BY r.result_id DESC LIMIT 1) AS result "
        "FROM inspections i WHERE i.work_id = %s", (work_id,)).fetchone()

    steps: list[dict] = []
    # the record's own dates, in the order a reader meets them
    if w.get("recommended_date"):
        steps.append({"step": "RECOMMENDED", "at": str(w["recommended_date"]),
                      "what": "the MP recommended this work"})
    if w.get("sanction_date"):
        steps.append({"step": "SANCTIONED", "at": str(w["sanction_date"]),
                      "what": "the work was sanctioned"})
    if insp:
        for col, step, what in (
                ("requested_at", "INSPECTION_REQUIRED", "a visit was asked for"),
                ("assigned_at", "ASSIGNED", "a field officer was assigned"),
                ("verified_at", "FIELD_VERIFIED", "it was seen on the ground"),
                ("recorded_at", "RESULT_RECORDED", "what was seen was recorded"),
                ("closed_at", "CLOSED", "the visit was closed")):
            if insp.get(col):
                steps.append({"step": step, "at": str(insp[col]), "what": what})
    if w.get("completed_date"):
        steps.append({"step": "COMPLETED", "at": str(w["completed_date"]),
                      "what": "the record says the work was completed"})
    steps.sort(key=lambda e: e["at"])

    return {"alert": _jsonable(dict(alert)) if alert else None,
            "inspection": _jsonable(dict(insp)) if insp else None,
            "timeline": steps,
            "history": _rows_jsonable(audit.for_work(con, work_id)),
            "chain": audit.verify_chain(con)}


def _described(agents: list[dict]) -> list[dict]:
    """Stored results under today's engine ids, each with its display name and question."""
    specs = registry.by_id()
    out = []
    for r in agents:
        aid = registry.canonical_id(r.get("agent", ""))
        spec = specs.get(aid)
        out.append({**r, "agent": aid, "name": spec.name if spec else aid,
                    "question": spec.question if spec else ""})
    return out


class Recommendation(BaseModel):
    """A recommendation not yet sanctioned, as typed into the pre-sanction form (T064)."""

    district_lgd: str = Field(min_length=1, max_length=8)
    description: str = Field(min_length=3, max_length=2000)
    amount: float = Field(gt=0, le=1e10)
    work_type_code: str | None = Field(default=None, max_length=40)
    agency_name: str | None = Field(default=None, max_length=300)
    is_outside_constituency: bool = False


@router.post("/presanction")
def presanction(rec: Recommendation, user: Principal = Depends(current_user)) -> dict:
    """Every engine on a recommendation before sanction -> Green / Amber / Red with the
    engines' own sentences. Nothing is stored and nothing is blocked."""
    scope = user.scope_district()
    if scope is not None and rec.district_lgd != scope:
        raise HTTPException(404, "no such district in your area")
    as_of = config.snapshot_date()
    with connect() as con:
        d = con.execute("SELECT district_lgd, name, state_lgd, state_name FROM districts "
                        "WHERE district_lgd = %s", (rec.district_lgd,)).fetchone()
        if d is None:
            raise HTTPException(404, "no such district")
        work = {"work_id": "PRE-SANCTION", "source": "SCENARIO", "house": None, "term": None,
                "state_lgd": d["state_lgd"], "state_name": d["state_name"],
                "district_lgd": d["district_lgd"], "district_name": d["name"],
                "constituency": None, "mp_name": None, "agency_name": rec.agency_name,
                "fy": None, "work_type_code": rec.work_type_code or None, "category": None,
                "description": rec.description.strip(), "amount": float(rec.amount),
                "recommended_date": as_of, "completed_date": None, "status": "RECOMMENDED",
                "quantity": None, "quantity_unit": None,
                "is_outside_constituency": rec.is_outside_constituency, "signals": {}}
        ctx = with_index(Context(stats=_stats(), as_of=as_of), con, work)
    result = presanction_judge(assess_work(work, ctx))
    return {**asdict(result), "as_of": as_of.isoformat(), "district_name": d["name"]}


class Example(Recommendation):
    """A work as typed into the Visualization Engine (T092): a recommendation, or a work further
    along when the judge gives its status and dates."""

    status: str = Field(default="RECOMMENDED", pattern="^(RECOMMENDED|SANCTIONED|COMPLETED)$")
    recommended_date: date | None = None
    sanction_date: date | None = None
    completed_date: date | None = None


@router.post("/explain")
def explain(ex: Example, user: Principal = Depends(current_user)) -> dict:
    """Every step DRISHTI takes on one work, for the Visualization Engine page (T092): the same
    pipeline as the batch, laid out step by step. Nothing is stored."""
    scope = user.scope_district()
    if scope is not None and ex.district_lgd != scope:
        raise HTTPException(404, "no such district in your area")
    as_of = config.snapshot_date()
    with connect() as con:
        d = con.execute("SELECT district_lgd, name, state_lgd, state_name FROM districts "
                        "WHERE district_lgd = %s", (ex.district_lgd,)).fetchone()
        if d is None:
            raise HTTPException(404, "no such district")
        work = {"work_id": "EXAMPLE", "source": "SCENARIO", "house": None, "term": None,
                "state_lgd": d["state_lgd"], "state_name": d["state_name"],
                "district_lgd": d["district_lgd"], "district_name": d["name"],
                "constituency": None, "mp_name": None, "agency_name": ex.agency_name,
                "fy": None, "work_type_code": ex.work_type_code or None, "category": None,
                "description": ex.description.strip(), "amount": float(ex.amount),
                "recommended_date": ex.recommended_date or as_of,
                "sanction_date": ex.sanction_date, "completed_date": ex.completed_date,
                "status": ex.status, "quantity": None, "quantity_unit": None,
                "is_outside_constituency": ex.is_outside_constituency, "signals": {}}
        ctx = with_index(Context(stats=_stats(), as_of=as_of), con, work)
    return explain_work(work, ctx)


@router.get("/presanction/options")
def presanction_options(user: Principal = Depends(current_user)) -> dict:
    """What the pre-sanction form offers: the user's districts and the work types."""
    where, params = _scope(user, alias="d")
    with connect() as con:
        rows = con.execute(f"SELECT d.district_lgd, d.name, d.state_name FROM districts d "
                           f"WHERE {where} ORDER BY d.state_name, d.name", params).fetchall()
    types = sorted(({"code": c, "name": s["name"]} for c, s in reference.work_types().items()),
                   key=lambda t: t["name"])
    return {"districts": [dict(r) for r in rows], "work_types": types,
            "as_of": config.snapshot_date().isoformat()}


# --- the officer-facing review loop ------------------------------------------------
# An alert is a request to look at a work; an inspection is that request reaching the
# field. The two moves below are the whole workflow, and neither can be skipped by a
# mistyped click: the site only offers the arrows in INSPECTION_NEXT and ALERT_NEXT.

INSPECTION_NEXT: dict[str, tuple[str, ...]] = {
    "REVIEW": ("INSPECTION_REQUIRED",),
    "INSPECTION_REQUIRED": ("ASSIGNED",),
    "ASSIGNED": ("FIELD_VERIFIED",),
    "FIELD_VERIFIED": ("RESULT_RECORDED",),
    "RESULT_RECORDED": ("CLOSED",),
    "CLOSED": (),
}
ALERT_NEXT: dict[str, tuple[str, ...]] = {
    "NEW": ("ACKNOWLEDGED", "RESOLVED"),
    "ACKNOWLEDGED": ("INVESTIGATING", "RESOLVED"),
    "INVESTIGATING": ("RESOLVED",),
    "RESOLVED": (),
}
INSPECTION_STATES = tuple(INSPECTION_NEXT)
ALERT_STATES = tuple(ALERT_NEXT)
OUTCOMES = ("OBSERVED", "NOT_OBSERVED", "PARTIALLY_OBSERVED", "UNABLE_TO_VERIFY")


def _check_move(moves: dict[str, tuple[str, ...]], current: str, want: str) -> None:
    if want not in moves:
        raise HTTPException(400, "unknown state")
    if want != current and want not in moves[current]:
        raise HTTPException(409, f"a {current.lower().replace('_', ' ')} alert or inspection "
                                 f"cannot move straight to {want.lower().replace('_', ' ')}")


@router.get("/inspections")
def list_inspections(state: str | None = None, district: str | None = None,
                     page: int = Query(default=1, ge=1),
                     user: Principal = Depends(current_user)) -> dict:
    """The inspection planner's list: works asked to be verified on the ground, in
    the order an officer should tackle them."""
    where, params = _scope(user, alias="works")
    clauses, args = [where], list(params)
    if state:
        clauses.append("i.state = %s")
        args.append(state)
    if district:
        clauses.append("works.district_lgd = %s")
        args.append(district)
    cond = " AND ".join(clauses)
    cols = ("i.inspection_id, i.work_id, i.state, i.band, i.assigned_to, i.due_date, "
            "i.priority, i.note, i.created_at, i.updated_at, "
            "works.district_lgd, works.district_name, works.state_name, "
            "works.work_type_code, works.description, works.amount, works.status, "
            "works.agency_name, a.case_size, a.alerts, "
            "EXISTS (SELECT 1 FROM evidence_facts e WHERE e.work_id = works.work_id) "
            "AS has_evidence, "
            "(SELECT count(*) FROM inspection_results r WHERE r.inspection_id = i.inspection_id) "
            "AS results")
    with connect() as con:
        total = con.execute(f"SELECT count(*) AS n FROM inspections i JOIN works USING (work_id) "
                            f"LEFT JOIN assessments a USING (work_id) WHERE {cond}",
                            args).fetchone()["n"]
        rows = con.execute(f"SELECT {cols} FROM inspections i JOIN works USING (work_id) "
                           f"LEFT JOIN assessments a USING (work_id) WHERE {cond} "
                           f"ORDER BY i.priority DESC NULLS LAST, i.due_date NULLS LAST, "
                           f"i.inspection_id LIMIT %s OFFSET %s",
                           args + [PAGE, (page - 1) * PAGE]).fetchall()
        counts = con.execute(f"SELECT i.state, count(*) AS n FROM inspections i "
                             f"JOIN works USING (work_id) WHERE {where} GROUP BY i.state",
                             params).fetchall()
    out = [_jsonable(dict(r)) for r in rows]
    for r in out:
        r["created_at"] = str(r["created_at"])
        r["updated_at"] = str(r["updated_at"])
    return {"total": total, "page": page, "page_size": PAGE, "items": out,
            "counts": {r["state"]: r["n"] for r in counts},
            "states": list(INSPECTION_STATES),
            "next": {k: list(v) for k, v in INSPECTION_NEXT.items()}}


class InspectionIn(BaseModel):
    work_id: str = Field(min_length=1, max_length=60)
    note: str | None = Field(default=None, max_length=1000)
    due_date: date | None = None
    assigned_to: str | None = Field(default=None, max_length=200)


@router.post("/inspections")
def create_inspection(body: InspectionIn, user: Principal = Depends(current_user)) -> dict:
    """Ask for a work to be verified on the ground. Idempotent per work: asking
    twice updates the existing visit instead of creating a second one."""
    where, params = _scope(user, alias="works")
    with connect() as con:
        w = con.execute(f"SELECT works.work_id, works.district_lgd, works.state_lgd, "
                        f"a.band, a.priority FROM works LEFT JOIN assessments a USING (work_id) "
                        f"WHERE works.work_id = %s AND {where}", (body.work_id, *params)).fetchone()
        if w is None:
            raise HTTPException(404, "no such work in your area")
        # the alert this visit answers, if there is one open: so the alert screen and
        # the planner never show two unrelated stories about the same work
        alert = con.execute("SELECT alert_id FROM alerts WHERE work_id = %s "
                            "AND state <> 'RESOLVED'", (body.work_id,)).fetchone()
        row = con.execute(
            "INSERT INTO inspections (work_id, district_lgd, state_lgd, band, state, "
            "assigned_to, due_date, priority, note, requested_by, requested_at, alert_id) "
            "VALUES (%s, %s, %s, %s, 'INSPECTION_REQUIRED', %s, %s, %s, %s, %s, now(), %s) "
            "ON CONFLICT (work_id) DO UPDATE SET state = 'INSPECTION_REQUIRED', "
            "assigned_to = EXCLUDED.assigned_to, due_date = EXCLUDED.due_date, "
            "note = EXCLUDED.note, band = EXCLUDED.band, priority = EXCLUDED.priority, "
            "requested_by = EXCLUDED.requested_by, requested_at = now(), "
            "alert_id = EXCLUDED.alert_id, "
            "updated_at = now() WHERE inspections.state NOT IN ('FIELD_VERIFIED', "
            "'RESULT_RECORDED', 'CLOSED') RETURNING inspection_id, state",
            (body.work_id, w["district_lgd"], w["state_lgd"], w["band"], body.assigned_to,
             body.due_date, float(w["priority"]) if w["priority"] is not None else None,
             body.note, user.user_id, alert["alert_id"] if alert else None)).fetchone()
        if row is None:                     # already reached the ground; do not rewind it
            existing = con.execute("SELECT inspection_id, state FROM inspections "
                                   "WHERE work_id = %s", (body.work_id,)).fetchone()
            raise HTTPException(409, f"this work is already at step "
                                     f"'{existing['state'].replace('_', ' ').lower()}'")
        con.commit()
        audit.record(con, actor=user.user_id, role=user.role, action="INSPECTION_REQUESTED",
                     entity="inspection", entity_id=row["inspection_id"], work_id=body.work_id,
                     after={"state": row["state"], "due_date": str(body.due_date or "")},
                     note=body.note)
        con.commit()
    return {"inspection_id": row["inspection_id"], "state": row["state"],
            "work_id": body.work_id}


class InspectionMove(BaseModel):
    state: str = Field(min_length=1, max_length=40)
    assigned_to: str | None = Field(default=None, max_length=200)
    due_date: date | None = None
    note: str | None = Field(default=None, max_length=1000)
    actor: str | None = Field(default=None, max_length=200)


@router.patch("/inspections/{inspection_id}")
def move_inspection(inspection_id: int, body: InspectionMove,
                   user: Principal = Depends(current_user)) -> dict:
    """Move a visit one step forward. The step list is fixed, and a visit cannot
    be marked seen on the ground until it has been assigned."""
    where, params = _scope(user, alias="works")
    with connect() as con:
        row = con.execute(f"SELECT i.state, i.work_id FROM inspections i "
                          f"JOIN works USING (work_id) WHERE i.inspection_id = %s AND {where}",
                          (inspection_id, *params)).fetchone()
        if row is None:
            raise HTTPException(404, "no such inspection in your area")
        if body.state not in INSPECTION_NEXT:
            raise HTTPException(400, "unknown inspection state")
        _check_move(INSPECTION_NEXT, row["state"], body.state)
        if body.state == "FIELD_VERIFIED" and not (body.assigned_to
                                                   or con.execute(
                                                       "SELECT assigned_to FROM inspections "
                                                       "WHERE inspection_id = %s",
                                                       (inspection_id,)).fetchone()
                                                       ["assigned_to"]):
            raise HTTPException(409, "name who verified it before marking it seen")
        # Each step gets its own timestamp, stamped when it is first reached, so the
        # work's timeline shows what really happened rather than when the row was last
        # touched. Nothing here is ever back-dated.
        stamp = {"ASSIGNED": "assigned_at", "FIELD_VERIFIED": "verified_at",
                 "CLOSED": "closed_at"}.get(body.state)
        con.execute(
            f"UPDATE inspections SET state = %s::text, "
            f"assigned_to = coalesce(%s::text, assigned_to), "
            f"due_date = coalesce(%s::date, due_date), note = coalesce(%s::text, note), "
            f"assigned_by = coalesce(assigned_by, %s::text), "
            f"{stamp + ' = COALESCE(' + stamp + ', now()),' if stamp else ''} "
            f"history = history || jsonb_build_array(jsonb_build_object("
            f"'step', %s::text, 'at', now(), 'by', %s::text, 'note', %s::text)), "
            f"updated_at = now() WHERE inspection_id = %s",
            (body.state, body.assigned_to, body.due_date, body.note,
             body.assigned_to or body.actor,
             body.state, body.actor, body.note, inspection_id))
        audit.record(con, actor=body.actor or user.user_id, role=user.role,
                     action="INSPECTION_ADVANCED", entity="inspection",
                     entity_id=inspection_id, work_id=row["work_id"],
                     before={"state": row["state"]}, after={"state": body.state},
                     note=body.note)
        con.commit()
    return {"inspection_id": inspection_id, "state": body.state}


class ResultIn(BaseModel):
    outcome: str = Field(pattern="^(" + "|".join(OUTCOMES) + ")$")
    observed: str | None = Field(default=None, max_length=2000)
    lat: float | None = Field(default=None, ge=-90, le=90)
    lon: float | None = Field(default=None, ge=-180, le=180)
    gps_source: str | None = Field(default=None, max_length=40)
    recorded_by: str | None = Field(default=None, max_length=200)


@router.post("/inspections/{inspection_id}/result")
def record_result(inspection_id: int, body: ResultIn,
                 user: Principal = Depends(current_user)) -> dict:
    """What the field officer saw. UNABLE_TO_VERIFY is a real answer and records no
    finding either way, exactly like NOT_ASSESSABLE in an engine."""
    where, params = _scope(user, alias="works")
    with connect() as con:
        row = con.execute(f"SELECT i.state, i.work_id FROM inspections i "
                          f"JOIN works USING (work_id) "
                          f"WHERE i.inspection_id = %s AND {where}", (inspection_id, *params)
                          ).fetchone()
        if row is None:
            raise HTTPException(404, "no such inspection in your area")
        if row["state"] not in ("FIELD_VERIFIED", "RESULT_RECORDED"):
            raise HTTPException(409, "a result can only be recorded after the visit is marked seen")
        con.execute("INSERT INTO inspection_results (inspection_id, outcome, observed, lat, lon, "
                    "gps_source, recorded_by) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                    (inspection_id, body.outcome, body.observed, body.lat, body.lon,
                     body.gps_source, body.recorded_by))
        audit.record(con, actor=body.recorded_by or user.user_id, role=user.role,
                     action="INSPECTION_RESULT_RECORDED", entity="inspection_result",
                     entity_id=inspection_id, work_id=row["work_id"],
                     after={"outcome": body.outcome, "observed": body.observed})
        con.execute("UPDATE inspections SET state = 'RESULT_RECORDED', "
                    "recorded_at = COALESCE(recorded_at, now()), updated_at = now() "
                    "WHERE inspection_id = %s", (inspection_id,))
        con.commit()
    return {"inspection_id": inspection_id, "state": "RESULT_RECORDED",
            "outcome": body.outcome}


@router.get("/alerts")
def list_alerts(state: str | None = None, page: int = Query(default=1, ge=1),
                user: Principal = Depends(current_user)) -> dict:
    """Open alerts, newest first, with the work each one points at."""
    where, params = _scope(user, alias="works")
    clauses, args = [where], list(params)
    if state:
        clauses.append("al.state = %s")
        args.append(state)
    cond = " AND ".join(clauses)
    cols = ("al.alert_id, al.work_id, al.code, al.engine, al.state, al.opened_at, "
            "al.updated_at, al.actor, al.note, works.district_lgd, works.district_name, "
            "works.state_name, works.work_type_code, works.description, works.amount, "
            "works.status, a.band, a.score, a.priority, a.case_size")
    with connect() as con:
        total = con.execute(f"SELECT count(*) AS n FROM alerts al JOIN works USING (work_id) "
                            f"LEFT JOIN assessments a USING (work_id) WHERE {cond}",
                            args).fetchone()["n"]
        rows = con.execute(f"SELECT {cols} FROM alerts al JOIN works USING (work_id) "
                           f"LEFT JOIN assessments a USING (work_id) WHERE {cond} "
                           f"ORDER BY al.state, a.priority DESC NULLS LAST, al.alert_id "
                           f"LIMIT %s OFFSET %s", args + [PAGE, (page - 1) * PAGE]).fetchall()
        counts = con.execute(f"SELECT al.state, count(*) AS n FROM alerts al "
                             f"JOIN works USING (work_id) WHERE {where} GROUP BY al.state",
                             params).fetchall()
    out = [_jsonable(dict(r)) for r in rows]
    for r in out:
        r["opened_at"] = str(r["opened_at"])
        r["updated_at"] = str(r["updated_at"])
    return {"total": total, "page": page, "page_size": PAGE, "items": out,
            "counts": {r["state"]: r["n"] for r in counts},
            "states": list(ALERT_STATES),
            "next": {k: list(v) for k, v in ALERT_NEXT.items()}}


class AlertMove(BaseModel):
    state: str = Field(min_length=1, max_length=40)
    note: str | None = Field(default=None, max_length=1000)
    actor: str | None = Field(default=None, max_length=200)


@router.patch("/alerts/{alert_id}")
def move_alert(alert_id: int, body: AlertMove, user: Principal = Depends(current_user)) -> dict:
    """Move an alert along. Starting an investigation also opens the inspection
    that will answer it, so the planner and the alert list never disagree."""
    where, params = _scope(user, alias="works")
    with connect() as con:
        row = con.execute(f"SELECT al.state, al.work_id FROM alerts al JOIN works USING (work_id) "
                          f"WHERE al.alert_id = %s AND {where}", (alert_id, *params)).fetchone()
        if row is None:
            raise HTTPException(404, "no such alert in your area")
        _check_move(ALERT_NEXT, row["state"], body.state)
        if body.state == "RESOLVED" and not (body.note or "").strip():
            # closing without looking is a legitimate decision (the work turned out to be
            # recorded already); it just has to say so, so the record is worth reading
            raise HTTPException(422, "say why this alert is closed, even if only in one line")
        con.execute("UPDATE alerts SET state = %s, note = coalesce(%s, note), actor = %s, "
                    "updated_at = now(), closed_at = CASE WHEN %s = 'RESOLVED' THEN now() "
                    "ELSE closed_at END WHERE alert_id = %s",
                    (body.state, body.note, body.actor, body.state, alert_id))
        audit.record(con, actor=body.actor or user.user_id, role=user.role,
                     action=f"ALERT_{body.state}", entity="alert", entity_id=alert_id,
                     work_id=row["work_id"], before={"state": row["state"]},
                     after={"state": body.state}, note=body.note)
        if body.state == "INVESTIGATING":
            w = con.execute("SELECT works.district_lgd, works.state_lgd, a.band, a.priority "
                            "FROM works LEFT JOIN assessments a USING (work_id) "
                            "WHERE works.work_id = %s", (row["work_id"],)).fetchone()
            con.execute(
                "INSERT INTO inspections (work_id, district_lgd, state_lgd, band, state, "
                "assigned_to, due_date, priority, note) "
                "VALUES (%s, %s, %s, %s, 'INSPECTION_REQUIRED', %s, NULL, %s, %s) "
                "ON CONFLICT (work_id) DO UPDATE SET state = CASE WHEN inspections.state IN "
                "('REVIEW', 'INSPECTION_REQUIRED') THEN 'INSPECTION_REQUIRED' "
                "ELSE inspections.state END, updated_at = now()",
                (row["work_id"], w["district_lgd"], w["state_lgd"], w["band"], body.actor,
                 float(w["priority"]) if w["priority"] is not None else None, body.note))
        con.commit()
    return {"alert_id": alert_id, "state": body.state}
