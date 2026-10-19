r"""Run the Cost agent's eval cases without Inspect (T167): the same cases, a plain report.

  apps\engine\.venv\Scripts\python.exe data\eval\cost\run.py [--label baseline] [--only id,...]

Writes data/trial/results/t167_cost_eval_<label>.{txt,json}. The Inspect task (task.py) runs the
same cases with Inspect's log and viewer.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cases as C  # noqa: E402
import levels as L  # noqa: E402

OUT = C.ROOT / "data" / "trial" / "results"


def run(only: set[str] | None = None) -> list[dict]:
    worlds = {name: C.build_world(name, spread, seed)
              for name, (spread, seed) in C.WORLDS.items()}
    rows = []
    for case in C.cases():
        if only and case.id not in only:
            continue
        for name, world in worlds.items():
            r = case.run(world)
            got = L.level(r)
            rows.append({"id": case.id, "family": case.family, "truth": case.truth,
                         "scope": case.scope, "pair": case.pair, "world": name,
                         "ideal": case.ideal, "allowed": list(case.allowed), "level": got,
                         "verdict": L.verdict(case.truth, case.allowed, got),
                         "codes": sorted(f.code for f in r.findings if f.risk > 0),
                         "headline": r.headline[:300],
                         "gap_share": (r.evidence.get("whole") or {}).get("gap_share"),
                         "leeway": r.evidence.get("leeway")})
    return rows


def summary(rows: list[dict]) -> list[str]:
    scored = [x for x in rows if x["scope"] == "cost"]
    lines = []
    by = defaultdict(Counter)
    for x in scored:
        by[x["truth"]][x["verdict"]] += 1
    n = len(scored)
    lines.append(f"{n} runs ({len({x['id'] for x in scored})} cases x {len(C.WORLDS)} worlds); "
                 f"pass {sum(x['verdict'] == 'pass' for x in scored)}, "
                 f"soft {sum(x['verdict'] == 'soft' for x in scored)}, "
                 f"hard {sum(x['verdict'] == 'hard' for x in scored)}")
    fr = [x for x in scored if x["truth"] == "fraud"]
    hon = [x for x in scored if x["truth"] != "fraud"]
    lines.append(f"frauds: {len(fr)} runs; flagged (check or ask) "
                 f"{sum(x['level'] in ('check', 'ask') for x in fr)}, asked "
                 f"{sum(x['level'] == 'ask' for x in fr)}, EXCUSED (fits/edge) "
                 f"{sum(x['level'] in ('fits', 'edge') for x in fr)}, not judged "
                 f"{sum(x['level'] == 'na' for x in fr)}")
    lines.append(f"honest + edge: {len(hon)} runs; clear (fits/edge) "
                 f"{sum(x['level'] in ('fits', 'edge') for x in hon)}, check "
                 f"{sum(x['level'] == 'check' for x in hon)}, ASKED "
                 f"{sum(x['level'] == 'ask' for x in hon)}, not judged "
                 f"{sum(x['level'] == 'na' for x in hon)}")
    lines.append(f"ideal level exact: {sum(x['level'] == x['ideal'] for x in scored)} of {n}")
    pairs = defaultdict(dict)
    rank = {"na": -1, "fits": 0, "edge": 1, "check": 2, "ask": 3}
    for x in scored:
        if x["pair"]:
            pairs[(x["pair"], x["world"])][x["truth"]] = x["level"]
    sep = [v for v in pairs.values() if "fraud" in v and len(v) == 2]
    above = sum(rank[v["fraud"]] > rank[next(lv for t, lv in v.items() if t != "fraud")]
                for v in sep)
    safe = sum(v["fraud"] in ("check", "ask") for v in sep)
    lines.append(f"look-alike pairs: fraud ranked above its honest twin in {above} of {len(sep)}; "
                 f"fraud at least 'check' in {safe} of {len(sep)}")
    other = [x for x in rows if x["scope"] != "cost"]
    if other:
        lines.append("out of the Cost agent's reach (another agent's job), not counted: "
                     + ", ".join(f"{x['id']}[{x['world']}]={x['level']}" for x in other))
    lines.append("")
    for x in rows:
        mark = {"pass": "  ok ", "soft": " soft", "hard": " HARD"}[x["verdict"]]
        lines.append(f"{mark} {x['id']:28s} {x['world']:5s} {x['truth']:6s} got {x['level']:5s} "
                     f"(ideal {x['ideal']}, allowed {'/'.join(x['allowed'])}) "
                     f"{','.join(x['codes']) or '-'}"
                     + (f"  gap {x['gap_share']:+.1%}" if isinstance(x["gap_share"], float)
                        else ""))
    return lines


def main() -> None:
    a = argparse.ArgumentParser()
    a.add_argument("--label", default="run")
    a.add_argument("--only", default="")
    args = a.parse_args()
    rows = run(set(args.only.split(",")) if args.only else None)
    text = "\n".join(summary(rows))
    print(text)
    (OUT / f"t167_cost_eval_{args.label}.txt").write_text(
        f"T167 Cost agent eval ({args.label})\n" + text + "\n", encoding="utf-8")
    (OUT / f"t167_cost_eval_{args.label}.json").write_text(
        json.dumps(rows, indent=1, ensure_ascii=False, default=str), encoding="utf-8")


if __name__ == "__main__":
    main()
