"""Shared helpers for the offline data scripts."""

from __future__ import annotations

import json
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


# Offline engine facts, one parquet per engine (built by the engine's data job), read with
# each work as work["signals"][engine] - locally here, from the work_signals table live.
#   engine -> (file in data/build, the columns that form its data, version column)
SIGNALS = {
    "cost_model": ("cost_expected.parquet", ("q10", "q50", "q90"), "model_version"),
    "delay": ("delay_scores.parquet", ("p_late", "rank_pct", "base_rate", "reasons"),
              "model_version"),
    "dup_split": ("dup_split.parquet", ("pairs", "group"), "model_version"),
}
JSON_COLUMNS = {"pairs", "group"}          # stored as JSON text in the parquet


def signal_rows():
    """(work_id, engine, data dict, version) for every built signal file."""
    for engine, (name, cols, vcol) in SIGNALS.items():
        path = BUILD / name
        if not path.exists():
            continue
        df = pd.read_parquet(path)
        for rec in df.to_dict("records"):
            r = clean(rec)
            data = {}
            for c in cols:
                v = r.get(c)
                if v is None:
                    continue
                if c in JSON_COLUMNS and isinstance(v, str):
                    v = json.loads(v)
                data[c] = v.tolist() if hasattr(v, "tolist") else v
            data = {k: v for k, v in data.items() if v is not None}
            yield r["work_id"], engine, data, str(r.get(vcol) or "")


def works_records(works: pd.DataFrame):
    """Each work as the engine reads it, with its offline engine facts under "signals"."""
    signals: dict[str, dict] = {}
    for work_id, engine, data, _v in signal_rows():
        signals.setdefault(work_id, {})[engine] = data
    for rec in works.to_dict("records"):
        r = clean(rec)
        r["signals"] = signals.get(r["work_id"], {})
        yield r


def load_context() -> Context:
    stats = StatsStore.from_rows(
        pd.read_parquet(BUILD / "cohort_stats.parquet").to_dict("records"),
        pd.read_parquet(BUILD / "duration_stats.parquet").to_dict("records"),
        pd.read_parquet(BUILD / "unit_rate_models.parquet").to_dict("records"),
        pd.read_parquet(BUILD / "timeline_quarters.parquet").to_dict("records"),
        pd.read_parquet(BUILD / "timeline_agencies.parquet").to_dict("records"),
        [e for e, (name, _c, _v) in SIGNALS.items() if (BUILD / name).exists()])
    return Context(stats=stats, as_of=config.snapshot_date())
