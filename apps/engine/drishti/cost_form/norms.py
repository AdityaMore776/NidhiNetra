"""How much of a material a work of a given size needs (Cost v3, T097).

Only checks that follow from the size itself, with nothing estimated:
  counts       a solar street light needs one light fitting, one battery and one panel each, and
               one pole unless it goes on an existing pole; a high mast needs its stated lamps
  area         paver blocks cover the path: length x width, plus 5% for cutting
  concrete     cement for a CC road of a nominal-mix grade (M10 / M15 / M20): length x width x
               thickness x bags per m3 of that mix, plus 5%; only when nothing else on the road
               uses cement (no PCC base, side drain, kerb or cross drain), so the whole cement
               line is the slab's; and its sand by the same mix (T136), only when the base takes
               none (no base, WBM or WMM); and its stone aggregate by the same mix (T144), with
               15% for the analysis-of-rates figures honest estimates use (0.85-0.90 m3 per m3
               of M20) and wastage. Under a stone base (WBM, WMM, GSB) whose stone is not on a
               base line of its own, only aggregate written for the slab is counted (a concrete
               size of 6-20 mm, or "concrete", "PCC", "slab")
  pipe         a water pipeline's main: its length, plus 10% (T144), when the house
               connections' pipes are on lines of their own (32 mm or less, or named for house
               connections); those are the agency's call. With every pipe on one line, its
               length plus 20 m a house connection, plus 10%. A water tank's connecting pipe as
               the form gives it, plus 10%
  capacity     solar street lights bought by the watt or watt-hour: panels at the size's Wp for
               each light, batteries at its Wh for each light, plus 5% for rounding (T144); a line
               in numbers is held to the count above, a line in Wp or Wh to the capacity

The form (validate.py) asks the agency to confirm a quantity above what the size needs (a typo
is corrected there); the Cost agent asks the officer about one well above it (agent.py).

Bags per m3 come from the nominal mix proportions of IS 456:2000 (Table 9: M10 1:3:6, M15 1:2:4,
M20 1:1.5:3) with the standard 1.54 dry-volume factor and loose cement at 1,440 kg/m3: M20 gives
1.54 x 1/5.5 x 1440 / 50 = 8.06 bags. Design mixes (M25 and above) have no fixed proportion and
are not checked. T096 adds the CPWD analysis-of-rates norms for more items.
"""

from __future__ import annotations

import math
import re

from drishti.cost_form import catalog

NOMINAL_MIX = {"M10": (1, 3, 6), "M15": (1, 2, 4), "M20": (1, 1.5, 3)}
DRY_VOLUME = 1.54
CEMENT_KG_PER_M3 = 1440
BAG_KG = 50
WASTAGE = 1.05
SAND_BULKING = 1.20     # moist sand measured by volume bulks 20-30% (IS 2386-3); honest
                        # estimates carry 0.44-0.47 m3 of sand per m3 of M20 for it
AGGREGATE_ROOM = 1.15   # the analysis-of-rates figures (0.85-0.90 m3 of stone per m3 of M20,
                        # against the mix's 0.84 dry) and wastage
PIPE_ROOM = 1.10        # pipe laid with slack, bends and cut lengths
CONNECTION_PIPE_M = 20  # a house connection's pipe from the main (honest: 6-15 m)
CONNECTION_MIN_M = 6    # the shortest honest house connection: the low end of the range
STONE_BASES = ("wbm", "wmm", "gsb", "other")   # bases that are themselves stone
SERVICE_MM = 32          # a pipe this narrow or narrower is a house connection's, not the main
_MM = re.compile(r"(?<![\d.])(\d{2,3})\s*mm\b", re.I)
_SERVICE = re.compile(r"\b(?:house|household|service|fhtc|tap)\s*(?:connections?|lines?|pipes?)?"
                      r"\b|\bconnections?\b", re.I)
# aggregate written for concrete: a concrete size (6-20 mm) or a concrete word
_SLAB = re.compile(r"(?<![\d.])(?:6|10|12(?:\.5)?|16|20)\s*mm\b|\b(?:concrete|cc|pcc|rcc|slab|"
                   r"m\s?10|m\s?15|m\s?20|pavement)\b"
                   # a bare size ending the line ("Kapchi 20", "Stone aggregate 20") is its mm
                   r"|(?<![\d.])(?:6|10|12(?:\.5)?|16|20)\s*$", re.I)


def cement_bags_per_m3(grade: str) -> float | None:
    mix = NOMINAL_MIX.get(grade)
    if not mix:
        return None
    return DRY_VOLUME * mix[0] / sum(mix) * CEMENT_KG_PER_M3 / BAG_KG


def _num(v) -> float | None:
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return None
    return float(v) if math.isfinite(v) else None


def to_first_unit(material_id: str, quantity, unit, target: str | None = None) -> float | None:
    """A quantity restated in the material's first unit (e.g. 2,500 kg of cement -> 50 bags), or
    in `target` (one of its units: 1.2 kWh of battery -> 1,200 Wh)."""
    mat, table, q = catalog.material(material_id), catalog.units(), _num(quantity)
    to = target or (mat["units"][0] if mat else None)
    if not mat or q is None or not isinstance(unit, str) or unit not in table or to not in table:
        return None
    (dim_u, f_u), (dim_f, f_f) = table[unit], table[to]
    return q * f_u / f_f if dim_u == dim_f and f_f > 0 else None


def needs(work_type: str | None, size: dict) -> list[dict]:
    """What the size needs: [{material, low, needed (in its first unit, or `unit`), why}]. T145
    (the owner: "it should give a range"): `low` is the standard amount for the size, `needed`
    the same with the room honest estimates carry (wastage, bulking, the analysis of rates); an
    honest estimate falls between them. A count has no room: low = needed."""
    size = size if isinstance(size, dict) else {}
    g = {k: _num(v) for k, v in size.items()}
    out = []
    if work_type == "STREET_LIGHT" and g.get("lights_nos"):
        n = g["lights_nos"]
        out.append({"material": "led_luminaire", "needed": n, "why": f"{n:g} lights"})
        if size.get("pole_material") == "existing_pole":
            out.append({"material": "pole", "needed": 0.0,
                        "why": "the lights go on existing poles"})
        else:
            out.append({"material": "pole", "needed": n, "why": f"{n:g} lights"})
        if size.get("light_power") == "solar_standalone":
            out.append({"material": "battery", "needed": n, "why": f"{n:g} solar lights"})
            out.append({"material": "solar_panel", "needed": n, "why": f"{n:g} solar lights"})
            # bought by capacity (T144): what each light carries, times the lights
            if g.get("panel_wp"):
                out.append({"material": "solar_panel", "unit": "wp",
                            "low": n * g["panel_wp"], "needed": n * g["panel_wp"] * WASTAGE,
                            "why": f"{n:g} lights x {g['panel_wp']:g} Wp, plus 5%"})
            if g.get("battery_wh"):
                out.append({"material": "battery", "unit": "wh",
                            "low": n * g["battery_wh"], "needed": n * g["battery_wh"] * WASTAGE,
                            "why": f"{n:g} lights x {g['battery_wh']:g} Wh, plus 5%"})
    elif work_type == "HIGH_MAST" and g.get("masts_nos") and g.get("lamps_per_mast"):
        n = g["masts_nos"] * g["lamps_per_mast"]
        out.append({"material": "led_luminaire", "needed": n,
                    "why": f"{g['masts_nos']:g} masts x {g['lamps_per_mast']:g} lamps"})
    elif work_type == "FOOTPATH" and g.get("length_m") and g.get("width_m"):
        area = g["length_m"] * g["width_m"]
        out.append({"material": "paver_block", "low": area, "needed": area * WASTAGE,
                    "why": f"{g['length_m']:g} m x {g['width_m']:g} m = {area:,.0f} m2, plus 5%"})
    elif work_type == "ROAD_CC":
        bags = cement_bags_per_m3(str(size.get("concrete_grade")))
        alone = (size.get("base_type") != "pcc" and not g.get("side_drain_m")
                 and not g.get("kerb_m") and not g.get("cross_drains_nos"))
        dims = (g.get("length_m"), g.get("width_m"), g.get("cc_thickness_mm"))
        if bags and alone and all(dims):
            vol = dims[0] * dims[1] * dims[2] / 1000
            out.append({"material": "cement", "low": vol * bags, "needed": vol * bags * WASTAGE,
                        "why": f"{vol:,.1f} m3 of {size['concrete_grade']} concrete "
                               f"({dims[0]:g} m x {dims[1]:g} m x {dims[2]:g} mm), "
                               f"{bags:.2f} bags per m3, plus 5%"})
            # sand from the same mix (T136: twice the sand went unasked); only under bases that
            # take none (GSB, brick soling and a sand bed do)
            sand = sand_m3_per_m3(str(size.get("concrete_grade")))
            if sand and size.get("base_type") in (None, "none", "wbm", "wmm"):
                out.append({"material": "sand", "low": vol * sand,
                            "needed": vol * sand * SAND_BULKING * WASTAGE,
                            "why": f"{vol:,.1f} m3 of {size['concrete_grade']} concrete, "
                                   f"{sand:.2f} m3 of dry sand per m3, plus 20% for moist "
                                   "sand's bulking and 5%"})
            # its stone by the same mix (T144); under a stone base, only the slab's lines
            stone = aggregate_m3_per_m3(str(size.get("concrete_grade")))
            if stone and size.get("base_type") in (None, "none", "brick_soling", "sand_bed",
                                                    *STONE_BASES):
                out.append({"material": "aggregate", "low": vol * stone,
                            "needed": vol * stone * AGGREGATE_ROOM,
                            "stone_base": size.get("base_type") in STONE_BASES,
                            "why": f"{vol:,.1f} m3 of {size['concrete_grade']} concrete, "
                                   f"{stone:.2f} m3 of dry stone per m3, plus 15%"})
    elif work_type == "WATER_SUPPLY" and g.get("length_m"):
        homes = g.get("house_connections_nos") or 0
        out.append({"material": "pipe", "low": g["length_m"] + homes * CONNECTION_MIN_M,
                    "needed": (g["length_m"] + homes * CONNECTION_PIPE_M) * PIPE_ROOM,
                    "why": f"{g['length_m']:,.0f} m of pipeline"
                           + (f" and {homes:g} house connections at {CONNECTION_PIPE_M} m"
                              if homes else "") + ", plus 10%",
                    # with the connections' pipes on lines of their own, the main alone
                    "main": {"low": g["length_m"], "needed": g["length_m"] * PIPE_ROOM,
                             "why": f"the pipeline's {g['length_m']:,.0f} m, plus 10%; the house "
                                    "connections' own pipes are not counted"}})
    elif work_type == "WATER_TANK" and g.get("connecting_pipe_m"):
        out.append({"material": "pipe", "low": g["connecting_pipe_m"],
                    "needed": g["connecting_pipe_m"] * PIPE_ROOM,
                    "why": f"{g['connecting_pipe_m']:,.0f} m of connecting pipe, plus 10%"})
    for n in out:
        n.setdefault("low", n["needed"])
    return out


def aggregate_m3_per_m3(grade: str) -> float | None:
    """Dry coarse aggregate per m3 of a nominal mix (IS 456 Table 9, the same 1.54 factor)."""
    mix = NOMINAL_MIX.get(grade)
    if not mix:
        return None
    return DRY_VOLUME * mix[2] / sum(mix)


def sand_m3_per_m3(grade: str) -> float | None:
    """Dry sand per m3 of a nominal mix (IS 456 Table 9, the same 1.54 factor as the cement)."""
    mix = NOMINAL_MIX.get(grade)
    if not mix:
        return None
    return DRY_VOLUME * mix[1] / sum(mix)


def for_slab(text) -> bool:
    """Aggregate written for the concrete (T144): a concrete size or a concrete word."""
    return bool(_SLAB.search(text)) if isinstance(text, str) else False


def for_service(text) -> bool:
    """A pipe line for house connections (T144): every diameter it states SERVICE_MM or less, or,
    with none stated, named for connections. A line stating a wider one is (or carries) the main,
    whatever its words."""
    if not isinstance(text, str):
        return False
    sizes = [int(m) for m in _MM.findall(text)]
    if sizes:
        return max(sizes) <= SERVICE_MM
    return bool(_SERVICE.search(text))


def for_base(text) -> bool:
    """Stone sized for a road's base course (T144): a stated size of 40 mm or more that is not
    written for concrete (WBM metal is 45-90 mm, WMM 53 mm and down)."""
    if not isinstance(text, str) or for_slab(text):
        return False
    return any(int(m) >= 40 for m in _MM.findall(text))


def stone_not_itemised(work_type: str | None, size: dict, lines: list[tuple]) -> int | None:
    """A CC road over a new stone base (WBM, WMM, GSB) whose base has no line of its own and
    whose stone is on a line sized for neither the slab nor the base: that line's index, else
    None (T144). The base's stone and the slab's cannot be told apart there, so neither can be
    checked."""
    size = size if isinstance(size, dict) else {}
    if work_type != "ROAD_CC" or size.get("base_type") not in ("wbm", "wmm", "gsb") \
            or not _num(size.get("base_thickness_mm")):
        return None
    if any(ln[1] == "granular_base" for ln in lines):
        return None
    text = (ln[4] if len(ln) > 4 else None for ln in lines)
    return next((ln[0] for ln, t in zip(lines, text, strict=True) if ln[1] == "aggregate"
                 and not for_slab(t) and not for_base(t)), None)


def held(need: dict, lines: list[tuple]) -> tuple[list, float, str, float]:
    """The lines a need holds and what it needs of them: (lines, needed, why, low). Lines are
    (index, material id, quantity, unit[, item text]). Shared by the quantity check and the whole
    estimate (agents/cost_estimate/whole.py), so the two never count different lines."""
    mat = need["material"]

    def text(ln: tuple):
        return ln[4] if len(ln) > 4 else None

    mine = [ln for ln in lines if ln[1] == mat]
    needed, why, low = need["needed"], need["why"], need.get("low", need["needed"])
    # under a stone base with no base line of its own, its stone may be on an aggregate line:
    # only the lines written for the slab are the slab's
    if need.get("stone_base") and not any(ln[1] == "granular_base" for ln in lines):
        mine = [ln for ln in mine if for_slab(text(ln))]
    # the house connections' pipes on lines of their own: the main alone, held to the length
    if need.get("main") and any(for_service(text(ln)) for ln in mine):
        mine = [ln for ln in mine if not for_service(text(ln))]
        needed, why, low = need["main"]["needed"], need["main"]["why"], need["main"]["low"]
    return mine, needed, why, low


def check(work_type: str | None, size: dict, lines: list[tuple]) -> list[dict]:
    """Each needed material against the lines: lines are (index, material id, quantity, unit) or
    (index, material id, quantity, unit, item text). Returns [{material, needed, quantity, ratio,
    lines, why, unit}] for materials the lines give in a unit that converts; a material with no
    line is not reported."""
    out = []
    for need in needs(work_type, size):
        mat = need["material"]
        unit_to = need.get("unit") or catalog.material(mat)["units"][0]
        mine, needed, why, low = held(need, lines)
        idx, total = [], 0.0
        for ln in mine:
            x = to_first_unit(mat, ln[2], ln[3], unit_to)
            if x is None:
                continue
            idx.append(ln[0])
            total += x
        if not idx:
            continue
        ratio = total / needed if needed > 0 else (math.inf if total > 0 else 1.0)
        out.append({"material": mat, "low": round(low, 2), "needed": round(needed, 2),
                    "quantity": round(total, 2), "ratio": ratio, "lines": idx, "why": why,
                    "unit": unit_to})
    return out
