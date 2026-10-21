"""The four agents together (T168, data/eval/pipeline/): two fixes the band test found.

- Time & Rules: a stalled site is the last three READABLE videos showing no change; a video with
  no change reading between them no longer resets the count (as T135 did for "can't tell" claims).
- Duplicate Work: a looser split whose other pieces the agency names as earlier phases of the same
  asset is still "check this", but its own code at the 1-in-4 prior (claimed leeway softens, never
  clears): the real works' 15 of 20 were read without any such declaration."""

from __future__ import annotations

from datetime import date, timedelta

from drishti.agents.dup_split.agent import assess as dup
from drishti.agents.dup_split.repeat import RepeatIndex
from drishti.agents.time_rules.agent import STALLED_RISK
from drishti.agents.time_rules.agent import assess as timing
from tests.agents.dup_split.test_dup_split import ROAD, _filler, _w
from tests.agents.time_rules.test_time_rules import AS_OF, _form, _visit, _work


def _late(changes):
    start = date(2025, 2, 1)
    vs = [_visit(start, kind="baseline", change=None)]
    vs += [_visit(start + timedelta(days=30 * (i + 1)), change=c) for i, c in enumerate(changes)]
    return _work(sanction_date=date(2025, 1, 20), cost_form=_form(months=4, start="2025-02"),
                 site_visits=vs)


def test_an_unreadable_video_between_still_videos_does_not_reset_the_stall():
    r = timing(_late(["changed"] * 6 + ["no_change", None, "no_change", "no_change"]), AS_OF)
    f = next(f for f in r.findings if f.code == "PAST_PROMISED_TIME")
    assert f.risk == STALLED_RISK and f.evidence["stalled"]


def test_a_change_among_the_last_videos_is_not_a_stall():
    r = timing(_late(["changed"] * 6 + ["no_change", "changed", "no_change", "no_change"]), AS_OF)
    f = next(f for f in r.findings if f.code == "PAST_PROMISED_TIME")
    assert not f.evidence["stalled"]


def _phases(declared: bool):
    first = date(2024, 12, 1)
    pieces = [_w(f"P{i}", f"{ROAD} reach-{i + 1}", a, rec=first + timedelta(days=40 * i),
                 wtype="ROAD_CC") for i, a in enumerate((499_000, 499_500))]
    if declared:
        pieces[1]["cost_form"] = {"work": {"work_type": "ROAD_CC", "nature": "continuation",
                                           "earlier_work_id": "P0"}}
    return pieces


def test_a_declared_phase_is_check_this_at_the_prior():
    pieces = _phases(True)
    r = dup(pieces[1], RepeatIndex.build(_filler() + pieces))
    assert [f.code for f in r.findings if f.risk > 0] == ["SPLIT_NEAR_LIMIT_DECLARED"]
    assert "names" in r.headline


def test_an_undeclared_one_keeps_the_measured_code():
    pieces = _phases(False)
    r = dup(pieces[1], RepeatIndex.build(_filler() + pieces))
    assert [f.code for f in r.findings if f.risk > 0] == ["SPLIT_NEAR_LIMIT"]
