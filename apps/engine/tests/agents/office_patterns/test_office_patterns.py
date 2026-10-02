"""Office Patterns (2 Oct 2026): a habit of an office, never of an MP, judged against the scheme."""

from datetime import date

import pytest

from drishti.agents.contract import Status, check_plain_language
from drishti.agents.office_patterns.agent import assess
from drishti.agents.office_patterns.index import (
    OfficeIndex,
    built_right_after_sanction,
    limit_just_above,
)


def _w(i, amount, office="BDO Hugger", district="639", wtype="ROAD_CC",
       desc="Construction of CC road", **kw):
    return {"work_id": f"W{office[:3]}{i}", "agency_name": office, "district_lgd": district,
            "amount": amount, "work_type_code": wtype, "description": desc,
            "status": "SANCTIONED", **kw}


def _scheme(hug_share: float, n: int = 40):
    """One office pricing `hug_share` of its works at Rs 4.9 lakh, twenty ordinary offices with
    about 10% there (the dashboard tables of 2 Oct 2026: 9.5% of all works)."""
    works = [_w(i, 490_000.0 if i < hug_share * n else 300_000.0 + 1_000 * i) for i in range(n)]
    for o in range(20):
        works += [_w(i, 200_000.0 + 7_000 * i, office=f"BDO Plain {o}") for i in range(36)]
        works += [_w(90 + i, 490_000.0, office=f"BDO Plain {o}") for i in range(4)]
    return works


def test_just_under_a_limit_excludes_the_limit_itself():
    assert limit_just_above(490_000) == 500_000 and limit_just_above(985_000) == 1_000_000
    assert limit_just_above(500_000) is None          # a whole Rs 5 lakh is round pricing
    assert limit_just_above(470_000) is None and limit_just_above(None) is None


def test_an_office_that_prices_most_works_at_the_limit_is_named_on_those_works():
    idx = OfficeIndex.build(_scheme(0.8))
    h = idx.limit_pricing({"district_lgd": "639", "agency_name": "BDO Hugger"})
    assert h.routine and h.count == 32 and h.total == 40 and h.lift > 3
    r = assess(_w(1, 490_000.0), idx)
    assert r.status == Status.ASSESSED and r.verdict == "PRICED_AT_LIMIT"
    assert "32 of its 40 works" in r.headline and "Rs 5.00 lakh" in r.headline
    check_plain_language(r.headline)
    # the same office's work priced elsewhere carries no finding, only the facts
    other = assess(_w(39, 340_000.0), idx)
    assert other.risk == 0 and other.evidence["priced_just_under_a_limit"]["office"] == 32


def test_an_ordinary_office_is_not_named():
    idx = OfficeIndex.build(_scheme(0.8))
    r = assess(_w(91, 490_000.0, office="BDO Plain 3"), idx)
    assert r.status == Status.ASSESSED and r.risk == 0 and r.verdict == "OFFICE_AS_USUAL"


def test_a_milder_habit_is_not_a_finding():
    # a fifth of the office's works at the limit, twice the scheme's share: not a habit to name
    idx = OfficeIndex.build(_scheme(0.2))
    assert not idx.limit_pricing({"district_lgd": "639", "agency_name": "BDO Hugger"}).routine
    assert assess(_w(1, 490_000.0), idx).risk == 0


def test_no_office_is_not_applicable_and_no_index_or_few_works_is_not_assessable():
    assert assess({**_w(1, 490_000.0), "agency_name": None}, None).status == \
        Status.NOT_APPLICABLE
    r = assess(_w(1, 490_000.0), None)
    assert r.status == Status.NOT_ASSESSABLE and "not a clean chit" in r.headline
    tiny = OfficeIndex.build([_w(i, 490_000.0) for i in range(5)])
    r = assess(_w(1, 490_000.0), tiny)
    assert r.status == Status.NOT_ASSESSABLE and "too few" in r.headline


@pytest.mark.parametrize("lag,construction,expected", [
    (3, True, True), (0, True, True), (-30, True, True), (8, True, False), (3, False, False)])
def test_built_right_after_sanction(lag, construction, expected):
    w = {"status": "COMPLETED", "sanction_date": date(2025, 3, 1),
         "completed_date": date(2025, 3, 1).fromordinal(date(2025, 3, 1).toordinal() + lag),
         "work_type_code": "COMMUNITY_HALL" if construction else "COMPUTER",
         "description": "Construction of community hall" if construction
         else "Purchase of computers"}
    assert built_right_after_sanction(w) is expected


def test_the_office_after_sanction_habit_is_a_fact_never_a_second_finding():
    built = [{"work_id": f"B{i}", "agency_name": "EE Fast", "district_lgd": "639",
              "amount": 400_000.0, "work_type_code": "COMMUNITY_HALL",
              "description": "Construction of community hall", "status": "COMPLETED",
              "sanction_date": date(2025, 3, 1), "completed_date": date(2025, 3, 3)}
             for i in range(20)]
    slow = [{**b, "work_id": f"S{i}{b['work_id']}", "agency_name": f"EE Slow {i}",
             "completed_date": date(2025, 12, 1)} for i in range(10) for b in built]
    idx = OfficeIndex.build(built + slow)
    r = assess(built[0], idx)
    assert r.risk == 0 and not r.findings and "R14" in r.headline
    assert idx.after_sanction(built[0]).routine
    assert any(o["habit"] == "built right after sanction" for o in idx.routine_offices())
