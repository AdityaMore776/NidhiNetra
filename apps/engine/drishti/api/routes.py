"""The engine's HTTP API, all under /api/v1.

Every route except the health checks needs a signed-in user, and every query
is scoped to that user's district when their role has one.
"""

from __future__ import annotations

from datetime import date
from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException, Query
from psycopg.types.json import Jsonb

from drishti import config
from drishti.agents import registry
from drishti.agents.statistical.cohort import StatsStore
from drishti.auth import Principal, current_user
from drishti.batch import (
    SIGNALS_COLUMNS,
    SIGNALS_JOIN,
    WORK_COLUMNS,
    _normalise,
    assess_one,
)
from drishti.db import connect
from drishti.pipeline.orchestrator import Context, assess_work
from drishti.validation import pii

router = APIRouter(prefix="/api/v1")

PAGE = 25
# Saved dashboard answers are keyed by the scoring version: a preview deployment of new
# scoring shares the live database, and must never overwrite the live site's answers.
CACHE_VERSION = "risk-v2"


@lru_cache(maxsize=1)
def _stats() -> StatsStore:
    return StatsStore.load(config.database_url())


def _scope(user: Principal, alias: str = "w") -> tuple[str, tuple]:
    d = user.scope_district()
    if d is None:
        return "TRUE", ()
    return f"{alias}.district_lgd = %s", (d,)


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
    return {"user_id": user.user_id, "role": user.role, "district_lgd": user.district_lgd,
            "name": user.name}


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
        "validation_alerts": alert_n.get("validation", 0),
        "snapshot_date": config.snapshot_date().isoformat(),
    }


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


def _list(user: Principal, *, q: str | None, district: str | None, wtype: str | None,
          band: str | None, review_only: bool, page: int) -> dict:
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
    if review_only:
        clauses.append("a.band IN ('CRITICAL', 'HIGH')")
    cond = " AND ".join(clauses)
    with connect() as con:
        total = con.execute(f"SELECT count(*) AS n FROM works w LEFT JOIN assessments a "
                            f"USING (work_id) WHERE {cond}", args).fetchone()["n"]
        rows = con.execute(
            f"SELECT w.work_id, w.source, w.district_lgd, w.district_name, w.state_name, "
            f"w.work_type_code, w.description, w.amount, w.status, w.recommended_date, "
            f"a.band, a.score, a.priority, a.limited, a.alerts, a.headline "
            f"FROM works w LEFT JOIN assessments a USING (work_id) WHERE {cond} "
            f"ORDER BY a.priority DESC NULLS LAST, w.work_id LIMIT %s OFFSET %s",
            args + [PAGE, (page - 1) * PAGE]).fetchall()
    return {"total": total, "page": page, "page_size": PAGE,
            "items": [_jsonable(r) for r in rows]}


@router.get("/works")
def works(q: str | None = None, district: str | None = None,
          type: str | None = Query(default=None), band: str | None = None,
          page: int = Query(default=1, ge=1), user: Principal = Depends(current_user)) -> dict:
    return _list(user, q=q, district=district, wtype=type, band=band, review_only=False,
                 page=page)


@router.get("/queue")
def queue(district: str | None = None, band: str | None = None,
          page: int = Query(default=1, ge=1), user: Principal = Depends(current_user)) -> dict:
    return _list(user, q=None, district=district, wtype=None, band=band, review_only=True,
                 page=page)


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
    assessment = _jsonable(dict(a))
    assessment["assessed_at"] = str(a["assessed_at"])
    if a["compact"]:
        full = assess_work(_normalise(dict(row)),
                           Context(stats=_stats(), as_of=config.snapshot_date())).to_row()
        for k in ("parts", "validation", "agents"):
            assessment[k] = full[k]
    assessment["agents"] = _described(assessment.get("agents") or [])
    work_row = {k: v for k, v in dict(row).items() if k != "signals"}
    return {"work": _jsonable(work_row), "assessment": assessment}


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
