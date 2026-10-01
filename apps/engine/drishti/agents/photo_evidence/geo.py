"""Is a point inside a district? Pure Python, so it runs wherever the engine runs (T310).

Outlines: reference/district_outlines.json (data/build_geo_reference.py, from the LGD
district boundaries the map uses). Works carry Census-2011 district codes in `district_lgd`
(a trap found 26 Sept 2026), so outlines are keyed by that census code, with the real LGD code
kept. PINs: reference/pin_district.json (India Post PIN -> district; its codes are Census-2011
codes too, so a PIN is compared with the work's own code).

The published outlines are simplified: a point within 5 km outside is "at the border", never a
finding (the trial's rule).
"""

from __future__ import annotations

import json
import math
from functools import cache
from pathlib import Path

from drishti import reference

REF = Path(reference.__file__).resolve().parent
KM_PER_DEG = 111.0
BORDER_KM = 5.0


@cache
def outlines() -> dict[str, dict]:
    return json.loads((REF / "district_outlines.json").read_text(encoding="utf-8"))


@cache
def pin_district() -> dict[str, str]:
    return json.loads((REF / "pin_district.json").read_text(encoding="utf-8"))


def _rings(geom: dict) -> list[list[list[float]]]:
    if geom["type"] == "Polygon":
        return [geom["coordinates"]]
    return list(geom["coordinates"])                     # MultiPolygon


def _inside_ring(x: float, y: float, ring: list[list[float]]) -> bool:
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            inside = not inside
        j = i
    return inside


def contains(geom: dict, lat: float, lon: float) -> bool:
    for poly in _rings(geom):
        outer, holes = poly[0], poly[1:]
        if _inside_ring(lon, lat, outer) and not any(_inside_ring(lon, lat, h) for h in holes):
            return True
    return False


def _seg_dist(px, py, ax, ay, bx, by) -> float:
    dx, dy = bx - ax, by - ay
    if dx == dy == 0:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def km_outside(geom: dict, lat: float, lon: float) -> float:
    """Distance from the point to the outline, in km (0 when inside)."""
    if contains(geom, lat, lon):
        return 0.0
    best = math.inf
    for poly in _rings(geom):
        for ring in poly:
            for a, b in zip(ring, ring[1:], strict=False):
                best = min(best, _seg_dist(lon, lat, a[0], a[1], b[0], b[1]))
    return best * KM_PER_DEG


def district_of_point(lat: float, lon: float) -> str | None:
    for o in outlines().values():
        if contains(o["geometry"], lat, lon):
            return o["name"]
    return None
