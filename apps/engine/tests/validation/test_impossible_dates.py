from datetime import date

import pytest

from drishti.validation.checks import validate
from drishti.validation.timeline import TimelineRates, impossible_date, quarter_of

# National figures measured on the real export, 2026-09-25 (1,096 of 85,773 = 1.28%).
QUARTERS = {
    "2023-Q3": (12948, 287),   # 2.22% - the portal's first months, bulk back-entry
    "2023-Q4": (18099, 265),   # 1.46%
    "2024-Q1": (25086, 443),   # 1.77% - 17th Lok Sabha end-of-term rush
    "2024-Q2": (49, 11),       # tiny quarter, 22%
    "2024-Q3": (3719, 18),     # 0.48% - a mature portal
}
AGENCIES = {
    "Thiruvananthapuram(DISTRICT COLLECTOR)": (400, 85),
    "Anand(DISTRICT COLLECTOR)": (500, 3),
    "Tiny office": (12, 6),
}


@pytest.fixture()
def rates():
    return TimelineRates.from_counts(QUARTERS, AGENCIES, overall=(85773, 1096))


def test_quarter_of():
    assert quarter_of(date(2024, 3, 31)) == "2024-Q1"
    assert quarter_of(date(2024, 4, 1)) == "2024-Q2"


def test_bulk_entry_quarter_is_a_records_note_not_a_queue_item(rates):
    i = impossible_date(date(2024, 2, 1), date(2023, 11, 1), "Anand(DISTRICT COLLECTOR)", rates)
    assert i.risk == pytest.approx(0.10)
    assert "bulk entry" in i.message and "2024-Q1" in i.message


def test_clean_quarter_is_individually_worth_a_check(rates):
    i = impossible_date(date(2024, 8, 1), date(2024, 5, 1), "Anand(DISTRICT COLLECTOR)", rates)
    assert i.risk == pytest.approx(0.30)
    assert "does not explain" in i.message


def test_borderline_quarter_stays_below_the_queue(rates):
    i = impossible_date(date(2023, 11, 1), date(2023, 8, 1), None, rates)
    assert 0.10 < i.risk < 0.30


def test_a_tiny_quarter_is_pulled_toward_the_national_rate(rates):
    # 11 of 49 would read as 22%; shrunk toward 1.28% it is still far above it
    assert rates.cohort_rate("2024-Q2") == pytest.approx((11 + 0.012778 * 200) / 249, rel=1e-3)
    i = impossible_date(date(2024, 5, 1), date(2024, 1, 1), None, rates)
    assert i.risk == pytest.approx(0.10)


def test_a_gap_under_a_week_is_a_clock_not_a_finding(rates):
    assert impossible_date(date(2024, 8, 5), date(2024, 8, 1), None, rates) is None


def test_office_level_concentration_is_named(rates):
    i = impossible_date(date(2024, 2, 1), date(2023, 11, 1),
                        "Thiruvananthapuram(DISTRICT COLLECTOR)", rates)
    assert "85 of 400" in i.message and "This office" in i.message


def test_small_offices_are_not_called_out(rates):
    assert rates.agency_concentration("Tiny office") is None
    assert rates.agency_concentration("Anand(DISTRICT COLLECTOR)") is None


def test_validate_uses_the_rates_when_given(rates):
    work = {"work_id": "W", "amount": 5e5, "work_type_code": "ROAD_CC", "description": "CC road",
            "recommended_date": date(2024, 2, 1), "completed_date": date(2023, 11, 1),
            "status": "COMPLETED", "agency_name": "Anand(DISTRICT COLLECTOR)"}
    issue = next(i for i in validate(work, date(2026, 5, 26), rates)
                 if i.code == "IMPOSSIBLE_TIMELINE")
    assert issue.risk == pytest.approx(0.10)


def test_a_concentrated_office_is_one_finding_not_many_queue_items(rates):
    # clean quarter, but the office dates many works this way: a recording practice
    i = impossible_date(date(2024, 8, 1), date(2024, 5, 1),
                        "Thiruvananthapuram(DISTRICT COLLECTOR)", rates)
    assert i.risk == pytest.approx(0.10)
    assert "This office" in i.message


def test_offices_needing_a_records_check_are_listed(rates):
    rows = rates.concentrated_offices()
    assert [r["agency_name"] for r in rows] == ["Thiruvananthapuram(DISTRICT COLLECTOR)"]
    assert rows[0]["bad"] == 85 and rows[0]["lift"] > 3
