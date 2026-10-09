"""Cutting an edited timelapse into shots, and keeping only still-camera shots (plan §4.3).

A timelapse posted online is edited: title cards, drone passes, zooms, cuts between cameras. A
cut is a jump in the colour histogram and in the small grey picture between two frames, far above
the video's usual frame-to-frame change. A shot is kept when it is long enough, has texture (not a
title card), and every frame aligns onto its first frame with little drift (a still camera).
Order within a shot is the only "time" the labels use, so no dates are needed.
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from drishti_vision.frames import SHARP, grey, quality
from drishti_vision.register import _features, align, align_features

CUT_UNRELATED = 0.9         # 1 - correlation above this: an unrelated picture, whatever matched
MIN_FRAMES = 12             # shorter shots cannot show lasting change
MAX_DRIFT = 0.06            # a still camera: no frame shifted more than this share of the width
MIN_ALIGNED = 0.9           # ... and this share of frames aligned onto the first


@dataclass
class Shot:
    start: int
    end: int                # exclusive
    keep: bool
    reason: str

    def __len__(self) -> int:
        return self.end - self.start


def _signature(img: np.ndarray) -> np.ndarray:
    """A 48x27 grey picture, blurred, with its mean and spread taken out: a change of light or
    contrast leaves it as it was."""
    small = cv2.resize(cv2.GaussianBlur(grey(img), (0, 0), 2), (48, 27),
                       interpolation=cv2.INTER_AREA).astype(np.float32)
    small -= small.mean()
    return small / max(float(small.std()), 1e-3)


def change_scores(frames: np.ndarray) -> np.ndarray:
    """(N-1,) 1 - the correlation of neighbouring frames' signatures: about 0 for the same view
    in any light, near 1 or more for an unrelated picture."""
    sigs = [_signature(f) for f in frames]
    out = np.zeros(max(0, len(frames) - 1), np.float32)
    for i in range(1, len(frames)):
        out[i - 1] = 1.0 - float((sigs[i - 1] * sigs[i]).mean())
    return out


def find_cuts(frames: np.ndarray) -> list[int]:
    """Indexes i where a new shot starts at frame i: frame i cannot be aligned onto frame i-1
    (another view, a title card, a camera knocked), or its picture is unrelated (CUT_UNRELATED).
    Light, shadows and passers-by never break an alignment of the same view."""
    if len(frames) < 2:
        return []
    scores = change_scores(frames)
    cuts = []
    prev = _features(frames[0], None)
    for i in range(1, len(frames)):
        cur = _features(frames[i], None)
        same = align_features(cur, prev, frames.shape[1:3]).ok
        if not same or scores[i - 1] > CUT_UNRELATED:
            cuts.append(i)
        prev = cur
    return cuts


def still_camera(frames: np.ndarray) -> tuple[bool, str]:
    if np.mean([quality(f).sharpness for f in frames]) < SHARP:
        return False, "no texture (a title card or a blurred shot)"
    ref = _features(frames[0], None)
    w = frames.shape[2]
    aligned, drifts = 0, []
    for f in frames[1:]:
        a = align(f, ref)
        if a.ok:
            aligned += 1
            c = np.array([[[w / 2, frames.shape[1] / 2]]], np.float32)
            moved = cv2.perspectiveTransform(c, a.homography)[0, 0] - c[0, 0]
            drifts.append(float(np.hypot(*moved)) / w)
    share = aligned / max(1, len(frames) - 1)
    if share < MIN_ALIGNED:
        return False, f"only {share:.0%} of frames align onto the first (a moving camera)"
    if drifts and max(drifts) > MAX_DRIFT:
        return False, f"the view drifts {max(drifts):.0%} of the width (a pan or a zoom)"
    return True, "still camera"


def split(frames: np.ndarray) -> list[Shot]:
    bounds = [0, *find_cuts(frames), len(frames)]
    out = []
    for a, b in zip(bounds[:-1], bounds[1:], strict=False):
        if b - a < MIN_FRAMES:
            out.append(Shot(a, b, False, f"{b - a} frames, under {MIN_FRAMES}"))
            continue
        keep, why = still_camera(frames[a:b])
        out.append(Shot(a, b, keep, why))
    return out
