r"""T061 + T062 (11 Oct 2026): the location lookup and the Inspection Planner on the real queue.

Input: the LIVE review queue (GET /api/v1/queue, public: the 217 cases of eSAKSHI's dashboard
table, each with its district, description and priority). For every district with queue cases:

  located   each case placed by planner/locate.py: village, block, area, or district (the
            district's start point; not placed)
  one day   planner/plan.py chooses an 8-hour day from the district's cases (no spot checks:
            they need the database, and the blueprint's measure is the flagged visits)
  km saved  the same chosen stops driven in queue order (highest priority first) against the
            planner's order; also every case of the district in one trip, both ways
  per day   an officer working down the queue (each next case added at the end of the drive,
            skipped if the day would run over) against the planner's day: cases visited and
            the value (priority) they carry
  eye       30 random placed cases (--seed; round 1 = 62, round 2 after the fixes = 63), printed
            with their description for reading by eye

-> results/t062_planner.txt (the numbers) and results/t062_eye_sample.txt (the 30 to read)

Run:  apps\engine\.venv\Scripts\python.exe data\trial\t062_planner.py [--url URL] [--seed N]
"""

from __future__ import annotations

import argparse
import json
import random
import statistics
import sys
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "data" / "trial" / "results"
sys.path.insert(0, str(ROOT / "apps" / "engine"))

from drishti.planner import locate as L  # noqa: E402
from drishti.planner import plan as P  # noqa: E402

LIVE = "https://nidhinetra-sih.vercel.app"


def fetch_queue(url: str) -> list[dict]:
    items, page = [], 1
    while True:
        with urllib.request.urlopen(f"{url}/api/v1/queue?page={page}", timeout=60) as r:
            d = json.load(r)
        items += d["items"]
        if len(items) >= d["total"] or not d["items"]:
            return items
        page += 1


def queue_day(home, stops: list[P.Stop], budget: float) -> list[P.Stop]:
    """Down the queue in priority order, each case driven to next; skipped if it won't fit."""
    route: list[P.Stop] = []
    for s in P.list_order(stops):
        if P.tour_minutes(home, route + [s]) <= budget + 1e-9:
            route.append(s)
    return route


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default=LIVE)
    ap.add_argument("--seed", type=int, default=63)
    args = ap.parse_args()
    queue = fetch_queue(args.url)

    by_district: dict[str, list[dict]] = defaultdict(list)
    precision = Counter()
    placed = []
    for item in queue:
        loc = L.locate(item.get("district_lgd"), item.get("description"))
        if loc is None:
            precision["no district"] += 1
            continue
        precision[loc.precision] += 1
        item["_loc"] = loc
        by_district[item["district_lgd"]].append(item)
        if loc.place:
            placed.append(item)

    rows = []
    for code, items in by_district.items():
        start = L.district_start(code)
        home = (start.lat, start.lon)
        stops = [P.Stop(i["work_id"], i["_loc"].lat, i["_loc"].lon, float(i["priority"] or 0))
                 for i in items]
        day = P.choose(home, stops, [], P.DAY_HOURS * 60)
        all_best = P.best_order(home, stops)
        naive = queue_day(home, stops, P.DAY_HOURS * 60)
        rows.append({
            "district": f"{items[0]['district_name']} ({items[0]['state_name']})",
            "cases": len(items),
            "placed": sum(i["_loc"].precision != "district" for i in items),
            "day_stops": len(day.route),
            "day_km": P.tour_km(home, day.route),
            "day_list_km": P.tour_km(home, P.list_order(day.route)),
            "all_km": P.tour_km(home, all_best),
            "all_list_km": P.tour_km(home, P.list_order(stops)),
            "day_min": P.tour_minutes(home, day.route),
            "naive_stops": len(naive), "naive_value": sum(x.value for x in naive),
            "day_value": sum(x.value for x in day.route),
        })

    lines = [f"T062 Inspection Planner on the live review queue ({args.url}), 11 Oct 2026", ""]
    lines.append(f"queue cases {len(queue)} in {len(by_district)} districts")
    for k in ("village", "block", "area", "district", "no district"):
        n = precision.get(k, 0)
        lines.append(f"  placed at {k:12s} {n:4d}  ({100 * n / len(queue):.1f}%)")
    lines.append("")

    def block(title: str, rs: list[dict]) -> None:
        if not rs:
            return
        dk = sum(r["day_km"] for r in rs)
        dl = sum(r["day_list_km"] for r in rs)
        ak = sum(r["all_km"] for r in rs)
        al = sum(r["all_list_km"] for r in rs)
        saved = [1 - r["day_km"] / r["day_list_km"] for r in rs if r["day_list_km"] > 0]
        lines.append(title)
        lines.append(f"  districts {len(rs)}, cases {sum(r['cases'] for r in rs)}, "
                     f"one-day stops {sum(r['day_stops'] for r in rs)} "
                     f"(all cases fit in the day in {sum(r['day_stops'] == r['cases'] for r in rs)})")
        lines.append(f"  one day:   queue order {dl:8.0f} road km, planned {dk:8.0f} km, "
                     f"saved {dl - dk:6.0f} km ({100 * (1 - dk / dl) if dl else 0:.1f}%)")
        if saved:
            lines.append(f"             per district: median saved "
                         f"{100 * statistics.median(saved):.1f}%, best {100 * max(saved):.1f}%, "
                         f"districts with any saving {sum(s > 1e-9 for s in saved)} of "
                         f"{len(saved)}")
        ns, nv = sum(r["naive_stops"] for r in rs), sum(r["naive_value"] for r in rs)
        ps, pv = sum(r["day_stops"] for r in rs), sum(r["day_value"] for r in rs)
        more = sum(r["day_stops"] > r["naive_stops"] for r in rs)
        lines.append(f"  per day:   working down the queue visits {ns} cases (value {nv:.1f}); the "
                     f"planner {ps} (value {pv:.1f}); more visits in {more} districts")
        lines.append(f"  all cases: queue order {al:8.0f} road km, planned {ak:8.0f} km, "
                     f"saved {al - ak:6.0f} km ({100 * (1 - ak / al) if al else 0:.1f}%)")
        lines.append("")

    block("All districts with queue cases", rows)
    block("Districts with 2+ cases placed below district level (the route has real places)",
          [r for r in rows if r["placed"] >= 2])
    block("Districts with 5+ cases", [r for r in rows if r["cases"] >= 5])

    lines.append("Per district (5+ cases), one 8-hour day:")
    lines.append(f"  {'district':42s} cases placed stops  queue-km plan-km saved  queue-day")
    for r in sorted(rows, key=lambda r: -r["cases"]):
        if r["cases"] < 5:
            continue
        lines.append(f"  {r['district'][:42]:42s} {r['cases']:5d} {r['placed']:6d} "
                     f"{r['day_stops']:5d} {r['day_list_km']:9.0f} {r['day_km']:7.0f} "
                     f"{r['day_list_km'] - r['day_km']:5.0f}  {r['naive_stops']:5d}")
    lines.append("")
    lines.append("Distances: straight line x 1.3 at 30 km/h, 40 min a stop, from the district's start")
    lines.append("point (its head office, else the outline's centre). Places are approximate.")
    (RESULTS / "t062_planner.txt").write_bytes(("\n".join(lines) + "\n").encode("utf-8"))
    print("\n".join(lines))

    rnd = random.Random(args.seed)
    sample = rnd.sample(placed, min(30, len(placed)))
    eye = [f"T062 eye sample (seed {args.seed}): 30 random queue cases placed below district level.",
           "Read: is the matched name the place where the work is (the village, or its block)?", ""]
    for n, i in enumerate(sample, 1):
        loc = i["_loc"]
        eye.append(f"{n:2d}. {i['work_id']}  [{i['district_name']}]  -> {loc.place} "
                   f"({loc.precision}, {loc.lat:.4f}, {loc.lon:.4f})")
        eye.append(f"    {(i['description'] or '')[:240]}")
    (RESULTS / "t062_eye_sample.txt").write_bytes(("\n".join(eye) + "\n").encode("utf-8"))
    print(f"\nwrote results/t062_planner.txt and results/t062_eye_sample.txt ({len(sample)} cases)")


if __name__ == "__main__":
    main()
