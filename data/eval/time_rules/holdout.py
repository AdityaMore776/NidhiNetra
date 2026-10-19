"""Time & Rules' held-out cases (T168): written and committed before their first run, after the main
set's fixes (only a video before the completion day clears a fast finish; complete without a date
is "couldn't check")."""

from __future__ import annotations

import sys
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
import world as W  # noqa: E402
from world import d, filed, m  # noqa: E402

_C = W.load(Path(__file__).with_name("cases.py"), "time_rules_cases")
case, visit, monthly, road, hall, record = (_C.case, _C.visit, _C.monthly, _C.road, _C.hall,
                                            _C.record)


def cases():
    out = []
    san = m(200)
    out.append(case(
        "TH-H1-hall-in-70-days-filmed", "honest", "fits", "fits/edge", "fast finish",
        "A hall finished 70 days after its start, filmed every fortnight.",
        "Past the early line and filmed.",
        lambda: filed(hall("YH1", m(240), san, start=san + timedelta(days=10)),
                      status="COMPLETED", completed_date=d(san + timedelta(days=80)),
                      site_visits=monthly(san + timedelta(days=10), san + timedelta(days=79),
                                          every=14))))
    out.append(case(
        "TH-H2-hall-fast-filmed", "edge", "fits", "fits/edge", "fast finish",
        "A small hall finished 40 days after its start (before the early line), filmed twice "
        "being built.",
        "Fast, but the videos show the work going on.",
        lambda: filed(hall("YH2", m(240), san, start=san + timedelta(days=10), area=60),
                      status="COMPLETED", completed_date=d(san + timedelta(days=50)),
                      site_visits=[visit(1, "baseline", san + timedelta(days=10)),
                                   visit(2, "monthly", san + timedelta(days=25)),
                                   visit(3, "check", san + timedelta(days=40))])))
    out.append(case(
        "TH-H3-extension-recorded", "edge", "fits", "fits/edge/check", "late",
        "A road past its promised time, with a 200-day extension the district recorded.",
        "A recorded extension moves the late line.",
        lambda: filed(road("YH3", m(500), m(460), start=m(450)), status="SANCTIONED",
                      time_extension_days=200, site_visits=monthly(m(450), m(20)))))
    out.append(case(
        "TH-H4-waiting-70-days", "honest", "fits", "fits/edge", "waiting",
        "A recommendation 70 days old, not sanctioned yet.",
        "Inside the 75-day clock.",
        lambda: record("YH4", "ROAD_CC", "CC road at Kusumi", 400_000, m(70))))

    out.append(case(
        "TH-F1-filmed-after-done", "evasion", "ask", "check/ask", "fast finish",
        "Complete 5 days after sanction; videos filmed only after the completion date.",
        "Videos after the finish do not show it being built.",
        lambda: filed(road("YF1", m(160), m(120), length=400), status="COMPLETED",
                      completed_date=d(m(115)),
                      site_visits=[visit(1, "monthly", m(100)), visit(2, "monthly", m(70))])))
    out.append(case(
        "TH-F2-reused-then-final", "evasion", "ask", "check/ask", "fast finish",
        "Complete 6 days after sanction; a reused video, then a final video.",
        "Neither shows this work going on.",
        lambda: filed(road("YF2", m(160), m(120), length=400), status="COMPLETED",
                      completed_date=d(m(114)),
                      site_visits=[visit(1, "check", m(117), reused_from=[
                          {"work_id": "WF-TIME-2", "visit_id": "V3", "frames": 40}]),
                          visit(2, "final", m(114))])))
    out.append(case(
        "TH-F3-backdated-10-days", "evasion", "ask", "check/ask", "record",
        "A Rs 7 lakh drain (no form) recorded complete 10 days before its sanction.",
        "R14's '7+ days before the sanction'.",
        lambda: record("YF3", "DRAIN", "Construction of drain at Sarkoni", 700_000, m(300),
                       m(200), m(210))))
    out.append(case(
        "TH-F4-built-same-day", "fraud", "ask", "ask", "record",
        "A Rs 12 lakh road (no form) recorded complete the day it was recommended.",
        "R13.",
        lambda: record("YF4", "ROAD_CC", "CC road at Patarahi", 1_200_000, m(300), m(300),
                       m(300))))
    out.append(case(
        "TH-F5-almost-stalled", "evasion", "check", "check/ask", "late",
        "A hall months past its time; its last three videos: no change, can't tell, no change.",
        "Past its own time: at least a follow-up.",
        lambda: filed(hall("YF5", m(700), m(660), days=240, start=m(640)), status="SANCTIONED",
                      site_visits=monthly(m(640), m(300)) + [
                          visit(30, "monthly", m(90), "no_change", verdict="cant_tell"),
                          visit(31, "monthly", m(60), None, verdict="cant_tell"),
                          visit(32, "monthly", m(30), "no_change", verdict="cant_tell")])))
    out.append(case(
        "TH-B1-sanction-before-recommendation", "broken", "edge", "na/edge/check", "broken",
        "A record sanctioned 30 days before it was recommended.",
        "Dates in an impossible order: at least a note, never a clean chit.",
        lambda: record("YB1", "ROAD_CC", "CC road at Barauli", 400_000, m(100), m(130))))
    return out
