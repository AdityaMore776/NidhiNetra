r"""Peer-cost bands, completion times and the road-length price curve.

Writes data/build/{cohort_stats,duration_stats,unit_rate_models}.parquet.

Every constant is the one measured in ~/saakshya (AD-106, 2026-09-09), and
this script ASSERTS that it reproduces those measurements before writing
anything. A drift means the corpus or the method changed, and that has to be
understood before it reaches an officer's screen.

Run: apps\engine\.venv\Scripts\python.exe data\build_stats.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "engine"))
from drishti.agents.statistical.band import MIN_COHORT, P10_P90_SD, SD_FLOOR, SHRINK_K  # noqa: E402
from drishti.agents.statistical.text import reads_as_bundle, stated_length  # noqa: E402

BUILD = Path(__file__).resolve().parent / "build"

# Published rates for a rural single-lane CC road (per metre), carried from
# analyse_costs.py so the corpus curve is checked against something outside it.
ROAD_ANCHOR = (4000.0, 6500.0, "published rural single-lane CC road rates")


def cohorts(w: pd.DataFrame) -> pd.DataFrame:
    sd_type = w.groupby("work_type_code").l.std()
    out = []
    for level, keys in (("type_district", ["work_type_code", "district_lgd"]),
                        ("type_state", ["work_type_code", "state_lgd"]),
                        ("type", ["work_type_code"])):
        g = w.groupby(keys).l
        s = pd.DataFrame({"n": g.size(), "p10": g.quantile(0.10), "p50": g.median(),
                          "p90": g.quantile(0.90)}).reset_index()
        s["sd_raw"] = (s.p90 - s.p10) / P10_P90_SD
        st = s.work_type_code.map(sd_type)
        s["sd"] = ((s.n * s.sd_raw + SHRINK_K * st) / (s.n + SHRINK_K)).clip(lower=SD_FLOOR)
        s["level"] = level
        s["key"] = s[keys[1]] if len(keys) == 2 else ""
        out.append(s[["level", "work_type_code", "key", "n", "p10", "p50", "p90", "sd"]])
    return pd.concat(out, ignore_index=True)


def check_against_ad106(w: pd.DataFrame, c: pd.DataFrame) -> None:
    td = c[c.level == "type_district"].set_index(["work_type_code", "key"])
    idx = pd.MultiIndex.from_arrays([w.work_type_code, w.district_lgd])
    m = td.reindex(idx)
    assessable = (m.n.values >= MIN_COHORT)
    z = (w.l.values - m.p50.values) / m.sd.values
    bundle = w.description.map(reads_as_bundle).values
    ok = assessable & ~bundle
    share = assessable.mean()
    above = (z[ok] >= 3).mean()
    print(f"type x district cohort n>={MIN_COHORT}: {share:.1%} of works (AD-106: 84.2%)")
    print(f"bundle share {bundle.mean():.1%} (AD-106: 8.8%)")
    print(f"z>=3 above peers after bundle gate: {above:.2%} (AD-106: 1.20%)")
    assert abs(share - 0.842) < 0.005, share
    assert abs(above - 0.0120) < 0.005, above


def durations(w: pd.DataFrame) -> pd.DataFrame:
    d = w[(w.status == "COMPLETED") & w.recommended_date.notna() & w.completed_date.notna()]
    days = (pd.to_datetime(d.completed_date) - pd.to_datetime(d.recommended_date)).dt.days
    d = d.assign(days=days)[days > 0]
    g = d.groupby("work_type_code").days
    s = pd.DataFrame({"n": g.size(), "p50": g.median(), "p90": g.quantile(0.90),
                      "p98": g.quantile(0.98)}).reset_index()
    s = s[s.n >= MIN_COHORT]
    print(f"median completion across completed works: {d.days.median():.0f} days (old: 392)")
    return s


def road_curve(w: pd.DataFrame) -> pd.DataFrame:
    s = w[w.work_type_code == "ROAD_CC"].copy()
    s["len_m"] = s.description.map(stated_length)
    s = s[s.len_m.notna()]
    x, y = np.log10(s.len_m.values), s.l.values
    slope, intercept = np.polyfit(x, y, 1)
    sd = float((y - (slope * x + intercept)).std())
    print(f"ROAD_CC length curve: n={len(s)}, slope={slope:.4f}, "
          f"intercept={intercept:.4f}, resid_sd={sd:.4f} (old: 4065, 0.6309, 4.5381, 0.2772)")
    assert len(s) == 4065 and abs(slope - 0.6309) < 0.01 and abs(sd - 0.2772) < 0.01
    return pd.DataFrame([{
        "work_type_code": "ROAD_CC", "unit": "m", "n": len(s), "slope": float(slope),
        "intercept": float(intercept), "resid_sd": sd, "anchor_low": ROAD_ANCHOR[0],
        "anchor_high": ROAD_ANCHOR[1], "anchor_label": ROAD_ANCHOR[2]}])


def timeline_counts(works: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """How often "completed before recommended" (by 7+ days) occurs, per recommendation
    quarter and per implementing office. Read by validation/timeline.py."""
    d = works[works.recommended_date.notna() & works.completed_date.notna()].copy()
    rec = pd.to_datetime(d.recommended_date)
    gap = (rec - pd.to_datetime(d.completed_date)).dt.days
    d["bad"] = (gap >= 7).astype(int)
    d["quarter"] = rec.dt.year.astype(str) + "-Q" + rec.dt.quarter.astype(str)
    q = d.groupby("quarter").agg(n=("bad", "size"), bad=("bad", "sum")).reset_index()
    a = (d[d.agency_name.notna()].groupby("agency_name")
         .agg(completed=("bad", "size"), bad=("bad", "sum")).reset_index())
    print(f"impossible dates: {int(q.bad.sum()):,} of {int(q.n.sum()):,} works with both dates "
          f"({q.bad.sum() / q.n.sum():.2%}; measured 1,096 of 85,773 on 2026-09-25)")
    return q, a


def main() -> None:
    works = pd.read_parquet(BUILD / "works.parquet")
    w = works[(works.amount > 0) & works.work_type_code.notna()].copy()
    w["l"] = np.log10(w.amount.astype(float))
    c = cohorts(w)
    check_against_ad106(w, c)
    c = c[c.n >= MIN_COHORT]
    d = durations(works)
    u = road_curve(w)
    tq, ta = timeline_counts(works)
    tq.to_parquet(BUILD / "timeline_quarters.parquet", index=False)
    ta.to_parquet(BUILD / "timeline_agencies.parquet", index=False)
    c.to_parquet(BUILD / "cohort_stats.parquet", index=False)
    d.to_parquet(BUILD / "duration_stats.parquet", index=False)
    u.to_parquet(BUILD / "unit_rate_models.parquet", index=False)
    print(f"wrote {len(c):,} cohorts, {len(d)} duration rows, {len(u)} unit-rate model")


if __name__ == "__main__":
    main()
