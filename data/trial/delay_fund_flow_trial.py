r"""Delay & Fund Flow engine (T410) on every real work: does Fund Flow reproduce FINDINGS C2?

Target (results/fund_flow_trial.json): 3,331 works of the 17th Lok Sabha still waiting for
sanction (Rs 168.9 crore). Also counts the office-backlog facts and writes 15 of them, at
random, for reading by eye. Writes results/delay_fund_flow.json.
Run: apps\engine\.venv\Scripts\python.exe data\trial\delay_fund_flow_trial.py
"""

from __future__ import annotations

import json
import random
import sys
from collections import Counter
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "data"))
from common import BUILD, load_context, works_records  # noqa: E402
from drishti.agents.delay.agent import assess  # noqa: E402

OUT = ROOT / "data" / "trial" / "results"


def main() -> None:
    works = pd.read_parquet(BUILD / "works.parquet")
    ctx = load_context(works)
    status, codes, money = Counter(), Counter(), Counter()
    backlog = []
    for w in works_records(works):
        r = assess(w, ctx.as_of, ctx.data.get("backlog"))
        status[r.status.value] += 1
        for f in r.findings:
            codes[f.code] += 1
            money[f.code] += float(w.get("amount") or 0)
            if f.code == "OFFICE_SANCTION_BACKLOG":
                backlog.append({"work_id": w["work_id"], "district": w["district_name"],
                                "text": f.text})
    random.Random(410).shuffle(backlog)
    res = {"status": dict(status), "findings": dict(codes),
           "value_cr": {k: round(v / 1e7, 1) for k, v in money.items()},
           "offices_flagged": len({b["text"].split(";")[0] for b in backlog}),
           "target_term_ended_works": 3331, "target_term_ended_value_cr": 168.9,
           "backlog_sample_for_reading": backlog[:15]}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "delay_fund_flow.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in res.items() if k != "backlog_sample_for_reading"},
                     indent=2))
    for b in backlog[:15]:
        print(b["work_id"], b["district"], "|", b["text"])


if __name__ == "__main__":
    main()
