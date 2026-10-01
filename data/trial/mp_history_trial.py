r"""Does an MP's history predict problems in their later works, beyond district and office? (1 Oct 2026)

The owner asked whether DRISHTI should look at an MP's history, e.g. a hidden MP risk score that
decides how thoroughly that MP's recommendations are checked. Before any design: is it proven?

Time split, so nothing in the past sees the future: history = works recommended before
2024-07-01, test = works recommended from 2024-07-01. For each test work, the past rate of the
same outcome among the earlier works of (a) its MP, (b) its district, (c) its implementing
office (each shrunk toward the overall rate with 20 pseudo-works; no history = overall rate).

Outcomes:
  late          not completed within 365 days (a REAL outcome, recorded by the portal)
  repeat_split  the Duplicate & Split engine finds a pair or a same-site split
  cost          the Cost engine finds a price question (above peers, unit price, per metre)
  guideline     Guideline Compliance R07 (possibly inadmissible) or R06 (impossible dates)
The engine outcomes are DRISHTI's own flags, not verified wrongdoing: a history built from them
measures how consistent the flags are, not how guilty anyone is.

Measured: AUC of each history alone, and the gain from adding the MP's history to the better of
district and office (logistic regression on the three rates, fitted on half the test MPs and
scored on the other half, so the gain is not an in-sample fit). Also how many test works have
no MP history at all (new MPs after the June 2024 election).

Reads the per-work engine results from a full run (scores parquet given as argv[1]).
Writes results/mp_history_trial.json.
Run: .venv-trial\Scripts\python.exe data\trial\mp_history_trial.py <scores.parquet>
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[2]
BUILD = ROOT / "data" / "build"
OUT = ROOT / "data" / "trial" / "results"
CUT = pd.Timestamp("2024-07-01")
SNAP = pd.Timestamp("2026-05-26")
K = 20.0


def shrunk(hist: pd.DataFrame, test: pd.DataFrame, key: str, y: str) -> np.ndarray:
    prior = hist[y].mean()
    g = hist.groupby(key)[y].agg(["sum", "count"])
    rate = (g["sum"] + K * prior) / (g["count"] + K)
    return test[key].map(rate).fillna(prior).to_numpy()


def main() -> None:
    w = pd.read_parquet(BUILD / "works.parquet")
    s = pd.read_parquet(sys.argv[1])[["work_id", "risks", "codes"]]
    w = w.merge(s, on="work_id")
    w["rec"] = pd.to_datetime(w.recommended_date)
    w["done"] = pd.to_datetime(w.completed_date)
    w = w[w.rec.notna() & (w.rec >= "2023-04-01")].copy()
    risks = w.risks.map(json.loads)
    w["repeat_split"] = [int(r.get("dup_split", 0) >= 0.35) for r in risks]
    w["cost"] = [int(r.get("statistical", 0) >= 0.30) for r in risks]
    codes = w.codes.fillna("")
    w["guideline"] = (codes.str.contains("POSSIBLY_INADMISSIBLE")
                      | codes.str.contains("IMPOSSIBLE_TIMELINE")).astype(int)
    w["late"] = (~(w.done.notna() & ((w.done - w.rec).dt.days <= 365))).astype(int)
    for c in ("mp_name", "district_lgd", "agency_name"):
        w[c] = w[c].fillna("NA").astype(str)
    hist, test = w[w.rec < CUT], w[w.rec >= CUT]
    late_test = test[test.rec <= SNAP - pd.Timedelta(days=365)]

    res = {"history": "recommended 2023-04-01 .. 2024-06-30", "test": "recommended from 2024-07-01",
           "test_works": len(test),
           "test_works_whose_mp_has_no_history": int((~test.mp_name.isin(hist.mp_name)).sum()),
           "outcomes": {}}
    rng = np.random.default_rng(1)
    for y in ("late", "repeat_split", "cost", "guideline"):
        t = late_test if y == "late" else test
        yy = t[y].to_numpy()
        if yy.sum() == 0 or yy.sum() == len(yy):
            continue
        x = {k: shrunk(hist, t, col, y) for k, col in
             (("mp", "mp_name"), ("district", "district_lgd"), ("office", "agency_name"))}
        aucs = {k: round(float(roc_auc_score(yy, v)), 4) for k, v in x.items()}
        # gain from adding the MP to district + office, fitted on half the MPs, scored on the rest
        mps = t.mp_name.unique()
        half = set(rng.choice(mps, len(mps) // 2, replace=False))
        fit = t.mp_name.isin(half).to_numpy()
        base = np.column_stack([x["district"], x["office"]])
        full = np.column_stack([x["district"], x["office"], x["mp"]])
        auc_base = roc_auc_score(yy[~fit], LogisticRegression().fit(base[fit], yy[fit])
                                 .predict_proba(base[~fit])[:, 1])
        auc_full = roc_auc_score(yy[~fit], LogisticRegression().fit(full[fit], yy[fit])
                                 .predict_proba(full[~fit])[:, 1])
        res["outcomes"][y] = {"works": len(t), "rate": round(float(yy.mean()), 4),
                              "auc_alone": aucs,
                              "district_plus_office": round(float(auc_base), 4),
                              "plus_mp_history": round(float(auc_full), 4),
                              "gain_from_mp": round(float(auc_full - auc_base), 4)}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "mp_history_trial.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
