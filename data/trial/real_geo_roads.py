r"""Duplicate Work on real geography, round 4: village lanes and hand pumps (T139).

Real descriptions say where these works are: 39% of the dashboard's roads and 45% of its paths
run "from X's house to Y's house", the lengths they state are short (median 121 m; 40% are
100 m or less), and roads are filed in same-day programmes (often 2-8 lanes by one MP in a
day). A third of borewells are hand pumps "near X's house", filed in batches of up to 20+.

The one-site rule for a road (`repeat.same_site`, `repeat.on_line`) calls two roads one when
both ends lie within LINEAR_METRES of the other's, or when OVERLAP_SHARE of one lies within
OVERLAP_METRES of the other's line. In a village where lanes run between rows of houses, an
honest neighbouring lane may meet either test. As in real_geo_check.py, everything is real but
the pins: each lane runs between two real houses (Open Buildings, Jaunpur's village cores) at a
length drawn from the lengths real descriptions state, its ends pinned with a phone's GPS error.

  random lanes      programmes of 1-8 lanes, each from a house to another house at a real length
  parallel streets  a lane and, a year later, the next street over, GAP metres away
  repeats           a sanctioned lane filed again 6-18 months later: its ends re-pinned; once
                    more 30-60 m longer at one end; once more as the inner 70% of it
  hand pumps        Jaunpur's real programme days and sizes, each pump at a real house

Writes results/real_geo_roads.txt and .json: counts and shares only.

Run:  apps\engine\.venv\Scripts\python.exe data\trial\real_geo_roads.py
      (after data\trial\real_geo_check.py --fetch; needs `pip install indiapins`)
"""

from __future__ import annotations

import argparse
import copy
import json
import math
import random
import re
import sys
from datetime import date, timedelta
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "apps" / "engine"))
sys.path.insert(0, str(ROOT / "data"))
sys.path.insert(0, str(ROOT / "data" / "trial"))

import real_geo_check as geo  # noqa: E402
from esakshi_dashboard import load  # noqa: E402

from drishti.agents.dup_split import agent as dup  # noqa: E402
from drishti.agents.dup_split import repeat  # noqa: E402
from drishti.cost_form import catalog  # noqa: E402

OUT = ROOT / "data" / "trial" / "results" / "real_geo_roads"
KM = re.compile(r"(\d+(?:\.\d+)?)\s*(?:km|kms|kilomet)", re.IGNORECASE)
METRES = re.compile(r"(\d[\d,]*(?:\.\d+)?)\s*(?:rm|r\.m\.?|rmt|mtrs?|meters?|metres?|mt|m)\b"
                    r"(?!\s*(?:x|\*|wide|width|chaura))", re.IGNORECASE)

ROAD_RULES = {
    "T139: ends 50 m, on the line 25 m": {"LINEAR_METRES": 50.0, "OVERLAP_METRES": 25.0,
                                          "ENDS_NEED_LINE": False},
    "ends 30 m": {"LINEAR_METRES": 30.0, "OVERLAP_METRES": 25.0, "ENDS_NEED_LINE": False},
    "ends 30 m, on the line 15 m": {"LINEAR_METRES": 30.0, "OVERLAP_METRES": 15.0,
                                    "ENDS_NEED_LINE": False},
    # both ends near AND on its line (within L m); a longer road or a part of one, whose ends
    # are not both near, still by the line within O m
    **{f"ends {e} AND line {L}; else line {o}": {
        "LINEAR_METRES": float(e), "ENDS_NEED_LINE": True, "ENDS_LINE_METRES": float(L),
        "OVERLAP_METRES": float(o)}
       for e, L, o in ((50, 20, 20), (50, 20, 25), (50, 15, 25), (30, 20, 25), (40, 20, 25))},
}
PUMP_RULES = {
    "T139: 50 m, same day counts": {"POINT_FAMILIES": ("lights",),
                                    "SAME_DAY_APART": ("lights",)},
    "+ pumps: same day apart": {"POINT_FAMILIES": ("lights",),
                                "SAME_DAY_APART": ("lights", "borewell")},
    "+ pumps one spot (20 m)": {"POINT_FAMILIES": ("lights", "borewell"),
                                "SAME_DAY_APART": ("lights", "borewell")},
}
KNOBS = ("LINEAR_METRES", "OVERLAP_METRES", "ENDS_NEED_LINE", "ENDS_LINE_METRES",
         "POINT_FAMILIES", "SAME_DAY_APART")


def lane_lengths(works: list[dict]) -> list[float]:
    """The lengths real road and path descriptions state, 20 m to 2 km."""
    out = []
    for w in works:
        if (catalog.family_of(w.get("work_type_code")) or ("",))[0] not in ("road", "path"):
            continue
        d = w.get("description") or ""
        m = KM.search(d)
        v = float(m.group(1)) * 1000 if m else None
        if v is None and (m := METRES.search(d)):
            v = float(m.group(1).replace(",", ""))
        if v is not None and 20 <= v <= 2000:
            out.append(v)
    return out


def _pin(places: geo.Places, x: float, y: float) -> tuple[float, float]:
    s = 15.0 if places.rnd.random() < 0.10 else 5.0
    return geo._latlon(x + places.rnd.gauss(0, s), y + places.rnd.gauss(0, s))


def _lane(wid: str, a: tuple, b: tuple, rec: date, places: geo.Places, *,
          status: str = "SANCTIONED") -> dict:
    """A CC road filed from point a to point b (metres east and north), its ends GPS-pinned."""
    (la, lo), (eb, eo) = _pin(places, *a), _pin(places, *b)
    length = math.dist(a, b)
    return {"work_id": wid, "district_lgd": geo.DISTRICT_LGD, "district_name": geo.DISTRICT,
            "mp_name": "SIM", "work_type_code": "ROAD_CC",
            "description": f"CC road {wid}", "amount": round(length * 3500, -2),
            "recommended_date": rec,
            "sanction_date": rec + timedelta(days=30) if status != "RECOMMENDED" else None,
            "status": status, "_ends": (a, b),
            "cost_form": {"work": {"work_type": "ROAD_CC", "nature": "new"},
                          "sites": [{"location": {"lat": round(la, 7), "lon": round(lo, 7),
                                                  "end_lat": round(eb, 7), "end_lon": round(eo, 7)},
                                     "size": {"length_m": round(length)}}]}}


def random_lanes(places: geo.Places, lengths: list[float], programmes: int) -> list[dict]:
    """Programmes of 1-8 lanes in a village, each lane from one real house to another."""
    rnd, out = places.rnd, []
    for p in range(programmes):
        core = places.village()
        houses = np.array(core["houses"])
        pts = places.xy[houses]
        rec = date(2023, 4, 1) + timedelta(days=rnd.randrange(0, 900))
        for _ in range(rnd.choice((1, 1, 2, 2, 3, 4, 5, 8))):
            i = rnd.randrange(len(houses))
            length = rnd.choice(lengths)
            d = np.hypot(*(pts - pts[i]).T)
            near = np.flatnonzero(np.abs(d - length) <= 0.15 * length)
            if not len(near):
                continue
            j = int(rnd.choice(list(near)))
            out.append(_lane(f"SIM/L/{len(out):05d}", tuple(pts[i]), tuple(pts[j]), rec, places))
    return out


def parallel_lanes(places: geo.Places, lengths: list[float], gap: float, n: int) -> list[dict]:
    """A lane, and a year later the next street over, `gap` metres away (both honest)."""
    rnd, out = places.rnd, []
    for k in range(n):
        core = places.village()
        x0, y0 = places.xy[rnd.choice(core["houses"])]
        th = rnd.uniform(0, math.pi)
        length = max(50.0, rnd.choice(lengths))
        ux, uy, nx, ny = math.cos(th), math.sin(th), -math.sin(th), math.cos(th)
        rec = date(2023, 4, 1) + timedelta(days=rnd.randrange(0, 500))
        out.append(_lane(f"SIM/P/{k:04d}a", (x0, y0), (x0 + ux * length, y0 + uy * length),
                         rec, places))
        s = rnd.uniform(-0.2, 0.2) * length
        l2 = length * rnd.uniform(0.8, 1.2)
        a = (x0 + nx * gap + ux * s, y0 + ny * gap + uy * s)
        out.append(_lane(f"SIM/P/{k:04d}b", a, (a[0] + ux * l2, a[1] + uy * l2),
                         rec + timedelta(days=rnd.randrange(200, 500)), places))
    return out


def lane_repeats(honest: list[dict], places: geo.Places, n: int, how: str) -> list[dict]:
    """n sanctioned lanes filed again 6-18 months later: re-pinned, longer, or a part of it."""
    rnd, out = places.rnd, []
    for w in rnd.sample(honest, min(n, len(honest))):
        (ax, ay), (bx, by) = w["_ends"]
        ln = math.dist((ax, ay), (bx, by)) or 1.0
        ux, uy = (bx - ax) / ln, (by - ay) / ln
        if how == "longer":
            ext = rnd.uniform(30, 60)
            a, b = (ax, ay), (bx + ux * ext, by + uy * ext)
        elif how == "part":
            a, b = (ax + ux * 0.15 * ln, ay + uy * 0.15 * ln), (bx - ux * 0.15 * ln,
                                                                by - uy * 0.15 * ln)
        else:
            a, b = (ax, ay), (bx, by)
        rec = w["recommended_date"] + timedelta(days=rnd.randrange(180, 540))
        out.append(_lane(f"SIM/R/{how[:2]}{len(out):04d}", a, b, rec, places,
                         status="RECOMMENDED"))
    return out


def honest_pumps(works: list[dict], places: geo.Places) -> list[dict]:
    """Jaunpur's real programme days and sizes (its light works), each a hand pump at a house."""
    out = []
    for w in geo.honest_lights(works, places, 10, True):
        w = copy.deepcopy(w)
        w["work_type_code"] = "BOREWELL"
        w["cost_form"]["work"]["work_type"] = "BOREWELL"
        w["cost_form"]["sites"] = w["cost_form"]["sites"][:1]
        w["_houses"] = w["_houses"][:1]
        out.append(w)
    return out


def _set(knobs: dict) -> None:
    for k, v in knobs.items():
        setattr(repeat, k, v)


def why(honest: list[dict], rest: list[dict]) -> dict:
    """What asked each honest lane: both ends, or lying on the line; a work filed the same day."""
    idx = repeat.RepeatIndex.build(rest + honest)
    out = {"same_day": 0, "by_ends": 0, "on_the_line": 0, "short_lane_<=100m": 0}
    for w in honest:
        found = idx.check(w)
        if not found or not found["at_site"]:
            continue
        x = found["at_site"][0][0]
        out["same_day"] += x.first == found["me"].first
        out["on_the_line" if x.work_id in found["overlap"] else "by_ends"] += 1
        out["short_lane_<=100m"] += w["cost_form"]["sites"][0]["size"]["length_m"] <= 100
    return out


def evaluate(rest: list[dict], honest: list[dict], probes: dict[str, list[dict]],
             rules: dict, engine: dict) -> dict:
    """The real Duplicate agent under each rule: honest works asked, each probe set asked."""
    out = {}
    for name, knobs in {**rules, "engine now": {}}.items():
        _set({**engine, **knobs})
        res = {}
        for label, ws in (("honest", honest), *probes.items()):
            idx = repeat.RepeatIndex.build(rest + honest + ([] if label == "honest" else ws))
            rs = [dup.assess(w, idx) for w in ws]
            res[label] = [sum(map(geo.asked, rs)), len(rs)]
            res[f"{label}_errors"] = sum(1 for r in rs if r.status.value == "ERROR")
        out[name] = res
    _set(engine)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()
    engine = {k: getattr(repeat, k) for k in KNOBS}
    pos, b = geo.post_offices(), geo.buildings()
    works, _ = load()
    lengths = lane_lengths(works)
    jaunpur = [w for w in works if w.get("district_name") == "Jaunpur"]
    lights = [w for w in jaunpur if w.get("work_type_code") == "STREET_LIGHT"]
    report = {"lengths": {"n": len(lengths),
                          "deciles": [round(x) for x in np.percentile(lengths, range(10, 100, 10))],
                          "share_100m_or_less": round(float(np.mean(np.array(lengths) <= 100)), 3)},
              "scenarios": []}

    def scenario(label: str, honest: list[dict], probes: dict, rules: dict,
                 earlier: list[dict] | None = None) -> None:
        rest = jaunpur + (earlier or [])
        r = evaluate(rest, honest, probes, rules, engine)
        reasons = why(honest, rest) if rules is ROAD_RULES else None
        report["scenarios"].append({"label": label, "rules": r, "why_asked_now": reasons})
        print(label, reasons or "")
        for name, x in r.items():
            print(f"   {name:<36} " + "  ".join(
                f"{k} {v[0]}/{v[1]}" for k, v in x.items() if isinstance(v, list)))

    places = geo.Places(b, pos, random.Random(args.seed))
    lanes = random_lanes(places, lengths, 300)
    scenario("roads: programmes of lanes between real houses", lanes,
             {f"repeat {how}": lane_repeats(lanes, places, 100, how)
              for how in ("re-pinned", "longer", "part")}, ROAD_RULES)
    for gap in (15, 25, 35, 50):
        places = geo.Places(b, pos, random.Random(args.seed))
        pairs = parallel_lanes(places, lengths, gap, 150)
        later = [w for w in pairs if w["work_id"].endswith("b")]
        firsts = [w for w in pairs if w["work_id"].endswith("a")]
        scenario(f"roads: the next street over, {gap} m away", later,
                 {"repeat re-pinned": lane_repeats(firsts, places, 100, "re-pinned")},
                 ROAD_RULES, earlier=firsts)
    places = geo.Places(b, pos, random.Random(args.seed))
    pumps = honest_pumps(lights, places)
    scenario("hand pumps at houses (Jaunpur's programme days)", pumps,
             {"repeat at the same house": geo.repeats(pumps, places, 100)}, PUMP_RULES)
    write(report)


def write(report: dict) -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.with_suffix(".json").write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    ln = report["lengths"]
    lines = ["Duplicate Work on real geography, round 4: village lanes and hand pumps (T139)", "",
             f"Lengths stated in real road and path descriptions: {ln['n']:,}; deciles "
             f"{ln['deciles']} m; {ln['share_100m_or_less']:.0%} are 100 m or less.", ""]
    for sc in report["scenarios"]:
        lines.append(sc["label"] + (f"   (honest asked now, by what: {sc['why_asked_now']})"
                                    if sc.get("why_asked_now") else ""))
        for name, x in sc["rules"].items():
            cells = "  ".join(f"{k} {v[0]}/{v[1]} ({v[0] / max(1, v[1]):.0%})"
                              for k, v in x.items() if isinstance(v, list))
            errs = sum(v for k, v in x.items() if k.endswith("_errors"))
            lines.append(f"   {name:<36} {cells}  errors {errs}")
        lines.append("")
    OUT.with_suffix(".txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
