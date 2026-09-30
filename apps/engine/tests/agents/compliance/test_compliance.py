from datetime import date

import pytest

from drishti.agents.compliance.agent import assess, evaluate, mcc_days, rules
from drishti.agents.contract import Status, check_plain_language

AS_OF = date(2026, 5, 26)


def _work(**kw):
    w = {"work_id": "W1", "work_type_code": "ROAD_CC", "district_lgd": "639", "state_lgd": "24",
         "amount": 500_000.0, "description": "Construction of CC road in village Bijdih",
         "status": "SANCTIONED", "recommended_date": date(2026, 1, 1), "completed_date": None,
         "agency_name": "BDO X", "is_outside_constituency": False}
    w.update(kw)
    return w


def _codes(fs):
    return {f.evidence["rule"]: f.evidence["severity"] for f in fs}


def test_every_rule_has_a_reference_and_both_languages():
    for r in rules().values():
        assert r["guideline_ref"] and r["message_en"] and r["message_hi"]
        check_plain_language(r["message_en"])
        assert r["severity"] in ("HIGH", "MEDIUM", "LOW")
        if not r["evaluable"]:
            assert r["needs"]


def test_clean_work_passes_every_checkable_rule():
    r = assess(_work(), AS_OF, p98=800)
    assert r.status == Status.ASSESSED and r.risk == 0.0 and not r.findings
    assert "R03" in r.evidence["rules_not_checkable"]
    assert any("Could not check" in lim for lim in r.limitations)


def test_r01_sanction_overdue_counts_days_less_the_election_code():
    assert mcc_days(date(2024, 3, 1), date(2024, 12, 31)) == 83
    w = _work(status="RECOMMENDED", recommended_date=date(2024, 3, 1))
    # 121 days on the calendar, 83 of them under the code of conduct -> 38: within 75
    assert "R01" not in _codes(evaluate(w, date(2024, 6, 30)))
    fs = evaluate(w, date(2024, 9, 30))           # 213 - 83 = 130 days
    assert _codes(fs)["R01"] == "MEDIUM"
    f = next(f for f in fs if f.evidence["rule"] == "R01")
    assert f.evidence["value"] == 130 and "75 days" in f.text and "para 3.12" in f.text


def test_r02_overdue_is_low_past_a_year_and_medium_past_the_types_p98():
    low = evaluate(_work(recommended_date=date(2025, 3, 1)), AS_OF, p98=800)
    assert _codes(low)["R02"] == "LOW"
    assert "sanction letter records why" in low[0].text
    med = evaluate(_work(recommended_date=date(2023, 6, 1)), AS_OF, p98=800)
    assert _codes(med)["R02"] == "MEDIUM" and "98%" in med[0].text
    assert "R02" not in _codes(evaluate(_work(status="COMPLETED",
                                              recommended_date=date(2023, 6, 1),
                                              completed_date=date(2024, 1, 1)), AS_OF, p98=800))


def test_r06_impossible_order_of_dates():
    fs = evaluate(_work(status="COMPLETED", recommended_date=date(2025, 6, 1),
                        completed_date=date(2025, 1, 1)), AS_OF)
    assert "R06" in _codes(fs)
    fs = evaluate(_work(status="COMPLETED", completed_date=date(2026, 9, 1)), AS_OF)
    assert _codes(fs)["R06"] == "LOW"


def test_r07_possibly_inadmissible_says_verify():
    fs = evaluate(_work(description="Construction of temple in village X"), AS_OF)
    f = next(f for f in fs if f.evidence["rule"] == "R07")
    assert f.evidence["severity"] == "MEDIUM" and "Verify" in f.text
    assert "R07" not in _codes(evaluate(_work(description="CC road near Shiv temple"), AS_OF))
    assert "R07" not in _codes(evaluate(_work(description="Repair of Vidya Mandir school"),
                                        AS_OF))


def test_r08_outside_area_above_ceiling_is_high_and_hard():
    fs = evaluate(_work(is_outside_constituency=True, amount=3_000_000.0), AS_OF)
    f = next(f for f in fs if f.evidence["rule"] == "R08")
    assert f.hard and f.risk == pytest.approx(1.0) and "para 2.9" in f.text
    assert "R08" not in _codes(evaluate(_work(is_outside_constituency=True,
                                              amount=2_000_000.0), AS_OF))


def test_r11_missing_key_data_lists_what_is_missing():
    fs = evaluate(_work(amount=None, description="Letter as per attached"), AS_OF)
    f = next(f for f in fs if f.evidence["rule"] == "R11")
    assert f.evidence["severity"] == "LOW"
    assert "an amount" in f.text and "description" in f.text


def test_signal_is_the_highest_severity_broken():
    r = assess(_work(is_outside_constituency=True, amount=3_000_000.0,
                     recommended_date=date(2025, 3, 1)), AS_OF, p98=800)
    assert r.risk == pytest.approx(1.0) and r.hard
    assert r.evidence["rules_broken"] == ["R02", "R08"]


def test_hindi_message_travels_with_each_finding():
    fs = evaluate(_work(is_outside_constituency=True, amount=3_000_000.0), AS_OF)
    assert all(f.evidence["message_hi"] for f in fs)


def test_not_assessable_without_a_status():
    r = assess(_work(status=None), AS_OF)
    assert r.status == Status.NOT_ASSESSABLE and r.risk == 0.0


def test_compliance_always_applies_so_there_is_no_not_applicable_case():
    # every record has a stage the guidelines speak to; a recommended-only work is assessed
    r = assess(_work(status="RECOMMENDED", recommended_date=date(2026, 5, 1)), AS_OF)
    assert r.status == Status.ASSESSED
