"""How much of a material a work of a given size needs (Cost v3, T097).

Only checks that follow from the size itself, with nothing estimated:
  counts       a solar street light needs one light fitting, one battery and one panel each, and
               one pole unless it goes on an existing pole; a high mast needs its stated lamps
  area         paver blocks cover the path: length x width, plus 5% for cutting
  concrete     cement for a CC road of a nominal-mix grade (M10 / M15 / M20): length x width x
               thickness x bags per m3 of that mix, plus 5%; only when nothing else on the road
               uses cement (no PCC base, side drain, kerb or cross drain), so the whole cement
               line is the slab's

The form (validate.py) asks the agency to confirm a quantity above what the size needs (a typo
is corrected there); the Cost agent asks the officer about one well above it (agent.py).

Bags per m3 come from the nominal mix proportions of IS 456:2000 (Table 9: M10 1:3:6, M15 1:2:4,
M20 1:1.5:3) with the standard 1.54 dry-volume factor and loose cement at 1,440 kg/m3: M20 gives
1.54 x 1/5.5 x 1440 / 50 = 8.06 bags. Design mixes (M25 and above) have no fixed proportion and
are not checked. T096 adds the CPWD analysis-of-rates norms for more items.
"""

from __future__ import annotations

import math

from drishti.cost_form import catalog

NOMINAL_MIX = {"M10": (1, 3, 6), "M15": (1, 2, 4), "M20": (1, 1.5, 3)}
DRY_VOLUME = 1.54
CEMENT_KG_PER_M3 = 1440
BAG_KG = 50
WASTAGE = 1.05


def cement_bags_per_m3(grade: str) -> float | None:
    mix = NOMINAL_MIX.get(grade)
    if not mix:
        return None
    return DRY_VOLUME * mix[0] / sum(mix) * CEMENT_KG_PER_M3 / BAG_KG


def _num(v) -> float | None:
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return None
    return float(v) if math.isfinite(v) else None


def to_first_unit(material_id: str, quantity, unit) -> float | None:
    """A quantity restated in the material's first unit (e.g. 2,500 kg of cement -> 50 bags)."""
    mat, table, q = catalog.material(material_id), catalog.units(), _num(quantity)
    if not mat or q is None or unit not in table or mat["units"][0] not in table:
        return None
    (dim_u, f_u), (dim_f, f_f) = table[unit], table[mat["units"][0]]
    return q * f_u / f_f if dim_u == dim_f and f_f > 0 else None


def needs(work_type: str | None, size: dict) -> list[dict]:
    """What the size needs: [{material, needed (in its first unit), why}]."""
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
    elif work_type == "HIGH_MAST" and g.get("masts_nos") and g.get("lamps_per_mast"):
        n = g["masts_nos"] * g["lamps_per_mast"]
        out.append({"material": "led_luminaire", "needed": n,
                    "why": f"{g['masts_nos']:g} masts x {g['lamps_per_mast']:g} lamps"})
    elif work_type == "FOOTPATH" and g.get("length_m") and g.get("width_m"):
        area = g["length_m"] * g["width_m"]
        out.append({"material": "paver_block", "needed": area * WASTAGE,
                    "why": f"{g['length_m']:g} m x {g['width_m']:g} m = {area:,.0f} m2, plus 5%"})
    elif work_type == "ROAD_CC":
        bags = cement_bags_per_m3(str(size.get("concrete_grade")))
        alone = (size.get("base_type") != "pcc" and not g.get("side_drain_m")
                 and not g.get("kerb_m") and not g.get("cross_drains_nos"))
        dims = (g.get("length_m"), g.get("width_m"), g.get("cc_thickness_mm"))
        if bags and alone and all(dims):
            vol = dims[0] * dims[1] * dims[2] / 1000
            out.append({"material": "cement", "needed": vol * bags * WASTAGE,
                        "why": f"{vol:,.1f} m3 of {size['concrete_grade']} concrete "
                               f"({dims[0]:g} m x {dims[1]:g} m x {dims[2]:g} mm), "
                               f"{bags:.2f} bags per m3, plus 5%"})
    return out


def check(work_type: str | None, size: dict, lines: list[tuple[int, str | None, object, object]]
          ) -> list[dict]:
    """Each needed material against the lines: lines are (index, material id, quantity, unit).
    Returns [{material, needed, quantity, ratio, lines, why}] for materials the lines give in a
    unit that converts; a material with no line is not reported."""
    out = []
    for need in needs(work_type, size):
        mat = need["material"]
        idx, total = [], 0.0
        for i, mid, q, unit in lines:
            if mid != mat:
                continue
            x = to_first_unit(mat, q, unit)
            if x is None:
                continue
            idx.append(i)
            total += x
        if not idx:
            continue
        needed = need["needed"]
        ratio = total / needed if needed > 0 else (math.inf if total > 0 else 1.0)
        out.append({"material": mat, "needed": round(needed, 2), "quantity": round(total, 2),
                    "ratio": ratio, "lines": idx, "why": need["why"],
                    "unit": catalog.material(mat)["units"][0]})
    return out
