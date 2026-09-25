import json

import pytest

from drishti.agents.contract import (AgentResult, BANNED_WORDS, Finding, Status,
                                     check_plain_language)


def _result(**kw):
    base = dict(agent="statistical", status=Status.ASSESSED, verdict="COST_TYPICAL",
                risk=0.0, confidence=0.8, hard=False, headline="Cost is typical.",
                version="t")
    base.update(kw)
    return AgentResult(**base)


def test_status_must_be_known():
    with pytest.raises(ValueError):
        _result(status="MAYBE")


def test_risk_and_confidence_are_clamped():
    r = _result(risk=1.7, confidence=-0.2)
    assert r.risk == 1.0 and r.confidence == 0.0


@pytest.mark.parametrize("word", BANNED_WORDS)
def test_headline_may_never_accuse(word):
    with pytest.raises(ValueError):
        _result(headline=f"This looks like {word} to us")


def test_finding_text_may_never_accuse():
    with pytest.raises(ValueError):
        Finding(code="X", text="an obvious scam", hard=False, risk=0.1)


def test_banned_words_match_whole_words_only():
    with pytest.raises(ValueError):
        check_plain_language("the theft-proof lock was fitted")  # 'theft' is a word here
    check_plain_language("scampi stall")  # contains 'scam' but is not the word


def test_round_trips_through_json():
    r = _result(findings=[Finding(code="COST_ABOVE_PEERS", text="Costs 3.1x peers",
                                  hard=False, risk=0.3, evidence={"z": 3.4})],
                limitations=["cohort of 25"])
    back = AgentResult.from_json(json.loads(json.dumps(r.to_json())))
    assert back == r
