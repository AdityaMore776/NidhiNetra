"""Site Progress v3 (T124, plan T120 §9): the monthly videos' readings judged.

Findings only for yes-or-no facts (the same frames, the same place, the wrong place) or the
agency's own claim failing twice; one bad month, GPS error alone, or "can't tell" never count."""

from __future__ import annotations

import json
import random
from datetime import date, timedelta

import pytest

from drishti.agents.contract import Status, check_plain_language
from drishti.agents.site_progress import sitemap, visits
from drishti.agents.site_progress.agent import MIN_INLIERS, MIN_REUSED_FRAMES, assess

AS_OF = date(2026, 10, 2)
GOOD = {"sealed": True, "in_app": True, "gps_inside": True, "mock_location": False,
        "views_match_site": True, "quality_ok": True, "viewpoints_expected": 5,
        "viewpoints_matched": 5, "zones_shown": ["v1", "v2", "v3", "v4", "v5"],
        "change": "changed", "claim_verdict": "shown"}


def visit(day: date, kind="monthly", claim="walls up to lintel level", **readings):
    return {"visit_id": f"{kind}-{day.isoformat()}", "kind": kind, "captured_at": day.isoformat(),
            "claim": claim, "readings": {**GOOD, **readings}}


def work(*vs, **kw):
    w = {"work_id": "W1", "status": "SANCTIONED", "site_visits": list(vs),
         "cost_form": {"work": {"nature": "new"}}}
    w.update(kw)
    return w


def months(n, start=date(2026, 3, 1), **readings):
    return [visit(start + timedelta(days=30 * i), **readings) for i in range(n)]


def codes(r):
    return [f.code for f in r.findings]


def base(**readings):
    return visit(date(2026, 2, 1), kind="baseline", claim=None, views_match_site=None,
                 change=None, claim_verdict=None, **readings)


# --- statuses ----------------------------------------------------------------------------------

def test_no_visit_is_not_applicable_never_a_clean_chit():
    r = assess({"work_id": "W1"}, AS_OF)
    assert r.status == Status.NOT_APPLICABLE and "not a clean chit" in r.headline


def test_visits_not_read_yet_are_not_assessable():
    r = assess(work({"visit_id": "a", "kind": "monthly", "captured_at": "2026-03-01"}), AS_OF)
    assert r.status == Status.NOT_ASSESSABLE and r.risk == 0


def test_honest_monthly_visits_raise_nothing():
    r = assess(work(base(), *months(4)), date(2026, 6, 15))
    assert r.status == Status.ASSESSED and not r.findings and r.verdict == "PROGRESS_AS_SHOWN"
    assert len(r.evidence["visits"]) == 5


# --- the yes-or-no facts ----------------------------------------------------------------------

def test_footage_seen_on_another_work():
    r = assess(work(base(), visit(date(2026, 3, 1),
                                  reused_from=[{"work_id": "W9", "visit_id": "x", "frames": 12}])),
               AS_OF)
    f = r.findings[0]
    assert f.code == "FOOTAGE_USED_BEFORE" and f.risk == 0.8 and "work W9" in f.text


def test_footage_from_this_works_own_earlier_visit_is_reuse_too():
    r = assess(work(base(), visit(date(2026, 3, 1),
                                  reused_from=[{"work_id": "W1", "visit_id": "y", "frames": 30}])),
               AS_OF)
    assert "an earlier visit of this same work" in r.findings[0].text


def test_a_couple_of_matching_frames_are_not_reuse():
    r = assess(work(base(), visit(date(2026, 3, 1), reused_from=[
        {"work_id": "W9", "visit_id": "x", "frames": MIN_REUSED_FRAMES - 1}])), AS_OF)
    assert "FOOTAGE_USED_BEFORE" not in codes(r)


def test_the_same_place_as_another_undeclared_work():
    same = [{"work_id": "W7", "inliers": MIN_INLIERS + 20}]
    assert "SAME_PLACE_AS_ANOTHER_WORK" in codes(
        assess(work(base(), visit(date(2026, 3, 1), same_place_as=same)), AS_OF))
    declared = work(base(), visit(date(2026, 3, 1), same_place_as=same),
                    cost_form={"work": {"nature": "continuation", "earlier_work_id": "W7"}})
    assert "SAME_PLACE_AS_ANOTHER_WORK" not in codes(assess(declared, AS_OF))
    weak = [{"work_id": "W7", "inliers": MIN_INLIERS - 1}]
    assert "SAME_PLACE_AS_ANOTHER_WORK" not in codes(
        assess(work(base(), visit(date(2026, 3, 1), same_place_as=weak)), AS_OF))


def test_not_at_this_site_needs_gps_and_views_both():
    both = visit(date(2026, 3, 1), gps_inside=False, gps_distance_m=850, views_match_site=False)
    f = assess(work(base(), both), AS_OF).findings[0]
    assert f.code == "NOT_FILMED_AT_THIS_SITE" and "850 m outside" in f.text
    gps_only = assess(work(base(), visit(date(2026, 3, 1), gps_inside=False)), AS_OF)
    assert not gps_only.findings and any("GPS error" in n for n in gps_only.evidence["notes"])
    views_only = assess(work(base(), visit(date(2026, 3, 1), views_match_site=False)), AS_OF)
    assert not views_only.findings


def test_a_mock_location_counts_as_gps_out():
    v = visit(date(2026, 3, 1), mock_location=True, views_match_site=False)
    assert "mock location" in assess(work(base(), v), AS_OF).findings[0].text


# --- the agency's own claim -------------------------------------------------------------------

def test_one_month_not_shown_is_never_enough():
    vs = months(3)
    vs[1]["readings"]["claim_verdict"] = "not_shown"
    assert "CLAIM_NOT_SHOWN" not in codes(assess(work(base(), *vs), AS_OF))


def test_two_visits_in_a_row_not_shown_is_asked():
    vs = months(3)
    for v in vs[1:]:
        v["readings"].update(claim_verdict="not_shown", claim_reason="the roof is not cast")
    f = next(f for f in assess(work(base(), *vs), AS_OF).findings if f.code == "CLAIM_NOT_SHOWN")
    assert f.risk == 0.5 and "two visits in a row" in f.text and "roof is not cast" in f.text


def test_cant_tell_is_a_note_never_a_finding():
    vs = months(3, claim_verdict="cant_tell")
    r = assess(work(base(), *vs), AS_OF)
    assert not r.findings and any("could not be judged" in n for n in r.evidence["notes"])


# --- complete, and already built --------------------------------------------------------------

def test_a_final_video_not_showing_the_work_finished():
    final = visit(date(2026, 8, 1), kind="final", complete_shown=False)
    r = assess(work(base(), *months(2), final, status="COMPLETED"), AS_OF)
    assert "COMPLETE_NOT_SHOWN" in codes(r)


def test_recorded_complete_without_a_final_video_is_a_note():
    r = assess(work(base(), *months(2), status="COMPLETED"), AS_OF)
    assert not r.findings and any("no final site video" in n for n in r.evidence["notes"])


def test_already_built_at_the_start_of_a_new_work():
    assert "ALREADY_BUILT_AT_START" in codes(assess(work(base(asset_at_start=True)), AS_OF))
    upgrade = work(base(asset_at_start=True), cost_form={"work": {"nature": "upgrade"}})
    assert "ALREADY_BUILT_AT_START" not in codes(assess(upgrade, AS_OF))


# --- not accepted, missed and still ----------------------------------------------------------

def test_an_unsealed_or_gallery_video_is_not_accepted_and_proves_nothing():
    bad = visit(date(2026, 3, 1), sealed=False, gps_inside=False, views_match_site=False)
    r = assess(work(base(), bad), AS_OF)
    assert "NOT_FILMED_AT_THIS_SITE" not in codes(r)
    assert any("not accepted" in n for n in r.evidence["notes"])


def test_missed_months_and_no_change_are_notes():
    vs = [visit(date(2026, 3, 1), change="no_change"), visit(date(2026, 6, 1), change="no_change")]
    r = assess(work(base(), *vs), AS_OF)
    assert not r.findings
    notes = " ".join(r.evidence["notes"])
    assert "No visit between" in notes and "this month's is due" in notes and "No change" in notes


def test_every_text_plain_with_hindi_and_json_safe():
    vs = [base(asset_at_start=True),
          visit(date(2026, 3, 1), reused_from=[{"work_id": "W9", "frames": 9}],
                same_place_as=[{"work_id": "W8", "inliers": 99}], gps_inside=False,
                views_match_site=False),
          visit(date(2026, 4, 1), claim_verdict="not_shown"),
          visit(date(2026, 5, 1), kind="final", claim_verdict="not_shown", complete_shown=False)]
    r = assess(work(*vs, status="COMPLETED"), AS_OF)
    assert len(r.findings) == 6
    check_plain_language(r.headline)
    for f in r.findings:
        check_plain_language(f.text)
        assert f.evidence["message_hi"]
    json.dumps(r.to_json(), default=str)


def test_damaged_visits_never_break_it():
    rng = random.Random(3)
    junk = [None, "", 0, -1, 1e9, "x", [], {}, [1, "a"], {"a": None}, True, float("nan")]
    for _ in range(400):
        v = {k: rng.choice(junk + [val]) for k, val in
             {"visit_id": "v", "kind": "monthly", "captured_at": "2026-03-01",
              "claim": "x", "readings": {k: rng.choice(junk + [x]) for k, x in GOOD.items()}
              | {"reused_from": rng.choice(junk + [[{"work_id": "W2", "frames": "7"}]])}}.items()}
        r = assess(work(v, rng.choice(junk)), AS_OF)
        assert r.status in (Status.ASSESSED, Status.NOT_ASSESSABLE, Status.NOT_APPLICABLE)
    assert visits.of({"site_visits": "junk"}) == []


# --- the site map -----------------------------------------------------------------------------

def test_a_compact_site_with_the_gps_margin():
    s = sitemap.site_of({"work": {"work_type": "COMMUNITY_HALL"},
                         "sites": [{"location": {"lat": 25.75, "lon": 82.69},
                                    "size": {"built_up_area_m2": 400}}]})
    assert s.kind == "compact" and s.radius_m == 25
    assert s.inside(25.75, 82.69) and s.inside(25.75 + 40 / 111_195, 82.69)      # 40 m: margin
    assert not s.inside(25.75 + 60 / 111_195, 82.69)


def test_a_linear_site_in_50_m_stretches():
    s = sitemap.site_of({"work": {"work_type": "ROAD_CC"},
                         "sites": [{"location": {"lat": 25.75, "lon": 82.69,
                                                 "end_lat": 25.752, "end_lon": 82.69}}]})
    assert s.kind == "linear" and s.length_m == pytest.approx(222.4, abs=0.5)
    assert s.stretches() == ["s1", "s2", "s3", "s4", "s5"]
    assert s.stretch_of(25.75 + 10 / 111_195, 82.69) == "s1"
    assert s.stretch_of(25.75 + 120 / 111_195, 82.69) == "s3"
    assert s.stretch_of(25.76, 82.69) is None                          # 1 km past the end


def test_no_pin_no_site():
    assert sitemap.site_of(None) is None
    assert sitemap.site_of({"sites": [{"location": {"lat": "x"}}]}) is None
