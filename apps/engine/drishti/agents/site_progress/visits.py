"""A work's site visits: the monthly videos' readings, as the agents read them (plan T120 §9).

The capture page (web /capture) films a visit; the video job (drishti/video/) reads it once and
stores the readings (migration 014, table site_visits); the batch attaches them to the work as
work["site_visits"]: a list of

    {"visit_id": str, "kind": "baseline" | "monthly" | "check" | "final",
     "captured_at": "YYYY-MM-DD...", "claim": str | None, "readings": {...}}

Readings (every key optional; a missing one means "not read", never "passed"):

    sealed            the upload's hash matches the one sealed when filming ended
    in_app            filmed in the capture page (not uploaded from the gallery)
    gps_inside        the GPS points fall inside the site (with the margin for GPS error)
    gps_distance_m    how far outside the site the GPS points were (median)
    mock_location     the phone reported a mock location
    views_match_site  the viewpoints match this site's own earlier views (None on the first visit)
    viewpoints_expected, viewpoints_matched
    zones_shown       zone ids matched this visit; zones_new: shown for the first time
    change            "changed" | "no_change" | "cant_tell" since the last visit, at the same views
    claim_verdict     "shown" | "not_shown" | "cant_tell": the agency's claim against the views
    claim_reason      the reader's reason, in plain words
    reused_from       [{"work_id", "visit_id", "frames"}]: the same frames seen before
    same_place_as     [{"work_id", "inliers"}]: another work's viewpoints show this place
    asset_at_start    the first visit shows the asset already standing
    complete_shown    on a final visit: every zone shows the finished work
    quality_ok        the video passed the at-site checks (light, coverage, pace)
    motion_consistent the phone's own motion matches the motion in the picture (False: a screen
                      may have been filmed, or the video is not this phone's)

This module only reads: it never raises on a malformed visit, it drops it.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date, datetime

KINDS = ("baseline", "monthly", "check", "final")
MIN_REUSED_FRAMES = 3         # frames already seen elsewhere that make a video not new footage
MIN_INLIERS = 40              # matching points that make two works' views one place


def _date(v) -> date | None:
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    if isinstance(v, str) and len(v) >= 10:
        try:
            return date.fromisoformat(v[:10])
        except ValueError:
            return None
    return None


def _finite(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def _bool(v) -> bool | None:
    return v if isinstance(v, bool) else None


def _ids(v) -> list[str]:
    return [str(x) for x in v if isinstance(x, (str, int)) and not isinstance(x, bool)] \
        if isinstance(v, list) else []


def _refs(v, key: str) -> list[dict]:
    out = []
    for x in v if isinstance(v, list) else []:
        if isinstance(x, dict) and isinstance(x.get("work_id"), str) and x["work_id"]:
            n = x.get(key)
            out.append({**x, key: int(n) if _finite(n) else 0})
    return out


@dataclass
class Visit:
    visit_id: str
    kind: str
    captured: date
    claim: str | None
    readings: dict = field(default_factory=dict)

    def get(self, key: str):
        return self.readings.get(key)

    @property
    def change(self) -> str | None:
        v = self.readings.get("change")
        return v if v in ("changed", "no_change", "cant_tell") else None

    @property
    def claim_verdict(self) -> str | None:
        v = self.readings.get("claim_verdict")
        return v if v in ("shown", "not_shown", "cant_tell") else None

    @property
    def shows_work(self) -> bool:
        """The visit shows the work going on: a change at the same views, or the claim shown."""
        return self.kind != "baseline" and (self.change == "changed"
                                            or self.claim_verdict == "shown")


def of(work: dict) -> list[Visit]:
    """The work's readable visits, oldest first."""
    raw = work.get("site_visits")
    out: list[Visit] = []
    for i, v in enumerate(raw if isinstance(raw, list) else []):
        if not isinstance(v, dict):
            continue
        captured = _date(v.get("captured_at"))
        kind = v.get("kind") if v.get("kind") in KINDS else None
        if captured is None or kind is None:
            continue
        r = v.get("readings") if isinstance(v.get("readings"), dict) else {}
        readings = {k: _bool(r.get(k)) for k in ("sealed", "in_app", "gps_inside",
                                                  "mock_location", "views_match_site",
                                                  "asset_at_start", "complete_shown",
                                                  "quality_ok", "motion_consistent")}
        for k in ("gps_distance_m", "viewpoints_expected", "viewpoints_matched"):
            n = r.get(k)
            readings[k] = float(n) if _finite(n) else None
        readings["zones_shown"] = _ids(r.get("zones_shown"))
        readings["zones_new"] = _ids(r.get("zones_new"))
        for k in ("change", "claim_verdict"):
            readings[k] = r.get(k) if isinstance(r.get(k), str) else None
        reason = r.get("claim_reason")
        readings["claim_reason"] = reason if isinstance(reason, str) else None
        readings["reused_from"] = _refs(r.get("reused_from"), "frames")
        readings["same_place_as"] = _refs(r.get("same_place_as"), "inliers")
        vid = v.get("visit_id")
        claim = v.get("claim")
        out.append(Visit(str(vid) if isinstance(vid, (str, int)) else f"visit-{i + 1}", kind,
                         captured, claim if isinstance(claim, str) and claim.strip() else None,
                         readings))
    out.sort(key=lambda x: (x.captured, KINDS.index(x.kind)))
    return out


def accepted(v: Visit) -> bool:
    """Sealed and filmed in the app, its motion matching its picture: Site Progress reads no
    other video (a rejected one is a note, and a retake is asked for)."""
    return (v.get("sealed") is not False and v.get("in_app") is not False
            and v.get("motion_consistent") is not False)


def genuine(v: Visit) -> bool:
    """Accepted, and nothing in its readings says it is not this site's own new footage: no
    frames seen before, no other work's place, not filmed elsewhere by both GPS and views. Only
    such a video can show the work going on to another agent (T135: one reused video silenced
    Time & Rules' "finished too fast")."""
    if not accepted(v):
        return False
    if any(r["frames"] >= MIN_REUSED_FRAMES for r in v.get("reused_from") or []):
        return False
    if any(r["inliers"] >= MIN_INLIERS for r in v.get("same_place_as") or []):
        return False
    gps_out = v.get("mock_location") is True or v.get("gps_inside") is False
    return not (gps_out and v.get("views_match_site") is False)
