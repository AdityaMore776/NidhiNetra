"""The engine's HTTP API, all under /api/v1.

Every route except the health checks needs a signed-in user, and every query
is scoped to that user's district when their role has one.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import date
from functools import lru_cache

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from psycopg.types.json import Jsonb
from pydantic import BaseModel, Field

from drishti import config, reference
from drishti import demo as work_demo
from drishti.agents import registry
from drishti.agents.cost_estimate import rates as cost_rates
from drishti.agents.office_patterns.index import OfficeIndex
from drishti.agents.statistical.cohort import StatsStore
from drishti.auth import Principal, current_user, viewer
from drishti.batch import (
    SIGNALS_COLUMNS,
    SIGNALS_JOIN,
    WORK_COLUMNS,
    _normalise,
    assess_one,
    office_national,
    with_evidence,
    with_index,
)
from drishti.cost_form import catalog as cost_form_catalog
from drishti.cost_form import pswif
from drishti.cost_form.validate import validate as validate_cost_form
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
def me(user: Principal = Depends(viewer)) -> dict:
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
def summary(user: Principal = Depends(viewer)) -> dict:
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


@router.get("/dashboard/districts")
def districts(user: Principal = Depends(viewer)) -> list[dict]:
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
def offices(user: Principal = Depends(viewer)) -> list[dict]:
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
def office_habits(user: Principal = Depends(viewer)) -> list[dict]:
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
    cols = ("w.work_id, w.source, w.district_lgd, w.district_name, w.state_name, "
            "w.work_type_code, w.description, w.amount, w.status, w.recommended_date, "
            "a.band, a.score, a.priority, a.limited, a.alerts, a.headline, a.case_id, "
            "a.case_size")
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
            "items": [_jsonable(r) for r in rows]}


@router.get("/works")
def works(q: str | None = None, district: str | None = None,
          type: str | None = Query(default=None), band: str | None = None,
          page: int = Query(default=1, ge=1), user: Principal = Depends(viewer)) -> dict:
    return _list(user, q=q, district=district, wtype=type, band=band, review_only=False,
                 page=page)


@router.get("/queue")
def queue(district: str | None = None, band: str | None = None,
          page: int = Query(default=1, ge=1), user: Principal = Depends(viewer)) -> dict:
    return _list(user, q=None, district=district, wtype=None, band=band, review_only=True,
                 page=page)


@router.get("/works/{work_id:path}")
def work(work_id: str, user: Principal = Depends(viewer)) -> dict:
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
            w = with_evidence(con, [_normalise(dict(row))])[0]
            ctx = with_index(Context(stats=_stats(), as_of=config.snapshot_date()), con, w)
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
    return {"work": _jsonable(work_row), "assessment": assessment}


def _described(agents: list[dict]) -> list[dict]:
    """Stored results under today's engine ids, each with its display name and question."""
    specs = registry.by_id()
    out = []
    for r in agents:
        aid = registry.canonical_id(r.get("agent", ""))
        spec = specs.get(aid)
        name, question = ((spec.name, spec.question) if spec
                          else registry.RETIRED.get(aid, (aid, "")))
        out.append({**r, "agent": aid, "name": name, "question": question})
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
def presanction(rec: Recommendation, user: Principal = Depends(viewer)) -> dict:
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
def explain(ex: Example, user: Principal = Depends(viewer)) -> dict:
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


WORK_FORM_MAX = 400_000            # a filled form is a few KB; refuse anything absurd


@router.post("/work-form/check")
def work_form_check(form: dict = Body(...), demo: bool = Query(False),
                    user: Principal = Depends(viewer)) -> dict:
    """The website's work intelligence form (PSWIF v1.0, T134), as an agency filled it, through
    the four agents: what the form still lacks for them, and every step of their verdict,
    checked against the real works of the form's district. Nothing is stored.

    `demo=true` (the form page's demonstration) also compares it with the example data of
    drishti/demo.py, placed in the form's district, and gives an example filing what its record
    shows after sanction."""
    if len(json.dumps(form, default=str)) > WORK_FORM_MAX:
        raise HTTPException(413, "this form is too large")
    district, state = (str(form.get(k) or "").strip() for k in ("district", "state"))
    if not district:
        raise HTTPException(422, "the form names no district (section C)")
    as_of = config.snapshot_date()
    if demo:
        # the example filings are written for their own day (T164): judged on an earlier
        # snapshot's, their later dates read as "in the future" and their site videos as not
        # filmed yet. Never earlier than the snapshot
        as_of = max(as_of, work_demo.as_of() or as_of)
    with connect() as con:
        rows = con.execute("SELECT district_lgd, name, state_lgd, state_name FROM districts "
                           "WHERE lower(name) = lower(%s)", (district,)).fetchall()
        if state and len(rows) > 1:
            rows = [r for r in rows if r["state_name"].lower() == state.lower()] or rows
        if not rows:
            raise HTTPException(404, f"no district named {district!r}")
        d = rows[0]
        scope = user.scope_district()
        if scope is not None and d["district_lgd"] != scope:
            raise HTTPException(404, "no such district in your area")
        work = pswif.to_work(form, district_lgd=d["district_lgd"], today=as_of,
                             state_lgd=d["state_lgd"], state_name=d["state_name"],
                             district_name=d["name"])
        extra = None
        if demo:
            work.update(work_demo.later(work["work_id"]))
            extra = [*work_demo.records(work), work]
        ctx = with_index(Context(stats=_stats(), as_of=as_of), con, work, extra=extra)
    checked = validate_cost_form(work["cost_form"], today=as_of)
    confirmed = set(work["cost_form"].get("confirmed") or [])
    return {
        "district": {"district_lgd": d["district_lgd"], "name": d["name"],
                     "state_name": d["state_name"]},
        "demo": demo,
        "form": {"ready": checked["ready"], "work_type": work["work_type_code"],
                 "grand_total": checked["computed"]["grand_total"],
                 "issues": [i for i in checked["issues"]
                            if i["level"] == "fix" or i["key"] not in confirmed]},
        "trace": explain_work(work, ctx),
    }


@router.get("/cost/data-gaps")
def cost_data_gaps(district: str = Query(..., max_length=64),
                   user: Principal = Depends(viewer)) -> dict:
    """Which prices the Cost check can judge in this district, and from where; for the rest, why
    not and what would close the gap (T135). Read live from the submitted forms: nothing
    stored, and a gap closes by itself as agencies file forms."""
    scope = user.scope_district()
    if scope is not None and district != scope:
        raise HTTPException(404, "no such district in your area")
    as_of = config.snapshot_date()
    with connect() as con:
        d = con.execute("SELECT district_lgd, name, state_lgd, state_name FROM districts "
                        "WHERE district_lgd = %s", (district,)).fetchone()
        if not d:
            raise HTTPException(404, "no such district")
        ctx = with_index(Context(stats=_stats(), as_of=as_of), con,
                         {"work_id": "", "district_lgd": d["district_lgd"],
                          "state_lgd": d["state_lgd"]})
    idx = (ctx.data or {}).get("rates")
    state = cost_rates._state({"state_lgd": d["state_lgd"], "state_name": d["state_name"]})
    rows = cost_rates.coverage(idx, d["district_lgd"], state, as_of,
                               cost_rates.load_sor(d["state_name"]))
    return {"district": {"district_lgd": d["district_lgd"], "name": d["name"],
                         "state_name": d["state_name"]},
            "as_of": as_of.isoformat(), "materials": rows,
            "priced": sum(1 for r in rows if r["source"]),
            "gaps": sum(1 for r in rows if not r["source"])}


@router.get("/presanction/options")
def presanction_options(user: Principal = Depends(viewer)) -> dict:
    """What the pre-sanction form offers: the user's districts and the work types."""
    where, params = _scope(user, alias="d")
    with connect() as con:
        rows = con.execute(f"SELECT d.district_lgd, d.name, d.state_name FROM districts d "
                           f"WHERE {where} ORDER BY d.state_name, d.name", params).fetchall()
    types = sorted(({"code": c, "name": s["name"]} for c, s in reference.work_types().items()),
                   key=lambda t: t["name"])
    return {"districts": [dict(r) for r in rows], "work_types": types,
            "as_of": config.snapshot_date().isoformat()}


@router.get("/cost-form/catalog")
def cost_form_fields(work_type: str | None = Query(default=None, max_length=40),
                     user: Principal = Depends(viewer)) -> dict:
    """Everything the cost estimate form shows for one work type (T093): every section, the
    size fields of its family, the expense line groups, the materials it suggests and the
    units. One source (reference/cost_form.yaml) for the form and its checks."""
    if work_type and not cost_form_catalog.family_of(work_type):
        raise HTTPException(404, "no such work type")
    return cost_form_catalog.for_type(work_type)


@router.post("/cost-form/validate")
def cost_form_check(form: dict | list | str | int | float | None = Body(default=None),
                    user: Principal = Depends(viewer)) -> dict:
    """The checks made while the cost estimate form is filled (T093): what must be fixed, what
    looks like a typing mistake to confirm, and the totals worked out from the lines. Never a
    flag, never a reference price; any body gets an answer, never an error."""
    return validate_cost_form(form if isinstance(form, dict) else {})


# ---- saved cost estimate forms (T099: the storage half of T094; migration 013) ---------------

class CostFormSave(BaseModel):
    """The implementing agency's cost estimate form for one work: a draft, or submitted."""

    work_id: str = Field(min_length=1, max_length=120)
    form: dict
    submit: bool = False


def _forms_ready(con) -> None:
    if not con.execute("SELECT to_regclass('cost_forms') IS NOT NULL AS ok").fetchone()["ok"]:
        raise HTTPException(503, "cost estimate forms are not set up on this database yet "
                                 "(migration 013_cost_forms.sql)")


def _work_in_area(con, work_id: str, user: Principal) -> dict:
    where, params = _scope(user, alias="works")
    row = con.execute(f"SELECT {WORK_COLUMNS}, {SIGNALS_COLUMNS} FROM works {SIGNALS_JOIN} "
                      f"WHERE works.work_id = %s AND {where}", (work_id, *params)).fetchone()
    if row is None:
        raise HTTPException(404, "no such work in your area")
    return _normalise(dict(row))


def _recommendation(w: dict) -> dict:
    """The form's read-only first section, from the work's own eSAKSHI record: the MP's amount
    is never taken from what the form sends (the Cost check compares the estimate with it)."""
    d = w.get("recommended_date")
    return {"work_id": w["work_id"], "mp_amount": w.get("amount"),
            "recommended_type": w.get("work_type_code"),
            "recommended_description": w.get("description"),
            "recommended_date": d.isoformat() if isinstance(d, date) else None}


def _earlier_candidates(con, w: dict) -> list[dict]:
    """The sanctioned works the agency must answer about (T100): at this map pin, or in the
    same words. Descriptions pass through the site's masker."""
    ctx = with_index(Context(stats=_stats(), as_of=config.snapshot_date()), con, w)
    idx = (ctx.data or {}).get("dup_split")
    out = []
    for x in idx.candidates(w) if idx is not None else []:
        out.append({"work_id": x.work_id, "description": pii.mask(x.description)[:300],
                    "amount": x.amount, "status": x.status,
                    "sanction_date": x.sanction.isoformat() if x.sanction else None,
                    "completed_date": x.done.isoformat() if x.done else None})
    return out


@router.get("/cost-forms/{work_id:path}")
def cost_form_read(work_id: str, user: Principal = Depends(current_user)) -> dict:
    """The saved form of one work (or none), and the earlier sanctioned works it must answer
    about. A district officer reaches only their district's works."""
    with connect() as con:
        _forms_ready(con)
        w = _work_in_area(con, work_id, user)
        row = con.execute("SELECT status, form, ready, saved_at, submitted_at FROM cost_forms "
                          "WHERE work_id = %s", (work_id,)).fetchone()
        if row is not None:
            w["cost_form"] = row["form"]
        candidates = _earlier_candidates(con, w)
    return {"work_id": work_id, "status": row["status"] if row else None,
            "form": row["form"] if row else None, "ready": bool(row and row["ready"]),
            "saved_at": str(row["saved_at"]) if row else None,
            "submitted_at": str(row["submitted_at"]) if row and row["submitted_at"] else None,
            "recommendation": _recommendation(w), "earlier_candidates": candidates}


@router.post("/cost-forms")
def cost_form_save(body: CostFormSave, user: Principal = Depends(current_user)) -> dict:
    """Save a draft, or submit a form whose checks all pass (else 422 with the issues). A
    submitted form is read-only (409), and submitting re-assesses the work at once, so the Cost
    and Duplicate checks answer from it."""
    with connect() as con:
        _forms_ready(con)
        w = _work_in_area(con, body.work_id, user)
        old = con.execute("SELECT status FROM cost_forms WHERE work_id = %s",
                          (body.work_id,)).fetchone()
        if old is not None and old["status"] == "submitted":
            raise HTTPException(409, "this work's cost estimate form is already submitted")
        form = {**body.form, "recommendation": _recommendation(w)}
        candidates = _earlier_candidates(con, {**w, "cost_form": form})
        checked = validate_cost_form(form, earlier=[c["work_id"] for c in candidates])
        if body.submit and not checked["ready"]:
            raise HTTPException(422, {"message": "the form has fields to fix or confirm",
                                      "issues": checked["issues"]})
        status = "submitted" if body.submit else "draft"
        con.execute(
            "INSERT INTO cost_forms (work_id, status, form, ready, saved_by, saved_at, "
            "submitted_at) VALUES (%s, %s, %s, %s, %s, now(), "
            "CASE WHEN %s THEN now() END) ON CONFLICT (work_id) DO UPDATE SET "
            "status = EXCLUDED.status, form = EXCLUDED.form, ready = EXCLUDED.ready, "
            "saved_by = EXCLUDED.saved_by, saved_at = now(), "
            "submitted_at = EXCLUDED.submitted_at",
            (body.work_id, status, Jsonb(form), checked["ready"], user.user_id, body.submit))
        con.commit()
        if body.submit:
            assess_one(con, body.work_id, Context(stats=_stats(), as_of=config.snapshot_date()))
            con.commit()
    return {"work_id": body.work_id, "status": status, "ready": checked["ready"],
            "issues": checked["issues"], "computed": checked["computed"],
            "earlier_candidates": candidates, "assessed": body.submit}
