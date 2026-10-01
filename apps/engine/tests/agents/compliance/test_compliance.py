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
    assert f.evidence["value"] == 130 and "75-day limit" in f.text and "para 3.12" in f.text
    assert "55 days past" in f.text and "1.7 times" in f.text


def _r01_risk(days: int) -> float:
    w = _work(status="RECOMMENDED", recommended_date=date(2025, 1, 1))
    from datetime import timedelta
    fs = evaluate(w, date(2025, 1, 1) + timedelta(days=days))
    return next(f for f in fs if f.evidence["rule"] == "R01").risk


def test_r01_signal_grows_with_the_wait_and_stops_at_its_severity():
    # T051: 80 days and 718 days waiting used to score the same 0.6
    r80, r150, r300, r900 = (_r01_risk(d) for d in (80, 150, 300, 900))
    assert 0.30 <= r80 < r150 < r300 <= 0.60
    assert r300 == pytest.approx(0.60) and r900 == pytest.approx(0.60)


def test_election_pauses_are_reference_data_with_a_checked_date():
    from drishti.agents.compliance.agent import calendar_checked_until, mcc_periods
    assert (date(2024, 3, 16), date(2024, 6, 6)) in mcc_periods()
    r = assess(_work(status="RECOMMENDED", recommended_date=date(2026, 1, 1)),
               calendar_checked_until().replace(year=calendar_checked_until().year + 3))
    assert any("last checked" in lim for lim in r.limitations)


def test_r02_overdue_is_low_past_a_year_and_medium_past_the_types_p98():
    low = evaluate(_work(recommended_date=date(2025, 3, 1)), AS_OF, p98=800)
    assert _codes(low)["R02"] == "LOW"
    assert "sanction letter records why" in low[0].text and "800 days" in low[0].text
    assert 0.15 <= low[0].risk < 0.30
    med = evaluate(_work(recommended_date=date(2023, 6, 1)), AS_OF, p98=800)
    assert _codes(med)["R02"] == "MEDIUM" and "98%" in med[0].text
    assert "days beyond the 800 days" in med[0].text
    assert 0.30 <= med[0].risk <= 0.60
    # further past the type's own norm scores higher, up to MEDIUM at twice it
    later = evaluate(_work(recommended_date=date(2021, 6, 1)), AS_OF, p98=800)
    assert later[0].risk > med[0].risk and later[0].risk == pytest.approx(0.60)
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


def test_r07_reads_hindi_script_with_the_same_landmark_guard():
    # T051: the same work in Devanagari used to pass unread
    assert "R07" in _codes(evaluate(_work(description="ग्राम रामपुर में मंदिर का निर्माण कार्य"),
                                    AS_OF))
    assert "R07" in _codes(evaluate(_work(description="मंदिर परिसर में शेड निर्माण"), AS_OF))
    for landmark in ("मंदिर के पास सड़क निर्माण", "मंदिर मार्ग पर इंटरलॉकिंग",
                     "सरस्वती शिशु मंदिर में कक्षा निर्माण"):
        assert "R07" not in _codes(evaluate(_work(description=landmark), AS_OF)), landmark


def test_a_script_the_reader_cannot_read_is_a_limitation_not_a_pass():
    r = assess(_work(description="கோவில் கட்டுமானம்"), AS_OF, p98=800)
    assert any("script the eligibility reader cannot read" in lim for lim in r.limitations)
    assert "R07" not in r.evidence["rules_checked"]


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
