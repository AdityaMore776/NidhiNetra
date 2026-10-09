"""Aligning every frame of a shot onto one reference frame (plan §4.3).

ORB points matched to the reference, as the engine's video job does (video/reader.py), with two
changes for timelapses:

- points are spread over a grid of cells (the strongest few in each), so the still background gets
  its say and the changing work (fresh brick, a new slab) cannot drown it out;
- a fixed timelapse camera only shakes, so the default model is a similarity (shift, rotation,
  zoom: 4 numbers), which far fewer matches fit reliably than a full homography (8 numbers). A
  handheld shot can ask for the homography.

The alignment can be limited to a mask (the frame minus overlays). A frame that cannot be aligned is
reported and left out, never silently kept.
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from drishti_vision.frames import grey

MATCH_RATIO = 0.8
RANSAC_PX = 3.0
MIN_INLIERS = 15
MAX_SHIFT = 0.15            # moving the centre more than this share of the width: wrong
MIN_SCALE, MAX_SCALE = 0.8, 1.25
MAX_ROTATE = 10.0           # degrees
CELLS = (4, 4)              # keypoints are kept per cell of this grid
PER_CELL = 120


@dataclass
class Alignment:
    ok: bool
    homography: np.ndarray | None   # frame -> reference, 3x3
    inliers: int


_ORB = None


def _orb():
    global _ORB
    if _ORB is None:
        _ORB = cv2.ORB_create(nfeatures=6000, fastThreshold=7, edgeThreshold=15, patchSize=15)
    return _ORB


def _features(img: np.ndarray, mask: np.ndarray | None):
    g = cv2.equalizeHist(grey(img))
    m = None if mask is None else (mask.astype(np.uint8) * 255)
    kps = _orb().detect(g, m)
    if not kps:
        return [], None
    h, w = g.shape
    cy, cx = CELLS
    buckets: dict[tuple[int, int], list] = {}
    for k in kps:
        key = (min(cy - 1, int(k.pt[1] * cy / h)), min(cx - 1, int(k.pt[0] * cx / w)))
        buckets.setdefault(key, []).append(k)
    kept = []
    for ks in buckets.values():
        kept += sorted(ks, key=lambda k: -k.response)[:PER_CELL]
    return _orb().compute(g, kept)


def _sane(h: np.ndarray, w: int, hgt: int) -> bool:
    if h is None or not np.all(np.isfinite(h)) or abs(h[2, 2]) < 1e-9:
        return False
    c = np.array([[[w / 2, hgt / 2]]], np.float32)
    moved = cv2.perspectiveTransform(c, h)[0, 0] - c[0, 0]
    if np.hypot(*moved) > MAX_SHIFT * w:
        return False
    a = h[:2, :2] / h[2, 2]
    s = np.sqrt(abs(np.linalg.det(a)))
    rot = np.degrees(np.arctan2(a[1, 0], a[0, 0]))
    return MIN_SCALE <= s <= MAX_SCALE and abs(rot) <= MAX_ROTATE


def align(img: np.ndarray, ref_feats, mask: np.ndarray | None = None,
          model: str = "similarity") -> Alignment:
    return align_features(_features(img, mask), ref_feats, img.shape[:2], model)


def align_features(feats, ref_feats, shape: tuple[int, int],
                   model: str = "similarity") -> Alignment:
    """As align(), from keypoints already found: (keypoints, descriptors) of the frame and of
    the reference, and the frame's (height, width)."""
    ka, da = feats
    kb, db = ref_feats
    if da is None or db is None or len(ka) < MIN_INLIERS or len(kb) < MIN_INLIERS:
        return Alignment(False, None, 0)
    pairs = cv2.BFMatcher(cv2.NORM_HAMMING).knnMatch(da, db, k=2)
    good = [m for m, *n in pairs if n and m.distance < MATCH_RATIO * n[0].distance]
    if len(good) < MIN_INLIERS:
        return Alignment(False, None, len(good))
    src = np.float32([ka[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
    dst = np.float32([kb[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)
    if model == "similarity":
        a, inl = cv2.estimateAffinePartial2D(src, dst, method=cv2.RANSAC,
                                             ransacReprojThreshold=RANSAC_PX, maxIters=4000)
        h = None if a is None else np.vstack([a, [0, 0, 1]])
    else:
        h, inl = cv2.findHomography(src, dst, cv2.RANSAC, RANSAC_PX)
    n = int(inl.sum()) if inl is not None else 0
    ok = n >= MIN_INLIERS and _sane(h, shape[1], shape[0])
    return Alignment(ok, h if ok else None, n)


def align_shot(frames: np.ndarray, ref: int | None = None, mask: np.ndarray | None = None,
               model: str = "similarity",
               ) -> tuple[np.ndarray, np.ndarray, list[Alignment]]:
    """(aligned frames, (N, H, W) bool where each aligned frame has picture, alignments). The
    reference is the middle frame unless given. Frames that fail keep zeros and no valid area."""
    n, hgt, w = frames.shape[:3]
    ref = n // 2 if ref is None else ref
    ref_feats = _features(frames[ref], mask)
    out = np.zeros_like(frames)
    valid = np.zeros((n, hgt, w), bool)
    report = []
    ones = np.full((hgt, w), 255, np.uint8)
    for t in range(n):
        a = Alignment(True, np.eye(3), 0) if t == ref else align(frames[t], ref_feats, mask, model)
        report.append(a)
        if a.ok:
            out[t] = cv2.warpPerspective(frames[t], a.homography, (w, hgt),
                                         flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
            # shrink the valid area by a few pixels: warped borders blur
            v = cv2.warpPerspective(ones, a.homography, (w, hgt)) > 0
            valid[t] = cv2.erode(v.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
    return out, valid, report
