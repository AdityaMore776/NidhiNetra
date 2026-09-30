r"""Trial 10 (T011, 30 Sept 2026) - the Guideline Compliance engine on every real work.

For each rule R01-R11: how many works break it, at which severity, and a sample of five
per rule to read by eye (written to results/compliance_sample.json). Rules the public
export cannot check are counted as "not checkable", never as passed.

Run:  apps\engine\.venv\Scripts\python.exe data\trial\compliance_trial.py
"""

from __future__ import annotations

import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "data"))

from common import BUILD, load_context, works_records  # noqa: E402
from drishti.agents.compliance.agent import assess, rules  # noqa: E402

OUT = ROOT / "data" / "trial" / "results"


def main() -> None:
    works = pd.read_parquet(BUILD / "works.parquet")
    ctx = load_context()
    per_rule: Counter = Counter()
    per_sev: Counter = Counter()
    top_sev: Counter = Counter()
    examples: dict[str, list] = defaultdict(list)
    statuses: Counter = Counter()
    for w in works_records(works):
        r = assess(w, ctx.as_of, ctx.stats.p98(w.get("work_type_code")), ctx.stats.timeline)
        statuses[r.status.value] += 1
        sevs = set()
        for f in r.findings:
            key = (f.evidence["rule"], f.evidence["severity"])
            per_sev[key] += 1
            sevs.add(f.evidence["severity"])
            examples[f.evidence["rule"]].append({"work_id": w["work_id"], "text": f.text,
                                                 "description": str(w["description"])[:200]})
        for rule in set(r.evidence.get("rules_broken", [])):
            per_rule[rule] += 1
        top = "HIGH" if "HIGH" in sevs else "MEDIUM" if "MEDIUM" in sevs else \
            "LOW" if "LOW" in sevs else "none"
        top_sev[top] += 1
    n = len(works)
    rng = random.Random(30)
    sample = {k: rng.sample(v, min(5, len(v))) for k, v in sorted(examples.items())}
    result = {
        "works": n, "status": dict(statuses),
        "works_breaking_rule": {k: {"works": per_rule[k], "share": round(per_rule[k] / n, 4),
                                    "title": rules()[k]["title"]} for k in sorted(per_rule)},
        "findings_by_rule_and_severity": {f"{k[0]} {k[1]}": v for k, v in sorted(per_sev.items())},
        "works_by_highest_severity": dict(top_sev),
        "not_checkable": [k for k, v in rules().items() if not v["evaluable"]],
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "compliance_trial.json").write_text(json.dumps(result, indent=2, ensure_ascii=False),
                                               encoding="utf-8")
    (OUT / "compliance_sample.json").write_text(json.dumps(sample, indent=2, ensure_ascii=False),
                                                encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
