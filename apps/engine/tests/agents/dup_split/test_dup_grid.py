"""Duplicate Work's map grid (T137) gives exactly the full scan's answers, only faster.

A check looks only at works filed in the grid cells within GRID_MARGIN_M of its own pins. Random
dense districts (roads and halls, short and long, some with one end, some with a far end typed
hundreds of km away) are checked both ways: every at-site work, distance, overlap and nearby note
must be the same."""

from __future__ import annotations

import copy
import random
from datetime import date, timedelta

from drishti.agents.dup_split.repeat import RepeatIndex

LAT, LON = 25.75, 82.69
M = 1 / 111_195


def _work(i: int, rng: random.Random) -> dict:
    linear = rng.random() < 0.5
    lat = LAT + rng.uniform(0, 1000) * M
    lon = LON + rng.uniform(0, 1000) * M
    loc = {"lat": lat, "lon": lon}
    if linear and rng.random() < 0.9:
        far = rng.random() < 0.02                       # a typo'd far end, hundreds of km off
        length = rng.uniform(30, 600) if not far else 400_000
        ang = rng.uniform(0, 6.283)
        import math
        loc.update(end_lat=lat + length * math.cos(ang) * M,
                   end_lon=lon + length * math.sin(ang) * M)
    wtype = rng.choice(["ROAD_CC", "ROAD_BT", "FOOTPATH", "DRAIN"]) if linear else \
        rng.choice(["COMMUNITY_HALL", "SCHOOL_BUILDING", "TOILET_BLOCK"])
    rec = date(2024, 1, 1) + timedelta(days=rng.randrange(700))
    done = rng.random() < 0.5
    return {"work_id": f"G{i}", "description": f"Work {i}", "amount": rng.uniform(1e5, 9e5),
            "recommended_date": rec, "sanction_date": rec + timedelta(days=30),
            "completed_date": rec + timedelta(days=200) if done else None,
            "status": "COMPLETED" if done else "SANCTIONED", "district_lgd": "639",
            "mp_name": "MP A", "work_type_code": wtype,
            "cost_form": {"work": {"work_type": wtype, "nature": "new"},
                          "sites": [{"location": loc, "size": {"length_m": 100}}]}}


def _found(idx: RepeatIndex, w: dict) -> tuple:
    f = idx.check(w)
    return (tuple((x.work_id, round(d, 6)) for x, d in f["at_site"]),
            tuple(sorted(f["overlap"].items())),
            tuple((x.work_id, round(d, 6)) for x, d in f["near"]))


def test_the_grid_gives_the_full_scans_answers():
    rng = random.Random(137)
    works = [_work(i, rng) for i in range(400)]
    grid = RepeatIndex.build(works)
    scan = copy.copy(grid)
    scan._grid, scan._wide = {}, {}                     # no grid: every earlier work is looked at
    assert grid._grid and grid._wide
    differ = [w["work_id"] for w in works if _found(grid, w) != _found(scan, w)]
    assert not differ
    asked = sum(bool(_found(grid, w)[0]) for w in works)
    assert asked > 20                                   # the districts are dense enough to matter


def test_a_new_work_checked_live_gets_the_same_answers():
    rng = random.Random(7)
    works = [_work(i, rng) for i in range(300)]
    grid = RepeatIndex.build(works)
    scan = copy.copy(grid)
    scan._grid, scan._wide = {}, {}
    for k in range(60):
        new = _work(10_000 + k, rng)
        new["recommended_date"] = date(2026, 6, 1)
        assert _found(grid, new) == _found(scan, new)
