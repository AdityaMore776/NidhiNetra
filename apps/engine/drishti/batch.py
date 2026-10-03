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

from drishti import records
from drishti.agents.delay.backlog import OfficeBacklog
from drishti.agents.dup_split.match import DupIndex
from drishti.agents.office_patterns.index import JUST_UNDER, OfficeIndex, limits
from drishti.agents.paperwork.vendors import VendorIndex
from drishti.agents.photo_evidence.index import PhotoIndex
from drishti.pipeline.orchestrator import Assessment, Context, assess_work

WORK_COLUMNS = ("work_id, source, house, term, state_lgd, state_name, district_lgd, "
                "district_name, constituency, mp_name, agency_name, fy, work_type_code, "
                "category, description, amount, recommended_date, completed_date, status, "
                "quantity, quantity_unit, is_outside_constituency, sanction_date")
# Offline engine facts for the work (migration 006, table work_signals), as one JSON object
# keyed by engine: {"cost_model": {...}, "delay": {...}}.
# ... and the facts read from its attached papers and photos (migration 009, T110), as
# work["evidence"] = {"files": [...]} (data/build_evidence.py, the engines' own readers).
SIGNALS_COLUMNS = "sig.signals AS signals, ev.evidence AS evidence"
SIGNALS_JOIN = ("LEFT JOIN LATERAL (SELECT jsonb_object_agg(s.engine, s.data) AS signals "
                "FROM work_signals s WHERE s.work_id = works.work_id) sig ON true "
                "LEFT JOIN LATERAL (SELECT e.data AS evidence FROM evidence_facts e "
                "WHERE e.work_id = works.work_id) ev ON true")

# Guideline Compliance's delay rules (R01, R02): real, but common to a third of all works
TIMING_CODES = frozenset({"SANCTION_OVERDUE", "COMPLETION_OVERDUE"})

UPSERT = """
INSERT INTO assessments (work_id, assessed_at, score, band, limited, priority, parts,
                         validation, agents, versions, alerts, headline, compact, case_id,
                         case_size)
VALUES (%(work_id)s, now(), %(score)s, %(band)s, %(limited)s, %(priority)s, %(parts)s,
        %(validation)s, %(agents)s, %(versions)s, %(alerts)s, %(headline)s, %(compact)s,
        %(case_id)s, %(case_size)s)
ON CONFLICT (work_id) DO UPDATE SET
    assessed_at = now(), score = EXCLUDED.score, band = EXCLUDED.band,
    limited = EXCLUDED.limited, priority = EXCLUDED.priority, parts = EXCLUDED.parts,
    validation = EXCLUDED.validation, agents = EXCLUDED.agents,
    versions = EXCLUDED.versions, alerts = EXCLUDED.alerts, headline = EXCLUDED.headline,
    compact = EXCLUDED.compact, case_id = EXCLUDED.case_id, case_size = EXCLUDED.case_size
"""


def _normalise(work: dict) -> dict:
    w = dict(records.work(work))          # Decimal amounts -> numbers, and every other column
    w["signals"] = w.get("signals") or {}
    return w


def row_for(a: Assessment) -> dict:
    row = a.to_row()
    alerts = [r.agent for r in a.agents if r.assessed and r.risk > 0]
    top = max((r for r in a.agents if r.assessed and r.risk > 0), key=lambda r: r.risk,
              default=None)
    row["alerts"] = alerts
    # one case per Duplicate & Split group (migration 012): the queue shows the group once
    row["case_id"], row["case_size"] = case_of(a)
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


def case_of(a: Assessment) -> tuple[str | None, int | None]:
    """The Duplicate & Split group a work belongs to, as (case id, works in it)."""
    for r in a.agents:
        if r.agent == "dup_split" and r.assessed:
            for f in r.findings:
                gid = (f.evidence or {}).get("group_id")
                if gid:
                    return str(gid), int((f.evidence or {}).get("size") or 0) or None
    return None, None


def indexes(works: list[dict]) -> dict:
    """The cross-work views engines need, from the same rows: the Duplicate & Split index and
    the vendors holding the certified works (Paperwork, T110). Every record is checked first
    (records.work): one malformed row used to stop the whole build."""
    works = [records.work(w) for w in works]
    return {"dup_split": DupIndex.build(works), "vendors": VendorIndex.build(works),
            "photos": PhotoIndex.build(works), "backlog": OfficeBacklog.build(works),
            "offices": OfficeIndex.build(works)}


_NATIONAL: dict[str, list[int]] = {}


def office_national(con: psycopg.Connection) -> list[int]:
    """The whole database's office counts (OfficeIndex.national), once per process: the API
    builds the office index from one district, but judges it against the scheme."""
    if "counts" not in _NATIONAL:
        lo = [(JUST_UNDER * lim, lim) for lim in limits()]
        under = " OR ".join("(amount >= %s AND amount < %s)" for _ in lo)
        row = con.execute(f"SELECT count(*) FILTER (WHERE amount > 0) AS priced, "
                          f"count(*) FILTER (WHERE {under}) AS under FROM works",
                          [x for pair in lo for x in pair]).fetchone()
        built = OfficeIndex.build(dict(r) for r in con.execute(
            "SELECT work_type_code, description, status, sanction_date, completed_date "
            "FROM works WHERE status = 'COMPLETED' AND sanction_date IS NOT NULL "
            "AND completed_date IS NOT NULL").fetchall()).national
        _NATIONAL["counts"] = [int(row["priced"]), int(row["under"]), built[2], built[3]]
    return _NATIONAL["counts"]


def with_index(ctx: Context, con: psycopg.Connection, work: dict) -> Context:
    """The context with indexes covering this work's district."""
    idx = (ctx.data or {}).get("dup_split")
    if idx is not None and idx.covers(work.get("district_lgd")):
        return ctx
    d = work.get("district_lgd")
    rows = con.execute(f"SELECT {WORK_COLUMNS}, {SIGNALS_COLUMNS} FROM works {SIGNALS_JOIN} "
                       "WHERE works.district_lgd = %s", (d,)).fetchall() if d else []
    data = indexes([_normalise(dict(r)) for r in rows])
    data["offices"].national = office_national(con)
    # a photo can be reused in another district: every work's evidence, not the district's
    data["photos"] = PhotoIndex.build(
        {"work_id": r["work_id"], "evidence": r["data"]}
        for r in con.execute("SELECT work_id, data FROM evidence_facts").fetchall())
    return replace(ctx, data={**(ctx.data or {}), **data})


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
                _normalise(dict(w)) for w in con.execute(
                    f"SELECT {WORK_COLUMNS}, {SIGNALS_COLUMNS} FROM works {SIGNALS_JOIN}")]
            ctx = replace(ctx, data={**(ctx.data or {}), **indexes(everything)})
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


QUEUE_BANDS = ("CRITICAL", "HIGH")


def sync_alerts(url: str) -> tuple[int, int]:
    """Open one alert per work now in the review queue, and close the rest (T060).

    An alert is only a request to look, so it carries no score of its own and is
    derived entirely from the assessment just written. One open alert per work, so
    re-running the batch never lengthens an officer's list; an alert an officer
    has already worked on keeps its state and its note.
    """
    with psycopg.connect(url, prepare_threshold=None) as con:
        opened = con.execute(
            "INSERT INTO alerts (work_id, code, engine) "
            "SELECT work_id, coalesce(parts->'reasons'->0->>'code', 'IN_REVIEW'), "
            "parts->'reasons'->0->>'source' FROM assessments "
            "WHERE band = ANY(%s) AND parts IS NOT NULL "
            "ON CONFLICT (work_id) WHERE state <> 'RESOLVED' DO NOTHING RETURNING alert_id",
            (list(QUEUE_BANDS),)).rowcount
        closed = con.execute(
            "UPDATE alerts SET state = 'RESOLVED', closed_at = now(), updated_at = now(), "
            "note = coalesce(note, 'Left the review queue on the latest assessment') "
            "WHERE state <> 'RESOLVED' AND work_id NOT IN "
            "(SELECT work_id FROM assessments WHERE band = ANY(%s)) RETURNING alert_id",
            (list(QUEUE_BANDS),)).rowcount
        con.commit()
    return opened, closed
