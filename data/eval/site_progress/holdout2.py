"""Site Progress: the owner's location rule (T168, 20 Oct 2026), as scenarios. Written after the rule
(LOCATION_NOT_RECORDED, FILMED_AWAY_FROM_FORM_SITE) from the owner's words, so they check the rule
as asked, not how it generalises: "each site check every time period also captures the location it
was taken at; if it differs a lot from where the form says the project is (a little is fine,
markers aren't fully accurate, a small rough area), flag it"."""

from __future__ import annotations

import sys
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
import world as W  # noqa: E402

import work_form_examples as wf  # noqa: E402

_C = W.load(Path(__file__).with_name("cases.py"), "site_progress_cases")
case, v, built, honest_months = _C.case, _C.v, _C.built, _C.honest_months
METRE = wf.METRE


def _pin(ref: str) -> tuple[float, float]:
    return wf.pin(zlib.crc32(ref.encode()) % 50)      # the same site cases.hall gives the work


def _at(ref: str, north_m: float, accuracy: float = 8.0) -> dict:
    lat, lon = _pin(ref)
    return {"gps_point": {"lat": round(lat + north_m * METRE, 6), "lon": lon},
            "gps_accuracy_m": accuracy, "gps_fixes": 25, "gps_weak": False}


def _months(ref: str, where: list[dict]) -> list[dict]:
    """honest_months, each video with its own location reading."""
    return [{**x, "readings": {**x["readings"], **w}} for x, w in zip(honest_months(), where,
                                                                      strict=True)]


def cases():
    out = []
    out.append(case(
        "SL-H1-filmed-around-the-site", "honest", "fits", "fits/edge", "location",
        "Every video records its location, all within 60 m of the form's pin (standing back to film).",
        "Inside the small rough area.",
        lambda: built("LH1", _months("LH1", [_at("LH1", d) for d in (0, 30, -45, 60, 20, 55)]))))
    out.append(case(
        "SL-H2-one-month-gps-off", "edge", "fits", "fits/edge", "location",
        "One monthly video without a location (GPS was off that day); the rest recorded.",
        "One is forgiven: a note asks for the location next time.",
        lambda: built("LH2", _months("LH2", [_at("LH2", 0), _at("LH2", 10), {"gps_fixes": 0},
                                             _at("LH2", 5), _at("LH2", 15), _at("LH2", 0)]))))
    out.append(case(
        "SL-H3-weak-gps-honest-accuracy", "edge", "fits", "fits/edge", "location",
        "Under trees: one video 110 m off with the phone saying +-45 m.",
        "The phone's own accuracy is allowed for.",
        lambda: built("LH3", _months("LH3", [_at("LH3", 0), _at("LH3", 10), _at("LH3", 110, 45),
                                             _at("LH3", 5), _at("LH3", 15), _at("LH3", 0)]))))
    out.append(case(
        "SL-F1-one-month-elsewhere", "evasion", "check", "check/ask", "location",
        "One monthly video recorded 450 m from the form's site (its views still look like the site).",
        "A lot more than a little: check this.",
        lambda: built("LF1", _months("LF1", [_at("LF1", 0), _at("LF1", 10), _at("LF1", 450),
                                             _at("LF1", 5), _at("LF1", 15), _at("LF1", 0)]))))
    out.append(case(
        "SL-F2-filmed-far-twice", "evasion", "ask", "ask", "location",
        "Two monthly videos recorded 300 m and 800 m from the form's site.",
        "Twice: a question.",
        lambda: built("LF2", _months("LF2", [_at("LF2", 0), _at("LF2", 300), _at("LF2", 0),
                                             _at("LF2", 800), _at("LF2", 15), _at("LF2", 0)]))))
    out.append(case(
        "SL-F3-gps-off-every-month", "evasion", "ask", "ask", "location",
        "The last three videos filmed with location off.",
        "Never recording where it was filmed dodges every location check.",
        lambda: built("LF3", _months("LF3", [_at("LF3", 0), _at("LF3", 10), _at("LF3", 0),
                                             {"gps_fixes": 0}, {"gps_fixes": 0},
                                             {"gps_fixes": 0}]))))
    out.append(case(
        "SL-F4-mock-location-twice", "evasion", "check", "check/ask", "location",
        "Two of the last three videos from a phone faking its location (views still matching).",
        "A faked location is not a recorded location.",
        lambda: built("LF4", _months("LF4", [_at("LF4", 0), _at("LF4", 10), _at("LF4", 0),
                                             {**_at("LF4", 0), "mock_location": True},
                                             _at("LF4", 5),
                                             {**_at("LF4", 0), "mock_location": True}]))))
    out.append(case(
        "SL-H4-old-readings", "honest", "fits", "fits/edge", "location",
        "Videos read before the fix count was recorded (no GPS fields at all).",
        "A reading that was not made says nothing: never a finding.",
        lambda: built("LH4", honest_months())))
    return out
