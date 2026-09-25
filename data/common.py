"""Shared helpers for the offline data scripts."""

from __future__ import annotations

import math
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
BUILD = Path(__file__).resolve().parent / "build"
sys.path.insert(0, str(ROOT / "apps" / "engine"))

from drishti import config  # noqa: E402
from drishti.agents.statistical.cohort import StatsStore  # noqa: E402
from drishti.pipeline.orchestrator import Context  # noqa: E402


def clean(rec: dict) -> dict:
    """pandas writes a missing string or date as NaN / NaT; the engine expects None.

    Without this a work with no type reached the statistical agent as the
    float NaN, which is truthy, and crashed it (6,658 errors in the first run).
    """
    out = {}
    for k, v in rec.items():
        if v is None or v is pd.NaT or (isinstance(v, float) and math.isnan(v)):
            out[k] = None
        else:
            out[k] = v
    return out


def works_records(works: pd.DataFrame):
    for rec in works.to_dict("records"):
        yield clean(rec)


def load_context() -> Context:
    stats = StatsStore.from_rows(
        pd.read_parquet(BUILD / "cohort_stats.parquet").to_dict("records"),
        pd.read_parquet(BUILD / "duration_stats.parquet").to_dict("records"),
        pd.read_parquet(BUILD / "unit_rate_models.parquet").to_dict("records"))
    return Context(stats=stats, as_of=config.snapshot_date())
