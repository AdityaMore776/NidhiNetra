"""The spots a site is filmed from (T158, docs/plans/T158-same-spot-filming.md).

For each viewpoint of a visit: where the person stood (`spot`, from the GPS fixes around it) and
which way they faced (`arc`, from the compass headings the phone logged). From the visits so far:
the `anchors` the next visit is guided back to. And how the claim's verdicts at each spot combine
into one (`combine`).

The anchor of a viewpoint is the first trusted visit's spot with a good fix; it moves only while
every earlier fix was poor, so the box cannot creep a little each month. The arc to cover comes
from the same visit, so it cannot shrink month by month either.

Combining (revised from the plan's first draft, 8 Oct 2026): a spot that does not face the part a
claim names answers "not shown" too (the reader sees no change there), so
  a claim about the whole work ("all rooms", "the entire road", "पूरा")
      not_shown  when any spot says not_shown (every spot should show the whole work)
      shown      when one spot says shown and at least half the needed spots were filmed
  a claim about one part
      shown      when any spot says shown
      not_shown  when every judged spot says not_shown and at least half the needed spots were
                 filmed (the part cannot be hiding at a spot nobody filmed)
  anything else is cant_tell, never a finding.
"""

from __future__ import annotations

import math
import re
import statistics

from drishti.agents.site_progress.sitemap import metres

GOOD_FIX_M = 15.0       # a fix this accurate can anchor a viewpoint for good
BOX_M = 6.0             # the box's radius: phone GPS is about 5 m under open sky
FACING_TOL_DEG = 20.0   # facing the anchor's middle within this: facing the right way
COVER_GOOD = 0.7        # this share of last time's arc panned: the same areas shown
PAD_S = 0.5             # GPS fixes this close before or after a viewpoint still place it
HOLD_S = 60.0           # with no fix during a viewpoint, the last one this recent still stands
BIN_DEG = 5.0
VERDICTS = ("shown", "not_shown", "cant_tell")

_WHOLE_EN = re.compile(r"\b(all|every|whole|entire|complete|completely|full|fully|throughout|"
                       r"both)\b", re.IGNORECASE)
_WHOLE_HI = ("सभी", "सारे", "सारी", "पूरा", "पूरी", "पूरे", "संपूर्ण", "सम्पूर्ण")


def _num(v) -> float | None:
    return (float(v) if isinstance(v, (int, float)) and not isinstance(v, bool)
            and math.isfinite(v) else None)


def spot(gps: list, t0: float, t1: float, poor_m: float = 50.0) -> dict | None:
    """The median of the good GPS fixes during a viewpoint (give or take PAD_S: fix timing). A
    phone standing still often reports no new fix (an iPhone reports on a change), so with none
    during the viewpoint the last good fix up to HOLD_S before it stands: no new fix, no move."""
    pts, before = [], None
    for p in gps or []:
        if not isinstance(p, dict):
            continue
        t, lat, lon, acc = (_num(p.get(k)) for k in ("t", "lat", "lon", "accuracy"))
        if None in (t, lat, lon) or (acc is not None and acc > poor_m):
            continue
        if t0 - PAD_S <= t <= t1 + PAD_S:
            pts.append((lat, lon, acc))
        elif t0 - HOLD_S <= t < t0 - PAD_S and (before is None or t > before[0]):
            before = (t, (lat, lon, acc))
    if not pts and before is not None:
        pts = [before[1]]
    if not pts:
        return None
    accs = [a for _la, _lo, a in pts if a is not None]
    return {"lat": statistics.median(p[0] for p in pts),
            "lon": statistics.median(p[1] for p in pts),
            "acc": round(statistics.median(accs), 1) if accs else None}


def headings(log: dict, t0: float, t1: float) -> list[float]:
    """The compass headings (degrees, 0 = north) the phone logged during a viewpoint."""
    out = []
    for h in (log or {}).get("heading") or []:
        if isinstance(h, dict):
            t, deg = _num(h.get("t")), _num(h.get("h"))
            if t is not None and deg is not None and t0 <= t <= t1:
                out.append(deg % 360.0)
    return out


def _diff(a: float, b: float) -> float:
    d = abs(a - b) % 360.0
    return min(d, 360.0 - d)


def arc(degs: list[float]) -> dict | None:
    """The smallest arc holding every heading (it may wrap past north), and its middle."""
    angles = sorted({d % 360.0 for d in degs})
    if not angles:
        return None
    gaps = [(angles[(i + 1) % len(angles)] - a) % 360.0 or (360.0 if len(angles) == 1 else 0.0)
            for i, a in enumerate(angles)]
    i = max(range(len(gaps)), key=gaps.__getitem__)
    start, end = angles[(i + 1) % len(angles)], angles[i]
    width = 360.0 - gaps[i]
    return {"from": round(start, 1), "to": round(end, 1),
            "mid": round((start + width / 2) % 360.0, 1), "width": round(width, 1)}


def covered(first: dict | None, degs: list[float]) -> float | None:
    """The share of an earlier arc that these headings panned across (None without an arc, or
    without any heading: a phone with no compass cannot tell, which is not 0%)."""
    if not first:
        return None
    if not degs:
        return None
    if first["width"] < 2 * BIN_DEG:
        return 1.0 if any(_diff(d, first["mid"]) <= FACING_TOL_DEG for d in degs) else 0.0
    n = math.ceil(first["width"] / BIN_DEG)
    centres = [(first["from"] + BIN_DEG * (k + 0.5)) % 360.0 for k in range(n)]
    hit = sum(any(_diff(d, c) <= BIN_DEG for d in degs) for c in centres)
    return round(hit / n, 3)


def pan_times(log: dict, t0: float, t1: float, facing: dict | None) -> list[float]:
    """When the phone faced the arc's start, middle and end (the 3 pictures across the pan); at a
    sixth, a half and five sixths of the viewpoint without a compass."""
    samples = [(t, d % 360.0) for h in (log or {}).get("heading") or [] if isinstance(h, dict)
               for t, d in [(_num(h.get("t")), _num(h.get("h")))]
               if t is not None and d is not None and t0 <= t <= t1]
    if not facing or not samples:
        return [t0 + (t1 - t0) * f for f in (1 / 6, 1 / 2, 5 / 6)]
    return [min(samples, key=lambda s: (_diff(s[1], target), s[0]))[0]
            for target in (facing["from"], facing["mid"], facing["to"])]


def _trusted(readings: dict) -> bool:
    r = readings or {}
    return (r.get("views_match_site") is not False and r.get("gps_inside") is not False
            and r.get("mock_location") is not True)


def anchors(visits: list[dict]) -> dict[str, dict]:
    """{viewpoint: {"box": {lat, lon, acc, box_m} | None, "facing": {...} | None}} from the
    visits so far, OLDEST FIRST, each {"readings": {...}, "spots": {viewpoint: {"spot": {...},
    "facing": {...}}}}. The facing is the box's visit's, else the first one filmed: a viewpoint
    with no usable GPS still has a way to face."""
    boxes: dict[str, list[tuple[dict, dict | None]]] = {}
    facings: dict[str, dict] = {}
    for v in visits:
        if not isinstance(v, dict) or not _trusted(v.get("readings")):
            continue
        for vid, s in (v.get("spots") or {}).items():
            if not isinstance(s, dict):
                continue
            f = s.get("facing") if isinstance(s.get("facing"), dict) else None
            if f is not None:
                facings.setdefault(vid, f)
            sp = s.get("spot")
            if isinstance(sp, dict) and _num(sp.get("lat")) is not None \
                    and _num(sp.get("lon")) is not None:
                boxes.setdefault(vid, []).append((sp, f))

    def acc(c) -> float:
        a = _num(c[0].get("acc"))
        return GOOD_FIX_M if a is None else a

    out = {}
    for vid in sorted(set(boxes) | set(facings)):
        box, facing = None, facings.get(vid)
        if vid in boxes:
            good = [c for c in boxes[vid] if acc(c) <= GOOD_FIX_M]
            c = good[0] if good else min(boxes[vid], key=acc)
            box = {"lat": c[0]["lat"], "lon": c[0]["lon"], "acc": _num(c[0].get("acc")),
                   "box_m": max(BOX_M, acc(c))}
            facing = c[1] or facing
        out[vid] = {"box": box, "facing": facing}
    return out


def offset_m(anchor: dict | None, here: dict | None) -> float | None:
    if not anchor or not here or _num(here.get("lat")) is None or _num(here.get("lon")) is None:
        return None
    return round(metres(anchor["lat"], anchor["lon"], here["lat"], here["lon"]), 1)


def whole_claim(claim: str | None) -> bool:
    """A claim about the whole work ("all rooms", "the entire road", "पूरा") rather than one part."""
    c = claim or ""
    return bool(_WHOLE_EN.search(c)) or any(w in c for w in _WHOLE_HI)


def combine(verdicts: dict, needed: int, filmed: int, whole: bool) -> str | None:
    """One verdict for the visit from the spots' verdicts (see the module's docstring)."""
    vs = {k: v for k, v in (verdicts or {}).items() if v in VERDICTS}
    if not vs:
        return None
    shown = any(v == "shown" for v in vs.values())
    no = [k for k, v in vs.items() if v == "not_shown"]
    enough = filmed >= math.ceil(max(1, needed) / 2)
    if whole:
        if no:
            return "not_shown"
        return "shown" if shown and enough else "cant_tell"
    if shown:
        return "shown"
    return "not_shown" if no and len(no) == len(vs) and enough else "cant_tell"
