"""Cost Estimate engine (Cost v3, T097): asks only when it is certain the estimate is too much for
what is being built. The planted cases of docs/plans/T097-cost-agent-v3.md §8: a bigger work at
the same unit price is never asked about; a higher price is, only when the MP's amount agrees;
an MP's low guess alone never is; a road is never compared per metre; a confirmed quantity beyond
what the size needs is; nothing typed by mistake reaches the engine."""

from __future__ import annotations

import copy
import json
import random
from datetime import date
from types import SimpleNamespace

import pytest

from drishti.agents import registry
from drishti.agents.contract import Status, check_plain_language
from drishti.agents.cost_estimate import agent, reference
from drishti.cost_form.validate import validate
from tests.cost_form.test_cost_form import road_form

TODAY = date(2026, 10, 3)
REF = {
    "state": "Testland", "source": "made up for tests", "years": [2024, 2026], "min_works": 30,
    "groups": {
        "STREET_LIGHT|solar": {"unit": "per light",
                               "state": {"n": 200, "p10": 20000, "median": 21000, "p90": 21500,
                                         "p98": 22000, "tight": True},
                               "districts": {"Alpha": {"n": 40, "p10": 30000, "median": 31000,
                                                       "p90": 31500, "p98": 32000,
                                                       "tight": True}}},
        "ROAD_CC": {"unit": "per metre",
                    "state": {"n": 500, "p10": 7000, "median": 7500, "p90": 8000, "p98": 8500,
                              "tight": True}, "districts": {}},
        "HIGH_MAST": {"unit": "per mast",
                      "state": {"n": 12, "p10": 1, "median": 2, "p90": 2, "p98": 2,
                                "tight": True}, "districts": {}},
    },
}


def ctx(ref=REF):
    return SimpleNamespace(as_of=TODAY, data={agent.AGENT: ref})


def light_form(lights=10, rate=21000, mp=None, district_note=None) -> dict:
    """A complete estimate for solar street lights: one line per light set, no charges, so the
    price per light is the rate."""
    f = road_form()
    f["work"].update(work_type="STREET_LIGHT", nature="installation",
                     description="Solar street lights along the main village road from the "
                                 "temple turning to the primary school, one every forty metres, "
                                 "where there is no light today and the road is dark at night.")
    site = f["sites"][0]
    site["location"].pop("end_lat"), site["location"].pop("end_lon")
    site["size"] = {"lights_nos": lights, "light_power": "solar_standalone", "led_w": 12,
                    "pole_height_m": 6, "pole_material": "gi", "panel_wp": 40,
                    "battery_wh": 300, "battery_type": "lifepo4", "warranty_years": 5}
    site["lines"] = [{"group": "materials", "item": "Solar street light set, complete",
                      "material_id": "none", "quantity": lights, "unit": "nos", "rate": rate,
                      "basis": "quotation"}]
    f["charges"] = {"contingency_percent": 0, "gst_percent": 0, "gst_amount": 0,
                    "labour_cess_amount": 0, "royalty_amount": 0, "other_fees_amount": 0}
    f["timing"].pop("sor_edition")
    total = lights * rate
    f["totals"] = {"total_as_per_document": total}
    f["recommendation"]["mp_amount"] = mp if mp is not None else total
    if mp is not None and abs(total - mp) / mp > 0.10:
        f["totals"]["reason_differs_from_mp"] = district_note or "Rates revised after survey."
    return f


def run(form, district="Beta", state="Testland", ref=REF):
    work = {"work_id": "W1", "state_name": state, "district_name": district, "cost_form": form}
    return agent.assess(work, ctx(ref))


def codes(r):
    return [f.code for f in r.findings]


# ---- when it does not apply --------------------------------------------------------------

def test_no_form_is_not_applicable():
    # T099: the record alone carries no size, and no price question from it was certain (0 of
    # the 15 a record-only check raised, data/trial/simple_certain_trial.py): never judged
    for work in ({"work_id": "W1"},
                 {"work_id": "W2", "state_name": "Testland", "district_name": "Alpha",
                  "work_type_code": "STREET_LIGHT", "amount": 9_000_000,
                  "description": "Installation of 10 solar street lights"}):
        r = agent.assess(work, ctx())
        assert r.status == Status.NOT_APPLICABLE and r.risk == 0 and not r.findings
        assert "no cost estimate form" in r.headline.lower()


def test_an_incomplete_form_is_not_assessed():
    f = light_form()
    del f["sites"][0]["size"]["led_w"]
    r = run(f)
    assert r.status == Status.NOT_ASSESSABLE and not r.findings
    assert "not a clean chit" in r.headline


# ---- price per unit of size ----------------------------------------------------------------

def test_a_normal_price_is_in_line():
    r = run(light_form())
    assert r.status == Status.ASSESSED and not r.findings
    assert r.verdict == "ESTIMATE_FITS_SIZE" and "in line" in r.headline


@pytest.mark.parametrize("lights", [2, 10, 50, 400])
def test_size_never_changes_the_answer(lights):
    """The same unit price at any number of lights: never asked about."""
    assert not run(light_form(lights=lights)).findings
    # a doubled price is asked about at every size, when the MP's amount agrees
    r = run(light_form(lights=lights, rate=42000, mp=lights * 21000))
    assert codes(r) == ["ESTIMATE_ABOVE_STANDARD_AND_MP"]


def test_a_high_price_above_the_mps_amount_is_asked_about():
    r = run(light_form(rate=42000, mp=210000))
    assert r.status == Status.ASSESSED and codes(r) == ["ESTIMATE_ABOVE_STANDARD_AND_MP"]
    text = r.findings[0].text
    assert "98 in 100" in text and "Beta" not in text and "Testland" in text
    assert "100% above the MP's recommended" in text and "LED 12 W" in text
    assert r.risk == pytest.approx(agent.PRICE_RISK)


def test_a_high_price_the_mp_also_recommended_is_only_a_note():
    r = run(light_form(rate=42000))           # the MP's amount equals the estimate
    assert not r.findings and "MP's amount was as high" in r.headline


def test_an_mps_low_guess_alone_is_never_a_question():
    r = run(light_form(rate=21000, mp=150000))   # 40% above the MP, normal price
    assert not r.findings
    assert any("not a question" in n for n in r.evidence["notes"])


def test_a_price_just_above_the_usual_top_is_left_alone():
    # 22,000 x 1.25 = 27,500: 27,000 per light is within the margin for a higher specification
    assert not run(light_form(rate=27000, mp=210000)).findings
    assert codes(run(light_form(rate=28000, mp=210000))) == ["ESTIMATE_ABOVE_STANDARD_AND_MP"]


def test_the_district_is_compared_with_its_own_works():
    # Alpha's standard light costs Rs 31,000: normal there, asked about in a district without
    # its own group (compared with the state)
    assert not run(light_form(rate=31000, mp=210000), district="Alpha").findings
    assert codes(run(light_form(rate=31000, mp=210000), district="Beta")) == [
        "ESTIMATE_ABOVE_STANDARD_AND_MP"]


def test_a_cheap_estimate_gets_a_note_not_a_question():
    r = run(light_form(rate=15000))
    assert not r.findings and "run short" in r.headline


# ---- what it never compares ------------------------------------------------------------------

def test_a_road_is_never_compared_per_metre():
    f = road_form()
    r = run(f)
    assert not any(f.code == "ESTIMATE_ABOVE_STANDARD_AND_MP" for f in r.findings)
    assert any("no width" in lim for lim in r.limitations)


def test_too_few_works_or_a_loose_group_means_could_not_check():
    f = light_form()
    f["work"]["work_type"] = "HIGH_MAST"
    f["sites"][0]["size"] = {"masts_nos": 1, "mast_height_m": 12.5, "lamps_per_mast": 6,
                             "lamp_w": 200, "mast_power": "grid", "cable_m": 50}
    r = run(f)
    assert r.status == Status.NOT_ASSESSABLE
    assert any("only 12 real works" in lim for lim in r.limitations)
    loose = copy.deepcopy(REF)
    loose["groups"]["STREET_LIGHT|solar"]["state"]["tight"] = False
    loose["groups"]["STREET_LIGHT|solar"]["districts"] = {}
    r = run(light_form(rate=42000, mp=210000), ref=loose)
    assert not r.findings and any("vary too much" in lim for lim in r.limitations)


def test_a_written_in_type_or_another_state_cannot_be_compared():
    f = light_form()
    f["work"].update(work_type="OTHER", other_type_name="Village haat platform")
    f["sites"][0]["size"] = {"size_measure": "platform area", "size_value": 120, "size_unit": "m2",
                             "specification": "Raised brick platform with a PCC top and a sheet "
                             "roof on steel columns, open on all sides"}
    assert run(f).status == Status.NOT_ASSESSABLE
    r = run(light_form(rate=42000, mp=210000), ref=None, state="Nowhere")
    assert r.status == Status.NOT_ASSESSABLE and not r.findings


# ---- quantities against the size --------------------------------------------------------------

def _with_line(f, item, material_id, quantity, unit="nos", rate=1000):
    f["sites"][0]["lines"].append({"group": "materials", "item": item, "material_id": material_id,
                                   "quantity": quantity, "unit": unit, "rate": rate,
                                   "basis": "quotation"})
    c = validate(f, today=TODAY)
    f["totals"]["total_as_per_document"] = c["computed"]["grand_total"]
    f["recommendation"]["mp_amount"] = c["computed"]["grand_total"]
    f["totals"].pop("reason_differs_from_mp", None)
    f["confirmed"] = [i["key"] for i in validate(f, today=TODAY)["issues"]
                      if i["level"] == "confirm"]
    return f


def test_a_confirmed_quantity_well_above_the_size_is_asked_about():
    r = run(_with_line(light_form(), "LiFePO4 battery 12.8 V", "battery", 13))
    assert codes(r) == ["MATERIAL_QUANTITY_ABOVE_SIZE"]
    assert "battery, 13 nos" in r.findings[0].text and "10 solar lights" in r.findings[0].text
    # 12 batteries for 10 lights: the form asked to confirm it, the engine leaves it
    assert not run(_with_line(light_form(), "LiFePO4 battery 12.8 V", "battery", 12)).findings


def test_poles_for_lights_on_existing_poles_are_asked_about():
    f = light_form()
    f["sites"][0]["size"]["pole_material"] = "existing_pole"
    r = run(_with_line(f, "GI pole 6 m", "pole", 10))
    assert codes(r) == ["MATERIAL_QUANTITY_ABOVE_SIZE"] and "existing poles" in r.findings[0].text


def test_a_suggested_but_unconfirmed_material_is_never_compared():
    f = _with_line(light_form(), "LiFePO4 battery 12.8 V", None, 20)
    assert f["confirmed"], "the form still asks the agency to confirm"
    assert not run(f).findings


def test_cement_beyond_the_slab_is_asked_about():
    f = road_form()
    f["sites"][0]["lines"][0]["material_id"] = "cement"
    assert not run(f).findings                       # 1,125 bags: under the 1,191 needed
    f["sites"][0]["lines"][0]["quantity"] = 2000     # 1.68 x what 140.6 m3 of M20 needs
    c = validate(f, today=TODAY)
    f["totals"]["total_as_per_document"] = c["computed"]["grand_total"]
    f["recommendation"]["mp_amount"] = c["computed"]["grand_total"]
    f["confirmed"] = [i["key"] for i in validate(f, today=TODAY)["issues"]
                      if i["level"] == "confirm"]
    r = run(f)
    assert codes(r) == ["MATERIAL_QUANTITY_ABOVE_SIZE"] and "M20" in r.findings[0].text


# ---- the real reference, the registry, and odd input --------------------------------------------

def test_jaunpur_solar_lights_against_the_real_uttar_pradesh_reference():
    ref = reference.load("Uttar Pradesh")
    assert ref and ref["groups"]["STREET_LIGHT|solar"]["districts"]["Jaunpur"]["n"] >= 30
    normal = run(light_form(rate=20896), district="Jaunpur", state="Uttar Pradesh", ref=None)
    assert normal.status == Status.ASSESSED and not normal.findings
    high = run(light_form(rate=40000, mp=208960), district="Jaunpur", state="Uttar Pradesh",
               ref=None)
    assert codes(high) == ["ESTIMATE_ABOVE_STANDARD_AND_MP"] and "Jaunpur" in high.findings[0].text
    assert not run(road_form(), district="Deoria", state="Uttar Pradesh", ref=None).findings


def test_it_is_the_cost_slot_and_the_old_cost_anomaly_is_retired():
    # T099 / T125: the first of the four agents, counted; its findings start at fusion v3's 1-in-4
    # prior, so none can queue a work alone until officers' verdicts are read
    spec = registry.by_id()[agent.AGENT]
    assert spec.weight == 0.25 and spec.assess is agent.assess and spec.name == "Cost"
    assert [e.id for e in registry.engines()][0] == agent.AGENT
    assert "statistical" not in registry.by_id() and "statistical" in registry.RETIRED
    from drishti.fusion import calibrated

    for code in ("ESTIMATE_ABOVE_STANDARD_AND_MP", "MATERIAL_QUANTITY_ABOVE_SIZE",
                 "ESTIMATE_ABOVE_FAIR_PRICE"):
        rate = calibrated.Reliability.load().rate(f"{agent.AGENT}:{code}")
        assert rate.basis == "prior" and rate.hit_rate == 0.25, code


def test_everything_it_says_is_plain_and_odd_forms_never_break_it():
    rng = random.Random(7)
    junk = [None, "", "x", -1, 0, 1e30, [], {}, True, "1,00,000"]
    forms = [light_form(rate=42000, mp=210000), road_form()]
    for _ in range(150):
        f = copy.deepcopy(rng.choice(forms))
        for _ in range(rng.randint(1, 4)):
            part = rng.choice([f["sites"][0]["size"], f["sites"][0]["lines"][0], f["work"],
                               f["recommendation"], f["totals"]])
            part[rng.choice(list(part))] = rng.choice(junk)
        r = run(f, district=rng.choice(["Alpha", "Beta", None]))
        json.dumps(r.evidence, default=str)
        for text in [r.headline, *r.limitations, *(x.text for x in r.findings)]:
            check_plain_language(text)
    for odd in (None, [], "x", {"sites": None}):
        assert run(odd).status in (Status.NOT_APPLICABLE, Status.NOT_ASSESSABLE)
