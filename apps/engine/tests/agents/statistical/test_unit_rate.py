import math

import pytest

from drishti.agents.statistical.unit_rate import UnitRateModel, road_check

MODEL = UnitRateModel(work_type_code="ROAD_CC", unit="m", n=4065, slope=0.6309,
                      intercept=4.5381, resid_sd=0.2772, anchor_low=4000.0,
                      anchor_high=6500.0, anchor_label="published rural CC road rates")


def test_fitted_price_is_zero_residual():
    predicted = MODEL.predict(1000.0)
    assert predicted == pytest.approx(10 ** (4.5381 + 0.6309 * 3.0))
    r = road_check(predicted, 1000.0, MODEL)
    assert r["z"] == pytest.approx(0.0, abs=1e-9)
    assert r["verdict"] == "UNIT_RATE_TYPICAL"


def test_three_times_the_fitted_price_is_not_flagged():
    r = road_check(3 * MODEL.predict(1000.0), 1000.0, MODEL)
    assert r["z"] == pytest.approx(math.log10(3) / 0.2772, abs=1e-6)
    assert r["verdict"] == "UNIT_RATE_TYPICAL"


def test_eight_times_is_flagged_with_the_per_metre_figure():
    amount = 8 * MODEL.predict(1000.0)
    r = road_check(amount, 1000.0, MODEL)
    assert r["z"] == pytest.approx(3.258, abs=1e-3)
    assert r["verdict"] == "UNIT_RATE_ABOVE"
    assert r["per_metre"] == pytest.approx(amount / 1000.0)
    assert r["anchor"] == (4000.0, 6500.0)
    assert r["above_anchor_x"] == pytest.approx(amount / 1000.0 / 6500.0)
