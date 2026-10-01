"""Peer groups, with back-off from district to state to the whole scheme.

The whole statistics table is ~2,400 rows, so it is read once per process
and every lookup after that is a dictionary hit. Cohorts below 20 works are
never used: below that the honest answer is that the question cannot be
asked (the same floor the old build measured, AD-106).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import psycopg
from psycopg.rows import dict_row

from drishti.agents.outlier.model import OutlierStats
from drishti.agents.statistical.band import MIN_COHORT, Cohort
from drishti.agents.statistical.price_model import PriceModel
from drishti.agents.statistical.unit_rate import UnitRateModel
from drishti.validation.timeline import TimelineRates

# Stored statistics are rounded when loaded so every copy of the database gives the same
# verdict. The hosted Postgres returns doubles with 15 significant digits, a local one with
# 17 (p90 5.19033169817029 vs 5.190331698170292); a work at exactly twice its peers' top
# (Rs 3,10,000 against Rs 1,55,000) then flipped between "typical" and "above the range".
# Found comparing the hosted and local runs, 30 Sept 2026: 241 works differed.
PRECISION = 9


def _fixed(v):
    return round(v, PRECISION) if isinstance(v, float) else v

BACKOFF = ("type_district", "type_state", "type")


@dataclass
class StatsStore:
    cohorts: dict[tuple[str, str, str], Cohort] = field(default_factory=dict)
    durations: dict[str, dict] = field(default_factory=dict)
    unit_models: dict[str, UnitRateModel] = field(default_factory=dict)
    # How common impossible dates were per quarter and per office (validation/timeline.py).
    timeline: TimelineRates | None = None
    # Offline engine signals that have been computed (work_signals.engine): lets an engine
    # tell "compared, nothing found" from "never compared".
    signals_built: frozenset[str] = frozenset()
    # The cost engine's word-price model (agents/statistical/price_model.py, T051).
    price_model: PriceModel | None = None
    # The Odd Overall engine's statistics and forest (agents/outlier/model.py, #63).
    outlier: OutlierStats | None = None

    @classmethod
    def from_rows(cls, cohorts, durations, unit_models, quarters=(), agencies=(),
                  signals_built=(), models=()) -> StatsStore:
        s = cls(signals_built=frozenset(signals_built))
        for m in models:
            if m["name"] == "price_model":
                s.price_model = PriceModel.from_json(m["data"])
            elif m["name"] == "outlier_stats":
                s.outlier = OutlierStats.from_json(m["data"])
        quarters, agencies = list(quarters), list(agencies)
        if quarters:
            s.timeline = TimelineRates.from_counts(
                {r["quarter"]: (int(r["n"]), int(r["bad"])) for r in quarters},
                {r["agency_name"]: (int(r["completed"]), int(r["bad"])) for r in agencies})
        for r in cohorts:
            if r["n"] < MIN_COHORT:
                continue
            s.cohorts[(r["level"], r["work_type_code"], r["key"])] = Cohort(
                level=r["level"], n=int(r["n"]), p10=_fixed(r["p10"]), p50=_fixed(r["p50"]),
                p90=_fixed(r["p90"]), sd=_fixed(r["sd"]))
        for r in durations:
            s.durations[r["work_type_code"]] = {k: _fixed(v) for k, v in dict(r).items()}
        for r in unit_models:
            s.unit_models[r["work_type_code"]] = UnitRateModel(**{
                k: _fixed(r[k]) for k in UnitRateModel.__dataclass_fields__})
        return s

    @classmethod
    def load(cls, url: str) -> StatsStore:
        with psycopg.connect(url, prepare_threshold=None, row_factory=dict_row) as con:
            return cls.from_rows(
                con.execute("SELECT * FROM cohort_stats").fetchall(),
                con.execute("SELECT * FROM duration_stats").fetchall(),
                con.execute("SELECT * FROM unit_rate_models").fetchall(),
                con.execute("SELECT * FROM timeline_quarters").fetchall(),
                con.execute("SELECT * FROM timeline_agencies").fetchall(),
                [r["engine"] for r in con.execute(
                    "SELECT DISTINCT engine FROM work_signals").fetchall()],
                con.execute("SELECT name, data FROM engine_models").fetchall())

    def cohort(self, work_type: str | None, district: str | None,
               state: str | None) -> Cohort | None:
        if not work_type:
            return None
        keys = {"type_district": district or "", "type_state": state or "", "type": ""}
        for level in BACKOFF:
            if level != "type" and not keys[level]:
                continue
            c = self.cohorts.get((level, work_type, keys[level]))
            if c is not None:
                return c
        return None

    def peer_type(self, work_type: str, scope: str) -> str:
        """The type's scope-split peer group ("LIBRARY|GOODS") when the stats have one."""
        split = f"{work_type}|{scope}"
        if ("type", split, "") in self.cohorts:
            return split
        return work_type

    def chain(self, work_type: str | None, district: str | None,
              state: str | None) -> list[Cohort]:
        """Every usable cohort from narrowest to broadest (district, state, scheme)."""
        if not work_type:
            return []
        keys = {"type_district": district or "", "type_state": state or "", "type": ""}
        out = []
        for level in BACKOFF:
            if level != "type" and not keys[level]:
                continue
            c = self.cohorts.get((level, work_type, keys[level]))
            if c is not None:
                out.append(c)
        return out

    def p98(self, work_type: str | None) -> float | None:
        row = self.durations.get(work_type or "")
        return float(row["p98"]) if row else None
