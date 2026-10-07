"""Frames: reading a video, dropping poor frames, and removing what moves (plan §4.3, §4.4).

Nothing here repaints a picture. A temporal median of a few neighbouring frames removes people and
vehicles that move between frames, with no model; what stays put is masked, never filled in.
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

WIDTH = 640                 # frames are read at this width (the engine's video job uses the same)
DARK = 40.0                 # mean grey below this: too dark (night, a covered lens)
SHARP = 60.0                # Laplacian variance below this: blurred
BRIGHT = 235.0              # mean grey above this: washed out
MOVED_BY = 0.25             # a pixel "moves" when its fine detail (log brightness) or colour ratio
                            # differs from its neighbours' median by this much
MAX_BLOB = 0.06             # a moving blob over this share of the frame is light, not a thing


@dataclass
class Quality:
    brightness: float
    sharpness: float

    @property
    def usable(self) -> bool:
        return DARK <= self.brightness <= BRIGHT and self.sharpness >= SHARP


def resize(img: np.ndarray, width: int = WIDTH) -> np.ndarray:
    h, w = img.shape[:2]
    if w == width:
        return img
    interp = cv2.INTER_AREA if w > width else cv2.INTER_LINEAR
    return cv2.resize(img, (width, round(h * width / w)), interpolation=interp)


def grey(img: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)


def quality(img: np.ndarray) -> Quality:
    g = grey(img)
    return Quality(float(g.mean()), float(cv2.Laplacian(g, cv2.CV_64F).var()))


def read_video(path: str, n: int | None = None, every_s: float | None = None,
               width: int = WIDTH) -> tuple[np.ndarray, float]:
    """(frames (N, H, W, 3) RGB, the video's frames a second). `n` frames spread evenly over the
    whole video, or one every `every_s` seconds; all frames if neither is given."""
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise OSError(f"cannot open video {path}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    if n and total > 0:
        wanted = set(np.linspace(0, total - 1, min(n, total)).round().astype(int).tolist())
    elif every_s:
        step = max(1, round(fps * every_s))
        wanted = None
    else:
        step, wanted = 1, None
    out, i = [], 0
    while True:
        ok = cap.grab()
        if not ok:
            break
        take = (i in wanted) if wanted is not None else (i % step == 0)
        if take:
            ok, bgr = cap.retrieve()
            if ok:
                out.append(resize(bgr[..., ::-1], width))
        i += 1
    cap.release()
    if not out:
        raise OSError(f"no frames read from {path}")
    return np.stack(out), float(fps)


def write_video(path: str, frames: np.ndarray, fps: float = 10.0) -> None:
    """Writes RGB frames as an .mp4 (used by the tests and the synthetic trial)."""
    h, w = frames.shape[1:3]
    vw = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))
    for f in frames:
        vw.write(np.ascontiguousarray(f[..., ::-1]))
    vw.release()


def temporal_median(frames: np.ndarray, radius: int = 1) -> np.ndarray:
    """Each frame replaced by the median of itself and `radius` frames each side (fewer at the
    ends). Removes what moves between frames; keeps what stays."""
    if radius <= 0:
        return frames.copy()
    out = np.empty_like(frames)
    n = len(frames)
    for t in range(n):
        lo, hi = max(0, t - radius), min(n, t + radius + 1)
        out[t] = np.median(frames[lo:hi], axis=0).astype(frames.dtype)
    return out


def _light_free(img: np.ndarray) -> np.ndarray:
    """(H, W, 3): fine detail of log brightness (a shadow or a dull day adds a smooth offset to log
    brightness, which subtracting its blur removes) and the two colour ratios (r, g)."""
    f = img.astype(np.float32) + 1.0
    s = f.sum(axis=2)
    logl = np.log(s / 3.0)
    detail = logl - cv2.GaussianBlur(logl, (0, 0), 6)
    return np.dstack([detail, f[..., 0] / s * 4.0, f[..., 1] / s * 4.0])


def motion_mask(frames: np.ndarray, radius: int = 1, moved: float = MOVED_BY,
                max_blob: float = MAX_BLOB) -> np.ndarray:
    """(N, H, W) bool: things that move between frames (people, vehicles). A pixel moves when its
    fine detail or colour differs from its neighbours' median; light and shadows change neither
    much. Blobs over `max_blob` of the frame are left out (a change of light, not a passer-by)."""
    lf = np.stack([_light_free(f) for f in frames])
    med = temporal_median(lf, radius)
    diff = np.abs(lf - med).max(axis=3) > moved
    kernel = np.ones((3, 3), np.uint8)
    area = frames.shape[1] * frames.shape[2]
    out = np.empty(diff.shape, bool)
    for t in range(len(diff)):
        m = cv2.morphologyEx(diff[t].astype(np.uint8), cv2.MORPH_OPEN, kernel)
        count, labels, stats, _ = cv2.connectedComponentsWithStats(m)
        keep = np.zeros(count, bool)
        keep[1:] = stats[1:, cv2.CC_STAT_AREA] <= max_blob * area
        m = keep[labels].astype(np.uint8)
        out[t] = cv2.dilate(m, kernel, iterations=2) > 0
    return out


def daylight_normalise(frames: np.ndarray) -> np.ndarray:
    """Evens out each frame's overall light and colour cast: every channel scaled so its median
    matches the shot's median. A shadow stays (it is local); a dull or bright day does not."""
    f = frames.astype(np.float32)
    med = np.median(f.reshape(len(f), -1, 3), axis=1)              # (N, 3)
    target = np.median(med, axis=0)
    scale = target[None, :] / np.maximum(med, 1.0)
    return np.clip(f * scale[:, None, None, :], 0, 255).astype(np.uint8)
