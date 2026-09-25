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

from drishti.agents.statistical.band import MIN_COHORT, Cohort
from drishti.agents.statistical.unit_rate import UnitRateModel

BACKOFF = ("type_district", "type_state", "type")


@dataclass
class StatsStore:
    cohorts: dict[tuple[str, str, str], Cohort] = field(default_factory=dict)
    durations: dict[str, dict] = field(default_factory=dict)
    unit_models: dict[str, UnitRateModel] = field(default_factory=dict)

    @classmethod
    def from_rows(cls, cohorts, durations, unit_models) -> StatsStore:
        s = cls()
        for r in cohorts:
            if r["n"] < MIN_COHORT:
                continue
            s.cohorts[(r["level"], r["work_type_code"], r["key"])] = Cohort(
                level=r["level"], n=int(r["n"]), p10=r["p10"], p50=r["p50"], p90=r["p90"],
                sd=r["sd"])
        for r in durations:
            s.durations[r["work_type_code"]] = dict(r)
        for r in unit_models:
            s.unit_models[r["work_type_code"]] = UnitRateModel(**{
                k: r[k] for k in UnitRateModel.__dataclass_fields__})
        return s

    @classmethod
    def load(cls, url: str) -> StatsStore:
        with psycopg.connect(url, prepare_threshold=None, row_factory=dict_row) as con:
            return cls.from_rows(
                con.execute("SELECT * FROM cohort_stats").fetchall(),
                con.execute("SELECT * FROM duration_stats").fetchall(),
                con.execute("SELECT * FROM unit_rate_models").fetchall())

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

    def p98(self, work_type: str | None) -> float | None:
        row = self.durations.get(work_type or "")
        return float(row["p98"]) if row else None
