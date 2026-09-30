r"""Assess every real work locally (no database) and report what the queue would hold.

Read the top of the list by eye before trusting it: in the old build the first
ranking of every new sweep surfaced filing conventions, not problems (AD-103,
AD-106).

Run: apps\engine\.venv\Scripts\python.exe data\dry_run.py
"""

from __future__ import annotations

import time
from collections import Counter

import pandas as pd

from common import BUILD, load_context, works_records  # noqa: E402
from drishti.pipeline.orchestrator import assess_work  # noqa: E402


def main() -> None:
    works = pd.read_parquet(BUILD / "works.parquet")
    ctx = load_context()
    t0 = time.time()
    rows = []
    verdicts, bands, issues = Counter(), Counter(), Counter()
    for w in works_records(works):
        a = assess_work(w, ctx)
        stat = next(r for r in a.agents if r.agent == "statistical")
        verdicts[stat.verdict] += 1
        bands[a.fused.band] += 1
        for i in a.validation:
            issues[i.code] += 1
        rows.append((a.priority, a.fused.score, a.fused.band, w["work_id"], w["amount"],
                     w["district_name"], stat.verdict, stat.headline[:110],
                     ",".join(i.code for i in a.validation)))
    print(f"assessed {len(rows):,} works in {time.time() - t0:.0f}s")
    print("bands:", dict(bands))
    print("statistical verdicts:", dict(verdicts))
    print("validation issues:", dict(issues))
    top = sorted(rows, reverse=True)[:25]
    for r in top:
        print(f"{r[2]:6} {r[1]:.2f} p={r[0]:.2f} Rs{r[4]:>12,.0f} {r[5]!s:18} {r[6]:18} {r[8]:30} | {r[7]}")


if __name__ == "__main__":
    main()
