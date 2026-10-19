"""Duplicate Work's held-out cases (T168): written and committed before their first run, after the
main set's fixes (SPLIT_NEAR_LIMIT, SAME_BUILDING_NEAR, a pin that cannot be compared), to test
whether those fixes hold on cases they were not built on, and stay quiet on honest look-alikes."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
import world as W  # noqa: E402
from world import OTHER, filed, m  # noqa: E402

_C = W.load(Path(__file__).with_name("cases.py"), "dup_split_cases")
at, case, done, hall, lights, piece, road, video = (_C.at, _C.case, _C.done, _C.hall, _C.lights,
                                                     _C.piece, _C.road, _C.video)


def cases():
    out = []
    # ---- honest look-alikes of the new rules ------------------------------------------------
    out.append(case(
        "DH-H1-two-halls-70m-other-size", "honest", "edge", "fits/edge", "neighbour",
        "A small new hall 70 m from the village's big old hall, in the same words.",
        "Another size: two buildings; the near note is enough.",
        lambda: filed(hall("XH1", 30, north=70, area=90)),
        lambda: [done(hall("XH1-OLD", 30, agency=OTHER[0], area=220), 500)]))
    out.append(case(
        "DH-H2-phase-two-60-days", "edge", "edge", "fits/edge/check", "split look-alike",
        "A road's declared phase II, filed 60 days after phase I, both at Rs 5 lakh.",
        "Declared and numbered; 'check this' is tolerated, never a question.",
        lambda: filed(piece("XH2-2", 31, 1, 500_000, m(40), work_nature="Extension / additional component",
                            prior_work_id="XH2-1", known_nearby_work_ids="XH2-1",
                            nearby_work_relationship="Same asset, separate phase")),
        lambda: [filed(piece("XH2-1", 31, 0, 500_000, m(100)), status="SANCTIONED")]))
    out.append(case(
        "DH-H3-borewells-two-blocks", "honest", "fits", "fits/edge", "split look-alike",
        "Two borewell-like pieces at 95% of the limit at two blocks, different words, same day.",
        "Different spots: never a split.",
        lambda: filed(piece("XH3-2", 32, 1, 476_000, m(30), gap=400, village="Barauli",
                            work_title="CC road at D-Block, Barauli",
                            scope_of_work="Construction of a CC road at D-Block of Barauli "
                                          "colony, 95 m long.")),
        lambda: [filed(piece("XH3-1", 32, 0, 474_000, m(30), village="Barauli",
                             work_title="CC road at C-Block, Barauli",
                             scope_of_work="Construction of a CC road at C-Block of Barauli "
                                           "colony, 95 m long."))]))
    out.append(case(
        "DH-H4-light-21m", "honest", "fits", "fits/edge", "neighbour",
        "A light 21 m from last year's light (the next house's pole).",
        "Just past one spot.",
        lambda: filed(lights("XH4", 33, north=21)),
        lambda: [done(lights("XH4-OLD", 33, agency=OTHER[1]), 300)]))

    # ---- fraud and evasion --------------------------------------------------------------------
    out.append(case(
        "DH-F1-hall-120m-same", "evasion", "check", "check/ask", "pin typed off",
        "The old hall filed again, same words and size, its pin typed 120 m off.",
        "Inside the 150 m near line: at least 'check this'.",
        lambda: filed(hall("XF1", 34, north=120)),
        lambda: [done(hall("XF1-OLD", 34, agency=OTHER[2]), 450)]))
    out.append(case(
        "DH-F2-four-parts-92pct", "evasion", "check", "check/ask", "split",
        "One lane in four numbered parts at 91.6-92.4% of Rs 5 lakh, within 10 days.",
        "Numbered parts just under a limit.",
        lambda: filed(piece("XF2-2", 35, 1, 460_000, m(56))),
        lambda: [filed(piece("XF2-1", 35, 0, 458_000, m(60))),
                 filed(piece("XF2-3", 35, 2, 461_000, m(53))),
                 filed(piece("XF2-4", 35, 3, 462_000, m(50)))]))
    out.append(case(
        "DH-F3-split-85-days", "evasion", "check", "check/ask", "split",
        "Two pieces of one lane at 99% of Rs 5 lakh, 85 days apart.",
        "The same job spread over months.",
        lambda: filed(piece("XF3-2", 36, 1, 496_000, m(30))),
        lambda: [filed(piece("XF3-1", 36, 0, 497_000, m(115)))]))
    out.append(case(
        "DH-F4-rebuild-called-new", "evasion", "ask", "ask", "same site",
        "A hall finished 16 months ago, filed as a 'new asset' 30 m from it.",
        "The pin says one site, whatever the form calls it.",
        lambda: filed(hall("XF4", 37, north=30)),
        lambda: [done(hall("XF4-OLD", 37, agency=OTHER[3]), 485)]))
    out.append(case(
        "DH-F5-light-15m-other-agency", "fraud", "ask", "ask", "same site",
        "Lights 15 m from last year's lights, filed by another agency.",
        "Inside one spot (20 m), not one programme.",
        lambda: filed(lights("XF5", 38, north=15, agency="Prakash Urja Agency")),
        lambda: [done(lights("XF5-OLD", 38, agency=OTHER[4]), 300)]))
    out.append(case(
        "DH-F6-road-reversed", "evasion", "ask", "ask", "same site",
        "The old road filed again with its two ends swapped.",
        "The same line, walked the other way.",
        lambda: filed(road("XF6", 39, north=291, end_lat=f"{at(39)[0]:.6f}",
                           end_lon=f"{at(39)[1]:.6f}")),
        lambda: [done(road("XF6-OLD", 39, agency=OTHER[0]), 330)]))
    old = at(40)
    out.append(case(
        "DH-F7-hall-45m-filmed", "evasion", "ask", "ask", "same site",
        "A hall pinned 45 m from a hall still being built, with its videos filmed there.",
        "Inside the one-site line.",
        lambda: filed(hall("XF7", 40, north=45, rec=m(160), sanction=m(130), start=m(110)),
                      status="SANCTIONED",
                      site_visits=[video(1, "baseline", m(110), *old)]),
        lambda: [filed(hall("XF7-OLD", 40, agency=OTHER[1], rec=m(400), sanction=m(360)),
                       status="SANCTIONED")]))

    # ---- broken -------------------------------------------------------------------------------
    out.append(case(
        "DH-B1-pin-zero", "broken", "na", "na/check/ask", "broken",
        "A form whose map pin is 0, 0, on an old road's site.",
        "A pin that cannot be compared is not a clean chit.",
        lambda: filed(road("XB1", 41, latitude="0", longitude="0", start_lat="0",
                           start_lon="0", end_lat="0", end_lon="0.001")),
        lambda: [done(road("XB1-OLD", 41, agency=OTHER[2]), 330)]))
    return out
