"""Duplicate Work (T135, the robustness loop: data/trial/agent_robustness_loop.py): an old road
filed again a little longer, a re-filed work declared a "continuation" or "upgrade", a finished
work named only among the nearby works, and map pins that cannot be right."""

from __future__ import annotations

from datetime import date

from drishti.agents.dup_split.agent import assess
from drishti.agents.dup_split.repeat import RepeatIndex, on_line, pin_problems
from tests.agents.dup_split.test_dup_split import DEG, LAT, LON, _filler, _form, _w, asked, notes

ROAD = "CC road from the school to the panchayat bhawan, Sirpur"


def _road(work_id, start, length, rec, done=None, status="SANCTIONED", nature="new",
          earlier=None, answers=None):
    form = _form(lat=LAT + start * DEG, lon=LON, wtype="ROAD_CC", nature=nature,
                 earlier=earlier, end=(LAT + (start + length) * DEG, LON), answers=answers)
    return _w(work_id, ROAD, rec=rec, done=done, status=status, wtype="ROAD_CC", form=form)


OLD = dict(rec=date(2024, 3, 1), done=date(2025, 6, 1), status="COMPLETED")


def _run(new, *old):
    return assess(new, RepeatIndex.build(_filler() + list(old) + [new]))


def test_the_old_road_filed_again_a_little_longer_is_asked():
    old = _road("OLD", 0, 300, **OLD)
    r = _run(_road("NEW", 0, 400, date(2026, 5, 1), status="RECOMMENDED"), old)
    assert asked(r) == ["SANCTIONED_WORK_AT_THIS_SITE"] and "runs over" in r.headline


def test_the_next_stretch_from_the_old_roads_end_is_not_asked():
    old = _road("OLD", 0, 300, **OLD)
    r = _run(_road("NEW", 300, 300, date(2026, 5, 1), status="RECOMMENDED"), old)
    assert not asked(r)
    assert on_line(((LAT + 300 * DEG, LON), (LAT + 600 * DEG, LON)),
                   ((LAT, LON), (LAT + 300 * DEG, LON))) <= 0.15


def test_a_continuation_declared_on_a_finished_roads_own_ground_is_a_rebuild():
    old = _road("OLD", 0, 300, **OLD)
    new = _road("NEW", 20, 300, date(2026, 5, 1), status="RECOMMENDED",
                nature="continuation", earlier="OLD")
    r = _run(new, old)
    assert asked(r) == ["REBUILT_SOON_AFTER_COMPLETION"] and "own ground" in r.headline


def test_a_continuation_declared_on_an_unfinished_roads_ground_is_asked():
    old = _road("OLD", 0, 300, rec=date(2025, 3, 1), status="SANCTIONED")
    new = _road("NEW", 20, 300, date(2026, 5, 1), status="RECOMMENDED",
                nature="continuation", earlier="OLD")
    r = _run(new, old)
    assert asked(r) == ["SANCTIONED_WORK_AT_THIS_SITE"] and "not finished yet" in r.headline


def test_a_real_continuation_from_the_end_is_a_note():
    old = _road("OLD", 0, 300, **OLD)
    new = _road("NEW", 300, 300, date(2026, 5, 1), status="RECOMMENDED",
                nature="continuation", earlier="OLD")
    r = _run(new, old)
    assert not asked(r) and notes(r) == ["CONTINUES_SANCTIONED_WORK"]


def test_a_finished_work_named_only_among_the_nearby_works_is_still_judged():
    old = _road("OLD", 0, 300, **OLD)
    new = _road("NEW", 10, 300, date(2026, 5, 1), status="RECOMMENDED",
                answers=[{"earlier_work": "OLD", "answer": "continues"}])
    assert asked(_run(new, old)) == ["REBUILT_SOON_AFTER_COMPLETION"]


def test_a_map_pin_outside_india_is_set_aside_and_said():
    for lat, lon in ((0.0, 0.0), (LON, LAT)):            # (0, 0), and the two swapped
        form = _form(lat=lat, lon=lon)
        new = _w("NEW", "Hall for the community, new building", rec=date(2025, 1, 5),
                 status="RECOMMENDED", form=form)
        r = assess(new, RepeatIndex.build(_filler() + [new]))
        assert any("not in India" in s for s in r.limitations), (lat, lon)
        assert pin_problems(form, False)


def test_a_road_with_one_end_only_says_so():
    form = _form(lat=LAT, lon=LON, wtype="ROAD_CC")
    new = _w("NEW", ROAD, rec=date(2026, 5, 1), status="RECOMMENDED", wtype="ROAD_CC", form=form)
    r = assess(new, RepeatIndex.build(_filler() + [new]))
    assert any("one end" in s for s in r.limitations)
