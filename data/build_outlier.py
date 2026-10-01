r"""Odd Overall (#63): robust z vs Isolation Forest on planted oddities, then the stored statistics.

The blueprint's outlier slot (weight 0.10) asks whether a record is unusual taken as a whole.
Both methods see the same three fields within the work type (agents/outlier/model.py): amount,
completion speed, description length.

  robust z     odd score = the second-largest |z| (two fields unusual at once), computable
               for ANY work from stored per-type percentiles (T051's rule)
  IsolationF.  sklearn IsolationForest on the same per-type z values (offline only)

PLANTED TEST. 1,000 ordinary completed works (every field within |z| < 1.5) are made odd in two
fields at once, three ways: amount x5 + completed 2 days after recommendation; amount x5 +
description cut to its first word; completed in 2 days + description cut. Each method's
threshold is its own 98.5th percentile on all real works, so 1.5% of real works are flagged;
false alarms are measured on 20,000 untouched works. The method that catches more is kept.

Writes data/build/outlier_model.json (-> engine_models "outlier_stats"),
results/outlier_trial.json and results/outlier_top_sample.csv (the 30 oddest real works, for
reading by eye). Run: .venv-trial\Scripts\python.exe data\build_outlier.py
"""

from __future__ import annotations

import json
import sys
from datetime import timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "engine"))
sys.path.insert(0, str(ROOT / "data"))
from common import clean  # noqa: E402
from drishti.agents.outlier.model import FIELDS, OutlierStats, features, odd_score  # noqa: E402

BUILD = ROOT / "data" / "build"
OUT = ROOT / "data" / "trial" / "results"
VERSION = "outlier-1"
MIN_TYPE = 20
FLAG_SHARE = 0.015
STRONG_SHARE = 0.001


def quantiles(recs: list[dict]) -> dict:
    rows = [{"t": r.get("work_type_code") or "NA", **features(r)} for r in recs]
    df = pd.DataFrame(rows)
    out: dict = {"*": {}}
    for f in FIELDS:
        col = df[f].dropna()
        out["*"][f] = [float(col.quantile(q)) for q in (0.1, 0.5, 0.9)]
    for t, g in df.groupby("t"):
        out[str(t)] = {f: [float(g[f].quantile(q)) for q in (0.1, 0.5, 0.9)]
                       for f in FIELDS if g[f].notna().sum() >= MIN_TYPE}
    return out


def zmatrix(stats: OutlierStats, recs: list[dict]) -> np.ndarray:
    """Per-type z of each field, 0 where a field is missing (for the Isolation Forest)."""
    z = np.zeros((len(recs), len(FIELDS)))
    for i, r in enumerate(recs):
        zs = stats.zscores(r)
        for j, f in enumerate(FIELDS):
            z[i, j] = zs.get(f, 0.0)
    return z


def plant(r: dict, kind: str) -> dict:
    p = dict(r)
    if "amount" in kind:
        p["amount"] = float(p["amount"]) * 5
    if "fast" in kind:
        p["completed_date"] = p["recommended_date"] + timedelta(days=2)
    if "short" in kind:
        p["description"] = (p["description"] or "").split()[0] if p["description"] else "x"
    return p


def main() -> None:
    w = pd.read_parquet(BUILD / "works.parquet")
    recs = [clean(r) for r in w.to_dict("records")]
    stats = OutlierStats(version=VERSION, quantiles={
        t: {f: tuple(v) for f, v in fs.items()} for t, fs in quantiles(recs).items()})
    s_all = np.array([odd_score(stats.zscores(r)) for r in recs])
    t_z = float(np.quantile(s_all, 1 - FLAG_SHARE))
    stats.threshold = t_z

    zall = zmatrix(stats, recs)
    forest = IsolationForest(n_estimators=100, random_state=26).fit(zall)
    s_if_all = -forest.score_samples(zall)
    t_if = float(np.quantile(s_if_all, 1 - FLAG_SHARE))

    rng = np.random.default_rng(63)
    ok = [i for i, r in enumerate(recs) if r.get("status") == "COMPLETED"
          and len(stats.zscores(r)) == 3 and max(abs(v) for v in stats.zscores(r).values()) < 1.5]
    pool = rng.choice(ok, 1000, replace=False)
    rest = np.setdiff1d(np.arange(len(recs)), pool)
    control = rng.choice(rest, 20000, replace=False)
    fa_z = float((s_all[control] >= t_z).mean())
    fa_if = float((s_if_all[control] >= t_if).mean())
    planted = {}
    for kind in ("amount+fast", "amount+short", "fast+short"):
        ps = [plant(recs[i], kind) for i in pool]
        sz = np.array([odd_score(stats.zscores(p)) for p in ps])
        sif = -forest.score_samples(zmatrix(stats, ps))
        planted[kind] = {"robust_z": round(float((sz >= t_z).mean()), 3),
                         "isolation_forest": round(float((sif >= t_if).mean()), 3)}
    # single-field oddities must NOT be caught (the cost engine already covers price)
    single = [plant(recs[i], "amount") for i in pool]
    single_z = float((np.array([odd_score(stats.zscores(p)) for p in single]) >= t_z).mean())
    single_if = float((-forest.score_samples(zmatrix(stats, single)) >= t_if).mean())

    # the winner is stored as numbers the engine scores in plain Python (model.Forest)
    trees = []
    for est, cols in zip(forest.estimators_, forest.estimators_features_, strict=True):
        t = est.tree_
        trees.append({"feature": t.feature.tolist(), "threshold": t.threshold.tolist(),
                      "left": t.children_left.tolist(), "right": t.children_right.tolist(),
                      "n": t.n_node_samples.tolist(), "cols": [int(c) for c in cols]})
    # the engine reports only the oddest 0.1%: read by eye (outlier_labels.py), the oddest 30
    # were mostly worth a look, 30 random flags at the 1.5% cut mostly not
    t_strong = float(np.quantile(s_if_all, 1 - STRONG_SHARE))
    model = {"version": VERSION, "threshold": t_z,
             "quantiles": {t: {f: list(v) for f, v in fs.items()}
                           for t, fs in stats.quantiles.items()},
             "forest": {"max_samples": int(forest.max_samples_), "trees": trees,
                        "threshold": t_strong, "threshold_1_5pct": t_if,
                        "max_score": float(s_if_all.max())}}
    (BUILD / "outlier_model.json").write_text(json.dumps(model), encoding="utf-8")
    live = OutlierStats.from_json(json.loads(json.dumps(model)))
    check = rng.choice(len(recs), 2000, replace=False)
    worst = max(abs(live.forest.score(live.vector(recs[i])) - s_if_all[i]) for i in check)
    assert worst < 1e-9, f"pure-Python forest differs from sklearn by {worst}"

    def rows(idx):
        return [{"work_id": recs[i]["work_id"], "score": round(float(s_if_all[i]), 3),
                 "type": recs[i].get("work_type_code"), "amount": recs[i].get("amount"),
                 "recommended": recs[i].get("recommended_date"),
                 "completed": recs[i].get("completed_date"), "status": recs[i].get("status"),
                 "description": str(recs[i].get("description"))[:200],
                 "z": json.dumps({k: round(v, 1) for k, v in stats.zscores(recs[i]).items()})}
                for i in idx]
    flagged = np.where(s_if_all >= t_if)[0]
    pd.DataFrame(rows(np.argsort(-s_if_all)[:30])).to_csv(OUT / "outlier_top_sample.csv",
                                                         index=False)
    pd.DataFrame(rows(rng.choice(flagged, 30, replace=False))).to_csv(
        OUT / "outlier_random_sample.csv", index=False)
    res = {"version": VERSION, "works": len(recs), "flag_share": FLAG_SHARE,
           "threshold_robust_z": round(t_z, 3), "threshold_forest": round(t_if, 4),
           "engine_threshold_oddest_0_1pct": round(t_strong, 4),
           "engine_findings_real_works": int((s_if_all >= t_strong).sum()),
           "flagged_real_works": {"robust_z": int((s_all >= t_z).sum()),
                                  "isolation_forest": int((s_if_all >= t_if).sum())},
           "kept": "isolation_forest (catches more planted two-field oddities)",
           "pure_python_forest_max_difference_from_sklearn": float(worst),
           "false_alarms_on_control": {"robust_z": round(fa_z, 4), "isolation_forest": round(fa_if, 4)},
           "planted_two_field_caught": planted,
           "planted_single_field_amount_x5_caught": {"robust_z": round(single_z, 3),
                                                     "isolation_forest": round(single_if, 3)}}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "outlier_trial.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
