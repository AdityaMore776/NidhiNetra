r"""T173 part 2: NidhiLens with no agency text in its prompt (plan docs/plans/T173-photo-only-progress.md).

Three ways to ask the same test items, the same adapter, on this PC (4-bit, as the engine runs it):
  claim   - today: the agency's written claim goes into the prompt (the T155/T168 setting);
  fixed   - code writes the claim from the agency's pick on the form's list (photo_only.fixed_claim);
  photos  - no claim at all; the model reports same place / stage A / stage B / permanent change and
            code compares the agency's pick with it (photo_only.verdict).
The pick of each test item is read off its ladder sentence (photo_only.pick_of_claim: all 1,761 test,
fresh and probe sentences map, and code reproduces every label from the reference answers).

  D:\nidhinetra-data\venv\Scripts\python.exe data\trial\t173_photo_only.py --set test --subset 150
  D:\nidhinetra-data\venv\Scripts\python.exe data\trial\t173_photo_only.py --set test --modes photos

Resumable: one JSON line a check in D:\nidhinetra-data\runs\t173\<set>_<mode>.jsonl. Writes
data/trial/results/t173_photo_only_<set>[_<n>].txt (+ .json) with macro-F1 and the observation
accuracies against the people's reference answers.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
os.environ.setdefault("HF_HOME", r"D:\nidhinetra-data\hf-cache")    # the model is there; C: is full
sys.path.insert(0, str(ROOT / "apps" / "vision"))
from drishti_vision import photo_only as po
from drishti_vision import vlmeval

REL = Path(r"D:\nidhinetra-data\release\siteclaim_test_v1")
ADAPTER = Path(r"D:\nidhinetra-data\models\q4b\final")
BASE = "Qwen/Qwen3-VL-4B-Instruct"
RUNS = Path(r"D:\nidhinetra-data\runs\t173")
RESULTS = ROOT / "data" / "trial" / "results"
MODES = ("claim", "fixed", "photos")


def load_items(name: str, subset: int) -> list[dict]:
    its = [json.loads(x) for x in (REL / f"items_{name}.jsonl").read_text(encoding="utf-8")
           .splitlines() if x.strip()]
    if subset:                      # an equal number of each label, fixed (seed 0)
        rng = random.Random(0)
        by: dict[str, list[dict]] = {}
        for i in its:
            by.setdefault(i["label"], []).append(i)
        k = subset // len(by)
        its = [i for lab in sorted(by) for i in rng.sample(by[lab], min(k, len(by[lab])))]
    return its


def ask(it: dict, mode: str) -> dict:
    pick = po.pick_of_claim(it["claim"])
    if mode == "claim":
        return it
    if mode == "fixed":
        return it | {"claim": po.fixed_claim(it["work_type"], pick, it["claim_kind"])}
    return it | {"claim": None}


def run(L, its: list[dict], mode: str, out: Path) -> list[dict]:
    from drishti_vision import vlm
    done = {}
    if out.exists():
        for x in out.read_text(encoding="utf-8").splitlines():
            if x.strip():
                r = json.loads(x)
                done[r["id"]] = r
    with open(out, "a", encoding="utf-8") as f:
        for it in its:
            if it["id"] in done:
                continue
            o = vlm.judge(L, ask(it, mode), REL)
            pick = po.pick_of_claim(it["claim"])
            if mode == "photos":
                ob = po.parse_observation(o["text"])
                pred = po.verdict(ob, pick, it["claim_kind"]) if ob else "unreadable"
            else:
                ob = o["answer"]
                pred = ob["verdict"] if ob else "unreadable"
            r = {"id": it["id"], "site": it["site"], "trick": it["trick"], "real": it.get("real", True),
                 "ab_distance": None, "truth": it["label"], "pred": pred, "conf": None,
                 "seconds": o["seconds"], "obs": {k: (ob or {}).get(k) for k in po.FIELDS},
                 "text": o["text"][:400]}
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
            f.flush()
            done[it["id"]] = r
            if len(done) % 25 == 0:
                print(f"{mode}: {len(done)}/{len(its)}", flush=True)
    return [done[i["id"]] for i in its if i["id"] in done]


def observed(rows: list[dict], its: list[dict]) -> dict:
    """How often the model's own facts match the people's reference answer, field by field."""
    ref = {i["id"]: i["reference_answer"] for i in its}
    out = {}
    for k in po.FIELDS:
        pairs = [(str(r["obs"].get(k) or "").replace("_", " ").lower(),
                  str(ref[r["id"]][k]).replace("_", " ").lower()) for r in rows]
        known = [(p, t) for p, t in pairs if t != "unknown"]
        out[k] = round(sum(p == t for p, t in known) / len(known), 3) if known else None
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", default="test", choices=("test", "fresh", "probe"))
    ap.add_argument("--subset", type=int, default=0)
    ap.add_argument("--modes", default=",".join(MODES))
    a = ap.parse_args()
    from drishti_vision import vlm
    its = load_items(a.set, a.subset)
    RUNS.mkdir(parents=True, exist_ok=True)
    L = vlm.load(BASE, quant4=True, adapter=str(ADAPTER))
    tag = f"{a.set}_{a.subset}" if a.subset else a.set
    lines = [f"T173 photo-only: set {a.set}, {len(its)} items "
             f"(labels {dict(Counter(i['label'] for i in its))}), NidhiLens 4-bit on the RTX 3070 Ti", ""]
    res = {}
    for mode in a.modes.split(","):
        rows = run(L, its, mode, RUNS / f"{a.set}_{mode}.jsonl")
        s = vlmeval.score(rows)
        h = s["headline_real_only"]
        res[mode] = {"headline": h, "confusion": s["confusion_real"], "observed": observed(rows, its)}
        lines.append(f"{mode:7} n {len(rows)}: macro-F1 {h['macro_f1']:.3f} {h.get('macro_f1_ci')}, "
                     f"accuracy {h['accuracy']:.3f}, fooled {h['fooled_rate']}, missed {h['missed_rate']}, "
                     f"unreadable {s['unreadable_answers']}")
        lines.append(f"        facts vs people's answer: {res[mode]['observed']}")
        lines.append(f"        confusion (truth -> predicted): {s['confusion_real']}")
    (RESULTS / f"t173_photo_only_{tag}.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    (RESULTS / f"t173_photo_only_{tag}.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
