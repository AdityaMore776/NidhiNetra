from datetime import date

from drishti.agents.statistical.timeline import delay_check

AS_OF = date(2026, 5, 26)


def test_open_work_past_the_98th_percentile_is_delayed():
    r = delay_check("SANCTIONED", date(2023, 12, 8), AS_OF, p98=800)
    assert r["verdict"] == "DELAYED"
    assert r["days"] == 900 and r["risk"] == 0.20


def test_open_work_within_the_norm_is_on_time():
    assert delay_check("SANCTIONED", date(2025, 5, 26), AS_OF, p98=800)["verdict"] == "ON_TIME"


def test_completed_works_are_never_delayed():
    assert delay_check("COMPLETED", date(2020, 1, 1), AS_OF, p98=800) is None


def test_missing_date_or_norm_is_not_assessed():
    assert delay_check("SANCTIONED", None, AS_OF, p98=800) is None
    assert delay_check("SANCTIONED", date(2020, 1, 1), AS_OF, p98=None) is None
