r"""Second held-out set for the Cost agent's eval (T167): written after the first held-out set had
been used to change the agent (holdout.py is "seen" since), labelled and committed BEFORE its first
run. Schemes and honest cases not yet tried: buildings' quantities, padding split across lines,
other concrete grades and thicknesses, dearer items with reasons.

run.py --holdout2 runs them.
"""

from __future__ import annotations

from cases import (EDGE, FLAG, FRAUD, HONEST, OK, OK_SOFT, Case, add_line, find, finish, hall,
                   lab, lines_total, road, rows, scale)


def _qty(p: dict, start: str, f: float, just: str = "") -> dict:
    n = find(p, start)
    p[f"boq_qty_{n}"] = f"{float(p[f'boq_qty_{n}']) * f:.2f}"
    if just:
        p[f"boq_just_{n}"] = just
    return p


def holdout2() -> list[Case]:
    c: list[Case] = []

    def add(*a, **k):
        c.append(Case(*a, **k))

    # ---- frauds ----------------------------------------------------------------------------------
    add("h2_fraud_hall_steel_rate", "fraud: one line", FRAUD, "check", FLAG,
        "A hall's steel at 1.5 times the district's rate; the rest fair.",
        "About Rs 1 lakh in one line.",
        lambda w: finish(scale(hall(w), 1.5, only=("TMT steel",))))

    def lump_plus_rates(w):
        p = scale(road(w), 1.06)
        p["lumpsum_components"] = f"{lines_total(p) * 0.06:.0f}"
        return finish(p)
    add("h2_fraud_lump_and_rates", "fraud: hidden", FRAUD, "check", FLAG,
        "Rates 6% high and a 6% lump sum: 12% in all, each part small.",
        "A construction estimate carries 2% of lump sums at most.", lump_plus_rates)
    add("h2_fraud_hall_bricks_qty", "fraud: quantity", FRAUD, "check", FLAG,
        "A hall with 1.5 times the bricks other halls of its size use, justified.",
        "Rs 1.5 lakh of bricks nobody lays.",
        lambda w: finish(_qty(hall(w), "Bricks", 1.5, "Boundary wall and plinth protection")))
    add("h2_fraud_hall_cement_qty", "fraud: quantity", FRAUD, "check", FLAG,
        "A hall with 1.4 times the cement other halls of its size use, justified.",
        "Rs 2 lakh of cement beyond the usual.",
        lambda w: finish(_qty(hall(w), "Cement", 1.4, "Extra plaster and flooring base")))

    def hall_days(w):
        return finish(lab(hall(w), "beldar", 1.0, days_f=2.5))
    add("h2_fraud_hall_labour_days", "fraud: labour", FRAUD, "check", FLAG,
        "A hall's labourers on the roll for 2.5 times the days other halls take.",
        "Inflated muster roll.", hall_days)

    def split_cement(w):
        p = road(w)
        n = find(p, "Cement")
        q, r = float(p[f"boq_qty_{n}"]), float(p[f"boq_rate_{n}"])
        p[f"boq_qty_{n}"] = f"{q / 3:.1f}"
        p[f"boq_rate_{n}"] = f"{r * 1.3:.0f}"
        for k in (2, 3):
            add_line(p, f"Cement OPC 43 grade (lot {k})", "bag", round(q / 3, 1), round(r * 1.3),
                     "District recent rates")
        return finish(p)
    add("h2_fraud_cement_split_30", "fraud: one line", FRAUD, "check", FLAG,
        "Cement 30% high, split into three lots so no line looks big.",
        "Rs 1.5 lakh over the market.", split_cement)

    def answered_stone(w):
        p = road(w)
        n = find(p, "Stone aggregate")
        p[f"boq_rate_{n}"] = f"{float(p[f'boq_rate_{n}']) * 2.5:.0f}"
        p[f"boq_just_{n}"] = "Special 10 mm chips from a distant quarry"
        return finish(p)
    add("h2_fraud_stone_25x_answered", "fraud: one line", FRAUD, "ask", FLAG,
        "Stone at 2.5 times the district's rate, 'special chips from a distant quarry'.",
        "Rs 4 lakh over the market.", answered_stone)
    add("h2_fraud_pad_13_wide_road", "fraud: salami padding", FRAUD, "check", FLAG,
        "A 600 m x 5.5 m road with every material 13% above the district.",
        "Beyond CPWD's 10% on a Rs 40 lakh road.",
        lambda w: finish(road(w, length=600, width=5.5, rate_up=1.13, days=300)))

    # ---- honest and edge cases -----------------------------------------------------------------
    add("h2_edge_hall_heavier_steel", "edge: specification", EDGE, "fits", OK_SOFT,
        "A hall in a seismic zone with 1.3 times the usual steel, justified.",
        "A heavier frame: the agency's engineering call.",
        lambda w: finish(_qty(hall(w), "TMT steel", 1.3, "Seismic zone IV detailing")))

    def thick(w):
        return finish(road(w, pavement_thickness_mm="200",
                           road_layer_spec="M20 PCC 200 mm over WBM base 100 mm",
                           cement_x=200 / 150))
    add("h2_edge_road_200mm", "edge: specification", EDGE, "fits", OK,
        "A 200 mm road (heavy traffic): a third more concrete than 150 mm, honestly.",
        "The size says it: more slab, more cement.", thick)

    def m15(w):
        return finish(road(w, road_material_grade="M15",
                           road_layer_spec="M15 PCC 150 mm over WBM base 100 mm",
                           cement_x=6.30 / 8.06))
    add("h2_edge_road_m15", "edge: specification", EDGE, "fits", OK,
        "An M15 road: less cement per m3 than M20.", "Honest, cheaper.", m15)

    def small_dear(w):
        p = road(w)
        add_line(p, "Road signage boards, retro-reflective", "nos", 3, 7000, "Approved quotation")
        return finish(p)
    add("h2_edge_small_dear_item", "edge: items", EDGE, "fits", OK,
        "Three signboards at twice the usual price.", "Rs 10,000 in all.", small_dear)

    def doors(w):
        p = hall(w)
        n = find(p, "Doors")
        p[f"boq_rate_{n}"] = f"{float(p[f'boq_rate_{n}']) * 1.5:.0f}"
        p[f"boq_just_{n}"] = "Fire-rated doors for a public hall"
        return finish(p)
    add("h2_edge_hall_fire_doors", "edge: specification", EDGE, "edge", OK_SOFT,
        "A hall's doors at 1.5 times the usual, fire-rated.", "A dearer item with a reason.",
        doors)
    add("h2_honest_hall_cheap", "honest noise", HONEST, "fits", OK,
        "An honest hall 8% below the district.", "Cheap is no question.",
        lambda w: finish(scale(hall(w), 0.92)))

    def many_lines(w):
        p = road(w)
        for n in list(rows(p)):
            if p[f"boq_desc_{n}"].startswith(("Coarse sand", "Stone aggregate")):
                q = float(p[f"boq_qty_{n}"])
                p[f"boq_qty_{n}"] = f"{q / 2:.2f}"
                add_line(p, p[f"boq_desc_{n}"] + " (second half)", p[f"boq_unit_{n}"], q / 2,
                         float(p[f"boq_rate_{n}"]), "District recent rates")
        return finish(p)
    add("h2_honest_lines_in_halves", "honest noise", HONEST, "fits", OK,
        "An honest road with its sand and stone each on two lines.", "Same money.", many_lines)
    return c
