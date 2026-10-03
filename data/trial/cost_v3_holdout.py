r"""Cost Estimate engine (T097) on works it has never seen: the Uttar Pradesh hold-out.

The reference is built from UP works dated before 2026 only (reference.build); the engine then
reads every 2026 UP work whose record states the size of a group it can compare (solar street
lights per light, high masts per mast), each turned into a complete cost estimate form:
size = the record's count, one line at the record's price per unit, the MP's amount = the
sanctioned amount (on eSAKSHI the two are equal). On those forms it measures:

  real         questions on the real works as they are (the MP's amount equals the estimate,
               so only a quantity question could arise: there are none on these forms)
  line         real works whose price per unit is above the question line (p98 x 1.25 of their
               group): the most that could ever be asked about if the MP's amount were lower
  planted      the same works priced 1.1x to 3x, the MP's amount left at the real figure: share
               asked about
  size         the same works at half, double and five times the number of units, same unit
               price: answers that change (must be 0)
  not checked  works whose group could not be compared (too few works, or not tight)

Run:  apps\engine\.venv\Scripts\python.exe data\trial\cost_v3_holdout.py
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import date
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "data"))
sys.path.insert(0, str(ROOT / "apps" / "engine"))
from esakshi_dashboard import load  # noqa: E402

from drishti.agents.cost_estimate import agent, reference  # noqa: E402
from drishti.cost_form.validate import validate  # noqa: E402

STATE = "Uttar Pradesh"
TODAY = date(2026, 10, 3)
OUT = ROOT / "data" / "trial" / "results" / "cost_v3_holdout_up.json"
PLANTED = (1.1, 1.25, 1.5, 2.0, 3.0)
SCALES = (0.5, 2.0, 5.0)


def _year(w: dict) -> int | None:
    d = w.get("recommended_date") or w.get("completed_date")
    return d.year if isinstance(d, date) else None


def form(key: str, units: int, rate: float, mp: float) -> dict:
    """A complete estimate: one line at the price per unit, no charges."""
    if key == "HIGH_MAST":
        work_type = "HIGH_MAST"
        size = {"masts_nos": units, "mast_height_m": 12.5, "lamps_per_mast": 6, "lamp_w": 200,
                "mast_power": "grid", "cable_m": 0}
    else:
        work_type = "STREET_LIGHT"
        size = {"lights_nos": units, "light_power": "solar_standalone", "led_w": 12,
                "pole_height_m": 6, "pole_material": "gi", "panel_wp": 40, "battery_wh": 300,
                "battery_type": "lifepo4", "warranty_years": 5}
    total = units * rate
    gap = abs(total - mp) / mp if mp else 0
    return {
        "recommendation": {"work_id": "HOLDOUT", "mp_amount": mp, "recommended_type": work_type,
                           "recommended_description": "hold-out", "recommended_date": "2026-01-01"},
        "work": {"inside_constituency": True, "land_owner": "panchayat", "land_free": True,
                 "work_type": work_type, "nature": "installation", "design_standard": "none",
                 "description": " ".join(["word"] * 30)},
        "sites": [{"location": {"district_lgd": "0", "block": "b", "gp_or_ward": "g",
                                "village": "v", "pin": "222001", "area_type": "rural",
                                "lat": 25.7, "lon": 82.7},
                   "size": size,
                   "site_conditions": {"terrain": "plain", "soil": "normal",
                                       "groundwater_shallow": "no", "access": "truck",
                                       "road_distance_m": 0, "site_water": True,
                                       "site_power": True, "demolition_m3": 0,
                                       "utility_shifting_nos": 0, "trees_nos": 0},
                   "lines": [{"group": "materials", "item": "Complete set, installed",
                              "material_id": "none", "quantity": units, "unit": "nos",
                              "rate": rate, "basis": "quotation"}]}],
        "charges": {"contingency_percent": 0, "gst_percent": 0, "gst_amount": 0,
                    "labour_cess_amount": 0, "royalty_amount": 0, "other_fees_amount": 0},
        "timing": {"estimate_month": "2026-09", "start_month": "2026-10", "duration_months": 3},
        "totals": {"total_as_per_document": total,
                   **({"reason_differs_from_mp": "hold-out"} if gap > 0.10 else {})},
        "prepared": {"prepared_by_role": "ia_engineer", "prepared_by_designation": "x",
                     "checked_by_designation": "x", "estimate_pdf": "f", "drawings": "f",
                     "site_photo_before": "f", "land_noc": "f"},
        "declarations": {"decl_no_land_cost": True, "decl_no_maintenance": True,
                         "decl_not_funded_elsewhere": True, "decl_actuals": True},
    }


def ready_form(key, units, rate, mp) -> dict | None:
    """The form, with its "looks unusual" checks confirmed as an agency would; None when the
    form refuses it (e.g. 215 masts at one site: the record was several sites)."""
    f = form(key, units, rate, mp)
    v = validate(f, today=TODAY)
    if any(i["level"] == "fix" for i in v["issues"]):
        return None
    f["confirmed"] = [i["key"] for i in v["issues"]]
    return f


def ask(ref, w, key, units, rate, mp):
    f = ready_form(key, units, rate, mp)
    if f is None:
        return None
    return agent.assess({"work_id": "H", "state_name": STATE,
                         "district_name": w.get("district_name"), "cost_form": f},
                        SimpleNamespace(as_of=TODAY, data={agent.AGENT: ref}))


def main() -> None:
    works, info = load()
    up = [w for w in works if w.get("state_name") == STATE]
    train = [w for w in up if (_year(w) or 9999) < 2026]
    test = [w for w in up if _year(w) == 2026]
    ref = reference.build(train, STATE, f"{info['works']:,} dashboard works, before 2026 only")
    rows = []
    for w in test:
        got = reference.record_price(w)
        if not got or got[0] not in ("STREET_LIGHT|solar", "HIGH_MAST"):
            continue
        key, _unit, price = got
        units = max(1, round(w["amount"] / price))
        if ready_form(key, units, price, float(w["amount"])) is None:
            continue
        rows.append((w, key, units, price, float(w["amount"])))
    refused = sum(1 for w in test if (reference.record_price(w) or ("",))[0]
                  in ("STREET_LIGHT|solar", "HIGH_MAST")) - len(rows)

    out = {"state": STATE, "reference": ref["source"], "reference_years": ref["years"],
           "test_works": len(rows), "refused_by_the_form": refused,
           "by_group": dict(Counter(r[1] for r in rows))}
    real = [ask(ref, w, k, n, p, mp) for w, k, n, p, mp in rows]
    compared = [r for r in real if any(s.get("price_per_unit") for s in r.evidence.get("sites", []))]
    out["not_checked"] = len(rows) - len(compared)
    out["not_checked_reasons"] = dict(Counter(
        r.limitations[0].split("because ")[-1][:60] for r in real if r not in compared))
    out["real_questions"] = sum(1 for r in real if r.findings)
    out["above_question_line"] = sum(
        1 for r in compared for s in r.evidence["sites"]
        if s.get("price_per_unit") and s["price_per_unit"] > s["question_above"])
    out["planted"] = {}
    for k in PLANTED:
        caught = 0
        for (w, key, n, p, mp), r0 in zip(rows, real, strict=True):
            if r0 not in compared:
                continue
            r = ask(ref, w, key, n, p * k, mp)
            caught += any(f.code == "ESTIMATE_ABOVE_STANDARD_AND_MP" for f in r.findings)
        out["planted"][f"x{k:g}"] = {"caught": caught, "of": len(compared)}
    changed = 0
    for (w, key, n, p, mp), r0 in zip(rows, real, strict=True):
        for s in SCALES:
            m = max(1, round(n * s))
            r = ask(ref, w, key, m, p, mp * m / n)
            if r is None:                   # the scaled form is refused (over 200 masts)
                continue
            changed += [f.code for f in r.findings] != [f.code for f in r0.findings]
    out["size_changes_answer"] = {"changed": changed, "of": len(rows) * len(SCALES)}
    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(out, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
