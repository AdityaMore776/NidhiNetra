r"""Cost engine version B: each work's expected cost range, learned from its description.

A work type is too coarse to price a work (a library building vs a book order), and a
district median carries one MP's filing habits. This job learns, from all 2 lakh real
works, what a work *described like this* usually costs: LightGBM quantile regression
(q 0.1 / 0.5 / 0.9) of log10(amount) on

  words        the description's words and word pairs (TF-IDF), numbers removed so the
               amount written in the text ("Rs 50 lakh") can never leak into the answer
  size         the stated length (m) and unit count, read by the engine's own readers
  context      work type, the engine's scope reading (goods / works), state, year

Every work's range comes from a model that never saw that work's constituency
(5-fold GroupKFold by constituency): an MP's copy-pasted works cannot teach the model
their own price, and the planted-inflation test in data/trial/cost_trial_v2.py stays
honest (a planted amount is never in the training data of the model that judges it).

Writes data/build/cost_expected.parquet (work_id, q10, q50, q90 in log10 rupees, model
version). The engine reads it through the `cost_expected` table (migration 006).

Run (needs lightgbm, scikit-learn, scipy: the trial venv):
    .venv-trial\Scripts\python.exe data\build_cost_model.py
"""

from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
import scipy.sparse as sp
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import GroupKFold

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "engine"))
from drishti.agents.statistical.scope import mast_count, read, stated_count  # noqa: E402
from drishti.agents.statistical.text import stated_length  # noqa: E402

BUILD = ROOT / "data" / "build"
OUT = ROOT / "data" / "trial" / "results"
MODEL_VERSION = "cost-model-b-2"
QUANTILES = (0.1, 0.5, 0.9)
PARAMS = dict(objective="quantile", n_estimators=400, learning_rate=0.08, num_leaves=63,
              min_child_samples=30, subsample=0.8, subsample_freq=1, colsample_bytree=0.5,
              verbose=-1, random_state=26)
_DIGITS = re.compile(r"\d+")


def features(w: pd.DataFrame) -> sp.csr_matrix:
    text = (w.description.fillna("").str.lower()).map(lambda s: _DIGITS.sub(" ", s))
    tf = TfidfVectorizer(min_df=5, max_features=20000, ngram_range=(1, 2), sublinear_tf=True)
    x_text = tf.fit_transform(text)
    rd = [read(t, d) for t, d in zip(w.work_type_code, w.description, strict=True)]
    sc = pd.Series([r.scope for r in rd], index=w.index)
    cat = pd.get_dummies(pd.DataFrame({"t": w.work_type_code.astype(str),
                                       "st": w.state_lgd.astype(str),
                                       "sc": w.work_type_code.astype(str) + "|" + sc}),
                         sparse=True, dtype=float)
    length = w.description.map(lambda d: stated_length(d, allow_km=True))
    count = pd.Series([r.count or stated_count(d) or mast_count(d)
                       for r, d in zip(rd, w.description, strict=True)], index=w.index,
                      dtype=float)
    num = np.column_stack([
        pd.to_datetime(w.recommended_date).dt.year.fillna(2020).to_numpy() - 2000,
        np.log10(length.fillna(1.0).to_numpy(dtype=float)), length.notna().to_numpy(float),
        np.log10(count.fillna(1).to_numpy(dtype=float)), count.notna().to_numpy(float),
        np.array([r.bundle for r in rd], float), np.array([r.many_sites for r in rd], float),
        np.array([r.undescribed for r in rd], float),
    ])
    return sp.hstack([x_text, sp.csr_matrix(cat.sparse.to_coo()),
                      sp.csr_matrix(num)]).tocsr().astype(np.float32)


def main() -> None:
    t0 = time.time()
    w = pd.read_parquet(BUILD / "works.parquet")
    w = w[(w.amount > 0) & w.work_type_code.notna()].reset_index(drop=True)
    y = np.log10(w.amount.astype(float).to_numpy())
    x = features(w)
    groups = w.constituency.fillna(w.mp_name).fillna("?").to_numpy()
    pred = {q: np.zeros(len(w)) for q in QUANTILES}
    for k, (tr, te) in enumerate(GroupKFold(n_splits=5).split(x, y, groups)):
        for q in QUANTILES:
            m = lgb.LGBMRegressor(alpha=q, **PARAMS).fit(x[tr], y[tr])
            pred[q][te] = m.predict(x[te])
        print(f"fold {k} done at {time.time() - t0:.0f}s", flush=True)
    # Out-of-fold quantiles came out too narrow (67% of works inside q10-q90, not 80%): a
    # new constituency is less predictable than the training folds suggest. Shift each
    # bound by the out-of-fold miss so that 10% of works sit below q10 and 10% above q90
    # (split-conformal style; one shift per bound, per work type).
    q10 = np.minimum(pred[0.1], pred[0.5])
    q90 = np.maximum(pred[0.9], pred[0.5])
    for t in w.work_type_code.unique():
        i = (w.work_type_code == t).to_numpy()
        q90[i] += max(0.0, float(np.quantile(y[i] - q90[i], 0.90)))
        q10[i] -= max(0.0, float(np.quantile(q10[i] - y[i], 0.90)))
    out = pd.DataFrame({"work_id": w.work_id, "q10": q10, "q50": pred[0.5], "q90": q90,
                        "model_version": MODEL_VERSION})
    out.to_parquet(BUILD / "cost_expected.parquet", index=False)
    mae = float(np.abs(y - pred[0.5]).mean())
    inside = float(((y >= q10) & (y <= q90)).mean())
    summary = {"model_version": MODEL_VERSION, "works": len(w), "features": x.shape[1],
               "folds": "GroupKFold(5) by constituency",
               "median_abs_error_log10": round(mae, 4),
               "median_abs_error_factor": round(10 ** mae, 3),
               "share_inside_q10_q90_after_calibration": round(inside, 4),
               "share_above_q90": round(float((y > q90).mean()), 4),
               "seconds": round(time.time() - t0)}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "cost_model_b.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
