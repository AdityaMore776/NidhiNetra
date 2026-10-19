"""Duplicate Work's eval cases (T168): is this work already sanctioned here, or one job cut to stay
under a limit? Labelled before the first run; plan docs/plans/T168-agent-evals.md §3.

Each case is a filing by a made-up agency in Jaunpur and, where it matters, the earlier works of
the district it should (or should not) be compared with. Geometry follows T139's real Jaunpur:
houses 8 m apart, lanes 25-35 m apart, one programme's lights filed the same day.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
from world import AGENCY, OTHER, Case, d, filed, m  # noqa: E402  (first: it sets the paths)

import work_form_examples as wf  # noqa: E402

AG = "dup_split"
LON_M = wf.METRE / math.cos(math.radians(wf.BASE[0]))     # one metre east, in degrees


def at(k: int, north: float = 0.0, east: float = 0.0) -> tuple[float, float]:
    lat, lon = wf.pin(k)
    return lat + north * wf.METRE, lon + east * LON_M


def road(ref, k, length=300.0, north=0.0, east=0.0, agency=AGENCY, village="Bhawanipur",
         rec=None, sanction=None, eastward=False, **over):
    """A road starting `north`/`east` metres from site k's pin, running north (or east)."""
    la, lo = at(k, north, east)
    ela, elo = at(k, north + (0 if eastward else length * 0.97), east + (length * 0.97 if eastward else 0))
    geo = {"latitude": f"{la:.6f}", "longitude": f"{lo:.6f}", "start_lat": f"{la:.6f}",
           "start_lon": f"{lo:.6f}", "end_lat": f"{ela:.6f}", "end_lon": f"{elo:.6f}"}
    geo.update(over)
    return wf.road(ref, agency, village, k, rec or m(50), sanction, length=length, **geo)


def hall(ref, k, north=0.0, east=0.0, agency=AGENCY, village="Kusumi", rec=None, sanction=None,
         area=180, **over):
    la, lo = at(k, north, east)
    return wf.hall(ref, agency, village, k, rec or m(45), sanction, area=area,
                   latitude=f"{la:.6f}", longitude=f"{lo:.6f}", **over)


def lights(ref, k, north=0.0, east=0.0, agency=AGENCY, village="Nayagaon", rec=None, **over):
    la, lo = at(k, north, east)
    return wf.lights(ref, agency, village, k, rec or m(40), 30_000, 300_000,
                     latitude=f"{la:.6f}", longitude=f"{lo:.6f}", **over)


def done(p, days_ago: int) -> dict:
    """An earlier work: recommended `days_ago` + 200 days back, sanctioned 40 days later,
    completed `days_ago`."""
    rec, san = m(days_ago + 200), m(days_ago + 160)
    p.update(mp_recommendation_date=d(rec), ida_received_date=d(rec), sanction_date=d(san),
             sanction_decision="Sanction")
    return filed(p, status="COMPLETED", completed_date=d(m(days_ago)), sanction_date=d(san))


def piece(ref, k, i, amount, rec, length=95.0, village="Pratappur", gap=100.0, **over):
    words = {"work_title": f"CC road in village {village}, part {i + 1}",
             "scope_of_work": f"Construction of a CC road in village {village}, part {i + 1} of "
                              "the lane from the main road to the harijan basti, 95 m long, "
                              "3.5 m wide, 150 mm thick in M20 over a WBM base."}
    words.update(over)
    p = road(ref, k, length=length, north=gap * i, village=village, rec=rec, **words)
    p["mp_recommended_amount"] = str(round(amount))
    return p


def video(n, kind, when, lat, lon, change="changed", claim=None, verdict="shown"):
    return wf.visit(n, kind, when, change if kind != "baseline" else None, claim,
                    verdict if kind != "baseline" else None,
                    gps_point={"lat": lat, "lon": lon})


def case(id, truth, ideal, allowed, family, story, why, work, extra=list, pair=None,
         scope="self"):
    return Case(id, AG, truth, ideal, tuple(allowed.split("/")), family, story, why, work, extra,
                pair, scope)


def cases() -> list[Case]:
    out = []

    # ---- honest -----------------------------------------------------------------------------
    out.append(case(
        "D-H1-new-road", "honest", "fits", "fits", "new site",
        "A new road in a village with no earlier work near it.",
        "Nothing sanctioned within 150 m.",
        lambda: filed(road("DH1", 0))))
    out.append(case(
        "D-H2-hall-300m", "honest", "fits", "fits/edge", "neighbour",
        "A new hall 300 m from the village's old hall.",
        "Two halls 300 m apart are two buildings.",
        lambda: filed(hall("DH2", 1)),
        lambda: [done(hall("DH2-OLD", 1, north=300, agency=OTHER[0]), 600)]))
    out.append(case(
        "D-H3-next-lane", "honest", "fits", "fits/edge", "neighbour",
        "A new lane 30 m east of an old lane, parallel to it (the next street over).",
        "T139: the next street over is 25-35 m away; its ends are near but it is not on the line.",
        lambda: filed(road("DH3", 2, east=30)),
        lambda: [done(road("DH3-OLD", 2, agency=OTHER[1]), 400)], pair="lane-30m"))
    out.append(case(
        "D-H4-light-next-house", "honest", "fits", "fits/edge", "neighbour",
        "Lights at the next row of houses, 25 m from lights finished last year.",
        "A light is one spot (20 m); 25 m is another house's pole.",
        lambda: filed(lights("DH4", 3, north=25)),
        lambda: [done(lights("DH4-OLD", 3, agency=OTHER[2]), 300)], pair="light-spot"))
    out.append(case(
        "D-H5-light-same-programme", "honest", "fits", "fits/edge", "programme",
        "Two lights 8 m apart filed the same day by one programme.",
        "T139: one programme's houses are not 'already sanctioned' before each other.",
        lambda: filed(lights("DH5-B", 4, north=8, rec=m(40))),
        lambda: [filed(lights("DH5-A", 4, rec=m(40)), status="SANCTIONED",
                       sanction_date=d(m(10)))]))
    out.append(case(
        "D-H6-crossing-road", "honest", "fits", "fits/edge", "neighbour",
        "A new road crossing an old one at right angles.",
        "Two roads share one point where they cross, not their ground.",
        lambda: filed(road("DH6", 5, north=150, east=-150, village="Madhopur", eastward=True)),
        lambda: [done(road("DH6-OLD", 5, village="Madhopur", agency=OTHER[3]), 500)]))
    out.append(case(
        "D-H7-two-works-70pct", "honest", "fits", "fits", "split look-alike",
        "Two roads at one place, each about 70% of the Rs 5 lakh limit.",
        "Pieces far below a limit are not cut to stay under it.",
        lambda: filed(piece("DH7-2", 6, 1, 352_000, m(60))),
        lambda: [filed(piece("DH7-1", 6, 0, 349_000, m(64)))], pair="split-share"))

    # ---- honest but unusual (edge) ----------------------------------------------------------
    out.append(case(
        "D-E1-declared-extension", "edge", "edge", "fits/edge", "declared",
        "A road declared as the extension of a finished road, starting at its end.",
        "A real continuation beside it: a note naming the earlier work.",
        lambda: filed(road("DE1", 7, north=300, work_nature="Extension / additional component",
                           prior_work_id="DE1-OLD", known_nearby_work_ids="DE1-OLD",
                           nearby_work_relationship="Same asset, separate phase")),
        lambda: [done(road("DE1-OLD", 7, agency=OTHER[4]), 500)]))
    out.append(case(
        "D-E2-rebuild-after-4y", "edge", "edge", "fits/edge", "declared",
        "A hall rebuilt, declared, four years after the old one was finished.",
        "Past the 3-year line a rebuild is plausible wear; a note.",
        lambda: filed(hall("DE2", 8, work_nature="Reconstruction / rebuild",
                           prior_work_id="DE2-OLD", existing_asset_same_site="Yes",
                           repeat_reason="Roof failed after four monsoons",
                           known_nearby_work_ids="DE2-OLD",
                           nearby_work_relationship="Rebuild / replacement")),
        lambda: [done(hall("DE2-OLD", 8, agency=OTHER[0]), 4 * 365 + 60)], pair="rebuild-age"))

    # ---- fraud --------------------------------------------------------------------------------
    out.append(case(
        "D-F1-road-on-old-road", "fraud", "ask", "ask", "same site",
        "A 'new' road pinned 20 m from a road finished last year; the form does not mention it.",
        "The same road paid for twice.",
        lambda: filed(road("DF1", 9, north=20)),
        lambda: [done(road("DF1-OLD", 9, agency=OTHER[1]), 330)], pair="lane-30m"))
    out.append(case(
        "D-F2-rebuild-16m", "fraud", "ask", "ask", "declared",
        "A hall declared rebuilt 16 months after the old one was finished.",
        "A new hall does not need rebuilding this soon.",
        lambda: filed(hall("DF2", 10, work_nature="Reconstruction / rebuild",
                           prior_work_id="DF2-OLD", existing_asset_same_site="Yes",
                           repeat_reason="Cracks after the monsoon",
                           known_nearby_work_ids="DF2-OLD",
                           nearby_work_relationship="Rebuild / replacement")),
        lambda: [done(hall("DF2-OLD", 10, agency=OTHER[2]), 485)], pair="rebuild-age"))
    out.append(case(
        "D-F3-split-3-parts", "fraud", "ask", "ask", "split",
        "One lane filed as three parts, each 98.6-99.6% of Rs 5 lakh.",
        "The strictest split.",
        lambda: filed(piece("DF3-2", 11, 1, 495_500, m(66))),
        lambda: [filed(piece("DF3-1", 11, 0, 493_000, m(70))),
                 filed(piece("DF3-3", 11, 2, 498_000, m(62)))], pair="split-share"))
    out.append(case(
        "D-F4-hall-refiled", "fraud", "ask", "ask", "same site",
        "The same hall filed again by another agency, its pin 10 m from the sanctioned one.",
        "One building, two works.",
        lambda: filed(hall("DF4", 12, north=10, agency="Jan Suvidha Works")),
        lambda: [filed(hall("DF4-OLD", 12, agency=OTHER[3], rec=m(200), sanction=m(160)),
                       status="SANCTIONED")]))
    out.append(case(
        "D-F5-light-on-light", "fraud", "ask", "ask", "same site",
        "A new light 5 m from a light finished last year (not one programme).",
        "One pole, two works.",
        lambda: filed(lights("DF5", 13, north=5)),
        lambda: [done(lights("DF5-OLD", 13, agency=OTHER[4]), 300)], pair="light-spot"))

    # ---- evasion: a fraud dressed to slip past a rule --------------------------------------
    old_hall = at(14)
    out.append(case(
        "D-V1-pin-70m-filmed-old", "evasion", "ask", "ask", "pin typed off",
        "The pin typed 70 m off an old hall; two site videos filmed at the old hall.",
        "T160: where the videos were filmed shows the real site.",
        lambda: filed(hall("DV1", 14, north=70, rec=m(200), sanction=m(170), start=m(150)),
                      status="SANCTIONED",
                      site_visits=[video(1, "baseline", m(150), *old_hall),
                                   video(2, "monthly", m(120), *old_hall, claim="walls up")]),
        lambda: [done(hall("DV1-OLD", 14, agency=OTHER[0]), 500)]))
    out.append(case(
        "D-V2-pin-70m-before-sanction", "evasion", "check", "check/ask", "pin typed off",
        "The same hall re-filed with its pin typed 70 m off, before sanction (no video yet).",
        "Only the pin is known; a same-kind building 70 m away, same size, not named: at least "
        "'check this' (the owner's rule: a fraud is never an edge case).",
        lambda: filed(hall("DV2", 15, north=70)),
        lambda: [done(hall("DV2-OLD", 15, agency=OTHER[1]), 500)], pair="hall-70m"))
    out.append(case(
        "D-V3-rebuild-called-upgrade", "evasion", "ask", "ask", "declared",
        "A hall finished 16 months ago, filed again as an 'upgrade' of itself, same size.",
        "T135: a continuation on the old work's own ground with its size is a rebuild.",
        lambda: filed(hall("DV3", 16, work_nature="Repair / renovation", prior_work_id="DV3-OLD",
                           known_nearby_work_ids="DV3-OLD",
                           nearby_work_relationship="Same asset, separate phase")),
        lambda: [done(hall("DV3-OLD", 16, agency=OTHER[2]), 485)]))
    out.append(case(
        "D-V4-split-95pct", "evasion", "check", "check/ask", "split",
        "Three parts of one lane at 94.6-95.4% of Rs 5 lakh: just below the strictest line.",
        "Moved 1% to dodge the 96% line: at least 'check this'.",
        lambda: filed(piece("DV4-2", 17, 1, 476_000, m(66))),
        lambda: [filed(piece("DV4-1", 17, 0, 473_000, m(70))),
                 filed(piece("DV4-3", 17, 2, 477_000, m(62)))], pair="split-share"))
    out.append(case(
        "D-V5-split-35-days", "evasion", "check", "check/ask", "split",
        "Three parts at 98-99.6% of Rs 5 lakh, filed 35 days apart.",
        "Spread past the 30-day window to dodge it: at least 'check this'.",
        lambda: filed(piece("DV5-2", 18, 1, 495_500, m(90))),
        lambda: [filed(piece("DV5-1", 18, 0, 493_000, m(125))),
                 filed(piece("DV5-3", 18, 2, 498_000, m(55)))]))
    out.append(case(
        "D-V6-road-longer", "evasion", "ask", "ask", "same site",
        "The old 300 m road filed again as 330 m from the same start.",
        "Mostly on the old road's line: the same ground.",
        lambda: filed(road("DV6", 19, length=330)),
        lambda: [done(road("DV6-OLD", 19, agency=OTHER[3]), 330)]))
    out.append(case(
        "D-V7-names-fake-work", "evasion", "ask", "ask", "same site",
        "Pinned on an old road, the form names another work ID that is not on record.",
        "Naming a work that does not exist must not excuse the one at the pin.",
        lambda: filed(road("DV7", 20, north=10, work_nature="Extension / additional component",
                           prior_work_id="WS/FAKE/0001", known_nearby_work_ids="WS/FAKE/0001",
                           nearby_work_relationship="Same asset, separate phase")),
        lambda: [done(road("DV7-OLD", 20, agency=OTHER[4]), 330)]))
    out.append(case(
        "D-V8-continues-unfinished", "evasion", "ask", "ask", "declared",
        "Declared an extension of a road still being built, but lying on its ground.",
        "T135: named, on the earlier work's own ground, not finished: still asked.",
        lambda: filed(road("DV8", 21, north=5, work_nature="Extension / additional component", prior_work_id="DV8-OLD",
                           known_nearby_work_ids="DV8-OLD",
                           nearby_work_relationship="Same asset, separate phase")),
        lambda: [filed(road("DV8-OLD", 21, agency=OTHER[0], rec=m(200), sanction=m(160)),
                       status="SANCTIONED")]))
    out.append(case(
        "D-V9-pin-swapped", "evasion", "na", "na/check/ask", "pin typed off",
        "On an old road, the form's latitude and longitude swapped (a pin outside India).",
        "A pin that cannot be compared must not read as 'nothing sanctioned here'.",
        lambda: filed(road("DV9", 22, north=10, latitude=f"{wf.pin(22)[1]:.6f}",
                           longitude=f"{wf.pin(22)[0]:.6f}", start_lat=f"{wf.pin(22)[1]:.6f}",
                           start_lon=f"{wf.pin(22)[0]:.6f}", end_lat=f"{wf.pin(22)[1]:.6f}",
                           end_lon=f"{wf.pin(22)[0] + 0.003:.6f}")),
        lambda: [done(road("DV9-OLD", 22, agency=OTHER[1]), 330)]))

    # ---- broken data ------------------------------------------------------------------------
    out.append(case(
        "D-B1-no-district", "broken", "na", "na", "broken",
        "A record with no district.",
        "No district, nothing to compare with.",
        lambda: {**filed(road("DB1", 23)), "district_lgd": None}))
    out.append(case(
        "D-B2-no-date-no-words", "broken", "na", "na", "broken",
        "A record with no dates and no description, no form.",
        "Nothing to compare.",
        lambda: {"work_id": "DB2", "source": "SCENARIO", "district_lgd": "194",
                 "state_lgd": "09", "district_name": "Jaunpur", "state_name": "Uttar Pradesh",
                 "description": "", "amount": 300000, "status": "SANCTIONED",
                 "work_type_code": "ROAD_CC"}))
    out.append(case(
        "D-B3-form-no-pin", "broken", "na", "na/edge/check", "broken",
        "A form with its map pin left blank, at the site of an old road.",
        "Without the pin, words alone are right 2 in 3: a note at most, never 'nothing here'.",
        lambda: filed(road("DB3", 24, latitude="", longitude="", start_lat="", start_lon="",
                           end_lat="", end_lon="")),
        lambda: [done(road("DB3-OLD", 24, agency=OTHER[2]), 330)]))
    return out

