"""Builds the downloadable SiteClaim test package (T155): every real photo the judges saw, the
eye-checked labels, each judge's exact answers, the exact prompts and the photo sources.

    python scripts/make_release.py <out_dir>

Reads NN_DATA (default D:/nidhinetra-data). No work names or other text from the government
records go in (they may name a beneficiary): only the public asset id, district code, work type,
the claim the benchmark wrote, and the label.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from drishti_vision import flagship_other  # noqa: E402
from drishti_vision.vlmdata import SYSTEM, read_items, user_prompt  # noqa: E402

DATA = Path(os.environ.get("NN_DATA", "D:/nidhinetra-data"))
JUDGES = {    # folder under runs/modal -> (name in the package, what it is)
    "ours4b": ("ours_4b", "Qwen3-VL-4B-Instruct + our LoRA (SFT, real photos only), 512 px"),
    "ours2b": ("ours_2b", "Qwen3-VL-2B-Instruct + our LoRA (SFT), 512 px"),
    "gem_pro31_batch": ("gemini_3_1_pro_plain", "Gemini 3.1 Pro, full-resolution photos, "
                                                "the same prompt as ours (Batch API)"),
    "gem_pro31_rules": ("gemini_3_1_pro_rules", "Gemini 3.1 Pro, full-resolution photos, our "
                                                "prompt + the task rules (Batch API)"),
    "base4b_v6": ("qwen3_vl_4b_untrained", "Qwen3-VL-4B-Instruct, no fine-tuning"),
    "base2b_v6": ("qwen3_vl_2b_untrained", "Qwen3-VL-2B-Instruct, no fine-tuning"),
}
KEEP = ("id", "split", "source", "site", "district", "work_type", "claim", "claim_kind",
        "lang", "trick", "real")


def main() -> None:
    out = Path(sys.argv[1])
    if out.exists():
        shutil.rmtree(out)
    (out / "predictions").mkdir(parents=True)
    test = [i for i in read_items(DATA / "vlm/v6/items_eye3.jsonl") if i.split == "test"]
    probe = read_items(DATA / "vlm/v6/probe_eye.jsonl")
    files = set()
    for name, its in (("test", test), ("probe", probe)):
        with open(out / f"items_{name}.jsonl", "w", encoding="utf-8") as f:
            for it in its:
                d = {k: getattr(it, k) for k in KEEP}
                d["image_a"] = "images/" + it.image_a
                d["image_b"] = "images/" + it.image_b
                d["label"] = it.target["verdict"]
                d["reference_answer"] = it.target
                d["label_checked_by_eye"] = it.label_check == "eye"
                f.write(json.dumps(d, ensure_ascii=False) + "\n")
                files |= {it.image_a, it.image_b}
    for rel in sorted(files):
        dst = out / "images" / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(DATA / rel, dst)
    ids = {"test": {i.id for i in test}, "probe": {i.id for i in probe}}
    for folder, (name, _) in JUDGES.items():
        for split in ("test", "probe"):
            src = DATA / "runs/modal" / folder / f"{split}.jsonl"
            if not src.exists():
                continue
            rows = [json.loads(x) for x in src.read_text(encoding="utf-8").splitlines() if x]
            rows = [{k: r.get(k) for k in ("id", "truth", "pred", "conf", "seconds", "usage",
                                            "served_by", "text")}
                    for r in rows if r["id"] in ids[split]]
            (out / "predictions" / f"{name}_{split}.jsonl").write_text(
                "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows),
                encoding="utf-8")
    example = test[0]
    (out / "PROMPTS.md").write_text(
        "# The exact prompts\n\nEvery judge got the two photos, labelled 'Photo A (last visit):' "
        "and 'Photo B (this visit):', then the question below.\n\n## System text (all judges)\n\n"
        f"```\n{SYSTEM}\n```\n\n## Extra system text (Gemini 'rules' only)\n\n"
        f"```\n{flagship_other.RULES}\n```\n\n## Question (example: item {example.id})\n\n"
        f"```\n{user_prompt(example.work_type, example.claim, example.claim_kind)}\n```\n",
        encoding="utf-8")
    man = {json.loads(x)["id"]: json.loads(x) for x in
           (DATA / "videos/manifest_yt.jsonl").read_text(encoding="utf-8").splitlines() if x}
    # images/vlm/v6/frames/<build>/<video id>-s<shot>/fNNN.jpg
    vids = sorted({f.split("/")[4].rsplit("-s", 1)[0] for f in files if "/frames/" in f})
    lines = ["# Where the photos come from", "",
             "- **GeoMGNREGA** (images/gov/mgnrega/photos/<asset id>/): the stage photos (1 "
             "before, 2 during, 3 after) that Indian MGNREGA works publish on ISRO's public "
             "Bhuvan portal (bhuvan-app2.nrsc.gov.in/mgnrega). Fetched at one request every "
             "1.5 s. The asset id is Bhuvan's.",
             "- **Timelapse frames** (images/vlm/v6/frames/...): frames from these YouTube "
             "videos, each under the Creative Commons Attribution licence (CC BY), as read from "
             "its own page:", ""]
    for v in vids:
        m = man.get(v, {})
        lines.append(f"  - {m.get('url', v)} by {m.get('attribution', '?')} "
                     f"({m.get('licence', '?')})")
    (out / "ATTRIBUTION.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(len(test), "test items,", len(probe), "probe items,", len(files), "photos,",
          len(vids), "videos")


if __name__ == "__main__":
    main()
