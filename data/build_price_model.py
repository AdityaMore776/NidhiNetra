r"""Cost engine version B, linear (T051): fit the word-price model and measure it against LightGBM.

The engine computes features (agents/statistical/price_model.py) for any work; this job fits
the weights on all real works and exports them as data:

  1. out-of-fold (GroupKFold(5) by constituency, as build_cost_model.py): each work's range
     comes from weights that never saw its constituency; per work type, the q10/q90 offsets
     are the 10% / 90% quantiles of those out-of-fold residuals (split-conformal)
     -> data/build/cost_expected_linear.parquet, for cost_trial_v2.py's planted test
  2. the weights refit on every work + the offsets -> data/build/price_model.json (loaded into
     the engine_models table)
  3. comparison with LightGBM version B (results/cost_model_b.json): median error, coverage

Run (needs scikit-learn: the trial venv): .venv-trial\Scripts\python.exe data\build_price_model.py
"""

from __future__ import annotations

import json
import sys
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.feature_extraction import DictVectorizer
from sklearn.linear_model import Ridge
from sklearn.model_selection import GroupKFold

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "engine"))
sys.path.insert(0, str(ROOT / "data"))
from common import clean  # noqa: E402
from drishti.agents.statistical.price_model import features  # noqa: E402

BUILD = ROOT / "data" / "build"
OUT = ROOT / "data" / "trial" / "results"
VERSION = "price-linear-1"
MIN_CONSTITUENCIES = 20
ALPHA = 3.0


def main() -> None:
    t0 = time.time()
    w = pd.read_parquet(BUILD / "works.parquet")
    w = w[(w.amount > 0) & w.work_type_code.notna()].reset_index(drop=True)
    recs = [clean(r) for r in w.to_dict("records")]
    feats = [features(r) for r in recs]
    groups = w.constituency.fillna(w.mp_name).fillna("?").to_numpy()
    # words used in at least 20 constituencies: meaning shared across the country
    # (and the same for word pairs and word-within-type)
    text_feature = ("w=", "b=", "tw=")
    spread_of: dict[str, set] = defaultdict(set)
    for f, g in zip(feats, groups, strict=True):
        for k in f:
            if k.startswith(text_feature):
                spread_of[k].add(g)
    keep = {k for k, s in spread_of.items() if len(s) >= MIN_CONSTITUENCIES}
    feats = [{k: v for k, v in f.items() if not k.startswith(text_feature) or k in keep}
             for f in feats]
    dv = DictVectorizer(sparse=True)
    x = dv.fit_transform(feats)
    y = np.log10(w.amount.astype(float).to_numpy())
    print(f"{x.shape[0]:,} works, {x.shape[1]:,} features ({len(keep):,} words) "
          f"at {time.time() - t0:.0f}s", flush=True)

    oof = np.zeros(len(w))
    for tr, te in GroupKFold(n_splits=5).split(x, y, groups):
        oof[te] = Ridge(alpha=ALPHA).fit(x[tr], y[tr]).predict(x[te])
    resid = y - oof
    types = w.work_type_code.to_numpy()
    spread = {}
    for t in np.unique(types):
        r = resid[types == t]
        spread[str(t)] = (float(np.quantile(r, 0.10)), float(np.quantile(r, 0.90)))
    lo = np.array([spread[t][0] for t in types])
    hi = np.array([spread[t][1] for t in types])
    pd.DataFrame({"work_id": w.work_id, "q10": oof + lo, "q50": oof, "q90": oof + hi,
                  "model_version": VERSION}).to_parquet(BUILD / "cost_expected_linear.parquet",
                                                        index=False)

    final = Ridge(alpha=ALPHA).fit(x, y)
    names = dv.get_feature_names_out()
    weights = {str(n): round(float(c), 6) for n, c in zip(names, final.coef_, strict=True)
               if abs(c) > 1e-6}
    model = {"version": VERSION, "intercept": float(final.intercept_), "weights": weights,
             "spread": spread, "default_spread": [float(np.quantile(resid, 0.10)),
                                                  float(np.quantile(resid, 0.90))]}
    (BUILD / "price_model.json").write_text(json.dumps(model), encoding="utf-8")

    mae = float(np.abs(resid).mean())
    inside = float(((y >= oof + lo) & (y <= oof + hi)).mean())
    lgb = json.loads((OUT / "cost_model_b.json").read_text(encoding="utf-8"))
    res = {"version": VERSION, "works": len(w), "features": int(x.shape[1]), "words": len(keep),
           "folds": "GroupKFold(5) by constituency",
           "median_abs_error_log10": round(mae, 4), "median_abs_error_factor": round(10 ** mae, 3),
           "share_inside_q10_q90": round(inside, 4),
           "share_above_q90": round(float((y > oof + hi).mean()), 4),
           "lightgbm_for_comparison": {k: lgb[k] for k in (
               "median_abs_error_log10", "median_abs_error_factor",
               "share_inside_q10_q90_after_calibration", "share_above_q90")},
           "model_kb": round(len(json.dumps(model)) / 1024),
           "seconds": round(time.time() - t0)}
    (OUT / "price_model.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
