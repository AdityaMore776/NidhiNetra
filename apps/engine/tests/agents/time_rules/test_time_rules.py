"""Time & Rules (T122, plan T120 §8): the 75-day clock, impossible dates, too fast, too late."""

import random
from datetime import date, timedelta

import pytest

from drishti.agents.contract import Status, check_plain_language
from drishti.agents.time_rules import window as win
from drishti.agents.time_rules.agent import LATE_FACT_RISK, assess

AS_OF = date(2026, 10, 2)


def _work(**kw):
    w = {"work_id": "W1", "work_type_code": "ROAD_CC", "district_lgd": "UP|X",
         "amount": 500_000.0, "description": "CC road from the school to the temple in village X",
         "status": "SANCTIONED", "recommended_date": date(2026, 1, 1),
         "sanction_date": date(2026, 2, 1), "completed_date": None, "agency_name": "BDO X"}
    w.update(kw)
    return w


def _form(months=4, start="2026-02", lost=("jul", "aug"), work_type="ROAD_CC"):
    return {"work": {"work_type": work_type},
            "timing": {"duration_months": months, "start_month": start},
            "sites": [{"site_conditions": {"lost_months": list(lost)}}]}


def _visit(day: date, kind="monthly", change="changed", **readings):
    return {"visit_id": f"v{day.isoformat()}", "kind": kind, "captured_at": day.isoformat(),
            "readings": {"change": change, **readings}}


def _codes(r):
    return {f.code for f in r.findings}


def _f(r, code):
    return next(f for f in r.findings if f.code == code)


# --- statuses ---------------------------------------------------------------------------------

def test_no_status_is_not_assessable_never_a_clean_chit():
    r = assess(_work(status=None), AS_OF)
    assert r.status == Status.NOT_ASSESSABLE and r.risk == 0 and "not a clean chit" in r.headline


def test_an_on_time_work_is_assessed_with_nothing_found():
    r = assess(_work(sanction_date=date(2026, 2, 1)), AS_OF)   # 31 days
    assert r.status == Status.ASSESSED and not r.findings
    assert r.verdict == "ON_TIME_AS_FAR_AS_CHECKED"
    assert any("No cost estimate form" in lim for lim in r.limitations)


# --- the 75-day clock -------------------------------------------------------------------------

def test_a_late_sanction_is_a_fact_about_the_office_never_a_finding_about_the_work():
    r = assess(_work(sanction_date=date(2026, 5, 1)), AS_OF)   # 120 days
    f = _f(r, "SANCTIONED_LATE")
    assert f.risk == LATE_FACT_RISK and f.evidence["value"] == 120 and f.evidence["limit"] == 75
    assert "not a finding about the work" in f.text and "report card" in f.text
    assert "60%" in f.text                     # measured on the dashboard (time_bands.json)
    assert f.evidence["message_hi"]


def test_the_clock_leaves_out_election_code_days():
    # 1 Mar - 1 Jul 2024 is 122 days, 83 of them under the 2024 general-election code
    r = assess(_work(recommended_date=date(2024, 3, 1), sanction_date=date(2024, 7, 1)), AS_OF)
    assert "SANCTIONED_LATE" not in _codes(r)


def test_still_waiting_keeps_rule_r01():
    r = assess(_work(status="RECOMMENDED", sanction_date=None,
                     recommended_date=date(2025, 1, 1)), date(2026, 1, 1))
    f = _f(r, "SANCTION_OVERDUE")
    assert f.evidence["rule"] == "R01" and f.risk <= 0.6


# --- impossible dates and the record's own fast-finish rules (no form) -------------------------

def test_completion_before_recommendation_keeps_rule_r06():
    r = assess(_work(status="COMPLETED", recommended_date=date(2026, 3, 1),
                     sanction_date=None, completed_date=date(2026, 1, 1)), AS_OF)
    assert "IMPOSSIBLE_TIMELINE" in _codes(r)


def test_without_a_form_r14_asks_about_a_construction_finished_within_a_week_of_sanction():
    r = assess(_work(status="COMPLETED", completed_date=date(2026, 2, 4)), AS_OF)
    assert "BUILT_RIGHT_AFTER_SANCTION" in _codes(r) and "FINISHED_TOO_FAST" not in _codes(r)


def test_the_other_guideline_rules_are_not_this_agents():
    r = assess(_work(description="Construction of boundary wall of temple", amount=2_000_000,
                     is_outside_constituency=True), AS_OF)
    assert all(f.evidence.get("rule") in (None, "R01", "R06", "R13", "R14") for f in r.findings)


# --- step A: is the estimate believable? -------------------------------------------------------

def test_the_window_from_a_believable_estimate():
    w = win.window(_form(months=4), "ROAD_CC", date(2026, 2, 10))
    assert w.start == date(2026, 2, 10)                 # sanction later than the declared month
    assert w.accepted_days == pytest.approx(4 * win.MONTH_DAYS)
    assert w.early == w.start + timedelta(days=round(4 * win.MONTH_DAYS / 4))
    grace = max(0.5 * 4 * win.MONTH_DAYS, win.GRACE_MIN_DAYS)
    assert w.late == w.start + timedelta(days=round(4 * win.MONTH_DAYS + grace
                                                    + 2 * win.MONTH_DAYS))
    assert not w.notes


def test_a_padded_estimate_buys_no_time():
    w = win.window(_form(months=60), "ROAD_CC", date(2026, 2, 10))
    longest, _ = win.longest_usual("ROAD_CC")
    assert w.accepted_days == longest and "buys no extra time" in w.notes[0]


def test_a_too_short_estimate_is_raised_to_the_shortest_believable_time():
    w = win.window(_form(months=0.1), "COMMUNITY_HALL", date(2026, 2, 10), )
    assert w.shortest_days == 21 and w.accepted_days == 21 and "shorter than" in w.notes[0]


def test_no_early_line_for_purchases_and_installations():
    w = win.window(_form(months=1, work_type="STREET_LIGHT"), "STREET_LIGHT", date(2026, 2, 10))
    assert w.early is None and w.late > w.start


def test_a_later_declared_start_moves_the_window():
    w = win.window(_form(start="2026-06"), "ROAD_CC", date(2026, 2, 10))
    assert w.start == date(2026, 6, 1)


def test_a_video_showing_work_earlier_moves_the_start_but_never_before_sanction():
    w = win.window(_form(start="2026-06"), "ROAD_CC", date(2026, 2, 10), date(2026, 3, 5))
    assert w.start == date(2026, 3, 5)
    w = win.window(_form(start="2026-06"), "ROAD_CC", date(2026, 2, 10), date(2026, 1, 5))
    assert w.start == date(2026, 2, 10)


def test_no_estimate_or_no_start_gives_no_window():
    assert win.window(None, "ROAD_CC", date(2026, 2, 10)) is None
    assert win.window(_form(months=0), "ROAD_CC", date(2026, 2, 10)) is None
    assert win.window({"timing": {"duration_months": 4}}, "ROAD_CC", None) is None


# --- step C: too fast ---------------------------------------------------------------------------

def _done(days_after_sanction, **kw):
    kw.setdefault("cost_form", _form(months=4))
    return _work(status="COMPLETED", sanction_date=date(2026, 2, 10),
                 completed_date=date(2026, 2, 10) + timedelta(days=days_after_sanction), **kw)


def test_finished_before_the_early_line_with_no_video_is_asked_about():
    r = assess(_done(10), AS_OF)                         # early line: a quarter of 4 months
    f = _f(r, "FINISHED_TOO_FAST")
    assert f.risk == 0.6 and "There are no site videos" in f.text and "was 4 months" in f.text
    assert "BUILT_RIGHT_AFTER_SANCTION" not in _codes(r)   # the window replaces R14
    assert r.evidence["window"]["early"]


def test_complete_before_its_own_planned_start_counts_from_the_sanction():
    # sanctioned 24 Jun, planned to start in July, recorded complete 30 Jun: 6 days, not "0"
    w = _work(status="COMPLETED", sanction_date=date(2026, 6, 24),
              completed_date=date(2026, 6, 30), cost_form=_form(months=4, start="2026-07"))
    f = _f(assess(w, AS_OF), "FINISHED_TOO_FAST")
    assert "6 days after its sanction (24 Jun 2026 to 30 Jun 2026)" in f.text
    assert f.evidence["value"] == 6


def test_a_fast_finish_the_videos_show_is_good_work_never_asked_about():
    vs = [_visit(date(2026, 2, 9), kind="baseline", change=None),
          _visit(date(2026, 2, 15)), _visit(date(2026, 2, 19), kind="final")]
    r = assess(_done(10, site_visits=vs), AS_OF)
    assert "FINISHED_TOO_FAST" not in _codes(r)


def test_videos_that_show_nothing_going_on_do_not_protect_a_fast_finish():
    vs = [_visit(date(2026, 2, 9), kind="baseline", change=None),
          _visit(date(2026, 2, 19), kind="final", change="no_change")]
    f = _f(assess(_done(10, site_visits=vs), AS_OF), "FINISHED_TOO_FAST")
    assert "No site video shows the work going on" in f.text


def test_finished_after_the_early_line_is_fine():
    assert "FINISHED_TOO_FAST" not in _codes(assess(_done(40), AS_OF))


def test_small_works_and_purchases_are_never_asked_about_a_fast_finish():
    assert "FINISHED_TOO_FAST" not in _codes(assess(_done(3, amount=200_000), AS_OF))
    lights = _done(3, work_type_code="STREET_LIGHT", description="Solar street lights 10 nos")
    lights["cost_form"] = _form(work_type="STREET_LIGHT")
    assert "FINISHED_TOO_FAST" not in _codes(assess(lights, AS_OF))


# --- step C: past its own promised time ---------------------------------------------------------

def test_past_the_late_line_is_a_follow_up():
    w = _work(cost_form=_form(months=4), sanction_date=date(2025, 1, 1))
    window = win.window(w["cost_form"], "ROAD_CC", date(2025, 1, 1))
    assert "PAST_PROMISED_TIME" not in _codes(assess(w, window.late))
    f = _f(assess(w, window.late + timedelta(days=1)), "PAST_PROMISED_TIME")
    assert f.risk == 0.2 and f.evidence["value"] == 1 and not f.evidence["stalled"]
    assert "follow up" in f.text and "2 declared lost months" in f.text


def test_past_the_late_line_with_the_site_standing_still_counts_more():
    vs = [_visit(date(2025, 6, 1) + timedelta(days=30 * i), change="no_change") for i in range(3)]
    w = _work(cost_form=_form(months=4, start="2025-01"), sanction_date=date(2025, 1, 1),
              site_visits=vs)
    f = _f(assess(w, AS_OF), "PAST_PROMISED_TIME")
    assert f.risk == 0.4 and f.evidence["stalled"] and "no change" in f.text


def test_a_recorded_extension_moves_the_late_line():
    w = _work(cost_form=_form(months=4), sanction_date=date(2025, 1, 1))
    late = win.window(w["cost_form"], "ROAD_CC", date(2025, 1, 1)).late
    w["time_extension_days"] = 30
    assert "PAST_PROMISED_TIME" not in _codes(assess(w, late + timedelta(days=10)))


def test_a_completed_work_is_never_past_its_time():
    w = _work(status="COMPLETED", completed_date=date(2026, 9, 1), cost_form=_form(months=1),
              sanction_date=date(2025, 1, 1))
    assert "PAST_PROMISED_TIME" not in _codes(assess(w, AS_OF))


# --- every sentence plain, every input safe ---------------------------------------------------

def test_every_text_is_plain_and_carries_hindi():
    for w in (_done(10), _work(sanction_date=date(2026, 6, 1)),
              _work(cost_form=_form(months=4), sanction_date=date(2025, 1, 1))):
        r = assess(w, AS_OF)
        check_plain_language(r.headline)
        for f in r.findings:
            check_plain_language(f.text)
            assert f.evidence.get("message_hi")


def test_damaged_forms_and_visits_never_break_it():
    rng = random.Random(7)
    junk = [None, "", 0, -3, 1e12, "x", [], {}, [1, "a"], {"a": None}, True, float("nan")]
    for _ in range(300):
        form = {"work": rng.choice(junk + [{"work_type": rng.choice(junk + ["ROAD_CC"])}]),
                "timing": rng.choice(junk + [{"duration_months": rng.choice(junk + [3]),
                                              "start_month": rng.choice(junk + ["2026-13",
                                                                                "2026-04"])}]),
                "sites": rng.choice(junk + [[{"site_conditions": {"lost_months":
                                                                  rng.choice(junk)}}]])}
        visits = rng.choice(junk + [[{"kind": rng.choice(junk + ["monthly"]),
                                      "captured_at": rng.choice(junk + ["2026-03-01"]),
                                      "readings": rng.choice(junk)}]])
        w = _done(rng.choice([1, 10, 100]), cost_form=form, site_visits=visits)
        r = assess(w, AS_OF)
        assert r.status in (Status.ASSESSED, Status.NOT_ASSESSABLE)
