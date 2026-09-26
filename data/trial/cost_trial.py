r"""Trial 1 - the Cost agent on real works, and a standard outlier model for comparison.

Question: if a real work's amount is inflated, how often is it caught, and how many ordinary
works are flagged along the way?

Method (planted inflation; there are no labelled fraud cases in the export):
  1. Take 1,000 real works whose cost currently reads as typical, not bundles, with a
     same-type same-district cohort of 20+ works (a held-out test set).
  2. Rebuild the peer bands WITHOUT those 1,000 works.
  3. Multiply each test work's amount by 1.5, 2, 3, 5 and 10 and re-run the agent.
  4. False alarms: another 20,000 untouched works run through the same bands.
  5. Comparison: Isolation Forest on
     log(amount) + work type + state, tuned to the SAME false-alarm rate, then scored on the
     same inflated works.

Run:  .venv-trial\Scripts\python.exe data\trial\cost_trial.py
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "apps" / "engine"))
sys.path.insert(0, str(ROOT / "data"))

from build_stats import cohorts  # noqa: E402
from drishti.agents.statistical.agent import assess  # noqa: E402
from drishti.agents.statistical.band import MIN_COHORT  # noqa: E402
from drishti.agents.statistical.cohort import StatsStore  # noqa: E402
from drishti.agents.statistical.text import reads_as_bundle  # noqa: E402
from drishti.agents.contract import not_built  # noqa: E402
from drishti.fusion.fuse import fuse  # noqa: E402

BUILD = ROOT / "data" / "build"
OUT = ROOT / "data" / "trial" / "results"
FACTORS = (1.5, 2.0, 3.0, 5.0, 10.0)
FLAGGED = {"COST_ABOVE_PEERS", "BUNDLED_SANCTION", "UNIT_RATE_ABOVE"}
AS_OF = date(2026, 5, 26)
rng = np.random.default_rng(26)


def clean(rec: dict) -> dict:
    return {k: (None if (isinstance(v, float) and np.isnan(v)) or v is pd.NaT else v)
            for k, v in rec.items()}


def main() -> None:
    w = pd.read_parquet(BUILD / "works.parquet")
    w = w[(w.amount > 0) & w.work_type_code.notna()].copy()
    w["l"] = np.log10(w.amount.astype(float))
    w["bundle"] = w.description.map(reads_as_bundle)

    # current cohorts, to choose works that read as typical today
    full = cohorts(w)
    td = full[(full.level == "type_district") & (full.n >= MIN_COHORT)].set_index(["work_type_code", "key"])
    m = td.reindex(pd.MultiIndex.from_arrays([w.work_type_code, w.district_lgd]))
    w["z_now"] = (w.l.values - m.p50.values) / m.sd.values
    pool = w[m.n.notna().values & ~w.bundle & (w.z_now.abs() < 2)]
    test = pool.sample(n=1000, random_state=26)
    rest = w.drop(test.index)
    control = rest.sample(n=20000, random_state=27)

    # bands WITHOUT the test works
    bands = cohorts(rest)
    stats = StatsStore.from_rows(bands[bands.n >= MIN_COHORT].to_dict("records"),
                                 pd.read_parquet(BUILD / "duration_stats.parquet").to_dict("records"),
                                 pd.read_parquet(BUILD / "unit_rate_models.parquet").to_dict("records"))

    def flagged(df: pd.DataFrame, factor: float) -> np.ndarray:
        out = []
        for rec in df.to_dict("records"):
            r = clean(rec)
            r["amount"] = float(r["amount"]) * factor
            res = assess(r, stats, AS_OF)
            out.append(res.status.value == "ASSESSED" and any(f.code in FLAGGED for f in res.findings))
        return np.array(out)

    ours = {"false_alarm_rate": float(flagged(control, 1.0).mean())}
    for f in FACTORS:
        ours[f"caught_x{f:g}"] = float(flagged(test, f).mean())

    # The stricter question: does the work reach the review queue (Medium or High) on the
    # price finding alone? Other agents are not built yet, so only this one speaks.
    def queued(df: pd.DataFrame, factor: float) -> np.ndarray:
        out = []
        for rec in df.to_dict("records"):
            r = clean(rec)
            r["amount"] = float(r["amount"]) * factor
            res = assess(r, stats, AS_OF)
            others = [not_built(a, "q") for a in ("site_progress", "image_reuse", "duplicate_project")]
            out.append(fuse(others + [res], []).band in ("MEDIUM", "HIGH"))
        return np.array(out)

    queue = {"false_alarm_rate": float(queued(control, 1.0).mean())}
    for f in FACTORS:
        queue[f"caught_x{f:g}"] = float(queued(test, f).mean())

    # ---- Isolation Forest, a standard outlier model, at the same false-alarm rate
    def features(df: pd.DataFrame, factor: float = 1.0) -> pd.DataFrame:
        x = pd.get_dummies(df[["work_type_code", "state_lgd"]].astype(str), dtype=float)
        x["logamt"] = np.log10(df.amount.astype(float) * factor)
        return x

    xtrain = features(rest)
    cols = xtrain.columns
    iforest = IsolationForest(n_estimators=300, random_state=26).fit(xtrain.values)
    ctrl_scores = -iforest.score_samples(features(control).reindex(columns=cols, fill_value=0).values)
    threshold = np.quantile(ctrl_scores, 1 - ours["false_alarm_rate"])
    iforest = {"false_alarm_rate": float((ctrl_scores > threshold).mean())}
    for f in FACTORS:
        s = -iforest.score_samples(features(test, f).reindex(columns=cols, fill_value=0).values)
        iforest[f"caught_x{f:g}"] = float((s > threshold).mean())

    # IF on amount alone (the simplest version)
    if1 = IsolationForest(n_estimators=300, random_state=26).fit(rest[["l"]].values)
    c1 = -if1.score_samples(control[["l"]].values)
    t1 = np.quantile(c1, 1 - ours["false_alarm_rate"])
    iforest_amount = {"false_alarm_rate": float((c1 > t1).mean())}
    for f in FACTORS:
        s = -if1.score_samples(np.log10(test.amount.astype(float).values * f).reshape(-1, 1))
        iforest_amount[f"caught_x{f:g}"] = float((s > t1).mean())

    result = {"test_works": len(test), "control_works": len(control),
              "drishti_cost_agent": ours, "drishti_review_queue": queue,
              "isolation_forest_type_state_amount": iforest,
              "isolation_forest_amount_only": iforest_amount}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "cost_trial.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
