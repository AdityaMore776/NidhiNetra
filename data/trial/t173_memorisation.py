r"""T173 part 1: did NidhiLens memorise its training items, or does it read the photos? (plan docs/plans/T173-photo-only-progress.md)

Training loss reached 0.02 by step 70 of 731, so the adapter may have learned its 2,924 training
items by heart. Probe: 40 training items (one a site, seed 0) whose answer is "open ground in A,
finished work in B, shown". Each is asked twice:
  as trained   -> it should say shown (it saw this exact item);
  photos swapped (B before A) -> a model that reads the photos says not_shown (B is less built);
  a model that memorised the item repeats "shown", often with the training reason word for word.

  D:\nidhinetra-data\venv\Scripts\python.exe data\trial\t173_memorisation.py

Writes data/trial/results/t173_memorisation.txt (+ .jsonl with every answer).
"""

from __future__ import annotations

import dataclasses
import json
import os
import random
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
os.environ.setdefault("HF_HOME", r"D:\nidhinetra-data\hf-cache")    # the model is there; C: is full
sys.path.insert(0, str(ROOT / "apps" / "vision"))
from drishti_vision import vlm
from drishti_vision.vlmdata import read_items

DATA = Path(r"D:\nidhinetra-data")
TRAIN_FILE = DATA / "vlm" / "v6" / "items_eye.jsonl"
ADAPTER = DATA / "models" / "q4b" / "final"
BASE = "Qwen/Qwen3-VL-4B-Instruct"
OUT = ROOT / "data" / "trial" / "results" / "t173_memorisation.txt"
N = 40


def pick() -> list:
    its = [i for i in read_items(TRAIN_FILE) if i.split == "train" and i.real
           and i.target.get("verdict") == "shown" and i.target.get("stage_A") == "not started"
           and i.target.get("stage_B") == "complete" and i.claim_kind == "period"]
    rng = random.Random(0)
    rng.shuffle(its)
    seen, out = set(), []
    for i in its:
        if i.site not in seen:
            seen.add(i.site)
            out.append(i)
    return out[:N]


def main() -> None:
    chosen = pick()
    L = vlm.load(BASE, quant4=True, adapter=str(ADAPTER))
    rows = []
    for k, it in enumerate(chosen):
        sw = dataclasses.replace(it, image_a=it.image_b, image_b=it.image_a)
        for mode, item in (("as trained", it), ("swapped", sw)):
            o = vlm.judge(L, item, DATA)
            a = o["answer"] or {}
            rows.append({"id": it.id, "site": it.site, "mode": mode, "verdict": a.get("verdict"),
                         "stage_A": a.get("stage_A"), "stage_B": a.get("stage_B"),
                         "reason": a.get("reason"), "train_reason": it.target["reason"]})
        print(f"{k + 1}/{len(chosen)}", flush=True)
    OUT.with_suffix(".jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")

    lines = [f"T173 memorisation probe: {len(chosen)} training items (one a site, seed 0), "
             "trained answer = A not started, B complete, shown", ""]
    for mode in ("as trained", "swapped"):
        rs = [r for r in rows if r["mode"] == mode]
        same_reason = sum((r["reason"] or "").strip() == r["train_reason"].strip() for r in rs)
        lines.append(f"{mode}: verdicts {dict(Counter(r['verdict'] for r in rs))}"
                     f" | stage_B {dict(Counter(r['stage_B'] for r in rs))}"
                     f" | training reason word for word {same_reason}/{len(rs)}")
    sw = [r for r in rows if r["mode"] == "swapped"]
    lines.append("")
    lines.append(f"Swapped photos read as going backwards (not_shown): "
                 f"{sum(r['verdict'] == 'not_shown' for r in sw)}/{len(sw)}; "
                 f"memorised answer kept (shown + training reason): "
                 f"{sum(r['verdict'] == 'shown' and (r['reason'] or '').strip() == r['train_reason'].strip() for r in sw)}"
                 f"/{len(sw)}")
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
