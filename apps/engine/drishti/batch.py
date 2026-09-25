"""Assess works already in the database and store the results.

Used by data/batch_assess.py for the whole real corpus, by the API to assess
a work on demand, and by tests. Upserts, so running it twice leaves one row
per work.
"""

from __future__ import annotations

import json
from typing import Iterable

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from drishti.pipeline.orchestrator import Assessment, Context, assess_work

WORK_COLUMNS = ("work_id, source, house, term, state_lgd, state_name, district_lgd, "
                "district_name, constituency, mp_name, agency_name, fy, work_type_code, "
                "category, description, amount, recommended_date, completed_date, status, "
                "quantity, quantity_unit, is_outside_constituency")

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
    return w


def row_for(a: Assessment) -> dict:
    row = a.to_row()
    alerts = [r.agent for r in a.agents if r.assessed and r.risk > 0]
    if any(i.risk > 0 for i in a.validation):
        alerts.append("validation")
    top = max((r for r in a.agents if r.assessed and r.risk > 0), key=lambda r: r.risk,
              default=None)
    row["alerts"] = alerts
    row["headline"] = top.headline if top else None
    # LOW works keep only their summary; the detail is rebuilt when opened
    # (keeps the free 500 MB database at a fraction of that - measured 489 MB without).
    row["compact"] = a.fused.band == "LOW"
    if row["compact"]:
        row["parts"], row["validation"], row["agents"] = {}, [], []
    for k in ("parts", "validation", "agents", "versions"):
        row[k] = Jsonb(json.loads(json.dumps(row[k], default=str)))
    return row


def assess_one(con: psycopg.Connection, work_id: str, ctx: Context) -> Assessment | None:
    work = con.execute(f"SELECT {WORK_COLUMNS} FROM works WHERE work_id = %s",
                       (work_id,)).fetchone()
    if work is None:
        return None
    a = assess_work(_normalise(dict(work)), ctx)
    con.execute(UPSERT, row_for(a))
    return a


def assess_all(url: str, ctx: Context, work_ids: Iterable[str] | None = None,
               chunk: int = 2000) -> dict[str, int]:
    """Assess every work (or the given ones). Returns counts per band."""
    bands: dict[str, int] = {}
    with psycopg.connect(url, prepare_threshold=None, row_factory=dict_row) as con:
        sql = f"SELECT {WORK_COLUMNS} FROM works"
        params: tuple = ()
        if work_ids is not None:
            sql += " WHERE work_id = ANY(%s)"
            params = (list(work_ids),)
        works = con.execute(sql, params).fetchall()
        batch: list[dict] = []
        for w in works:
            a = assess_work(_normalise(dict(w)), ctx)
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
    return bands
