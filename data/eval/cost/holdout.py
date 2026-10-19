r"""Held-out cases for the Cost agent's eval (T167): written and labelled AFTER the agent's T167
changes, committed BEFORE they were first run, and never used to tune a threshold. They test
whether the rules generalise: other work types, padding spread differently, schemes mixed.

Same shape as cases.py (Case, the same worlds, levels and verdicts). run.py --holdout runs them.
"""

from __future__ import annotations

from cases import (
    EDGE,
    FLAG,
    FRAUD,
    HONEST,
    OK,
    OK_SOFT,
    Case,
    add_line,
    find,
    finish,
    hall,
    lab,
    lights,
    lines_total,
    road,
    scale,
)


def holdout() -> list[Case]:
    c: list[Case] = []

    def add(*a, **k):
        c.append(Case(*a, **k))

    # ---- frauds, schemes spread differently -------------------------------------------------
    def two_lines(w):
        p = road(w)
        return finish(scale(p, 1.35, only=("Coarse sand", "Stone aggregate")))
    add("ho_fraud_two_lines_35", "fraud: one line", FRAUD, "check", FLAG,
        "Sand and stone 35% above the district; cement and base fair.",
        "About a tenth of the estimate in two padded lines.", two_lines)

    def hall_13(w):
        return finish(scale(hall(w), 1.13))
    add("ho_fraud_hall_13", "fraud: salami padding", FRAUD, "check", FLAG,
        "A community hall with every line 13% above the district.",
        "Beyond CPWD's 10% on a Rs 9 lakh building.", hall_13)

    def hall_22(w):
        return finish(scale(hall(w), 1.22))
    add("ho_fraud_hall_22", "fraud: uniform padding", FRAUD, "ask", FLAG,
        "A community hall with every line 22% above the district.", "Beyond 15%.", hall_22)

    def sand_stone_qty(w):
        p = road(w)
        for start in ("Coarse sand", "Stone aggregate"):
            n = find(p, start)
            p[f"boq_qty_{n}"] = f"{float(p[f'boq_qty_{n}']) * 1.22:.1f}"
            p[f"boq_just_{n}"] = "Extra for the approaches"
        return finish(p)
    add("ho_fraud_qty_two_materials", "fraud: quantity", FRAUD, "check", FLAG,
        "Sand and stone each 22% above what the slab takes, both 'justified'.",
        "Each under the 25% question line; together real money.", sand_stone_qty)

    def mixed(w):
        p = scale(road(w), 1.08)
        p["other_charges"] = f"{lines_total(p) * 0.08:.0f}"   # tax already in the rates
        return finish(p)
    add("ho_fraud_rates_plus_charges", "fraud: hidden", FRAUD, "check", FLAG,
        "Rates 8% high and 8% 'other charges' though tax is in the rates: 16% in all.",
        "Each part looks like an edge case alone.", mixed)

    def kg_padded(w):
        p = scale(road(w), 1.16, only=("Cement",))
        n = find(p, "Cement")
        p[f"boq_qty_{n}"] = f"{float(p[f'boq_qty_{n}']) * 50:g}"
        p[f"boq_rate_{n}"] = f"{float(p[f'boq_rate_{n}']) / 50:.2f}"
        p[f"boq_unit_{n}"] = "kg"
        return finish(p)
    add("ho_fraud_cement_kg_16", "fraud: one line", FRAUD, "check", FLAG,
        "Cement 16% high, written per kg.", "The unit changes nothing.", kg_padded)

    add("ho_fraud_hall_labour_16", "fraud: labour", FRAUD, "check", FLAG,
        "A hall's masons and labourers both at 1.6 times the district's wage.",
        "Real money in wages no crew here earns.",
        lambda w: finish(lab(lab(hall(w), "mason", 1.6), "beldar", 1.6)))

    def hall_ghost(w):
        p = hall(w)
        for k in [k for k in p if k.startswith("lab_trade_") and p[k] == "mason"]:
            n = k.removeprefix("lab_trade_")
            p[f"lab_workers_{n}"] = f"{float(p[f'lab_workers_{n}']) * 3:g}"
        return finish(p)
    add("ho_fraud_hall_ghost_masons", "fraud: labour", FRAUD, "check", FLAG,
        "A hall with three times the masons on the roll for the same days.", "Ghost workers.",
        hall_ghost)
    add("ho_fraud_lights_130_mp", "fraud: price per unit", FRAUD, "check", FLAG,
        "Standard 12 W lights at 1.3 times the district's 98th percentile; the MP agrees.",
        "Just beyond the price margin.", lambda w: lights(27_200))

    def big_road_11(w):
        return finish(road(w, length=800, width=3.75, rate_up=1.11))
    add("ho_fraud_long_road_11", "fraud: salami padding", FRAUD, "check", FLAG,
        "An 800 m road, every material 11% above the district.", "Lakhs of rupees.",
        big_road_11)

    # ---- honest and edge cases ------------------------------------------------------------------
    def tiles(w):
        p = hall(w)
        n = find(p, "Vitrified")
        p[f"boq_rate_{n}"] = f"{float(p[f'boq_rate_{n}']) * 1.4:.0f}"
        p[f"boq_just_{n}"] = "Anti-skid tiles for the kitchen and ramp"
        return finish(p)
    add("ho_edge_hall_better_tiles", "edge: specification", EDGE, "edge", OK_SOFT,
        "A hall with anti-skid tiles at 1.4 times the usual tile rate (5% of the estimate).",
        "One dearer item, small money, explained.", tiles)
    add("ho_edge_hall_top_range", "edge: rates", EDGE, "edge", OK,
        "A hall with every line 6% above the district.", "Within CPWD's 10%.",
        lambda w: finish(scale(hall(w), 1.06)))
    def big_crew(w):
        p = lab(hall(w), "mason", 1.0, days_f=0.5)
        for k in [k for k in p if k.startswith("lab_trade_") and p[k] == "mason"]:
            n = k.removeprefix("lab_trade_")
            p[f"lab_workers_{n}"] = f"{float(p[f'lab_workers_{n}']) * 2:g}"
        return finish(p)
    add("ho_honest_hall_big_crew", "edge: labour", EDGE, "fits", OK,
        "A hall built faster with twice the masons for half the days: the same person-days.",
        "The agency's call.", big_crew)
    add("ho_honest_lights_120", "edge: price per unit", EDGE, "edge", OK,
        "Lights at 1.15 times the 98th percentile, MP agrees.", "Within the price margin.",
        lambda w: lights(24_000))

    def wide_road(w):
        return finish(road(w, length=500, width=5.5))
    add("ho_honest_wide_road", "honest noise", HONEST, "fits", OK,
        "An honest 5.5 m wide road (a district road).", "Bigger, honest.", wide_road)

    def gst_and_sundries(w):
        p = road(w)
        p["tax_treatment"] = "Added separately"
        p["lumpsum_components"] = f"{lines_total(p) * 0.015:.0f}"
        p["other_charges"] = f"{lines_total(p) * 0.18:.0f}"
        return finish(p)
    add("ho_honest_gst_sundries", "honest noise", HONEST, "fits", OK,
        "GST 18% added separately and 1.5% sundries.", "Ordinary charges.", gst_and_sundries)

    def extra_item(w):
        p = road(w)
        add_line(p, "Road signage boards, retro-reflective", "nos", 4, 3500, "Approved quotation")
        return finish(p)
    add("ho_honest_signage", "honest noise", HONEST, "fits", OK,
        "An honest road with four signboards no reader prices.", "Small, honest extra.",
        extra_item)
    add("ho_edge_price_rise_9_hall", "edge: rates", EDGE, "edge", OK,
        "A hall filed after a 9% price rise.", "Within CPWD's 10%.",
        lambda w: finish(scale(hall(w), 1.09)))
    return c
