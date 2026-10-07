"""Measures (plan §8): numpy only, so the teacher can be measured where no model runs.

- auroc: progress yes / no, ranked by score (ties counted half)
- kendall_tau: the build-up score against frame order, over one shot
- selective: accuracy where the model answers, and how often it answers (the "can't tell" band)
- ece: calibration error of probabilities
- patch_scores: precision, recall and IoU of progress patches against a truth map
- audits: the shortcut tests, as shares of pairs called progress where none was made
"""

from __future__ import annotations

import numpy as np


def auroc(scores: np.ndarray, labels: np.ndarray) -> float:
    s, y = np.asarray(scores, float), np.asarray(labels).astype(bool)
    pos, neg = s[y], s[~y]
    if len(pos) == 0 or len(neg) == 0:
        return float("nan")
    order = np.argsort(np.concatenate([pos, neg]), kind="mergesort")
    ranks = np.empty(len(order), float)
    allv = np.concatenate([pos, neg])[order]
    i = 0
    while i < len(allv):                      # average ranks over ties
        j = i
        while j + 1 < len(allv) and allv[j + 1] == allv[i]:
            j += 1
        ranks[order[i:j + 1]] = (i + j) / 2 + 1
        i = j + 1
    r_pos = ranks[:len(pos)].sum()
    return float((r_pos - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg)))


def kendall_tau(a: np.ndarray, b: np.ndarray) -> float:
    a, b = np.asarray(a, float), np.asarray(b, float)
    n = len(a)
    if n < 2:
        return float("nan")
    da = np.sign(a[:, None] - a[None, :])
    db = np.sign(b[:, None] - b[None, :])
    iu = np.triu_indices(n, 1)
    num = (da[iu] * db[iu]).sum()
    den = np.sqrt((da[iu] != 0).sum() * (db[iu] != 0).sum())
    return float(num / den) if den else float("nan")


def selective(probs: np.ndarray, labels: np.ndarray, low: float = 0.35, high: float = 0.65,
              ) -> tuple[float, float]:
    """(accuracy where it answers, share it answers): probabilities in [low, high] are "can't
    tell" and never count."""
    p, y = np.asarray(probs, float), np.asarray(labels).astype(int)
    answer = (p < low) | (p > high)
    if not answer.any():
        return float("nan"), 0.0
    acc = float(((p[answer] > 0.5).astype(int) == y[answer]).mean())
    return acc, float(answer.mean())


def ece(probs: np.ndarray, labels: np.ndarray, bins: int = 10) -> float:
    p, y = np.asarray(probs, float), np.asarray(labels, float)
    edges = np.linspace(0, 1, bins + 1)
    out = 0.0
    for lo, hi in zip(edges[:-1], edges[1:], strict=True):
        m = (p >= lo) & ((p < hi) if hi < 1 else (p <= hi))
        if m.any():
            out += m.mean() * abs(p[m].mean() - y[m].mean())
    return float(out)


def patch_scores(pred: np.ndarray, truth: np.ndarray, ignore: np.ndarray | None = None,
                 ) -> dict[str, float]:
    """Progress patches: pred bool, truth int (1, 0, -1 ignored). Counts summed over all maps."""
    pred, truth = np.asarray(pred, bool), np.asarray(truth)
    k = truth != -1
    if ignore is not None:
        k &= ~ignore
    t = truth == 1
    tp = int((pred & t & k).sum())
    fp = int((pred & ~t & k).sum())
    fn = int((~pred & t & k).sum())
    prec = tp / (tp + fp) if tp + fp else float("nan")
    rec = tp / (tp + fn) if tp + fn else float("nan")
    iou = tp / (tp + fp + fn) if tp + fp + fn else float("nan")
    return {"precision": prec, "recall": rec, "iou": iou, "tp": tp, "fp": fp, "fn": fn}


def false_progress(probs: np.ndarray, threshold: float = 0.5) -> float:
    """Share of pairs where no work was done that are called progress (an audit set's rate)."""
    p = np.asarray(probs, float)
    return float((p > threshold).mean()) if p.size else float("nan")


def both_ways(p_ab: np.ndarray, p_ba: np.ndarray, threshold: float = 0.5) -> float:
    """Share of pairs called progress in both directions: the model saw "different", not
    "added"."""
    a, b = np.asarray(p_ab, float), np.asarray(p_ba, float)
    return float(((a > threshold) & (b > threshold)).mean()) if a.size else float("nan")
