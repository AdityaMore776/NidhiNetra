r"""Quantities held to the work's own size, for more of what MPLADS builds (T144): planted filings.

The Cost agent asks about a quantity only when the agency confirmed it and it is more than 25%
above what the size needs (agent.QUANTITY_MARGIN); the form asks the agency to confirm anything
above the need. T144 adds three needs (cost_form/norms.py), each from the work's own size:

  stone      a CC road's coarse aggregate by its concrete mix (IS 456), plus 15%
  pipe       a water pipeline's pipes: its length plus 20 m a house connection, plus 10%
  capacity   solar lights bought by the watt or watt-hour: panels at each light's Wp, batteries
             at each light's Wh, plus 5%

and reads stone named for a road's base course as the base, not the concrete's aggregate.

Planted filings of the website form, each run through pswif.py, validate.py and the Cost agent
as the live check does (the agency confirms whatever the form asks it to: the worst case for a
false question):

  honest   roads: the slab's stone at 0.84-0.92 m3 per m3 of concrete (the mix's dry 0.84 to
           the analysis-of-rates figures), the base's stone on a line of its own named four ways
           (a WBM line, "aggregate for WBM", a plain "Stone aggregate 63 mm", or no stone base);
           pipelines: 1.00-1.05 x the length plus 6-15 m a house connection; solar lights: each
           light's Wp and Wh x the lights, +-3%; and roads with all their stone on one line with
           no size (the form asks the agency to itemise it before it is judged)
  padded   the honest filing with the one quantity x1.25, x1.5 or x2 (totals and the MP's amount
           raised to match, so nothing else on the form gives it away)

Nothing here is a real agency or work. Writes results/quantity_trial.txt and .json.

Run:  apps\engine\.venv\Scripts\python.exe data\trial\quantity_trial.py [--n 200]
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from datetime import date, timedelta
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "data"))
sys.path.insert(0, str(ROOT / "data" / "trial"))
sys.path.insert(0, str(ROOT / "apps" / "engine"))
import work_form_examples as wf  # noqa: E402

from drishti.agents.cost_estimate import agent  # noqa: E402
from drishti.cost_form import norms, pswif  # noqa: E402
from drishti.cost_form.validate import validate  # noqa: E402

OUT = ROOT / "data" / "trial" / "results" / "quantity_trial"
AS_OF = date(2026, 10, 2)
PADS = (1.25, 1.5, 2.0)
BASES = ("wbm line", "aggregate for WBM", "plain 63 mm", "no stone base", "one unsized line")


def run(p: dict) -> dict:
    """The filing through the live path; the agency confirms what the form asks."""
    form = pswif.to_cost_form(p, AS_OF)
    v = validate(form, today=AS_OF)
    form["confirmed"] = [i["key"] for i in v["issues"] if i["level"] == "confirm"]
    fixes = [i["code"] for i in v["issues"] if i["level"] == "fix"]
    work = {"work_id": p["recommendation_ref"], "state_name": "Uttar Pradesh",
            "district_name": "Jaunpur", "district_lgd": "UTTAR PRADESH|JAUNPUR",
            "cost_form": form, "cost_form_meta": {"saved_by": p["implementing_agency"]}}
    r = agent.assess(work, SimpleNamespace(as_of=AS_OF, data={"sor": None, "rates": None}))
    q = [f.evidence for f in r.findings if f.code == "MATERIAL_QUANTITY_ABOVE_SIZE"]
    return {"fixes": fixes, "asked": [e["material"] for e in q],
            "form_confirms": sum(1 for i in v["issues"] if i["code"] == "more_than_size_needs")}


def totals(p: dict) -> dict:
    """Totals and the MP's amount raised to match the lines, so only the quantity differs."""
    t = wf.estimate_total(p)
    p.update({"technical_estimate": f"{t:.2f}", "mp_recommended_amount": f"{t:.0f}",
              "mplads_share": f"{t:.0f}"})
    return p


def _set_row(p: dict, n: int, desc: str, unit: str, qty: float, rate: float) -> None:
    p.update({f"boq_code_{n}": "", f"boq_desc_{n}": desc, f"boq_unit_{n}": unit,
              f"boq_qty_{n}": f"{qty:g}", f"boq_rate_{n}": f"{rate:g}",
              f"boq_source_{n}": "District recent rates", f"boq_measure_ref_{n}": f"MB p.{n}",
              f"boq_just_{n}": ""})


def road(rng: random.Random, i: int, base: str, stone_x: float = 1.0) -> dict:
    length = rng.choice((150, 200, 250, 300, 400, 500))
    width = rng.choice((3.0, 3.5, 3.75))
    rec = AS_OF - timedelta(days=rng.randint(10, 150))
    p = wf.road(f"QT-R{i}", "Gramin Nirman Vibhag", f"Gaon {i}", 30 + i % 200, rec, None,
                length=length, width=width)
    rows = {int(k.removeprefix("boq_desc_")): v for k, v in p.items() if k.startswith("boq_desc_")}
    stone_row = next(n for n, v in rows.items() if v.startswith("Stone aggregate"))
    base_row = next(n for n, v in rows.items() if v.startswith("WBM"))
    vol = length * width * 0.15
    _set_row(p, stone_row, "Stone aggregate 20 mm", "cum",
             round(vol * rng.uniform(0.84, 0.92) * stone_x, 1), wf.RATE["aggregate"])
    base_qty = float(p[f"boq_qty_{base_row}"])
    if base == "aggregate for WBM":
        _set_row(p, base_row, "Stone aggregate 63 mm for WBM", "cum", base_qty, 1650)
    elif base == "plain 63 mm":
        _set_row(p, base_row, "Stone aggregate 63 mm", "cum", base_qty, 1650)
    elif base == "one unsized line":
        # the slab's and the base's stone together, no size: the form asks to itemise (T144)
        slab = float(p[f"boq_qty_{stone_row}"])
        _set_row(p, stone_row, "Stone aggregate", "cum", round(slab + base_qty, 1),
                 wf.RATE["aggregate"])
        for k in [k for k in p if k.endswith(f"_{base_row}") and k.startswith("boq_")]:
            del p[k]
    elif base == "no stone base":
        _set_row(p, base_row, "Brick soling, first class bricks", "m2",
                 round(length * width), 410)
        p["road_layer_spec"] = "M20 PCC 150 mm over brick soling"
    return totals(p)


def pipeline(rng: random.Random, i: int, pipe_x: float = 1.0, one_line: bool = False) -> dict:
    """`one_line`: the main and the connections' pipes on one line (the allowance a connection
    then applies); else each on its own (the main alone held to the length)."""
    length = rng.choice((300, 450, 600, 900, 1200, 2000))
    homes = rng.choice((0, 10, 25, 40, 80))
    pipe = length * rng.uniform(1.0, 1.05) * pipe_x
    taps = sum(rng.uniform(6, 15) for _ in range(homes)) * (pipe_x if one_line else 1.0)
    if one_line:
        rows = [("HDPE pipes, 110 mm main and 20 mm house connections", "m", round(pipe + taps),
                 360, "District recent rates")]
    else:
        rows = [("HDPE pipe 110 mm PE100 PN6", "m", round(pipe), 410, "District recent rates")]
        if homes:
            rows.append(("HDPE pipe 20 mm for house connections", "m", round(taps), 65,
                         "District recent rates"))
    rows.append(("Sluice valve 100 mm", "nos", max(2, length // 300), 9500, "Approved quotation"))
    lines, total = wf.boq(rows)
    rec = AS_OF - timedelta(days=rng.randint(10, 150))
    lat, lon = wf.pin(i)
    p = wf.common(f"QT-W{i}", "Jal Nigam Division", f"Gaon {i}", rec, None,
                  rec + timedelta(days=40), 90, total, total)
    p.update(lines)
    p.update({
        "work_title": f"Water pipeline to the habitation, Gaon {i}",
        "sector": "Drinking water facilities", "work_type": "water", "work_nature": "New asset",
        "scope_of_work": f"Laying a {length} m HDPE water pipeline, 110 mm PE100 PN6, from the "
                         "existing overhead tank near the panchayat bhawan to the lower basti"
                         + (f", with {homes} house connections" if homes else "")
                         + f" and sluice valves, in village Gaon {i}, where households now carry "
                         "water from a hand pump a kilometre away.",
        "site_geometry_type": "Linear asset / alignment", "latitude": f"{lat:.6f}",
        "longitude": f"{lon:.6f}", "start_lat": f"{lat:.6f}", "start_lon": f"{lon:.6f}",
        "end_lat": f"{lat + length * 0.8 / 111_000:.6f}", "end_lon": f"{lon:.6f}",
        "water_system_type": "Pipeline", "pipeline_length_m": str(length),
        "pipeline_diameter_mm": "110", "pipe_material": "HDPE",
        "connections_users": str(homes), "sanction_decision": "",
    })
    return totals(p)


def solar(rng: random.Random, i: int, x: float = 1.0, by: str = "wp") -> dict:
    n = rng.choice((5, 10, 15, 20, 30))
    wp = rng.choice((40, 60, 75))
    volts, ah = rng.choice(((12.8, 30), (12.8, 40), (25.6, 20)))
    wh = volts * ah
    rows = [("LED luminaire 12 W, IP65", "nos", n, 3200, "Approved quotation"),
            ("GI pole 6 m with bracket and foundation", "nos", n, 9500, "Approved quotation")]
    if by == "wp":
        rows += [(f"Solar PV module {wp} Wp", "Wp", round(n * wp * rng.uniform(0.97, 1.03) * x),
                  38, "Approved quotation"),
                 (f"LiFePO4 battery {volts} V {ah} Ah", "nos", n, 9000, "Approved quotation")]
    else:
        rows += [(f"Solar PV module {wp} Wp", "nos", n, wp * 38, "Approved quotation"),
                 (f"LiFePO4 battery {volts} V {ah} Ah", "kWh",
                  round(n * wh * rng.uniform(0.97, 1.03) * x / 1000, 2), 28000,
                  "Approved quotation")]
    lines, total = wf.boq(rows)
    p = wf.lights(f"QT-S{i}", "Urja Vikas Nigam", f"Gaon {i}", 30 + i % 200,
                  AS_OF - timedelta(days=rng.randint(10, 150)), 1.0, total)
    for k in [k for k in p if k.startswith("boq_")]:
        del p[k]
    p.update(lines)
    p.update({"energy_quantity": str(n), "solar_wp": str(wp),
              "battery_spec": f"LiFePO4 {volts} V {ah} Ah",
              "scope_of_work": f"Supply and installation of {n} standalone solar street lights, "
                               f"each a 12 W LED with a {wp} Wp panel and a LiFePO4 "
                               f"{volts} V {ah} Ah battery on a 6 m GI pole, in village Gaon {i}."})
    return totals(p)


def rate_of(results: list[dict], want: str) -> dict:
    n = len(results)
    asked = sum(1 for r in results if want in r["asked"])
    return {"n": n, "asked": asked, "share": round(asked / n, 4) if n else None,
            "not_judged": sum(1 for r in results if r["fixes"]),
            "form_confirms": sum(1 for r in results if r["form_confirms"])}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=200)
    args = ap.parse_args()
    rng = random.Random(144)
    out: dict = {"n": args.n, "pads": PADS, "cells": {}}
    lines = [f"T144 quantity trial: {args.n} planted filings a cell, seed 144",
             "(asked = the Cost agent's MATERIAL_QUANTITY_ABOVE_SIZE; the form asked the agency "
             "to confirm = it was shown the need first; not judged = a form fix left)", ""]

    def cell(name: str, want: str, make) -> None:
        res = [run(make(i)) for i in range(args.n)]
        r = rate_of(res, want)
        out["cells"][name] = r
        lines.append(f"  {name:<58} asked {r['asked']:>4}/{r['n']} ({r['share']:.1%})"
                     f"   form asked to confirm {r['form_confirms']:>4}   not judged "
                     f"{r['not_judged']}")

    lines.append("CC roads: the slab's stone")
    for base in BASES:
        cell(f"honest, base: {base}", "aggregate", lambda i, b=base: road(rng, i, b))
    for x in PADS:
        for base in ("wbm line", "plain 63 mm"):
            cell(f"stone x{x}, base: {base}", "aggregate",
                 lambda i, b=base, x=x: road(rng, i, b, x))
    lines.append("")
    lines.append("Water pipelines: pipes against the length and house connections")
    for one in (False, True):
        how = "all pipe on one line" if one else "main and connections itemised"
        cell(f"honest, {how}", "pipe", lambda i, o=one: pipeline(rng, i, 1.0, o))
        for x in PADS:
            cell(f"pipes x{x}, {how}", "pipe", lambda i, x=x, o=one: pipeline(rng, i, x, o))
    lines.append("")
    lines.append("Solar street lights bought by capacity")
    for by, mat in (("wp", "solar_panel"), ("wh", "battery")):
        cell(f"honest, {by.upper()} lines", mat, lambda i, b=by: solar(rng, i, 1.0, b))
        for x in PADS:
            cell(f"{by.upper()} x{x}", mat, lambda i, b=by, x=x: solar(rng, i, x, b))

    # the honest filings asked about anything at all (any quantity question)
    lines += ["", "Constants: " + ", ".join(f"{k} {getattr(norms, k)}" for k in (
        "AGGREGATE_ROOM", "PIPE_ROOM", "CONNECTION_PIPE_M", "WASTAGE")) +
              f", the agent's margin {agent.QUANTITY_MARGIN}"]
    OUT.with_suffix(".txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    OUT.with_suffix(".json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
