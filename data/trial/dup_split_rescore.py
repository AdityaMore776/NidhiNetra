r"""Trial (2 Oct 2026): the T051 labelled repeat pairs, re-read by main's matcher and this one.

The pairs read by eye for T051 (dup_split_v2_labels.py: DEV1, DEV2, TEST, TEST2; "same" = one
asset funded twice, "different" = two works) are re-scored from their saved descriptions by the
pair rules of two versions of agents/dup_split/match.py: the one on the base branch (with its
generic-word list) and the working copy. Only what the CSVs carry is used: both descriptions,
the gap in days and the two amounts. The district-boilerplate step (it needs the whole district)
and the completion clock (it needs the completion date) are left out, so this measures how the
two versions read words and places, not the whole engine.

Writes results/dup_split_rescore.json: per label, the pairs, how many each version flags, and the
pairs whose answer changed (work ids only).

Run: apps\engine\.venv\Scripts\python.exe data\trial\dup_split_rescore.py [--base origin/main]
"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import subprocess
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "apps" / "engine"))

from drishti.agents.dup_split import match as new  # noqa: E402

OUT = ROOT / "data" / "trial" / "results"
FILES = {"DEV1": "dup_split_v2_pairs_dev1.csv", "DEV2": "dup_split_v2_pairs_dev2.csv",
         "TEST": "dup_split_v2_pairs_test.csv", "TEST2": "dup_split_v2_pairs_test2.csv"}


def git_show(base: str, path: str) -> str:
    return subprocess.run(["git", "show", f"{base}:{path}"], cwd=ROOT, capture_output=True,
                          text=True, encoding="utf-8", check=True).stdout


def base_matcher(base: str) -> types.ModuleType:
    """match.py as it stands on the base branch, reading the base branch's generic words."""
    src = git_show(base, "apps/engine/drishti/agents/dup_split/match.py")
    old = types.ModuleType("base_match")
    sys.modules["base_match"] = old
    exec(compile(src, "base_match", "exec"), old.__dict__)
    words = git_show(base, "apps/engine/drishti/reference/generic_words.txt")
    generic = frozenset(x.strip() for x in words.splitlines()
                        if x.strip() and not x.startswith("#"))
    old.generic_words = lambda: generic
    return old


def flagged(m: types.ModuleType, r: dict) -> bool:
    a, b = r["desc_a"], r["desc_b"]
    pa, pb = m.place_words(a), m.place_words(b)
    if not pa or not pb:
        return False
    na, nb = m.site_numbers(a), m.site_numbers(b)
    if na and nb and na != nb:
        return False
    if hasattr(m, "segment"):                    # numbered pieces (2 Oct 2026)
        ga, gb = m.segment(a), m.segment(b)
        if ga and gb and ga != gb:
            return False
    sa, sb = m.sides(a), m.sides(b)
    if sa and sb and sa != sb:
        return False
    t = m.text_sim(a, b)
    if t < m.TEXT_MIN:
        return False
    p = m.place_agreement(pa, pb)
    if p < m.PLACE_MIN:
        return False
    gap = int(float(r["gap_days"]))
    x, y = float(r["amount_a"]), float(r["amount_b"])
    diff = abs(x - y) / max(x, y, 1.0)
    score = (0.5 * t + 0.2 * p / 100 + 0.15 * max(0.0, 1 - gap / 730)
             + 0.15 * max(0.0, 1 - diff / m.AMOUNT_TOL))
    return score >= m.FLAG


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="origin/main")
    args = ap.parse_args()
    old = base_matcher(args.base)
    spec = importlib.util.spec_from_file_location(
        "labels", ROOT / "data" / "trial" / "dup_split_v2_labels.py")
    labels = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(labels)
    totals: dict[str, dict[str, int]] = {}
    changed = []
    for sample, name in FILES.items():
        lab = getattr(labels, sample)
        with (OUT / name).open(encoding="utf-8") as f:
            for r in csv.DictReader(f):
                verdict = lab.get((r["a"], r["b"])) or lab.get((r["b"], r["a"]))
                if not verdict:
                    continue
                o, n = flagged(old, r), flagged(new, r)
                t = totals.setdefault(verdict, {"pairs": 0, "flagged_base": 0,
                                                "flagged_branch": 0})
                t["pairs"] += 1
                t["flagged_base"] += o
                t["flagged_branch"] += n
                if o != n:
                    changed.append({"sample": sample, "a": r["a"], "b": r["b"],
                                    "label": verdict, "base": o, "branch": n})
    res = {"base": args.base, "by_label": totals, "changed": changed}
    for v in res["by_label"].values():
        v["share_flagged_base"] = round(v["flagged_base"] / v["pairs"], 3)
        v["share_flagged_branch"] = round(v["flagged_branch"] / v["pairs"], 3)
    (OUT / "dup_split_rescore.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
