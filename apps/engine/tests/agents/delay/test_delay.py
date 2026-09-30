from datetime import date

import pytest

from drishti.agents.contract import Status
from drishti.agents.delay.agent import assess

AS_OF = date(2026, 5, 26)
REASONS = ["the implementing office's past record (91% of its works finished more than a "
           "year after recommendation)", "its size (Rs 25.00 lakh)"]


def _work(**kw):
    w = {"work_id": "W1", "status": "SANCTIONED", "recommended_date": date(2026, 1, 1),
         "signals": {"delay": {"p_late": 0.93, "rank_pct": 0.96, "base_rate": 0.72,
                               "reasons": REASONS}}}
    w.update(kw)
    return w


def test_riskiest_open_works_get_a_finding_with_reasons_and_no_verdict():
    r = assess(_work(), AS_OF)
    assert r.status == Status.ASSESSED and r.verdict == "LIKELY_LATE"
    assert r.risk == pytest.approx((0.96 - 0.5) / 0.5)
    text = r.findings[0].text
    assert "4% of open works" in text and "93%" in text and "72%" in text
    assert "past record" in text and "will be late" not in text


def test_ordinary_work_has_a_small_signal_and_no_finding():
    w = _work(signals={"delay": {"p_late": 0.7, "rank_pct": 0.6, "base_rate": 0.72,
                                 "reasons": []}})
    r = assess(w, AS_OF)
    assert r.status == Status.ASSESSED and not r.findings
    assert r.risk == pytest.approx(0.2)
    low = assess(_work(signals={"delay": {"p_late": 0.3, "rank_pct": 0.2, "base_rate": 0.72}}),
                 AS_OF)
    assert low.risk == 0.0


def test_completed_work_is_not_applicable():
    assert assess(_work(status="COMPLETED"), AS_OF).status == Status.NOT_APPLICABLE


def test_work_already_past_a_year_is_not_applicable_compliance_reports_it():
    r = assess(_work(recommended_date=date(2024, 1, 1)), AS_OF)
    assert r.status == Status.NOT_APPLICABLE and "Compliance" in r.headline


def test_no_stored_score_is_not_assessable():
    assert assess(_work(signals={}), AS_OF).status == Status.NOT_ASSESSABLE
    assert assess(_work(recommended_date=None), AS_OF).status == Status.NOT_ASSESSABLE
