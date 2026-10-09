"""Duplicate Work by where the site videos were filmed (T160, the agents audit of 9 Oct 2026).

The loophole: a map pin typed 60-90 m from an earlier same-kind building passed both the 50 m
one-site line here and Site Progress's 100 m "not at the form's pin" (SITE_NOT_AT_FORM_PIN). Two
or more site videos filmed within 50 m of that building, nearer to it than to the form's pin, put
the work there: asked about as if the pin had been typed honestly."""

from __future__ import annotations

from datetime import date

from drishti.agents.dup_split.agent import assess
from drishti.agents.dup_split.repeat import RepeatIndex
from tests.agents.dup_split.test_dup_split import DEG, HALL, LAT, LON, _filler, _form, _w, asked

CODE = "SANCTIONED_WORK_WHERE_FILMED"


def _visit(i, north, kind="monthly", **readings):
    r = {"sealed": True, "in_app": True, "motion_consistent": True, "views_match_site": True,
         "gps_weak": False, "mock_location": False,
         "gps_point": {"lat": LAT + north * DEG, "lon": LON}}
    r.update(readings)
    return {"visit_id": f"v{i}", "kind": kind, "captured_at": date(2025, 3 + i, 1),
            "claim": "walls up to lintel", "readings": r}


def _old():
    return _w("OLD", HALL, status="COMPLETED", rec=date(2023, 3, 1), done=date(2024, 2, 1),
              form=_form())


def _new(pin_north=75, visits=(), wtype="COMMUNITY_HALL", form=None):
    w = _w("NEW", HALL, rec=date(2025, 1, 5), wtype=wtype,
           form=form or _form(lat=LAT + pin_north * DEG, wtype=wtype))
    w["site_visits"] = list(visits)
    return w


def _run(new, old=None):
    old = old or _old()
    return assess(new, RepeatIndex.build(_filler() + [old, new]))


def test_a_pin_typed_75_m_off_and_filmed_at_the_old_hall_is_asked():
    r = _run(_new(75, [_visit(0, 5, kind="baseline"), _visit(1, 8), _visit(2, 3)]))
    assert asked(r) == [CODE], r.headline
    f = next(f for f in r.findings if f.code == CODE)
    assert f.evidence["other"] == "OLD" and f.evidence["pin_to_other_m"] == 75.0
    assert set(f.evidence["visits"]) == {"v0", "v1", "v2"}
    assert "filmed" in f.text and "75 m" in f.text
    # the note about a same-kind building just past 50 m gives way to the question
    assert not any(x.code == "NEAR_SANCTIONED_WORK" for x in r.findings)


def test_without_videos_it_stays_a_note_as_before():
    r = _run(_new(75))
    assert not asked(r)
    assert any(f.code == "NEAR_SANCTIONED_WORK" for f in r.findings)


def test_one_video_is_not_enough():
    assert not asked(_run(_new(75, [_visit(0, 5, kind="baseline")])))


def test_filmed_at_its_own_pin_is_left_alone():
    # an honest new hall 75 m from the old one, filmed around its own pin (and once from the
    # side nearer the old hall, still nearer its own pin)
    assert not asked(_run(_new(75, [_visit(0, 75, kind="baseline"), _visit(1, 70),
                                    _visit(2, 40)])))


def test_videos_that_cannot_be_trusted_on_place_do_not_count():
    for bad in ({"mock_location": True}, {"gps_weak": True}, {"views_match_site": False},
                {"sealed": False}, {"gps_point": None}):
        visits = [_visit(0, 5, kind="baseline", **bad), _visit(1, 8, **bad), _visit(2, 3)]
        assert not asked(_run(_new(75, visits))), bad


def test_most_videos_must_agree():
    # two at the old hall, three at the form's pin: where it stands is not settled
    visits = [_visit(0, 5, kind="baseline"), _visit(1, 8), _visit(2, 75), _visit(3, 76),
              _visit(4, 74)]
    assert not asked(_run(_new(75, visits)))


def test_a_declared_continuation_of_that_hall_is_not_asked_here():
    form = _form(lat=LAT + 75 * DEG, nature="extension", earlier="OLD")
    r = _run(_new(visits=[_visit(0, 5, kind="baseline"), _visit(1, 8)], form=form))
    assert CODE not in asked(r)


def test_a_road_or_a_street_light_is_not_judged_by_where_it_was_filmed():
    road_old = _w("OLD", "CC road from temple to school", wtype="ROAD_CC", status="COMPLETED",
                  rec=date(2023, 3, 1), done=date(2024, 2, 1),
                  form=_form(wtype="ROAD_CC", end=(LAT + 200 * DEG, LON)))
    road = _new(visits=[_visit(0, 5, kind="baseline"), _visit(1, 8)], wtype="ROAD_CC",
                form=_form(lat=LAT + 75 * DEG, wtype="ROAD_CC",
                           end=(LAT + 275 * DEG, LON)))
    assert CODE not in asked(_run(road, road_old))
    light_old = _w("OLD", "Solar street light near Ram's house", wtype="STREET_LIGHT",
                   status="COMPLETED", rec=date(2023, 3, 1), done=date(2024, 2, 1),
                   form=_form(wtype="STREET_LIGHT"))
    light = _new(75, [_visit(0, 2, kind="baseline"), _visit(1, 1)], wtype="STREET_LIGHT")
    assert CODE not in asked(_run(light, light_old))


def test_already_asked_by_its_pin_is_not_asked_twice():
    r = _run(_new(30, [_visit(0, 5, kind="baseline"), _visit(1, 8)]))
    assert asked(r) == ["SANCTIONED_WORK_AT_THIS_SITE"]


def test_a_pin_far_off_names_the_hall_it_was_filmed_at():
    # 400 m off: Site Progress says the pin is elsewhere; Duplicate Work now names the hall
    r = _run(_new(400, [_visit(0, 5, kind="baseline"), _visit(1, 8)]))
    assert asked(r) == [CODE]
