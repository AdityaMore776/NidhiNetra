import math

import pytest

from drishti.agents.statistical.band import (Cohort, cost_risk, cost_verdict, shrunk_sd,
                                              zscore)


def _cohort():
    sd = shrunk_sd(n=100, p10=5.0, p90=5.6, sd_type=0.3)
    return Cohort(level="type_district", n=100, p10=5.0, p50=5.3, p90=5.6, sd=sd)


def test_shrunk_sd_matches_the_measured_formula():
    # sd_raw = 0.6 / 2.563 = 0.23410; (100*0.23410 + 12*0.3) / 112
    assert shrunk_sd(n=100, p10=5.0, p90=5.6, sd_type=0.3) == pytest.approx(0.24116, abs=1e-4)


def test_sd_never_falls_below_the_floor():
    assert shrunk_sd(n=500, p10=5.0, p90=5.0, sd_type=0.0) == 0.10


def test_zscore_is_in_log10_rupees():
    c = _cohort()
    assert zscore(10 ** 6.1, c) == pytest.approx(3.317, abs=1e-3)
    assert zscore(10 ** 4.5, c) == pytest.approx(-3.317, abs=1e-3)
    assert zscore(10 ** 5.3, c) == pytest.approx(0.0, abs=1e-9)


def test_verdicts():
    assert cost_verdict(3.32, bundle=False) == "COST_ABOVE_PEERS"
    assert cost_verdict(-3.32, bundle=False) == "COST_BELOW_PEERS"
    assert cost_verdict(0.5, bundle=False) == "COST_TYPICAL"
    assert cost_verdict(0.5, bundle=True) == "COST_TYPICAL"  # inside the band a list is fine
    assert cost_verdict(4.0, bundle=True) == "BUNDLED_SANCTION"
    assert cost_verdict(-4.0, bundle=True) == "BUNDLED_SANCTION"


@pytest.mark.parametrize("z,risk", [(2.9, 0.0), (3.0, 0.30), (3.5, 0.35), (4.0, 0.40),
                                    (5.0, 0.45), (40.0, 0.45)])
def test_cost_risk_is_soft_and_capped(z, risk):
    assert cost_risk(z) == pytest.approx(risk)


def test_below_band_and_bundles_carry_small_risk():
    assert cost_risk(-3.5, verdict="COST_BELOW_PEERS") == pytest.approx(0.10)
    assert cost_risk(6.0, verdict="BUNDLED_SANCTION") == pytest.approx(0.15)


def test_typical_range_in_rupees():
    lo, hi = _cohort().range_inr()
    assert lo == pytest.approx(10 ** 5.0) and hi == pytest.approx(10 ** 5.6)
    assert math.isclose(_cohort().median_inr(), 10 ** 5.3)
