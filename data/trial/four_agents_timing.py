r"""Timing facts for the Time & Rules agent (T110 plan): sanction lag and build times, measured.

Reads the eSAKSHI public dashboard tables (data/raw/esakshi_dashboard, gitignored, through
data/esakshi_dashboard.py) and writes AGGREGATES ONLY to results/four_agents_timing.json and .txt:

  1. Sanction lag (recommendation -> sanction) on every work with both dates: percentiles, the
     share past 45 and past 75 days (the guideline clock; T001 settles which), by month.
  2. Recommendations still waiting at the snapshot, and how long they have waited.
  3. Build time (sanction -> completion) per work type: percentiles, the share done within 7 / 14 /
     30 days, done before its own sanction.
  4. Why one fixed window per type would punish good work: the spread inside a type, and inside a
     type by amount band.

Caveat printed with the numbers: build times come from works that finished by the snapshot (2 Oct
2026), so slow works are under-counted (censored). The fast end, which the "too early" question
uses, is not affected by that.

Run: apps\engine\.venv\Scripts\python.exe data\trial\four_agents_timing.py
"""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "data"))
import esakshi_dashboard  # noqa: E402

OUT = ROOT / "data" / "trial" / "results" / "four_agents_timing"
CONSTRUCTION = {"ROAD_CC", "ROAD_BT", "FOOTPATH", "DRAIN", "BOUNDARY_WALL", "COMMUNITY_HALL",
                "SCHOOL_BUILDING", "LIBRARY", "CREMATORIUM", "TOILET_BLOCK", "CULVERT",
                "CHECK_DAM", "POND", "BUS_SHELTER", "HEALTH_BUILDING"}
BANDS = [(0, 3e5, "under Rs 3 lakh"), (3e5, 10e5, "Rs 3-10 lakh"), (10e5, 1e12, "Rs 10 lakh+")]
MIN_TYPE = 30


def q(xs: list[float], p: float) -> float | None:
    """Linear-interpolated percentile, p in [0, 100]."""
    if not xs:
        return None
    s = sorted(xs)
    k = (len(s) - 1) * p / 100
    lo = int(k)
    hi = min(lo + 1, len(s) - 1)
    return round(s[lo] + (s[hi] - s[lo]) * (k - lo), 1)


def pct(n: int, d: int) -> float | None:
    return round(100 * n / d, 1) if d else None


def spread(days: list[int]) -> dict:
    return {"works": len(days), "p5": q(days, 5), "p10": q(days, 10), "median": q(days, 50),
            "p90": q(days, 90), "p95": q(days, 95)}


def main() -> None:
    works, info = esakshi_dashboard.load()
    as_of = info["as_of"]
    out: dict = {"source": "eSAKSHI public dashboard tables, downloaded 2 Oct 2026",
                 "works": info["works"], "snapshot": as_of.isoformat(),
                 "with_recommended_date": info["with_recommended_date"],
                 "with_sanction_date": info["with_sanction_date"]}

    # 1. sanction lag
    lags, bad, by_month = [], 0, defaultdict(list)
    for w in works:
        r, s = w["recommended_date"], w["sanction_date"]
        if r and s:
            d = (s - r).days
            if d < 0:
                bad += 1
                continue
            lags.append(d)
            by_month[r.strftime("%Y-%m")].append(d)
    rec_dates = [w["recommended_date"] for w in works if w["recommended_date"]]
    out["sanction_lag"] = {
        **spread(lags), "recommended_from": min(rec_dates).isoformat(),
        "recommended_to": max(rec_dates).isoformat(),
        "sanction_before_recommendation": bad,
        "same_day": sum(d == 0 for d in lags),
        "within_7_days": sum(d <= 7 for d in lags),
        "past_45_days": sum(d > 45 for d in lags), "past_45_pct": pct(sum(d > 45 for d in lags), len(lags)),
        "past_75_days": sum(d > 75 for d in lags), "past_75_pct": pct(sum(d > 75 for d in lags), len(lags)),
        "past_150_days": sum(d > 150 for d in lags),
        "by_month": {m: {"works": len(v), "median": q(v, 50), "past_75_pct": pct(sum(d > 75 for d in v), len(v))}
                     for m, v in sorted(by_month.items())},
    }

    # 2. still waiting at the snapshot
    waiting = [(as_of - w["recommended_date"]).days for w in works
               if w["status"] == "RECOMMENDED" and w["recommended_date"]]
    out["still_waiting"] = {**spread(waiting), "past_75_days": sum(d > 75 for d in waiting)}

    # 3. build time per type
    build, before_sanction = defaultdict(list), Counter()
    amounts = defaultdict(list)
    for w in works:
        s, c = w["sanction_date"], w["completed_date"]
        if not (s and c):
            continue
        t = w["work_type_code"]
        d = (c - s).days
        if d < 0:
            before_sanction[t] += 1
            continue
        build[t].append(d)
        amounts[t].append((w["amount"] or 0, d))
    all_days = [d for v in build.values() for d in v]
    out["build_time_all"] = {**spread(all_days),
                             "completed_before_own_sanction": sum(before_sanction.values()),
                             "done_within_7_days": sum(d <= 7 for d in all_days),
                             "done_within_7_pct": pct(sum(d <= 7 for d in all_days), len(all_days))}
    per_type = {}
    for t, days in sorted(build.items(), key=lambda kv: -len(kv[1])):
        if len(days) < MIN_TYPE:
            continue
        row = {**spread(days), "within_7": sum(d <= 7 for d in days),
               "within_14": sum(d <= 14 for d in days), "within_30": sum(d <= 30 for d in days),
               "within_30_pct": pct(sum(d <= 30 for d in days), len(days)),
               "before_own_sanction": before_sanction[t],
               "p90_over_p10": round(q(days, 90) / max(q(days, 10), 1), 1)}
        bands = {}
        for lo, hi, name in BANDS:
            ds = [d for a, d in amounts[t] if lo <= a < hi]
            if len(ds) >= 10:
                bands[name] = {"works": len(ds), "median": q(ds, 50), "p10": q(ds, 10), "p90": q(ds, 90)}
        row["by_amount"] = bands
        per_type[t] = row
    out["build_time_by_type"] = per_type

    # 4. one fixed "too early" line for every construction work would hit good work
    con = [(w["work_type_code"], (w["completed_date"] - w["sanction_date"]).days, w["amount"] or 0)
           for w in works if w["sanction_date"] and w["completed_date"]
           and w["work_type_code"] in CONSTRUCTION and w["completed_date"] >= w["sanction_date"]]
    out["construction_fixed_lines"] = {
        "works": len(con),
        "done_within_30_days": sum(d <= 30 for _, d, _ in con),
        "done_within_14_days": sum(d <= 14 for _, d, _ in con),
        "done_within_14_days_rs5_lakh_plus": sum(d <= 14 and a >= 5e5 for _, d, a in con),
        "done_within_7_days_rs5_lakh_plus": sum(d <= 7 and a >= 5e5 for _, d, a in con),
    }
    # 5. completion evidence today: does a completed work carry any picture at all?
    done = [w for w in works if w["status"] == "COMPLETED" and w["has_image"] is not None]
    out["completed_with_image"] = {"completed_works": len(done), "with_image": sum(w["has_image"] for w in done),
                                   "with_image_pct": pct(sum(w["has_image"] for w in done), len(done))}
    # the portal's own stages for sanctioned works (the Sanctioned table's "Work Status")
    out["dashboard_work_status"] = dict(Counter(w["dashboard_status"] for w in works
                                                if w["dashboard_status"]).most_common())
    out["caveat"] = ("Build times come from works finished by the snapshot, so slow works are under-counted; "
                     "the fast end is not affected. The dashboard's Recommended table covers recommendations "
                     f"from {out['sanction_lag']['recommended_from']} to {out['sanction_lag']['recommended_to']}.")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.with_suffix(".json").write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    lines = [f"eSAKSHI dashboard works: {out['works']:,} (snapshot {out['snapshot']})", ""]
    sl = out["sanction_lag"]
    lines += [f"SANCTION LAG ({sl['works']:,} works with both dates; recommended {sl['recommended_from']} to "
              f"{sl['recommended_to']})",
              f"  p10 / median / p90: {sl['p10']} / {sl['median']} / {sl['p90']} days",
              f"  past 45 days: {sl['past_45_days']:,} ({sl['past_45_pct']}%)   past 75 days: {sl['past_75_days']:,} "
              f"({sl['past_75_pct']}%)   past 150 days: {sl['past_150_days']:,}",
              f"  same day: {sl['same_day']:,}   within 7 days: {sl['within_7_days']:,}   "
              f"sanction dated before recommendation: {sl['sanction_before_recommendation']}", ""]
    sw = out["still_waiting"]
    lines += [f"STILL WAITING at the snapshot: {sw['works']:,} (median {sw['median']} days; past 75: "
              f"{sw['past_75_days']:,})", ""]
    ba = out["build_time_all"]
    lines += [f"BUILD TIME, sanction -> completion ({ba['works']:,} works)",
              f"  p5 / p10 / median / p90 / p95: {ba['p5']} / {ba['p10']} / {ba['median']} / {ba['p90']} / {ba['p95']} days",
              f"  done within 7 days of sanction: {ba['done_within_7_days']:,} ({ba['done_within_7_pct']}%); "
              f"completed before its own sanction: {ba['completed_before_own_sanction']}", "",
              f"  {'type':<18}{'works':>7}{'p5':>7}{'p10':>7}{'median':>8}{'p90':>7}{'p95':>7}{'<=30d':>8}"
              f"{'p90/p10':>9}"]
    for t, r in per_type.items():
        lines.append(f"  {t:<18}{r['works']:>7}{r['p5']:>7}{r['p10']:>7}{r['median']:>8}{r['p90']:>7}{r['p95']:>7}"
                     f"{r['within_30_pct']:>7}%{r['p90_over_p10']:>9}")
    lines += ["", "  by amount band (median days, p10-p90):"]
    for t, r in per_type.items():
        if len(r["by_amount"]) >= 2:
            parts = [f"{b}: {v['median']} ({v['p10']}-{v['p90']}, {v['works']})" for b, v in r["by_amount"].items()]
            lines.append(f"  {t:<18}" + " | ".join(parts))
    cf = out["construction_fixed_lines"]
    lines += ["", f"CONSTRUCTION WORKS ({cf['works']:,}): done within 30 days {cf['done_within_30_days']:,}; within 14 "
              f"{cf['done_within_14_days']:,}; within 14 at Rs 5 lakh+ {cf['done_within_14_days_rs5_lakh_plus']}; "
              f"within 7 at Rs 5 lakh+ {cf['done_within_7_days_rs5_lakh_plus']}"]
    ci = out["completed_with_image"]
    lines += ["", f"COMPLETED WORKS WITH ANY PICTURE: {ci['with_image']:,} of {ci['completed_works']:,} "
              f"({ci['with_image_pct']}%)",
              "PORTAL STAGES of sanctioned works: " + ", ".join(f"{k} {v:,}" for k, v in
                                                              out["dashboard_work_status"].items()),
              "", "CAVEAT: " + out["caveat"]]
    OUT.with_suffix(".txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
