"""Site Progress' held-out cases (T168): written and committed before their first run. The main set
passed on the agent as it was, so these probe subtler ways past it, and honest room for error."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
import world as W  # noqa: E402

_C = W.load(Path(__file__).with_name("cases.py"), "site_progress_cases")
case, v, built, honest_months = _C.case, _C.v, _C.built, _C.honest_months


def _with(visit: dict, **readings) -> dict:
    return {**visit, "readings": {**visit["readings"], **readings}}


def cases():
    out = []
    hm = honest_months()
    out.append(case(
        "SH-H1-two-dark-not-in-a-row", "edge", "fits", "fits/edge", "room for error",
        "Honest months; two of the five monthly videos too dark, not one after the other.",
        "Under 4 of the last 5: forgiven.",
        lambda: built("ZH1", [hm[0], _with(hm[1], quality_ok=False, change=None,
                                           claim_verdict=None), hm[2], hm[3],
                              _with(hm[4], quality_ok=False, change=None,
                                    claim_verdict=None), hm[5]])))
    out.append(case(
        "SH-H2-viewpoint-blocked", "edge", "fits", "fits/edge", "room for error",
        "Honest months; on two visits a viewpoint was blocked by a parked truck and skipped.",
        "A skipped viewpoint is a note.",
        lambda: built("ZH2", [hm[0], hm[1], _with(hm[2], viewpoints_matched=4,
                                                  viewpoints_skipped=["V3"]), hm[3],
                              _with(hm[4], viewpoints_matched=4, viewpoints_skipped=["V3"]),
                              hm[5]])))
    out.append(case(
        "SH-H3-retake-after-unsealed", "edge", "fits", "fits/edge", "room for error",
        "One upload unsealed, retaken the next day properly.",
        "The unsealed one is not accepted; the retake is.",
        lambda: built("ZH3", hm[:3] + [_with(v(9, "monthly", 89), sealed=False), hm[3]] + hm[4:])))

    out.append(case(
        "SH-F1-own-video-again", "evasion", "ask", "ask", "reuse",
        "Last month's video uploaded again as this month's.",
        "Frames already seen on an earlier visit of this same work.",
        lambda: built("ZF1", hm[:4] + [v(6, "monthly", 30, reused_from=[
            {"work_id": "ZF1", "visit_id": "V5", "frames": 120}])])))
    out.append(case(
        "SH-F2-four-of-five-unusable", "evasion", "ask", "check/ask", "room for error",
        "Four of the last five monthly videos too dark, one good between them.",
        "4 of the last 5 (T137).",
        lambda: built("ZF2", [hm[0], hm[1]] + [
            _with(v(10 + i, "monthly", 120 - 20 * i, None, "work going on", None),
                  quality_ok=False) if i != 2 else v(10 + i, "monthly", 120 - 20 * i)
            for i in range(5)])))
    out.append(case(
        "SH-F3-dark-between-not-shown", "evasion", "ask", "ask", "claim",
        "The false claim not shown, then a too-dark video, then not shown again.",
        "A poor video between does not reset the count.",
        lambda: built("ZF3", hm[:3] + [
            v(5, "monthly", 90, claim="roof slab cast", verdict="not_shown"),
            v(6, "monthly", 60, None, "roof slab cast", None, quality_ok=False),
            v(7, "monthly", 30, claim="roof slab cast", verdict="not_shown")])))
    out.append(case(
        "SH-F4-final-at-another-work", "fraud", "ask", "ask", "reuse",
        "Complete; the final video shows the same place as another work's videos.",
        "The finished building is another work's.",
        lambda: built("ZF4", hm + [v(9, "final", 20, claim="complete", complete_shown=True,
                                     same_place_as=[{"work_id": "WF-TIME-2",
                                                     "inliers": 500}])],
                      status="COMPLETED", done_days_ago=25)))
    out.append(case(
        "SH-F5-no-first-visit-late-start", "evasion", "check", "check/ask", "built before",
        "No first visit; the first video is a monthly one, then the final one: complete.",
        "Nothing filmed before work started shows the asset is new.",
        lambda: built("ZF5", [v(1, "monthly", 60, claim="plastering"),
                              v(2, "final", 25, claim="complete", complete_shown=True)],
                      status="COMPLETED", done_days_ago=25)))
    out.append(case(
        "SH-F6-mock-gps-every-month", "evasion", "ask", "ask", "elsewhere",
        "Every monthly video from a phone reporting a mock location, views not matching.",
        "Faked GPS and other views: filmed elsewhere.",
        lambda: built("ZF6", [hm[0]] + [_with(x, mock_location=True, views_match_site=False,
                                              viewpoints_matched=0, change=None,
                                              claim_verdict=None) for x in hm[1:]])))
    out.append(case(
        "SH-B1-readings-all-empty", "broken", "na", "na", "broken",
        "Two videos with every reading empty.",
        "Not read: couldn't check.",
        lambda: built("ZB1", [{"visit_id": "V1", "kind": "baseline",
                               "captured_at": W.m(100).isoformat(),
                               "readings": {"change": None, "claim_verdict": None}},
                              {"visit_id": "V2", "kind": "monthly",
                               "captured_at": W.m(70).isoformat(), "readings": {}}])))
    return out
