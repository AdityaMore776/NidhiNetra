"""The site map of a work (plan T120 §9.3 and §9.7): where the site is, and its zones.

From the cost estimate form's map pins (site 1):

  compact site (building, pond, lights at one place)
      a circle around the pin: radius = max(MIN_RADIUS_M, the side of the built-up area); its
      zones are the fixed viewpoints set on the first visit (each viewpoint sees its own part of
      the site), so a part of the site is placed by what the camera sees, never by GPS alone
  linear site (road, drain, wall, pipeline: the form has both ends)
      the line between the two pins, cut into STRETCH_M stretches; a GPS point is placed on the
      nearest stretch (a 50 m stretch is ten times phone GPS error)

GPS_MARGIN_M is added to "inside the site" for GPS error: phone GPS is about 4.9 m under open sky
(GPS.gov) and worse near buildings and trees, so a point is "outside" only well beyond that.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from drishti.cost_form import catalog

EARTH_M = 6_371_000.0
MIN_RADIUS_M = 25.0
STRETCH_M = 50.0
GPS_MARGIN_M = 20.0


def _num(v) -> float | None:
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) and v == v else None


def metres(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = (math.sin((p2 - p1) / 2) ** 2
         + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2)
    return 2 * EARTH_M * math.asin(min(1.0, math.sqrt(a)))


def _xy(lat0: float, lon0: float, lat: float, lon: float) -> tuple[float, float]:
    """Local metres east and north of (lat0, lon0)."""
    return (math.radians(lon - lon0) * EARTH_M * math.cos(math.radians(lat0)),
            math.radians(lat - lat0) * EARTH_M)


@dataclass(frozen=True)
class Site:
    kind: str                     # "compact" | "linear"
    lat: float
    lon: float
    radius_m: float = MIN_RADIUS_M
    end_lat: float | None = None
    end_lon: float | None = None

    @property
    def length_m(self) -> float:
        return (metres(self.lat, self.lon, self.end_lat, self.end_lon)
                if self.kind == "linear" else 0.0)

    def stretches(self) -> list[str]:
        n = max(1, math.ceil(self.length_m / STRETCH_M)) if self.kind == "linear" else 0
        return [f"s{i + 1}" for i in range(n)]

    def _along(self, lat: float, lon: float) -> tuple[float, float]:
        """(metres along the line from the start, metres away from it)."""
        ex, ey = _xy(self.lat, self.lon, self.end_lat, self.end_lon)
        px, py = _xy(self.lat, self.lon, lat, lon)
        length = math.hypot(ex, ey) or 1e-9
        t = (px * ex + py * ey) / length
        tc = min(max(t, 0.0), length)
        cx, cy = ex * tc / length, ey * tc / length
        return t, math.hypot(px - cx, py - cy) + max(0.0, -t, t - length)

    def outside_by(self, lat: float, lon: float) -> float:
        """How far a point is outside the site (0 inside), before the GPS margin."""
        if self.kind == "linear":
            return max(0.0, self._along(lat, lon)[1] - self.radius_m)
        return max(0.0, metres(self.lat, self.lon, lat, lon) - self.radius_m)

    def inside(self, lat: float, lon: float) -> bool:
        return self.outside_by(lat, lon) <= GPS_MARGIN_M

    def stretch_of(self, lat: float, lon: float) -> str | None:
        if self.kind != "linear" or not self.inside(lat, lon):
            return None
        t, _ = self._along(lat, lon)
        n = len(self.stretches())
        return f"s{min(n, max(1, int(max(t, 0.0) // STRETCH_M) + 1))}"

    def to_json(self) -> dict:
        return {"kind": self.kind, "lat": self.lat, "lon": self.lon, "radius_m": self.radius_m,
                "end_lat": self.end_lat, "end_lon": self.end_lon,
                "length_m": round(self.length_m, 1), "stretches": self.stretches(),
                "gps_margin_m": GPS_MARGIN_M, "stretch_m": STRETCH_M}


def site_of(form: dict | None, work_type: str | None = None) -> Site | None:
    """The site from the form's first site, or None when it has no usable map pin."""
    if not isinstance(form, dict):
        return None
    sites = form.get("sites")
    site = sites[0] if isinstance(sites, list) and sites and isinstance(sites[0], dict) else {}
    loc = site.get("location") if isinstance(site.get("location"), dict) else {}
    lat, lon = _num(loc.get("lat")), _num(loc.get("lon"))
    if lat is None or lon is None or not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return None
    part = form.get("work") if isinstance(form.get("work"), dict) else {}
    wt = part.get("work_type") if isinstance(part.get("work_type"), str) else work_type
    elat, elon = _num(loc.get("end_lat")), _num(loc.get("end_lon"))
    if catalog.is_linear(wt) and elat is not None and elon is not None:
        return Site("linear", lat, lon, MIN_RADIUS_M / 2, elat, elon)
    size = site.get("size") if isinstance(site.get("size"), dict) else {}
    area = _num(size.get("built_up_area_m2")) or _num(size.get("area_m2"))
    radius = max(MIN_RADIUS_M, math.sqrt(area)) if area and area > 0 else MIN_RADIUS_M
    return Site("compact", lat, lon, radius)
