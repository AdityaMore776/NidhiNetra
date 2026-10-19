"""Site Progress' eval fix (T168, data/eval/site_progress/holdout.py, FINDINGS "T168").

No first visit, one late-stage monthly video, then the final one: nothing filmed shows the asset
is new, and FIRST_FILMED_FINISHED (only a first video already finished) let it pass. Two progress
videos before the final are still enough (T139); one is "check this" (NO_FIRST_VISIT, risk 0.3)."""

from __future__ import annotations

from datetime import date

from drishti.agents.site_progress.agent import CHECK_RISK, assess
from tests.agents.site_progress.test_site_progress_v3 import AS_OF, codes, visit, work

FINAL = {"complete_shown": True}


def _done(*visits):
    return work(*visits, status="COMPLETED", completed_date=date(2026, 4, 30))


def test_one_late_monthly_video_then_the_final_is_check_this():
    r = assess(_done(visit(date(2026, 4, 1), claim="plastering"),
                     visit(date(2026, 5, 1), kind="final", claim="complete", **FINAL)), AS_OF)
    f = next(f for f in r.findings if f.code == "NO_FIRST_VISIT")
    assert f.risk == CHECK_RISK and "first visit" in f.text
    assert "FIRST_FILMED_FINISHED" not in codes(r)


def test_two_progress_videos_before_the_final_are_still_enough():
    r = assess(_done(visit(date(2026, 3, 1), claim="foundation laid"),
                     visit(date(2026, 4, 1), claim="walls up to lintel level"),
                     visit(date(2026, 5, 1), kind="final", claim="complete", **FINAL)), AS_OF)
    assert "NO_FIRST_VISIT" not in codes(r)


def test_a_work_still_being_built_without_a_first_visit_is_not_checked_yet():
    r = assess(work(visit(date(2026, 4, 1), claim="plastering")), AS_OF)
    assert "NO_FIRST_VISIT" not in codes(r)


def test_a_declared_upgrade_without_a_first_visit_is_not_checked():
    w = _done(visit(date(2026, 4, 1), claim="plastering"),
              visit(date(2026, 5, 1), kind="final", claim="complete", **FINAL))
    w["cost_form"] = {"work": {"nature": "upgrade", "earlier_work_id": "W0"}}
    assert "NO_FIRST_VISIT" not in codes(assess(w, AS_OF))
