"""records.work: every column of a work read one way, malformed values dropped, never guessed."""

import math
from datetime import date, datetime
from decimal import Decimal

from drishti import records


def test_text_stays_as_written_codes_read_as_digits_and_junk_is_no_value():
    assert records.text(" Construction of CC road ") == " Construction of CC road "
    assert records.text(101) == "101"
    assert records.text(101.0) == "101"            # a pandas code column with a gap in it
    for junk in (None, float("nan"), True, [], {}, 5.5, float("inf")):
        assert records.text(junk) is None


def test_dates_read_from_iso_and_indian_day_first_text():
    assert records.day(date(2024, 2, 1)) == date(2024, 2, 1)
    assert records.day(datetime(2024, 2, 1, 10, 30)) == date(2024, 2, 1)
    assert records.day("2024-02-01") == date(2024, 2, 1)
    assert records.day("2024-02-01T00:00:00") == date(2024, 2, 1)
    assert records.day("01/02/2024") == date(2024, 2, 1)
    assert records.day("01-02-2024") == date(2024, 2, 1)
    assert records.day(" 1.2.2024 ") == date(2024, 2, 1)
    for junk in (None, "", "2024-13-45", "31/02/2024", "not a date", 20240201, float("nan"), []):
        assert records.day(junk) is None


def test_amounts_read_from_any_number_type_and_grouped_text():
    w = records.work({"amount": Decimal("500000.00"), "quantity": "1,00,000"})
    assert w["amount"] == 500000.0 and isinstance(w["amount"], float)
    assert w["quantity"] == 100000.0
    for junk in (float("nan"), "abc", True, [], "", float("inf")):
        assert records.work({"amount": junk})["amount"] is None
    assert records.work({"amount": -5})["amount"] == -5.0      # kept: the engines judge it


def test_outside_area_reads_only_a_clear_yes_or_no():
    for yes in (True, 1, "true", "Yes", " y "):
        assert records.flag(yes) is True
    for no in (False, 0, "false", "NO"):
        assert records.flag(no) is False
    for junk in (None, float("nan"), 2, "maybe", [], {}):
        assert records.flag(junk) is None


def test_a_clean_record_comes_back_as_the_same_object():
    w = {"work_id": "W1", "description": "Construction of hall", "amount": 500000.0,
         "recommended_date": date(2024, 1, 1), "completed_date": None, "status": "COMPLETED",
         "is_outside_constituency": False, "signals": {}, "evidence": {"files": []},
         "extra": object()}
    assert records.work(w) is w


def test_a_malformed_record_is_copied_never_changed_in_place():
    w = {"work_id": 7, "amount": "5,00,000", "district_lgd": float("nan"),
         "recommended_date": "10/01/2024", "signals": "x", "unknown": "kept"}
    out = records.work(w)
    assert out == {"work_id": "7", "amount": 500000.0, "district_lgd": None,
                   "recommended_date": date(2024, 1, 10), "signals": {}, "unknown": "kept"}
    assert w["amount"] == "5,00,000" and math.isnan(w["district_lgd"])
    assert "completed_date" not in out                 # an absent column stays absent
    assert records.work(None) == {} and records.work("x") == {}
