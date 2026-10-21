"""Time & Rules' eval fixes (T168, data/eval/time_rules/, FINDINGS "T168").

A video filmed on the day the work is called complete (or the final video) does not show the work
going on: it never clears "finished too fast". A work recorded complete without a completion date
cannot be judged for its pace: "couldn't check", never a clean chit."""

from datetime import date, timedelta

from drishti.agents.contract import Status
from drishti.agents.time_rules.agent import assess
from tests.agents.time_rules.test_time_rules import AS_OF, _codes, _form, _visit, _work

SAN = date(2026, 6, 1)
DONE = SAN + timedelta(days=6)


def _fast(visits):
    return _work(status="COMPLETED", sanction_date=SAN, completed_date=DONE,
                 cost_form=_form(months=4, start="2026-06"), site_visits=visits)


def test_one_video_on_the_completion_day_does_not_clear_a_fast_finish():
    r = assess(_fast([_visit(DONE)]), AS_OF)
    assert "FINISHED_TOO_FAST" in _codes(r), r.headline


def test_the_final_video_alone_does_not_clear_a_fast_finish():
    r = assess(_fast([_visit(SAN + timedelta(days=1), kind="baseline", change=None),
                      _visit(DONE - timedelta(days=1), kind="final")]), AS_OF)
    assert "FINISHED_TOO_FAST" in _codes(r), r.headline


def test_videos_of_the_work_going_on_before_the_finish_still_clear_it():
    r = assess(_fast([_visit(SAN + timedelta(days=1), kind="baseline", change=None),
                      _visit(SAN + timedelta(days=3), kind="check"),
                      _visit(DONE - timedelta(days=1))]), AS_OF)
    assert "FINISHED_TOO_FAST" not in _codes(r), r.headline


def test_complete_without_a_completion_date_is_not_a_clean_chit():
    r = assess(_work(status="COMPLETED", sanction_date=date(2026, 5, 1), completed_date=None),
               AS_OF)
    assert r.status == Status.NOT_ASSESSABLE and r.risk == 0
    assert "completion date" in r.headline and "not a clean chit" in r.headline


def test_sanctioned_before_it_was_recommended_is_a_note_never_a_clean_chit():
    r = assess(_work(recommended_date=date(2026, 3, 1), sanction_date=date(2026, 1, 30)), AS_OF)
    f = next(f for f in r.findings if f.code == "SANCTIONED_BEFORE_RECOMMENDED")
    assert 0 < f.risk < 0.1 and "impossible order" in f.text
    near = assess(_work(recommended_date=date(2026, 3, 1), sanction_date=date(2026, 2, 26)), AS_OF)
    assert "SANCTIONED_BEFORE_RECOMMENDED" not in _codes(near)      # a few days: a typing slip
