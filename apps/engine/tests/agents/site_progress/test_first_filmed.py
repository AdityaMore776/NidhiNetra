"""Site Progress: a work first filmed already finished (T139).

On Jaunpur's real dates 532 of 1,025 completed works (most of them solar street lights) were closed
within the month of their sanction. An honest agency films a first video before work and a final
one; with no first video, ALREADY_BUILT_AT_START could never be asked, so an old asset filmed once
as the "final" video passed as new. Progress filmed in between is enough: only a work whose first
video already shows it finished is asked."""

from __future__ import annotations

from datetime import date

from drishti.agents.site_progress.agent import assess
from tests.agents.site_progress.test_site_progress_v3 import AS_OF, base, codes, visit, work

FINAL = {"complete_shown": True}


def test_only_a_final_video_for_a_new_work_is_asked():
    r = assess(work(visit(date(2026, 4, 10), kind="final", claim="complete", **FINAL),
                    status="COMPLETED", completed_date=date(2026, 4, 9)), AS_OF)
    assert codes(r) == ["FIRST_FILMED_FINISHED"]
    assert r.findings[0].risk > 0 and "before work started" in r.findings[0].text


def test_a_first_monthly_video_already_showing_it_complete_is_asked():
    r = assess(work(visit(date(2026, 4, 10), claim="complete", **FINAL)), AS_OF)
    assert "FIRST_FILMED_FINISHED" in codes(r)


def test_a_first_video_and_a_final_one_on_the_same_day_is_not_asked():
    # a light installed in an hour: the first video before, the final after
    day = date(2026, 4, 10)
    first = base()
    first["captured_at"] = day.isoformat()
    r = assess(work(first, visit(day, kind="final", claim="complete", **FINAL),
                    status="COMPLETED", completed_date=day), AS_OF)
    assert "FIRST_FILMED_FINISHED" not in codes(r)


def test_progress_filmed_before_the_final_video_is_not_asked():
    r = assess(work(visit(date(2026, 3, 1), claim="foundation laid"),
                    visit(date(2026, 4, 1), claim="walls up to lintel level"),
                    visit(date(2026, 5, 1), kind="final", claim="complete", **FINAL),
                    status="COMPLETED", completed_date=date(2026, 4, 30)), AS_OF)
    assert "FIRST_FILMED_FINISHED" not in codes(r)


def test_a_declared_upgrade_filmed_only_at_the_end_is_not_asked():
    w = work(visit(date(2026, 4, 10), kind="final", claim="complete", **FINAL),
             status="COMPLETED", completed_date=date(2026, 4, 9))
    w["cost_form"] = {"work": {"nature": "upgrade", "earlier_work_id": "W0"}}
    assert "FIRST_FILMED_FINISHED" not in codes(assess(w, AS_OF))
