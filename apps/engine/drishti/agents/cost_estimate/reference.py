"""What the same kind of work costs, per unit of its size, in a state and its districts (T097).

Reference A (the prototype): real works of one state. A work enters a group only when its record
states the size of one job (the Cost engine's own readers: a count of lights, one high mast, a
length); several sites, bundles and empty descriptions stay out. Each group keeps the 10th, 50th,
90th and 98th percentiles of price per unit, for the state and for every district with enough
works.

A group is USED only when its own spread shows it captures the size. If the middle 80% of its works
already runs past +25% of the median, the records are missing something that sets the price (a
road's width, a mast's height, a light's wattage), so comparing with it would mistake size for
price. Measured on Uttar Pradesh (T095): solar street lights are one standard item (p90 = median);
CC roads per metre spread to +58.5% because eSAKSHI records no width, so roads stay unchecked
until the Schedule of Rates (T096) or completed forms supply the size.

Built by data/build_cost_reference.py into reference/cost/<state>.json; nothing here is guessed.
"""

from __future__ import annotations

import json
import math
import re
from collections import defaultdict
from datetime import date
from functools import cache
from pathlib import Path

DIR = Path(__file__).resolve().parents[2] / "reference" / "cost"
MIN_WORKS = 30          # fewer works in a group: no comparison ("could not check")
TIGHT = 1.25            # p90 within +25% of the median: the group captures the size
SOLAR = re.compile(r"solar|सोलर|सौर", re.I)

# eSAKSHI work type -> how its size is read from the record, and the form field it matches
PER_METRE = {"ROAD_CC", "ROAD_BT", "FOOTPATH", "DRAIN", "BOUNDARY_WALL", "EMBANKMENT",
             "WATER_SUPPLY", "ELECTRICITY"}
PER_UNIT = {"BOREWELL": "wells_nos", "WATER_TANK": "tanks_nos", "BUS_SHELTER": None,
            "TOILET_BLOCK": None, "CULVERT": None, "CCTV": None}
UNIT_TEXT = {"per light": "light", "per mast": "high mast", "per metre": "metre",
             "per unit": "unit"}


def slug(state: str | None) -> str:
    return re.sub(r"[^a-z0-9]+", "_", (state or "").lower()).strip("_")


def _q(xs: list[float], p: float) -> float:
    s = sorted(xs)
    k = (len(s) - 1) * p
    lo, hi = math.floor(k), math.ceil(k)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


def stats(prices: list[float]) -> dict:
    med = _q(prices, 0.5)
    return {"n": len(prices), "p10": round(_q(prices, 0.10)), "median": round(med),
            "p90": round(_q(prices, 0.90)), "p98": round(_q(prices, 0.98)),
            "tight": bool(med > 0 and _q(prices, 0.90) <= TIGHT * med)}


def record_price(w: dict) -> tuple[str, str, float] | None:
    """(group key, unit, price per unit) for one real work whose record states its size."""
    from drishti.agents.statistical import scope as reader
    from drishti.agents.statistical.text import stated_length

    typ, text = w.get("work_type_code"), w.get("description") or ""
    amount = w.get("amount")
    if not isinstance(amount, (int, float)) or isinstance(amount, bool) or amount <= 0:
        return None
    r = reader.read(typ, text)
    if r.undescribed or r.many_sites:
        return None
    if typ in ("STREET_LIGHT", "HIGH_MAST") and (typ == "HIGH_MAST" or r.scope == reader.MAST):
        n = reader.mast_count(text) or (1 if reader.single_unit("STREET_LIGHT", text) else None)
        return ("HIGH_MAST", "per mast", amount / n) if n else None
    if typ == "STREET_LIGHT":
        n = r.count or (1 if reader.single_unit(typ, text) else None)
        if not n:
            return None
        # a light whose record says solar; without the word its power source is unknown
        key = "STREET_LIGHT|solar" if SOLAR.search(text) else "STREET_LIGHT|unstated"
        return key, "per light", amount / n
    if typ in PER_METRE:
        m = stated_length(text)
        return (typ, "per metre", amount / m) if not r.bundle and m == m and m > 0 else None
    if typ in PER_UNIT:
        n = r.count or (1 if reader.single_unit(typ, text) else None)
        return (typ, "per unit", amount / n) if n else None
    return None


def build(works: list[dict], state: str, source: str) -> dict:
    """The reference for one state from its real works (see the module note)."""
    groups: dict[str, dict] = {}
    prices: dict[str, list[float]] = defaultdict(list)
    by_district: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    years = []
    for w in works:
        if w.get("state_name") != state:
            continue
        got = record_price(w)
        if not got:
            continue
        key, unit, price = got
        groups.setdefault(key, {"unit": unit})
        prices[key].append(price)
        by_district[key][w.get("district_name") or "?"].append(price)
        d = w.get("recommended_date") or w.get("completed_date")
        if isinstance(d, date):
            years.append(d.year)
    for key, g in groups.items():
        g["state"] = stats(prices[key])
        g["districts"] = {d: stats(v) for d, v in sorted(by_district[key].items())
                          if len(v) >= MIN_WORKS}
    return {"state": state, "source": source, "built": date.today().isoformat(),
            "years": [min(years), max(years)] if years else None, "min_works": MIN_WORKS,
            "tight": TIGHT, "groups": dict(sorted(groups.items()))}


@cache
def load(state: str | None) -> dict | None:
    path = DIR / f"{slug(state)}.json"
    if not state or not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def form_key(work_type: str | None, size: dict) -> tuple[str, str | None] | None:
    """(group key, the form's size field that counts its units) for one site of a form."""
    if work_type == "STREET_LIGHT":
        power = size.get("light_power")
        key = {"solar_standalone": "STREET_LIGHT|solar", "grid": "STREET_LIGHT|grid"}.get(power)
        return (key, "lights_nos") if key else None
    if work_type == "HIGH_MAST":
        return "HIGH_MAST", "masts_nos"
    if work_type in PER_METRE:
        return work_type, "length_m"
    if work_type in PER_UNIT:
        return work_type, PER_UNIT[work_type]
    return None


def group(ref: dict | None, key: str | None, district: str | None) -> tuple[dict | None, str, str]:
    """(stats to compare with or None, where they are from, why not when None)."""
    if not ref:
        return None, "", "there is no price reference for this state yet"
    g = (ref.get("groups") or {}).get(key or "")
    if not g:
        return None, "", "no real works of this kind and specification to compare with"
    st, where = None, ref["state"]
    if district and district in (g.get("districts") or {}):
        st, where = g["districts"][district], district
    elif (g.get("state") or {}).get("n", 0) >= ref.get("min_works", MIN_WORKS):
        st = g["state"]
    if not st:
        return None, "", (f"only {(g.get('state') or {}).get('n', 0)} real works of this kind "
                          f"to compare with (at least {ref.get('min_works', MIN_WORKS)} needed)")
    if not st.get("tight"):
        return None, "", (f"the real works of this kind in {where} vary too much in price per "
                          f"{UNIT_TEXT.get(g['unit'], 'unit')} (the middle 80% runs to "
                          f"+{100 * (st['p90'] / st['median'] - 1):.0f}%): their records miss "
                          "something that sets the price, such as width, height or wattage")
    return {**st, "unit": g["unit"]}, where, ""
