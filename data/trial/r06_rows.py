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

Run:  apps\engine\.venv\Scripts\python.exe data\with_env.py trial\r06_rows.py
"""

from __future__ import annotations

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
       w.completed_date, w.sanction_date, w.district_name, w.agency_name, w.description,
       a.band, a.compact
FROM works w
LEFT JOIN assessments a USING (work_id)
WHERE w.completed_date <= w.recommended_date - {MIN_GAP_DAYS}
ORDER BY md5(w.work_id)
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


def main() -> None:
    url = os.environ["DATABASE_URL"]
    try:
        timeline = StatsStore.load(url).timeline
    except Exception as exc:                    # noqa: BLE001  (say so, judge without rates)
        print(f"could not load the timeline rates ({type(exc).__name__}); judging without them")
        timeline = None
    with psycopg.connect(url, prepare_threshold=None, row_factory=dict_row) as con:
        counts = con.execute(COUNTS).fetchone()
        cases = con.execute(CASES).fetchall()
    judged = [(r, *judge(r, timeline)) for r in cases]
    out = {"counts": {k: int(v) for k, v in counts.items()},
           "r06_by_severity": dict(Counter(sev for _r, sev, _w in judged)),
           "r06_by_reason": dict(Counter(f"{sev} {why}" for _r, sev, why in judged)),
           "bands_of_these_works": dict(Counter(str(r["band"]) for r, _s, _w in judged)),
           "stored_in_full": sum(1 for r, _s, _w in judged if r["compact"] is False),
           "timeline_rates_loaded": timeline is not None,
           "min_gap_days": MIN_GAP_DAYS}
    OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out, indent=2))
    shown = [j for j in judged if j[1] == "MEDIUM"][:10] + [j for j in judged if j[1] != "MEDIUM"][:10]
    print(f"\n{len(shown)} of {len(judged)} works recorded complete {MIN_GAP_DAYS}+ days before "
          "their recommendation (fixed random order; up to 10 MEDIUM first, then up to 10 others):")
    for r, sev, why in shown:
        print(_line(r, sev, why))
    print(f"\ncounts saved to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
