r"""T159: NidhiLens the way the engine runs it, on the 883 real main-test checks of the report.

The same fine-tuned 4B model, three ways:
    benchmark      the report's run: full precision, merged adapter, the original photos
                   (NidhiLens report, data/predictions/ours_4b_test.jsonl)
    bf16, frames   full precision; each photo first made into what the video job keeps of a phone
                   video (a frame 1280 px on its long side, saved as JPEG quality 80)
                   [apps/vision/modal/train_modal.py::reader_check --no-quant4]
    4-bit, frames  the same frames, with the 4-bit weights the engine's VLMReader loads (to fit
                   the team's 8 GB GPU) [reader_check]
For each: the model's raw verdict, and the verdict after the engine's own code: the answer goes
through readers.VLMReader (sure = 0.6: an unsure answer becomes "can't tell") and video.visit's
_answer, exactly as the video job judges one spot. Scored as the report scores (vlmeval._rates on
real items, bootstrap by site, McNemar against the benchmark's raw verdicts).

    apps\engine\.venv\Scripts\python.exe data\trial\t159_reader.py --q4 Q4.jsonl --bf16 BF16.jsonl

Writes data/trial/results/t159_reader.txt and .json. No model runs here: the answers come from
the Modal runs (GPU) and the report's files.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "apps" / "engine"))
sys.path.insert(0, str(ROOT / "apps" / "vision"))

from drishti.agents.site_progress.readers import VLMReader
from drishti.video.visit import _answer
from drishti_vision import vlmeval

REPORT = ROOT / "NidhiLens (Fine-Tuned Qwen for site progress monitoring)" / "data"
OUT = ROOT / "data" / "trial" / "results" / "t159_reader"


def _read(p: Path) -> list[dict]:
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]


def engine_verdict(verdict: str | None, probs: dict, reason: str) -> str | None:
    """One spot judged through the engine's own code (VLMReader, then visit._answer)."""
    def runner(a, b, wt, claim, kind):
        return {"verdict": verdict or "cant_tell", "probs": probs, "reason": reason}
    answers = VLMReader(runner=runner).judge(["the claim"], [("before-v1", b"a"),
                                                             ("now-v1", b"b")])
    return _answer(answers, True)[0]


def rows_of(raw: list[dict], items: dict[str, dict], engine: bool) -> list[dict]:
    out = []
    for r in raw:
        it = items[r["id"]]
        probs = r.get("probs") or ({r["pred"]: r["conf"]} if r.get("conf") is not None else {})
        raw_v = r.get("verdict", r.get("pred")) or "cant_tell"
        pred = engine_verdict(raw_v, probs, r.get("reason") or "") if engine else raw_v
        out.append({"id": r["id"], "truth": it["label"], "pred": pred or "cant_tell",
                    "trick": it["trick"], "site": it["site"], "real": True,
                    "seconds": r.get("seconds")})
    return out


def _f(x: float | None) -> str:
    return "n/a" if x is None else f"{x:.3f}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--q4", required=True, type=Path)
    ap.add_argument("--bf16", required=True, type=Path)
    a = ap.parse_args()
    items = {i["id"]: i for i in _read(REPORT / "items_test.jsonl")}
    runs = {"benchmark (report)": _read(REPORT / "predictions" / "ours_4b_test.jsonl"),
            "bf16, video frames": _read(a.bf16), "4-bit, video frames": _read(a.q4)}
    ids = set(items)
    for name, raw in runs.items():
        ids &= {r["id"] for r in raw}
    bench = rows_of([r for r in runs["benchmark (report)"] if r["id"] in ids], items, False)
    lines = [(f"T159: NidhiLens-4B as the engine runs it, on {len(ids)} real main-test checks "
              "(every label checked by eye)"), "",
             (f"{'run':24s} {'verdict':8s} {'macro-F1 [95% CI]':24s} {'fooled':>7s} "
              f"{'missed':>7s} {'answered':>9s}  McNemar against the benchmark")]
    res = {}
    for name, raw in runs.items():
        raw = [r for r in raw if r["id"] in ids]
        for engine in (False, True):
            rows = rows_of(raw, items, engine)
            h = vlmeval._rates(rows)
            ci = vlmeval.bootstrap(rows, "macro_f1")
            mc = vlmeval.mcnemar(rows, bench)
            key = f"{name} | {'engine' if engine else 'raw'}"
            secs = [r["seconds"] for r in rows if r.get("seconds")]
            res[key] = {**h, "macro_f1_ci95": ci, "mcnemar_vs_benchmark": mc,
                        "seconds_per_check_l4": round(statistics.mean(secs), 2) if secs else None}
            same = mc["only_a_right"] == mc["only_b_right"] == 0
            lines.append(
                f"{name:24s} {'engine' if engine else 'raw':8s} "
                f"{h['macro_f1']:.3f} [{ci[0]:.3f}, {ci[1]:.3f}]{'':4s} "
                f"{_f(h['fooled_rate']):>7s} {_f(h['missed_rate']):>7s} "
                f"{_f(h['answered_share']):>9s}  "
                + ("same answers" if same else
                   f"{mc['only_a_right']} against {mc['only_b_right']}, p = {mc['p']:.3g}"))
    lines += ["", ("fooled = no-progress checks judged shown; missed = progress checks not judged "
                   "shown; answered = share not 'can't tell'."),
              ("engine = the raw answer passed through readers.VLMReader (sure 0.6) and "
               "video.visit._answer, as the video job judges one spot.")]
    for k, v in res.items():
        if v["seconds_per_check_l4"] and k.endswith("| raw"):
            lines.append(f"seconds a check on an L4 GPU, {k.split(' |')[0]}: "
                         f"{v['seconds_per_check_l4']}")
    OUT.with_suffix(".json").write_text(json.dumps(res, indent=1) + "\n", encoding="utf-8")
    OUT.with_suffix(".txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
