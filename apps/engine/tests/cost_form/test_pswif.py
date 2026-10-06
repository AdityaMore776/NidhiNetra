"""The website's work intelligence form (PSWIF v1.0) read by the agents (T134)."""

from __future__ import annotations

import random
from datetime import date

import pytest

from drishti.cost_form import pswif
from drishti.cost_form.validate import validate

TODAY = date(2026, 10, 2)
SCOPE = ("Construction of a 300 m long, 3.5 m wide cement concrete road, 150 mm thick in M20 over "
         "a 100 mm WBM base, from the Primary School gate to the Panchayat Bhawan in village "
         "Sikrara, replacing an earthen track that floods every monsoon.")


def road(**over) -> dict:
    """A complete filing as the website form exports it (flat field names)."""
    p = {
        "recommendation_ref": "WF-1", "mp_recommendation_date": "2026-06-10",
        "implementing_agency": "Rural Engineering Department", "work_title": "CC road",
        "recommendation_jurisdiction": "Normal constituency / permitted State jurisdiction",
        "sector": "Railways / roads / bridges / pathways", "work_type": "road",
        "work_nature": "New asset", "scope_of_work": SCOPE, "state": "Uttar Pradesh",
        "district": "Jaunpur", "block_tehsil": "Sikrara", "village_ward": "Sikrara",
        "land_ownership": "Local Government / Panchayat / ULB",
        "site_geometry_type": "Linear asset / alignment", "latitude": "25.7463",
        "longitude": "82.6837", "start_lat": "25.7463", "start_lon": "82.6837",
        "end_lat": "25.7490", "end_lon": "82.6837", "terrain": "Plain",
        "site_access": "Motorable all-weather", "road_subtype": "CC road",
        "road_length_m": "300", "road_width_m": "3.5", "pavement_thickness_mm": "150",
        "base_thickness_mm": "100", "road_material_grade": "M20",
        "existing_road_condition": "Earthen", "road_layer_spec": "WBM base",
        "sor_name": "UP PWD SoR", "sor_year": "2025-26", "tax_treatment": "Included in rates",
        "boq_desc_1": "Cement OPC 43 grade", "boq_unit_1": "bag", "boq_qty_1": "1100",
        "boq_rate_1": "380", "boq_source_1": "District recent rates",
        "boq_desc_2": "Coarse sand", "boq_unit_2": "Cum", "boq_qty_2": "75",
        "boq_rate_2": "1800", "boq_source_2": "District recent rates",
        "boq_desc_3": "Stone aggregate 20 mm", "boq_unit_3": "cu.m", "boq_qty_3": "150",
        "boq_rate_3": "2100", "boq_source_3": "District recent rates",
        "technical_estimate": "868000", "mp_recommended_amount": "900000",
        "sanction_decision": "Sanction", "sanction_date": "2026-07-01",
        "expected_start_date": "2026-07-15", "estimated_duration_days": "120",
        "no_land_acquisition": True, "no_om_funding": True, "certify_accuracy": True,
        "consent_agent_verification": True,
    }
    p.update(over)
    return p


def test_a_road_filing_becomes_the_form_the_agents_read():
    f = pswif.to_cost_form(road(), TODAY)
    assert f["work"]["work_type"] == "ROAD_CC" and f["work"]["nature"] == "new"
    site = f["sites"][0]
    # a linear work is pinned at both ends
    assert site["location"]["lat"] == 25.7463 and site["location"]["end_lat"] == 25.749
    assert site["size"] == {"length_m": 300, "width_m": 3.5, "cc_thickness_mm": 150,
                            "concrete_grade": "M20", "base_type": "wbm",
                            "base_thickness_mm": 100, "existing_surface": "earth"}
    assert [(ln["material_id"], ln["unit"], ln["basis"]) for ln in site["lines"]] == [
        ("cement", "bag", "market_rate"), ("sand", "m3", "market_rate"),
        ("aggregate", "m3", "market_rate")]
    assert f["timing"] == {"start_month": "2026-07", "duration_months": 3.94,
                           "sor_edition": "UP PWD SoR 2025-26"}
    assert f["charges"] == {"gst_percent": 0, "gst_amount": 0}
    v = validate(f, today=TODAY)
    assert v["ready"], v["issues"]
    assert v["computed"]["grand_total"] == 868000


def test_fields_the_website_form_never_asks_are_not_required():
    f = pswif.to_cost_form(road(), TODAY)
    assert validate(f, today=TODAY)["ready"]
    # the same content as the engine's own form: soil, drawings, contingency ... are missing
    own = {**f, "form_version": None}
    missing = {i["field"].split(".")[-1] for i in validate(own, today=TODAY)["issues"]
               if i["code"] == "required"}
    assert {"soil", "drawings", "contingency_percent", "estimate_month"} <= missing


def test_what_the_agency_did_not_write_is_still_required():
    f = pswif.to_cost_form(road(road_length_m="", scope_of_work="A road."), TODAY)
    fixes = {i["field"] for i in validate(f, today=TODAY)["issues"] if i["level"] == "fix"}
    assert "sites[0].size.length_m" in fixes and "work.description" in fixes


def test_a_line_check_counts_as_confirmed_only_with_a_written_justification():
    # 3,000 bags of cement for this road is far more than its size needs: the form asks to confirm
    heavy = road(boq_qty_1="3000", technical_estimate=str(868000 + 1900 * 380),
                 mp_recommended_amount="1590000")
    f = pswif.to_cost_form(heavy, TODAY)
    assert not validate(f, today=TODAY)["ready"]
    justified = pswif.to_cost_form({**heavy, "boq_just_1": "extra for the approach ramps"}, TODAY)
    assert any(k.startswith("more_than_size_needs:sites[0].lines[0]")
               for k in justified["confirmed"])
    assert validate(justified, today=TODAY)["ready"]


@pytest.mark.parametrize("over,code", [
    ({"work_type": "building", "work_title": "Community hall"}, "COMMUNITY_HALL"),
    ({"work_type": "building", "work_title": "Two classrooms for the school"}, "SCHOOL_BUILDING"),
    ({"work_type": "building", "sector": "Public health", "work_title": "Sub-centre"},
     "HEALTH_BUILDING"),
    ({"work_type": "energy", "energy_asset_type": "Solar street lights"}, "STREET_LIGHT"),
    ({"work_type": "energy", "energy_asset_type": "High mast"}, "HIGH_MAST"),
    ({"work_type": "water", "water_system_type": "Overhead tank"}, "WATER_TANK"),
    ({"work_type": "drainage", "work_title": "Covered drain"}, "DRAIN"),
    ({"work_type": "road", "road_subtype": "Paver block road"}, "FOOTPATH"),
    ({"work_type": "park"}, "PLAYGROUND"),
    ({"work_type": "other"}, "OTHER"),
    ({"work_type": ""}, "OTHER"),
])
def test_the_forms_types_map_to_the_engines(over, code):
    assert pswif.work_type(road(**{"scope_of_work": "", **over})) == code


def test_the_title_names_the_building_before_the_scopes_landmarks():
    hall = road(work_type="building", work_title="Community hall",
                scope_of_work="A hall for the village, opposite the primary school.")
    assert pswif.work_type(hall) == "COMMUNITY_HALL"


def test_solar_lights_size_and_battery_are_read():
    p = road(work_type="energy", energy_asset_type="Solar street lights", energy_quantity="10",
             watt_per_unit="12", pole_height_m="6", solar_wp="40",
             battery_spec="LiFePO4 25.6 V 12 Ah")
    size = pswif.to_cost_form(p, TODAY)["sites"][0]["size"]
    assert size == {"lights_nos": 10, "light_power": "solar_standalone", "led_w": 12,
                    "pole_height_m": 6, "panel_wp": 40, "battery_wh": pytest.approx(307.2),
                    "battery_type": "lifepo4"}


def test_a_continuation_names_its_earlier_work_and_answers_about_nearby_works():
    p = road(work_nature="Continuation / next phase", prior_work_id="WS/OLD/1",
             known_nearby_work_ids="WS/OLD/1, WS/OLD/2",
             nearby_work_relationship="Same asset, separate phase")
    f = pswif.to_cost_form(p, TODAY)
    assert f["work"]["nature"] == "continuation" and f["work"]["earlier_work_id"] == "WS/OLD/1"
    assert [r["earlier_work"] for r in f["earlier_works"]] == ["WS/OLD/1", "WS/OLD/2"]
    assert all(r["answer"] == "continues" for r in f["earlier_works"])


def test_the_work_record_carries_the_form_and_never_an_mp_name():
    w = pswif.to_work(road(mp_name="Shri Someone"), district_lgd="181", today=TODAY,
                      completed_date="2026-07-05", status="COMPLETED")
    assert w["work_id"] == "WF-1" and w["district_lgd"] == "181" and w["mp_name"] is None
    assert w["work_type_code"] == "ROAD_CC" and w["amount"] == 900000
    assert w["sanction_date"] == "2026-07-01" and w["status"] == "COMPLETED"
    assert w["cost_form"]["work"]["work_type"] == "ROAD_CC"
    assert w["source"] == "SCENARIO"
    # not sanctioned yet: a recommendation
    assert pswif.to_work(road(sanction_decision=""))["status"] == "RECOMMENDED"


def test_damaged_filings_never_break_the_adapter():
    rng = random.Random(4)
    junk = [None, "", "abc", "-1", "1e999", [], {}, True, 0, "  ", "२३", "9" * 40]
    keys = list(road()) + ["boq_desc_9", "boq_qty_9", "known_nearby_work_ids", "__meta"]
    for _ in range(300):
        p = {k: rng.choice(junk + [v]) for k, v in road().items()}
        for k in rng.sample(keys, 6):
            p[k] = rng.choice(junk)
        f = pswif.to_cost_form(p, TODAY)
        validate(f, today=TODAY)
        pswif.to_work(p)
    assert pswif.to_cost_form("not a dict")["work"]["work_type"] == "OTHER"


def test_the_rate_index_knows_which_agency_filed_and_when():
    from drishti.agents.cost_estimate import rates

    def filing(i, agency, filed="2026-06-14"):
        return pswif.to_work(road(recommendation_ref=f"WF-{i}", implementing_agency=agency,
                                  ida_received_date=filed), district_lgd="181", today=TODAY)

    same = [filing(i, "Rural Engineering Department") for i in range(5)]
    idx = rates.RateIndex.build(same)
    # five forms, but all from one agency: no district rate for anyone
    assert idx.district_rate("181", "cement", "pwd", "WF-X", date(2026, 7, 1)) is None
    mixed = same + [filing(5, "PWD Division 2"), filing(6, "Jal Nigam")]
    idx = rates.RateIndex.build(mixed)
    rate, forms, agencies = idx.district_rate("181", "cement", "zila panchayat", "WF-X",
                                              date(2026, 7, 1))
    assert rate == 380 and forms == 7 and agencies == 3
    # never the agency's own forms
    assert idx.district_rate("181", "cement", "rural engineering department", "WF-X",
                             date(2026, 7, 1)) is None
    # filed more than six months before: too old to count
    assert idx.district_rate("181", "cement", "zila panchayat", "WF-X", date(2027, 3, 1)) is None


# ---- v1.1: the labour schedule (T141) -------------------------------------------------------

LABOUR = {"lab_trade_1": "beldar", "lab_grade_1": "unskilled", "lab_workers_1": "8",
          "lab_days_1": "60", "lab_rate_1": "450", "lab_task_1": "Earthwork and carrying concrete",
          "lab_lines_1": "1-3", "lab_source_1": "Minimum wages notification",
          "lab_trade_2": "mason", "lab_grade_2": "skilled", "lab_workers_2": "4",
          "lab_days_2": "45", "lab_rate_2": "800", "lab_task_2": "Laying and finishing concrete",
          "lab_lines_2": "1, 3", "lab_source_2": "District recent rates"}
V11 = {"__meta": {"form_version": "PSWIF v1.1"}}


def test_the_labour_schedule_becomes_one_labour_line_per_trade():
    f = pswif.to_cost_form(road(**LABOUR, **V11, technical_estimate="1228000",
                                mp_recommended_amount="1250000"), TODAY)
    assert f["form_version"] == "PSWIF v1.1"
    lab = [ln for ln in f["sites"][0]["lines"] if ln["group"] == "labour"]
    assert [(ln["material_id"], ln["workers"], ln["days"], ln["rate"], ln["for_lines"])
            for ln in lab] == [("labour_beldar", 8, 60, 450, [1, 2, 3]),
                               ("labour_mason", 4, 45, 800, [1, 3])]
    assert lab[0]["basis"] == "other" and lab[0]["basis_other"] == "Minimum wages notification"
    v = validate(f, today=TODAY)
    assert v["ready"], [i for i in v["issues"] if i["level"] == "fix"]
    assert v["computed"]["grand_total"] == 868000 + 8 * 60 * 450 + 4 * 45 * 800


def test_a_filing_shows_v11_by_its_labour_rows():
    assert pswif.version(road(**LABOUR)) == "PSWIF v1.1"
    assert pswif.version(road()) == "PSWIF v1.0"


def test_a_v11_trade_not_on_the_list_needs_its_grade():
    rows = {"lab_trade_1": "other", "lab_name_1": "Stone carver", "lab_workers_1": "2",
            "lab_days_1": "10", "lab_rate_1": "900", "lab_task_1": "Carving the plaque stone",
            "lab_source_1": "Approved quotation"}
    f = pswif.to_cost_form(road(**rows, **V11, technical_estimate="886000"), TODAY)
    assert "labour_grade_needed" in {i["code"] for i in validate(f, today=TODAY)["issues"]}
    f = pswif.to_cost_form(road(**rows, lab_grade_1="skilled", **V11,
                                technical_estimate="886000"), TODAY)
    assert validate(f, today=TODAY)["ready"]


def test_a_v11_composite_line_cannot_be_paid_again_by_a_labour_row():
    f = pswif.to_cost_form(road(**LABOUR, **V11, boq_inclab_3=True,
                                technical_estimate="1228000"), TODAY)
    assert "labour_paid_twice" in {i["code"] for i in validate(f, today=TODAY)["issues"]}


def test_v11_labour_left_among_the_boq_lines_is_asked_to_move_and_still_priced_as_its_trade():
    f = pswif.to_cost_form(road(boq_desc_4="Mason", boq_unit_4="day", boq_qty_4="100",
                                boq_rate_4="800", boq_source_4="District recent rates",
                                technical_estimate="948000", **V11), TODAY)
    ln = f["sites"][0]["lines"][3]
    assert ln["group"] == "materials" and ln["material_id"] == "labour_mason"
    assert "labour_outside_section" in {i["code"] for i in validate(f, today=TODAY)["issues"]}


def test_a_machine_hired_with_its_operator_by_the_hour_is_a_machine():
    for over in ({}, V11):
        f = pswif.to_cost_form(road(boq_desc_4="JCB with operator", boq_unit_4="hr",
                                    boq_qty_4="40", boq_rate_4="1200",
                                    boq_source_4="Approved quotation",
                                    technical_estimate="916000", **over), TODAY)
        ln = f["sites"][0]["lines"][3]
        assert ln["group"] == "machinery" and "material_id" not in ln
        assert validate(f, today=TODAY)["ready"]


def test_a_v10_export_keeps_its_labour_among_the_boq_lines():
    f = pswif.to_cost_form(road(boq_desc_4="Mason", boq_unit_4="day", boq_qty_4="100",
                                boq_rate_4="800", boq_source_4="District recent rates",
                                technical_estimate="948000"), TODAY)
    assert f["sites"][0]["lines"][3]["group"] == "labour"
    assert validate(f, today=TODAY)["ready"]


@pytest.mark.parametrize("text,expected", [
    ("1, 3-5", [1, 3, 4, 5]), ("Lines 1 to 4", [1, 2, 3, 4]), ("BOQ 2 & 6", [2, 6]),
    ("२, ३", [2, 3]), ("all", ["all"]), ("", None),
])
def test_the_lines_a_labour_row_works_on_are_read_as_numbers(text, expected):
    assert pswif.line_numbers(text) == expected
