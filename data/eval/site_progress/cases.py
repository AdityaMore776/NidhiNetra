"""Site Progress' eval cases (T168): do the monthly site videos show real, new work, at this work's
site, for this work only? Labelled before the first run; plan docs/plans/T168-agent-evals.md §3.

Each case is a filing with the site videos as the video job leaves its readings
(work_form_examples.visit: sealed, filmed in the app, at the site, five viewpoints matched, unless
the case says otherwise). The agent judges the readings; NidhiLens (the reader that writes
claim_verdict) is tested on real photos in data/eval/nidhilens/.
"""

from __future__ import annotations

import sys
import zlib
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
from world import AGENCY, Case, filed, m  # noqa: E402  (first: it sets the paths)

import work_form_examples as wf  # noqa: E402

AG = "site_progress"


def case(id, truth, ideal, allowed, family, story, why, work, extra=list, pair=None,
         scope="self"):
    return Case(id, AG, truth, ideal, tuple(allowed.split("/")), family, story, why, work, extra,
                pair, scope)


def v(n, kind, days_ago, change="changed", claim="walls rising", verdict="shown", **more):
    if kind == "baseline":
        return wf.visit(n, kind, m(days_ago), **more)
    return wf.visit(n, kind, m(days_ago), change, claim, verdict, **more)


def hall(ref, sanction_days_ago=200, **over):
    k = zlib.crc32(ref.encode()) % 50
    san = m(sanction_days_ago)
    return wf.hall(ref, AGENCY, "Kusumi", k, san - timedelta(days=30), san,
                   start=san + timedelta(days=20), **over)


def built(ref, visits, status="SANCTIONED", sanction_days_ago=200, done_days_ago=None, **over):
    rec = {"status": status, "site_visits": visits}
    if done_days_ago is not None:
        rec["completed_date"] = m(done_days_ago).isoformat()
    return filed(hall(ref, sanction_days_ago, **over), **rec)


def honest_months(n=5, start=180) -> list[dict]:
    """A first visit, then a month of new work at a time, the claim shown."""
    return [v(1, "baseline", start)] + [v(i + 2, "monthly", start - 30 * (i + 1),
                                          claim=f"stage {i + 1} done") for i in range(n)]


def cases() -> list[Case]:
    out = []
    # ---- honest -------------------------------------------------------------------------------
    out.append(case(
        "S-H1-honest-months", "honest", "fits", "fits/edge", "honest",
        "A first visit, then five monthly videos of new work, each claim shown.",
        "Nothing to check.",
        lambda: built("SH1", honest_months())))
    out.append(case(
        "S-H2-one-dark-month", "edge", "fits", "fits/edge", "room for error",
        "Honest months, one of them filmed at dusk (too dark).",
        "One poor video is forgiven (T136).",
        lambda: built("SH2", honest_months()[:3] + [
            v(4, "monthly", 90, None, "stage 3 done", None, quality_ok=False)] +
            honest_months()[4:]), pair="dark"))
    out.append(case(
        "S-H3-gps-jitter", "edge", "fits", "fits/edge", "room for error",
        "Honest months; on two of them the GPS wandered 60 m outside the site, views matching.",
        "GPS error alone never fails a video.",
        lambda: built("SH3", [x if i not in (2, 4) else {**x, "readings": {
            **x["readings"], "gps_inside": False, "gps_distance_m": 60}}
            for i, x in enumerate(honest_months())]), pair="gps"))
    out.append(case(
        "S-H4-monsoon-pause", "edge", "fits", "fits/edge", "honest",
        "Two monthly videos in the monsoon show no change; the claims say 'work paused for rain'.",
        "A pause shown honestly is a note.",
        lambda: built("SH4", honest_months(3) + [
            v(10, "monthly", 60, "no_change", "work paused for rain", "cant_tell"),
            v(11, "monthly", 30, "no_change", "work paused for rain", "cant_tell")])))
    out.append(case(
        "S-H5-declared-upgrade", "edge", "fits", "fits/edge", "honest",
        "An upgrade of an existing hall: the first visit shows the old hall, as the form says.",
        "An existing asset the form declares.",
        lambda: built("SH5", [v(1, "baseline", 180, asset_at_start=True)] +
                      honest_months()[1:], work_nature="Repair / renovation")))
    out.append(case(
        "S-H6-complete-filmed", "honest", "fits", "fits/edge", "honest",
        "Complete, with a final video showing every part finished.",
        "Nothing to check.",
        lambda: built("SH6", honest_months() + [v(9, "final", 20, claim="complete",
                                                  complete_shown=True)],
                      status="COMPLETED", done_days_ago=25)))

    # ---- fraud --------------------------------------------------------------------------------
    out.append(case(
        "S-F1-footage-reused", "fraud", "ask", "ask", "reuse",
        "The third video reuses 42 frames of another hall's video.",
        "Not new filming.",
        lambda: built("SF1", honest_months()[:2] + [
            v(3, "monthly", 120, reused_from=[{"work_id": "WF-TIME-2", "visit_id": "V3",
                                               "frames": 42}])] + honest_months()[3:])))
    out.append(case(
        "S-F2-filmed-elsewhere", "fraud", "ask", "ask", "elsewhere",
        "A monthly video filmed 2.4 km away; its views do not match the site.",
        "GPS and views both say elsewhere.",
        lambda: built("SF2", honest_months()[:3] + [
            v(4, "monthly", 90, None, "roof cast", None, gps_inside=False, gps_distance_m=2400,
              views_match_site=False, viewpoints_matched=0)]), pair="gps"))
    out.append(case(
        "S-F3-claim-not-shown-twice", "fraud", "ask", "ask", "claim",
        "'Roof slab cast' claimed twice; neither video shows a slab.",
        "The claim failing twice in a row.",
        lambda: built("SF3", honest_months(2) + [
            v(5, "monthly", 90, claim="roof slab cast", verdict="not_shown"),
            v(6, "monthly", 60, "no_change", "roof slab cast, plaster", "not_shown")])))
    out.append(case(
        "S-F4-complete-not-shown", "fraud", "ask", "ask", "complete",
        "Recorded complete; the final video shows unfinished parts.",
        "Complete, not shown complete.",
        lambda: built("SF4", honest_months() + [v(9, "final", 20, claim="complete",
                                                  complete_shown=False)],
                      status="COMPLETED", done_days_ago=25)))
    out.append(case(
        "S-F5-already-built", "fraud", "ask", "ask", "built before",
        "A 'new' hall whose first visit already shows a hall standing.",
        "Built before sanction, or another scheme's hall.",
        lambda: built("SF5", [v(1, "baseline", 180, asset_at_start=True)] +
                      honest_months()[1:])))
    out.append(case(
        "S-F6-never-filmed", "fraud", "ask", "ask", "no video",
        "Sanctioned 200 days ago; not one site video.",
        "Never filming dodges every other check.",
        lambda: built("SF6", [])))
    out.append(case(
        "S-F7-same-place", "fraud", "ask", "ask", "reuse",
        "The site's viewpoints show the same place as another work's videos.",
        "One site shown for two works.",
        lambda: built("SF7", [v(1, "baseline", 180, same_place_as=[
            {"work_id": "WF-TIME-2", "inliers": 600}])] + honest_months()[1:])))

    # ---- evasion ------------------------------------------------------------------------------
    out.append(case(
        "S-V1-cant-tell-between", "evasion", "ask", "ask", "claim",
        "The false claim not shown, then a 'can't tell' month, then not shown again.",
        "T135: a 'can't tell' between does not reset the count.",
        lambda: built("SV1", honest_months(2) + [
            v(5, "monthly", 120, claim="roof slab cast", verdict="not_shown"),
            v(6, "monthly", 90, claim="roof slab cast", verdict="cant_tell"),
            v(7, "monthly", 60, claim="roof slab cast", verdict="not_shown")])))
    out.append(case(
        "S-V2-film-badly-every-month", "evasion", "ask", "check/ask", "room for error",
        "Every monthly video too dark or too short to show anything.",
        "Filming badly every month would dodge every check (T137).",
        lambda: built("SV2", [v(1, "baseline", 180)] + [
            v(i + 2, "monthly", 150 - 30 * i, None, "work going on", None, quality_ok=False)
            for i in range(5)]), pair="dark"))
    out.append(case(
        "S-V3-mock-location", "evasion", "ask", "ask", "elsewhere",
        "A monthly video from a phone reporting a mock location; its views do not match.",
        "A faked GPS and other views.",
        lambda: built("SV3", honest_months(3) + [
            v(6, "monthly", 60, None, "plaster done", None, mock_location=True,
              views_match_site=False, viewpoints_matched=0)])))
    out.append(case(
        "S-V4-skip-first-visit", "evasion", "ask", "check/ask", "built before",
        "No first visit; the first video is the final one, showing a finished hall.",
        "Nothing shows the asset is new (T139).",
        lambda: built("SV4", [v(1, "final", 20, claim="complete", complete_shown=True)],
                      status="COMPLETED", done_days_ago=25)))
    out.append(case(
        "S-V5-unsealed-only", "evasion", "ask", "ask", "no video",
        "Five uploads, none sealed or filmed in the app.",
        "None accepted: as if never filmed.",
        lambda: built("SV5", [v(i + 1, "monthly" if i else "baseline", 180 - 30 * i,
                                sealed=False) for i in range(5)])))
    out.append(case(
        "S-V6-pin-150m-off", "evasion", "ask", "check/ask", "elsewhere",
        "Every video filmed about 150 m from the form's pin, views matching each other.",
        "The work is not where the form says (T135).",
        lambda: built("SV6", [x if x["kind"] == "baseline" else {**x, "readings": {
            **x["readings"], "gps_inside": False, "gps_distance_m": 150 + 5 * i}}
            for i, x in enumerate(honest_months())])))
    out.append(case(
        "S-V7-few-reused-frames", "evasion", "ask", "check/ask", "reuse",
        "A monthly video re-encoded so that only 3 frames match another work's footage.",
        "MIN_REUSED_FRAMES is 3: still the same footage.",
        lambda: built("SV7", honest_months()[:3] + [
            v(4, "monthly", 90, reused_from=[{"work_id": "WF-TIME-2", "visit_id": "V3",
                                              "frames": 3}])] + honest_months()[4:])))
    out.append(case(
        "S-V8-complete-no-final", "evasion", "ask", "check/ask", "complete",
        "Recorded complete 90 days ago after two monthly videos; no final video ever.",
        "T137: complete must be filmed complete.",
        lambda: built("SV8", honest_months(2), status="COMPLETED", done_days_ago=90)))

    # ---- broken -------------------------------------------------------------------------------
    out.append(case(
        "S-B1-not-read-yet", "broken", "na", "na", "broken",
        "Three videos uploaded; the video job has not read them yet.",
        "Filmed, unread: couldn't check.",
        lambda: built("SB1", [{"visit_id": f"V{i}", "kind": "monthly",
                               "captured_at": m(90 - 30 * i).isoformat(), "readings": {}}
                              for i in range(3)])))
    out.append(case(
        "S-B2-not-sanctioned", "broken", "na", "na", "broken",
        "Not sanctioned yet, no video (the first is filmed before work).",
        "The question does not arise yet.",
        lambda: filed(hall("SB2", sanction_decision=""))))
    out.append(case(
        "S-B3-future-dated", "broken", "na", "na/edge/check/ask", "broken",
        "The only videos are dated next month (a phone's wrong clock).",
        "Not counted; not a clean chit.",
        lambda: built("SB3", [v(1, "baseline", -20), v(2, "monthly", -40)],
                      sanction_days_ago=40)))
    return out
