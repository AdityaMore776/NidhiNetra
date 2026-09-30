r"""Delay Prediction engine: will an open work miss the one-year norm? (T040)

The guidelines expect a work to finish within a year of its recommendation, "generally"
(para 3.13). The public export records which works finished and when, so the labels are
real: late = not completed within 365 days of recommendation.

1. MEASURE (what FINDINGS reports)
   a. Strict time-based backtest, as data/trial/delay_trial.py: pretend today is
      2025-01-01; train only on works whose outcome was known then (recommended
      2023-04-01..2023-12-31); test on works recommended 2025-01-01..2025-05-26 (each has
      a full year of follow-up before the 26 May 2026 snapshot). Office, district and type
      track records come from the training works only.
   b. Held-out districts: the same training period, 5-fold GroupKFold by district, so a
      district's own record never helps score it.
   Baseline for both: the implementing office's own past late rate.

2. SCORE (what the live engine shows)
   Train on every work whose one-year outcome is known at the snapshot; score the works
   still open and less than a year old (their outcome is not known yet). Each score comes
   with its three strongest reasons (LightGBM's exact per-feature contributions, i.e.
   tree SHAP values) and its rank among all scored works.

Writes data/build/delay_scores.parquet and data/trial/results/delay_model.json.
Run: .venv-trial\Scripts\python.exe data\build_delay_model.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold, KFold

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "engine"))
from drishti.agents.statistical.scope import read  # noqa: E402

BUILD = ROOT / "data" / "build"
OUT = ROOT / "data" / "trial" / "results"
SNAP = pd.Timestamp("2026-05-26")
T0 = pd.Timestamp("2025-01-01")
HORIZON = 365
MODEL_VERSION = "delay-model-1"
CAT = ["work_type_code", "state_lgd", "house", "category"]
NUM = ["log_amount", "month", "desc_len", "bundle", "outside", "office_open", "office_recent",
       "agency_name_rate", "district_lgd_rate", "work_type_code_rate"]
FEATS = NUM + CAT
PARAMS = dict(n_estimators=300, learning_rate=0.05, num_leaves=31, min_child_samples=50,
              subsample=0.8, subsample_freq=1, colsample_bytree=0.8, random_state=26, verbose=-1)


def target_encode(train: pd.DataFrame, test: pd.DataFrame, col: str, prior: float,
                  k: float = 20.0) -> tuple[np.ndarray, np.ndarray]:
    """Late rate per category shrunk toward the overall rate; out-of-fold for training rows."""
    tr = np.full(len(train), prior)
    for fit_idx, enc_idx in KFold(5, shuffle=True, random_state=26).split(train):
        g = train.iloc[fit_idx].groupby(col).late.agg(["sum", "count"])
        rate = (g["sum"] + prior * k) / (g["count"] + k)
        tr[enc_idx] = train.iloc[enc_idx][col].map(rate).fillna(prior).to_numpy()
    g = train.groupby(col).late.agg(["sum", "count"])
    rate = (g["sum"] + prior * k) / (g["count"] + k)
    return tr, test[col].map(rate).fillna(prior).to_numpy()


def office_load(all_works: pd.DataFrame) -> pd.DataFrame:
    """Works the same office had open, and had received in the past year, on the day each
    work was recommended (facts known that day)."""
    out = []
    for _, g in all_works.groupby("agency_name", sort=False):
        rec = np.sort(g.rec.to_numpy())
        done = np.sort(g.done.dropna().to_numpy())
        opened = np.searchsorted(rec, g.rec.to_numpy(), side="left")
        closed = np.searchsorted(done, g.rec.to_numpy(), side="right")
        recent = opened - np.searchsorted(rec, (g.rec - pd.Timedelta(days=365)).to_numpy(),
                                          side="left")
        out.append(pd.DataFrame({"office_open": opened - closed, "office_recent": recent},
                                index=g.index))
    return pd.concat(out)


def prepare() -> pd.DataFrame:
    w = pd.read_parquet(BUILD / "works.parquet")
    w["rec"] = pd.to_datetime(w.recommended_date)
    w["done"] = pd.to_datetime(w.completed_date)
    w = w[w.rec.notna() & (w.rec >= "2023-04-01") & ~(w.done < w.rec)].copy()
    w["agency_name"] = w.agency_name.fillna("NA").astype(str)
    w = w.join(office_load(w))
    w["late"] = (~(w.done.notna() & ((w.done - w.rec).dt.days <= HORIZON))).astype(int)
    w["known"] = (w.rec <= SNAP - pd.Timedelta(days=HORIZON)) | \
        (w.done.notna() & ((w.done - w.rec).dt.days <= HORIZON))
    w["log_amount"] = np.log10(w.amount.fillna(0).astype(float).clip(lower=1000))
    w["month"] = w.rec.dt.month
    w["desc_len"] = w.description.fillna("").str.len()
    w["bundle"] = [int(read(t, d).bundle) for t, d in zip(w.work_type_code, w.description,
                                                          strict=True)]
    w["outside"] = w.is_outside_constituency.fillna(False).astype(int)
    for c in ("work_type_code", "state_lgd", "district_lgd", "house", "term", "category"):
        w[c] = w[c].fillna("NA").astype(str)
    return w


def encode(train: pd.DataFrame, test: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    train, test = train.copy(), test.copy()
    prior = train.late.mean()
    for col in ("agency_name", "district_lgd", "work_type_code"):
        tr, te = target_encode(train, test, col, prior)
        train[f"{col}_rate"], test[f"{col}_rate"] = tr, te
    for c in CAT:
        cats = pd.Index(sorted(train[c].unique()))
        train[c] = pd.Categorical(train[c], categories=cats)
        test[c] = pd.Categorical(test[c].where(test[c].isin(cats)), categories=cats)
    return train, test


def fit(train: pd.DataFrame) -> lgb.LGBMClassifier:
    return lgb.LGBMClassifier(**PARAMS).fit(train[FEATS], train.late, categorical_feature=CAT)


def report(y: np.ndarray, score: np.ndarray) -> dict:
    k = max(1, int(len(y) * 0.10))
    order = np.argsort(-score, kind="stable")
    return {"auc": round(float(roc_auc_score(y, score)), 4),
            "late_in_riskiest_10pct": round(float(y[order[:k]].mean()), 4),
            "late_in_safest_10pct": round(float(y[order[-k:]].mean()), 4)}


def backtest(w: pd.DataFrame) -> dict:
    train = w[(w.rec < T0 - pd.Timedelta(days=HORIZON))]
    test = w[(w.rec >= T0) & (w.rec <= SNAP - pd.Timedelta(days=HORIZON))]
    tr, te = encode(train, test)
    p = fit(tr).predict_proba(te[FEATS])[:, 1]
    y = te.late.to_numpy()
    return {"train": "recommended 2023-04-01 .. 2023-12-31",
            "test": "recommended 2025-01-01 .. 2025-05-26", "train_works": len(tr),
            "test_works": len(te), "late_rate_test": round(float(y.mean()), 4),
            "model": report(y, p), "baseline_office_record": report(y, te.agency_name_rate.to_numpy())}


def held_out_districts(w: pd.DataFrame) -> dict:
    base = w[(w.rec < T0 - pd.Timedelta(days=HORIZON))].reset_index(drop=True)
    p = np.zeros(len(base))
    office = np.zeros(len(base))
    for fit_idx, te_idx in GroupKFold(5).split(base, groups=base.district_lgd):
        tr, te = encode(base.iloc[fit_idx], base.iloc[te_idx])
        p[te_idx] = fit(tr).predict_proba(te[FEATS])[:, 1]
        office[te_idx] = te.agency_name_rate.to_numpy()
    y = base.late.to_numpy()
    return {"works": len(base), "folds": "GroupKFold(5) by district",
            "model": report(y, p), "baseline_office_record": report(y, office)}


REASON = {
    "agency_name_rate": "the implementing office's past record ({v:.0%} of its works finished "
                        "more than a year after recommendation)",
    "district_lgd_rate": "the district's past record ({v:.0%} of its works finished late)",
    "work_type_code_rate": "works of this type often run late ({v:.0%} did)",
    "office_open": "the office had {v:,.0f} works still open when this one was recommended",
    "office_recent": "the office received {v:,.0f} works in the year before this one",
    "log_amount": "its size (Rs {amt})",
    "month": "the month it was recommended",
    "desc_len": "how little the description says",
    "bundle": "it covers several sites or units",
    "outside": "it is outside the MP's constituency",
    "work_type_code": "its work type",
    "state_lgd": "its state",
    "house": "the house of Parliament of the recommending MP",
    "category": "its category",
}


def reason_text(feat: str, row: pd.Series) -> str:
    v = row[feat]
    if feat == "log_amount":
        amt = float(10 ** v)
        s = f"{amt / 1e5:.2f} lakh" if amt < 1e7 else f"{amt / 1e7:.2f} crore"
        return REASON[feat].format(amt=s)
    try:
        return REASON[feat].format(v=float(v))
    except (ValueError, TypeError):
        return REASON[feat]


def score_open(w: pd.DataFrame) -> pd.DataFrame:
    known = w[w.known]
    todo = w[~w.known & (w.status != "COMPLETED")]
    tr, te = encode(known, todo)
    model = fit(tr)
    p = model.predict_proba(te[FEATS])[:, 1]
    contrib = model.predict(te[FEATS], pred_contrib=True)[:, :-1]     # last column = bias
    rank = pd.Series(p).rank(pct=True).to_numpy()
    rows = []
    for i, (_, r) in enumerate(te.iterrows()):
        top = [j for j in np.argsort(-contrib[i]) if contrib[i][j] > 0][:3]
        rows.append({"work_id": r.work_id, "p_late": float(p[i]), "rank_pct": float(rank[i]),
                     "base_rate": float(tr.late.mean()),
                     "reasons": [reason_text(FEATS[j], r) for j in top],
                     "model_version": MODEL_VERSION})
    return pd.DataFrame(rows)


def main() -> None:
    w = prepare()
    bt = backtest(w)
    print("backtest", json.dumps(bt), flush=True)
    hd = held_out_districts(w)
    print("held-out districts", json.dumps(hd), flush=True)
    scores = score_open(w)
    scores.to_parquet(BUILD / "delay_scores.parquet", index=False)
    res = {"model_version": MODEL_VERSION, "label": "not completed within 365 days of recommendation",
           "strict_backtest": bt, "held_out_districts": hd,
           "scored_open_works": len(scores),
           "scored_mean_p_late": round(float(scores.p_late.mean()), 4)}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "delay_model.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
