r"""Planted-form trial for the Cost agent's whole-estimate check (T121, plan T120 §6.5 and §14).

No real cost estimate form exists yet (the form is new), so this measures the RULE on synthetic
forms, and says so. Each form is a CC road (100-500 m x 3.75 m, M20, 150 mm) with the six lines
the form recognises (cement, sand, aggregate, GSB, unskilled and skilled labour) plus a mixer hire,
a plaque and cube tests that are never compared.

  honest      every rate = the fair rate x a random factor (log-normal, spread SIGMA), cement
              quantity = what the size needs x 0.97-1.08, the rest x 0.95-1.05
  padded      the same honest form with every compared rate x (1 + m), m = 5, 10, 15, 20, 30%
  one line    the same honest form with the cement rate x 2 (one costly line)
  quantity    the same honest form with the cement quantity x 1.5 (rates honest)

The fair rate comes from (a) the Schedule of Rates (= the base rates), or (b) the district's own
rates: the median of 60 other honest forms from 12 agencies (rates.RateIndex). SIGMA is an
ASSUMPTION about how far honest rates spread (5%, 10%, 15%); real spreads come from real forms
(T098). Targets (plan §14): 9 in 10 forms padded by 20%+ asked, at most 2 in 100 honest asked.

Writes data/trial/results/cost_whole_trial.json and .txt.
Run: apps\engine\.venv\Scripts\python.exe data\trial\cost_whole_trial.py
"""

from __future__ import annotations

import json
import math
import random
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "apps" / "engine"))
from drishti.agents.cost_estimate import agent, rates, whole  # noqa: E402
from drishti.cost_form import norms  # noqa: E402

OUT = ROOT / "data" / "trial" / "results" / "cost_whole_trial"
TODAY = date(2026, 10, 3)
BASE = {"cement": ("bag", 400), "sand": ("m3", 2500), "aggregate": ("m3", 3000),
        "granular_base": ("m3", 1500), "labour_unskilled": ("day", 450),
        "labour_skilled": ("day", 800)}
PER_250M = {"sand": 70, "aggregate": 135, "granular_base": 94, "labour_unskilled": 900,
            "labour_skilled": 250}
SOR = {"edition": "trial SoR", "materials": {m: {"unit": u, "rate": r}
                                             for m, (u, r) in BASE.items()}}
N_FORMS = 1000
SIGMAS = (0.05, 0.10, 0.15)
MARKUPS = (0.05, 0.10, 0.15, 0.20, 0.30)


def cement_need(length: float) -> float:
    vol = length * 3.75 * 150 / 1000
    return vol * 1.54 / (1 + 1.5 + 3) * 1440 / 50 * 1.05     # M20 nominal mix, plus 5%


def honest(rng: random.Random, sigma: float) -> dict:
    length = rng.uniform(100, 500)
    lines = []
    for m, (unit, base) in BASE.items():
        q = (cement_need(length) * rng.uniform(0.97, 1.08) if m == "cement"
             else PER_250M[m] * length / 250 * rng.uniform(0.95, 1.05))
        lines.append({"group": "labour" if m.startswith("labour") else "materials",
                      "item": m, "material_id": m, "unit": unit, "quantity": round(q, 2),
                      "rate": round(base * math.exp(rng.gauss(0, sigma)), 2)})
    lines += [{"group": "machinery", "item": "Mixer hire", "material_id": "none", "unit": "day",
               "quantity": round(30 * length / 250), "rate": 2500},
              {"group": "finishing", "item": "MPLADS plaque", "unit": "ls", "amount": 15000},
              {"group": "quality", "item": "Cube tests", "unit": "ls", "amount": 10000}]
    return {"work": {"work_type": "ROAD_CC"}, "timing": {"estimate_month": "2026-09"},
            "sites": [{"size": {"length_m": round(length, 1), "width_m": 3.75,
                                "concrete_grade": "M20", "cc_thickness_mm": 150,
                                "base_type": "gsb", "side_drain_m": 0, "kerb_m": 0,
                                "cross_drains_nos": 0}, "lines": lines}]}


def computed(form: dict) -> dict:
    total = 0.0
    for ln in form["sites"][0]["lines"]:
        total += ln["amount"] if ln["unit"] == "ls" else ln["quantity"] * ln["rate"]
    return {"lines_total": total, "grand_total": total}


def variant(form: dict, rate: dict | None = None, qty: dict | None = None,
            every: float = 1.0) -> dict:
    f = json.loads(json.dumps(form))
    for ln in f["sites"][0]["lines"]:
        m = ln.get("material_id")
        if m in BASE:
            ln["rate"] = round(ln["rate"] * every * (rate or {}).get(m, 1.0), 2)
            ln["quantity"] = round(ln["quantity"] * (qty or {}).get(m, 1.0), 2)
    return f


def asked(form: dict, sor, index) -> bool:
    w = whole.judge(form, computed(form), "ROAD_CC", sor, index, "TRIAL", "this-agency",
                    "W", TODAY)
    return w.verdict == "ASK"


def quantity_asked(form: dict) -> bool:
    """The Cost agent's separate quantity question: a confirmed material more than 25% above
    what the size needs (agent.QUANTITY_MARGIN)."""
    site = form["sites"][0]
    lines = [(j, ln.get("material_id"), ln.get("quantity"), ln.get("unit"))
             for j, ln in enumerate(site["lines"])]
    return any(q["ratio"] > agent.QUANTITY_MARGIN
               for q in norms.check("ROAD_CC", site["size"], lines))


def main() -> None:
    out = {"forms_per_cell": N_FORMS, "assumption": "honest rate spread SIGMA is assumed, not "
           "measured; real spreads need real forms (T098)",
           "rule": {"gap_share": whole.GAP_SHARE, "gap_min_rs": whole.GAP_MIN_RS,
                    "min_coverage": whole.MIN_COVERAGE, "qty_tolerance": whole.QTY_TOLERANCE},
           "results": []}
    lines = ["Cost whole-estimate rule on synthetic CC-road forms (plan T120 §6.5)",
             f"{N_FORMS} forms per cell. Rule: ask when the gap is >= {whole.GAP_SHARE:.0%} and "
             f">= Rs {whole.GAP_MIN_RS:,}.", ""]
    for source in ("sor", "district"):
        for sigma in SIGMAS:
            rng = random.Random(f"{source}-{sigma}")
            index = None
            if source == "district":
                others = [{"work_id": f"O{k}", "district_lgd": "TRIAL",
                           "cost_form": honest(rng, sigma),
                           "cost_form_meta": {"saved_by": f"agency-{k % 12}"}} for k in range(60)]
                index = rates.RateIndex.build(others)
            sor = SOR if source == "sor" else None
            forms = [honest(rng, sigma) for _ in range(N_FORMS)]
            row = {"fair_rate_from": source, "sigma": sigma,
                   "honest_asked": sum(asked(f, sor, index) for f in forms) / N_FORMS}
            for m in MARKUPS:
                row[f"every_line_+{round(m * 100)}%"] = sum(
                    asked(variant(f, every=1 + m), sor, index) for f in forms) / N_FORMS
            row["one_line_x2 (cement rate)"] = sum(
                asked(variant(f, rate={"cement": 2.0}), sor, index) for f in forms) / N_FORMS
            row["cement_quantity_x1.5"] = sum(
                asked(variant(f, qty={"cement": 1.5}), sor, index) for f in forms) / N_FORMS
            row["cement_quantity_x1.5, whole or quantity question"] = sum(
                asked(v, sor, index) or quantity_asked(v)
                for v in (variant(f, qty={"cement": 1.5}) for f in forms)) / N_FORMS
            row["honest, quantity question"] = sum(quantity_asked(f) for f in forms) / N_FORMS
            out["results"].append(row)
            lines.append(f"fair rate from {source:8} spread {sigma:.0%}: " + ", ".join(
                f"{k.replace('_', ' ')} {v:.1%}" for k, v in row.items()
                if k not in ("fair_rate_from", "sigma")))
    lines += ["", "Targets (plan §14): every line +20% or more asked >= 90%; honest asked <= 2%.",
              "Synthetic forms only: the honest spread is an assumption."]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.with_suffix(".json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    OUT.with_suffix(".txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
