"""Synthetic construction timelapses with exact ground truth (plan §9).

A site is built element by element (a pit, footings, earth backfilled over them, a plinth, a
frame, walls rising course by course, a roof, plaster over the walls, windows), in one of five
kinds. Around it come the things that are NOT progress: people, vehicles, scaffolding, stacked
materials, a moving shadow, the day's light, camera shake, a date stamp and a logo.

Every frame comes with the truth, in the camera's reference position: which permanent element is on
top at each pixel, and which pixels something temporary covers. That lets the pipeline be measured
where the answer is known. A number measured here is about the pipeline, never about real sites.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import cv2
import numpy as np

from drishti_vision.stages import STAGES

KINDS = ("masonry", "concrete_frame", "wood", "steel", "road")


def work_type_of(kind: str) -> str:
    return "road" if kind == "road" else "building"


@dataclass
class Element:
    """One permanent piece of work: there from frame `start` on, never removed."""

    eid: int
    start: int
    stage: int
    mask: np.ndarray            # (H, W) bool, reference position
    tex: np.ndarray             # (H, W, 3) float32 in [0, 1]
    buried: bool = False        # earth over finished work: looks like the ground it started as


@dataclass
class Temporary:
    """Something temporary for frames [start, end): scaffolding, a stack, a parked machine."""

    start: int
    end: int
    mask: np.ndarray
    tex: np.ndarray
    kind: str


@dataclass
class SynthShot:
    site_id: str
    kind: str
    work_type: str
    seed: int
    frames: np.ndarray          # (T, H, W, 3) uint8 RGB, as the camera saw them
    built: np.ndarray           # (T, H, W) int16: the permanent element on top (0: none), reference
    temporary: np.ndarray       # (T, H, W) bool: covered by something temporary, reference
    buried_ids: frozenset[int]
    overlay: np.ndarray         # (H, W) bool: date stamp and logo (fixed on screen)
    stage: np.ndarray           # (T,) int16 index into STAGES[work_type]
    shake: np.ndarray           # (T, 2, 3) affine: reference -> camera
    elements: list[dict] = field(default_factory=list)


def _smooth_noise(rng: np.random.Generator, h: int, w: int, cells: int) -> np.ndarray:
    small = rng.random((max(2, h // cells), max(2, w // cells))).astype(np.float32)
    return cv2.resize(small, (w, h), interpolation=cv2.INTER_CUBIC)


def _solid(rng, h, w, rgb, amp=0.05, cells=4) -> np.ndarray:
    base = np.array(rgb, np.float32)[None, None, :]
    n = (_smooth_noise(rng, h, w, cells) - 0.5) * 2 * amp
    fine = (rng.random((h, w)).astype(np.float32) - 0.5) * amp
    return np.clip(base + (n + fine)[..., None], 0, 1)


def _bricks(rng, h, w, unit_w, unit_h, rgb, mortar=(0.78, 0.76, 0.7)) -> np.ndarray:
    tex = _solid(rng, h, w, rgb, amp=0.08, cells=3)
    m = np.array(mortar, np.float32)
    for y in range(0, h, unit_h):
        tex[y:y + 1] = m
        off = (y // unit_h) % 2 * unit_w // 2
        for x in range(off, w, unit_w):
            tex[y:y + unit_h, x:x + 1] = m
    return tex


def _stripes(rng, h, w, period, rgb, dark=0.75, vertical=True) -> np.ndarray:
    tex = _solid(rng, h, w, rgb, amp=0.04)
    idx = np.arange(w if vertical else h)
    line = ((idx % period) < max(1, period // 3)).astype(np.float32)
    shade = 1 - (1 - dark) * line
    return tex * (shade[None, :, None] if vertical else shade[:, None, None])


def _gravel(rng, h, w, rgb) -> np.ndarray:
    return _solid(rng, h, w, rgb, amp=0.22, cells=1)


def _rect(h, w, x0, y0, x1, y1) -> np.ndarray:
    m = np.zeros((h, w), bool)
    m[max(0, int(y0)):max(0, int(y1)), max(0, int(x0)):max(0, int(x1))] = True
    return m


def _poly(h, w, pts) -> np.ndarray:
    m = np.zeros((h, w), np.uint8)
    cv2.fillPoly(m, [np.array(pts, np.int32)], 1)
    return m.astype(bool)


def _lines(h, w, segs, thick) -> np.ndarray:
    m = np.zeros((h, w), np.uint8)
    for (x0, y0), (x1, y1) in segs:
        cv2.line(m, (int(x0), int(y0)), (int(x1), int(y1)), 1, thick)
    return m.astype(bool)


class Site:
    """One synthetic site: its scene, its plan of work and its temporary things, fixed by `seed`."""

    def __init__(self, kind: str, seed: int, n_frames: int = 60, size: tuple[int, int] = (192, 256),
                 bury: bool | None = None, site_id: str | None = None) -> None:
        if kind not in KINDS:
            raise ValueError(f"kind must be one of {KINDS}")
        self.kind, self.seed, self.T = kind, seed, n_frames
        self.H, self.W = size
        self.work_type = work_type_of(kind)
        self.site_id = site_id or f"synth-{kind}-{seed}"
        rng = np.random.default_rng(seed)
        self.rng = rng
        self.bury = bool(rng.random() < 0.6) if bury is None else bury
        self.background = self._background()
        self.elements: list[Element] = []
        if kind == "road":
            self._plan_road()
        else:
            self._plan_building()
        self._schedule()
        self.temporaries = self._temporaries()
        self.phase = rng.random()

    # -- the scene -----------------------------------------------------------------------------
    def _background(self) -> np.ndarray:
        rng, H, W = self.rng, self.H, self.W
        hz = int(H * 0.5)
        img = np.zeros((H, W, 3), np.float32)
        top, bottom = np.array([0.45, 0.62, 0.85]), np.array([0.78, 0.84, 0.9])
        a = np.linspace(0, 1, hz)[:, None, None]
        img[:hz] = top * (1 - a) + bottom * a
        img[hz:] = _solid(rng, H - hz, W, (0.5, 0.45, 0.33), amp=0.12, cells=3)
        self.ground = img.copy()
        # distant buildings with windows and trees: texture the alignment can lock onto
        x = 0
        while x < W:
            bw, bh = int(rng.integers(W // 14, W // 7)), int(rng.integers(H // 14, H // 6))
            shade = rng.uniform(0.35, 0.65)
            img[hz - bh:hz, x:x + bw] = (shade, shade * 0.95, shade * 0.9)
            for wy in range(hz - bh + 3, hz - 3, 6):
                for wx in range(x + 2, x + bw - 2, 5):
                    if rng.random() < 0.6:
                        img[wy:wy + 2, wx:wx + 2] = (0.15, 0.15, 0.2)
            x += bw + int(rng.integers(0, W // 20))
        for _ in range(int(rng.integers(3, 6))):
            cx = int(rng.choice([rng.integers(0, W // 5), rng.integers(4 * W // 5, W)]))
            cy, r = int(hz - rng.integers(0, H // 10)), int(rng.integers(H // 20, H // 10))
            m = np.zeros((H, W), np.uint8)
            cv2.circle(m, (cx, cy), r, 1, -1)
            img[m.astype(bool)] = _solid(rng, H, W, (0.2, 0.38, 0.18), amp=0.1)[m.astype(bool)]
        # fence posts along the front
        for px in range(int(rng.integers(2, 8)), W, int(W // 12)):
            img[int(H * 0.9):int(H * 0.97), px:px + 2] = (0.3, 0.22, 0.14)
        return img

    # -- the plan of work ------------------------------------------------------------------------
    def _add(self, stage_name: str, mask: np.ndarray, tex: np.ndarray, buried=False) -> None:
        stage = STAGES[self.work_type].index(stage_name)
        self.elements.append(Element(len(self.elements) + 1, 0, stage, mask, tex, buried))

    def _plan_building(self) -> None:
        rng, H, W, k = self.rng, self.H, self.W, self.kind
        x0, x1 = int(W * rng.uniform(0.25, 0.33)), int(W * rng.uniform(0.67, 0.75))
        yb, yt = int(H * rng.uniform(0.78, 0.83)), int(H * rng.uniform(0.33, 0.4))
        plinth_top = yb - int(H * 0.05)
        pit = _rect(H, W, x0 - 3, yb - int(H * 0.03), x1 + 3, yb + int(H * 0.06))
        self._add("excavated", pit, _solid(rng, H, W, (0.27, 0.19, 0.12), amp=0.08))
        feet = np.zeros((H, W), bool)
        for fx in np.linspace(x0, x1 - W // 20, 4):
            feet |= _rect(H, W, fx, yb - int(H * 0.01), fx + W // 20, yb + int(H * 0.05))
        self._add("footing", feet, _solid(rng, H, W, (0.62, 0.62, 0.6), amp=0.05))
        if self.bury:
            below = pit & ~_rect(H, W, x0, plinth_top, x1, yb)
            fill = self.ground * np.float32(0.97) + np.float32(0.01)
            self._add("plinth", below, fill, buried=True)
        self._add("plinth", _rect(H, W, x0, plinth_top, x1, yb),
                  _solid(rng, H, W, (0.58, 0.57, 0.55), amp=0.05))
        cols = np.zeros((H, W), bool)
        if k == "concrete_frame":
            for cx in np.linspace(x0, x1 - W // 30, 4):
                cols |= _rect(H, W, cx, yt, cx + W // 30, plinth_top)
            ctex = _solid(rng, H, W, (0.66, 0.66, 0.64), amp=0.05)
        elif k == "steel":
            xs = np.linspace(x0, x1, 4)
            segs = [((x, yt), (x, plinth_top)) for x in xs]
            segs += [((xs[i], plinth_top), (xs[i + 1], yt)) for i in range(3)]
            cols = _lines(H, W, segs, 3)
            ctex = _solid(rng, H, W, (0.2, 0.24, 0.3), amp=0.04)
        elif k == "wood":
            for cx in np.linspace(x0, x1 - 3, 7):
                cols |= _rect(H, W, cx, yt, cx + 3, plinth_top)
            ctex = _solid(rng, H, W, (0.55, 0.38, 0.2), amp=0.06)
        else:  # masonry: brick corner piers
            for cx in (x0, x1 - W // 25):
                cols |= _rect(H, W, cx, yt, cx + W // 25, plinth_top)
            ctex = _bricks(rng, H, W, 10, 5, (0.62, 0.27, 0.18))
        self._add("columns", cols, ctex)
        wall_tex = {
            "masonry": lambda: _bricks(rng, H, W, 10, 5, (0.64, 0.28, 0.19)),
            "concrete_frame": lambda: _bricks(rng, H, W, 16, 8, (0.7, 0.7, 0.68),
                                              mortar=(0.55, 0.55, 0.53)),
            "wood": lambda: _stripes(rng, H, W, 7, (0.6, 0.42, 0.24), dark=0.7),
            "steel": lambda: _stripes(rng, H, W, 6, (0.45, 0.52, 0.6), dark=0.8),
        }[k]()
        courses = 4
        edges = np.linspace(plinth_top, yt, courses + 1).astype(int)
        for i in range(courses):
            m = _rect(H, W, x0, edges[i + 1], x1, edges[i])
            if k == "concrete_frame":
                m &= ~cols
            self._add("walls", m, wall_tex)
        if k == "wood":
            roof = _poly(H, W, [(x0 - 8, yt), (x1 + 8, yt), ((x0 + x1) // 2, yt - int(H * 0.12))])
            rtex = _stripes(rng, H, W, 5, (0.45, 0.2, 0.15), dark=0.8, vertical=False)
        else:
            roof = _rect(H, W, x0 - 6, yt - int(H * 0.04), x1 + 6, yt)
            rtex = _solid(rng, H, W, (0.5, 0.5, 0.5) if k != "steel" else (0.3, 0.33, 0.38))
        self._add("roof", roof, rtex)
        facade = _rect(H, W, x0, yt, x1, plinth_top)
        cover = {"masonry": (0.88, 0.84, 0.72), "concrete_frame": (0.9, 0.86, 0.62),
                 "wood": (0.92, 0.92, 0.9), "steel": (0.7, 0.76, 0.82)}[k]
        self._add("plaster", facade, _solid(rng, H, W, cover, amp=0.03))
        holes = np.zeros((H, W), bool)
        wy0, wy1 = yt + (plinth_top - yt) // 4, yt + (plinth_top - yt) // 2
        for wx in np.linspace(x0 + W // 20, x1 - W // 10, 3):
            holes |= _rect(H, W, wx, wy0, wx + W // 18, wy1)
        door_x = (x0 + x1) // 2
        door_top = plinth_top - (plinth_top - yt) // 2
        holes |= _rect(H, W, door_x - W // 40, door_top, door_x + W // 40, plinth_top)
        self._add("finishing", holes, _solid(rng, H, W, (0.16, 0.18, 0.22), amp=0.03))

    def _plan_road(self) -> None:
        rng, H, W = self.rng, self.H, self.W
        y0, y1 = int(H * rng.uniform(0.66, 0.72)), int(H * rng.uniform(0.84, 0.88))
        segs = 6
        xs = np.linspace(0, W, segs + 1).astype(int)
        layers = [("earthwork", _solid(rng, H, W, (0.45, 0.3, 0.18), amp=0.1)),
                  ("sub_base", _gravel(rng, H, W, (0.6, 0.58, 0.52))),
                  ("base", _gravel(rng, H, W, (0.38, 0.38, 0.36))),
                  ("surface", _stripes(rng, H, W, 40, (0.78, 0.78, 0.76), dark=0.6))]
        for name, tex in layers:
            for i in range(segs):
                self._add(name, _rect(H, W, xs[i], y0, xs[i + 1], y1), tex)
        edge = _rect(H, W, 0, y0 - 4, W, y0) | _rect(H, W, 0, y1, W, y1 + 4)
        self._add("shoulders", edge, _solid(rng, H, W, (0.35, 0.4, 0.25), amp=0.06))

    def _schedule(self) -> None:
        """Start frames in order of work, spread over 8% to 80% of the shot (the end stays quiet,
        so the last changes can be checked for whether they last)."""
        n = len(self.elements)
        lo = int(self.T * 0.08)
        hi = max(lo + 1, int(self.T * 0.8))
        starts = np.sort(self.rng.integers(lo, hi, n))
        order = sorted(range(n), key=lambda i: (self.elements[i].stage, i))
        for rank, i in enumerate(order):
            self.elements[i].start = int(starts[rank])

    def _temporaries(self) -> list[Temporary]:
        rng, H, W, T = self.rng, self.H, self.W, self.T
        out = []
        if self.work_type == "building":
            walls = [e for e in self.elements if STAGES["building"][e.stage] == "walls"]
            plaster = [e for e in self.elements if STAGES["building"][e.stage] == "plaster"]
            box = np.zeros((H, W), bool)
            for e in walls:
                box |= e.mask
            ys, xs = np.nonzero(box)
            gx0, gx1, gy0, gy1 = xs.min() - 6, xs.max() + 6, ys.min() - 8, ys.max()
            segs = [((x, gy0), (x, gy1)) for x in range(gx0, gx1 + 1, max(6, W // 18))]
            segs += [((gx0, y), (gx1, y)) for y in range(gy0, gy1 + 1, max(6, H // 14))]
            start = min(e.start for e in walls) - 1
            end = min(T, max(e.start for e in plaster) + int(rng.integers(2, 5)))
            out.append(Temporary(start, end, _lines(H, W, segs, 1),
                                 _solid(rng, H, W, (0.82, 0.82, 0.85), amp=0.02), "scaffold"))
        for _ in range(int(rng.integers(3, 6))):
            s = int(rng.integers(int(T * 0.1), max(int(T * 0.1) + 1, int(T * 0.75))))
            d = int(rng.integers(3, 13))
            x = rng.choice([rng.uniform(0.02, 0.16), rng.uniform(0.78, 0.9)]) * W
            y = rng.uniform(0.86, 0.93) * H
            m = _rect(H, W, x, y, x + W * 0.09, y + H * 0.05)
            bricks = rng.random() < 0.5
            tex = (_bricks(rng, H, W, 6, 3, (0.66, 0.3, 0.2)) if bricks
                   else _bricks(rng, H, W, 12, 5, (0.92, 0.92, 0.88), mortar=(0.6, 0.6, 0.6)))
            out.append(Temporary(s, min(T, s + d), m, tex, "materials"))
        for _ in range(int(rng.integers(1, 3))):
            s, d = int(rng.integers(0, max(1, int(T * 0.8)))), int(rng.integers(2, 7))
            x, y = rng.uniform(0.05, 0.75) * W, rng.uniform(0.6, 0.75) * H
            m = _rect(H, W, x, y, x + W * 0.16, y + H * 0.1)
            out.append(Temporary(s, min(T, s + d), m, _solid(rng, H, W, (0.85, 0.7, 0.1)),
                                 "machine"))
        return out

    # -- rendering -----------------------------------------------------------------------------
    def stage_at(self, t: int) -> int:
        started = [e.stage for e in self.elements if e.start <= t]
        return max(started) if started else 0

    def state(self, t: int) -> tuple[np.ndarray, np.ndarray]:
        """(image, built) of the permanent work at frame t, reference position, before light."""
        img = self.background.copy()
        built = np.zeros((self.H, self.W), np.int16)
        for e in self.elements:
            if e.start <= t:
                img[e.mask] = e.tex[e.mask]
                built[e.mask] = e.eid
        return img, built

    def _people(self, img, temp, rng, t) -> None:
        H, W = self.H, self.W
        active = any(abs(e.start - t) <= 3 for e in self.elements)
        n = int(rng.poisson(1.5 + (2.5 if active else 0.0)))
        vests = [(1.0, 0.5, 0.05), (0.95, 0.85, 0.1), (0.15, 0.3, 0.8), (0.8, 0.1, 0.1)]
        for _ in range(n):
            x = rng.uniform(0.15, 0.85) * W
            y = rng.uniform(0.45, 0.88) * H
            bw, bh = max(3, int(W * 0.022)), max(6, int(H * 0.07))
            body = _rect(self.H, self.W, x, y, x + bw, y + bh)
            img[body] = vests[int(rng.integers(len(vests)))]
            head = np.zeros((self.H, self.W), np.uint8)
            cv2.circle(head, (int(x + bw / 2), int(y - bw / 2)), max(2, bw // 2), 1, -1)
            img[head.astype(bool)] = (0.55, 0.38, 0.28)
            temp |= body | head.astype(bool)
        if rng.random() < 0.2:
            x, y = rng.uniform(0, 0.8) * W, rng.uniform(0.58, 0.8) * H
            truck = _rect(self.H, self.W, x, y, x + W * 0.2, y + H * 0.09)
            img[truck] = (0.2, 0.3, 0.6)
            temp |= truck

    def render(self, t: int, variant: int = 0) -> tuple[np.ndarray, np.ndarray, np.ndarray,
                                                         np.ndarray]:
        """(camera frame uint8 RGB, built, temporary, shake) at frame t. `variant` > 0 renders the
        same state of work at another moment of the same day: other people, light, shadow and
        shake."""
        H, W = self.H, self.W
        rng = np.random.default_rng((self.seed, t, variant))
        img, built = self.state(t)
        temp = np.zeros((H, W), bool)
        for o in self.temporaries:
            if o.start <= t < o.end:
                img[o.mask] = o.tex[o.mask]
                temp |= o.mask
        self._people(img, temp, rng, t)
        # a shadow band sweeping across, cyclic: light, not work
        pos = ((t * 0.29 + variant * 0.37 + self.phase) % 1.0) * 1.4 * W - 0.2 * W
        band = _poly(H, W, [(pos, 0), (pos + W * 0.25, 0), (pos + W * 0.1, H), (pos - W * 0.15, H)])
        img[band] *= 0.62
        # the day's light: gain, contrast, white balance
        gain = rng.uniform(0.7, 1.2)
        contrast = rng.uniform(0.8, 1.1)
        wb = np.array([1 + rng.normal(0, 0.06), 1.0, 1 + rng.normal(0, 0.06)], np.float32)
        img = np.clip(((img - 0.5) * contrast + 0.5) * gain * wb, 0, 1)
        # camera shake: reference -> camera
        ang, tx, ty = rng.uniform(-0.6, 0.6), rng.uniform(-1, 1) * W * 0.012, \
            rng.uniform(-1, 1) * W * 0.012
        shake = cv2.getRotationMatrix2D((W / 2, H / 2), ang, 1.0)
        shake[:, 2] += (tx, ty)
        frame = cv2.warpAffine((img * 255).astype(np.uint8), shake, (W, H),
                               borderMode=cv2.BORDER_REFLECT)
        frame = self._overlay(frame, t)
        frame = np.clip(frame + rng.normal(0, 2.0, frame.shape), 0, 255).astype(np.uint8)
        ok, buf = cv2.imencode(".jpg", frame[..., ::-1], [cv2.IMWRITE_JPEG_QUALITY, 85])
        frame = cv2.imdecode(buf, cv2.IMREAD_COLOR)[..., ::-1].copy()
        return frame, built, temp, shake.astype(np.float32)

    def _overlay_items(self, t: int) -> list[tuple[str, tuple[int, int]]]:
        day = 1 + t % 28
        month = 1 + (t // 28) % 12
        stamp = f"2024-{month:02d}-{day:02d} {10 + t % 7:02d}:{(t * 13) % 60:02d}"
        scale = self.W / 640
        (sw, _), _ = cv2.getTextSize(stamp, cv2.FONT_HERSHEY_SIMPLEX, scale, 1)
        return [("SITECAM 07", (4, int(14 * scale * 2))),
                (stamp, (self.W - sw - 4, self.H - 5))]

    def _overlay(self, frame: np.ndarray, t: int) -> np.ndarray:
        scale = self.W / 640
        out = frame.copy()
        for text, org in self._overlay_items(t):
            cv2.putText(out, text, org, cv2.FONT_HERSHEY_SIMPLEX, scale, (0, 0, 0), 3, cv2.LINE_AA)
            cv2.putText(out, text, org, cv2.FONT_HERSHEY_SIMPLEX, scale, (255, 255, 255), 1,
                        cv2.LINE_AA)
        return out

    def overlay_mask(self) -> np.ndarray:
        scale = self.W / 640
        m = np.zeros((self.H, self.W), bool)
        for t in range(self.T):
            for text, (x, y) in self._overlay_items(t):
                (w, h), base = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, scale, 3)
                ys = slice(max(0, y - h - 2), min(self.H, y + base + 2))
                m[ys, max(0, x - 2):min(self.W, x + w + 2)] = True
        return m

    def shot(self, variant: int = 0) -> SynthShot:
        """The whole shot. `variant` > 0: the same work seen at other moments (another camera on
        the same spot, or a re-upload of a different recording)."""
        T, H, W = self.T, self.H, self.W
        frames = np.zeros((T, H, W, 3), np.uint8)
        built = np.zeros((T, H, W), np.int16)
        temp = np.zeros((T, H, W), bool)
        shake = np.zeros((T, 2, 3), np.float32)
        for t in range(T):
            frames[t], built[t], temp[t], shake[t] = self.render(t, variant)
        return SynthShot(
            site_id=self.site_id, kind=self.kind, work_type=self.work_type, seed=self.seed,
            frames=frames, built=built, temporary=temp,
            buried_ids=frozenset(e.eid for e in self.elements if e.buried),
            overlay=self.overlay_mask(), stage=np.array([self.stage_at(t) for t in range(T)],
                                                        np.int16),
            shake=shake,
            elements=[{"eid": e.eid, "start": e.start, "stage": STAGES[self.work_type][e.stage],
                       "buried": e.buried, "pixels": int(e.mask.sum())} for e in self.elements])


def truth_pair(shot: SynthShot, t1: int, t2: int, patch: int, min_share: float = 0.25,
               ) -> tuple[np.ndarray, np.ndarray]:
    """The true label of each patch for (t1, t2), reference position: 1 permanent work added and
    visible at t2, 0 nothing added, -1 too little to call (a sliver of a patch). Also the patches
    whose only change is buried work (earth over finished work), which no picture can show."""
    new = shot.built[t2] != shot.built[t1]
    buried = new & np.isin(shot.built[t2], list(shot.buried_ids))
    visible = new & ~buried & ~shot.temporary[t2]
    H, W = new.shape
    gh, gw = H // patch, W // patch

    def share(m):
        return m[:gh * patch, :gw * patch].reshape(gh, patch, gw, patch).mean(axis=(1, 3))

    s, b = share(visible), share(buried)
    out = np.where(s >= min_share, 1, np.where((s == 0), 0, -1)).astype(np.int8)
    return out, (b >= min_share) & (s < min_share)
