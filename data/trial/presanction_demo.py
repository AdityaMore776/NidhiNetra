r"""Demo (T064, 1 Oct 2026) - the pre-sanction check on real recommendations.

Each demo work is put through the check as it stood on the day it arrived: status not yet
sanctioned, the check's "today" = its own recommendation date, compared only with the works of
its district recommended BEFORE it (nothing from its future leaks in), exactly as the form
would have answered that day. (Re-dating a work to the data's "today" would stretch the gap to
its earlier copy and weaken the repeat score: the repeat rules weigh time.)

  ordinary   a Rs 5 lakh community hall with no earlier copy               -> expected GREEN
  refiled    a hall recommended again 225 days after an identical one      -> expected AMBER
  temple     a prohibited-work reading (Annexure-II)                       -> expected AMBER
  vague big  Rs 25 lakh "Construction of Community Hall": no place, 2.5x the
             top of the state's usual range                                -> expected RED

Writes results/presanction_demo.json (work ids and the engines' sentences only).

Run:  apps\engine\.venv\Scripts\python.exe data\trial\presanction_demo.py
"""

from __future__ import annotations

import json
import sys
from dataclasses import replace
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "data"))

from common import BUILD, clean, load_context, works_records  # noqa: E402
from drishti.agents.dup_split.match import DupIndex  # noqa: E402
from drishti.pipeline.orchestrator import assess_work  # noqa: E402
from drishti.presanction import judge  # noqa: E402

OUT = ROOT / "data" / "trial" / "results"
DEMO = {
    "ordinary": "WS/MP618/2024-2025/156175",
    "refiled": "NOREF-b14cbede407a6e",
    "temple": "WS/MP476/2024-2025/72649",
    "vague big": "NOREF-840ee6aa1b9fe3",
}


def main() -> None:
    works = pd.read_parquet(BUILD / "works.parquet")
    demo = works[works.work_id.isin(DEMO.values())]
    assert len(demo) == len(DEMO), "a demo work id is missing"
    ctx = load_context(works[~works.work_id.isin(DEMO.values())])
    out = {}
    for name, wid in DEMO.items():
        w = clean(demo[demo.work_id == wid].iloc[0].to_dict())
        rec = w["recommended_date"]
        w |= {"status": "RECOMMENDED", "completed_date": None, "signals": {}}
        before = works[(works.district_lgd == w["district_lgd"]) & (works.work_id != wid)
                       & works.recommended_date.map(lambda d, r=rec: d is not None and d < r)]
        day = replace(ctx, as_of=rec, data={**ctx.data, "dup_split": DupIndex.build(
            list(works_records(before)))})
        p = judge(assess_work(w, day))
        out[name] = {"work_id": wid, "district": w["district_name"], "checked_on": str(rec),
                     "description": str(w["description"])[:120], "amount": w["amount"],
                     "colour": p.colour, "band": p.band, "score": p.score,
                     "reasons": [f"{r['engine']}: {r['text']}" for r in p.reasons]}
        print(f"\n{name:10} {p.colour:6} {p.band:8} {w['district_name']} Rs{w['amount']:,.0f} | "
              f"{str(w['description'])[:80]}")
        for r in p.reasons:
            print(f"   - {r['engine']}: {r['text'][:200]}")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "presanction_demo.json").write_text(json.dumps(out, indent=2, default=str),
                                               encoding="utf-8")


if __name__ == "__main__":
    main()
