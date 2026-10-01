"""Fund Flow (stored id `delay`, T053): is money stuck waiting for sanction?"""

from datetime import date

import pytest

from drishti.agents.contract import Status
from drishti.agents.delay.agent import assess
from drishti.agents.delay.backlog import OfficeBacklog

AS_OF = date(2026, 5, 26)


def _work(**kw):
    w = {"work_id": "W1", "status": "RECOMMENDED", "recommended_date": date(2026, 1, 1),
         "work_type_code": "ROAD_CC", "state_lgd": "9", "district_lgd": "162",
         "agency_name": "BDO SLOW", "term": "18th Lok Sabha", "house": "Lok Sabha"}
    w.update(kw)
    return w


def _backlog():
    works = ([{"work_id": f"S{i}", "district_lgd": "162", "agency_name": "BDO SLOW",
               "recommended_date": date(2025, 1, 1), "status": "RECOMMENDED"} for i in range(25)]
             + [{"work_id": f"Q{i}", "district_lgd": "162", "agency_name": "BDO QUICK",
                 "recommended_date": date(2025, 1, 1), "status": "SANCTIONED"}
                for i in range(100)])
    return OfficeBacklog.build(works)


def test_a_work_of_an_ended_term_still_waiting_is_money_stuck():
    w = _work(recommended_date=date(2024, 2, 1), term="17th Lok Sabha")
    r = assess(w, AS_OF)
    assert r.status == Status.ASSESSED and r.verdict == "TERM_ENDED_UNSANCTIONED"
    assert "05 Jun 2024" in r.headline and r.risk == pytest.approx(0.40)


def test_rajya_sabha_terms_are_not_modelled_and_it_says_so():
    r = assess(_work(term="Rajya Sabha", house="Rajya Sabha"), AS_OF)
    assert r.status == Status.ASSESSED and not r.findings
    assert any("Rajya Sabha" in lim for lim in r.limitations)


def test_an_office_with_far_more_waiting_than_its_district_is_a_backlog_finding():
    r = assess(_work(), AS_OF, _backlog())
    f = next(f for f in r.findings if f.code == "OFFICE_SANCTION_BACKLOG")
    assert "25 of its 25" in f.text and "25 of 125" in f.text
    quick = assess(_work(agency_name="BDO QUICK"), AS_OF, _backlog())
    assert not quick.findings and quick.evidence["office_waiting"] == 0
    assert "0 of its 100" in quick.headline


def test_no_prediction_is_made_for_sanctioned_or_completed_works():
    # T053: the delay prediction was removed; a sanctioned work has no money waiting
    for status in ("SANCTIONED", "COMPLETED"):
        assert assess(_work(status=status), AS_OF).status == Status.NOT_APPLICABLE


def test_not_assessable_without_a_date():
    assert assess(_work(recommended_date=None), AS_OF).status == Status.NOT_ASSESSABLE
