r"""Build the Cost Estimate engine's price reference for one state (T097).

Reads the eSAKSHI dashboard tables (data/raw/esakshi_dashboard, from the team pack) and writes
apps/engine/drishti/reference/cost/<state>.json: per group of the same kind and specification
(a solar street light, a high mast, a CC road per metre, ...), the 10th / 50th / 90th / 98th
percentile of price per unit for the state and each district with 30+ works, and whether the
group is tight enough to compare with (agents/cost_estimate/reference.py explains the rules).
Aggregates only: no description, name or work id is written, so the file is committed.

Run:  apps\engine\.venv\Scripts\python.exe data\build_cost_reference.py [--state "Uttar Pradesh"]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "data"))
sys.path.insert(0, str(ROOT / "apps" / "engine"))
from esakshi_dashboard import load  # noqa: E402

from drishti.agents.cost_estimate import reference  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", default="Uttar Pradesh")
    args = ap.parse_args()
    works, info = load()
    ref = reference.build(works, args.state,
                          f"eSAKSHI dashboard tables, as of {info['as_of']}")
    reference.DIR.mkdir(parents=True, exist_ok=True)
    path = reference.DIR / f"{reference.slug(args.state)}.json"
    path.write_text(json.dumps(ref, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{args.state}: years {ref['years']}")
    for key, g in ref["groups"].items():
        st = g["state"]
        state_ok = st["tight"] and st["n"] >= ref["min_works"]
        used = [f"{d} ({v['n']})" for d, v in g["districts"].items() if v["tight"]]
        loose = [f"{d} ({v['n']})" for d, v in g["districts"].items() if not v["tight"]]
        print(f"  {key:24} {g['unit']:10} n={st['n']:4}  median {st['median']:>9,}  "
              f"p90 {st['p90']:>9,}  p98 {st['p98']:>9,}  state: "
              f"{'USED' if state_ok else 'not used'}; districts used: {', '.join(used) or '-'}"
              f"{'; too loose: ' + ', '.join(loose) if loose else ''}")
    print("A group is compared with a form only when it is tight and priced in the form's own "
          "unit of size (a road priced per m2 is never compared with roads per metre).")
    print(f"wrote {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
