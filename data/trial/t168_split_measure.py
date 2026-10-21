r"""T168: how often would a looser split rule fire on the real works? (plan docs/plans/T168-agent-evals.md)

The eval found two ways past Duplicate Work's strictest split (every piece 96-100% of a limit,
recommended within 30 days): pieces at 95% of the limit, and pieces 35 days apart. Before any
"check this" tier is added for them, this counts the groups each rule finds on the research
export's 2,09,993 real works (no forms: groups by wording, repeat.split_groups as the engine runs
it), and prints a fixed random sample of the new groups (seed 0) to read by eye.

  apps\engine\.venv\Scripts\python.exe data\trial\t168_split_measure.py

Writes data/trial/results/t168_split_measure.txt.
"""

from __future__ import annotations

import math
import random
import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "apps" / "engine"))
from drishti.agents.dup_split.match import _count_copies, _localise  # noqa: E402
from drishti.agents.dup_split.repeat import Rec, loose_split_groups, split_groups  # noqa: E402

OUT = ROOT / "data" / "trial" / "results" / "t168_split_measure.txt"
RULES = {"strict (96%, 30 days)": (0.96, 30), "share 90%, 30 days": (0.90, 30),
         "96%, 90 days": (0.96, 90), "share 90%, 90 days": (0.90, 90)}


def _clean(r: dict) -> dict:
    return {k: (None if (isinstance(v, float) and math.isnan(v)) or v is pd.NaT else v)
            for k, v in r.items()}


def main() -> None:
    w = pd.read_parquet(ROOT / "data" / "build" / "works.parquet")
    by: dict[str, list[Rec]] = defaultdict(list)
    for r in w.to_dict("records"):
        x = Rec.of(_clean(r))
        if x is not None:
            by[x.district].append(x)
    for recs in by.values():
        _localise(recs)
        _count_copies(recs)
    found: dict[str, dict[str, dict]] = {}
    for name, (share, gap) in RULES.items():
        groups = {}
        for recs in by.values():
            for g in split_groups(recs, share, gap).values():
                groups[g["group_id"]] = g
        found[name] = groups
    desc = {x.work_id: x for recs in by.values() for x in recs}
    lines = [f"{len(w):,} works, {sum(len(v) for v in by.values()):,} comparable, "
             f"{len(by)} districts", ""]
    strict = found["strict (96%, 30 days)"]
    for name, groups in found.items():
        works = sum(g["size"] for g in groups.values())
        lines.append(f"{name:24} {len(groups):5} groups {works:6} works "
                     f"({len(set(groups) - set(strict))} groups new against strict)")
    engine: dict[str, dict] = {}
    for recs in by.values():
        for g in loose_split_groups(recs, split_groups(recs)).values():
            engine[g["group_id"]] = g
    lines += ["", f"the engine's T168 rule (SPLIT_NEAR_LIMIT, check this): {len(engine)} groups, "
                  f"{sum(g['size'] for g in engine.values())} works"]
    for name in ("share 90%, 30 days", "96%, 90 days"):
        new = sorted(set(found[name]) - set(strict))
        sample = random.Random(0).sample(new, min(20, len(new)))
        lines += ["", f"--- {name}: a sample of {len(sample)} of the {len(new)} new groups"]
        for gid in sample:
            g = found[name][gid]
            lines.append(f"{gid} {g['kind']} size {g['size']} days {g['days']} limit "
                         f"{g['limit']:,.0f} amounts {[round(a) for a in g['amounts']]}")
            for wid in g["members"]:
                x = desc[wid]
                lines.append(f"    {x.rec} {x.work_type:10} {x.description[:110]}")
    text = "\n".join(lines) + "\n"
    OUT.write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
