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
    r = assess(_work(), AS_OF)
    assert r.status == Status.ASSESSED and r.risk == 0.0 and not r.findings
    assert "R03" in r.evidence["rules_not_checkable"]
    assert any("Could not check" in lim for lim in r.limitations)


def test_r01_sanction_overdue_counts_days_less_the_election_code():
    assert mcc_days(date(2024, 3, 1), date(2024, 12, 31)) == 83
    w = _work(status="RECOMMENDED", recommended_date=date(2024, 3, 1))
    # 121 days on the calendar, 83 of them under the code of conduct -> 38: within 75
    assert "R01" not in _codes(evaluate(w, date(2024, 6, 30)))
    fs = evaluate(w, date(2024, 9, 30))           # 213 - 83 = 130 days
    f = next(f for f in fs if f.evidence["rule"] == "R01")
    assert f.evidence["value"] == 130 and "75-day limit" in f.text and "para 3.12" in f.text
    assert "55 days past" in f.text


def _r01(days: int):
    from datetime import timedelta
    w = _work(status="RECOMMENDED", recommended_date=date(2025, 1, 1))
    fs = evaluate(w, date(2025, 1, 1) + timedelta(days=days))
    return next(f for f in fs if f.evidence["rule"] == "R01")


def test_r01_a_few_days_past_the_limit_scores_almost_nothing():
    # T054: at 75-90 days 6 in 10 works still wait; day 76 used to score half the maximum
    f = _r01(80)
    assert f.evidence["severity"] == "LOW" and f.risk <= 0.06
    assert "This is common" in f.text and "in 100 works" in f.text


def test_r01_signal_grows_as_fewer_works_that_old_still_wait():
    r80, r200, r365, r730, r900 = (_r01(d).risk for d in (80, 200, 365, 730, 900))
    assert r80 < r200 < r365 < r730
    assert 0.20 <= r365 <= 0.30
    assert r730 == pytest.approx(0.60) and r900 == pytest.approx(0.60)
    late = _r01(730)
    assert late.evidence["severity"] == "MEDIUM" and "turned down" in late.text
    assert late.evidence["share_still_waiting"] < 0.05


def test_r01_an_ended_terms_leftover_runs_on_the_para_315_clock():
    w = _work(status="RECOMMENDED", term="17th Lok Sabha", recommended_date=date(2024, 1, 10))
    f = next(f for f in evaluate(w, AS_OF) if f.evidence["rule"] == "R01")
    assert f.evidence["severity"] == "LOW" and f.risk == pytest.approx(0.15)
    assert "para 3.15" in f.text and "record needs closing" in f.text
    assert f.evidence["term_ended"] == "2024-06-05"
    # within 75 days of the term's end: the ordinary clock still applies
    early = evaluate(w, date(2024, 7, 1))
    assert all("para 3.15" not in f.text for f in early)


def test_election_pauses_are_reference_data_with_a_checked_date():
    from drishti.agents.compliance.agent import calendar_checked_until, mcc_periods
    assert (date(2024, 3, 16), date(2024, 6, 6)) in mcc_periods()
    r = assess(_work(status="RECOMMENDED", recommended_date=date(2026, 1, 1)),
               calendar_checked_until().replace(year=calendar_checked_until().year + 3))
    assert any("last checked" in lim for lim in r.limitations)


def test_r02_open_past_a_year_is_always_a_low_note():
    # T054: 4 in 10 works recommended 2-3 years ago are still shown open; the old
    # "past 98% of finished works" MEDIUM line was an artefact of the data starting in 2023
    for rec in (date(2025, 3, 1), date(2023, 6, 1), date(2021, 6, 1)):
        fs = evaluate(_work(recommended_date=rec), AS_OF)
        f = next(f for f in fs if f.evidence["rule"] == "R02")
        assert f.evidence["severity"] == "LOW" and f.risk <= 0.10
        assert "still shown as open" in f.text and "sanction letter records why" in f.text
    assert "R02" not in _codes(evaluate(_work(recommended_date=date(2025, 9, 1)), AS_OF))
    assert "R02" not in _codes(evaluate(_work(status="COMPLETED",
                                              recommended_date=date(2023, 6, 1),
                                              completed_date=date(2024, 1, 1)), AS_OF))


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
    r = assess(_work(description="கோவில் கட்டுமானம்"), AS_OF)
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
                     recommended_date=date(2025, 3, 1)), AS_OF)
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


def test_r12_a_big_sum_that_does_not_say_what_or_where():
    # T053: replaced the Odd Overall engine; 30/30 read as a question the record cannot answer
    big = _work(amount=5_000_000.0, description="Building")
    f = next(f for f in evaluate(big, AS_OF, type_top=1_000_000.0) if f.evidence["rule"] == "R12")
    assert f.evidence["severity"] == "MEDIUM" and "does not say where" in f.text
    # a place, a number, a small sum, or a sum ordinary for the type: not raised
    for kw in ({"description": "Building at Sitapur village"},
               {"description": "Building of 2 rooms"},
               {"amount": 900_000.0},
               {"description": "Building", "amount": 900_000.0}):
        fs = evaluate(_work(**({"amount": 5_000_000.0, "description": "Building"} | kw)), AS_OF,
                      type_top=1_000_000.0 if kw.get("amount", 0) != 900_000.0 else 2_000_000.0)
        assert "R12" not in _codes(fs), kw


def test_r13_a_building_recorded_complete_within_days():
    done = _work(work_type_code="COMMUNITY_HALL", amount=1_500_000.0, status="COMPLETED",
                 description="Construction of community hall at Kayakkunnu colony",
                 recommended_date=date(2025, 12, 15), completed_date=date(2025, 12, 15))
    f = next(f for f in evaluate(done, AS_OF) if f.evidence["rule"] == "R13")
    assert "0 days after it was recommended" in f.text
    # a purchase, a slow build, a cheap job, or a backfilled older work: not raised
    for kw in ({"work_type_code": "STREET_LIGHT"}, {"completed_date": date(2026, 3, 1)},
               {"amount": 300_000.0},
               {"description": "Community hall at Kayakkunnu (2019-2020)"}):
        assert "R13" not in _codes(evaluate(done | kw, AS_OF)), kw


def test_r12_a_size_written_as_a_word_is_a_stated_size():
    fs = evaluate(_work(amount=5_300_000.0, description="Purchase of Two Ambulance"), AS_OF,
                  type_top=1_000_000.0)
    assert "R12" not in _codes(fs)


# ---- R14 and the 2 Oct 2026 R07 reading (eSAKSHI dashboard tables) ---------------------------

def _built(**kw):
    return _work(**{"status": "COMPLETED", "work_type_code": "COMMUNITY_HALL",
                    "amount": 900_000.0, "description": "Construction of community hall at Bijdih",
                    "recommended_date": date(2025, 1, 10), "sanction_date": date(2025, 9, 1),
                    "completed_date": date(2025, 9, 3)} | kw)


def test_r14_a_construction_complete_two_days_after_sanction_is_medium():
    f = next(f for f in evaluate(_built(), AS_OF) if f.evidence["rule"] == "R14")
    assert f.code == "BUILT_RIGHT_AFTER_SANCTION" and f.evidence["severity"] == "MEDIUM"
    assert "2 days after it was sanctioned" in f.text and f.evidence["value"] == 2
    assert "स्वीकृति के 2 दिन बाद" in f.evidence["message_hi"]
    check_plain_language(f.text)


def test_r14_needs_a_construction_of_size_and_a_short_gap():
    assert "R14" not in _codes(evaluate(_built(completed_date=date(2025, 9, 20)), AS_OF))
    assert "R14" not in _codes(evaluate(_built(amount=150_000.0), AS_OF))
    goods = _built(work_type_code="COMPUTER", description="Purchase of computers for school")
    assert "R14" not in _codes(evaluate(goods, AS_OF))
    before = evaluate(_built(completed_date=date(2025, 8, 1)), AS_OF)
    assert "31 days before it was sanctioned" in next(
        f for f in before if f.evidence["rule"] == "R14").text


def test_r14_without_a_sanction_date_says_it_could_not_check():
    r = assess(_built(sanction_date=None), AS_OF)
    assert "R14" not in r.evidence["rules_checked"]
    assert any("no sanction date" in lim for lim in r.limitations)


def test_r14_an_office_that_does_this_routinely_is_low_and_named_once():
    from drishti.agents.office_patterns.index import OfficeIndex

    own = [_built(work_id=f"B{i}", agency_name="EE Fast") for i in range(20)]
    others = [_built(work_id=f"S{i}", agency_name=f"EE {i % 10}",
                     completed_date=date(2025, 12, 1)) for i in range(200)]
    f = next(f for f in evaluate(own[0], AS_OF, offices=OfficeIndex.build(own + others))
             if f.evidence["rule"] == "R14")
    assert f.evidence["severity"] == "LOW" and f.risk == pytest.approx(0.10)
    assert "20 of its 20 constructions" in f.text and f.evidence["office_routine"]


@pytest.mark.parametrize("text,flagged", [
    # roads named after a place of worship, and things beside or near one: not the work
    ("Construction of Puthiyakavu temple link road, ward 2, Udayamperoor GP", False),
    ("Construction of Pera- St.John's Marthoma Church- Cheruvalloore Road in Ummannoor", False),
    ("ram mandir prangan ke samip shed nirman karya", False),
    ("gram sahodra me mandir parisar ke bagal me chabutra ka nirman", False),
    ("school se Shiv mandir tak pcc nirman kary", False),
    ("construction of Pulic Distribution shop at Ward no.12", False),
    ("Development of Ramesh Chandra Memorial Institution Play Ground", False),
    ("Construction of boundary wall at Saraswati Sishu Bidya Mandir", False),
    ("Electrification from Salempur to Abhay Nandan Private ITI College", False),
    ("private bus stand ke pas high mast", False),
    # the work itself on or for a place of worship, or for a private institution
    ("Muraura talab shiv mandir ka saundaryikaran karya", True),
    ("Rampur me Hanuman mandir nirman", True),
    ("Construction of Toilet in Catholic Church", True),
    ("For Construction of Community Hall in Mandir", True),
    ("Construction of boundary wall of jama masjid at Kanganj", True),
    ("JAGAT PRIVETE ITI ME SOLAR PLANT", True),
    ("table of kitchen, private school,", True),
])
def test_r07_reading_on_real_dashboard_wording(text, flagged):
    from drishti.agents.compliance.eligibility import v2

    assert bool(v2(text)) is flagged
