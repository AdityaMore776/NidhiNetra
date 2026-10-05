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


def test_two_unusable_videos_in_a_row_are_a_note_now():
    """T137: checked every month, "the last two unusable" asked 1 honest work in 4 a year at the
    assumed error rates (data/trial/architecture_bakeoff.py site); 4 of the last 5 asks 1 in 60."""
    vs = [base(), *months(3), visit(LAST, **DARK), visit(LAST + timedelta(days=30), **PARTIAL)]
    r = assess(work(*vs), AS_OF)
    assert codes(r) == [] and "too dark" in notes(r)


def test_four_of_the_last_five_videos_unusable_is_asked():
    vs = [base(), *months(2), visit(LAST, **DARK), visit(LAST + timedelta(days=30), **PARTIAL),
          visit(LAST + timedelta(days=45)), visit(LAST + timedelta(days=60), **DARK),
          visit(LAST + timedelta(days=62), **DARK)]
    r = assess(work(*vs), AS_OF)
    assert codes(r) == ["SITE_VIDEOS_UNUSABLE"]
    assert "4 of the last 5" in r.findings[0].text


def test_every_video_so_far_unusable_is_asked_from_the_third():
    """A dodger who films three bad videos and stops is not left waiting for a fifth."""
    first = visit(date(2026, 2, 1), kind="baseline", claim=None, quality_ok=False,
                  views_match_site=None, change=None, claim_verdict=None, viewpoints_expected=0,
                  viewpoints_matched=0)
    vs = [first, visit(date(2026, 3, 1), **DARK), visit(date(2026, 4, 1), **PARTIAL)]
    assert codes(assess(work(*vs), AS_OF)) == ["SITE_VIDEOS_UNUSABLE"]
    assert codes(assess(work(*vs[:2]), AS_OF)) == []


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


def test_views_that_never_match_while_the_gps_is_at_the_site_are_asked():
    """The way round "filmed elsewhere" (needs GPS and views both): fake the GPS inside. Videos
    whose views do not match the site are unusable; 4 of the last 5 are asked."""
    off = {"views_match_site": False, "viewpoints_matched": 0, "change": "cant_tell"}
    vs = [base(), *months(2), *[visit(LAST + timedelta(days=20 * k), **off) for k in range(4)]]
    assert codes(assess(work(*vs), AS_OF)) == ["SITE_VIDEOS_UNUSABLE"]


def test_filmed_elsewhere_needs_the_gps_far_out_a_near_one_is_unusable():
    """T137: GPS jitter (60-300 m in a village) with views lost in the same video read as "filmed
    elsewhere" for 1 honest work in 130 a year; it now needs the GPS FAR_M+ out (or a mock
    location). Filming 200 m away is still caught: those views do not match the site."""
    near = {"gps_inside": False, "gps_distance_m": 180.0, "views_match_site": False,
            "viewpoints_matched": 0, "change": "cant_tell"}
    r = assess(work(base(), *months(2), visit(LAST, **near)), AS_OF)
    assert codes(r) == [] and "views do not match the site" in notes(r)
    vs = [base(), *months(2), *[visit(LAST + timedelta(days=20 * k), **near) for k in range(4)]]
    assert codes(assess(work(*vs), AS_OF)) == ["SITE_VIDEOS_UNUSABLE"]
    far = dict(near, gps_distance_m=900.0)
    assert codes(assess(work(base(), *months(2), visit(LAST, **far)), AS_OF)) == \
        ["NOT_FILMED_AT_THIS_SITE"]
    unknown = dict(near, gps_distance_m=None)          # an older reading without the distance
    assert codes(assess(work(base(), *months(2), visit(LAST, **unknown)), AS_OF)) == \
        ["NOT_FILMED_AT_THIS_SITE"]


def test_recorded_complete_without_a_final_video_is_asked_after_the_grace():
    """T137: two honest months filmed, then "complete" with no final video was only a note."""
    done = AS_OF - timedelta(days=40)
    vs = [base(), *months(2)]
    r = assess(work(*vs, status="COMPLETED", completed_date=done.isoformat()), AS_OF)
    assert codes(r) == ["COMPLETE_NOT_FILMED"]
    soon = AS_OF - timedelta(days=10)                   # inside the grace: a note
    r = assess(work(*vs, status="COMPLETED", completed_date=soon.isoformat()), AS_OF)
    assert codes(r) == []
    final = visit(done + timedelta(days=5), kind="final", complete_shown=True)
    r = assess(work(*vs, final, status="COMPLETED", completed_date=done.isoformat()), AS_OF)
    assert codes(r) == []


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
