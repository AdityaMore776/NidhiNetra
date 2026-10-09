"""SiteClaim-Bench scoring (plan T150 §7; task T155).

HEADLINE NUMBERS USE ONLY REAL, UNEDITED PHOTOS from the test districts (the owner's rule, 7 Oct
2026):
an item with any edit (pasted people, light, dark, blocked) is reported apart, never in a headline.

    macro_f1         the three verdicts weighted equally
    fooled_rate      of the pairs with NO real progress (view, busy, double claim, swapped; staged
    and
                     light when edited items are scored apart), the share called "shown"
    missed_rate      of the real progress pairs, the share not called "shown"
    answered         accuracy when the model answers (not cant_tell) and how often it answers
    ece              calibration of the verdict's probability
    per_trick        accuracy for each trick
    cost             seconds a check; rupees per 1,000 checks on the owner's PC (electricity only)

Every rate has a bootstrap 95% interval over ASSETS (items of one asset are not independent).
"""

from __future__ import annotations

import json
import random
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

from drishti_vision.vlmdata import NO_PROGRESS_TRICKS, VERDICTS

GPU_WATTS = 290            # RTX 3070 Ti board power under load
RUPEES_PER_KWH = 8.0       # Indian domestic tariff, order of magnitude


def macro_f1(truth: list[str], pred: list[str]) -> float:
    f1s = []
    for v in VERDICTS:
        tp = sum(t == v and p == v for t, p in zip(truth, pred, strict=True))
        fp = sum(t != v and p == v for t, p in zip(truth, pred, strict=True))
        fn = sum(t == v and p != v for t, p in zip(truth, pred, strict=True))
        if tp + fp + fn == 0:
            continue
        f1s.append(2 * tp / (2 * tp + fp + fn))
    return float(np.mean(f1s)) if f1s else 0.0


def ece(conf: list[float], correct: list[bool], bins: int = 10) -> float:
    conf_a, cor = np.array(conf), np.array(correct, float)
    out = 0.0
    for lo in np.linspace(0, 1, bins, endpoint=False):
        m = (conf_a >= lo) & (conf_a < lo + 1 / bins)
        if m.any():
            out += m.mean() * abs(conf_a[m].mean() - cor[m].mean())
    return float(out)


def _rates(rows: list[dict]) -> dict:
    truth = [r["truth"] for r in rows]
    pred = [r["pred"] for r in rows]
    nop = [r for r in rows if r["trick"] in NO_PROGRESS_TRICKS and r["truth"] == "not_shown"]
    prog = [r for r in rows if r["truth"] == "shown"]
    ans = [r for r in rows if r["pred"] != "cant_tell"]

    def mean(xs: list) -> float | None:
        return float(np.mean(xs)) if xs else None

    return {
        "n": len(rows),
        "accuracy": mean([t == p for t, p in zip(truth, pred, strict=True)]) or 0.0,
        "macro_f1": macro_f1(truth, pred),
        "fooled_rate": mean([r["pred"] == "shown" for r in nop]),
        "n_no_progress": len(nop),
        "missed_rate": mean([r["pred"] != "shown" for r in prog]),
        "n_progress": len(prog),
        "answered_accuracy": mean([r["pred"] == r["truth"] for r in ans]),
        "answered_share": len(ans) / len(rows) if rows else 0,
    }


def bootstrap(rows: list[dict], key: str, n: int = 1000, seed: int = 0) -> tuple[float, float]:
    by = defaultdict(list)
    for r in rows:
        by[r["site"]].append(r)
    sites = list(by)
    rng = random.Random(seed)
    vals = []
    for _ in range(n):
        sample = [x for s in (rng.choice(sites) for _ in sites) for x in by[s]]
        v = _rates(sample)[key]
        if v is not None:
            vals.append(v)
    if not vals:
        return (float("nan"), float("nan"))
    return (float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5)))


def score(rows: list[dict]) -> dict:
    """rows: one per item, {site, trick, real, truth, pred, conf, seconds}."""
    real = [r for r in rows if r["real"]]
    edited = [r for r in rows if not r["real"]]
    out = {"headline_real_only": _rates(real),
           "edited_items_apart": _rates(edited) if edited else None}
    h = out["headline_real_only"]
    for key in ("macro_f1", "fooled_rate", "missed_rate"):
        h[key + "_ci95"] = bootstrap(real, key)
    confd = [r for r in real if r.get("conf") is not None]
    h["ece"] = (ece([r["conf"] for r in confd], [r["pred"] == r["truth"] for r in confd])
                if confd else None)
    per = defaultdict(list)
    for r in rows:
        per[(r["trick"], r["real"])].append(r["pred"] == r["truth"])
    out["per_trick"] = {f"{t}{'' if real_ else ' (edited)'}":
                        {"n": len(v), "accuracy": float(np.mean(v))}
                        for (t, real_), v in sorted(per.items())}
    out["confusion_real"] = {t: dict(Counter(r["pred"] for r in real if r["truth"] == t))
                             for t in VERDICTS}
    secs = [r["seconds"] for r in rows if r.get("seconds")]
    if secs:
        s = float(np.mean(secs))
        out["cost"] = {"seconds_per_check": round(s, 3),
                       "rupees_per_1000_checks_local": round(1000 * s * GPU_WATTS / 3.6e6
                                                             * RUPEES_PER_KWH, 2)}
        bills = [r["cost_usd"] for r in rows if r.get("cost_usd") is not None]
        if bills:                       # an API model: its own token bills, not electricity
            out["cost"]["usd_per_1000_checks_api"] = round(1000 * float(np.mean(bills)), 3)
            del out["cost"]["rupees_per_1000_checks_local"]
    out["refused"] = sum(bool(r.get("refused")) for r in rows)
    out["unreadable_answers"] = sum(r["pred"] == "unreadable" for r in rows)
    # the shortcut check: no-progress pairs whose photos look nearly the same vs clearly different
    nop = [r for r in real if r["trick"] in NO_PROGRESS_TRICKS and r.get("ab_distance") is not None]
    if nop:
        cut = float(np.median([r["ab_distance"] for r in nop]))
        near = [r for r in nop if r["ab_distance"] <= cut]
        far = [r for r in nop if r["ab_distance"] > cut]
        out["fooled_by_photo_difference"] = {
            "split_at_distance": round(cut, 4),
            "near_identical": {"n": len(near), "fooled_rate": float(np.mean(
                [r["pred"] == "shown" for r in near])) if near else None},
            "clearly_different": {"n": len(far), "fooled_rate": float(np.mean(
                [r["pred"] == "shown" for r in far])) if far else None}}
    return out


def mcnemar(rows_a: list[dict], rows_b: list[dict]) -> dict:
    """Exact McNemar test on the items both judges answered (plan T150 §7.4: a difference counts
    only if this agrees): how many only A got right, only B got right, and the two-sided p."""
    from math import comb
    b_by = {r["id"]: r for r in rows_b}
    pairs = [(r["pred"] == r["truth"], b_by[r["id"]]["pred"] == b_by[r["id"]]["truth"])
             for r in rows_a if r["id"] in b_by]
    only_a = sum(x and not y for x, y in pairs)
    only_b = sum(y and not x for x, y in pairs)
    n = only_a + only_b
    p = 1.0 if n == 0 else min(1.0, 2 * sum(comb(n, k) for k in range(min(only_a, only_b) + 1))
                               / 2 ** n)
    return {"n": len(pairs), "only_a_right": only_a, "only_b_right": only_b, "p": p}


def row(it, o: dict) -> dict:
    """One prediction line: the item's facts and the judge's answer."""
    a = o["answer"]
    pred = a["verdict"] if a else "unreadable"
    conf = (o["probs"] or {}).get(pred) if a else None
    return {"id": it.id, "site": it.site, "trick": it.trick, "real": it.real,
            "ab_distance": it.ab_distance,
            "truth": it.target["verdict"], "pred": pred, "conf": conf, "probs": o["probs"],
            "seconds": o["seconds"], "text": o["text"][:400],
            "served_by": o.get("served_by"), "cost_usd": o.get("cost_usd"),
            "usage": o.get("usage"), "refused": bool(o.get("refused"))}


def predict(L, items: list, root: Path, out_path: Path, log=print, batch: int = 1) -> list[dict]:
    """Runs a judge over `items`, resumable (one JSON line an item in `out_path`). `L` is a loaded
    local model (vlm.load) or any callable judge(item, root) -> {text, answer, probs, seconds, ...}
    (flagship_claude.ClaudeJudge, flagship_other.GeminiJudge / OpenAIJudge). `batch` > 1 answers
    that many items in one go (local models only; vlm.judge_batch)."""
    from drishti_vision import vlm
    done = {}
    if out_path.exists():
        for line in out_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                done[r["id"]] = r
    todo = [it for it in items if it.id not in done]
    step = batch if batch > 1 and not callable(L) else 1
    with open(out_path, "a", encoding="utf-8") as f:
        for k in range(0, len(todo), step):
            chunk = todo[k:k + step]
            try:
                if step > 1:
                    outs = vlm.judge_batch(L, chunk, root)
                else:
                    outs = [L(chunk[0], root) if callable(L) else vlm.judge(L, chunk[0], root)]
            except Exception as e:  # noqa: BLE001 (an API error is recorded, the run goes on)
                if getattr(e, "stop_run", False):     # e.g. a daily quota: stop, resume later
                    log(f"stopped: {type(e).__name__}: {str(e)[:160]}")
                    break
                log(f"{chunk[0].id}: {type(e).__name__}: {str(e)[:120]}")
                continue
            for it, o in zip(chunk, outs, strict=True):
                r = row(it, o)
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
                done[it.id] = r
            f.flush()
            n = len(done)
            if n // 25 != (n - len(chunk)) // 25:
                log(f"{n}/{len(items)}")
    return [done[it.id] for it in items if it.id in done]
