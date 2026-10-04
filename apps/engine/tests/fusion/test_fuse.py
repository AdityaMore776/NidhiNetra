"""Risk fusion v2 (T050-T054), kept selectable with DRISHTI_FUSION=v2: these tests pin it.
The default since 2 Oct 2026 is v3 (tests/fusion/test_calibrated.py)."""

import pytest

from drishti.agents.contract import AgentResult, Finding, Status, not_built
from drishti.fusion.fuse import CRITICAL_V2 as CRITICAL
from drishti.fusion.fuse import HIGH_V2 as HIGH
from drishti.fusion.fuse import MEDIUM_V2 as MEDIUM
from drishti.fusion.fuse import band_of_v2 as band_of
from drishti.fusion.fuse import fuse, weights


@pytest.fixture(autouse=True)
def _v2(monkeypatch):
    monkeypatch.setenv("DRISHTI_FUSION", "v2")


def _r(agent, risk, hard=False, status=Status.ASSESSED, code="X", evidence=None):
    f = [Finding(code, f"{agent} sentence", hard=hard, risk=risk,
                 evidence=evidence or {})] if risk else []
    return AgentResult(agent=agent, status=status, verdict=code, risk=risk, confidence=0.9,
                       hard=hard, headline=f"{agent} headline", version="t", findings=f)


def _all(*results):
    names = {r.agent for r in results}
    return list(results) + [not_built(a, "q") for a in weights() if a not in names]


def test_weights_come_from_the_registry():
    w = weights()
    # T125: the four agents count the same; the retired engines are not in the registry at all
    assert w == {"cost_estimate": 0.25, "dup_split": 0.25, "time_rules": 0.25,
                 "site_progress": 0.25}


def test_score_is_the_weighted_sum_and_parts_add_up_exactly():
    f = fuse(_all(_r("time_rules", 0.6), _r("cost_estimate", 0.5), _r("dup_split", 0.85)), [])
    assert f.score == pytest.approx(0.25 * 0.6 + 0.25 * 0.5 + 0.25 * 0.85)
    assert sum(p.contribution for p in f.parts) == pytest.approx(f.score, abs=1e-12)
    assert [p.source for p in f.parts] == ["dup_split", "time_rules", "cost_estimate"]


def test_an_engine_shown_but_not_counted_adds_nothing():
    f = fuse(_all(_r("delay", 1.0)), [])
    assert f.score == 0.0 and f.parts == [] and f.band == "LOW"


def test_only_assessed_results_count():
    f = fuse(_all(_r("cost_estimate", 0.9, status=Status.NOT_ASSESSABLE)), [])
    assert f.score == 0.0


def test_no_engine_signal_scores_zero():
    assert fuse(_all()).score == 0.0


@pytest.mark.parametrize("score,band", [(0.0, "LOW"), (MEDIUM - 1e-9, "LOW"), (MEDIUM, "MEDIUM"),
                                        (HIGH, "HIGH"), (CRITICAL, "CRITICAL"), (1.0, "CRITICAL")])
def test_bands(score, band):
    assert band_of(score) == band


def test_one_timing_signal_alone_is_medium_two_engines_agreeing_is_high():
    alone = fuse(_all(_r("time_rules", 0.6)), [])                           # 15 of 100
    assert alone.band == "MEDIUM"
    weak = fuse(_all(_r("time_rules", 0.6), _r("dup_split", 0.15)), [])     # 19
    assert weak.band == "MEDIUM"
    two = fuse(_all(_r("time_rules", 0.6), _r("cost_estimate", 0.35)), [])  # 24
    assert two.band == "HIGH"
    strong = fuse(_all(_r("time_rules", 0.6), _r("dup_split", 0.6)), [])    # 30
    assert strong.band == "CRITICAL"


def test_one_serious_breach_lifts_to_high_two_to_critical_as_an_explicit_part():
    one = fuse(_all(_r("time_rules", 0.6, hard=True)), [])
    assert one.score == pytest.approx(HIGH) and one.hard_trigger == "time_rules"
    floor = next(p for p in one.parts if p.source == "floor")
    assert floor.contribution == pytest.approx(HIGH - 0.25 * 0.6)
    assert sum(p.contribution for p in one.parts) == pytest.approx(one.score, abs=1e-12)
    weak = fuse(_all(_r("cost_estimate", 0.1), _r("time_rules", 0.3, hard=True)), [])
    assert weak.band == "LOW"        # a hard finding below 0.6 is not a serious breach
    two = AgentResult(agent="time_rules", status=Status.ASSESSED, verdict="V", risk=0.6,
                      confidence=0.9, hard=True, headline="h", version="t",
                      findings=[Finding("A", "a", hard=True, risk=0.6),
                                Finding("B", "b", hard=True, risk=0.6)])
    f = fuse(_all(two), [])
    assert f.band == "CRITICAL" and f.score == pytest.approx(CRITICAL)


def test_reasons_are_the_top_three_contributions_in_english_and_hindi():
    late = _r("time_rules", 0.6, code="SANCTION_OVERDUE",
              evidence={"message_hi": "स्वीकृति समय सीमा से अधिक लंबित है।"})
    f = fuse(_all(late, _r("cost_estimate", 0.4, code="ESTIMATE_ABOVE_STANDARD_AND_MP"),
                  _r("dup_split", 0.5, code="REPEATED_WHILE_OPEN"), _r("delay", 1.0)), [])
    assert [x["source"] for x in f.reasons] == ["time_rules", "dup_split", "cost_estimate"]
    assert f.reasons[0]["text_en"] == "time_rules sentence"
    assert f.reasons[0]["text_hi"] == "स्वीकृति समय सीमा से अधिक लंबित है।"
    assert "चालू कार्य" in f.reasons[1]["text_hi"]          # engine template for the code
    assert all(x["source"] != "delay" for x in f.reasons)


def test_limited_when_a_counted_engine_could_not_assess():
    f = fuse(_all(_r("time_rules", 0.0), _r("cost_estimate", 0.0, status=Status.NOT_ASSESSABLE),
                  _r("dup_split", 0.0)), [])
    assert f.limited is True
    g = fuse(_all(_r("time_rules", 0.0), _r("cost_estimate", 0.0), _r("dup_split", 0.0),
                  _r("site_progress", 0.0, status=Status.NOT_APPLICABLE),
                  _r("delay", 0.0, status=Status.NOT_ASSESSABLE)), [])
    assert g.limited is False       # NOT_APPLICABLE is not "could not check"; delay is retired
