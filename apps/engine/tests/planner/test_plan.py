"""T062: one day's visits: greedy by value per extra minute within the hours, then best order."""

import itertools
import random

import pytest

from drishti.planner import plan as P

HOME = (22.50, 72.90)


def stop(key, lat, lon, value=1.0, kind="flagged"):
    return P.Stop(key=key, lat=lat, lon=lon, value=value, kind=kind)


def test_road_km_is_the_straight_line_times_the_road_factor():
    # one degree of latitude is 111.2 km on the sphere
    assert P.road_km((22.0, 72.0), (23.0, 72.0)) == pytest.approx(111.19 * 1.3, rel=1e-3)
    assert P.road_km(HOME, HOME) == 0.0


def test_a_day_counts_driving_at_30_kmh_and_40_minutes_a_stop():
    one = [stop("A", 22.50 + 15 / 111.19 / 1.3, 72.90)]          # 15 road km away
    assert P.tour_minutes(HOME, one) == pytest.approx(2 * 30 + 40, rel=1e-3)
    assert P.tour_minutes(HOME, []) == 0.0


def _brute(start, stops):
    return min(P.tour_km(start, list(p)) for p in itertools.permutations(stops))


@pytest.mark.parametrize("n", [1, 2, 3, 5, 7])
def test_the_exact_order_is_the_shortest_round_trip(n):
    rnd = random.Random(n)
    stops = [stop(f"S{i}", 22 + rnd.random(), 72 + rnd.random()) for i in range(n)]
    got = P.best_order(HOME, stops)
    assert sorted(s.key for s in got) == sorted(s.key for s in stops)
    assert P.tour_km(HOME, got) == pytest.approx(_brute(HOME, stops))


def test_stops_at_one_place_are_visited_together():
    a1, a2 = stop("A1", 23.0, 73.0), stop("A2", 23.0, 73.0)
    b = stop("B", 22.0, 72.0)
    got = [s.key for s in P.best_order(HOME, [a1, b, a2])]
    assert abs(got.index("A1") - got.index("A2")) == 1


def test_a_long_route_is_improved_and_keeps_every_stop():
    rnd = random.Random(7)
    stops = [stop(f"S{i}", 22 + rnd.random(), 72 + rnd.random()) for i in range(20)]
    got = P.best_order(HOME, stops)
    assert sorted(s.key for s in got) == sorted(s.key for s in stops)
    assert P.tour_km(HOME, got) <= P.tour_km(HOME, stops)


def test_the_day_never_runs_over_its_hours():
    rnd = random.Random(3)
    flagged = [stop(f"F{i}", 22 + rnd.random(), 72 + rnd.random(), rnd.random() + 0.5)
               for i in range(30)]
    for hours in (1, 3, 8, 12):
        day = P.choose(HOME, flagged, [], hours * 60)
        assert P.tour_minutes(HOME, day.route) <= hours * 60 + 1e-6
        assert {s.key for s in day.route} | {s.key for s in day.left} == {s.key for s in flagged}


def test_more_value_per_extra_minute_goes_first():
    near_small = stop("near", 22.52, 72.90, value=1.0)        # ~3 road km away
    far_big = stop("far", 23.40, 72.90, value=1.5)            # ~130 road km away
    # room for one stop's visit plus a short drive only
    day = P.choose(HOME, [far_big, near_small], [], 60)
    assert [s.key for s in day.route] == ["near"]
    assert [s.key for s in day.left] == ["far"]


def test_spot_checks_only_fill_time_the_flagged_works_leave():
    flagged = [stop(f"F{i}", 22.50, 72.90) for i in range(3)]          # 3 x 40 min = 120
    spot = [stop(f"R{i}", 22.50, 72.90, value=0.0, kind="spot") for i in range(3)]
    day = P.choose(HOME, flagged, spot, 200)                          # room for 5 visits
    kinds = [s.kind for s in day.route]
    assert kinds.count("flagged") == 3 and kinds.count("spot") == 2
    assert [s.key for s in day.left_spot] == ["R2"]


def test_a_day_too_short_for_one_visit_is_empty():
    day = P.choose(HOME, [stop("A", 22.50, 72.90)], [], 30)
    assert day.route == [] and [s.key for s in day.left] == ["A"]


def test_nothing_to_visit_gives_an_empty_day():
    day = P.choose(HOME, [], [], 480)
    assert day.route == [] and day.left == [] and day.left_spot == []


def test_list_order_visits_by_value_then_spot_checks():
    a, b = stop("A", 23.0, 73.0, 2.0), stop("B", 22.0, 72.0, 3.0)
    r = stop("R", 22.5, 73.5, 0.0, kind="spot")
    assert [s.key for s in P.list_order([a, r, b])] == ["B", "A", "R"]
