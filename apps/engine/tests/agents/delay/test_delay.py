"""Delay v2 (T051): the late-rate ladder scores any open work from stored counts."""

from datetime import date

import pytest

from drishti.agents.contract import Status
from drishti.agents.delay.agent import assess
from drishti.agents.delay.rates import DelayRates

AS_OF = date(2026, 5, 26)


def _rates():
    return DelayRates.from_rows([
        {"level": "all", "key": "", "n": 1000, "late": 700},
        {"level": "type", "key": "ROAD_CC", "n": 400, "late": 260},
        {"level": "state_type", "key": "9|ROAD_CC", "n": 200, "late": 150},
        {"level": "district_type", "key": "162|ROAD_CC", "n": 60, "late": 48},
        {"level": "office", "key": "BDO SLOW", "n": 212, "late": 209},
        {"level": "office", "key": "BDO QUICK", "n": 80, "late": 20},
        {"level": "office", "key": "BDO TINY", "n": 3, "late": 3},
    ])


def _work(**kw):
    w = {"work_id": "W1", "status": "SANCTIONED", "recommended_date": date(2026, 1, 1),
         "work_type_code": "ROAD_CC", "state_lgd": "9", "district_lgd": "162",
         "agency_name": "BDO SLOW"}
    w.update(kw)
    return w


def test_an_office_that_rarely_finishes_in_a_year_gets_a_finding_with_its_own_record():
    r = assess(_work(), AS_OF, _rates())
    assert r.status == Status.ASSESSED and r.verdict == "LIKELY_LATE"
    text = r.findings[0].text
    assert "finished 3 of its 212 past works within a year" in text
    assert "will be late" not in text and "30% within a year" in text
    assert 0 < r.risk <= 1


def test_a_quick_office_has_no_finding_and_no_signal():
    r = assess(_work(agency_name="BDO QUICK"), AS_OF, _rates())
    assert r.status == Status.ASSESSED and not r.findings and r.risk == 0.0


def test_a_new_office_borrows_its_districts_record_and_says_so():
    # v1 could not score a work recommended after its offline run at all
    r = assess(_work(agency_name="A BRAND NEW OFFICE"), AS_OF, _rates())
    assert r.status == Status.ASSESSED and r.evidence["level"] == "district_type"
    assert any("No past record for this implementing office" in lim for lim in r.limitations)


def test_a_new_district_and_type_back_off_to_the_country():
    r = assess(_work(agency_name="", district_lgd="999", state_lgd="99",
                     work_type_code="NEW_TYPE"), AS_OF, _rates())
    assert r.status == Status.ASSESSED and r.evidence["level"] == "all"


def test_a_record_of_three_works_cannot_raise_a_finding():
    r = assess(_work(agency_name="BDO TINY"), AS_OF, _rates())
    assert not r.findings


def test_signal_grows_with_how_much_likelier_than_average():
    slow = assess(_work(), AS_OF, _rates()).risk
    mid = assess(_work(agency_name="A BRAND NEW OFFICE"), AS_OF, _rates()).risk
    assert slow > mid > 0


def test_completed_and_overdue_works_are_not_applicable():
    assert assess(_work(status="COMPLETED"), AS_OF, _rates()).status == Status.NOT_APPLICABLE
    r = assess(_work(recommended_date=date(2024, 1, 1)), AS_OF, _rates())
    assert r.status == Status.NOT_APPLICABLE and "Guideline Compliance" in r.headline


def test_not_assessable_without_a_date_or_a_table():
    assert assess(_work(recommended_date=None), AS_OF, _rates()).status == \
        Status.NOT_ASSESSABLE
    assert assess(_work(), AS_OF, None).status == Status.NOT_ASSESSABLE


def test_a_work_of_an_ended_term_still_waiting_for_sanction_is_fund_flow():
    # T410: Fund Flow merged in; a 17th Lok Sabha work waiting, two years old
    w = _work(status="RECOMMENDED", recommended_date=date(2024, 2, 1), term="17th Lok Sabha",
              house="Lok Sabha")
    r = assess(w, AS_OF, _rates())
    assert r.status == Status.ASSESSED and r.verdict == "TERM_ENDED_UNSANCTIONED"
    assert "05 Jun 2024" in r.headline and r.risk == pytest.approx(0.40)
    rs = assess(w | {"term": "Rajya Sabha", "house": "Rajya Sabha"}, AS_OF, _rates())
    assert rs.status == Status.NOT_APPLICABLE        # past a year, no fund-flow fact


def test_an_office_with_far_more_waiting_than_its_district_is_a_backlog_fact():
    from drishti.agents.delay.backlog import OfficeBacklog
    works = ([{"work_id": f"S{i}", "district_lgd": "162", "agency_name": "BDO SLOW",
               "recommended_date": date(2025, 1, 1), "status": "RECOMMENDED"} for i in range(25)]
             + [{"work_id": f"Q{i}", "district_lgd": "162", "agency_name": "BDO QUICK",
                 "recommended_date": date(2025, 1, 1), "status": "SANCTIONED"}
                for i in range(100)])
    backlog = OfficeBacklog.build(works)
    w = _work(status="RECOMMENDED", recommended_date=date(2026, 1, 1), term="18th Lok Sabha")
    r = assess(w, AS_OF, _rates(), backlog)
    f = next(f for f in r.findings if f.code == "OFFICE_SANCTION_BACKLOG")
    assert "25 of its 25" in f.text and "25 of 125" in f.text
    quick = assess(w | {"agency_name": "BDO QUICK"}, AS_OF, _rates(), backlog)
    assert "OFFICE_SANCTION_BACKLOG" not in {x.code for x in quick.findings}
    assert quick.evidence["office_waiting"] == 0


def test_the_stored_riskiest_tenth_cut_keeps_warnings_rare():
    # T410: a fixed 0.90 cut warned on 43% of real open works; the stored cut is the 90th
    # percentile of open works' estimates
    rows = [{"level": "all", "key": "", "n": 1000, "late": 700},
            {"level": "office", "key": "BDO SLOW", "n": 212, "late": 200},
            {"level": "flag", "key": "p90", "n": 1_000_000, "late": 995_000}]
    rates = DelayRates.from_rows(rows)
    assert rates.flag_p == pytest.approx(0.995)
    r = assess(_work(), AS_OF, rates)          # p ~ 0.93: likely late, not in the riskiest tenth
    assert r.verdict == "ORDINARY_DELAY_RISK" and not r.findings and r.risk > 0


def test_shrinkage_pulls_a_thin_record_toward_the_step_above():
    est = _rates().estimate(_work(agency_name="BDO TINY"))
    assert est.p_late < 1.0 and est.p_late == pytest.approx((3 + 20 * est.steps[-2][2]) / 23)
