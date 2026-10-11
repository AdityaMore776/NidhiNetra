"""One day's inspection visits for a district officer (T062), the blueprint's algorithm.

  travel     straight-line km x 1.3 (roads wind), at 30 km/h; 40 minutes at each stop; the day
             starts and ends at the district's start point (planner/locate.py)
  value      a flagged work's queue priority = risk x (1 + log10(amount in lakh)), as the queue
             ranks it; a spot check (a random lower-risk work) has no value of its own
  choose     flagged works first: add the one with the most value per extra minute (its cheapest
             place in the route so far) while the day fits; re-order; repeat until none fits.
             Then spot checks fill the time left, nearest first. What does not fit is listed
  order      exact (Held-Karp) up to 12 places; above that nearest neighbour + 2-opt. Stops at
             one place are one place: visited together

Pure functions; the API (planner/service.py) supplies the works.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from drishti.planner.locate import km

ROAD_FACTOR = 1.3
SPEED_KMH = 30.0
STOP_MIN = 40.0
DAY_HOURS = 8.0
EXACT_UP_TO = 12

Point = tuple[float, float]


@dataclass(frozen=True)
class Stop:
    key: str
    lat: float
    lon: float
    value: float
    kind: str = "flagged"           # flagged | spot


@dataclass
class Day:
    route: list[Stop] = field(default_factory=list)
    left: list[Stop] = field(default_factory=list)          # flagged works for the next trip
    left_spot: list[Stop] = field(default_factory=list)


def road_km(a: Point, b: Point) -> float:
    return km(a[0], a[1], b[0], b[1]) * ROAD_FACTOR


def _pt(s: Stop) -> Point:
    return (s.lat, s.lon)


def tour_km(start: Point, stops: list[Stop]) -> float:
    if not stops:
        return 0.0
    pts = [start, *(_pt(s) for s in stops), start]
    return sum(road_km(a, b) for a, b in zip(pts, pts[1:], strict=False))


def tour_minutes(start: Point, stops: list[Stop]) -> float:
    if not stops:
        return 0.0
    return tour_km(start, stops) / SPEED_KMH * 60.0 + STOP_MIN * len(stops)


def list_order(stops: list[Stop]) -> list[Stop]:
    """The order of the queue page: flagged works by value, then the spot checks."""
    return sorted(stops, key=lambda s: (s.kind != "flagged", -s.value, s.key))


# ------------------------------------------------------------------ route order

def _held_karp(start: Point, places: list[Point]) -> list[int]:
    n = len(places)
    d0 = [road_km(start, p) for p in places]
    d = [[road_km(a, b) for b in places] for a in places]
    best: dict[tuple[int, int], tuple[float, int]] = {}
    for j in range(n):
        best[(1 << j, j)] = (d0[j], -1)
    for mask in range(1, 1 << n):
        for j in range(n):
            cur = best.get((mask, j))
            if cur is None:
                continue
            for k in range(n):
                if mask & (1 << k):
                    continue
                nxt = (mask | (1 << k), k)
                cost = cur[0] + d[j][k]
                if nxt not in best or cost < best[nxt][0]:
                    best[nxt] = (cost, j)
    full = (1 << n) - 1
    last = min(range(n), key=lambda j: best[(full, j)][0] + d0[j])
    order, mask = [], full
    while last != -1:
        order.append(last)
        prev = best[(mask, last)][1]
        mask ^= 1 << last
        last = prev
    return order[::-1]


def _two_opt(start: Point, places: list[Point]) -> list[int]:
    left = set(range(len(places)))
    order, here = [], start
    while left:                                   # nearest neighbour
        j = min(left, key=lambda i: (road_km(here, places[i]), i))
        order.append(j)
        left.discard(j)
        here = places[j]

    def length(o: list[int]) -> float:
        pts = [start, *(places[i] for i in o), start]
        return sum(road_km(a, b) for a, b in zip(pts, pts[1:], strict=False))

    best, improved = length(order), True
    while improved:
        improved = False
        for i in range(len(order) - 1):
            for k in range(i + 1, len(order)):
                cand = order[:i] + order[i:k + 1][::-1] + order[k + 1:]
                c = length(cand)
                if c < best - 1e-9:
                    order, best, improved = cand, c, True
    return order


def best_order(start: Point, stops: list[Stop]) -> list[Stop]:
    """The shortest round trip through the stops (exact when it is small)."""
    places: list[Point] = []
    at: dict[Point, list[Stop]] = {}
    for s in stops:
        if _pt(s) not in at:
            places.append(_pt(s))
            at[_pt(s)] = []
        at[_pt(s)].append(s)
    if not places:
        return []
    order = (_held_karp(start, places) if len(places) <= EXACT_UP_TO
             else _two_opt(start, places))
    cand = [s for i in order for s in at[places[i]]]
    # never longer than the order it was given (2-opt from nearest neighbour can be)
    return cand if tour_km(start, cand) <= tour_km(start, stops) + 1e-9 else list(stops)


# ------------------------------------------------------------------ choosing the day

def _cheapest_insert(start: Point, route: list[Stop], s: Stop) -> tuple[float, int]:
    """Extra minutes to visit s at its best place in the route, and that place."""
    pts = [start, *(_pt(r) for r in route), start]
    best, where = float("inf"), 0
    for i in range(len(pts) - 1):
        extra = (road_km(pts[i], _pt(s)) + road_km(_pt(s), pts[i + 1])
                 - road_km(pts[i], pts[i + 1]))
        if extra < best:
            best, where = extra, i
    return best / SPEED_KMH * 60.0 + STOP_MIN, where


def _fill(start: Point, route: list[Stop], pool: list[Stop], budget_min: float,
          by_value: bool) -> tuple[list[Stop], list[Stop]]:
    pool = list(pool)
    while True:
        used = tour_minutes(start, route)
        pick = None
        for s in pool:
            extra, where = _cheapest_insert(start, route, s)
            if used + extra > budget_min + 1e-9:
                continue
            # flagged: value per extra minute; spot checks: nearest first
            rank = ((s.value / extra, s.value) if by_value else (-extra, 0.0)) + (_neg(s.key),)
            if pick is None or rank > pick[0]:
                pick = (rank, s, where)
        if pick is None:
            return route, pool
        _, s, where = pick
        route = route[:where] + [s] + route[where:]
        pool.remove(s)
        better = best_order(start, route)
        if tour_minutes(start, better) <= tour_minutes(start, route):
            route = better


def _neg(key: str) -> tuple[int, ...]:
    """Sorts keys in reverse so that, on a tie, the earlier key wins a max()."""
    return tuple(-ord(c) for c in key)


def choose(start: Point, flagged: list[Stop], spot: list[Stop], budget_min: float) -> Day:
    route, left = _fill(start, [], flagged, budget_min, by_value=True)
    route, left_spot = _fill(start, route, spot, budget_min, by_value=False)
    return Day(route=route, left=list_order(left), left_spot=sorted(left_spot,
                                                                    key=lambda s: s.key))
