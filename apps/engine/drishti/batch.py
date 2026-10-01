"""Assess works already in the database and store the results.

Used by data/batch_assess.py for the whole real corpus, by the API to assess
a work on demand, and by tests. Upserts, so running it twice leaves one row
per work.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import replace

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from drishti.agents.dup_split.match import DupIndex
from drishti.pipeline.orchestrator import Assessment, Context, assess_work

WORK_COLUMNS = ("work_id, source, house, term, state_lgd, state_name, district_lgd, "
                "district_name, constituency, mp_name, agency_name, fy, work_type_code, "
                "category, description, amount, recommended_date, completed_date, status, "
                "quantity, quantity_unit, is_outside_constituency")
# Offline engine facts for the work (migration 006, table work_signals), as one JSON object
# keyed by engine: {"cost_model": {...}, "delay": {...}}.
SIGNALS_COLUMNS = "sig.signals AS signals"
SIGNALS_JOIN = ("LEFT JOIN LATERAL (SELECT jsonb_object_agg(s.engine, s.data) AS signals "
                "FROM work_signals s WHERE s.work_id = works.work_id) sig ON true")

# Guideline Compliance's delay rules (R01, R02): real, but common to a third of all works
TIMING_CODES = frozenset({"SANCTION_OVERDUE", "COMPLETION_OVERDUE"})

UPSERT = """
INSERT INTO assessments (work_id, assessed_at, score, band, limited, priority, parts,
                         validation, agents, versions, alerts, headline, compact)
VALUES (%(work_id)s, now(), %(score)s, %(band)s, %(limited)s, %(priority)s, %(parts)s,
        %(validation)s, %(agents)s, %(versions)s, %(alerts)s, %(headline)s, %(compact)s)
ON CONFLICT (work_id) DO UPDATE SET
    assessed_at = now(), score = EXCLUDED.score, band = EXCLUDED.band,
    limited = EXCLUDED.limited, priority = EXCLUDED.priority, parts = EXCLUDED.parts,
    validation = EXCLUDED.validation, agents = EXCLUDED.agents,
    versions = EXCLUDED.versions, alerts = EXCLUDED.alerts, headline = EXCLUDED.headline,
    compact = EXCLUDED.compact
"""


def _normalise(work: dict) -> dict:
    w = dict(work)
    for k in ("amount", "quantity"):
        if w.get(k) is not None:
            w[k] = float(w[k])
    w["signals"] = w.get("signals") or {}
    return w


def row_for(a: Assessment) -> dict:
    row = a.to_row()
    alerts = [r.agent for r in a.agents if r.assessed and r.risk > 0]
    if any(i.risk > 0 for i in a.validation):
        alerts.append("validation")
    top = max((r for r in a.agents if r.assessed and r.risk > 0), key=lambda r: r.risk,
              default=None)
    row["alerts"] = alerts
    # the headline is the score's reason that sets the work apart: a sanction or completion
    # delay is shared by a third of all works, so in the queue list it only leads when
    # nothing else counts (read on the local copy of the site, 30 Sept 2026)
    reasons = a.fused.reasons
    specific = [r for r in reasons if r["code"] not in TIMING_CODES]
    lead = (specific or reasons or [None])[0]
    row["headline"] = lead["text_en"] if lead else (top.headline if top else None)
    # LOW and MEDIUM works keep only their summary; the detail is rebuilt when opened
    # (keeps the free 500 MB database at a fraction of that - measured 489 MB without).
    row["compact"] = a.fused.band in ("LOW", "MEDIUM")
    if row["compact"]:
        row["parts"], row["validation"], row["agents"] = {}, [], []
    for k in ("parts", "validation", "agents", "versions"):
        row[k] = Jsonb(json.loads(json.dumps(row[k], default=str)))
    return row


def district_index(con: psycopg.Connection, district_lgd) -> DupIndex:
    """The Duplicate & Split comparison index for one district (T051): what the API needs to
    compare one work, saved or new, with every other work of its district."""
    rows = con.execute(f"SELECT {WORK_COLUMNS} FROM works WHERE district_lgd = %s",
                       (district_lgd,)).fetchall() if district_lgd else []
    return DupIndex.build(_normalise(dict(r)) for r in rows)


def with_index(ctx: Context, con: psycopg.Connection, work: dict) -> Context:
    """The context with a comparison index covering this work's district."""
    idx = (ctx.data or {}).get("dup_split")
    if idx is not None and idx.covers(work.get("district_lgd")):
        return ctx
    return replace(ctx, data={**(ctx.data or {}),
                              "dup_split": district_index(con, work.get("district_lgd"))})


def assess_one(con: psycopg.Connection, work_id: str, ctx: Context) -> Assessment | None:
    work = con.execute(f"SELECT {WORK_COLUMNS}, {SIGNALS_COLUMNS} FROM works "
                       f"{SIGNALS_JOIN} WHERE work_id = %s", (work_id,)).fetchone()
    if work is None:
        return None
    work = _normalise(dict(work))
    a = assess_work(work, with_index(ctx, con, work))
    con.execute(UPSERT, row_for(a))
    return a


def assess_all(url: str, ctx: Context, work_ids: Iterable[str] | None = None,
               chunk: int = 2000) -> dict[str, int]:
    """Assess every work (or the given ones). Returns counts per band."""
    bands: dict[str, int] = {}
    with psycopg.connect(url, prepare_threshold=None, row_factory=dict_row) as con:
        sql = f"SELECT {WORK_COLUMNS}, {SIGNALS_COLUMNS} FROM works {SIGNALS_JOIN}"
        params: tuple = ()
        if work_ids is not None:
            sql += " WHERE work_id = ANY(%s)"
            params = (list(work_ids),)
        works = [_normalise(dict(w)) for w in con.execute(sql, params).fetchall()]
        if "dup_split" not in (ctx.data or {}):
            # every work of the database, so each is compared with its whole district
            everything = works if work_ids is None else [
                _normalise(dict(w)) for w in con.execute(f"SELECT {WORK_COLUMNS} FROM works")]
            ctx = replace(ctx, data={**(ctx.data or {}), "dup_split": DupIndex.build(everything)})
        batch: list[dict] = []
        for w in works:
            a = assess_work(w, ctx)
            bands[a.fused.band] = bands.get(a.fused.band, 0) + 1
            batch.append(row_for(a))
            if len(batch) >= chunk:
                with con.cursor() as cur:
                    cur.executemany(UPSERT, batch)
                con.commit()
                batch.clear()
        if batch:
            with con.cursor() as cur:
                cur.executemany(UPSERT, batch)
            con.commit()
        con.execute("DELETE FROM dashboard_cache")   # saved dashboard answers are now stale
        con.commit()
    return bands
