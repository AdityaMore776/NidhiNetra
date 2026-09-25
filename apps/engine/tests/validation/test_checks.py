from datetime import date

import pytest

from drishti.validation.checks import Severity, validate
from drishti.validation.prohibited import match

AS_OF = date(2026, 5, 26)


def _work(**kw):
    w = {"work_id": "W1", "amount": 500_000.0, "work_type_code": "ROAD_CC",
         "description": "Construction of CC road in village Bijdih",
         "recommended_date": date(2024, 6, 1), "completed_date": None, "status": "SANCTIONED"}
    w.update(kw)
    return w


def _codes(issues):
    return {i.code for i in issues}


def test_clean_record_has_no_issues():
    assert validate(_work(), AS_OF) == []


def test_completed_before_recommended():
    issues = validate(_work(recommended_date=date(2024, 6, 1),
                            completed_date=date(2024, 1, 1), status="COMPLETED"), AS_OF)
    i = next(i for i in issues if i.code == "IMPOSSIBLE_TIMELINE")
    assert i.severity == Severity.WARN
    assert "152 days" in i.message
    assert i.risk == pytest.approx(0.30)


def test_migration_window_is_named_and_weighs_less():
    issues = validate(_work(recommended_date=date(2023, 8, 1),
                            completed_date=date(2023, 2, 1), status="COMPLETED"), AS_OF)
    i = next(i for i in issues if i.code == "IMPOSSIBLE_TIMELINE")
    assert "back-entered" in i.message
    assert i.risk == pytest.approx(0.10)


def test_completion_after_the_data_ends():
    issues = validate(_work(completed_date=date(2044, 10, 20), status="COMPLETED"), AS_OF)
    assert "FUTURE_DATE" in _codes(issues)


def test_missing_amount_and_type():
    assert "MISSING_AMOUNT" in _codes(validate(_work(amount=None), AS_OF))
    issues = validate(_work(work_type_code=None), AS_OF)
    assert next(i for i in issues if i.code == "MISSING_WORK_TYPE").severity == Severity.INFO


def test_prohibited_object_is_an_info_note_with_the_clause():
    issues = validate(_work(description="C/o Welcome Gate at Chubam in Longding District"),
                      AS_OF)
    i = next(i for i in issues if i.code == "PROHIBITED_CATEGORY")
    assert i.severity == Severity.INFO
    assert "Annexure-II item 15" in i.message
    assert i.risk == pytest.approx(0.10)


@pytest.mark.parametrize("text", [
    "Construction of CC road near Maruteshwar temple",
    "Construction of class rooms to Bal Vikas Vidya Mandir",
    "Installation work of Highmast Light near Achanur Mallikarjuna temple",
])
def test_landmarks_are_not_prohibited_works(text):
    assert match(text) is None


def test_superseded_items_are_never_checked():
    # GOVT_BUILDING is superseded: eSAKSHI offers government office buildings
    assert match("Construction of office building for the panchayat") is None
