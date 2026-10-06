r"""Duplicate Work's T139 rules in other districts, round 5: do they hold where villages differ?

T139 fitted the one-site rules to Jaunpur's village cores (real_geo_check.py, real_geo_roads.py):
street lights and hand pumps are one spot (20 m) and one programme's are never repeats of each
other, purchases are compared by kind, and a road is the same road only when both ends are near
AND it lies on the other's line. Jaunpur is one kind of place: large nucleated villages on the
Gangetic plain, houses 8 m apart. This runs the same scenarios in districts that look different,
each with its own real works, real post offices and real buildings (Open Buildings):

  Kheri      Terai plains, Uttar Pradesh            Howrah    dense peri-urban, West Bengal
  Bokaro     plateau hamlets, Jharkhand             Palakkad  dispersed homesteads, Kerala
  Puri       coast, Odisha                          Kheda     compact villages, Gujarat

Each scenario is run under the rules before T139 (T137) and the engine now:
  lights   the district's real light works (dates, MPs, programme days), each at a real house,
           10 a village in one hamlet / anywhere in the core; 100 planted repeats
  pumps    the same programmes as hand pumps (borewell)
  roads    programmes of lanes between real houses at real stated lengths; the next street over
           at 25 and 35 m; 100 repeats re-pinned

Writes results/real_geo_districts.txt and .json: counts and shares only.

Run:  apps\engine\.venv\Scripts\python.exe data\trial\real_geo_districts.py
      (fetches each district's buildings once, about 200-800 MB read; needs indiapins, s2sphere)
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "apps" / "engine"))
sys.path.insert(0, str(ROOT / "data"))
sys.path.insert(0, str(ROOT / "data" / "trial"))

import real_geo_check as geo  # noqa: E402
import real_geo_roads as rg  # noqa: E402
from esakshi_dashboard import load  # noqa: E402

from drishti.agents.dup_split import repeat  # noqa: E402

OUT = ROOT / "data" / "trial" / "results" / "real_geo_districts"
DISTRICTS = ("Jaunpur", "Kheri", "Bokaro", "Puri", "Howrah", "Palakkad", "Kheda")
KNOBS = ("POINT_FAMILIES", "POINT_METRES", "BY_TYPE", "SAME_DAY_APART", "LINEAR_METRES",
         "ENDS_NEED_LINE", "ENDS_LINE_METRES", "OVERLAP_METRES")
BEFORE = {"POINT_FAMILIES": (), "BY_TYPE": (), "SAME_DAY_APART": (), "LINEAR_METRES": 50.0,
          "ENDS_NEED_LINE": False}
MIN_LIGHTS = 50


def spacing(b: np.ndarray) -> dict:
    """How close the district's real houses stand (20-250 m2), and how many village cores."""
    xy, area = geo._xy(b[:, 0], b[:, 1]), b[:, 2]
    pts = xy[(area >= 20) & (area <= 250)]
    d, _ = cKDTree(pts).query(pts, k=2)
    return {"houses": len(pts), "nearest_median_m": round(float(np.median(d[:, 1])), 1),
            "nearest_within_15m": round(float((d[:, 1] <= 15).mean()), 3)}


def run_district(name: str, works: list[dict], lengths: list[float], seed: int,
                 engine: dict) -> dict:
    geo.configure(name)
    pos = geo.post_offices()
    if not geo.OB_FILE.exists():
        print(f"{name}: fetching buildings ({len(geo.CELLS)} cells)")
        geo.fetch(pos)
    b = geo.buildings()
    mine = [w for w in works if w.get("district_name") == name]
    lights = [w for w in mine if w.get("work_type_code") == "STREET_LIGHT"]
    out = {"district": name, "post_offices": len(pos), "buildings": len(b), "works": len(mine),
           "light_works": len(lights), "spacing": spacing(b), "scenarios": {}}
    rules = {"before T139": BEFORE}

    def scenario(label, honest, probes, earlier=None):
        if not honest:
            return
        r = rg.evaluate(mine + (earlier or []), honest, probes, rules, engine)
        out["scenarios"][label] = r
        print(f"  {label:<34} " + "   ".join(
            f"{rule}: " + ", ".join(f"{k} {v[0]}/{v[1]}" for k, v in x.items()
                                    if isinstance(v, list)) for rule, x in r.items()))

    places = geo.Places(b, pos, random.Random(seed))
    out["village_cores"] = len(places.cores)
    print(f"{name}: {len(pos)} post offices, {len(places.cores)} village cores, "
          f"{len(mine)} works ({len(lights)} lights), houses {out['spacing']}")
    if len(places.cores) < 10:
        return out
    if len(lights) >= MIN_LIGHTS:
        for hamlet in (True, False):
            places = geo.Places(b, pos, random.Random(seed))
            honest = geo.honest_lights(lights, places, 10, hamlet)
            scenario(f"lights, 10 a village, {'one hamlet' if hamlet else 'anywhere'}", honest,
                     {"repeats": geo.repeats(honest, places, 100)})
        places = geo.Places(b, pos, random.Random(seed))
        pumps = rg.honest_pumps(lights, places)
        scenario("hand pumps at houses", pumps, {"repeats": geo.repeats(pumps, places, 100)})
    places = geo.Places(b, pos, random.Random(seed))
    lanes = rg.random_lanes(places, lengths, 300)
    scenario("roads: programmes of lanes", lanes,
             {"repeats": rg.lane_repeats(lanes, places, 100, "re-pinned")})
    for gap in (25, 35):
        places = geo.Places(b, pos, random.Random(seed))
        pairs = rg.parallel_lanes(places, lengths, gap, 150)
        firsts = [w for w in pairs if w["work_id"].endswith("a")]
        scenario(f"roads: the next street over, {gap} m",
                 [w for w in pairs if w["work_id"].endswith("b")],
                 {"repeats": rg.lane_repeats(firsts, places, 100, "re-pinned")}, earlier=firsts)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--only", nargs="*")
    args = ap.parse_args()
    engine = {k: getattr(repeat, k) for k in KNOBS}
    works, _ = load()
    lengths = rg.lane_lengths(works)
    report = [run_district(d, works, lengths, args.seed, engine)
              for d in (args.only or DISTRICTS)]
    write(report)


def write(report: list[dict]) -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.with_suffix(".json").write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    lines = ["Duplicate Work's T139 rules in other districts (round 5)", "",
             "Honest works asked, and planted repeats asked: before T139 -> the engine now.", ""]
    for d in report:
        sp = d["spacing"]
        lines.append(f"{d['district']}: {d['post_offices']} post offices, "
                     f"{d.get('village_cores', 0)} village cores, {d['works']:,} real works "
                     f"({d['light_works']:,} lights); houses {sp['nearest_median_m']} m apart "
                     f"(median), {sp['nearest_within_15m']:.0%} within 15 m of the next")
        for label, r in d["scenarios"].items():
            b, n = r["before T139"], r["engine now"]
            h0, h1, p0, p1 = b["honest"], n["honest"], b["repeats"], n["repeats"]
            lines.append(f"   {label:<34} honest {h0[0] / max(1, h0[1]):6.1%} -> "
                         f"{h1[0] / max(1, h1[1]):6.1%} (of {h1[1]:>4})   repeats "
                         f"{p0[0] / max(1, p0[1]):5.0%} -> {p1[0] / max(1, p1[1]):5.0%}")
        lines.append("")
    OUT.with_suffix(".txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
