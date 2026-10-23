r"""T173 part 2: the code-written claim against the agency's own words, check by check.

"fixed" (this PC, 4-bit: data/trial/t173_photo_only.py --modes fixed) against the report's NidhiLens run
with the agency's claim (T155, full precision, saved in the NidhiLens report folder,
data/predictions/ours_4b_<set>.jsonl). T159 measured 4-bit against full precision on the same 883:
macro-F1 0.933 against 0.935, McNemar p 0.66, but 4-bit is fooled more (10 against 4), so for the test set the
agency's words are also shown in 4-bit (T159's run on phone-video frames, D:\nidhinetra-data\t159\q4_frames.jsonl;
the engine's sure = 0.6 never changes an answer there, so its raw verdict is the engine's).

  D:\nidhinetra-data\venv\Scripts\python.exe data\trial\t173_compare.py

Writes data/trial/results/t173_compare.txt (+ .json).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "apps" / "vision"))
from drishti_vision import vlmeval  # noqa: E402

REPORT = ROOT / "NidhiLens (Fine-Tuned Qwen for site progress monitoring)" / "data"
RUNS = Path(r"D:\nidhinetra-data\runs\t173")
T159_Q4 = Path(r"D:\nidhinetra-data\t159\q4_frames.jsonl")
OUT = ROOT / "data" / "trial" / "results" / "t173_compare"


def _read(p: Path) -> list[dict]:
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]


def rows(path: Path, items: dict[str, dict]) -> list[dict]:
    out = []
    for r in _read(path):
        it = items.get(r["id"])
        if it:
            out.append({"id": r["id"], "site": it["site"], "trick": it["trick"], "real": True,
                        "truth": it["label"], "pred": r.get("pred") or r["verdict"]})
    return out


def line(name: str, rs: list[dict]) -> tuple[str, dict]:
    h = vlmeval._rates(rs)
    ci = vlmeval.bootstrap(rs, "macro_f1")
    nope = sum(r["truth"] != "shown" for r in rs)
    real = sum(r["truth"] == "shown" for r in rs)
    fooled = sum(r["pred"] == "shown" and r["truth"] != "shown" for r in rs)
    missed = sum(r["pred"] != "shown" and r["truth"] == "shown" for r in rs)
    return (f"  {name:34} n {len(rs)}: macro-F1 {h['macro_f1']:.3f} [{ci[0]:.3f}, {ci[1]:.3f}], "
            f"accuracy {h['accuracy']:.3f}, fooled {fooled} of {nope}, missed {missed} of {real}",
            {"n": len(rs), **h, "macro_f1_ci95": ci, "fooled": fooled, "missed": missed})


def main() -> None:
    lines, res = ["T173: NidhiLens with a claim written by code from the agency's pick, against the "
                  "agency's own words (same checks)", ""], {}
    for name in ("test", "fresh"):
        fixed_p = RUNS / f"{name}_fixed.jsonl"
        if not fixed_p.exists():
            continue
        items = {i["id"]: i for i in _read(REPORT / f"items_{name}.jsonl")}
        fixed = rows(fixed_p, items)
        claim = rows(REPORT / "predictions" / f"ours_4b_{name}.jsonl", items)
        ids = {r["id"] for r in fixed} & {r["id"] for r in claim}
        fixed = [r for r in fixed if r["id"] in ids]
        claim = [r for r in claim if r["id"] in ids]
        lines.append(f"{name} ({len(ids)} checks answered by both):")
        a, ra = line("agency's words (T155, full prec.)", claim)
        b, rb = line("code-written claim (4-bit)", fixed)
        m = vlmeval.mcnemar(fixed, claim)
        lines += [a, b, f"  McNemar: only code-written right {m['only_a_right']}, only agency's words "
                        f"right {m['only_b_right']}, p {m['p']:.3g}", ""]
        res[name] = {"claim": ra, "fixed": rb, "mcnemar": m}
        if name == "test" and T159_Q4.exists():
            q4 = [r for r in rows(T159_Q4, items) if r["id"] in ids]
            c, rc = line("agency's words (T159, 4-bit)", q4)
            m4 = vlmeval.mcnemar(fixed, q4)
            lines[-1:] = [c, f"  McNemar, both 4-bit: only code-written right {m4['only_a_right']}, only agency's "
                             f"words right {m4['only_b_right']}, p {m4['p']:.3g}", ""]
            res[name] |= {"claim_q4": rc, "mcnemar_q4": m4}
    OUT.with_suffix(".txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    OUT.with_suffix(".json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
