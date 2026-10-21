"""Site Progress: every site video records where it was filmed, near where the form says the work is
(T168, the owner, 20 Oct 2026).

"Make sure each site check every time period also captures the location it was taken at, and if
the locations where the implementing agency's form says the project would take place differ by a
lot (a little here and there is fine, markers aren't fully accurate, it can be a small rough area)
then flag it."

  LOCATION_NOT_RECORDED       2 of the last 3 accepted videos carry no usable location (no fix,
                              only an "approximate" one past 500 m, or a faked "mock" location;
                              weak GPS under trees is honest noise, T136): check this; all of the
                              last 3: a question. One alone is a note (a retake is asked for)
  FILMED_AWAY_FROM_FORM_SITE  a video filmed more than AWAY_M beyond the edge of every place the
                              form gives (the site's own size, a road's line), after the phone's
                              own reported accuracy: one video check this, two or more a question
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from drishti.agents.site_progress import sitemap
from drishti.agents.site_progress.agent import AWAY_M, CHECK_RISK, assess
from tests.agents.site_progress.test_site_progress_v3 import AS_OF, codes, visit, work

LAT, LON = 25.75, 82.69
DEG = 1 / 111_195


def _form(**loc):
    return {"work": {"nature": "new", "work_type": "COMMUNITY_HALL"},
            "sites": [{"location": {"lat": LAT, "lon": LON, **loc},
                       "size": {"built_up_area_m2": 400}}]}       # a 20 m side: radius 25 m


def _at(north_m: float, accuracy: float = 8.0, **more):
    return {"gps_point": {"lat": LAT + north_m * DEG, "lon": LON}, "gps_accuracy_m": accuracy,
            "gps_fixes": 30, "gps_weak": False, **more}


def _visits(*readings):
    first = date(2026, 3, 1)
    return [visit(first + timedelta(days=30 * i), **r) for i, r in enumerate(readings)]


def _w(*readings, form=None):
    return work(*_visits(*readings), cost_form=form or _form())


def risk(r, code):
    return next((f.risk for f in r.findings if f.code == code), None)


# ---- the location is recorded every time ------------------------------------------------------

def test_one_video_without_a_location_is_a_note_never_a_finding():
    r = assess(_w(_at(0), {"gps_fixes": 0}, _at(0)), AS_OF)
    assert "LOCATION_NOT_RECORDED" not in codes(r)
    assert any("no location" in n for n in r.evidence["notes"])


@pytest.mark.parametrize("missing", [{"gps_fixes": 0},
                                     {"gps_weak": True, "gps_fixes": 4, "gps_accuracy_m": 1800},
                                     {"mock_location": True, **_at(0)}])
def test_two_of_the_last_three_without_a_location_is_check_this(missing):
    r = assess(_w(_at(0), missing, _at(0), missing), AS_OF)
    assert risk(r, "LOCATION_NOT_RECORDED") == CHECK_RISK, r.headline


def test_weak_gps_under_trees_is_still_a_location_the_views_decide():
    # T136: weak GPS (here +-120 m) on every video is honest noise, never a finding
    weak = {"gps_weak": True, "gps_fixes": 9, "gps_accuracy_m": 120}
    r = assess(_w(weak, weak, weak), AS_OF)
    assert "LOCATION_NOT_RECORDED" not in codes(r)


def test_the_last_three_without_a_location_is_a_question():
    r = assess(_w(_at(0), {"gps_fixes": 0}, {"gps_fixes": 0}, {"gps_fixes": 0}), AS_OF)
    assert risk(r, "LOCATION_NOT_RECORDED") >= 0.4


def test_readings_that_say_nothing_about_gps_are_not_judged():
    # older readings (before the fix count was recorded) carry no GPS fields: not a finding
    r = assess(work(*_visits({}, {}, {}), cost_form=_form()), AS_OF)
    assert "LOCATION_NOT_RECORDED" not in codes(r)


# ---- near where the form says the work is ----------------------------------------------------

def test_filming_around_the_site_is_inside_the_rough_area():
    # the site's own 25 m, standing 40 m back to film it, a pin typed a little off
    r = assess(_w(_at(0), _at(60), _at(-55), _at(90)), AS_OF)
    assert "FILMED_AWAY_FROM_FORM_SITE" not in codes(r), r.headline


def test_one_video_filmed_far_from_the_form_is_check_this():
    r = assess(_w(_at(0), _at(0), _at(400), _at(0)), AS_OF)
    assert risk(r, "FILMED_AWAY_FROM_FORM_SITE") == CHECK_RISK
    f = next(f for f in r.findings if f.code == "FILMED_AWAY_FROM_FORM_SITE")
    assert "m from" in f.text and f.evidence["visits"]


def test_two_videos_filmed_far_from_the_form_is_a_question():
    r = assess(_w(_at(0), _at(250), _at(0), _at(600)), AS_OF)
    assert risk(r, "FILMED_AWAY_FROM_FORM_SITE") >= 0.5


def test_the_phones_own_accuracy_is_allowed_for():
    edge = sitemap.MIN_RADIUS_M + AWAY_M
    r = assess(_w(_at(0), _at(edge + 30, accuracy=40), _at(0)), AS_OF)
    assert "FILMED_AWAY_FROM_FORM_SITE" not in codes(r)


def test_a_road_is_its_whole_line_not_just_its_first_pin():
    road = _form(end_lat=LAT + 800 * DEG, end_lon=LON)
    road["work"]["work_type"] = "ROAD_CC"
    r = assess(_w(_at(0), _at(400), _at(780), form=road), AS_OF)
    assert "FILMED_AWAY_FROM_FORM_SITE" not in codes(r), r.headline


def test_a_form_with_no_usable_pin_is_not_judged_by_distance():
    r = assess(_w(_at(0), _at(5000), form={"work": {"nature": "new"}, "sites": [{}]}), AS_OF)
    assert "FILMED_AWAY_FROM_FORM_SITE" not in codes(r)


def test_a_faked_location_is_never_used_as_where_it_was_filmed():
    r = assess(_w(_at(0), _at(5000, mock_location=True), _at(0)), AS_OF)
    assert "FILMED_AWAY_FROM_FORM_SITE" not in codes(r)


def test_every_place_the_form_gives_counts():
    two = _form()
    two["sites"].append({"location": {"lat": LAT + 2000 * DEG, "lon": LON},
                         "size": {"built_up_area_m2": 400}})
    assert len(sitemap.places(two)) == 2
    r = assess(_w(_at(0), _at(2000), _at(0), form=two), AS_OF)
    assert "FILMED_AWAY_FROM_FORM_SITE" not in codes(r)
