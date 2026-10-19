"""Time & Rules' eval cases (T168): was the work sanctioned on time, and is it being finished in a
believable time? Labelled before the first run; plan docs/plans/T168-agent-evals.md §3.

Two kinds of work: a filing of the website's form (the comfort window from the agency's own
estimate, and what the site videos show), and an eSAKSHI record without a form (the measured
record rules R01, R06, R13, R14).
"""

from __future__ import annotations

import sys
import zlib
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
from world import AGENCY, PLACE, Case, d, filed, m  # noqa: E402  (first: it sets the paths)

import work_form_examples as wf  # noqa: E402

AG = "time_rules"


def _k(ref: str) -> int:
    """A site of its own for each filing (the same on every run)."""
    return zlib.crc32(ref.encode()) % 50


def case(id, truth, ideal, allowed, family, story, why, work, extra=list, pair=None,
         scope="self"):
    return Case(id, AG, truth, ideal, tuple(allowed.split("/")), family, story, why, work, extra,
                pair, scope)


def visit(n, kind, when, change="changed", claim="work in progress", verdict="shown", **more):
    if kind == "baseline":
        return wf.visit(n, kind, when, **more)
    return wf.visit(n, kind, when, change, claim, verdict, **more)


def monthly(start: date, until: date, change="changed", every=30) -> list[dict]:
    """A first visit at the start, then one a month to `until`."""
    vs, n, t = [visit(1, "baseline", start)], 2, start + timedelta(days=every)
    while t <= until:
        vs.append(visit(n, "monthly", t, change))
        n, t = n + 1, t + timedelta(days=every)
    return vs


def road(ref, rec, sanction, days=120, start=None, length=300, **over):
    return wf.road(ref, AGENCY, "Bhawanipur", _k(ref), rec, sanction, length=length, days=days,
                   start=start, **over)


def hall(ref, rec, sanction, days=240, start=None, **over):
    return wf.hall(ref, AGENCY, "Kusumi", _k(ref), rec, sanction, days=days, start=start, **over)


def record(wid, wtype, desc, amount, rec, sanction=None, done=None, status=None) -> dict:
    """An eSAKSHI record without a form."""
    status = status or ("COMPLETED" if done else "SANCTIONED" if sanction else "RECOMMENDED")
    return {"work_id": wid, "source": "SCENARIO", **PLACE, "agency_name": "Office of the "
            "Executive Engineer, RES", "work_type_code": wtype, "description": desc,
            "amount": float(amount), "recommended_date": rec, "sanction_date": sanction,
            "completed_date": done, "status": status, "mp_name": None}


def cases() -> list[Case]:
    out = []
    # ---- honest -------------------------------------------------------------------------------
    san = m(110)
    out.append(case(
        "T-H1-on-track", "honest", "fits", "fits/edge", "in progress",
        "A road sanctioned 110 days ago on a 120-day estimate, filmed changing every month.",
        "Inside its window.",
        lambda: filed(road("TH1", m(140), san, start=san + timedelta(days=10)),
                      status="SANCTIONED",
                      site_visits=monthly(san + timedelta(days=10), m(5)))))
    san2 = m(90)
    out.append(case(
        "T-H2-fast-but-filmed", "edge", "fits", "fits/edge", "fast finish",
        "A short road finished 25 days after its start, filmed being built twice before.",
        "A real fast finish is filmed: never asked.",
        lambda: filed(road("TH2", m(130), san2, start=san2 + timedelta(days=5), length=120),
                      status="COMPLETED", completed_date=d(san2 + timedelta(days=30)),
                      site_visits=[visit(1, "baseline", san2 + timedelta(days=5)),
                                   visit(2, "check", san2 + timedelta(days=15)),
                                   visit(3, "monthly", san2 + timedelta(days=27))]),
        pair="fast"))
    out.append(case(
        "T-H3-sanctioned-late", "honest", "edge", "fits/edge", "late sanction",
        "Sanctioned 130 days after the recommendation, then built on time.",
        "A late sanction is the office's pace (60% of works), never a finding about the work.",
        lambda: filed(road("TH3", m(200), m(70), start=m(60)), status="SANCTIONED",
                      site_visits=monthly(m(60), m(5)))))
    out.append(case(
        "T-H4-late-but-moving", "edge", "check", "fits/edge/check", "late",
        "A hall past its promised time (with grace), still filmed changing every month.",
        "Most works finish late: a follow-up at most, never a question.",
        lambda: filed(hall("TH4", m(560), m(520), days=240, start=m(500)), status="SANCTIONED",
                      site_visits=monthly(m(500), m(10))), pair="late"))
    out.append(case(
        "T-H5-record-normal", "honest", "fits", "fits/edge", "record",
        "A Rs 8 lakh community hall (no form) completed 200 days after sanction.",
        "An ordinary pace.",
        lambda: record("TH5", "COMMUNITY_HALL", "Construction of community hall at Kusumi",
                       800_000, m(500), m(450), m(250))))
    out.append(case(
        "T-H6-purchase-fast", "honest", "fits", "fits/edge", "record",
        "Computers for a school (no form) delivered 3 days after sanction.",
        "A purchase is delivered, not built: never a fast-finish question.",
        lambda: record("TH6", "COMPUTERS", "Supply of 10 computers to the primary school "
                       "Kusumi", 400_000, m(200), m(150), m(147))))
    out.append(case(
        "T-H7-waiting-40-days", "honest", "fits", "fits/edge", "waiting",
        "A recommendation 40 days old, not sanctioned yet.",
        "Inside the 75-day clock.",
        lambda: record("TH7", "ROAD_CC", "CC road at Bhawanipur", 400_000, m(40))))
    out.append(case(
        "T-H8-waiting-long", "edge", "check", "edge/check", "waiting",
        "A recommendation waiting 300 days for sanction.",
        "Past the clock: the office's delay, a follow-up, never fraud by the agency.",
        lambda: record("TH8", "ROAD_CC", "CC road at Nayagaon", 400_000, m(300))))

    # ---- fraud --------------------------------------------------------------------------------
    san3 = m(100)
    out.append(case(
        "T-F1-done-in-6-days", "fraud", "ask", "ask", "fast finish",
        "A 350 m road recorded complete 6 days after sanction, never filmed.",
        "A road this size is not built in 6 days (R14 line); nothing shows it.",
        lambda: filed(road("TF1", m(140), san3, length=350), status="COMPLETED",
                      completed_date=d(san3 + timedelta(days=6))), pair="fast"))
    out.append(case(
        "T-F2-done-before-recommended", "fraud", "ask", "check/ask", "record",
        "A record (no form) completed 60 days before it was recommended.",
        "R06: dates in an impossible order, outside a bulk-entry quarter.",
        lambda: record("TF2", "ROAD_CC", "CC road at Madhopur", 450_000, m(200), m(150),
                       m(260))))
    out.append(case(
        "T-F3-built-in-days", "fraud", "ask", "ask", "record",
        "A Rs 8 lakh hall (no form) recorded complete 5 days after recommendation.",
        "R13: a construction this size cannot be finished that fast.",
        lambda: record("TF3", "COMMUNITY_HALL", "Construction of community hall at Sonbarsa",
                       800_000, m(200), m(198), m(195))))
    out.append(case(
        "T-F4-right-after-sanction", "fraud", "ask", "ask", "record",
        "A Rs 6 lakh road (no form) recorded complete 3 days after its sanction.",
        "R14 (25 of 25 read).",
        lambda: record("TF4", "ROAD_CC", "CC road at Ujarpur", 600_000, m(300), m(200), m(197))))
    out.append(case(
        "T-F5-abandoned", "fraud", "ask", "ask", "late",
        "A hall 9 months past its promised time; the last three videos show no change.",
        "Stopped: ask why.",
        lambda: filed(hall("TF5", m(700), m(660), days=240, start=m(640)), status="SANCTIONED",
                      site_visits=monthly(m(640), m(300)) + [
                          visit(20 + i, "monthly", m(90 - 30 * i), "no_change", verdict="cant_tell")
                          for i in range(3)]), pair="late"))

    # ---- evasion ------------------------------------------------------------------------------
    san4 = m(100)
    out.append(case(
        "T-V1-filmed-on-the-last-day", "evasion", "ask", "check/ask", "fast finish",
        "Complete 6 days after sanction; one video, filmed on the completion day, 'changed'.",
        "One video on the day it is called complete does not show the work going on.",
        lambda: filed(road("TV1", m(140), san4, length=350), status="COMPLETED",
                      completed_date=d(san4 + timedelta(days=6)),
                      site_visits=[visit(1, "final", san4 + timedelta(days=6))])))
    out.append(case(
        "T-V2-start-years-away", "evasion", "check", "check/ask", "late",
        "Sanctioned 500 days ago, a 120-day estimate, the start declared two years after sanction.",
        "A declared start counts at most 6 months after sanction (T135).",
        lambda: filed(road("TV2", m(540), m(500), start=m(500) + timedelta(days=730)),
                      status="SANCTIONED")))
    out.append(case(
        "T-V3-ten-year-estimate", "evasion", "check", "check/ask", "late",
        "A road with a 10-year estimate, sanctioned 2 years ago, nothing filmed for a year.",
        "An estimate over twice the usual buys only the typical time.",
        lambda: filed(road("TV3", m(770), m(730), days=3650), status="SANCTIONED")))
    out.append(case(
        "T-V4-padded-estimate", "evasion", "check", "check/ask", "late",
        "A road with a 700-day estimate, sanctioned 900 days ago, not finished, never filmed.",
        "An estimate past the usual buys only the usual time (9 in 10 finished works).",
        lambda: filed(road("TV4", m(940), m(900), days=700), status="SANCTIONED")))
    out.append(case(
        "T-V5-reused-video", "evasion", "ask", "ask", "fast finish",
        "Complete 6 days after sanction; its video reuses another work's footage.",
        "A reused video never shows this work going on.",
        lambda: filed(road("TV5", m(140), san4, length=350), status="COMPLETED",
                      completed_date=d(san4 + timedelta(days=6)),
                      site_visits=[visit(1, "baseline", san4 + timedelta(days=1)),
                                   visit(2, "check", san4 + timedelta(days=4),
                                         reused_from=[{"work_id": "WF-TIME-2",
                                                       "visit_id": "V3", "frames": 40}])])))
    out.append(case(
        "T-V6-nine-days-after-sanction", "evasion", "check", "check/ask", "record",
        "A Rs 6 lakh road (no form) recorded complete 9 days after its sanction.",
        "Two days past R14's 7-day line: as unbelievable for a road. LIMIT (after the first "
        "run): R14's line was measured on the dashboard's sanction dates (25 of 25 at 0-7 days); "
        "widening it needs the same measurement at 8-21 days, and no table with sanction dates "
        "is on this PC. With a form the comfort window catches it (T-F1).",
        lambda: record("TV6", "ROAD_CC", "CC road at Siddhipur", 600_000, m(300), m(200),
                       m(191)), scope="limit"))
    out.append(case(
        "T-V7-backdated-complete", "evasion", "ask", "check/ask", "record",
        "A Rs 6 lakh road (no form) recorded complete 20 days BEFORE its sanction.",
        "R14 includes 7+ days before the sanction.",
        lambda: record("TV7", "ROAD_CC", "CC road at Lalganj Khurd", 600_000, m(300), m(200),
                       m(220))))

    # ---- broken -------------------------------------------------------------------------------
    out.append(case(
        "T-B1-no-status", "broken", "na", "na", "broken",
        "A record with no status.",
        "Its dates cannot be read against a status.",
        lambda: {**record("TB1", "ROAD_CC", "CC road at Patarahi", 400_000, m(100)),
                 "status": None}))
    out.append(case(
        "T-B2-complete-no-date", "broken", "na", "na/check", "broken",
        "A Rs 6 lakh road recorded complete with no completion date (no form).",
        "How fast it was finished cannot be checked: not a clean chit.",
        lambda: record("TB2", "ROAD_CC", "CC road at Belahari", 600_000, m(300), m(200),
                       None, status="COMPLETED")))
    out.append(case(
        "T-B3-done-in-future", "broken", "na", "na/edge/check", "broken",
        "A record completed on a date after the data was published.",
        "R06's second half: a date that has not happened yet (LOW).",
        lambda: record("TB3", "ROAD_CC", "CC road at Harihar Tola", 400_000, m(300), m(200),
                       m(-60))))
    return out
