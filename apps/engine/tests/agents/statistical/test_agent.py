from datetime import date

import pytest

from drishti.agents.contract import Status
from drishti.agents.statistical import agent as cost
from drishti.agents.statistical.agent import above_risk, assess
from drishti.agents.statistical.cohort import StatsStore

AS_OF = date(2026, 5, 26)


def _c(level, wtype, key, n, p10, p50, p90, sd=0.2):
    return {"level": level, "work_type_code": wtype, "key": key, "n": n, "p10": p10,
            "p50": p50, "p90": p90, "sd": sd}


ROAD_MODEL = {"work_type_code": "ROAD_CC", "unit": "m", "n": 4065, "slope": 0.6309,
              "intercept": 4.5381, "resid_sd": 0.2772, "anchor_low": 4000.0,
              "anchor_high": 6500.0, "anchor_label": "published rural CC road rates"}


@pytest.fixture()
def stats():
    return StatsStore.from_rows(
        cohorts=[
            # roads: district peers Rs 79k-3.2 lakh; state peers up to Rs 10 lakh
            _c("type_district", "ROAD_CC", "639", 709, 4.9, 5.204, 5.5),
            _c("type_state", "ROAD_CC", "24", 5000, 5.0, 5.5, 6.0),
            _c("type", "ROAD_CC", "", 40000, 5.0, 5.6, 6.1),
            # a library type split by what the money buys
            _c("type_district", "LIBRARY|GOODS", "639", 100, 4.0, 4.3, 4.7),
            _c("type_state", "LIBRARY|GOODS", "24", 300, 4.0, 4.5, 5.0),
            _c("type", "LIBRARY|GOODS", "", 2000, 4.0, 5.0, 5.5),
            _c("type_district", "LIBRARY|WORKS", "639", 40, 5.5, 5.85, 6.1),
            _c("type_state", "LIBRARY|WORKS", "24", 200, 5.5, 5.9, 6.2),
            _c("type", "LIBRARY|WORKS", "", 1300, 5.4, 5.85, 6.3),
            # street lights: one light usually Rs 20k-1 lakh
            _c("type_state", "STREET_LIGHT", "24", 3000, 4.3, 4.6, 5.0),
            _c("type", "STREET_LIGHT", "", 30000, 4.3, 4.7, 5.0),
        ],
        durations=[{"work_type_code": "ROAD_CC", "n": 900, "p50": 380, "p90": 700,
                    "p98": 800}],
        unit_models=[ROAD_MODEL])


def _work(**kw):
    w = {"work_id": "W1", "work_type_code": "ROAD_CC", "district_lgd": "639",
         "district_name": "Anand", "state_lgd": "24", "amount": 160_000.0,
         "description": "Construction of CC road in village Bijdih", "status": "SANCTIONED",
         "recommended_date": date(2025, 11, 1), "quantity": None, "quantity_unit": None,
         "is_outside_constituency": False}
    w.update(kw)
    return w


def _cost_findings(r):
    return [f for f in r.findings if f.code not in ("DELAYED", "CEILING_BREACH")]


def test_typical_cost(stats):
    r = assess(_work(), stats, AS_OF)
    assert r.status == Status.ASSESSED and r.verdict == "COST_TYPICAL" and r.risk == 0.0
    assert "usual range" in r.headline and "Anand" in r.headline


def test_costly_work_is_judged_against_the_top_of_the_usual_range(stats):
    r = assess(_work(amount=1_300_000.0), stats, AS_OF)
    assert r.verdict == "COST_ABOVE_PEERS" and r.hard is False
    row = r.evidence["comparison"][0]
    assert row["metric"] == "Total cost" and row["this_work"] == 1_300_000.0
    assert row["typical_low"] == pytest.approx(10 ** 4.9)
    assert row["typical_high"] == pytest.approx(10 ** 5.5)
    top = 1_300_000.0 / 10 ** 5.5
    assert f"{top:.1f} times the top" in r.headline
    assert "709 similar works in Anand" in r.headline and "Check" in r.headline
    assert r.risk == pytest.approx(above_risk(top))


def test_high_for_the_district_but_ordinary_for_the_state_is_not_flagged(stats):
    # Rs 8 lakh: 2.5x the district's top (a district that files small roads), but under the
    # state's usual top of Rs 10 lakh. v1 called this "10.1x the typical amount".
    r = assess(_work(amount=800_000.0), stats, AS_OF)
    assert r.verdict == "COST_TYPICAL" and not _cost_findings(r)


def test_risk_grows_with_distance_so_flags_do_not_all_score_the_same():
    assert above_risk(1.9) == 0.0
    assert above_risk(2.0) == pytest.approx(0.35)
    assert above_risk(2.0) < above_risk(4.0) < above_risk(8.0) <= 0.9
    assert above_risk(1000.0) == pytest.approx(0.9)


def test_library_building_is_compared_with_buildings_not_book_orders(stats):
    # The owner's case: v1 compared this with book purchases ("typical Rs 10,000").
    r = assess(_work(work_type_code="LIBRARY", amount=1_500_000.0,
                     description="Construction of Library at Bothali under Nagar Panchayat"),
               stats, AS_OF)
    assert r.evidence["peer_type"] == "LIBRARY|WORKS"
    assert r.verdict == "COST_TYPICAL"


def test_book_order_is_compared_with_book_orders(stats):
    r = assess(_work(work_type_code="LIBRARY", amount=25_000.0,
                     description="Purchase of books for school library"), stats, AS_OF)
    assert r.evidence["peer_type"] == "LIBRARY|GOODS" and r.verdict == "COST_TYPICAL"
    assert "book and equipment purchase" in r.headline


def test_undescribed_sanction_is_not_assessable(stats):
    for text in ("Letter as per attached.", "List as per attached", "NA", "(no description)",
                 "???? ????? ?????"):
        r = assess(_work(amount=10_000_000.0, description=text), stats, AS_OF)
        assert r.status == Status.NOT_ASSESSABLE, text
        assert "does not say what is built or bought" in r.headline


def test_many_site_sanction_is_a_bundle_not_a_mark_up(stats):
    r = assess(_work(amount=10_000_000.0,
                     description="Roads construction in Allahabad loksabha kshetra"),
               stats, AS_OF)
    assert r.verdict == "BUNDLED_SANCTION" and r.risk == pytest.approx(cost.BUNDLE_RISK)
    assert "several sites" in r.headline


def test_counted_units_are_priced_per_unit(stats):
    ok = assess(_work(work_type_code="STREET_LIGHT", amount=2_000_000.0,
                      description="Installation of 50 nos solar street lights in village X"),
                stats, AS_OF)
    assert ok.evidence["reading"] == "per_unit" and not _cost_findings(ok)
    row = next(x for x in ok.evidence["comparison"] if x["metric"] == "Cost per unit")
    assert row["this_work"] == pytest.approx(40_000.0)
    dear = assess(_work(work_type_code="STREET_LIGHT", amount=20_000_000.0,
                        description="Installation of 50 nos solar street lights in village X"),
                  stats, AS_OF)
    assert dear.verdict == "UNIT_PRICE_ABOVE" and "per unit" in dear.headline


def test_road_with_a_length_is_judged_per_metre_not_by_total(stats):
    ok = assess(_work(amount=3_000_000.0, description="CC road 1200 mtr in village X"),
                stats, AS_OF)
    assert ok.evidence["reading"] == "per_metre" and not _cost_findings(ok)
    amount = 8 * 10 ** (4.5381 + 0.6309 * 3)       # 8x the fitted price for 1,000 m
    dear = assess(_work(amount=amount, description="CC road 1000 mtr in village X"),
                  stats, AS_OF)
    assert any(f.code == "UNIT_RATE_ABOVE" for f in dear.findings)
    assert "Cost per metre" in [x["metric"] for x in dear.evidence["comparison"]]


def test_a_road_stated_in_kilometres_is_read_per_metre(stats):
    r = assess(_work(amount=29_495_741.0,
                     description="Laying of 1.2 Km Black Top Road in Gangaram Village"),
               stats, AS_OF)
    row = next(x for x in r.evidence["comparison"] if x["metric"] == "Cost per metre")
    assert row["this_work"] == pytest.approx(29_495_741.0 / 1200.0)
    assert r.verdict == "UNIT_RATE_ABOVE"


def test_far_above_every_similar_work_is_a_scope_question_not_a_mark_up(stats):
    r = assess(_work(amount=53_000_000.0,
                     description="Construction of Skill Hub Building near Government ITI"),
               stats, AS_OF)
    assert r.verdict == "SCOPE_FAR_LARGER" and r.risk == pytest.approx(cost.SCOPE_RISK)
    assert "check what it covers and that its type is right" in r.headline
    assert "times" not in r.headline


def test_learned_range_that_expects_a_big_job_clears_it(stats):
    # Version B: works described like this usually cost up to Rs 6 crore -> not flagged.
    r = assess(_work(amount=53_000_000.0,
                     description="Construction of Skill Hub Building near Government ITI",
                     cost_expected={"q10": 7.0, "q50": 7.5, "q90": 7.8}), stats, AS_OF)
    assert not _cost_findings(r)
    assert "Expected for this description" in [x["metric"] for x in r.evidence["comparison"]]


def test_learned_range_that_agrees_keeps_the_flag_and_says_so(stats):
    r = assess(_work(amount=1_300_000.0, cost_expected={"q10": 5.0, "q50": 5.2, "q90": 5.5}),
               stats, AS_OF)
    assert r.verdict == "COST_ABOVE_PEERS" and "described like this one" in r.headline


PRICE = {"version": "test", "intercept": 5.0,
         "weights": {"w=building": 1.6, "w=skill": 0.6, "t=ROAD_CC": 0.2, "w=road": 0.0},
         "spread": {"ROAD_CC": [-0.3, 0.3]}, "default_spread": [-0.4, 0.4]}


def _with_price(stats):
    from drishti.agents.statistical.price_model import PriceModel
    stats.price_model = PriceModel.from_json(PRICE)
    return stats


def test_the_word_price_model_judges_a_work_it_has_never_seen(stats):
    # T051: version B used to exist only for works in the training file; a new work was
    # judged by peers alone. Now any description gets a range from stored word weights.
    s = _with_price(stats)
    big = assess(_work(work_id="NEW-1", amount=53_000_000.0,
                       description="Construction of Skill Hub Building near Government ITI"),
                 s, AS_OF)
    assert not _cost_findings(big)                     # words say: a big building
    plain = assess(_work(work_id="NEW-2", amount=1_300_000.0), s, AS_OF)
    assert plain.verdict == "COST_ABOVE_PEERS"         # words say: an ordinary road
    assert "described like this one" in plain.headline


def test_price_model_features_ignore_numbers_and_read_size():
    from drishti.agents.statistical.price_model import features
    f = features({"work_type_code": "ROAD_CC", "state_lgd": "24",
                  "description": "CC road 450 mtr at Rs 5 lakh in ward 12",
                  "recommended_date": date(2025, 1, 1)})
    assert "w=road" in f and not any(k.startswith("w=") and k[2:].isdigit() for k in f)
    assert f["has_length"] == 1.0 and f["year"] == 25.0


def test_well_below_district_and_state_is_a_soft_note(stats):
    r = assess(_work(amount=15_000.0), stats, AS_OF)
    assert r.verdict == "COST_BELOW_PEERS" and r.risk == pytest.approx(cost.BELOW_RISK)


def test_overdue_and_ceiling_are_left_to_compliance(stats):
    # R02 / R08 in Guideline Compliance report these; the cost engine carrying them too
    # counted one fact twice in the risk score (13,158 "cost" flags were only DELAYED)
    old = assess(_work(recommended_date=date(2023, 1, 1)), stats, AS_OF)
    outside = assess(_work(amount=3_000_000.0, is_outside_constituency=True), stats, AS_OF)
    for r in (old, outside):
        assert not {f.code for f in r.findings} & {"DELAYED", "CEILING_BREACH"}
        assert not r.hard


@pytest.mark.parametrize("kw,reason", [({"amount": None}, "amount"),
                                       ({"amount": 0}, "amount"),
                                       ({"work_type_code": None}, "type"),
                                       ({"work_type_code": "BRIDGE"}, "20")])
def test_not_assessable_is_said_out_loud(stats, kw, reason):
    r = assess(_work(**kw), stats, AS_OF)
    assert r.status == Status.NOT_ASSESSABLE and r.risk == 0.0
    assert reason in r.headline


def test_cost_always_applies_so_a_recommended_work_is_assessed_not_not_applicable(stats):
    # Every work carries the amount it was recommended at; the cost question never waits
    # for evidence, so this engine has no NOT_APPLICABLE case (unlike photo checks).
    r = assess(_work(status="RECOMMENDED"), stats, AS_OF)
    assert r.status == Status.ASSESSED
