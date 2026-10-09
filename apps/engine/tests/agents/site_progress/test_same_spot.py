"""T158: film from the same spot every month, and more spots for big works
(docs/plans/T158-same-spot-filming.md)."""

from __future__ import annotations

import pytest

from drishti.agents.site_progress import sitemap

PIN = {"lat": 25.75, "lon": 82.69}


def _form(work_type: str, size: dict, **loc) -> dict:
    return {"work": {"work_type": work_type},
            "sites": [{"location": {**PIN, **loc}, "size": size}]}


def _spots(work_type: str, size: dict, **loc) -> int:
    form = _form(work_type, size, **loc)
    return sitemap.spots_needed(sitemap.site_of(form), form)


# ---- how many spots a work needs (plan §C) ----

@pytest.mark.parametrize("size,spots", [
    ({"built_up_area_m2": 100, "floors_nos": 1}, 2),       # 10×10 m room
    ({"built_up_area_m2": 450, "floors_nos": 1}, 2),       # 30×15 m school block
    ({"built_up_area_m2": 2400, "floors_nos": 1}, 4),      # 60×40 m hall
])
def test_buildings_need_a_pair_of_spots_for_every_40_m_of_side(size, spots):
    assert _spots("COMMUNITY_HALL", size) == spots


def test_a_ground_of_100_by_60_m_needs_six_spots():
    assert _spots("PLAYGROUND", {"area_m2": 6000}) == 6


def test_floors_do_not_make_a_building_wider():
    # 2,400 m² over 3 floors is an 800 m² footprint: about 40 m long, one pair of spots
    assert _spots("COMMUNITY_HALL", {"built_up_area_m2": 2400, "floors_nos": 3}) == 2


def test_a_form_length_is_used_when_given():
    assert _spots("BUS_SHELTER", {"length_m": 50, "depth_m": 3}) == 4


def test_no_size_on_the_form_asks_for_the_minimum_two():
    assert _spots("COMMUNITY_HALL", {}) == 2
    assert sitemap.spots_needed(None, None) == 2


def test_a_huge_pond_is_capped():
    assert _spots("POND", {"water_area_m2": 1_000_000, "avg_depth_m": 2}) == sitemap.MAX_SPOTS


def test_a_short_road_needs_every_stretch():
    # about 590 m between the two pins: 12 stretches of 50 m, all asked
    assert _spots("ROAD_CC", {"length_m": 600}, end_lat=25.7553, end_lon=82.69) == 12


def test_a_long_road_needs_a_sample_and_both_ends():
    # about 3.3 km: 6 stretches at random plus the first and the last
    assert _spots("ROAD_CC", {"length_m": 3300}, end_lat=25.78, end_lon=82.69) == \
        sitemap.SAMPLE_STRETCHES + 2


# ---- the site circle uses the footprint (fix found while planning T158) ----

def test_a_pond_circle_uses_its_water_area():
    site = sitemap.site_of(_form("POND", {"water_area_m2": 10_000}))
    assert site.radius_m == pytest.approx(100.0)


def test_a_building_circle_uses_its_footprint_not_all_floors():
    site = sitemap.site_of(_form("COMMUNITY_HALL", {"built_up_area_m2": 2700, "floors_nos": 3}))
    assert site.radius_m == pytest.approx(30.0)


# ---- which stretches of a long road are asked (drawn when filming starts) ----

def _road(end_lat: float) -> sitemap.Site:
    return sitemap.site_of(_form("ROAD_CC", {}, end_lat=end_lat, end_lon=82.69))


def test_a_short_road_asks_every_stretch():
    site = _road(25.7553)
    assert sitemap.stretches_asked(site, b"seed-1") == site.stretches()


def test_a_long_road_asks_both_ends_and_a_fixed_draw_for_one_visit():
    site = _road(25.78)
    asked = sitemap.stretches_asked(site, b"seed-1")
    all_ = site.stretches()
    assert len(asked) == sitemap.SAMPLE_STRETCHES + 2 == len(set(asked))
    assert asked[0] == all_[0] and asked[-1] == all_[-1]
    assert set(asked) <= set(all_)
    assert asked == sorted(asked, key=all_.index)
    assert sitemap.stretches_asked(site, b"seed-1") == asked          # the same visit
    draws = {tuple(sitemap.stretches_asked(site, f"seed-{i}".encode())) for i in range(2, 8)}
    assert len(draws) > 1                                              # other visits differ


def test_a_compact_site_asks_no_stretches():
    site = sitemap.site_of(_form("COMMUNITY_HALL", {"built_up_area_m2": 400}))
    assert sitemap.stretches_asked(site, b"seed-1") == []
    assert sitemap.stretches_asked(None, b"seed-1") == []


# ---- where a viewpoint was filmed from, and which way (plan §A) ----

from drishti.agents.site_progress import spots  # noqa: E402


def _fix(t, lat, acc=5.0):
    return {"t": t, "lat": lat, "lon": 82.69, "accuracy": acc}


def test_the_spot_is_the_median_of_the_good_fixes_around_the_viewpoint():
    gps = [_fix(0, 25.7500), _fix(5, 25.7501), _fix(6, 25.7501), _fix(7, 25.7502),
           _fix(8, 25.7503, acc=80), _fix(30, 25.80)]   # too early, poor, long after: left out
    s = spots.spot(gps, 5.0, 8.0)
    assert s["lat"] == pytest.approx(25.7501, abs=1e-7) and s["acc"] == 5.0
    assert spots.spot(gps, 100.0, 105.0) is None             # the last fix (30 s) too old to stand


def test_a_phone_standing_still_keeps_its_last_fix():
    # found by the browser run (capture_e2e): standing still, a phone may send no new fix
    gps = [_fix(1, 25.7500), _fix(3, 25.7504), _fix(4, 25.7509, acc=90)]
    s = spots.spot(gps, 20.0, 25.0)
    assert s["lat"] == 25.7504 and s["acc"] == 5.0          # the last GOOD fix before it


def test_the_facing_is_the_smallest_arc_holding_the_headings():
    a = spots.arc([80, 120, 100, 95])
    assert (a["from"], a["to"], a["mid"], a["width"]) == (80, 120, 100, 40)


def test_an_arc_across_north_wraps():
    a = spots.arc([350, 10, 20, 355])
    assert (a["from"], a["to"], a["mid"], a["width"]) == (350, 20, 5, 30)


def test_no_compass_no_facing():
    assert spots.arc([]) is None


def test_headings_are_read_from_the_log_inside_the_viewpoint():
    log = {"heading": [{"t": 1, "h": 10}, {"t": 4, "h": 90}, {"t": 6, "h": 100},
                       {"t": 9, "h": 200}, {"t": 5, "h": "x"}, "junk"]}
    assert spots.headings(log, 3.0, 7.0) == [90.0, 100.0]


def test_coverage_of_last_times_arc():
    first = spots.arc([60, 150])                           # 90° panned the first time
    assert spots.covered(first, list(range(60, 151, 5))) == pytest.approx(1.0)
    assert spots.covered(first, list(range(60, 106, 5))) == pytest.approx(0.5, abs=0.07)
    assert spots.covered(first, []) is None          # no compass: can't tell, not 0%
    assert spots.covered(None, [100]) is None


def test_a_narrow_arc_is_covered_by_facing_it():
    narrow = spots.arc([100, 102])
    assert spots.covered(narrow, [110]) == 1.0 and spots.covered(narrow, [150]) == 0.0


# ---- the anchor the next visit is guided back to (plan §B) ----

def _visit(spot_lat, acc, trusted=True, facing=None, vid="v1"):
    readings = {"views_match_site": True if trusted else False}
    return {"readings": readings,
            "spots": {vid: {"spot": {"lat": spot_lat, "lon": 82.69, "acc": acc},
                            "facing": facing}}}


def test_the_first_good_fix_is_the_anchor_and_never_moves():
    first = _visit(25.75000, 6, facing={"from": 80, "to": 120, "mid": 100, "width": 40})
    later = _visit(25.75020, 4, facing={"from": 0, "to": 10, "mid": 5, "width": 10})
    a = spots.anchors([first, later])["v1"]
    assert a["box"]["lat"] == 25.75 and a["box"]["box_m"] == spots.BOX_M
    assert a["facing"]["mid"] == 100


def test_a_poor_first_fix_gives_way_once_to_a_good_one():
    poor = _visit(25.75000, 40)
    good = _visit(25.75020, 8)
    best_later = _visit(25.75040, 3)
    a = spots.anchors([poor, good, best_later])["v1"]["box"]
    assert a["lat"] == 25.7502 and a["box_m"] == 8


def test_with_only_poor_fixes_the_best_one_anchors_with_a_bigger_box():
    a = spots.anchors([_visit(25.75, 40), _visit(25.7501, 30)])["v1"]["box"]
    assert a["lat"] == 25.7501 and a["box_m"] == 30


def test_a_visit_that_did_not_match_the_site_never_anchors():
    away = _visit(25.80, 3, trusted=False)
    here = _visit(25.75, 6)
    assert spots.anchors([away, here])["v1"]["box"]["lat"] == 25.75
    assert spots.anchors([away]) == {}


def test_a_viewpoint_with_no_usable_gps_still_has_its_facing():
    # found by the browser run (capture_e2e): the facing must not hang on the GPS
    arc_ = {"from": 80, "to": 120, "mid": 100, "width": 40}
    v = {"readings": {}, "spots": {"v2": {"spot": None, "facing": arc_}}}
    assert spots.anchors([v]) == {"v2": {"box": None, "facing": arc_}}


def test_metres_from_the_anchor():
    a = spots.anchors([_visit(25.75, 5)])["v1"]["box"]
    assert spots.offset_m(a, {"lat": 25.7501, "lon": 82.69}) == pytest.approx(11.1, abs=0.2)
    assert spots.offset_m(a, None) is None


# ---- the claim judged spot by spot, then combined (plan §D, revised) ----

@pytest.mark.parametrize("claim,whole", [
    ("walls up to lintel level in all rooms", True),
    ("the entire road surfaced", True),
    ("plaster complete", True),
    ("सभी कमरों में प्लास्टर", True),
    ("पूरी सड़क बन गई", True),
    ("toilet block roof cast", False),
    ("foundation completed", False),
])
def test_whole_work_claims_are_told_apart(claim, whole):
    assert spots.whole_claim(claim) is whole


def test_a_part_claim_shown_at_one_spot_is_shown():
    v = {"v1": "shown", "v2": "not_shown", "v3": "cant_tell"}
    assert spots.combine(v, needed=4, filmed=3, whole=False) == "shown"


def test_a_part_claim_is_not_shown_only_when_every_spot_and_enough_spots_say_so():
    assert spots.combine({"v1": "not_shown", "v2": "not_shown"}, 4, 2, False) == "not_shown"
    assert spots.combine({"v1": "not_shown", "v2": "cant_tell"}, 4, 2, False) == "cant_tell"
    # one spot of four filmed: the part may be where nobody filmed
    assert spots.combine({"v1": "not_shown"}, 4, 1, False) == "cant_tell"


def test_a_whole_work_claim_contradicted_at_one_spot_is_not_shown():
    v = {"v1": "shown", "v2": "not_shown", "v3": "shown"}
    assert spots.combine(v, needed=4, filmed=3, whole=True) == "not_shown"


def test_a_whole_work_claim_needs_half_the_spots_to_be_shown():
    assert spots.combine({"v1": "shown", "v2": "shown"}, 4, 2, True) == "shown"
    assert spots.combine({"v1": "shown"}, 4, 1, True) == "cant_tell"


def test_no_answer_from_any_spot_is_no_verdict():
    assert spots.combine({"v1": None, "v2": "maybe"}, 2, 2, False) is None
    assert spots.combine({}, 2, 0, True) is None


def test_the_three_pictures_are_taken_facing_the_start_middle_and_end_of_the_arc():
    log = {"heading": [{"t": 2.0, "h": 60}, {"t": 3.0, "h": 100}, {"t": 4.0, "h": 150},
                       {"t": 5.0, "h": 105}]}
    facing = spots.arc([60, 150])
    assert spots.pan_times(log, 2.0, 5.0, facing) == [2.0, 5.0, 4.0]      # the middle is 105°
    assert spots.pan_times({}, 0.0, 6.0, None) == pytest.approx([1.0, 3.0, 5.0])


# ---- what Site Progress says about the spots (plan §D) ----

from datetime import date  # noqa: E402

from drishti.agents.contract import Status  # noqa: E402
from drishti.agents.site_progress.agent import assess  # noqa: E402
from tests.agents.site_progress.test_site_progress_v3 import (  # noqa: E402
    AS_OF,
    base,
    codes,
    months,
    work,
)


def test_claim_not_shown_names_the_spots():
    vs = months(3)
    for v in vs[1:]:
        v["readings"].update(claim_verdict="not_shown", claim_spots_not_shown=["v2"],
                             spot_verdicts={"v1": "cant_tell", "v2": "not_shown"})
    f = next(f for f in assess(work(base(), *vs), AS_OF).findings if f.code == "CLAIM_NOT_SHOWN")
    assert "at spot v2" in f.text


def test_too_few_spots_filmed_is_a_note_never_a_finding():
    vs = months(2, spots_needed=4, spots_filmed=2)
    r = assess(work(base(), *vs), AS_OF)
    assert not r.findings
    assert any("2 of the 4 spots" in n for n in r.evidence["notes"])


def test_far_from_the_spot_or_a_short_pan_is_a_note_never_a_finding():
    vs = months(2, spot_offsets_m={"v1": 3.0, "v2": 24.6}, spot_coverage={"v1": 1.0, "v3": 0.45})
    r = assess(work(base(), *vs), AS_OF)
    assert not r.findings
    notes = " ".join(r.evidence["notes"])
    assert "viewpoint v2 was filmed about 25 m" in notes and "viewpoint v1 was" not in notes
    assert "at viewpoint v3" in notes and "45%" in notes


def test_stretches_asked_but_not_filmed_are_a_note():
    vs = months(2, stretches_missed=["s4", "s9"])
    r = assess(work(base(), *vs), AS_OF)
    assert not r.findings and any("s4, s9" in n for n in r.evidence["notes"])


def test_the_work_page_gets_each_visits_spots():
    vs = months(1, spots_needed=4, spots_filmed=3,
                spot_verdicts={"v1": "shown", "v2": "not_shown", "v3": "cant_tell"})
    r = assess(work(base(), *vs), AS_OF)
    s = r.evidence["visits"][-1]["spots"]
    assert s == {"needed": 4, "filmed": 3,
                 "verdicts": {"v1": "shown", "v2": "not_shown", "v3": "cant_tell"}}


def test_spot_readings_in_a_wrong_shape_never_break_it():
    vs = months(2, spots_needed="four", spot_offsets_m=["x"], spot_coverage={"v1": "all"},
                spot_verdicts={"v1": "maybe", "v2": 3}, claim_spots_not_shown="v2",
                stretches_missed=7)
    r = assess(work(base(), *vs), AS_OF)
    assert r.status == Status.ASSESSED and not r.findings


def test_visits_with_spots_but_not_read_yet_are_not_assessable():
    w = work({"visit_id": "x", "kind": "monthly", "captured_at": date(2026, 9, 1).isoformat(),
              "claim": "roof cast", "readings": {}})
    assert assess(w, AS_OF).status == Status.NOT_ASSESSABLE
    assert codes(assess(w, AS_OF)) == []
