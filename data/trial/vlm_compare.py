r"""T155: the claim judge against the flagship, at each model's best: accuracy AND cost.

Reads the prediction files fetched from the Modal volume (D:\nidhinetra-data\runs\modal\<judge>\
<split>.jsonl, or the shards <split>_s0.jsonl, <split>_s1.jsonl, ...), scores every judge on the
SAME items (real, unedited photos; every test label checked by eye), and prices one check:
    flagship    its billed tokens (thinking included) x the provider's published price
    ours        measured seconds a check x the GPU's published price a second
Writes data/trial/results/vlm_compare.txt and .json (counts and rates only; no names, no photos).

    python data/trial/vlm_compare.py --runs D:\nidhinetra-data\runs\modal --split calib
    python data/trial/vlm_compare.py --runs D:\nidhinetra-data\runs\modal --split test --ref sft4b_v6_real
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# Published prices, read on 8 Oct 2026. Re-read them on the day of any new run.
API_USD_PER_M = {        # (input, output incl. thinking) per million tokens, prompts <= 200k
    "gemini-3.1-pro-preview": (2.00, 12.00),     # ai.google.dev/gemini-api/docs/pricing
    "gemini-3.8-flash": (0.75, 3.75),            # same page; rises to 1.50 / 7.50 on 1 Jan 2027
}
BATCH_DISCOUNT = 0.5        # ai.google.dev/gemini-api/docs/batch-mode
GPU_USD_PER_S = {"L4": 0.000222, "A100-40GB": 0.000583}    # modal.com/pricing


def _vlmeval():
    import sys
    sys.path.insert(0, str(ROOT / "apps" / "vision"))
    from drishti_vision import vlmeval
    return vlmeval


def read_rows(folder: Path, split: str, suffix: str = "") -> list[dict]:
    files = sorted(folder.glob(f"{split}{suffix}_s*.jsonl")) or \
        [p for p in [folder / f"{split}{suffix}.jsonl"] if p.exists()]
    rows, seen = [], set()
    for f in files:
        for line in f.read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                if r["id"] not in seen:
                    seen.add(r["id"])
                    rows.append(r)
    return rows


def usd_per_check(rows: list[dict], gpu: str) -> tuple[float | None, str]:
    api = [r for r in rows if r.get("usage")]
    if api:
        model = next((m for m in API_USD_PER_M if m in str(api[0].get("served_by", ""))), None)
        if model is None:
            return None, "unknown API price"
        pin, pout = API_USD_PER_M[model]
        batch = "(batch)" in str(api[0].get("served_by", ""))
        c = sum(r["usage"]["in"] * pin + r["usage"]["out"] * pout for r in api) / 1e6 / len(api)
        if batch:                       # Batch API: "50% of the standard cost" (same page)
            c *= BATCH_DISCOUNT
        return c, f"{model} billed tokens{', Batch API price' if batch else ''}"
    secs = [r["seconds"] for r in rows if r.get("seconds")]
    if not secs:
        return None, "no timing"
    return sum(secs) / len(secs) * GPU_USD_PER_S[gpu], f"{gpu} GPU time"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", required=True)
    ap.add_argument("--split", default="test")
    ap.add_argument("--ref", default="", help="judge folder the others are compared with")
    ap.add_argument("--judges", default="", help="comma list of judge folders (default: all)")
    ap.add_argument("--gpu", default="L4", help="the GPU our judges were timed on")
    ap.add_argument("--keep", default="", help="items .jsonl: score only its items of the split "
                                               "(the eye-checked ones)")
    a = ap.parse_args()
    ev = _vlmeval()
    runs = Path(a.runs)
    names = a.judges.split(",") if a.judges else sorted(p.name for p in runs.iterdir() if p.is_dir())
    judges = {}
    for n in names:
        for suffix, label in (("", n), ("_1024", n + " @1024px")):
            rows = read_rows(runs / n, a.split, suffix)
            if rows:
                judges[label] = rows
    common = set.intersection(*(set(r["id"] for r in rows) for rows in judges.values()))
    if a.keep:
        keep = {json.loads(x)["id"] for x in Path(a.keep).read_text(encoding="utf-8").splitlines()
                if x.strip() and json.loads(x)["split"] == a.split}
        common &= keep
    out, lines = {}, [f"T155: judges on the same {len(common)} {a.split} items (real photos; "
                      "labels checked by eye)", ""]
    ref = {r["id"]: r for r in judges.get(a.ref, [])}
    for name, rows in judges.items():
        rows = [r for r in rows if r["id"] in common]
        s = ev.score(rows)
        h = s["headline_real_only"]
        cost, how = usd_per_check(rows, a.gpu)
        out[name] = {"n": h["n"], "macro_f1": h["macro_f1"], "macro_f1_ci95": h["macro_f1_ci95"],
                     "fooled_rate": h["fooled_rate"], "fooled_ci95": h["fooled_rate_ci95"],
                     "missed_rate": h["missed_rate"], "accuracy": h["accuracy"],
                     "unreadable": s["unreadable_answers"], "per_trick": s["per_trick"],
                     "usd_per_1000_checks": None if cost is None else round(1000 * cost, 3),
                     "cost_basis": how}
        f = (lambda v: "n/a" if v is None else f"{v:.3f}")
        lines.append(f"{name}: n {h['n']}, macro-F1 {f(h['macro_f1'])} "
                     f"[{f(h['macro_f1_ci95'][0])}, {f(h['macro_f1_ci95'][1])}], accuracy "
                     f"{f(h['accuracy'])}, fooled {f(h['fooled_rate'])} of {h['n_no_progress']}, "
                     f"missed {f(h['missed_rate'])} of {h['n_progress']}, unreadable "
                     f"{s['unreadable_answers']}")
        lines.append(f"    cost: {'n/a' if cost is None else f'${1000 * cost:.3f}'} per 1,000 "
                     f"checks ({how})")
        if ref and name != a.ref:
            m = ev.mcnemar(list(ref.values()), rows)
            out[name]["mcnemar_vs_ref"] = m
            lines.append(f"    against {a.ref}: only {a.ref} right {m['only_a_right']}, only this "
                         f"right {m['only_b_right']}, McNemar p {m['p']:.3g}")
    res = ROOT / "data" / "trial" / "results"
    stem = f"vlm_compare_{a.split}"
    (res / f"{stem}.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (res / f"{stem}.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
