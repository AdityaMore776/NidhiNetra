"""Cost (T136, the robustness loop's round 6): what got past it and how it stays caught.

Sand from the mix (twice the sand went unasked), a line no reader prices raised eightfold (an
equipment-hire line hid Rs 5.5 lakh), rates written the way people write money ("Rs 464/-" read as
no rate), and a form whose lines carry no rate passing as complete."""

from __future__ import annotations

import pytest

from drishti.agents.cost_estimate import whole
from drishti.cost_form import norms, pswif
from drishti.cost_form.validate import validate
from tests.cost_form.test_pswif import TODAY, road

SIZE = {"length_m": 300, "width_m": 3.5, "cc_thickness_mm": 150, "concrete_grade": "M20",
        "base_type": "wbm"}


def test_sand_follows_the_nominal_mix_with_room_for_bulking():
    need = {n["material"]: n["needed"] for n in norms.needs("ROAD_CC", SIZE)}
    vol = 300 * 3.5 * 0.15
    # M20 = 1:1.5:3: 1.54 x 1.5 / 5.5 = 0.42 m3 of dry sand per m3; +20% bulking, +5%
    assert need["sand"] == pytest.approx(vol * 0.42 * 1.20 * 1.05, rel=0.01)
    # honest estimates carry 0.44-0.47 m3 per m3: under the need, so the form asks nothing
    assert 0.47 * vol < need["sand"]


@pytest.mark.parametrize("base", ["gsb", "brick_soling", "sand_bed", "pcc"])
def test_sand_is_not_checked_under_a_base_that_takes_sand(base):
    mats = {n["material"] for n in norms.needs("ROAD_CC", {**SIZE, "base_type": base})}
    assert "sand" not in mats


def test_money_written_by_hand_is_read():
    for text, value in (("Rs 464/-", 464.0), ("₹ 380", 380.0), ("INR 2,100.00", 2100.0),
                        ("Rs. 1,250", 1250.0), ("४६४", 464.0), (" 12 ", 12.0)):
        assert pswif._n(text) == value
    for junk in ("abc", "rs", "nan", "inf", "", None, True):
        assert pswif._n(junk) is None


def test_a_line_without_a_readable_rate_is_a_fix_never_ready():
    p = road(boq_rate_1="see attached", boq_rate_2="as per quote")
    v = validate(pswif.to_cost_form(p, TODAY), today=TODAY)
    assert not v["ready"]
    assert sum(1 for i in v["issues"] if i["code"] == "line_incomplete") == 2


def _form(extra_lines):
    f = pswif.to_cost_form(road(), TODAY)
    f["sites"][0]["lines"] += extra_lines
    return f


def test_items_no_reader_knows_beyond_their_share_are_not_shown_fair():
    hire = {"group": "other", "item": "Concrete mixer and vibrator hire", "unit": "day",
            "quantity": 250.0, "rate": 2500.0}
    lines_total = sum(ln["quantity"] * ln["rate"] for ln in _form([hire])["sites"][0]["lines"])
    extra = whole.unexplained(_form([hire]), {"lines_total": lines_total}, civil=True)
    assert extra["unread_items"] == pytest.approx(250 * 2500 - whole.UNREAD_SHARE * lines_total)
    small = dict(hire, quantity=10.0)
    lines_total = sum(ln["quantity"] * ln["rate"] for ln in _form([small])["sites"][0]["lines"])
    assert "unread_items" not in whole.unexplained(_form([small]), {"lines_total": lines_total},
                                                   civil=True)
    # a building (no size norms: not "civil") is never held to it
    assert "unread_items" not in whole.unexplained(_form([hire]), {"lines_total": 1e6},
                                                   civil=False)
