r"""Trial 4 - Fund Flow on the real money and date records.

What the public data can and cannot support:
  - CAN: the money funnel (allocated -> recommended -> sanctioned -> completed -> spent) from
    the MP-level files, summed to state and house level (DRISHTI never scores MPs); the timing
    of recommendations and completions from the works export; works still waiting for
    sanction long after the 75-day limit.
  - CANNOT: backtest a lapse forecast - the files are one snapshot, with no payment dates.

Run:  .venv-trial\Scripts\python.exe data\trial\fund_flow_trial.py
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
BUILD = ROOT / "data" / "build"
RAW = Path.home() / "saakshya" / "data" / "raw" / "inrolls"
OUT = ROOT / "data" / "trial" / "results"
SNAP = pd.Timestamp("2026-05-26")
SANCTION_DAYS = 75
MONEY = ["allocated_cr", "recommended_cr", "sanctioned_cr", "completed_cr", "expenditure_cr"]


def funnel() -> dict:
    frames = [pd.read_csv(RAW / f) for f in ("mplads_17ls.csv", "mplads_18ls.csv", "mplads_rs.csv")]
    m = pd.concat(frames, ignore_index=True)
    by_term = m.groupby("tenure_label")[MONEY].sum().round(1)
    by_term["spent_share_of_allocated"] = (by_term.expenditure_cr / by_term.allocated_cr).round(3)
    by_term["completed_share_of_recommended"] = (by_term.completed_cr / by_term.recommended_cr).round(3)
    ls17 = m[m.tenure_label == "17th Lok Sabha"].groupby("state_name")[MONEY].sum()
    ls17 = ls17[ls17.allocated_cr >= 50]
    ls17["spent_share"] = (ls17.expenditure_cr / ls17.allocated_cr).round(3)
    ls17["unspent_cr"] = (ls17.allocated_cr - ls17.expenditure_cr).round(1)
    return {"by_term": by_term.reset_index().to_dict("records"),
            "ls17_states_lowest_spent_share": ls17.sort_values("spent_share")
            .head(6)[["allocated_cr", "expenditure_cr", "unspent_cr", "spent_share"]].reset_index().to_dict("records"),
            "ls17_states_highest_spent_share": ls17.sort_values("spent_share", ascending=False)
            .head(3)[["allocated_cr", "expenditure_cr", "spent_share"]].reset_index().to_dict("records")}


def timing(w: pd.DataFrame) -> dict:
    q = w.groupby(w.rec.dt.to_period("Q")).agg(
        works=("work_id", "size"),
        done_within_1y=("done_1y", "mean"),
        done_by_snapshot=("done", lambda s: s.notna().mean()))
    q = q[(q.index >= pd.Period("2023Q3")) & (q.index <= pd.Period("2025Q2"))]
    q.index = q.index.astype(str)
    months = w[w.done.notna() & (w.done >= "2023-04-01") & (w.done < "2026-04-01")]
    mshare = months.done.dt.month.value_counts(normalize=True).sort_index()
    return {"recommendations_by_quarter": q.round(3).reset_index(names="quarter").to_dict("records"),
            "completions_share_by_month": {int(k): round(float(v), 4) for k, v in mshare.items()},
            "march_vs_average_month": round(float(mshare.get(3, 0) / (1 / 12)), 2)}


def sanction_backlog(w: pd.DataFrame) -> dict:
    waiting = w[(w.status == "RECOMMENDED") & ((SNAP - w.rec).dt.days > SANCTION_DAYS)]
    by_term = waiting.groupby("term").agg(works=("work_id", "size"), value_cr=("amount", lambda s: s.sum() / 1e7))
    dist = w[w.rec <= SNAP - pd.Timedelta(days=SANCTION_DAYS)].groupby(["state_name", "district_name"]).agg(
        recommended=("work_id", "size"),
        waiting=("status", lambda s: (s == "RECOMMENDED").sum()))
    dist = dist[dist.recommended >= 100]
    dist["waiting_share"] = (dist.waiting / dist.recommended).round(3)
    return {"waiting_beyond_75_days": int(len(waiting)),
            "waiting_value_cr": round(float(waiting.amount.sum() / 1e7), 1),
            "median_days_waiting": int((SNAP - waiting.rec).dt.days.median()),
            "by_term": by_term.round(1).reset_index().to_dict("records"),
            "districts_with_100plus_recommendations": int(len(dist)),
            "districts_over_half_waiting": int((dist.waiting_share > 0.5).sum()),
            "worst_districts": dist.sort_values("waiting_share", ascending=False).head(8)
            .reset_index().to_dict("records")}


def main() -> None:
    w = pd.read_parquet(BUILD / "works.parquet")
    w["rec"] = pd.to_datetime(w.recommended_date)
    w["done"] = pd.to_datetime(w.completed_date)
    w = w[w.rec.notna()].copy()
    w["done_1y"] = w.done.notna() & ((w.done - w.rec).dt.days.between(0, 365))
    res = {"funnel": funnel(), "timing": timing(w), "sanction_backlog": sanction_backlog(w)}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "fund_flow_trial.json").write_text(json.dumps(res, indent=2, default=str), encoding="utf-8")
    print(json.dumps(res, indent=2, default=str))


if __name__ == "__main__":
    main()
