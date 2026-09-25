r"""Trial 3 - Delay Prediction on real completion histories.

Question asked AT RECOMMENDATION TIME: will this work still be unfinished a year after the
MP recommended it (the guidelines expect works to finish within a year)?

Labels are real: the export records which works were completed and when.

Strict backtest - pretend today is T0 = 2025-01-01:
  - train only on works whose outcome was already known at T0 (recommended before
    2024-01-01, so a full year had passed);
  - test on works recommended after T0 (2025-01-01 .. 2025-05-26; each has a full year of
    follow-up before the 2026-05-26 snapshot).
Office and district track records are computed from the training works only. Office backlog
counts works still open on the day each work was recommended - known at the time.

Baselines: the implementing office's past late rate, and the work type's past late rate.

Run:  .venv-trial\Scripts\python.exe data\trial\delay_trial.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import KFold

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "apps" / "engine"))
from drishti.agents.statistical.text import reads_as_bundle  # noqa: E402

BUILD = ROOT / "data" / "build"
OUT = ROOT / "data" / "trial" / "results"
SNAP = pd.Timestamp("2026-05-26")
T0 = pd.Timestamp("2025-01-01")
HORIZON = 365


def share_late(y: np.ndarray, score: np.ndarray, top: bool, share: float = 0.10) -> float:
    k = max(1, int(len(y) * share))
    order = np.argsort(-score if top else score, kind="stable")
    return round(float(y[order[:k]].mean()), 4)


def target_encode(train: pd.DataFrame, test: pd.DataFrame, col: str, prior: float, k: float = 20.0):
    """Late rate per category, shrunk toward the overall rate; out-of-fold for training rows."""
    tr = np.full(len(train), prior)
    for fit_idx, enc_idx in KFold(5, shuffle=True, random_state=26).split(train):
        g = train.iloc[fit_idx].groupby(col).late.agg(["sum", "count"])
        rate = (g["sum"] + prior * k) / (g["count"] + k)
        tr[enc_idx] = train.iloc[enc_idx][col].map(rate).fillna(prior).values
    g = train.groupby(col).late.agg(["sum", "count"])
    rate = (g["sum"] + prior * k) / (g["count"] + k)
    return tr, test[col].map(rate).fillna(prior).values


def office_load(all_works: pd.DataFrame) -> pd.DataFrame:
    """Per work: works the same office had open, and had received in the past year, on the
    day this work was recommended (only facts known that day)."""
    out = []
    for _, g in all_works.groupby("agency_name", sort=False):
        rec = np.sort(g.rec.values)
        done = np.sort(g.done.dropna().values)
        opened = np.searchsorted(rec, g.rec.values, side="left")
        closed = np.searchsorted(done, g.rec.values, side="right")
        recent = opened - np.searchsorted(rec, (g.rec - pd.Timedelta(days=365)).values, side="left")
        out.append(pd.DataFrame({"office_open": opened - closed, "office_recent": recent},
                                index=g.index))
    return pd.concat(out)


def stuck_now(w: pd.DataFrame) -> dict:
    """Works recommended Apr 2023 - May 2024 (2+ years before the snapshot) and still open."""
    old = w[(w.rec >= "2023-04-01") & (w.rec <= SNAP - pd.Timedelta(days=730))]
    open_ = old[old.status != "COMPLETED"]
    return {"recommended_apr2023_may2024": int(len(old)), "still_open_2_years_later": int(len(open_)),
            "share": round(len(open_) / len(old), 3), "value_cr": round(float(open_.amount.sum()) / 1e7, 1),
            "by_status": open_.status.value_counts().to_dict(),
            "by_type": open_.work_type_code.value_counts().head(6).to_dict()}


def main() -> None:
    w = pd.read_parquet(BUILD / "works.parquet")
    w["rec"] = pd.to_datetime(w.recommended_date)
    w["done"] = pd.to_datetime(w.completed_date)
    stuck = stuck_now(w[w.rec.notna()])
    w = w[w.rec.notna() & ~(w.done < w.rec)].copy()             # impossible dates out
    w["agency_name"] = w.agency_name.fillna("NA").astype(str)
    w = w.join(office_load(w))

    w["late"] = (~(w.done.notna() & ((w.done - w.rec).dt.days <= HORIZON))).astype(int)
    w["log_amount"] = np.log10(w.amount.astype(float).clip(lower=1000))
    w["month"] = w.rec.dt.month
    w["desc_len"] = w.description.fillna("").str.len()
    w["bundle"] = w.description.map(reads_as_bundle).astype(int)
    w["outside"] = w.is_outside_constituency.fillna(False).astype(int)
    for c in ("work_type_code", "state_lgd", "district_lgd", "house", "term", "category"):
        w[c] = w[c].fillna("NA").astype(str)

    train = w[(w.rec >= "2023-04-01") & (w.rec < T0 - pd.Timedelta(days=HORIZON))].copy()
    test = w[(w.rec >= T0) & (w.rec <= SNAP - pd.Timedelta(days=HORIZON))].copy()
    prior = train.late.mean()
    for col in ("agency_name", "district_lgd", "work_type_code"):
        tr, te = target_encode(train, test, col, prior)
        train[f"{col}_rate"], test[f"{col}_rate"] = tr, te

    cat = ["work_type_code", "state_lgd", "house", "category"]
    feats = ["log_amount", "month", "desc_len", "bundle", "outside", "office_open", "office_recent",
             "agency_name_rate", "district_lgd_rate", "work_type_code_rate", *cat]
    for c in cat:
        cats = pd.Index(sorted(train[c].unique()))
        train[c] = pd.Categorical(train[c], categories=cats)
        test[c] = pd.Categorical(test[c].where(test[c].isin(cats)), categories=cats)
    model = lgb.LGBMClassifier(n_estimators=300, learning_rate=0.05, num_leaves=31,
                               min_child_samples=50, subsample=0.8, subsample_freq=1,
                               colsample_bytree=0.8, random_state=26, verbose=-1)
    model.fit(train[feats], train.late, categorical_feature=cat)
    p = model.predict_proba(test[feats])[:, 1]
    y = test.late.values

    def report(score: np.ndarray) -> dict:
        return {"auc": round(roc_auc_score(y, score), 4),
                "late_in_riskiest_10pct": share_late(y, score, top=True),
                "late_in_safest_10pct": share_late(y, score, top=False)}

    # District level: can we forecast which districts' new works will run late?
    test["p"] = p
    d = test.groupby("district_lgd").agg(n=("late", "size"), actual=("late", "mean"),
                                         predicted=("p", "mean"), past=("district_lgd_rate", "first"))
    d = d[d.n >= 50]
    district_level = {
        "districts_with_50plus_new_works": int(len(d)),
        "rank_correlation_model": round(float(d.actual.corr(d.predicted, method="spearman")), 4),
        "rank_correlation_past_district_rate": round(float(d.actual.corr(d.past, method="spearman")), 4),
        "mean_abs_error_model_pts": round(float((d.actual - d.predicted).abs().mean() * 100), 1),
    }

    res = {
        "stuck_now": stuck,
        "district_level": district_level,
        "setup": {"pretend_today": str(T0.date()), "horizon_days": HORIZON,
                  "train": "recommended 2023-04-01 .. 2023-12-31", "test": "recommended 2025-01-01 .. 2025-05-26"},
        "train_works": int(len(train)), "test_works": int(len(test)),
        "late_rate_train": round(float(train.late.mean()), 4),
        "late_rate_test": round(float(y.mean()), 4),
        "model": report(p) | {"mean_predicted": round(float(p.mean()), 4)},
        "baseline_office_record": report(test.agency_name_rate.values),
        "baseline_work_type_record": report(test.work_type_code_rate.values),
        "baseline_office_backlog": report(test.office_open.values.astype(float)),
        "feature_importance": dict(sorted(zip(feats, map(int, model.feature_importances_)),
                                          key=lambda kv: -kv[1])),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "delay_trial.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
