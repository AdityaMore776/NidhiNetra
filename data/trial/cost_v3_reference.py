r"""Cost v3 prototype reference (T095): what works cost, and how long they take, in one state.

The new Cost agent (docs/plans/T097-cost-agent-v3.md) compares an implementing agency's cost estimate
with what works of the same kind and size cost in the same place. Until the state's Schedule of
Rates is in (T096), its only reference is real works. This script reads the eSAKSHI dashboard
tables (data/raw/esakshi_dashboard, 40,935 works, 2023-2026 prices) for ONE state and writes,
per work type:

  amounts      p10 / p25 / median / p75 / p90 of the whole amount (Rs)
  unit costs   Rs per metre (roads, paths, drains, walls) or Rs per unit (lights, masts, pumps,
               ...) for works whose description states the size, read by the Cost engine's own
               readers; works covering several sites, bundles or nothing describable are left out
  band         how far above and below the median the middle 80% of unit costs lie: the
               "normal percent above or below average" (T097)
  p98          the line only 2 in 100 real works lie above: where T097 starts asking
  by year      median unit cost per year, to see whether prices moved within the window
  by district  median unit cost per district (10+ works), to see how much place matters
  times        days from recommendation to sanction, sanction to completion and recommendation
               to completion

Only aggregates are written (no descriptions, no names, no work ids), so the output is safe to
commit. eSAKSHI states no width, thickness or specification, so these bands are wider than the
Schedule-of-Rates reference will be: that is the measured starting point, not the target.

Run:  apps\engine\.venv\Scripts\python.exe data\trial\cost_v3_reference.py [--state "Uttar Pradesh"]
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "data"))
sys.path.insert(0, str(ROOT / "apps" / "engine"))
from esakshi_dashboard import load  # noqa: E402

from drishti.agents.statistical import scope as reader  # noqa: E402
from drishti.agents.statistical.text import stated_length  # noqa: E402

OUT = ROOT / "data" / "trial" / "results"
# priced per metre when the description states a length
PER_METRE = {"ROAD_CC", "ROAD_BT", "FOOTPATH", "DRAIN", "BOUNDARY_WALL", "EMBANKMENT",
             "WATER_SUPPLY", "ELECTRICITY"}
# priced per unit when the description states a count (or exactly one unit)
PER_UNIT = {"STREET_LIGHT", "BOREWELL", "CCTV", "COMPUTER", "FURNITURE", "TOILET_BLOCK",
            "BUS_SHELTER", "WATER_TANK", "SPORTS_EQUIPMENT", "MEDICAL_EQUIPMENT", "AMBULANCE",
            "CULVERT"}
MIN_GROUP = 10          # a group with fewer works is reported as too small, never as a range


def _q(xs: list[float], p: float) -> float:
    s = sorted(xs)
    k = (len(s) - 1) * p
    lo, hi = math.floor(k), math.ceil(k)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


def _dist(xs: list[float]) -> dict | None:
    if len(xs) < MIN_GROUP:
        return {"n": len(xs), "too_few": True} if xs else None
    med = statistics.median(xs)
    out = {"n": len(xs), "p10": _q(xs, 0.10), "p25": _q(xs, 0.25), "median": med,
           "p75": _q(xs, 0.75), "p90": _q(xs, 0.90), "p95": _q(xs, 0.95), "p98": _q(xs, 0.98)}
    if med > 0:
        # the middle 80% as a percent above / below the median: the agent's allowed band
        out["band_pct"] = {"below": round(100 * (1 - out["p10"] / med), 1),
                           "above": round(100 * (out["p90"] / med - 1), 1)}
        # the line only 2 in 100 real works of this kind and place lie above (T097's threshold)
        out["p98_above_median_pct"] = round(100 * (out["p98"] / med - 1), 1)
    return {k: (round(v) if isinstance(v, float) and not k.endswith("_pct") else v)
            for k, v in out.items()}


def _year(w: dict) -> int | None:
    d = w.get("recommended_date") or w.get("completed_date")
    return d.year if d else None


def unit_cost(w: dict) -> tuple[str, float] | None:
    """(pricing unit, Rs per unit) when the description states the size of ONE job."""
    typ, text, amount = w.get("work_type_code"), w.get("description") or "", w.get("amount")
    if not amount or amount <= 0:
        return None
    r = reader.read(typ, text)
    if r.undescribed or r.many_sites:
        return None
    if typ == "STREET_LIGHT" and r.scope == reader.MAST:
        n = reader.mast_count(text) or (1 if reader.single_unit(typ, text) else None)
        return ("per high mast", amount / n) if n else None
    if typ in PER_METRE:
        if r.bundle:
            return None
        m = stated_length(text)
        return ("per metre", amount / m) if m == m and m > 0 else None
    if typ in PER_UNIT:
        n = r.count or (1 if reader.single_unit(typ, text) else None)
        return ("per unit", amount / n) if n else None
    return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", default="Uttar Pradesh")
    args = ap.parse_args()
    works, info = load()
    mine = [w for w in works if w.get("state_name") == args.state]
    if not mine:
        raise SystemExit(f"no works for state {args.state!r}")

    amounts = defaultdict(list)
    units = defaultdict(list)
    unit_name = {}
    by_year = defaultdict(lambda: defaultdict(list))
    by_district = defaultdict(lambda: defaultdict(list))
    times = defaultdict(lambda: defaultdict(list))
    for w in mine:
        typ = w.get("work_type_code") or "OTHER"
        key = typ
        uc = unit_cost(w)
        if uc and uc[0] == "per high mast":
            key = "STREET_LIGHT (high mast)"
        if w.get("amount"):
            amounts[key].append(float(w["amount"]))
        if uc:
            unit_name[key] = uc[0]
            units[key].append(uc[1])
            if _year(w):
                by_year[key][_year(w)].append(uc[1])
            by_district[key][w.get("district_name") or "?"].append(uc[1])
        rec, san, done = w.get("recommended_date"), w.get("sanction_date"), w.get("completed_date")
        if rec and san and san >= rec:
            times[key]["recommended_to_sanction"].append((san - rec).days)
        if san and done and done >= san:
            times[key]["sanction_to_completion"].append((done - san).days)
        if rec and done and done >= rec:
            times[key]["recommended_to_completion"].append((done - rec).days)

    out = {"state": args.state, "source": f"eSAKSHI dashboard tables, as of {info['as_of']}",
           "works": len(mine), "min_group": MIN_GROUP,
           "note": "aggregates only; eSAKSHI states no width, thickness or specification",
           "types": {}}
    for key in sorted(amounts, key=lambda k: -len(amounts[k])):
        t = {"works": len(amounts[key]), "amount": _dist(amounts[key])}
        if units.get(key):
            t["pricing_unit"] = unit_name[key]
            t["unit_cost"] = _dist(units[key])
            t["unit_cost_by_year"] = {str(y): _dist(v) for y, v in sorted(by_year[key].items())
                                      if len(v) >= MIN_GROUP}
            t["unit_cost_by_district"] = {d: _dist(v) for d, v in sorted(by_district[key].items())
                                          if len(v) >= MIN_GROUP}
        t["days"] = {k: _dist(v) for k, v in times[key].items() if v}
        out["types"][key] = t

    OUT.mkdir(parents=True, exist_ok=True)
    slug = args.state.lower().replace(" ", "_")
    path = OUT / f"cost_v3_reference_{slug}.json"
    path.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")

    print(f"{args.state}: {len(mine):,} works ({out['source']})\n")
    print(f"{'type':28} {'works':>6} {'sized':>6}  {'unit':13} {'median':>9}  band (below/above)"
          f"   rec->sanction  sanction->done (median days)")
    for key, t in out["types"].items():
        u = t.get("unit_cost") or {}
        band = u.get("band_pct")
        d = t["days"]
        rs = (d.get("recommended_to_sanction") or {}).get("median", "-")
        sd = (d.get("sanction_to_completion") or {}).get("median", "-")
        print(f"{key:28} {t['works']:6} {u.get('n', 0):6}  {t.get('pricing_unit', ''):13} "
              f"{u.get('median', '-') if not u.get('too_few') else '(few)':>9}  "
              f"{'-' if not band else f'-{band['below']}% / +{band['above']}%':18}   "
              f"{rs:>8}       {sd:>8}")
    print(f"\nwrote {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
