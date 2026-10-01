r"""Delay engine v2 (T051): the late-rate ladder, measured the way v1's model was, then built.

Label (as v1, data/build_delay_model.py): late = not completed within 365 days of
recommendation. Works recommended from 2023-04-01 (the eSAKSHI era); impossible dates dropped.

1. MEASURE, with the same two tests v1 was judged on (results/delay_model.json):
   a. strict time-based backtest: pretend today is 2025-01-01; counts only from works whose
      outcome was known then (recommended 2023-04-01..2023-12-31); test on works recommended
      2025-01-01..2025-05-26
   b. held-out districts: the same training period, 5 folds by district, so a district's own
      record never helps score it (what a new district looks like to the engine)
   Baseline: the implementing office's own past late rate (v1's baseline).
2. BUILD: counts from every work whose one-year outcome is known at the snapshot, per step of
   the ladder (agents/delay/rates.py), written to data/build/delay_rates.parquet and loaded
   into the delay_rates table.

Run: apps\engine\.venv\Scripts\python.exe data\build_delay_rates.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "engine"))
from drishti.agents.delay.rates import LEVELS, DelayRates  # noqa: E402

BUILD = ROOT / "data" / "build"
OUT = ROOT / "data" / "trial" / "results"
SNAP = pd.Timestamp("2026-05-26")
T0 = pd.Timestamp("2025-01-01")
HORIZON = 365
VERSION = "delay-rates-2"


def prepare() -> pd.DataFrame:
    w = pd.read_parquet(BUILD / "works.parquet")
    w["rec"] = pd.to_datetime(w.recommended_date)
    w["done"] = pd.to_datetime(w.completed_date)
    w = w[w.rec.notna() & (w.rec >= "2023-04-01") & ~(w.done < w.rec)].copy()
    w["agency_name"] = w.agency_name.fillna("").astype(str)
    w["late"] = (~(w.done.notna() & ((w.done - w.rec).dt.days <= HORIZON))).astype(int)
    w["known"] = (w.rec <= SNAP - pd.Timedelta(days=HORIZON)) | \
        (w.done.notna() & ((w.done - w.rec).dt.days <= HORIZON))
    for c in ("work_type_code", "state_lgd", "district_lgd"):
        w[c] = w[c].fillna("NA").astype(str)
    return w


def counts(train: pd.DataFrame) -> list[dict]:
    t = train.work_type_code
    keyed = {"type": t, "state_type": train.state_lgd + "|" + t,
             "district_type": train.district_lgd + "|" + t, "office": train.agency_name}
    rows = [{"level": "all", "key": "", "n": len(train), "late": int(train.late.sum())}]
    for lv in LEVELS:
        g = train.assign(k=keyed[lv])
        if lv == "office":
            g = g[g.k != ""]
        agg = g.groupby("k").late.agg(["size", "sum"]).reset_index()
        rows += [{"level": lv, "key": k, "n": int(n), "late": int(s)}
                 for k, n, s in agg.itertuples(index=False)]
    return rows


def auc(y: np.ndarray, s: np.ndarray) -> float:
    r = pd.Series(s).rank().to_numpy()
    pos = y == 1
    n1, n0 = pos.sum(), (~pos).sum()
    return float((r[pos].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


def report(y: np.ndarray, s: np.ndarray) -> dict:
    k = max(1, int(len(y) * 0.10))
    order = np.argsort(-s, kind="stable")
    return {"auc": round(auc(y, s), 4),
            "late_in_riskiest_10pct": round(float(y[order[:k]].mean()), 4),
            "late_in_safest_10pct": round(float(y[order[-k:]].mean()), 4)}


def score(rates: DelayRates, df: pd.DataFrame) -> np.ndarray:
    return np.array([rates.estimate(r).p_late for r in df.to_dict("records")])


def office_only(train: pd.DataFrame, test: pd.DataFrame) -> np.ndarray:
    """v1's baseline: the office's own late rate, shrunk toward the overall rate."""
    prior = train.late.mean()
    g = train.groupby("agency_name").late.agg(["sum", "count"])
    rate = (g["sum"] + prior * 20) / (g["count"] + 20)
    return test.agency_name.map(rate).fillna(prior).to_numpy()


def main() -> None:
    w = prepare()
    train = w[w.rec < T0 - pd.Timedelta(days=HORIZON)]
    test = w[(w.rec >= T0) & (w.rec <= SNAP - pd.Timedelta(days=HORIZON))]
    rates = DelayRates.from_rows(counts(train))
    y = test.late.to_numpy()
    backtest = {"train": "recommended 2023-04-01 .. 2023-12-31",
                "test": "recommended 2025-01-01 .. 2025-05-26",
                "train_works": len(train), "test_works": len(test),
                "late_rate_test": round(float(y.mean()), 4),
                "ladder": report(y, score(rates, test)),
                "baseline_office_record": report(y, office_only(train, test))}
    print("backtest", json.dumps(backtest), flush=True)

    base = train.reset_index(drop=True)
    districts = np.array(sorted(base.district_lgd.unique()))
    rng = np.random.default_rng(26)
    fold_of = dict(zip(districts, rng.integers(0, 5, len(districts)), strict=True))
    fold = base.district_lgd.map(fold_of).to_numpy()
    p = np.zeros(len(base))
    office = np.zeros(len(base))
    for f in range(5):
        tr, te = base[fold != f], base[fold == f]
        p[fold == f] = score(DelayRates.from_rows(counts(tr)), te)
        office[fold == f] = office_only(tr, te)
    held = {"works": len(base), "folds": "5 folds by district",
            "ladder": report(base.late.to_numpy(), p),
            "baseline_office_record": report(base.late.to_numpy(), office)}
    print("held-out districts", json.dumps(held), flush=True)

    known = w[w.known]
    rows = counts(known)
    live = DelayRates.from_rows(rows)
    todo = w[~w.known & (w.status != "COMPLETED")]
    est = [live.estimate(r) for r in todo.to_dict("records")]
    # T410: the riskiest tenth of open works, stored with the counts (a fixed p >= 0.90 cut
    # flagged 43% of open works: most offices finish few works within a year)
    p90 = float(np.quantile([e.p_late for e in est], 0.90))
    rows.append({"level": "flag", "key": "p90", "n": 1_000_000, "late": int(p90 * 1_000_000)})
    pd.DataFrame(rows).assign(version=VERSION).to_parquet(BUILD / "delay_rates.parquet",
                                                         index=False)
    v1 = json.loads((OUT / "delay_model.json").read_text(encoding="utf-8"))
    res = {"version": VERSION, "label": "not completed within 365 days of recommendation",
           "strict_backtest": backtest, "held_out_districts": held,
           "v1_lightgbm_for_comparison": {
               "strict_backtest_auc": v1["strict_backtest"]["model"]["auc"],
               "held_out_districts_auc": v1["held_out_districts"]["model"]["auc"]},
           "rows": len(rows), "base_rate_known": round(live.base, 4),
           "open_works_scored": len(est),
           "estimate_rests_on": pd.Series([e.level for e in est]).value_counts().to_dict(),
           "p_late_quantiles_open": {q: round(float(np.quantile([e.p_late for e in est], q)), 4)
                                     for q in (0.5, 0.9, 0.99)}}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "delay_rates.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
