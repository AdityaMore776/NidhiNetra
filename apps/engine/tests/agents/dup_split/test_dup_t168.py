"""Duplicate Work's eval fixes (T168, data/eval/dup_split/, FINDINGS "T168").

A fraud is never an edge case (the owner, 19 Oct 2026): the ways past the strictest split, and a
re-filed building pinned just past the one-site line, reach at least "check this" (risk 0.3,
SPLIT_NEAR_LIMIT and SAME_BUILDING_NEAR); a form whose map pin cannot be compared says so
instead of "nothing sanctioned here"."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from drishti.agents.contract import Status
from drishti.agents.dup_split.agent import CHECK_RISK, assess
from drishti.agents.dup_split.repeat import RepeatIndex
from tests.agents.dup_split.test_dup_split import DEG, HALL, LAT, LON, ROAD, _filler, _form, _w


def counted(r):
    return {f.code: f.risk for f in r.findings if f.risk > 0}


def _pieces(amounts, days, numbered=True, wtype="ROAD_CC"):
    first = date(2024, 12, 1)
    return [_w(f"P{i}", f"{ROAD} reach-{i + 1}" if numbered else ROAD, a,
               rec=first + timedelta(days=days * i), wtype=wtype)
            for i, a in enumerate(amounts)]


@pytest.mark.parametrize("amounts,days,numbered,want", [
    ((499_000, 499_500), 0, True, "SPLIT_JUST_UNDER_LIMIT"),     # the strictest: unchanged
    ((499_000, 499_500), 40, True, "SPLIT_NEAR_LIMIT"),          # 31-90 days: check this
    ((499_000, 499_500), 40, False, "SPLIT_NEAR_LIMIT"),         # the same work filed twice
    ((499_000, 499_500), 120, True, None),                       # months apart: two jobs
    ((473_000, 476_000, 477_000), 4, True, "SPLIT_NEAR_LIMIT"),  # numbered parts at 95%
    ((473_000, 476_000), 0, False, None),                        # 95%, unnumbered: different spots
    ((470_000, 476_000), 40, True, None),                        # 94% AND weeks apart: not
    ((499_000,) * 6, 0, True, None),                             # a series, not one job
])
def test_ways_past_the_strictest_split_reach_check_this(amounts, days, numbered, want):
    pieces = _pieces(amounts, days, numbered)
    idx = RepeatIndex.build(_filler() + pieces)
    r = assess(pieces[0], idx)
    got = counted(r)
    if want is None:
        assert not got, r.headline
    else:
        assert list(got) == [want], (got, r.headline)
        if want == "SPLIT_NEAR_LIMIT":
            assert got[want] == CHECK_RISK and "check" in r.headline.lower()


def test_a_new_work_checked_on_the_spot_finds_the_looser_split_too():
    pieces = _pieces((499_000, 499_500), 40)
    idx = RepeatIndex.build(_filler() + pieces[:1])         # the second piece is not indexed
    assert list(counted(assess(pieces[1], idx))) == ["SPLIT_NEAR_LIMIT"]


def _hall(work_id, north_m, rec, area=180, desc=HALL, done=None):
    form = _form(lat=LAT + north_m * DEG)
    form["sites"][0]["size"] = {"builtup_area": area}
    return _w(work_id, desc, rec=rec, done=done, status="COMPLETED" if done else "SANCTIONED",
              sanction=rec + timedelta(days=40), form=form)


def test_a_building_refiled_just_past_the_line_is_check_this():
    old = _hall("OLD", 0, date(2023, 1, 10), done=date(2024, 1, 10))
    new = _hall("NEW", 70, date(2025, 3, 1))
    r = assess(new, RepeatIndex.build(_filler() + [old, new]))
    assert counted(r) == {"SAME_BUILDING_NEAR": CHECK_RISK}, r.headline


@pytest.mark.parametrize("change", ["other words", "other size", "named"])
def test_a_different_building_nearby_stays_a_note(change):
    old = _hall("OLD", 0, date(2023, 1, 10), done=date(2024, 1, 10))
    new = _hall("NEW", 70, date(2025, 3, 1),
                desc="Construction of anganwadi centre building in Sirpur primary school campus"
                if change == "other words" else HALL,
                area=60 if change == "other size" else 180)
    if change == "named":
        new["cost_form"]["earlier_works"] = [{"earlier_work": "OLD", "answer": "different",
                                              "difference": "the old hall is the panchayat's, "
                                                            "this is the school's"}]
    r = assess(new, RepeatIndex.build(_filler() + [old, new]))
    assert not counted(r), r.headline
    assert "NEAR_SANCTIONED_WORK" in [f.code for f in r.findings]


@pytest.mark.parametrize("loc", [{"lat": LON, "lon": LAT}, {"lat": 0.0, "lon": 0.0}, {}])
def test_a_form_pin_that_cannot_be_compared_is_not_a_clean_chit(loc):
    old = _w("OLD", HALL, rec=date(2023, 1, 10), done=date(2024, 1, 10), status="COMPLETED",
             form=_form())
    form = _form()
    form["sites"] = [{"location": loc}]
    new = _w("NEW", HALL, rec=date(2025, 3, 1), form=form)
    r = assess(new, RepeatIndex.build(_filler() + [old, new]))
    assert r.status == Status.NOT_ASSESSABLE, r.headline
    assert "map pin" in r.headline and "not a clean chit" in r.headline
    assert "LOOKS_LIKE_SANCTIONED_WORK" in [f.code for f in r.findings]   # the notes stay


def test_a_record_without_a_form_is_still_compared_by_words():
    old = _w("OLD", HALL, rec=date(2023, 1, 10), done=date(2024, 1, 10), status="COMPLETED")
    new = _w("NEW", HALL, rec=date(2025, 3, 1))
    r = assess(new, RepeatIndex.build(_filler() + [old, new]))
    assert r.status == Status.ASSESSED
