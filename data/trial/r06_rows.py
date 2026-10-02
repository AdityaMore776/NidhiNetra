r"""R06 (recorded complete before it was recommended) on the hosted database: how often it
fires, and up to 20 cases to read by eye (T056 follow-up).

R06 is the one rule breach still counted at the 1-in-4 prior (reference/reliability.json). A
first look at the stored findings in the Supabase editor returned 3 flags, but the batch stores
the full findings only for HIGH and CRITICAL works (migration 003: LOW and MEDIUM rows are
"compact", rebuilt when opened), and R06 alone is MEDIUM at most. So the stored findings cannot
count R06. This script counts from the works table (completion date 7+ days before the
recommendation date, the rule's condition) and re-runs R06's own check on every case with the
stored quarter and office rates, exactly as the batch does.

Prints counts and up to 20 cases in a fixed random order, as plain lines to copy from the terminal.
Descriptions and office names are masked (validation/pii.py) and only printed: nothing carrying a
description is saved. The counts go to results/r06_hosted.json.

Second run (T056, after 10 of the 21 MEDIUM cases were read): --medium 21 prints every MEDIUM case
in the same fixed order (the first 10 are the ones already read), and the counts gain a table by
state and, for Kerala (8 of the first 10), by office: is "completed before recommended" a state's
recording habit rather than a question about each work?

Run:  apps\engine\.venv\Scripts\python.exe data\with_env.py trial\r06_rows.py --medium 21
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "apps" / "engine"))
from drishti.agents.statistical.cohort import StatsStore  # noqa: E402
from drishti.validation.pii import mask  # noqa: E402
from drishti.validation.timeline import MIN_GAP_DAYS, impossible_date  # noqa: E402

OUT = ROOT / "data" / "trial" / "results" / "r06_hosted.json"
MEDIUM_FROM = 0.30          # compliance/agent.py: R06 is MEDIUM at risk >= 0.30, else LOW

COUNTS = f"""
SELECT count(*) AS works,
       count(*) FILTER (WHERE recommended_date IS NOT NULL AND completed_date IS NOT NULL)
           AS with_both_dates,
       count(*) FILTER (WHERE completed_date <= recommended_date - {MIN_GAP_DAYS})
           AS completed_before_recommended
FROM works
"""
CASES = f"""
SELECT w.work_id, w.status, w.work_type_code, w.amount, w.recommended_date,
       w.completed_date, w.sanction_date, w.state_name, w.district_name, w.agency_name,
       w.description,
       a.band, a.compact
FROM works w
LEFT JOIN assessments a USING (work_id)
WHERE w.completed_date <= w.recommended_date - {MIN_GAP_DAYS}
ORDER BY md5(w.work_id)
"""
# the denominators: works with both dates, by state and (for the state asked about) by office
BOTH_BY_STATE = """
SELECT coalesce(state_name, '?') AS state, count(*) AS n FROM works
WHERE recommended_date IS NOT NULL AND completed_date IS NOT NULL GROUP BY 1
"""
BOTH_BY_OFFICE = """
SELECT coalesce(agency_name, '?') AS office, count(*) AS n FROM works
WHERE recommended_date IS NOT NULL AND completed_date IS NOT NULL AND state_name ILIKE %s
GROUP BY 1
"""


def judge(r: dict, timeline) -> tuple[str, str]:
    """R06's answer for this work, as the batch gives it: severity and why."""
    imp = impossible_date(r["recommended_date"], r["completed_date"], r["agency_name"], timeline)
    if imp is None:
        return "none", "-"
    why = ("office habit" if "This office recorded" in imp.message
           else "bulk-entry quarter" if "bulk entry of works" in imp.message
           else "no rates loaded" if timeline is None else "stands out")
    return ("MEDIUM" if imp.risk >= MEDIUM_FROM else "LOW"), why


def _line(r: dict, sev: str, why: str) -> str:
    gap = (r["recommended_date"] - r["completed_date"]).days
    amount = f"Rs {float(r['amount']) / 1e5:.2f} lakh" if r["amount"] is not None else "no amount"
    desc = " ".join((mask(r["description"]) or "").split())[:160]
    office = " ".join((mask(r["agency_name"]) or "").split())[:60]
    return (f"{r['work_id']} | {r['status']} | {r['work_type_code']} | {amount} | "
            f"recommended {r['recommended_date']} | completed {r['completed_date']} "
            f"({gap} days before) | sanctioned {r['sanction_date']} | {r['district_name']} | "
            f"office: {office} | R06 {sev} ({why}) | band {r['band']} | {desc}")


def _table(judged, key, both: dict) -> list[dict]:
    rows = {}
    for r, sev, why in judged:
        k = r[key] or "?"
        row = rows.setdefault(k, {key: k, "with_both_dates": int(both.get(k, 0)), "cases": 0,
                                  "medium": 0, "office_habit": 0, "bulk_entry": 0})
        row["cases"] += 1
        row["medium"] += sev == "MEDIUM"
        row["office_habit"] += why == "office habit"
        row["bulk_entry"] += why == "bulk-entry quarter"
    for row in rows.values():
        n = row["with_both_dates"]
        row["share_pct"] = round(100 * row["cases"] / n, 2) if n else None
    return sorted(rows.values(), key=lambda x: (-x["cases"], str(x[key])))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--medium", type=int, default=10, help="MEDIUM cases to print")
    ap.add_argument("--others", type=int, default=10, help="other cases to print")
    ap.add_argument("--state", default="kerala", help="state whose offices to break down")
    args = ap.parse_args()
    url = os.environ["DATABASE_URL"]
    try:
        timeline = StatsStore.load(url).timeline
    except Exception as exc:                    # noqa: BLE001  (say so, judge without rates)
        print(f"could not load the timeline rates ({type(exc).__name__}); judging without them")
        timeline = None
    with psycopg.connect(url, prepare_threshold=None, row_factory=dict_row) as con:
        counts = con.execute(COUNTS).fetchone()
        cases = con.execute(CASES).fetchall()
        by_state = {r["state"]: r["n"] for r in con.execute(BOTH_BY_STATE).fetchall()}
        by_office = {r["office"]: r["n"] for r in con.execute(BOTH_BY_OFFICE,
                                                              (args.state,)).fetchall()}
    judged = [(r, *judge(r, timeline)) for r in cases]
    in_state = [j for j in judged if (j[0]["state_name"] or "").lower() == args.state.lower()]
    out = {"counts": {k: int(v) for k, v in counts.items()},
           "r06_by_severity": dict(Counter(sev for _r, sev, _w in judged)),
           "r06_by_reason": dict(Counter(f"{sev} {why}" for _r, sev, why in judged)),
           "bands_of_these_works": dict(Counter(str(r["band"]) for r, _s, _w in judged)),
           "stored_in_full": sum(1 for r, _s, _w in judged if r["compact"] is False),
           "timeline_rates_loaded": timeline is not None,
           "min_gap_days": MIN_GAP_DAYS,
           "national_share_pct": round(100 * int(counts["completed_before_recommended"])
                                       / max(1, int(counts["with_both_dates"])), 2),
           "by_state": _table(judged, "state_name", by_state),
           f"{args.state}_offices": _table(in_state, "agency_name", by_office)}
    OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items() if k not in ("by_state",
                      f"{args.state}_offices")}, indent=2))
    print(f"\nBy state (works with both dates, cases {MIN_GAP_DAYS}+ days early, share, MEDIUM):")
    for row in out["by_state"]:
        print(f"  {row['state_name']} | {row['with_both_dates']} | {row['cases']} | "
              f"{row['share_pct']}% | MEDIUM {row['medium']} | office habit {row['office_habit']}"
              f" | bulk entry {row['bulk_entry']}")
    print(f"\n{args.state.title()} by office:")
    for row in out[f"{args.state}_offices"]:
        print(f"  {mask(row['agency_name'])} | {row['with_both_dates']} | {row['cases']} | "
              f"{row['share_pct']}% | MEDIUM {row['medium']}")
    medium = [j for j in judged if j[1] == "MEDIUM"][:args.medium]
    others = [j for j in judged if j[1] != "MEDIUM"][:args.others]
    print(f"\n{len(medium)} MEDIUM and {len(others)} other of {len(judged)} works recorded "
          f"complete {MIN_GAP_DAYS}+ days before their recommendation (fixed random order):")
    for r, sev, why in medium + others:
        print(_line(r, sev, why))
    print(f"\ncounts saved to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
