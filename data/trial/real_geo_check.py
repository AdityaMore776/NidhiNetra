r"""The Duplicate Work agent on real geography: Jaunpur's real works at real buildings (T139).

The owner (5 Oct 2026): "find relevant data or example data that you can from anywhere and test on
it temporarily, after rounds of testing iterate from what you've seen". No agency has filed the
form's map pins yet, so the pins are the one thing simulated here; everything around them is real:

  works      Jaunpur's 1,038 real works in the eSAKSHI dashboard tables (data/esakshi_dashboard.py):
             their dates, amounts, MPs, kinds and descriptions. 1,006 are solar street lights,
             each filed as its own work at one or a few named houses.
  villages   Jaunpur's post offices with a map position (the India Post directory, packaged on
             PyPI as `indiapins`): 106 real village and town centres inside the district.
  buildings  Google's Open Buildings v3 (CC BY 4.0, satellite footprints): every building within
             600 m of those centres, confidence 0.70 or more (data/raw/open_buildings/, fetched
             once with --fetch; never committed).

An honest agency pins each work at its own building, with a phone's GPS error (5 m, and 15 m for
one pin in ten). Each light work goes to a real house; works of one programme (one MP, one day)
go to a few villages, a handful per village, either in one hamlet (the nearest houses to one
house) or anywhere in the village core. Building works go to real buildings of 150 m2 or more.
A planted repeat files a sanctioned work again 6-18 months later at the same building.

  honest asked   honest works the agent asks about (SANCTIONED_WORK_AT_THIS_SITE): false alarms
  repeats asked  planted repeats it asks about

Each scenario is run under the one-site rule as it was (T137) and each change tried (RULES), and
the planted repeats once more with the pin moved to the next building (an agency dodging the rule).

Writes results/real_geo_check.txt and .json: counts and shares only, never a description or name.

Run:  apps\engine\.venv\Scripts\python.exe data\trial\real_geo_check.py --fetch   (once, ~400 MB)
      apps\engine\.venv\Scripts\python.exe data\trial\real_geo_check.py
Needs `pip install indiapins s2sphere` (this script only).
"""

from __future__ import annotations

import argparse
import bz2
import copy
import gzip
import json
import math
import os
import random
import re
import sys
import urllib.request
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "apps" / "engine"))
sys.path.insert(0, str(ROOT / "data"))

from drishti.agents.dup_split import agent as dup
from drishti.agents.dup_split import repeat
from esakshi_dashboard import load

DISTRICT = "Jaunpur"
BOX = (25.30, 26.25, 82.00, 83.20)                 # lat min, lat max, lon min, lon max
CELLS = ("3991", "398f")                           # Open Buildings S2 level-6 cells over it
OB_URL = ("https://storage.googleapis.com/open-buildings-data/v3/"
          "points_s2_level_6_gzip_no_header/{}_buildings.csv.gz")
OB_DIR = ROOT / "data" / "raw" / "open_buildings"
OB_FILE = OB_DIR / "jaunpur_cores.csv"
CORE_M = 600.0                                     # a village core around its post office
MIN_CONF = 0.70
OUT = ROOT / "data" / "trial" / "results" / "real_geo_check"
AS_OF = date(2026, 10, 2)


# ---------------------------------------------------------------- real data

def post_offices() -> list[tuple[float, float]]:
    """Jaunpur's post offices with a map position inside the district's box."""
    import indiapins
    path = os.path.join(os.path.dirname(indiapins.__file__), "pins.json.bz2")
    out = set()
    for line in bz2.open(path).read().decode().splitlines():
        r = json.loads(line)
        lat, lon = r.get("Latitude"), r.get("Longitude")
        if (r.get("District") == DISTRICT.upper() and isinstance(lat, float)
                and isinstance(lon, float) and BOX[0] <= lat <= BOX[1] and BOX[2] <= lon <= BOX[3]):
            out.add((round(lat, 6), round(lon, 6)))
    return sorted(out)


def _xy(lat, lon, lat0: float = 25.75, lon0: float = 82.6):
    return np.c_[(np.asarray(lon) - lon0) * 111_320 * math.cos(math.radians(lat0)),
                 (np.asarray(lat) - lat0) * 110_574]


def _latlon(x: float, y: float, lat0: float = 25.75, lon0: float = 82.6) -> tuple[float, float]:
    return lat0 + y / 110_574, lon0 + x / (111_320 * math.cos(math.radians(lat0)))


def fetch(pos: list[tuple[float, float]]) -> None:
    """Stream the two Open Buildings cells and keep the buildings in the village cores."""
    centres = cKDTree(_xy([p[0] for p in pos], [p[1] for p in pos]))
    OB_DIR.mkdir(parents=True, exist_ok=True)
    kept = 0
    with OB_FILE.open("w", encoding="utf-8") as out:
        out.write("lat,lon,area,conf\n")
        for cell in CELLS:
            with urllib.request.urlopen(OB_URL.format(cell)) as resp, \
                    gzip.GzipFile(fileobj=resp) as gz:
                batch = []
                for raw in gz:
                    f = raw.split(b",")
                    lat, lon, conf = float(f[0]), float(f[1]), float(f[3])
                    if conf >= MIN_CONF and BOX[0] <= lat <= BOX[1] and BOX[2] <= lon <= BOX[3]:
                        batch.append((lat, lon, float(f[2]), conf))
                    if len(batch) >= 200_000:
                        kept += _keep(batch, centres, out)
                        batch = []
                kept += _keep(batch, centres, out)
            print(f"  cell {cell}: {kept:,} buildings kept so far")


def _keep(batch, centres, out) -> int:
    if not batch:
        return 0
    a = np.array(batch)
    d, _ = centres.query(_xy(a[:, 0], a[:, 1]))
    n = 0
    for (lat, lon, area, conf), dist in zip(batch, d, strict=True):
        if dist <= CORE_M:
            out.write(f"{lat:.7f},{lon:.7f},{area:.1f},{conf:.3f}\n")
            n += 1
    return n


def buildings() -> np.ndarray:
    """[[lat, lon, area], ...] of the village cores' buildings."""
    if not OB_FILE.exists():
        sys.exit(f"{OB_FILE} not found: run with --fetch once")
    return np.loadtxt(OB_FILE, delimiter=",", skiprows=1, usecols=(0, 1, 2))


# ---------------------------------------------------------------- simulated pins

class Places:
    """Real houses and large buildings by village core, drawn without replacement."""

    def __init__(self, b: np.ndarray, pos: list[tuple[float, float]], rnd: random.Random):
        self.rnd = rnd
        xy = _xy(b[:, 0], b[:, 1])
        self.xy, self.area = xy, b[:, 2]
        self.tree = cKDTree(xy)
        centres = _xy([p[0] for p in pos], [p[1] for p in pos])
        self.cores = []
        for c in centres:
            idx = np.array(self.tree.query_ball_point(c, r=CORE_M * 0.85), dtype=int)
            houses = idx[(self.area[idx] >= 20) & (self.area[idx] <= 250)]
            big = idx[self.area[idx] >= 150]
            if len(houses) >= 60 and len(big) >= 6:
                self.cores.append({"houses": list(houses), "big": list(big)})
        self.used: set[int] = set()

    def village(self) -> dict:
        return self.rnd.choice(self.cores)

    def houses(self, core: dict, k: int, hamlet: bool) -> list[int]:
        free = [i for i in core["houses"] if i not in self.used]
        if len(free) < k:
            return []
        if hamlet:                          # the nearest free houses to one house
            seed = self.rnd.choice(free)
            d = np.hypot(*(self.xy[free] - self.xy[seed]).T)
            pick = [free[i] for i in np.argsort(d)[:k]]
        else:
            pick = self.rnd.sample(free, k)
        self.used.update(pick)
        return pick

    def big(self, core: dict) -> int | None:
        free = [i for i in core["big"] if i not in self.used]
        if not free:
            return None
        i = self.rnd.choice(free)
        self.used.add(i)
        return i

    def pin(self, i: int) -> dict:
        """The building's centre with a phone's GPS error."""
        s = 15.0 if self.rnd.random() < 0.10 else 5.0
        x, y = self.xy[i]
        lat, lon = _latlon(x + self.rnd.gauss(0, s), y + self.rnd.gauss(0, s))
        return {"lat": round(lat, 7), "lon": round(lon, 7)}


LIGHTS_N = re.compile(r"\b0?(\d)\s*(?:nag|nah|nos?|no\.)\b", re.IGNORECASE)


def _lights(desc: str) -> int:
    m = LIGHTS_N.search(desc or "")
    return max(1, min(5, int(m.group(1)))) if m else 1


def _form(work_type: str, sites: list[dict], size: dict) -> dict:
    return {"work": {"work_type": work_type, "nature": "new"},
            "sites": [{"location": s, "size": size} for s in sites]}


def honest_lights(works: list[dict], places: Places, per_village: int, hamlet: bool) -> list[dict]:
    """Each real light work at its own real house(s), a programme's works per_village a village."""
    by_prog: dict[tuple, list[dict]] = defaultdict(list)
    for w in works:
        by_prog[(w["mp_name"], w.get("recommended_date") or w.get("completed_date"))].append(w)
    out = []
    for prog in sorted(by_prog, key=str):
        ws = by_prog[prog]
        for k in range(0, len(ws), per_village):
            chunk, core = ws[k:k + per_village], places.village()
            need = sum(_lights(w["description"]) for w in chunk)
            hs = places.houses(core, need, hamlet)
            if not hs:
                continue
            for w in chunk:
                n = _lights(w["description"])
                mine, hs = hs[:n], hs[n:]
                w = copy.deepcopy(w)
                w["cost_form"] = _form("STREET_LIGHT", [places.pin(i) for i in mine],
                                       {"lights_nos": 1})
                w["_houses"] = mine
                out.append(w)
    return out


def honest_buildings(places: Places, n_villages: int, per_village: int, start: int) -> list[dict]:
    """Building works (hall, school, health, library) at distinct real large buildings."""
    types = ("COMMUNITY_HALL", "SCHOOL_BUILDING", "HEALTH_BUILDING", "LIBRARY")
    out, rnd = [], places.rnd
    for v in range(n_villages):
        core = places.village()
        for k in range(per_village):
            i = places.big(core)
            if i is None:
                break
            d = date(2023, 4, 1) + timedelta(days=rnd.randrange(0, 900))
            wt = rnd.choice(types)
            out.append({
                "work_id": f"SIM/B/{start + len(out):05d}", "district_lgd": "UTTAR PRADESH|JAUNPUR",
                "district_name": DISTRICT, "state_name": "Uttar Pradesh", "mp_name": "SIM",
                "work_type_code": wt, "description": f"Construction of building {v}-{k}",
                "amount": float(rnd.randrange(5, 25)) * 1e5, "recommended_date": d,
                "sanction_date": d + timedelta(days=40), "status": "SANCTIONED",
                "cost_form": _form(wt, [places.pin(i)],
                                   {"floor_area_m2": float(rnd.randrange(80, 300))}),
                "_houses": [i]})
    return out


def honest_purchases(places: Places, n_places: int, start: int) -> list[dict]:
    """Two purchases of different kinds for one institution (a real large building), months
    apart: computers, then furniture; all pinned at the institution."""
    types = ("COMPUTER", "FURNITURE", "SPORTS_EQUIPMENT", "MEDICAL_EQUIPMENT")
    out, rnd = [], places.rnd
    for v in range(n_places):
        i = places.big(places.village())
        if i is None:
            continue
        d = date(2023, 4, 1) + timedelta(days=rnd.randrange(0, 600))
        for wt in rnd.sample(types, 2):
            out.append({
                "work_id": f"SIM/G/{start + len(out):05d}", "district_lgd": "UTTAR PRADESH|JAUNPUR",
                "district_name": DISTRICT, "state_name": "Uttar Pradesh", "mp_name": "SIM",
                "work_type_code": wt, "description": f"Supply of {wt.lower()} to institution {v}",
                "amount": float(rnd.randrange(2, 9)) * 1e5, "recommended_date": d,
                "sanction_date": d + timedelta(days=30), "status": "SANCTIONED",
                "cost_form": _form(wt, [places.pin(i)], {}), "_houses": [i]})
            d += timedelta(days=rnd.randrange(60, 400))
    return out


def moved(planted: list[dict], places: Places) -> list[dict]:
    """The same repeats with the pin moved to the nearest other building (an evasion)."""
    out = []
    for w in planted:
        r = copy.deepcopy(w)
        sites = []
        for i, s in zip(w["_houses"], w["cost_form"]["sites"], strict=True):
            _d, j = places.tree.query(places.xy[i], k=2)
            sites.append({"location": places.pin(int(j[1])), "size": s.get("size", {})})
        r["cost_form"]["sites"] = sites
        r["work_id"] = r["work_id"].replace("SIM/R/", "SIM/M/")
        out.append(r)
    return out


def repeats(honest: list[dict], places: Places, n: int) -> list[dict]:
    """n sanctioned works filed again 6-18 months later at the same building(s)."""
    rnd = places.rnd
    pool = [w for w in honest if (w.get("sanction_date") or w.get("completed_date")
                                  or w.get("status") in ("SANCTIONED", "COMPLETED"))]
    out = []
    for w in rnd.sample(pool, min(n, len(pool))):
        first = w.get("recommended_date") or w.get("sanction_date") or w.get("completed_date")
        d = first + timedelta(days=rnd.randrange(180, 540))
        r = copy.deepcopy(w)
        r.update(work_id=f"SIM/R/{len(out):05d}-{w['work_id'][-6:]}", recommended_date=d,
                 sanction_date=None, completed_date=None, status="RECOMMENDED",
                 description=w["description"] + " (filed again)")
        r["cost_form"]["sites"] = [{"location": places.pin(i), "size": s.get("size", {})}
                                   for i, s in zip(w["_houses"], w["cost_form"]["sites"],
                                                   strict=True)]
        out.append(r)
    return out


# ---------------------------------------------------------------- the agent

def asked(result) -> bool:
    return any(f.code == "SANCTIONED_WORK_AT_THIS_SITE" for f in result.findings)


# the one-site rule as it was (T137) and the changes tried on real geography, one at a time
RULES = {
    "T137: 50 m, same family": {"POINT_FAMILIES": (), "BY_TYPE": (), "SAME_DAY_APART": ()},
    "+ lights: same day apart": {"POINT_FAMILIES": (), "BY_TYPE": (),
                                 "SAME_DAY_APART": ("lights",)},
    "+ purchases by type": {"POINT_FAMILIES": (), "BY_TYPE": ("goods",),
                            "SAME_DAY_APART": ("lights",)},
    **{f"+ lights one spot, {m} m": {"POINT_FAMILIES": ("lights",), "POINT_METRES": float(m),
                                      "BY_TYPE": ("goods",), "SAME_DAY_APART": ("lights",)}
       for m in (5, 10, 15, 20)},
}
ENGINE = {k: getattr(repeat, k) for k in ("POINT_FAMILIES", "POINT_METRES", "BY_TYPE",
                                          "SAME_DAY_APART")}


def run(rest: list[dict], honest: list[dict], planted: list[dict], evasive: list[dict]) -> dict:
    """The real Duplicate agent, under each rule, on every honest, planted and evasive work."""
    out = {}
    for name, knobs in {**RULES, "engine now": ENGINE}.items():
        for k, v in {**ENGINE, **knobs}.items():
            setattr(repeat, k, v)
        res = {}
        for label, extra in (("honest", []), ("repeats", planted), ("moved", evasive)):
            index = repeat.RepeatIndex.build(rest + honest + extra)
            ws = honest if label == "honest" else extra
            rs = [dup.assess(w, index) for w in ws]
            res[label] = len(rs)
            res[f"{label}_asked"] = sum(map(asked, rs))
            res[f"{label}_errors"] = sum(1 for r in rs if r.status.value == "ERROR")
            if label == "honest":
                res["honest_notes"] = sum(1 for r in rs if any(
                    f.code == "NEAR_SANCTIONED_WORK" for f in r.findings))
        out[name] = res
    for k, v in ENGINE.items():
        setattr(repeat, k, v)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fetch", action="store_true")
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()
    pos = post_offices()
    print(f"{len(pos)} post offices of {DISTRICT} with a position in the district")
    if args.fetch:
        fetch(pos)
    b = buildings()
    works, _ = load()
    jaunpur = [w for w in works if w.get("district_name") == DISTRICT]
    lights = [w for w in jaunpur if w.get("work_type_code") == "STREET_LIGHT"]
    others = [w for w in jaunpur if w.get("work_type_code") != "STREET_LIGHT"]
    report = {"post_offices": len(pos), "buildings": len(b), "works": len(jaunpur),
              "light_works": len(lights), "geometry": geometry(b, pos), "scenarios": []}

    for label, kind, per, hamlet in (
            ("lights, 5 a village, one hamlet", "lights", 5, True),
            ("lights, 10 a village, one hamlet", "lights", 10, True),
            ("lights, 10 a village, anywhere in the core", "lights", 10, False),
            ("lights, 25 a village, anywhere in the core", "lights", 25, False),
            ("buildings, 2 a village", "buildings", 2, False),
            ("buildings, 4 a village", "buildings", 4, False),
            ("purchases, 2 kinds an institution", "purchases", 2, False)):
        places = Places(b, pos, random.Random(args.seed))
        if kind == "lights":
            honest, rest = honest_lights(lights, places, per, hamlet), others
        elif kind == "buildings":
            honest, rest = honest_buildings(places, 120, per, 0), jaunpur
        else:
            honest, rest = honest_purchases(places, 200, 0), jaunpur
        planted = repeats(honest, places, 100)
        evasive = moved(planted, places)
        rules = run(rest, honest, planted, evasive)
        report["scenarios"].append({"label": label, "villages": len(places.cores), "rules": rules})
        print(label)
        for name, r in rules.items():
            share = r["honest_asked"] / max(1, r["honest"])
            print(f"   {name:<28} honest asked {r['honest_asked']:>4}/{r['honest']:<5} "
                  f"({share:5.1%})  repeats {r['repeats_asked']:>3}/{r['repeats']}  pin moved "
                  f"next door {r['moved_asked']:>3}/{r['moved']}  notes {r['honest_notes']}")
    write(report)


def geometry(b: np.ndarray, pos) -> dict:
    """How close real buildings stand in the village cores."""
    xy, area = _xy(b[:, 0], b[:, 1]), b[:, 2]
    out = {}
    for name, sel in (("houses_20_250m2", (area >= 20) & (area <= 250)),
                      ("large_150m2", area >= 150)):
        pts = xy[sel]
        t = cKDTree(pts)
        d, _ = t.query(pts, k=2)
        nn = d[:, 1]
        within = np.array([len(x) - 1 for x in t.query_ball_point(pts, r=repeat.PIN_METRES)])
        out[name] = {"n": len(pts), "nearest_median_m": round(float(np.median(nn)), 1),
                     "share_nearest_within_15m": round(float((nn <= 15).mean()), 3),
                     "share_nearest_within_50m": round(float((nn <= 50).mean()), 3),
                     "same_kind_within_50m_median": float(np.median(within))}
    return out


def write(report: dict) -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.with_suffix(".json").write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    lines = ["The Duplicate Work agent on real geography: Jaunpur (T139)", "",
             f"Real works {report['works']:,} ({report['light_works']:,} solar street lights); "
             f"{report['post_offices']} post offices; {report['buildings']:,} Open Buildings "
             "in the village cores", "", "How close real buildings stand:"]
    for k, g in report["geometry"].items():
        lines.append(f"  {k:<16} {g['n']:>7,}  nearest {g['nearest_median_m']} m (median); "
                     f"nearest within 15 m {g['share_nearest_within_15m']:.0%}, within 50 m "
                     f"{g['share_nearest_within_50m']:.0%}; same kind within 50 m: "
                     f"{g['same_kind_within_50m_median']:.0f} (median)")
    lines += ["", "Each scenario: honest filings at real buildings; 100 planted repeats (the same",
              "building 6-18 months later); the same repeats with the pin moved to the next "
              "building.", ""]
    for sc in report["scenarios"]:
        lines.append(sc["label"])
        for name, r in sc["rules"].items():
            lines.append(f"   {name:<28} honest asked {r['honest_asked']:>4}/{r['honest']:<5} "
                         f"{r['honest_asked'] / max(1, r['honest']):6.1%}   repeats asked "
                         f"{r['repeats_asked']:>3}/{r['repeats']:<3}  pin moved next door "
                         f"{r['moved_asked']:>3}/{r['moved']:<3}  notes {r['honest_notes']:>4}"
                         f"  errors {r['honest_errors'] + r['repeats_errors'] + r['moved_errors']}")
        lines.append("")
    OUT.with_suffix(".txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
