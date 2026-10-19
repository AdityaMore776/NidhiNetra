r"""Run an agent's eval cases without Inspect AI and write a plain report (T168).

  apps\engine\.venv\Scripts\python.exe data\eval\common\report.py dup_split --label baseline
  apps\engine\.venv\Scripts\python.exe data\eval\common\report.py dup_split --set holdout --label firstrun

Writes data/trial/results/t168_<agent>_<set>_<label>.txt and .json: every case in both worlds,
its level, the codes raised, and the totals (fraud excused, honest asked, broken cleared must be 0).
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import world as W  # noqa: E402,I001  (first: it sets the paths levels.py imports from)
import levels as L  # noqa: E402

OUT = W.ROOT / "data" / "trial" / "results"
SETS = ("main", "holdout", "holdout2")


def case_sets(agent: str) -> dict[str, list[W.Case]]:
    """The agent's case files: data/eval/<agent>/cases.py (main), holdout.py, holdout2.py."""
    folder = W.ROOT / "data" / "eval" / agent
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))
    out = {}
    for name, mod in (("main", "cases"), ("holdout", "holdout"), ("holdout2", "holdout2")):
        if (folder / f"{mod}.py").exists():
            out[name] = W.load(folder / f"{mod}.py", f"{agent}_{mod}").cases()
    return out


def judge(case: W.Case, w: W.World) -> dict:
    r = W.run(case, w)
    target = case.agent
    if target == "pipeline":
        got = r.fused.band
        res = None
    else:
        res = r.results.get(target)
        got = L.level(res)
    return {"case": case.id, "world": w.name, "truth": case.truth, "family": case.family,
            "scope": case.scope, "allowed": list(case.allowed), "ideal": case.ideal, "got": got,
            "agent": target,
            "verdict": L.verdict(case.truth, case.allowed, got) if target != "pipeline"
            else L.band_verdict(case.truth, case.allowed, got),
            "codes": L.codes(res) if res else sorted(
                f"{a}:{f.code}" for a, x in r.results.items() for f in x.findings
                if f.risk >= L.FACT_RISK),
            "notes": L.codes(res, counted=False) if res else [],
            "band": r.fused.band, "score": round(r.fused.score, 3),
            "headline": (res.headline if res else "")[:240], "pair": case.pair or ""}


def totals(rows: list[dict]) -> dict:
    agg: dict[str, list[float]] = {}
    for x in rows:
        if x["scope"] != "self":
            continue
        grade = L.band_scores if x.get("agent") == "pipeline" else L.scores
        for k, v in grade(x["truth"], tuple(x["allowed"]), x["ideal"], x["got"]).items():
            if not math.isnan(v):
                agg.setdefault(k, []).append(v)
    out = {k: f"{sum(v):.0f}/{len(v)}" for k, v in agg.items()}
    out["verdicts"] = dict(Counter(x["verdict"] for x in rows if x["scope"] == "self"))
    apart = [x for x in rows if x["scope"] != "self"]
    if apart:
        out["apart"] = {f"{x['case']}@{x['world']}": f"{x['scope']}: {x['truth']} got {x['got']}"
                        for x in apart}
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("agent")
    ap.add_argument("--set", default="main", choices=SETS)
    ap.add_argument("--label", default="run")
    a = ap.parse_args()
    cases = case_sets(a.agent)[a.set]
    rows = [judge(c, W.world(n)) for c in cases for n in W.WORLDS]
    tot = totals(rows)
    lines = [f"T168 {a.agent} eval, set {a.set}, label {a.label}: {len(cases)} cases x "
             f"{len(W.WORLDS)} worlds", "totals: " + json.dumps(tot), ""]
    for x in rows:
        mark = {"pass": " ", "soft": "~", "hard": "X"}[x["verdict"]]
        notes = f" notes {','.join(x['notes'])}" if x["notes"] else ""
        apart = f" [{x['scope']}: not counted]" if x["scope"] != "self" else ""
        lines.append(f"{mark} {x['case']:28} {x['world']:6} {x['truth']:7} got {x['got']:6} "
                     f"(allowed {'/'.join(x['allowed'])}) {','.join(x['codes']) or '-'}"
                     f"{notes}{apart}")
        if x["verdict"] != "pass":
            lines.append(f"      {x['headline']}")
    text = "\n".join(lines) + "\n"
    print(text)
    stem = OUT / f"t168_{a.agent}_{a.set}_{a.label}"
    stem.with_suffix(".txt").write_text(text, encoding="utf-8")
    stem.with_suffix(".json").write_text(json.dumps({"totals": tot, "rows": rows}, indent=1,
                                                    ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
