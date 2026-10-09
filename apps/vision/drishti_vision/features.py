"""Patch features: what each patch of a frame looks like, as a unit vector (plan §5.1, §7).

Two extractors with one interface, `extract(frames) -> (N, gh, gw, D)` unit vectors:

- `Handcrafted`: colour ratios and gradient orientations, made steady under overall light changes.
  CPU only, no download. Used by the tests and where no GPU is at hand.
- `Dinov2` (model.py): the frozen pretrained backbone the plan uses on real data.

The hindsight teacher only needs "how far apart are these two patches", so either works; DINOv2 is
the stronger one on real pictures.
"""

from __future__ import annotations

import warnings
from typing import Protocol

import cv2
import numpy as np


class Extractor(Protocol):
    patch: int

    def extract(self, frames: np.ndarray) -> np.ndarray: ...


def grid(h: int, w: int, patch: int) -> tuple[int, int]:
    return h // patch, w // patch


def patch_share(mask: np.ndarray, patch: int) -> np.ndarray:
    """(..., H, W) bool -> (..., gh, gw) share of each patch that is True."""
    *lead, h, w = mask.shape
    gh, gw = grid(h, w, patch)
    m = mask[..., :gh * patch, :gw * patch].reshape(*lead, gh, patch, gw, patch)
    return m.mean(axis=(-3, -1))


class Handcrafted:
    """Per patch, on a 2x2 grid of cells: chromaticity (r, g) mean and spread, and an 8-bin
    histogram of gradient orientations on log brightness (a change of overall light adds a
    constant to log brightness, which no gradient sees). Centred on the shot's mean, then unit
    length, so cosine distance compares what differs between patches."""

    def __init__(self, patch: int = 16, bins: int = 8, center: bool = True) -> None:
        self.patch, self.bins, self.center = patch, bins, center

    @property
    def dim(self) -> int:
        return 4 * (4 + self.bins)

    def _one(self, img: np.ndarray) -> np.ndarray:
        p, b = self.patch, self.bins
        f = img.astype(np.float32) + 1.0
        s = f.sum(axis=2)
        chroma = f[..., :2] / s[..., None]                         # r, g: light-free
        logl = np.log(s / 3.0)
        gx = cv2.Sobel(logl, cv2.CV_32F, 1, 0, ksize=3)
        gy = cv2.Sobel(logl, cv2.CV_32F, 0, 1, ksize=3)
        mag = np.minimum(np.hypot(gx, gy), 1.0)                     # strong edges count once
        ang = (np.arctan2(gy, gx) % np.pi) / np.pi * b
        h, w = logl.shape
        gh, gw = grid(h, w, p)
        c = p // 2
        hist = np.zeros((gh * 2, gw * 2, b), np.float32)
        idx = np.minimum(ang.astype(int), b - 1)[:gh * p, :gw * p]
        mg = mag[:gh * p, :gw * p]
        cy = (np.arange(gh * p) // c)[:, None].repeat(gw * p, 1)
        cx = (np.arange(gw * p) // c)[None, :].repeat(gh * p, 0)
        np.add.at(hist, (cy, cx, idx), mg)
        hist = hist / float(c * c)
        cr = chroma[:gh * p, :gw * p].reshape(gh * 2, c, gw * 2, c, 2)
        mean = cr.mean(axis=(1, 3))
        spread = cr.std(axis=(1, 3))
        cells = np.concatenate([mean * 8.0, spread * 16.0, hist * 2.0], axis=2)
        return cells.reshape(gh, 2, gw, 2, -1).transpose(0, 2, 1, 3, 4).reshape(gh, gw, -1)

    def extract(self, frames: np.ndarray) -> np.ndarray:
        """`center`: subtract the shot's mean feature first (for comparing patches within one
        shot); off when frames from many shots are encoded one at a time (model.py)."""
        raw = np.stack([self._one(f) for f in frames])
        if self.center:
            raw = raw - raw.mean(axis=(0, 1, 2), keepdims=True)
        return raw / np.maximum(np.linalg.norm(raw, axis=-1, keepdims=True), 1e-6)


def smooth(feats: np.ndarray, valid: np.ndarray, radius: int = 1) -> np.ndarray:
    """Each frame's patch feature replaced by the median of its valid neighbours within `radius`
    frames (a patch masked in a frame borrows from its neighbours), renormalised."""
    n = len(feats)
    out = feats.copy()
    for t in range(n):
        lo, hi = max(0, t - radius), min(n, t + radius + 1)
        f, v = feats[lo:hi], valid[lo:hi]
        masked = np.where(v[..., None], f, np.nan)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)      # all-masked: handled below
            med = np.nanmedian(masked, axis=0)
        has = v.any(axis=0)
        out[t] = np.where(has[..., None], med, feats[t])
    return out / np.maximum(np.linalg.norm(out, axis=-1, keepdims=True), 1e-6)
