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


def predict(L, items: list, root: Path, out_path: Path, log=print) -> list[dict]:
    """Runs the model over `items`, resumable (one JSON line an item in `out_path`)."""
    from drishti_vision import vlm
    done = {}
    if out_path.exists():
        for line in out_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                done[r["id"]] = r
    with open(out_path, "a", encoding="utf-8") as f:
        for k, it in enumerate(items):
            if it.id in done:
                continue
            o = vlm.judge(L, it, root)
            a = o["answer"]
            pred = a["verdict"] if a else "unreadable"
            conf = (o["probs"] or {}).get(pred) if a else None
            r = {"id": it.id, "site": it.site, "trick": it.trick, "real": it.real,
                 "ab_distance": it.ab_distance,
                 "truth": it.target["verdict"], "pred": pred, "conf": conf, "probs": o["probs"],
                 "seconds": o["seconds"], "text": o["text"][:400]}
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
            f.flush()
            done[it.id] = r
            if (k + 1) % 25 == 0:
                log(f"{k + 1}/{len(items)}")
    return [done[it.id] for it in items if it.id in done]
