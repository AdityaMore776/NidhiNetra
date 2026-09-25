"""The engine's HTTP API, all under /api/v1.

Every route except the health checks needs a signed-in user, and every query
is scoped to that user's district when their role has one.
"""

from __future__ import annotations

from datetime import date
from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException, Query

from drishti import config
from drishti.agents.statistical.cohort import StatsStore
from drishti.auth import Principal, current_user
from drishti.batch import WORK_COLUMNS, _normalise, assess_one
from drishti.db import connect
from drishti.pipeline.orchestrator import AGENT_ORDER, QUESTIONS, Context, assess_work

router = APIRouter(prefix="/api/v1")

BUILT = {"statistical"}
AGENT_NAMES = {"site_progress": "Site Progress", "image_reuse": "Image Reuse",
               "duplicate_project": "Duplicate Project", "statistical": "Statistical"}
PAGE = 25


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
        if isinstance(v, date):
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


@router.get("/dashboard/summary")
def summary(user: Principal = Depends(current_user)) -> dict:
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
    alert_n = {r["agent"]: r["n"] for r in alerts}
    return {
        "works": totals["works"], "amount": float(totals["amount"]),
        "bands": {b: 0 for b in ("HIGH", "MEDIUM", "LOW")} | {r["band"]: r["n"] for r in bands},
        "agents": [{"id": a, "name": AGENT_NAMES[a], "question": QUESTIONS[a],
                    "built": a in BUILT, "alerts": alert_n.get(a, 0)} for a in AGENT_ORDER],
        "validation_alerts": alert_n.get("validation", 0),
        "snapshot_date": config.snapshot_date().isoformat(),
    }


@router.get("/dashboard/districts")
def districts(user: Principal = Depends(current_user)) -> list[dict]:
    where, params = _scope(user)
    with connect() as con:
        rows = con.execute(
            f"SELECT w.district_lgd, max(w.district_name) AS name, max(w.state_name) AS state, "
            f"count(*) AS works, coalesce(sum(w.amount), 0) AS amount, "
            f"count(*) FILTER (WHERE a.band IN ('HIGH', 'MEDIUM')) AS review "
            f"FROM works w LEFT JOIN assessments a USING (work_id) "
            f"WHERE {where} AND w.district_lgd IS NOT NULL GROUP BY w.district_lgd", params
        ).fetchall()
    return [{**_jsonable(r), "share": (r["review"] / r["works"]) if r["works"] else 0.0}
            for r in rows]


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
        clauses.append("a.band IN ('HIGH', 'MEDIUM')")
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
    where, params = _scope(user)
    with connect() as con:
        row = con.execute(f"SELECT {WORK_COLUMNS} FROM works w WHERE w.work_id = %s "
                          f"AND {where}", (work_id, *params)).fetchone()
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
    return {"work": _jsonable(dict(row)), "assessment": assessment}
