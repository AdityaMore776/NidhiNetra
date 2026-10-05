"""Site Progress gives room for error and still does its job (T136).

A person filming a site gets things wrong: a dark evening, a short clip, a viewpoint blocked by a
truck, weak GPS under trees, a month missed. None of these is a finding on its own. Two unusable
videos in a row are: otherwise filming badly every month would be a way past every check."""

from __future__ import annotations

from datetime import date, timedelta

from drishti.agents.site_progress.agent import assess
from drishti.agents.site_progress.visits import of as read_visits
from drishti.agents.site_progress.visits import unusable
from tests.agents.site_progress.test_site_progress_v3 import AS_OF, base, codes, months, visit, work

DARK = {"quality_ok": False, "views_match_site": None, "change": "cant_tell",
        "claim_verdict": "cant_tell", "viewpoints_matched": 0}
PARTIAL = {"views_match_site": None, "viewpoints_matched": 1, "change": "cant_tell"}
LAST = date(2026, 3, 1) + timedelta(days=30 * 4)


def notes(r) -> str:
    return " ".join(r.evidence["notes"])


def test_one_dark_video_between_good_ones_is_a_note_not_a_finding():
    vs = [base(), *months(2), visit(date(2026, 5, 1), **DARK), *months(2, start=LAST)]
    r = assess(work(*vs), AS_OF)
    assert codes(r) == [] and "too dark, blurred or short" in notes(r)


def test_the_last_two_videos_unusable_is_asked():
    vs = [base(), *months(3), visit(LAST, **DARK), visit(LAST + timedelta(days=30), **PARTIAL)]
    r = assess(work(*vs), AS_OF)
    assert codes(r) == ["SITE_VIDEOS_UNUSABLE"]
    assert "too dark" in r.findings[0].text and "viewpoints not filmed" in r.findings[0].text


def test_two_unusable_then_a_good_one_is_not_asked():
    vs = [base(), *months(2), visit(LAST, **DARK), visit(LAST + timedelta(days=30), **DARK),
          visit(LAST + timedelta(days=60))]
    assert codes(assess(work(*vs), AS_OF)) == []


def test_a_dark_video_is_never_proof_of_filming_elsewhere():
    vs = [base(), *months(2), visit(LAST, quality_ok=False, gps_inside=False,
                                    gps_distance_m=900.0, views_match_site=False)]
    r = assess(work(*vs), AS_OF)
    assert "NOT_FILMED_AT_THIS_SITE" not in codes(r)


def test_a_claim_not_shown_on_two_dark_videos_is_not_asked():
    vs = [base(), *months(2), visit(LAST, claim="roof slab cast", claim_verdict="not_shown",
                                    quality_ok=False),
          visit(LAST + timedelta(days=30), claim="roof slab cast", claim_verdict="not_shown",
                quality_ok=False)]
    r = assess(work(*vs), AS_OF)
    assert "CLAIM_NOT_SHOWN" not in codes(r)


def test_most_viewpoints_found_again_is_a_note():
    vs = [base(), *months(3, viewpoints_matched=3)]
    r = assess(work(*vs), AS_OF)
    assert codes(r) == [] and "found 3 of the site's" in notes(r)


def test_skipped_viewpoints_and_weak_gps_are_notes():
    vs = [base(), *months(2), visit(LAST, viewpoints_skipped=["v4"], gps_weak=True,
                                    gps_inside=None)]
    r = assess(work(*vs), AS_OF)
    assert codes(r) == []
    assert "v4 could not be filmed" in notes(r) and "GPS was too weak" in notes(r)


def test_filmed_elsewhere_is_one_finding_not_two():
    out = {"gps_inside": False, "gps_distance_m": 2400.0, "views_match_site": False,
           "viewpoints_matched": 0}
    vs = [base(), *months(2), visit(LAST, **out), visit(LAST + timedelta(days=30), **out)]
    r = assess(work(*vs), AS_OF)
    assert codes(r) == ["NOT_FILMED_AT_THIS_SITE"]


def test_readings_that_were_never_made_say_nothing():
    v = read_visits(work(visit(LAST, claim=None)))[0]
    v.readings = {k: None for k in v.readings}
    assert unusable(v) is None


def test_views_that_never_match_while_the_gps_is_at_the_site_twice_is_asked():
    """The way round "filmed elsewhere" (needs GPS and views both): fake the GPS inside. Two
    videos in a row whose views do not match the site are asked about, with a lower weight."""
    off = {"views_match_site": False, "viewpoints_matched": 0, "change": "cant_tell"}
    vs = [base(), *months(2), visit(LAST, **off), visit(LAST + timedelta(days=30), **off)]
    assert codes(assess(work(*vs), AS_OF)) == ["SITE_VIDEOS_UNUSABLE"]


def test_complete_with_not_one_video_is_asked_at_once():
    """T136: "complete" just past Time & Rules' early line, checked the next day, went unasked
    until 60 days after the planned start."""
    san = AS_OF - timedelta(days=40)
    w = work(sanction_date=san.isoformat(), status="COMPLETED",
             completed_date=(AS_OF - timedelta(days=1)).isoformat())
    w["cost_form"]["timing"] = {"start_month": san.isoformat()[:7]}
    r = assess(w, AS_OF)
    assert codes(r) == ["NO_SITE_VIDEO"] and "Recorded complete" in r.headline
    # open, and not yet 60 days past the start: not due, not asked
    w.update(status="SANCTIONED", completed_date=None)
    assert codes(assess(w, AS_OF)) == []
