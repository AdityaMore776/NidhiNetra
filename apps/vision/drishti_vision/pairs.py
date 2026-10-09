"""Pairs (A, B) for the student, with their labels (plan §4.5, §5).

From each labelled shot:
- forward pairs (t1 < t2) labelled by the hindsight teacher: progress or none;
- swapped pairs (B before A): work disappearing is never progress, so the label is none and the
  patch map is all none. This makes the model learn the direction of change, not "different";
- short-gap pairs, mostly none: neighbouring frames differ by light, not by work.
Pairs the teacher leaves out (-1) are not used. Classes are balanced per shot.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from drishti_vision.hindsight import NONE, PROGRESS, TEMPORARY, Hindsight


@dataclass
class Pair:
    shot_id: str
    a: int
    b: int
    label: int              # 1 progress, 0 none
    kind: str               # forward | swapped | short
    patches: np.ndarray     # (gh, gw) int8: 1 progress, 0 none, -1 ignore
    truth: np.ndarray | None = None     # synthetic shots only: the true map and label
    truth_label: int | None = None


PAIR_KINDS = ("forward", "short", "swapped")


def target_map(patches: np.ndarray) -> np.ndarray:
    """The student's patch target: progress 1; none and temporary 0; unknown -1 (ignored)."""
    out = np.full(patches.shape, -1, np.int8)
    out[patches == PROGRESS] = 1
    out[(patches == NONE) | (patches == TEMPORARY)] = 0
    return out


def sample(shot_id: str, hs: Hindsight, n: int, rng: np.random.Generator, short_gap: int = 2,
           swap_share: float = 0.2, short_share: float = 0.2) -> list[Pair]:
    T = hs.T
    out: list[Pair] = []
    pos, neg = [], []
    tries = 0
    want = n
    while (len(pos) + len(neg) < 3 * want) and tries < 20 * want:
        tries += 1
        if rng.random() < short_share:
            t1 = int(rng.integers(0, T - 1))
            t2 = min(T - 1, t1 + int(rng.integers(1, short_gap + 1)))
            kind = "short"
        else:
            t1, t2 = sorted(int(x) for x in rng.choice(T, 2, replace=False))
            kind = "forward"
        if t1 == t2:
            continue
        lab = hs.label(t1, t2)
        if lab.label == -1:
            continue
        p = Pair(shot_id, t1, t2, lab.label, kind, target_map(lab.patches))
        if lab.by_stage:
            # the stage marks say work was done that the pictures cannot show: the pair says
            # progress, the patches are not trusted
            p.patches = np.full(p.patches.shape, -1, np.int8)
        (pos if lab.label == 1 else neg).append(p)
    k = min(len(pos), len(neg), want // 2) if pos and neg else min(want, len(pos) + len(neg))
    if pos and neg:
        out = pos[:k] + neg[:k]
    else:
        out = (pos + neg)[:k]
    n_swap = int(round(swap_share * len(out)))
    for p in [q for q in out if q.label == 1][:n_swap]:
        out.append(Pair(shot_id, p.b, p.a, 0, "swapped",
                        np.where(p.patches == -1, -1, 0).astype(np.int8)))
    return out
