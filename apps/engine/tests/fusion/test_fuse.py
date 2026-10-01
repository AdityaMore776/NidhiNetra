import pytest

from drishti.agents.contract import AgentResult, Finding, Status, not_built
from drishti.fusion.fuse import CRITICAL, HIGH, MEDIUM, band_of, fuse, weights
from drishti.validation.checks import Issue, Severity


def _r(agent, risk, hard=False, status=Status.ASSESSED, code="X", evidence=None):
    f = [Finding(code, f"{agent} sentence", hard=hard, risk=risk,
                 evidence=evidence or {})] if risk else []
    return AgentResult(agent=agent, status=status, verdict=code, risk=risk, confidence=0.9,
                       hard=hard, headline=f"{agent} headline", version="t", findings=f)


def _all(*results):
    names = {r.agent for r in results}
    return list(results) + [not_built(a, "q") for a in weights() if a not in names]


def test_blueprint_weights_come_from_the_registry():
    w = weights()
    assert w["compliance"] == 0.30 and w["statistical"] == 0.20 and w["dup_split"] == 0.20
    # shown, not counted: Delay is below its accuracy target, Odd Overall's random flags read
    # 3/30 worth a look (#63), and the evidence engines have pilot evidence only
    assert w["outlier"] == 0.0 and w["delay"] == 0.0
    assert w["paperwork"] == 0.0 and w["photo_evidence"] == 0.0


def test_score_is_the_weighted_sum_and_parts_add_up_exactly():
    f = fuse(_all(_r("compliance", 0.6), _r("statistical", 0.5), _r("dup_split", 0.85)), [])
    assert f.score == pytest.approx(0.30 * 0.6 + 0.20 * 0.5 + 0.20 * 0.85)
    assert sum(p.contribution for p in f.parts) == pytest.approx(f.score, abs=1e-12)
    assert [p.source for p in f.parts] == ["compliance", "dup_split", "statistical"]


def test_an_engine_shown_but_not_counted_adds_nothing():
    f = fuse(_all(_r("delay", 1.0)), [])
    assert f.score == 0.0 and f.parts == [] and f.band == "LOW"


def test_only_assessed_results_count():
    f = fuse(_all(_r("statistical", 0.9, status=Status.NOT_ASSESSABLE)), [])
    assert f.score == 0.0


def test_validation_issues_are_shown_not_counted():
    f = fuse(_all(), [Issue("IMPOSSIBLE_TIMELINE", Severity.WARN, "m", risk=0.3)])
    assert f.score == 0.0


@pytest.mark.parametrize("score,band", [(0.0, "LOW"), (MEDIUM - 1e-9, "LOW"), (MEDIUM, "MEDIUM"),
                                        (HIGH, "HIGH"), (CRITICAL, "CRITICAL"), (1.0, "CRITICAL")])
def test_bands(score, band):
    assert band_of(score) == band


def test_one_guideline_delay_alone_is_medium_two_engines_agreeing_is_high():
    alone = fuse(_all(_r("compliance", 0.6)), [])            # 18 of 100
    assert alone.band == "MEDIUM"
    weak = fuse(_all(_r("compliance", 0.6), _r("dup_split", 0.15)), [])     # 21: bulk order
    assert weak.band == "MEDIUM"
    two = fuse(_all(_r("compliance", 0.6), _r("statistical", 0.35)), [])    # 25
    assert two.band == "HIGH"
    repeat = fuse(_all(_r("compliance", 0.6), _r("dup_split", 0.45)), [])   # 27: weak repeat
    assert repeat.band == "HIGH"
    strong = fuse(_all(_r("compliance", 0.6), _r("dup_split", 0.6)), [])    # 30 (T051 cut)
    assert strong.band == "CRITICAL"
    split = fuse(_all(_r("compliance", 0.6), _r("dup_split", 0.8)), [])     # 34: under limit
    assert split.band == "CRITICAL"


def test_one_serious_rule_breach_lifts_to_high_two_to_critical_as_an_explicit_part():
    one = fuse(_all(_r("compliance", 1.0, hard=True)), [])
    assert one.score == pytest.approx(max(0.30, HIGH)) and one.hard_trigger == "compliance"
    weak = fuse(_all(_r("statistical", 0.1), _r("compliance", 0.3, hard=True)), [])
    assert weak.band == "LOW"        # a hard finding below 0.6 is not a serious breach
    two = AgentResult(agent="compliance", status=Status.ASSESSED, verdict="V", risk=1.0,
                      confidence=0.9, hard=True, headline="h", version="t",
                      findings=[Finding("A", "a", hard=True, risk=1.0),
                                Finding("B", "b", hard=True, risk=1.0)])
    f = fuse(_all(two), [])
    # the rules alone give 0.30 = CRITICAL already; lift a lower one to check the part
    low = fuse(_all(_r("statistical", 0.6, hard=True), _r("dup_split", 0.6, hard=True)), [])
    assert f.band == "CRITICAL"
    assert low.band == "CRITICAL" and low.score == pytest.approx(CRITICAL)
    floor = next(p for p in low.parts if p.source == "floor")
    assert floor.contribution == pytest.approx(CRITICAL - (0.2 * 0.6 + 0.2 * 0.6))
    assert sum(p.contribution for p in low.parts) == pytest.approx(low.score, abs=1e-12)


def test_reasons_are_the_top_three_contributions_in_english_and_hindi():
    comp = _r("compliance", 0.6, code="SANCTION_OVERDUE",
              evidence={"message_hi": "स्वीकृति समय सीमा से अधिक लंबित है।"})
    f = fuse(_all(comp, _r("statistical", 0.4, code="COST_ABOVE_PEERS"),
                  _r("dup_split", 0.6, code="REPEATED_WHILE_OPEN"), _r("delay", 1.0)), [])
    assert [x["source"] for x in f.reasons] == ["compliance", "dup_split", "statistical"]
    assert f.reasons[0]["text_en"] == "compliance sentence"
    assert f.reasons[0]["text_hi"] == "स्वीकृति समय सीमा से अधिक लंबित है।"
    assert "चालू कार्य" in f.reasons[1]["text_hi"]          # engine template for the code
    assert all(x["source"] != "delay" for x in f.reasons)


def test_limited_when_a_counted_engine_could_not_assess():
    f = fuse(_all(_r("compliance", 0.0), _r("statistical", 0.0, status=Status.NOT_ASSESSABLE),
                  _r("dup_split", 0.0)), [])
    assert f.limited is True
    g = fuse(_all(_r("compliance", 0.0), _r("statistical", 0.0), _r("dup_split", 0.0),
                  _r("delay", 0.0, status=Status.NOT_APPLICABLE)), [])
    assert g.limited is False       # delay is not counted; outlier is not built
