r"""Trial (2 Oct 2026): the T051 eligibility TEST sample, re-read by main's R07 reader and this one.

The 50 fresh works the frozen v2 reader flagged (results/eligibility_test_sample.json, read by
eye in eligibility_trial.py TEST_LABELS: "clear" = plainly prohibited, "grey" = worth a look,
anything else = a misread) are passed through the engine's reader (agents/compliance/eligibility.py
v2) as it stands on the base branch and in the working copy. A reader change should keep the clear
and grey flags and drop misreads.

Writes results/eligibility_rescore.json (sample indexes only).

Run: apps\engine\.venv\Scripts\python.exe data\trial\eligibility_rescore.py [--base origin/main]
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import types
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "apps" / "engine"))
sys.path.insert(0, str(ROOT / "data" / "trial"))

from eligibility_trial import TEST_LABELS  # noqa: E402

from drishti.agents.compliance import eligibility as new  # noqa: E402

OUT = ROOT / "data" / "trial" / "results"


def base_reader(base: str) -> types.ModuleType:
    path = "apps/engine/drishti/agents/compliance/eligibility.py"
    src = subprocess.run(["git", "show", f"{base}:{path}"], cwd=ROOT, capture_output=True,
                         text=True, encoding="utf-8", check=True).stdout
    old = types.ModuleType("base_eligibility")
    sys.modules["base_eligibility"] = old
    exec(compile(src, "base_eligibility", "exec"), old.__dict__)
    return old


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="origin/main")
    args = ap.parse_args()
    old = base_reader(args.base)
    sample = json.loads((OUT / "eligibility_test_sample.json").read_text(encoding="utf-8"))
    rows = []
    for i, (_wid, _item, desc) in enumerate(sample):
        label = TEST_LABELS.get(i, "no")
        rows.append({"index": i, "label": label, "base": old.v2(desc) is not None,
                     "branch": new.v2(desc) is not None})
    by: dict[str, Counter] = {}
    for r in rows:
        c = by.setdefault(r["label"], Counter())
        c["works"] += 1
        c["flagged_base"] += r["base"]
        c["flagged_branch"] += r["branch"]
    res = {"base": args.base, "sample": len(rows), "by_label": {k: dict(v) for k, v in by.items()},
           "changed": [r for r in rows if r["base"] != r["branch"]]}
    (OUT / "eligibility_rescore.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
