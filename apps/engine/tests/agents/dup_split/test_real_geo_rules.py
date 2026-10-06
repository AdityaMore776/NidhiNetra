"""Duplicate Work's one-site rule on real geography (T139, data/trial/real_geo_check.py).

Jaunpur's real works are mostly solar street lights at named houses, and its houses stand 8 m
apart (Open Buildings). Under the 50 m same-family rule, 37-87% of honest light works were asked
"already sanctioned here?" and half of one institution's honest purchases of another kind. Three
rules fixed it without losing the repeats filed later at the same place:

  * a street light filed the same day (one programme's houses) is never "already sanctioned"
    before it; a hall filed twice on one day still is
  * a street light is at the same site only within POINT_METRES (one spot), not 50 m
  * a purchase is compared with purchases of the same work type (computers vs furniture differ)
"""

from __future__ import annotations

from datetime import date, timedelta

from drishti.agents.dup_split import agent
from drishti.agents.dup_split.repeat import PIN_METRES, POINT_METRES, RepeatIndex

LAT, LON = 25.75, 82.69
M = 1 / 111_195                     # degrees of latitude in a metre


def _work(wid: str, wtype: str, north_m: float, rec: date, *, status: str = "COMPLETED",
          size: dict | None = None) -> dict:
    done = status == "COMPLETED"
    return {"work_id": wid, "description": f"Work {wid} at the site", "amount": 2e5,
            "recommended_date": rec, "sanction_date": rec + timedelta(days=30),
            "completed_date": rec + timedelta(days=120) if done else None,
            "status": status, "district_lgd": "639", "mp_name": "MP A", "work_type_code": wtype,
            "cost_form": {"work": {"work_type": wtype, "nature": "new"},
                          "sites": [{"location": {"lat": LAT + north_m * M, "lon": LON},
                                     "size": size or {}}]}}


def _asked(works: list[dict], wid: str) -> bool:
    idx = RepeatIndex.build(works)
    r = agent.assess(next(w for w in works if w["work_id"] == wid), idx)
    return any(f.code == "SANCTIONED_WORK_AT_THIS_SITE" for f in r.findings)


D = date(2025, 1, 10)


def test_one_programmes_lights_filed_the_same_day_are_not_asked_about_each_other():
    # one programme: lights at neighbouring houses, 6 m apart, recommended on one day
    works = [_work("A", "STREET_LIGHT", 0, D), _work("B", "STREET_LIGHT", 6, D)]
    assert not _asked(works, "B")
    # the same light filed again on a later day is asked
    works[1] = _work("B", "STREET_LIGHT", 6, D + timedelta(days=90), status="SANCTIONED")
    assert _asked(works, "B")


def test_a_hall_filed_twice_on_one_day_is_still_asked():
    # the same-day exception is for a programme of lights only: two halls at one pin are one hall
    works = [_work("A", "COMMUNITY_HALL", 0, D), _work("B", "COMMUNITY_HALL", 10, D)]
    assert _asked(works, "B")


def test_a_neighbours_street_light_is_not_the_same_site():
    later = D + timedelta(days=300)
    near = POINT_METRES + 15                           # the next house but one, well inside 50 m
    assert near < PIN_METRES
    works = [_work("L1", "STREET_LIGHT", 0, D),
             _work("L2", "STREET_LIGHT", near, later, status="SANCTIONED")]
    assert not _asked(works, "L2")
    r = agent.assess(works[1], RepeatIndex.build(works))
    assert not any(f.code == "NEAR_SANCTIONED_WORK" for f in r.findings)   # no note either


def test_a_street_light_filed_again_at_the_same_house_is_asked():
    later = D + timedelta(days=300)
    works = [_work("L1", "STREET_LIGHT", 0, D),
             _work("L2", "STREET_LIGHT", POINT_METRES - 8, later, status="SANCTIONED")]
    assert _asked(works, "L2")
    r = agent.assess(works[1], RepeatIndex.build(works))
    top = next(f for f in r.findings if f.code == "SANCTIONED_WORK_AT_THIS_SITE")
    assert top.evidence["pin_metres"] == POINT_METRES


def test_one_schools_computers_and_furniture_are_two_purchases():
    later = D + timedelta(days=200)
    works = [_work("C1", "COMPUTER", 0, D), _work("F1", "FURNITURE", 3, later, status="SANCTIONED")]
    assert not _asked(works, "F1")
    # computers bought again for the same school are still asked
    works[1] = _work("C2", "COMPUTER", 3, later, status="SANCTIONED")
    assert _asked(works, "C2")


def test_buildings_keep_the_50_m_line_and_the_family():
    later = D + timedelta(days=400)
    works = [_work("H1", "COMMUNITY_HALL", 0, D),
             _work("H2", "LIBRARY", PIN_METRES - 10, later, status="SANCTIONED")]
    assert _asked(works, "H2")                          # a hall filed again as a library


# --- round 4: village lanes and hand pumps (data/trial/real_geo_roads.py) -----------------------

E = 1 / (111_320 * 0.9010)          # degrees of longitude in a metre at this latitude


def _road(wid: str, north_m: float, east0: float, east1: float, rec: date, *,
          status: str = "COMPLETED", north_end: float | None = None) -> dict:
    """A CC road along a street north_m metres north, from east0 to east1 metres east."""
    w = _work(wid, "ROAD_CC", north_m, rec, status=status, size={"length_m": abs(east1 - east0)})
    loc = w["cost_form"]["sites"][0]["location"]
    loc.update(lon=LON + east0 * E, end_lat=LAT + (north_m if north_end is None else north_end) * M,
               end_lon=LON + east1 * E)
    return w


def test_the_next_street_over_is_not_the_same_road():
    # two honest lanes 120 m long, a row of houses (30 m) apart: both ends within 50 m
    later = D + timedelta(days=365)
    works = [_road("R1", 0, 0, 120, D), _road("R2", 30, 5, 125, later, status="SANCTIONED")]
    assert not _asked(works, "R2")


def test_a_lane_filed_again_with_its_ends_re_pinned_is_asked():
    later = D + timedelta(days=365)
    works = [_road("R1", 0, 0, 120, D), _road("R2", 6, -8, 112, later, status="SANCTIONED")]
    assert _asked(works, "R2")


def test_a_lane_filed_again_longer_is_still_asked():
    later = D + timedelta(days=365)
    works = [_road("R1", 0, 0, 120, D), _road("R2", 4, 0, 170, later, status="SANCTIONED")]
    assert _asked(works, "R2")


def test_hand_pumps_at_neighbouring_houses_are_not_asked():
    later = D + timedelta(days=200)
    same_day = [_work("P1", "BOREWELL", 0, D), _work("P2", "BOREWELL", 12, D)]
    assert not _asked(same_day, "P2")                       # one programme's pumps
    works = [_work("P1", "BOREWELL", 0, D),
             _work("P3", "BOREWELL", 35, later, status="SANCTIONED")]
    assert not _asked(works, "P3")                          # a neighbour's pump, later
    works[1] = _work("P4", "BOREWELL", 6, later, status="SANCTIONED")
    assert _asked(works, "P4")                              # the same house's pump again
