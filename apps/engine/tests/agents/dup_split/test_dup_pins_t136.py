"""Duplicate Work by the forms' map pins (T136, the robustness loop's round 6).

The strictest split, found by pins as well as by words: one lane filed as pieces laid end to end,
each 96-100% of a limit, escaped when one piece was called another kind of road. And a same-kind
building just past the 50 m one-site line is named in a note, never counted."""

from __future__ import annotations

from datetime import date

from drishti.agents.dup_split.agent import assess
from drishti.agents.dup_split.repeat import NEAR_METRES, PIN_METRES, RepeatIndex
from tests.agents.dup_split.test_dup_split import DEG, HALL, LAT, LON, _filler, _form, _w, asked


def _piece(i, wtype="ROAD_CC", amount=490_000.0, desc=None, rec=None, mp="MP A"):
    start, end = LAT + 100 * i * DEG, LAT + (100 * i + 95) * DEG
    return _w(f"P{i}", desc or f"Road part {i}", wtype=wtype, amount=amount,
              rec=rec or date(2025, 1, 5 + i), mp=mp,
              form=_form(lat=start, wtype=wtype, end=(end, LON)))


def test_pieces_laid_end_to_end_just_under_the_limit_are_a_split():
    pieces = [_piece(0, desc="CC road in the lane"), _piece(1, wtype="FOOTPATH",
                                                            desc="Paver block path"),
              _piece(2, desc="Concrete road, another reach")]
    idx = RepeatIndex.build(_filler() + pieces)
    r = assess(pieces[1], idx)
    assert asked(r) == ["SPLIT_JUST_UNDER_LIMIT"]
    assert "map pins" in r.findings[0].text


def test_pieces_not_all_just_under_the_limit_are_not_a_split():
    pieces = [_piece(0), _piece(1, amount=420_000.0), _piece(2)]
    idx = RepeatIndex.build(_filler() + pieces)
    assert not asked(assess(pieces[1], idx))


def test_pieces_far_apart_in_time_or_by_another_mp_are_not_a_split():
    late = [_piece(0), _piece(1, rec=date(2025, 3, 1))]
    # T168: 55 days apart is past the strictest split, but "check this" (risk 0.3), never asked
    assert asked(assess(late[1], RepeatIndex.build(_filler() + late))) == ["SPLIT_NEAR_LIMIT"]
    far = [_piece(0), _piece(1, rec=date(2025, 6, 1))]
    assert not asked(assess(far[1], RepeatIndex.build(_filler() + far)))
    other_mp = [_piece(0), _piece(1, mp="MP B")]
    assert not asked(assess(other_mp[1], RepeatIndex.build(_filler() + other_mp)))


def test_pieces_with_a_gap_between_them_are_not_a_split():
    a = _piece(0)
    b = _w("P1", "Road part 1", wtype="ROAD_CC", amount=490_000.0, rec=date(2025, 1, 6),
           form=_form(lat=LAT + 400 * DEG, wtype="ROAD_CC", end=(LAT + 495 * DEG, LON)))
    assert not asked(assess(b, RepeatIndex.build(_filler() + [a, b])))


def test_a_same_kind_building_just_past_the_one_site_line_is_a_note():
    old = _w("OLD", HALL, status="COMPLETED", rec=date(2023, 3, 1), done=date(2024, 2, 1),
             form=_form())
    new = _w("NEW", HALL, rec=date(2025, 1, 5), form=_form(lat=LAT + 60 * DEG))
    r = assess(new, RepeatIndex.build(_filler() + [old, new]))
    assert not asked(r)
    notes = [f for f in r.findings if f.code == "NEAR_SANCTIONED_WORK"]
    assert notes and notes[0].risk == 0 and notes[0].evidence["other"] == "OLD"
    far = _w("FAR", HALL, rec=date(2025, 1, 5), form=_form(lat=LAT + (NEAR_METRES + 20) * DEG))
    r = assess(far, RepeatIndex.build(_filler() + [old, far]))
    assert not any(f.code == "NEAR_SANCTIONED_WORK" for f in r.findings)
    assert PIN_METRES < 60 < NEAR_METRES
