"""The cost estimate form (T093): its field list, the material matcher and the checks made while
it is filled. A normal mistake must be caught on the agency's screen as "fix" or "confirm",
never become a flag, and no input may break the checks."""

from __future__ import annotations

import copy
import json
import random
from datetime import date
from pathlib import Path

import pytest

from drishti import reference
from drishti.cost_form import catalog, materials
from drishti.cost_form.validate import validate

TODAY = date(2026, 10, 3)
SPEC = Path(__file__).resolve().parents[4] / "docs" / "specs" / "2026-10-03-cost-estimate-form.md"


def road_form() -> dict:
    """A complete, correct estimate for a 250 m x 3.75 m M20 CC road (made-up figures)."""
    lines = [
        {"group": "materials", "item": "Cement OPC 43 grade", "quantity": 1125, "unit": "bag",
         "rate": 400, "basis": "market_rate"},
        {"group": "materials", "item": "Coarse sand (balu)", "quantity": 70, "unit": "m3",
         "rate": 2500, "basis": "market_rate"},
        {"group": "materials", "item": "Stone aggregate 20 mm (gitti)", "quantity": 135,
         "unit": "m3", "rate": 3000, "basis": "sor", "sor_code": "UP-PWD 5.3"},
        {"group": "materials", "item": "GSB", "quantity": 94, "unit": "m3", "rate": 1500,
         "basis": "sor", "sor_code": "UP-PWD 4.1"},
        {"group": "labour", "item": "Unskilled labour", "material_id": "labour_beldar",
         "quantity": 900, "unit": "day", "rate": 450, "basis": "sor", "sor_code": "UP-LAB-1",
         "workers": 10, "days": 90,
         "activity": "Earthwork, mixing and carrying the concrete", "for_lines": [1, 2, 3, 4]},
        {"group": "labour", "item": "Skilled labour (mason)", "material_id": "labour_mason",
         "quantity": 250, "unit": "day", "rate": 800, "basis": "sor", "sor_code": "UP-LAB-2",
         "workers": 5, "days": 50,
         "activity": "Laying, levelling and finishing the concrete"},
        {"group": "machinery", "item": "Concrete mixer and vibrator hire", "quantity": 30,
         "unit": "day", "rate": 2500, "basis": "quotation"},
        {"group": "finishing", "item": "MPLADS plaque", "unit": "ls", "amount": 15000,
         "basis": "market_rate"},
        {"group": "quality", "item": "Concrete cube tests", "unit": "ls", "amount": 10000,
         "basis": "sor", "sor_code": "UP-QC-1"},
    ]
    # lines 18,76,000; contingency 3% 56,280; GST 18% on 19,32,280 = 3,47,810.40; cess 19,323
    return {
        "recommendation": {"work_id": "WS/MP0000/2026-2027/1", "mp_amount": 2_200_000,
                           "recommended_type": "ROAD_CC",
                           "recommended_description": "CC road in village Bhagwatipur",
                           "recommended_date": "2026-08-01"},
        "work": {"inside_constituency": True, "land_owner": "panchayat", "land_free": True,
                 "work_type": "ROAD_CC", "nature": "new", "design_standard": "pmgsy",
                 "description": "New cement concrete road of 250 metres from the panchayat "
                                "bhawan to the primary school in village Bhagwatipur, replacing a "
                                "broken brick road that floods every monsoon; width follows the "
                                "village road standard."},
        "sites": [{
            "location": {"district_lgd": "9999", "block": "Badlapur", "gp_or_ward": "Bhagwatipur",
                         "village": "Bhagwatipur", "pin": "222001", "area_type": "rural",
                         "lat": 25.75, "lon": 82.69, "end_lat": 25.752, "end_lon": 82.69},
            "size": {"length_m": 250, "width_m": 3.75, "concrete_grade": "M20",
                     "cc_thickness_mm": 150, "base_type": "gsb", "base_thickness_mm": 100,
                     "existing_surface": "brick", "raising_m": 0.2, "shoulder_width_m": 0.5,
                     "side_drain_m": 0, "cross_drains_nos": 0, "kerb_m": 0,
                     "signs_markings": False},
            "site_conditions": {"terrain": "plain", "soil": "normal", "groundwater_shallow": "no",
                                "access": "truck", "road_distance_m": 0, "site_water": True,
                                "site_power": False, "demolition_m3": 0,
                                "utility_shifting_nos": 0, "trees_nos": 0},
            "lines": lines}],
        "charges": {"contingency_percent": 3, "gst_percent": 18, "gst_amount": 347_810.4,
                    "labour_cess_amount": 19_323, "royalty_amount": 0, "other_fees_amount": 0},
        "timing": {"estimate_month": "2026-09", "sor_edition": "UP PWD SoR 2025-26",
                   "start_month": "2026-11", "duration_months": 6},
        "totals": {"total_as_per_document": 2_299_413},
        "prepared": {"prepared_by_role": "ia_engineer",
                     "prepared_by_designation": "Junior Engineer",
                     "checked_by_designation": "Assistant Engineer", "estimate_pdf": "file-1",
                     "drawings": "file-2", "site_photo_before": "file-3", "land_noc": "file-4"},
        "declarations": {"decl_no_land_cost": True, "decl_no_maintenance": True,
                         "decl_not_funded_elsewhere": True, "decl_actuals": True},
    }


def _rebalance(f):
    """After a test changes a line: the GST, the document's total and the MP's amount follow."""
    c = _run(f)["computed"]
    base = c["lines_total"] + c["contingency_amount"] + c["escalation_amount"]
    f["charges"]["gst_amount"] = round(base * f["charges"]["gst_percent"] / 100, 2)
    grand = _run(f)["computed"]["grand_total"]
    f["totals"]["total_as_per_document"] = grand
    f["recommendation"]["mp_amount"] = grand
    return f


def _codes(result, level=None):
    return {(i["code"], i["field"]) for i in result["issues"] if level in (None, i["level"])}


def _run(form):
    return validate(form, today=TODAY)


# ---- the field list ---------------------------------------------------------------------

def test_every_work_type_has_its_size_fields():
    codes = set(reference.work_types())
    covered = {t for fam in catalog.load()["families"].values() for t in fam["types"]}
    assert codes <= covered, codes - covered


def test_the_field_list_is_consistent():
    data = catalog.load()
    units = set(data["units"])
    sections = [data[s] for s in catalog.SECTIONS]
    sections += [f["fields"] for f in data["families"].values()]
    for fields in sections:
        ids = [f["id"] for f in fields]
        assert len(ids) == len(set(ids)), ids
        for f in fields:
            assert f["kind"] in {"number", "choice", "multi", "bool", "text", "date", "month",
                                 "gps", "file", "list"}, f
            if f.get("unit"):
                assert f["unit"] in units, f
            if f.get("hard") and f.get("soft"):
                assert f["hard"][0] <= f["soft"][0] <= f["soft"][1] <= f["hard"][1], f
    for m in data["materials"]:
        assert m["units"] and set(m["units"]) <= units, m
        assert m["guard"] is None or m["guard"][0] < m["guard"][1]


def test_the_spec_lists_every_field():
    text = SPEC.read_text(encoding="utf-8")
    data = catalog.load()
    ids = {f["id"] for s in catalog.SECTIONS for f in data[s]}
    ids |= {f["id"] for fam in data["families"].values() for f in fam["fields"]}
    ids |= {m["id"] for m in data["materials"]}
    missing = sorted(i for i in ids if f"`{i}`" not in text)
    assert not missing, f"the spec does not mention: {missing}"


def test_the_size_a_work_is_priced_by():
    assert catalog.pricing_size("ROAD_CC", {"length_m": 250, "width_m": 3.75}) == ("m2", 937.5)
    assert catalog.pricing_size("WATER_TANK", {"tanks_nos": 2, "capacity_l": 10000}) == ("kl", 20.0)
    assert catalog.pricing_size("CULVERT", {"structure_type": "pipe", "barrel_length_m": 8,
                                            "pipe_rows_nos": 2}) == ("m", 16.0)
    assert catalog.pricing_size("CULVERT", {"structure_type": "slab", "spans_nos": 1,
                                            "span_m": 4, "deck_width_m": 5}) == ("m2", 20.0)
    assert catalog.pricing_size("TOILET_BLOCK", {"seats_men_nos": 4, "seats_women_nos": 4,
                                                 "seats_accessible_nos": 1}) == ("nos", 9.0)
    assert catalog.pricing_size("COMPUTER", {}) is None
    assert catalog.pricing_size("ROAD_CC", {"length_m": 250}) is None


# ---- materials typed freely ---------------------------------------------------------------

@pytest.mark.parametrize("typed,expected", [
    ("Cement OPC 43 grade", "cement"), ("सीमेंट", "cement"), ("sariya 12mm", "steel_rebar"),
    ("TMT bars Fe500", "steel_rebar"), ("Coarse sand (balu)", "sand"), ("बालू", "sand"),
    ("Morang", "sand"), ("Gitti 20 mm", "aggregate"), ("First class bricks", "brick"),
    ("Skilled labour (mason)", "labour_mason"), ("Unskilled labour", "labour_unskilled"),
    ("Interlocking paver block 80mm", "paver_block"), ("Geotextile fabric", None), ("", None),
    ("Internal plaster", None), ("Electrical distribution panel", None),
])
def test_a_typed_item_is_recognised_or_left_alone(typed, expected):
    assert materials.match(typed) == expected


def test_rates_are_restated_per_the_materials_own_unit():
    cement, brick = catalog.material("cement"), catalog.material("brick")
    assert materials.per_first_unit(cement, 8, "kg") == pytest.approx(400)
    assert materials.per_first_unit(brick, 8000, "thousand") == pytest.approx(8)
    assert materials.per_first_unit(cement, 8, "m3") is None


# ---- the checks while the form is filled -------------------------------------------------

def test_a_complete_correct_estimate_is_ready():
    r = _run(road_form())
    assert r["ready"], [i for i in r["issues"]]
    c = r["computed"]
    assert c["lines_total"] == 1_876_000 and c["grand_total"] == pytest.approx(2_299_413.4)
    assert c["sites"][0]["pricing"] == {"unit": "m2", "value": 937.5}
    assert c["mp_gap"] == pytest.approx(0.0452, abs=1e-4)
    assert "reference" not in json.dumps(r).lower()       # never shows a reference price


def test_a_missing_size_must_be_fixed():
    f = road_form()
    del f["sites"][0]["size"]["width_m"]
    r = _run(f)
    assert ("required", "sites[0].size.width_m") in _codes(r, "fix") and not r["ready"]


def test_an_impossible_value_is_fixed_an_unusual_one_confirmed():
    f = road_form()
    f["sites"][0]["size"]["width_m"] = 37
    assert ("impossible", "sites[0].size.width_m") in _codes(_run(f), "fix")
    f["sites"][0]["size"]["width_m"] = 14
    r = _run(f)
    assert ("unusual", "sites[0].size.width_m") in _codes(r, "confirm") and not r["ready"]


def test_a_confirmed_typo_guard_lets_the_form_through():
    f = road_form()
    f["sites"][0]["size"]["width_m"] = 14
    f["confirmed"] = ["unusual:sites[0].size.width_m"]
    assert _run(f)["ready"]


def test_the_amount_must_be_quantity_times_rate():
    f = road_form()
    f["sites"][0]["lines"][0]["amount"] = 4_500_000          # an extra zero
    assert ("line_arithmetic", "sites[0].lines[0].amount") in _codes(_run(f), "fix")


def test_a_rate_with_an_extra_zero_is_asked_about_not_flagged():
    f = road_form()
    f["sites"][0]["lines"][0]["rate"] = 4000                 # Rs 4,000 a bag
    r = _run(_rebalance(f))
    assert ("rate_typo", "sites[0].lines[0].rate") in _codes(r, "confirm")
    assert not _codes(r, "fix")
    f["sites"][0]["lines"][0].update(unit="kg", quantity=56_250, rate=8)   # same cement, in kg
    assert ("rate_typo", "sites[0].lines[0].rate") not in _codes(_run(_rebalance(f)))


def test_the_wrong_unit_for_a_material_is_asked_about():
    f = road_form()
    f["sites"][0]["lines"][0]["unit"] = "m"
    assert ("unit_for_material", "sites[0].lines[0].unit") in _codes(_run(f), "confirm")


def test_any_material_can_be_typed():
    f = road_form()
    f["sites"][0]["lines"].append({"group": "materials", "item": "Geotextile fabric",
                                   "quantity": 900, "unit": "m2", "rate": 60,
                                   "basis": "quotation"})
    r = _run(_rebalance(f))
    assert r["ready"], r["issues"]
    line = r["computed"]["sites"][0]["lines"][-1]
    assert line["material_id"] is None and line["amount"] == 54_000


def test_a_person_can_overrule_the_suggested_material():
    f = road_form()
    f["sites"][0]["lines"][1]["material_id"] = "none"
    assert _run(f)["computed"]["sites"][0]["lines"][1]["material_id"] is None


def test_a_type_not_in_the_list_can_be_written_in():
    f = road_form()
    f["work"]["work_type"] = "OTHER"
    r = _run(f)
    fixes = _codes(r, "fix")
    assert ("required", "work.other_type_name") in fixes
    assert ("required", "sites[0].size.size_value") in fixes
    f["work"]["other_type_name"] = "Village haat platform"
    f["sites"][0]["size"] = {"size_measure": "platform area", "size_value": 120,
                             "size_unit": "m2", "specification": "Raised brick platform with a "
                             "PCC top and a sheet roof on steel columns, open on all sides"}
    r = _run(f)
    assert r["ready"], r["issues"]
    assert r["computed"]["sites"][0]["pricing"] == {"unit": "m2", "value": 120.0}


def test_goods_need_a_specification_and_a_price_basis():
    f = road_form()
    f["work"].update(work_type="COMPUTER", nature="purchase")
    f["sites"][0]["size"] = {"receiving_institution": "Government inter college"}
    f["sites"][0]["lines"] = [{"group": "goods", "item": "Desktop computer", "quantity": 10,
                               "unit": "nos", "rate": 55000, "basis": "gem"}]
    r = _run(f)
    fixes = _codes(r, "fix")
    assert ("required", "sites[0].lines[0].spec") in fixes
    assert ("goods_price_basis", "sites[0].lines[0].gem_id") in fixes
    assert ("required", "work.land_owner") not in fixes          # no land for a purchase


def test_the_lines_must_add_up_to_the_estimate_document():
    f = road_form()
    f["totals"]["total_as_per_document"] = 2_400_000
    assert ("total_mismatch", "totals.total_as_per_document") in _codes(_run(f), "fix")


def test_a_big_gap_from_the_mps_amount_needs_a_reason():
    f = road_form()
    f["recommendation"]["mp_amount"] = 1_500_000             # 53% below the estimate
    assert ("required", "totals.reason_differs_from_mp") in _codes(_run(f), "fix")
    f["totals"]["reason_differs_from_mp"] = "The MP's figure left out the base layer and GST."
    assert _run(f)["ready"]


def test_a_road_cannot_be_shorter_than_the_distance_between_its_ends():
    f = road_form()
    f["sites"][0]["location"]["end_lat"] = 25.76              # about 1.1 km away
    assert ("shorter_than_ends", "sites[0].size.length_m") in _codes(_run(f), "fix")


def test_dates_margins_and_declarations():
    f = road_form()
    f["timing"]["estimate_month"] = "2026-12"
    assert ("future_estimate", "timing.estimate_month") in _codes(_run(f), "fix")
    f["timing"]["estimate_month"] = "2024-01"
    assert ("old_prices", "timing.estimate_month") in _codes(_run(f), "confirm")
    f = road_form()
    f["charges"]["escalation_percent"] = 5
    assert ("escalation_short_work", "charges.escalation_percent") in _codes(_run(f), "fix")
    f = road_form()
    f["work"]["land_free"] = False
    f["declarations"]["decl_no_maintenance"] = False
    fixes = _codes(_run(f), "fix")
    assert ("land_not_free", "work.land_free") in fixes
    assert ("declaration", "declarations.decl_no_maintenance") in fixes


def test_lump_sums_and_costs_mplads_does_not_pay_are_asked_about():
    f = road_form()
    f["sites"][0]["lines"].append({"group": "other", "item": "Annual maintenance for 3 years",
                                   "unit": "ls", "amount": 600_000, "basis": "other"})
    r = _run(f)
    confirms = {c for c, _ in _codes(r, "confirm")}
    assert {"maybe_not_payable", "lump_sums", "other_share"} <= confirms


@pytest.mark.parametrize("seed", range(5))
def test_no_input_breaks_the_checks(seed):
    rng = random.Random(seed)
    junk = [None, "", "abc", -1, 0, 1e30, float("nan"), [], {}, True, "1,00,000", "2026-13",
            "９９", "सीमेंट"]
    for _ in range(80):
        f = road_form()
        for _ in range(rng.randint(1, 6)):
            part = rng.choice(["work", "charges", "timing", "totals", "recommendation"])
            key = rng.choice(list(f[part]) or ["x"])
            f[part][key] = rng.choice(junk)
            site = f["sites"][0]
            sec = rng.choice(["size", "location", "site_conditions"])
            k = rng.choice(list(site[sec]))
            site[sec][k] = rng.choice(junk)
            ln = rng.choice(site["lines"])
            ln[rng.choice(list(ln))] = rng.choice(junk)
        json.dumps(_run(f))
    for odd in (None, [], "x", {"sites": "x"}, {"sites": [None, 3]}, {"work": []}):
        r = _run(copy.deepcopy(odd))
        assert r["ready"] is False and r["issues"]


# ---- earlier works at this site and continuations (T100) -------------------------------------

def _with(nature=None, earlier_id=None, answers=None):
    f = road_form()
    if nature:
        f["work"]["nature"] = nature
        f["work"].update(existing_description="half of the road was laid in 2024",
                         earlier_scheme="mplads")
        if nature != "continuation":
            f["work"].update(existing_age_years=2, existing_condition="good")
    if earlier_id:
        f["work"]["earlier_work_id"] = earlier_id
    if answers is not None:
        f["earlier_works"] = answers
    return f


def test_a_continuation_must_name_the_work_it_continues():
    assert ("continuation_needs_id", "work.earlier_work_id") in _codes(
        _run(_with("continuation")), "fix")
    r = _run(_with("continuation", "WS/MP1/2024-2025/9"))
    assert r["ready"], r["issues"]


def test_every_sanctioned_look_alike_must_be_answered():
    r = validate(road_form(), today=TODAY, earlier=["WS/A", "WS/B"])
    assert {i["code"] for i in r["issues"] if i["level"] == "fix"} == {"earlier_unanswered"}
    assert not r["ready"]
    answered = _with(answers=[
        {"earlier_work": "WS/A", "answer": "different",
         "difference": "the other road is in the SC colony"},
        {"earlier_work": "WS/B", "answer": "different",
         "difference": "that one is the drain beside the school"}])
    assert validate(answered, today=TODAY, earlier=["WS/A", "WS/B"])["ready"]


def test_the_same_work_cannot_be_estimated_again():
    r = validate(_with(answers=[{"earlier_work": "WS/A", "answer": "same"}]), today=TODAY,
                 earlier=["WS/A"])
    assert ("same_as_sanctioned", "earlier_works[0].answer") in _codes(r, "fix")
    assert not r["ready"]


def test_continues_must_match_the_nature_and_the_earlier_work():
    bad = _with(answers=[{"earlier_work": "WS/A", "answer": "continues"}])
    assert ("continues_mismatch", "earlier_works[0].answer") in _codes(_run(bad), "fix")
    good = _with("continuation", "WS/A", answers=[{"earlier_work": "WS/A", "answer": "continues"}])
    assert validate(good, today=TODAY, earlier=["WS/A"])["ready"]


def test_different_must_say_what_differs():
    r = _run(_with(answers=[{"earlier_work": "WS/A", "answer": "different", "difference": "x"}]))
    assert ("too_short", "earlier_works[0].difference") in _codes(r, "fix")
    r = _run(_with(answers=[{"earlier_work": "WS/A", "answer": "maybe"}]))
    assert ("not_a_choice", "earlier_works[0].answer") in _codes(r, "fix")
