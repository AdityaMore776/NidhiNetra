from datetime import date

import pytest

from drishti.agents.contract import Status
from drishti.agents.statistical.agent import assess
from drishti.agents.statistical.cohort import StatsStore

AS_OF = date(2026, 5, 26)


@pytest.fixture()
def stats():
    return StatsStore.from_rows(
        cohorts=[{"level": "type_district", "work_type_code": "ROAD_CC", "key": "639",
                  "n": 709, "p10": 4.9, "p50": 5.204, "p90": 5.5, "sd": 0.20}],
        durations=[{"work_type_code": "ROAD_CC", "n": 900, "p50": 380, "p90": 700,
                    "p98": 800}],
        unit_models=[{"work_type_code": "ROAD_CC", "unit": "m", "n": 4065, "slope": 0.6309,
                      "intercept": 4.5381, "resid_sd": 0.2772, "anchor_low": 4000.0,
                      "anchor_high": 6500.0, "anchor_label": "published rural CC road rates"}])


def _work(**kw):
    w = {"work_id": "W1", "work_type_code": "ROAD_CC", "district_lgd": "639",
         "district_name": "Anand", "state_lgd": "24", "amount": 160_000.0,
         "description": "Construction of CC road in village Bijdih", "status": "SANCTIONED",
         "recommended_date": date(2025, 11, 1), "quantity": None, "quantity_unit": None,
         "is_outside_constituency": False}
    w.update(kw)
    return w


def test_typical_cost(stats):
    r = assess(_work(), stats, AS_OF)
    assert r.status == Status.ASSESSED and r.verdict == "COST_TYPICAL" and r.risk == 0.0
    assert "usual range" in r.headline and "Anand" in r.headline


def test_costly_work_carries_the_decks_comparison_table(stats):
    r = assess(_work(amount=1_099_108.0), stats, AS_OF)
    assert r.verdict == "COST_ABOVE_PEERS"
    assert 0.30 <= r.risk <= 0.45 and r.hard is False
    row = r.evidence["comparison"][0]
    assert row["metric"] == "Total cost"
    assert row["this_work"] == 1_099_108.0
    assert row["typical_low"] == pytest.approx(10 ** 4.9)
    assert row["typical_high"] == pytest.approx(10 ** 5.5)
    assert row["deviation_pct"] == pytest.approx((1_099_108 / 10 ** 5.204 - 1) * 100)
    assert "6.9x" in r.headline and "709" in r.headline
    assert r.evidence["cohort"]["level"] == "type_district"


def test_bulk_order_is_explained_not_flagged_as_mispricing(stats):
    r = assess(_work(amount=5_000_000.0, description="Installation of 60 Highmast lights"),
               stats, AS_OF)
    assert r.verdict == "BUNDLED_SANCTION" and r.risk == pytest.approx(0.15)


def test_road_length_adds_a_per_metre_row(stats):
    amount = 8 * 10 ** (4.5381 + 0.6309 * 3)       # 8x the fitted price for 1,000 m
    r = assess(_work(amount=amount, description="CC road 1000 mtr in village X"), stats, AS_OF)
    metrics = [row["metric"] for row in r.evidence["comparison"]]
    assert "Cost per metre" in metrics
    assert any(f.code == "UNIT_RATE_ABOVE" for f in r.findings)


def test_delay_is_a_soft_finding(stats):
    r = assess(_work(recommended_date=date(2023, 1, 1)), stats, AS_OF)
    assert any(f.code == "DELAYED" and f.risk == pytest.approx(0.20) for f in r.findings)
    assert r.risk == pytest.approx(0.20)


def test_outside_constituency_ceiling_is_the_only_hard_signal(stats):
    r = assess(_work(amount=3_000_000.0, is_outside_constituency=True), stats, AS_OF)
    f = next(f for f in r.findings if f.code == "CEILING_BREACH")
    assert f.hard and f.risk == pytest.approx(0.70)
    assert "para 2.9" in f.text
    assert r.hard


@pytest.mark.parametrize("kw,reason", [({"amount": None}, "amount"),
                                       ({"amount": 0}, "amount"),
                                       ({"work_type_code": None}, "type"),
                                       ({"work_type_code": "BRIDGE"}, "20")])
def test_not_assessable_is_said_out_loud(stats, kw, reason):
    r = assess(_work(**kw), stats, AS_OF)
    assert r.status == Status.NOT_ASSESSABLE and r.risk == 0.0
    assert reason in r.headline


def test_money_ahead_of_site_waits_for_site_progress(stats):
    r = assess(_work(), stats, AS_OF)
    assert any("Site Progress" in lim for lim in r.limitations)


def test_countable_items_admit_the_bulk_explanation():
    stats = StatsStore.from_rows(
        cohorts=[{"level": "type_district", "work_type_code": "STREET_LIGHT", "key": "639",
                  "n": 466, "p10": 4.0, "p50": 4.2, "p90": 4.5, "sd": 0.2}],
        durations=[], unit_models=[])
    work = _work(work_type_code="STREET_LIGHT", amount=2_000_000.0,
                 description="Supply and installation of LED lights for the block")
    r = assess(work, stats, AS_OF)
    assert r.verdict == "COST_ABOVE_PEERS"
    assert "many units" in r.headline
    assert r.confidence == pytest.approx(0.6)


def test_a_road_stated_in_kilometres_gets_a_per_metre_row(stats):
    r = assess(_work(amount=29_495_741.0,
                     description="Laying of 1.2 Km Black Top Road in Gangaram Village"),
               stats, AS_OF)
    row = next(x for x in r.evidence["comparison"] if x["metric"] == "Cost per metre")
    assert row["this_work"] == pytest.approx(29_495_741.0 / 1200.0)
