"""Cost (T144): quantities held to the work's own size for more of what MPLADS builds.

A CC road's stone by its concrete mix (as its cement and sand already were), a water pipeline's
pipes by its length, and solar lights bought by the watt or watt-hour by what each light carries.
Stone named for a road's base course is the base, not the concrete's aggregate."""

from __future__ import annotations

import pytest

from drishti.agents.cost_estimate import whole
from drishti.cost_form import materials, norms, pswif
from drishti.cost_form.validate import validate
from tests.agents.cost_estimate.test_whole_estimate import codes, run
from tests.cost_form.test_pswif import TODAY, road

SIZE = {"length_m": 300, "width_m": 3.5, "cc_thickness_mm": 150, "concrete_grade": "M20"}
VOL = 300 * 3.5 * 0.15


BASE_STONE = ["Stone aggregate 40 mm for WBM", "Coarse aggregate 63 mm for WBM base",
              "Stone metal for WMM", "Aggregate for GSB", "Aggregate for sub-base",
              "40mm ballast for base course"]
CONCRETE_STONE = ["Stone aggregate 20 mm", "20 mm gitti", "Coarse aggregate for PCC",
                  "Coarse aggregate 40 mm for PCC base", "Stone chips for concrete"]


@pytest.mark.parametrize("text", BASE_STONE)
def test_stone_named_for_a_base_course_is_the_base(text):
    assert materials.match(text) == "granular_base"


@pytest.mark.parametrize("text", CONCRETE_STONE)
def test_concrete_aggregate_stays_aggregate(text):
    assert materials.match(text) == "aggregate"


def test_a_roads_stone_follows_its_mix_with_room_for_the_analysis_of_rates():
    need = {n["material"]: n for n in norms.needs("ROAD_CC", {**SIZE, "base_type": "none"})}
    # M20 = 1:1.5:3: 1.54 x 3 / 5.5 = 0.84 m3 of dry stone per m3; +15%
    assert need["aggregate"]["needed"] == pytest.approx(VOL * 0.84 * 1.15, rel=0.01)
    # honest estimates carry 0.85-0.90 m3 per m3 (the analysis of rates): under the need
    assert 0.90 * VOL < need["aggregate"]["needed"]
    assert not need["aggregate"]["stone_base"]


@pytest.mark.parametrize("base", ["pcc"])
def test_stone_is_not_checked_when_a_pcc_base_shares_it(base):
    mats = {n["material"] for n in norms.needs("ROAD_CC", {**SIZE, "base_type": base})}
    assert "aggregate" not in mats and "cement" not in mats


def _lines(*rows):
    return [(i, mid, q, unit, text) for i, (mid, q, unit, text) in enumerate(rows)]


def test_under_a_stone_base_only_the_slabs_stone_is_counted_unless_the_base_has_its_own_line():
    size = {**SIZE, "base_type": "wbm"}
    slab = ("aggregate", 140, "m3", "Stone aggregate 20 mm")
    base_stone = ("aggregate", 130, "m3", "Stone aggregate 63 mm")   # the WBM's metal, unnamed
    q = next(x for x in norms.check("ROAD_CC", size, _lines(slab, base_stone))
             if x["material"] == "aggregate")
    assert q["quantity"] == 140 and q["lines"] == [0]
    # with the base on a line of its own, every aggregate line is the slab's
    q = next(x for x in norms.check("ROAD_CC", size, _lines(
        slab, ("aggregate", 130, "m3", "Stone aggregate"), ("granular_base", 110, "m3", "WBM")))
        if x["material"] == "aggregate")
    assert q["quantity"] == 270 and q["ratio"] > 1.5


def test_a_pipelines_pipes_are_its_length_and_its_house_connections():
    size = {"length_m": 600, "house_connections_nos": 20}
    need = norms.needs("WATER_SUPPLY", size)[0]
    assert need["material"] == "pipe"
    assert need["needed"] == pytest.approx((600 + 20 * 20) * 1.10)
    honest = norms.check("WATER_SUPPLY", size, _lines(("pipe", 630, "m", "HDPE pipe 90 mm"),
                                                      ("pipe", 240, "m", "HDPE pipe 20 mm")))
    assert honest[0]["ratio"] < 1.0
    padded = norms.check("WATER_SUPPLY", size, _lines(("pipe", 1890, "m", "HDPE pipe 90 mm")))
    assert padded[0]["ratio"] > 1.25
    # pipes counted in lengths of 6 m (nos) are not converted, never guessed
    assert norms.check("WATER_SUPPLY", size, _lines(("pipe", 105, "nos", "HDPE pipe"))) == []


@pytest.mark.parametrize("text,service", [
    ("HDPE pipe 20 mm for house connections", True), ("GI pipe 25mm", True), ("FHTC pipe", True),
    ("Pipe for house connections", True), ("HDPE pipe 110 mm PE100 PN6", False),
    ("HDPE pipe", False), ("DI pipe 150 mm for connections main", False),
    ("HDPE pipes, 110 mm main and 20 mm house connections", False)])
def test_a_house_connections_pipe_is_told_by_its_width_or_its_name(text, service):
    assert norms.for_service(text) is service


def test_with_the_connections_itemised_the_main_alone_is_held_to_the_length():
    size = {"length_m": 600, "house_connections_nos": 80}
    taps = ("pipe", 900, "m", "HDPE pipe 20 mm for house connections")   # never judged
    honest = norms.check("WATER_SUPPLY", size, _lines(("pipe", 615, "m", "HDPE pipe 110 mm"), taps))
    assert honest[0]["needed"] == pytest.approx(660) and honest[0]["lines"] == [0]
    padded = norms.check("WATER_SUPPLY", size, _lines(("pipe", 920, "m", "HDPE pipe 110 mm"), taps))
    assert padded[0]["ratio"] > 1.25
    # every pipe on one line: the connections' allowance stays, so honest is never asked
    one = norms.check("WATER_SUPPLY", size, _lines(("pipe", 1515, "m", "HDPE pipes, all sizes")))
    assert one[0]["needed"] == pytest.approx((600 + 80 * 20) * 1.10) and one[0]["ratio"] < 1.0


def test_solar_lights_bought_by_capacity_are_held_to_what_each_light_carries():
    size = {"lights_nos": 10, "light_power": "solar_standalone", "panel_wp": 40,
            "battery_wh": 307.2}
    got = {(q["material"], q["unit"]): q for q in norms.check("STREET_LIGHT", size, _lines(
        ("solar_panel", 800, "wp", "Solar PV module"), ("battery", 3.1, "kwh", "LiFePO4 battery"),
        ("led_luminaire", 10, "nos", "LED luminaire 12 W")))}
    assert got[("solar_panel", "wp")]["ratio"] == pytest.approx(800 / (400 * 1.05))
    assert got[("battery", "wh")]["quantity"] == pytest.approx(3100)
    assert got[("battery", "wh")]["ratio"] < 1.0
    # a count line is still held to the count
    count = norms.check("STREET_LIGHT", size, _lines(("battery", 20, "nos", "Battery")))
    assert count[0]["unit"] == "nos" and count[0]["ratio"] == 2.0


def test_a_capacity_need_never_prices_count_lines_in_the_whole_estimate():
    # the whole estimate shares a need over the lines in the material's first unit only
    size = {"lights_nos": 10, "light_power": "solar_standalone", "panel_wp": 40,
            "battery_wh": 300}
    needs = [n for n in norms.needs("STREET_LIGHT", size) if n["material"] == "battery"]
    assert {n.get("unit") for n in needs} == {None, "wh"}


def _confirm_all(f: dict) -> dict:
    f["confirmed"] = [i["key"] for i in validate(f, today=TODAY)["issues"]
                      if i["level"] == "confirm"]
    return f


def test_the_honest_road_filing_has_room_for_its_stone():
    v = validate(pswif.to_cost_form(road(), TODAY), today=TODAY)
    assert not any(i["code"] == "more_than_size_needs" and "aggregate" in i["field"]
                   for i in v["issues"])
    assert "MATERIAL_QUANTITY_ABOVE_SIZE" not in codes(run(pswif.to_cost_form(road(), TODAY)))


def stone(qty: int) -> dict:
    """The test road with `qty` m3 of 20 mm stone, its totals and the MP's amount to match."""
    total = str(1100 * 380 + 75 * 1800 + qty * 2100)
    return road(boq_qty_3=str(qty), technical_estimate=total, mp_recommended_amount=total)


def test_twice_the_stone_a_road_can_use_is_asked_once_confirmed():
    f = pswif.to_cost_form(stone(300), TODAY)
    v = validate(f, today=TODAY)
    assert any(i["code"] == "more_than_size_needs" for i in v["issues"])
    r = run(_confirm_all(f))
    q = next(x for x in r.findings if x.code == "MATERIAL_QUANTITY_ABOVE_SIZE")
    assert q.evidence["material"] == "aggregate" and q.evidence["ratio"] > 1.25
    # a little over (within 25%) is confirmed by the agency, never asked
    r = run(_confirm_all(pswif.to_cost_form(stone(170), TODAY)))
    assert "MATERIAL_QUANTITY_ABOVE_SIZE" not in codes(r)


def test_the_bases_stone_named_as_such_is_never_counted_as_the_slabs():
    p = road(boq_desc_4="Stone aggregate 63 mm for WBM", boq_unit_4="cu.m", boq_qty_4="125",
             boq_rate_4="1650", boq_source_4="District recent rates")
    f = pswif.to_cost_form(p, TODAY)
    assert f["sites"][0]["lines"][3]["material_id"] == "granular_base"
    assert "MATERIAL_QUANTITY_ABOVE_SIZE" not in codes(run(_confirm_all(f)))


def test_the_whole_estimate_holds_only_the_slabs_stone_to_the_slabs_need():
    # a WBM road whose base metal is an aggregate line named by its size alone
    p = road(boq_desc_4="Stone aggregate 63 mm", boq_unit_4="cu.m", boq_qty_4="125",
             boq_rate_4="1650", boq_source_4="District recent rates")
    f = _confirm_all(pswif.to_cost_form(p, TODAY))
    w = whole.judge(f, validate(f, today=TODAY)["computed"], "ROAD_CC", None, None, "T|BETA",
                    "agency-A", "W1", TODAY, "Testland")
    held = {x.index: x.needed for x in w.lines if x.material == "aggregate"}
    assert held.get(2) is not None          # the 20 mm line: the slab's
    assert held.get(3) is None               # the 63 mm line: not held to the slab's need


def test_a_road_over_a_stone_base_must_itemise_its_stone():
    size = {**SIZE, "base_type": "wbm", "base_thickness_mm": 100}
    one = _lines(("aggregate", 260, "m3", "Stone aggregate"))
    assert norms.stone_not_itemised("ROAD_CC", size, one) == 0
    # itemised either way: the slab's stone by its size, or the base on its own line
    assert norms.stone_not_itemised("ROAD_CC", size, _lines(
        ("aggregate", 140, "m3", "Stone aggregate 20 mm"))) is None
    assert norms.stone_not_itemised("ROAD_CC", size, _lines(
        ("aggregate", 140, "m3", "Stone aggregate"), ("granular_base", 120, "m3", "WBM"))) is None
    # the base's stone sized as such (63 mm) beside the slab's (20 mm): told apart by their sizes
    assert norms.stone_not_itemised("ROAD_CC", size, _lines(
        ("aggregate", 140, "m3", "Stone aggregate 20 mm"),
        ("aggregate", 125, "m3", "Stone aggregate 63 mm"))) is None
    # no new stone base, nothing to tell apart
    assert norms.stone_not_itemised("ROAD_CC", {**SIZE, "base_type": "brick_soling",
                                                 "base_thickness_mm": 75}, one) is None
    p = road(boq_desc_3="Stone aggregate")
    v = validate(pswif.to_cost_form(p, TODAY), today=TODAY)
    assert any(i["code"] == "stone_not_itemised" and i["level"] == "fix" for i in v["issues"])


@pytest.mark.parametrize("text,slab", [
    ("Stone aggregate 20 mm", True), ("Kapchi 20", True), ("Aggregate 12.5", True),
    ("Aggregate for M20 concrete", True), ("Gitti 40", False), ("Stone aggregate", False),
    ("Stone aggregate 63 mm", False)])
def test_stone_written_for_the_slab_is_told_by_its_size_or_its_use(text, slab):
    assert norms.for_slab(text) is slab
