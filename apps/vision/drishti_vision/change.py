"""Is the change between the before and after photos certain? (owner's rule, 7 Oct 2026; T153)

A "progress" item may enter the data only when progress is certain. The portal's stage label says
before / after, but some "before" photos already show a building, and some works barely change on
camera (a levelled playfield, a resurfaced lane). So a before -> after pair counts as progress only
if
the photos differ MORE than the asset's own noise: the two photos taken at the same moment (stage 1
photo 1 vs photo 2, stage 3 photo 1 vs photo 2) differ by viewpoint and light only. This is the
hindsight teacher's idea (T146 §5.1, thresholds from each shot's own noise) applied to photo sets.

Distance = 1 - cosine of the mean DINOv2 patch features of the two photos (a bag of parts, tolerant
to
a moved camera). The rule's margins are set by eye on real assets (FINDINGS "T153").
"""

from __future__ import annotations

from itertools import product
from pathlib import Path

import cv2
import numpy as np

SIDE = 434                 # 31 DINOv2 patches of 14 px
MARGIN = 1.25              # before->after must differ this many times more than the noise
FLOOR = 0.25               # and at least this much in absolute terms (set by eye, pilot)


def _read(path: Path) -> np.ndarray:
    img = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if img is None:
        raise FileNotFoundError(path)
    return cv2.resize(img, (SIDE, SIDE), interpolation=cv2.INTER_AREA)[..., ::-1]   # RGB


class Embedder:
    def __init__(self, device: str = "cuda", name: str = "dinov2_vitb14_reg") -> None:
        from drishti_vision.model import Dinov2Extractor
        self.ex = Dinov2Extractor(name, device)
        self.cache: dict[str, np.ndarray] = {}

    def __call__(self, path: Path) -> np.ndarray:
        k = str(path)
        if k not in self.cache:
            f = self.ex.extract(_read(path)[None])[0]             # (gh, gw, D), unit vectors
            v = f.reshape(-1, f.shape[-1]).mean(0)
            self.cache[k] = v / (np.linalg.norm(v) + 1e-8)
        return self.cache[k]


def distance(a: np.ndarray, b: np.ndarray) -> float:
    return float(1.0 - np.dot(a, b))


def asset_change(asset: dict, root: Path, emb: Embedder) -> dict:
    """Distances for one GeoMGNREGA asset and the certainty verdicts for its progress pairs."""
    files = {(p["stage"], p["n"]): root / p["file"] for p in asset["photos"] if p.get("file")}
    e = {k: emb(v) for k, v in files.items()}

    def d(s1: int, s2: int) -> float | None:
        ds = [distance(e[(s1, a)], e[(s2, b)]) for a, b in product((1, 2), (1, 2))
              if (s1, a) in e and (s2, b) in e and (s1, a) != (s2, b)]
        return float(np.mean(ds)) if ds else None

    noise = [x for x in (d(1, 1), d(3, 3)) if x is not None]
    out = {"d13": d(1, 3), "d12": d(1, 2), "d23": d(2, 3), "noise": max(noise) if noise else None}
    for key in ("d13", "d12"):
        v = out[key]
        out[f"ok_{key[1:]}"] = bool(v is not None and out["noise"] is not None
                                    and v > MARGIN * out["noise"] and v > FLOOR)
    return out
