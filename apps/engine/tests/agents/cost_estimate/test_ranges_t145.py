"""Cost (T145): what a quantity or a price should be is a range, never one figure.

The owner (6 Oct 2026): the cost "size prediction" or "price prediction" "should give a range and
not just 'should be quantity 1334'". A quantity's range runs from the standard amount for the size
to the same with the room honest estimates carry; a rate's from the lowest to the highest rate
other agencies here charge (a schedule's rate is its own range); the whole estimate's fair price
from those lowest to those highest rates."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from drishti.agents.cost_estimate import agent, labour, rates
from drishti.cost_form import catalog, norms
from tests.agents.cost_estimate.test_whole_estimate import TODAY, _others, priced

SIZE = {"length_m": 300, "width_m": 3.5, "cc_thickness_mm": 150, "concrete_grade": "M20",
        "base_type": "wbm"}


def test_a_range_reads_as_an_officer_reads_it():
    assert catalog.range_text(1270.2, 1333.6, "bag") == "1,270 to 1,334 bags"
    assert catalog.range_text(10, 10, "nos") == "10"            # a count is one figure
    assert catalog.range_text(None, 83.3, "m3").startswith("83")


def test_every_need_runs_from_the_standard_amount_to_it_with_room():
    got = {n["material"]: n for n in norms.needs("ROAD_CC", SIZE)}
    vol = 300 * 3.5 * 0.15
    assert got["cement"]["low"] == pytest.approx(vol * 8.06, rel=0.01)       # the mix alone
    assert got["cement"]["needed"] == pytest.approx(got["cement"]["low"] * 1.05)
    assert got["sand"]["low"] < got["sand"]["needed"]
    assert got["aggregate"]["low"] == pytest.approx(vol * 0.84, rel=0.01)
    lights = {(n["material"], n.get("unit")): n for n in norms.needs(
        "STREET_LIGHT", {"lights_nos": 10, "light_power": "solar_standalone", "panel_wp": 40})}
    assert lights[("solar_panel", None)]["low"] == lights[("solar_panel", None)]["needed"] == 10
    assert lights[("solar_panel", "wp")]["low"] == 400


def test_the_check_carries_the_range_and_the_honest_figure_falls_in_it():
    q = norms.check("ROAD_CC", SIZE, [(0, "cement", 1300, "bag", "Cement OPC 43")])[0]
    assert q["low"] <= 1300 <= q["needed"]


def test_a_rate_from_other_agencies_carries_their_lowest_and_highest():
    works = _others(4, 2, 1.0) + _others(4, 2, 1.2)
    for k, w in enumerate(works[4:]):                  # two more agencies at +20%
        w["work_id"], w["cost_form_meta"]["saved_by"] = f"P{k}", f"agency-hi-{k % 2}"
    idx = rates.RateIndex.build(works)
    found, _gap = idx.price("T|BETA", None, "sand", "agency-X", "W1", TODAY)
    rate, _level, _where, low, high = found
    assert low < rate < high and high == pytest.approx(low * 1.2, rel=0.02)


def test_a_schedule_rate_is_its_own_range():
    fair = rates.Fair(400.0, "sor", "the SoR")
    assert fair.low == fair.high == 400.0


def _run(form, index):
    work = {"work_id": "W1", "state_name": "Testland", "district_name": "Beta",
            "district_lgd": "T|BETA", "cost_form": form, "cost_form_meta": {"saved_by": "agency-A"}}
    return agent.assess(work, SimpleNamespace(as_of=TODAY, data={"sor": None, "rates": index}))


def test_the_whole_estimates_fair_price_is_a_range():
    works = _others(4, 2, 0.95) + _others(4, 2, 1.05)
    for k, w in enumerate(works[4:]):
        w["work_id"], w["cost_form_meta"]["saved_by"] = f"P{k}", f"agency-hi-{k % 2}"
    r = _run(priced(), rates.RateIndex.build(works))
    w = r.evidence["whole"]
    assert w["fair_low"] < w["fair_total"] < w["fair_high"]
    note = " ".join(r.evidence.get("notes") or [])
    assert "at the lowest and highest rates other agencies here charge" in note


def test_a_labour_rate_question_names_what_other_agencies_pay():
    row = labour.Row(0, 0, "labour_mason", "skilled", "Mason", 1800.0, 118.0, 4, 29.5,
                     fair=750.0, margin=2.0, level="trade", where="the district",
                     fair_low=700.0, fair_high=800.0)
    text = labour.rate_sentence(labour.Labour(rows=[row], asked=[row]))
    assert "other agencies pay Rs 700 to Rs 800 a day" in text
    assert row.to_json()["fair_low"] == 700.0
