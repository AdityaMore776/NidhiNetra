import pytest

from drishti.agents.contract import AgentResult, Finding, Status, not_built
from drishti.fusion.fuse import CORROBORATION, SOFT_CAP, VALIDATION_CAP, fuse
from drishti.validation.checks import Issue, Severity

REL = {"statistical": 0.8, "duplicate_project": 0.8, "image_reuse": 0.8, "site_progress": 0.8}


def _r(agent, risk, conf=1.0, hard=False, status=Status.ASSESSED):
    f = [Finding("X", "a finding", hard=hard, risk=risk)] if risk else []
    return AgentResult(agent=agent, status=status, verdict="V", risk=risk, confidence=conf,
                       hard=hard, headline="h", version="t", findings=f)


def _built(*results):
    names = {r.agent for r in results}
    rest = [not_built(a, "q") for a in REL if a not in names]
    return list(results) + rest


def test_weight_is_risk_times_confidence_times_reliability():
    f = fuse(_built(_r("statistical", 0.4, conf=0.5)), [], REL)
    assert f.score == pytest.approx(0.4 * 0.5 * 0.8)


def test_soft_findings_are_capped():
    f = fuse(_built(_r("statistical", 1.0, conf=1.0)), [], {**REL, "statistical": 1.0})
    assert f.score == pytest.approx(SOFT_CAP)


def test_strongest_plus_corroboration_and_parts_sum_exactly():
    rs = _built(_r("statistical", 0.4), _r("image_reuse", 0.8, hard=True),
                _r("duplicate_project", 0.1))
    f = fuse(rs, [Issue("IMPOSSIBLE_TIMELINE", Severity.WARN, "m", risk=0.1)], REL)
    w = {"statistical": 0.32, "image_reuse": 0.64, "duplicate_project": 0.08,
         "validation": 0.10}
    expected = 0.64 + CORROBORATION * (0.32 + 0.08 + 0.10)
    assert expected < 1.0
    assert f.score == pytest.approx(expected)
    assert sum(p.contribution for p in f.parts) == pytest.approx(f.score, abs=1e-9)
    assert {p.source: p.weight for p in f.parts} == pytest.approx(w)


def test_score_is_capped_at_one_and_parts_still_sum():
    rs = _built(_r("statistical", 0.45), _r("image_reuse", 1.0, hard=True),
                _r("duplicate_project", 1.0, hard=True), _r("site_progress", 1.0, hard=True))
    f = fuse(rs, [], {k: 1.0 for k in REL})
    assert f.score == pytest.approx(1.0)
    assert sum(p.contribution for p in f.parts) == pytest.approx(1.0, abs=1e-9)


def test_validation_is_one_capped_input():
    issues = [Issue("A", Severity.WARN, "m", risk=0.3), Issue("B", Severity.WARN, "m", risk=0.3)]
    f = fuse(_built(), issues, REL)
    assert f.score == pytest.approx(VALIDATION_CAP)
    assert f.band == "MEDIUM"


@pytest.mark.parametrize("score_risk,band", [(0.1, "LOW"), (0.40, "MEDIUM")])
def test_bands_by_score(score_risk, band):
    f = fuse(_built(_r("statistical", score_risk)), [], {**REL, "statistical": 1.0})
    assert f.band == band


def test_one_strong_hard_finding_is_high_on_its_own():
    f = fuse(_built(_r("image_reuse", 0.8, conf=0.9, hard=True)), [],
             {**REL, "image_reuse": 0.5})
    assert f.score < 0.60
    assert f.band == "HIGH" and f.hard_trigger == "image_reuse"


def test_a_weak_hard_finding_is_not():
    f = fuse(_built(_r("image_reuse", 0.5, conf=0.9, hard=True)), [], REL)
    assert f.band == "MEDIUM"


def test_limited_evidence_when_two_or_more_agents_could_not_assess():
    f = fuse(_built(_r("statistical", 0.0)), [], REL)
    assert f.limited is True
    full = [_r(a, 0.0) for a in REL]
    assert fuse(full, [], REL).limited is False


def test_errors_carry_no_weight():
    rs = _built(_r("statistical", 0.9, status=Status.ERROR))
    assert fuse(rs, [], REL).score == 0.0
