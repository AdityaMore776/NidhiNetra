"""The hindsight teacher: progress is change that never goes back (plan §5.1).

It sees a whole aligned shot. For a pair of frames t1 < t2 and each patch:

    changed     the patch at t2 is far from how it was at t1 (distance > hi)
    reverted    at some frame t >= t2 the patch is close to how it was at t1 again (distance < lo)
    progress    changed and never reverted: a wall, a slab, a tile laid over cement
    temporary   changed and reverted: scaffolding, stacked materials, a parked machine, a shadow
    unknown     masked, or too near the end of the shot to know whether it reverts

"Looks like the final scene" is NOT the test: work covered later (plaster over brick, tile over
cement) never looks like the end, yet never goes back either. Two thresholds with a gap between them
keep noise from flipping a label.

A rule, not a model: the same inputs always give the same labels, and every label can be explained.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from drishti_vision.features import smooth

NONE, PROGRESS, TEMPORARY, UNKNOWN = 0, 1, 2, -1
MIN_FUTURE = 3              # valid frames at or after t2 needed to say a change lasts
MIN_SHARE = 0.02            # a progress pair: at least this share of the known patches is progress
MAX_UNKNOWN = 0.5           # more unknown patches than this: the pair is left out


@dataclass
class PairLabel:
    t1: int
    t2: int
    patches: np.ndarray     # (gh, gw) int8: NONE, PROGRESS, TEMPORARY or UNKNOWN
    label: int              # 1 progress, 0 none, -1 left out
    progress_share: float
    temporary_share: float
    unknown_share: float
    by_stage: bool = False  # the label came from the stage marks (buried or hidden work)


NOISE_GAPS = (3, 4, 5)      # frames this far apart rarely differ by real work: their distances are
                            # mostly noise (not 1 or 2: smoothing windows overlap and hide noise)
NOISE_Q, NOISE_TIMES = 75, 2.0


def calibrate(feats: np.ndarray, valid: np.ndarray, floor: float = 0.05) -> tuple[float, float]:
    """(lo, hi) from the shot itself: `lo` is twice the 75th percentile of the distances between
    frames 3 to 5 apart (light, shadows, small shifts; most patches see no work in so short a gap),
    `hi` twice `lo`. On synthetic shots it comes within 0.02 IoU of the best fixed value, with no
    tuning for the backbone or the camera (data/trial/results/vision_synth_trial.txt)."""
    ds = []
    for g in NOISE_GAPS:
        if len(feats) > g:
            d = 1.0 - np.einsum("tijd,tijd->tij", feats[:-g], feats[g:])
            ds.append(d[valid[:-g] & valid[g:]])
    noise = np.concatenate(ds) if ds else np.zeros(0)
    lo = max(floor, NOISE_TIMES * float(np.percentile(noise, NOISE_Q))) if noise.size else floor
    return lo, 2.0 * lo


class Hindsight:
    def __init__(self, feats: np.ndarray, valid: np.ndarray, lo: float | None = None,
                 hi: float | None = None, radius: int = 1, min_future: int = MIN_FUTURE,
                 stages: np.ndarray | None = None) -> None:
        """feats (T, gh, gw, D) unit vectors of an aligned shot; valid (T, gh, gw) patches that may
        be used (not masked, inside the picture); stages (T,) stage index per frame or -1."""
        self.valid = valid
        self.S = smooth(feats, valid, radius)
        c_lo, c_hi = calibrate(self.S, valid)
        self.lo = c_lo if lo is None else lo
        self.hi = c_hi if hi is None else hi
        if self.hi <= self.lo:
            raise ValueError("hi must be above lo")
        self.min_future = min_future
        self.stages = stages
        self._rows: dict[int, np.ndarray] = {}

    @property
    def T(self) -> int:
        return len(self.S)

    def row(self, t1: int) -> np.ndarray:
        """(T, gh, gw) distance of every frame's patch from frame t1's; NaN where not valid."""
        if t1 not in self._rows:
            d = 1.0 - np.einsum("ijd,tijd->tij", self.S[t1], self.S)
            ok = self.valid & self.valid[t1][None]
            self._rows[t1] = np.where(ok, d, np.nan).astype(np.float32)
        return self._rows[t1]

    def patches(self, t1: int, t2: int) -> np.ndarray:
        if not 0 <= t1 < t2 < self.T:
            raise ValueError("need 0 <= t1 < t2 < T")
        d = self.row(t1)
        later = d[t2:]
        n_future = np.sum(~np.isnan(later), axis=0)
        with np.errstate(all="ignore"):
            back = np.nanmin(np.where(np.isnan(later), np.inf, later), axis=0)
        d12 = d[t2]
        out = np.full(d12.shape, UNKNOWN, np.int8)
        known = ~np.isnan(d12)
        out[known & (d12 < self.lo)] = NONE
        changed = known & (d12 > self.hi)
        enough = n_future >= self.min_future
        out[changed & enough & (back >= self.lo)] = PROGRESS
        out[changed & enough & (back < self.lo)] = TEMPORARY
        return out

    def label(self, t1: int, t2: int) -> PairLabel:
        p = self.patches(t1, t2)
        known = p != UNKNOWN
        n = int(known.sum())
        share = (lambda k: float((p == k).sum()) / n) if n else (lambda k: 0.0)
        prog, temp = share(PROGRESS), share(TEMPORARY)
        unknown = 1.0 - n / p.size
        if unknown > MAX_UNKNOWN:
            lab = -1
        elif prog >= MIN_SHARE:
            lab = 1
        elif prog == 0.0:
            lab = 0
        else:
            lab = -1
        by_stage = False
        if self.stages is not None and self.stages[t1] >= 0 and self.stages[t2] > self.stages[t1]:
            by_stage = lab != 1
            lab = 1
        return PairLabel(t1, t2, p, lab, prog, temp, unknown, by_stage)
