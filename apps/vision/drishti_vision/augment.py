"""Augmentations for pairs, each teaching one thing (plan §4.5).

| Augmentation                                        | Teaches the model                         |
|-----------------------------------------------------|-------------------------------------------|
| different crop, zoom, rotation, perspective, A vs B | a handheld phone never stands in the same |
|                                                     | spot twice                                |
| light, contrast, white balance, gamma, a shadow,    | light and weather are not progress        |
| haze, rain                                          |                                           |
| JPEG, blur, noise, low resolution                   | cheap phones and bad days                 |
| corners blanked                                     | never read the date                       |
| people, machines, scaffolds, stacks pasted into B   | dressing up the site is not progress      |

Every function takes a numpy Generator, so one seed gives one result. The patch labels of B follow
B's warp; a patch moved outside the picture, or hidden under something pasted, becomes -1.
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np


@dataclass
class Config:
    warp: float = 0.06          # corner jitter, share of the shorter side
    rotate: float = 4.0         # degrees
    zoom: tuple[float, float] = (0.9, 1.12)
    p_shadow: float = 0.4
    p_haze: float = 0.15
    p_rain: float = 0.1
    p_corrupt: float = 0.6
    p_corners: float = 0.5
    p_paste: float = 0.5
    max_paste: int = 4


def photometric(img: np.ndarray, rng: np.random.Generator, cfg: Config | None = None
                ) -> np.ndarray:
    cfg = cfg or Config()
    f = img.astype(np.float32) / 255.0
    gain, contrast, gamma = rng.uniform(0.6, 1.4), rng.uniform(0.7, 1.3), rng.uniform(0.7, 1.4)
    wb = rng.uniform(0.85, 1.15, 3).astype(np.float32)
    f = np.clip(((f - 0.5) * contrast + 0.5) * gain * wb, 0, 1) ** gamma
    grey = f.mean(axis=2, keepdims=True)
    f = np.clip(grey + (f - grey) * rng.uniform(0.6, 1.3), 0, 1)
    h, w = f.shape[:2]
    if rng.random() < cfg.p_shadow:
        x = rng.uniform(-0.2, 1.0) * w
        poly = np.array([(x, 0), (x + rng.uniform(0.1, 0.4) * w, 0),
                         (x + rng.uniform(-0.1, 0.4) * w, h), (x - rng.uniform(0, 0.3) * w, h)],
                        np.int32)
        m = np.zeros((h, w), np.uint8)
        cv2.fillPoly(m, [poly], 1)
        m = cv2.GaussianBlur(m.astype(np.float32), (0, 0), 3)[..., None]
        f = f * (1 - m * rng.uniform(0.2, 0.5))
    if rng.random() < cfg.p_haze:
        a = rng.uniform(0.1, 0.35)
        f = f * (1 - a) + a * np.float32(0.8)
    if rng.random() < cfg.p_rain:
        streaks = np.zeros((h, w), np.uint8)
        for _ in range(int(rng.integers(40, 120))):
            x, y = int(rng.integers(0, w)), int(rng.integers(0, h))
            ln = int(rng.integers(4, 12))
            cv2.line(streaks, (x, y), (x + ln // 4, y + ln), 1, 1)
        f = np.where(streaks[..., None] > 0, f * 0.6 + 0.4 * np.float32(0.85), f)
    return (np.clip(f, 0, 1) * 255).astype(np.uint8)


def corrupt(img: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    out = img
    if rng.random() < 0.3:
        s = rng.uniform(0.4, 0.8)
        h, w = out.shape[:2]
        size = (max(8, int(w * s)), max(8, int(h * s)))
        small = cv2.resize(out, size, interpolation=cv2.INTER_AREA)
        out = cv2.resize(small, (w, h), interpolation=cv2.INTER_LINEAR)
    if rng.random() < 0.3:
        out = cv2.GaussianBlur(out, (0, 0), rng.uniform(0.5, 1.5))
    if rng.random() < 0.4:
        out = np.clip(out + rng.normal(0, rng.uniform(2, 8), out.shape), 0, 255).astype(np.uint8)
    if rng.random() < 0.6:
        ok, buf = cv2.imencode(".jpg", out, [cv2.IMWRITE_JPEG_QUALITY, int(rng.integers(25, 91))])
        out = cv2.imdecode(buf, cv2.IMREAD_UNCHANGED)
    return out


def random_homography(h: int, w: int, rng: np.random.Generator,
                      cfg: Config | None = None) -> np.ndarray:
    """A small random view change: rotation, zoom about the centre, corners jittered."""
    cfg = cfg or Config()
    rot = cv2.getRotationMatrix2D((w / 2, h / 2), rng.uniform(-cfg.rotate, cfg.rotate),
                                  rng.uniform(*cfg.zoom))
    m = np.vstack([rot, [0, 0, 1]]).astype(np.float64)
    src = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
    j = cfg.warp * min(h, w)
    dst = src + rng.uniform(-j, j, src.shape).astype(np.float32)
    return cv2.getPerspectiveTransform(src, dst).astype(np.float64) @ m


def warp(img: np.ndarray, hom: np.ndarray) -> np.ndarray:
    h, w = img.shape[:2]
    return cv2.warpPerspective(img, hom, (w, h), flags=cv2.INTER_LINEAR,
                               borderMode=cv2.BORDER_CONSTANT)


def warp_patches(labels: np.ndarray, hom: np.ndarray, patch: int) -> np.ndarray:
    """Patch labels after the picture is warped by `hom`: each output patch takes the label of the
    input patch under its centre; outside the picture, -1."""
    gh, gw = labels.shape
    ys, xs = np.mgrid[0:gh, 0:gw]
    centres = np.stack([(xs + 0.5) * patch, (ys + 0.5) * patch], -1).reshape(-1, 1, 2)
    src = cv2.perspectiveTransform(centres.astype(np.float32), np.linalg.inv(hom))
    src = src.reshape(gh, gw, 2)
    sx, sy = np.floor(src[..., 0] / patch).astype(int), np.floor(src[..., 1] / patch).astype(int)
    inside = (sx >= 0) & (sx < gw) & (sy >= 0) & (sy < gh)
    out = np.full((gh, gw), -1, np.int8)
    out[inside] = labels[sy[inside], sx[inside]]
    return out


def erase_corners(img: np.ndarray, rng: np.random.Generator, frac_h=(0.06, 0.12),
                  frac_w=(0.15, 0.4)) -> np.ndarray:
    out = img.copy()
    h, w = out.shape[:2]
    for top in (True, False):
        for left in (True, False):
            if rng.random() < 0.5:
                bh, bw = int(h * rng.uniform(*frac_h)), int(w * rng.uniform(*frac_w))
                ys = slice(0, bh) if top else slice(h - bh, h)
                xs = slice(0, bw) if left else slice(w - bw, w)
                out[ys, xs] = out.reshape(-1, 3).mean(axis=0).astype(np.uint8)
    return out


def _thing(rng: np.random.Generator, h: int, w: int) -> tuple[np.ndarray, np.ndarray]:
    """One temporary thing at a random place: (mask, colour image)."""
    kind = rng.choice(["person", "person", "machine", "scaffold", "stack", "bags"])
    m = np.zeros((h, w), np.uint8)
    col = np.zeros((h, w, 3), np.uint8)
    x, y = int(rng.uniform(0.05, 0.85) * w), int(rng.uniform(0.35, 0.85) * h)
    if kind == "person":
        bw, bh = max(3, int(w * rng.uniform(0.02, 0.04))), max(6, int(h * rng.uniform(0.06, 0.12)))
        cv2.rectangle(m, (x, y), (x + bw, y + bh), 1, -1)
        cv2.circle(m, (x + bw // 2, y - bw // 2), max(2, bw // 2), 1, -1)
        col[:] = rng.choice([(255, 128, 12), (240, 220, 30), (40, 80, 200), (200, 30, 30)])
    elif kind == "machine":
        bw, bh = int(w * rng.uniform(0.12, 0.25)), int(h * rng.uniform(0.07, 0.14))
        cv2.rectangle(m, (x, y), (x + bw, y + bh), 1, -1)
        col[:] = rng.choice([(220, 180, 25), (40, 70, 150), (230, 230, 230)])
    elif kind == "scaffold":
        bw, bh = int(w * rng.uniform(0.2, 0.45)), int(h * rng.uniform(0.2, 0.4))
        y = max(0, y - bh)
        for gx in range(x, x + bw + 1, max(5, bw // 6)):
            cv2.line(m, (gx, y), (gx, y + bh), 1, 1)
        for gy in range(y, y + bh + 1, max(5, bh // 5)):
            cv2.line(m, (x, gy), (x + bw, gy), 1, 1)
        col[:] = (205, 205, 215)
    else:
        bw, bh = int(w * rng.uniform(0.06, 0.12)), int(h * rng.uniform(0.04, 0.07))
        cv2.rectangle(m, (x, y), (x + bw, y + bh), 1, -1)
        base = (170, 75, 50) if kind == "stack" else (235, 235, 225)
        col[:] = base
        for gy in range(y, y + bh, 3):
            cv2.line(col, (x, gy), (x + bw, gy), (120, 120, 120), 1)
    return m.astype(bool), col


def paste_transients(img: np.ndarray, labels: np.ndarray, patch: int, rng: np.random.Generator,
                     n: int | None = None, bank: list[np.ndarray] | None = None,
                     ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Pastes 1..4 temporary things into `img` (frame B). Labels stay 0 where they were 0 (a
    staged site is still no progress); progress patches hidden under a paste become -1. `bank`:
    RGBA cutouts (e.g. people and machines from SODA or MOCS) used instead of drawn shapes.
    Returns (image, labels, pasted mask)."""
    h, w = img.shape[:2]
    out = img.copy()
    pasted = np.zeros((h, w), bool)
    for _ in range(n if n is not None else int(rng.integers(1, 5))):
        if bank:
            cut = bank[int(rng.integers(len(bank)))]
            ch, cw = cut.shape[:2]
            if ch >= h or cw >= w:
                continue
            y, x = int(rng.integers(0, h - ch)), int(rng.integers(0, w - cw))
            a = cut[..., 3] > 127
            out[y:y + ch, x:x + cw][a] = cut[..., :3][a]
            pasted[y:y + ch, x:x + cw] |= a
        else:
            m, col = _thing(rng, h, w)
            out[m] = col[m]
            pasted |= m
    gh, gw = labels.shape
    cover = pasted[:gh * patch, :gw * patch].reshape(gh, patch, gw, patch).mean(axis=(1, 3))
    new = labels.copy()
    new[(cover > 0.3) & (labels == 1)] = -1
    return out, new, pasted


def augment_pair(a: np.ndarray, b: np.ndarray, labels: np.ndarray, patch: int,
                 rng: np.random.Generator, cfg: Config | None = None, staged: bool | None = None,
                 ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """One training pair, augmented: A and B each get their own view change, light and damage; B
    may be dressed up. Labels follow B."""
    cfg = cfg or Config()
    h, w = b.shape[:2]
    ha, hb = random_homography(h, w, rng, cfg), random_homography(h, w, rng, cfg)
    a2, b2 = warp(a, ha), warp(b, hb)
    lab = warp_patches(labels, hb, patch)
    if staged if staged is not None else rng.random() < cfg.p_paste:
        b2, lab, _ = paste_transients(b2, lab, patch, rng)
    a2, b2 = photometric(a2, rng, cfg), photometric(b2, rng, cfg)
    if rng.random() < cfg.p_corrupt:
        a2 = corrupt(a2, rng)
    if rng.random() < cfg.p_corrupt:
        b2 = corrupt(b2, rng)
    if rng.random() < cfg.p_corners:
        a2, b2 = erase_corners(a2, rng), erase_corners(b2, rng)
    return a2, b2, lab
