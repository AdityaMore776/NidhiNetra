"""Burned-in dates, logos and watermarks (plan §4.3).

A date stamp would let a model read the date instead of seeing the building. Two kinds are found,
with no model, on a shot whose frames are aligned:

- fixed on screen: an overlay does not move with the scene. On RAW (unaligned) frames it sits on
  identical pixels in every frame, while the scene shakes and its light changes. So: pixels with
  strong edges and almost no change over the shot.
- flickering digits: a time stamp changes every frame in one small box near an edge of the frame.
  So: edge pixels that change in most frames, gathered into boxes near the border.

Corner bands are also blanked at random in training (augment.py), for overlays these miss.
"""

from __future__ import annotations

import cv2
import numpy as np

from drishti_vision.frames import grey

STILL = 6.0                 # temporal std (grey levels) below this: a still pixel
EDGE = 60.0                 # gradient magnitude above this: an edge
FLICKER = 0.35              # an edge pixel changing in this share of frames: flicker
BORDER = 0.22               # flickering pixels are looked for within this share of the frame's
                            # height from the top or bottom edge
EDGE_GAP = 0.04             # ... and their box must reach this close to the edge
MAX_BOX_H = 0.12            # an overlay box is never taller than this share of the frame


def _edges(g: np.ndarray) -> np.ndarray:
    gx = cv2.Sobel(g, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(g, cv2.CV_32F, 0, 1, ksize=3)
    return np.hypot(gx, gy)


def overlay_mask(raw: np.ndarray, grow: int = 3) -> np.ndarray:
    """(H, W) bool mask of overlays, from the shot's RAW frames (before alignment)."""
    n = len(raw)
    g = np.stack([grey(f) for f in raw]).astype(np.float32)
    h, w = g.shape[1:]
    edges = np.stack([_edges(x) for x in g])
    strong = (edges > EDGE).mean(axis=0) > 0.5
    still = g.std(axis=0) < STILL
    fixed = strong & still
    if n >= 3:
        changed = (np.abs(np.diff(g, axis=0)) > 40) & (edges[1:] > EDGE)
        flicker = changed.mean(axis=0) > FLICKER
        band = np.zeros((h, w), bool)
        b = int(h * BORDER)
        band[:b] = band[h - b:] = True
        flicker &= band
    else:
        flicker = np.zeros((h, w), bool)
    out = np.zeros((h, w), bool)
    # gather letters into boxes: close the gaps between them
    for m, hug in ((fixed, False), (flicker, True)):
        m = cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((5, 15), np.uint8))
        count, labels, stats, _ = cv2.connectedComponentsWithStats(m)
        for i in range(1, count):
            x, y, bw, bh, area = stats[i]
            if area < 20 or bh > MAX_BOX_H * h or bw > 0.8 * w:
                continue
            # a changing stamp hugs the top or bottom edge; scene edges in that band do not
            if hug and not (y + bh >= h - EDGE_GAP * h or y <= EDGE_GAP * h):
                continue
            out[y:y + bh, x:x + bw] = True
    if grow:
        out = cv2.dilate(out.astype(np.uint8), np.ones((2 * grow + 1, 2 * grow + 1), np.uint8)) > 0
    return out


def corner_bands(h: int, w: int, frac_h: float = 0.1, frac_w: float = 0.35) -> np.ndarray:
    """The four corner boxes where dates and logos usually sit."""
    m = np.zeros((h, w), bool)
    bh, bw = int(h * frac_h), int(w * frac_w)
    m[:bh, :bw] = m[:bh, w - bw:] = m[h - bh:, :bw] = m[h - bh:, w - bw:] = True
    return m
