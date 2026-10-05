"""Site Progress and Time & Rules (T135, the robustness loop: data/trial/agent_robustness_loop.py):
never filming, uploading only unsealed videos, slipping "can't tell" between two "not shown", vague
claims, a form pin that is not where the work is, videos dated after today, and a reused video
passing as proof that the work was built."""

from __future__ import annotations

from datetime import date, timedelta

from drishti.agents.contract import Status
from drishti.agents.site_progress.agent import NO_VIDEO_DAYS, assess
from drishti.agents.time_rules.agent import assess as time_assess
from drishti.records import status as read_status
from drishti.records import work as read_work
from tests.agents.site_progress.test_site_progress_v3 import AS_OF, base, codes, months, visit

SANCTIONED = AS_OF - timedelta(days=120)


def sanctioned(*vs, days_ago=120, **kw):
    w = {"work_id": "W1", "status": "SANCTIONED", "site_visits": list(vs),
         "sanction_date": (AS_OF - timedelta(days=days_ago)).isoformat(),
         "cost_form": {"work": {"nature": "new"}, "timing": {"duration_months": 6}}}
    w.update(kw)
    return w


def test_never_filmed_months_after_sanction_is_asked():
    r = assess(sanctioned(), AS_OF)
    assert r.status == Status.ASSESSED and codes(r) == ["NO_SITE_VIDEO"]


def test_not_yet_due_is_not_asked():
    r = assess(sanctioned(days_ago=NO_VIDEO_DAYS - 10), AS_OF)
    assert r.status == Status.NOT_APPLICABLE and not r.findings


def test_a_start_promised_years_away_buys_no_more_than_six_months():
    w = sanctioned(days_ago=400)
    w["cost_form"]["timing"]["start_month"] = "2029-01"
    assert codes(assess(w, AS_OF)) == ["NO_SITE_VIDEO"]


def test_a_record_without_a_form_is_the_old_process_and_never_asked():
    w = sanctioned()
    del w["cost_form"]
    assert assess(w, AS_OF).status == Status.NOT_APPLICABLE


def test_only_unsealed_videos_is_the_same_as_none():
    vs = [visit(SANCTIONED + timedelta(days=30 * i), sealed=False) for i in range(1, 4)]
    r = assess(sanctioned(*vs), AS_OF)
    assert "NO_SITE_VIDEO" in codes(r) and "none accepted" in r.headline


def test_cant_tell_between_two_not_shown_still_counts_twice():
    vs = [base(), *months(2),
          visit(date(2026, 5, 1), claim="roof slab cast", claim_verdict="not_shown"),
          visit(date(2026, 5, 15), claim="roof slab cast", claim_verdict="cant_tell"),
          visit(date(2026, 6, 1), claim="roof slab cast", claim_verdict="not_shown")]
    assert "CLAIM_NOT_SHOWN" in codes(assess(sanctioned(*vs), AS_OF))
    # a "shown" between them starts the count again
    vs[-2] = visit(date(2026, 5, 15), claim="roof slab cast", claim_verdict="shown")
    assert "CLAIM_NOT_SHOWN" not in codes(assess(sanctioned(*vs), AS_OF))


def test_vague_claims_are_asked_to_be_specific():
    vs = [base(), *months(3, claim="Work in progress", claim_verdict="cant_tell")]
    r = assess(sanctioned(*vs), AS_OF)
    assert any("vague" in n for n in r.evidence["notes"])


def test_filmed_every_time_away_from_the_forms_pin():
    vs = [base(gps_inside=False, gps_distance_m=320.0),
          *months(3, gps_inside=False, gps_distance_m=310.0)]
    r = assess(sanctioned(*vs), AS_OF)
    assert codes(r) == ["SITE_NOT_AT_FORM_PIN"]
    # one bad GPS fix is GPS error, never a question
    vs = [base(), *months(2), visit(date(2026, 7, 1), gps_inside=False, gps_distance_m=300.0)]
    assert not codes(assess(sanctioned(*vs), AS_OF))


def test_a_video_dated_after_today_is_not_counted():
    vs = [base(), *months(2), visit(AS_OF + timedelta(days=30), claim="road complete")]
    r = assess(sanctioned(*vs), AS_OF)
    assert any("after today" in n for n in r.evidence["notes"])
    assert len(r.evidence["visits"]) == 3


def test_a_reused_video_does_not_prove_a_fast_finish():
    san = date(2026, 6, 24)
    w = {"work_id": "W1", "status": "COMPLETED", "work_type_code": "ROAD_CC", "amount": 1.7e6,
         "recommended_date": "2026-05-15", "sanction_date": san.isoformat(),
         "completed_date": (san + timedelta(days=6)).isoformat(),
         "cost_form": {"work": {"work_type": "ROAD_CC"},
                       "timing": {"duration_months": 4, "start_month": "2026-07"}},
         "site_visits": [visit(san + timedelta(days=1), kind="baseline", claim=None,
                               views_match_site=None, change=None, claim_verdict=None),
                         visit(san + timedelta(days=4), claim="concrete laid",
                               reused_from=[{"work_id": "W9", "visit_id": "V3",
                                             "frames": 60}])]}
    r = time_assess(w, AS_OF)
    assert "FINISHED_TOO_FAST" in [f.code for f in r.findings]


def test_complete_without_a_date_says_so():
    w = {"work_id": "W1", "status": "COMPLETED", "work_type_code": "ROAD_CC",
         "sanction_date": "2026-06-24", "cost_form": {"timing": {"duration_months": 4}}}
    r = time_assess(w, AS_OF)
    assert any("without a completion date" in s for s in r.limitations)


def test_a_status_reads_the_same_in_any_case():
    assert read_status("completed ") == read_status("Completed") == "COMPLETED"
    assert read_status("complete") == "COMPLETED"
    assert read_work({"status": "sanctioned"})["status"] == "SANCTIONED"
    assert read_status(None) is None
