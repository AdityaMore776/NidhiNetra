"""Properties every agent must keep, on generated inputs (T168, Hypothesis).

The labelled evals (data/eval/) test chosen cases; these test rules that must hold for EVERY input
Hypothesis can think of, and shrink a failure to its smallest example:

  invariance    what the agent must not care about: the agency's name, GPS jitter of a few metres,
                every date moved by the same days, the order the site videos arrive in
  monotonicity  more of a bad thing never lowers the answer: more padding, a faster "finish"
  room          one more good video never adds a finding; one poor video never makes a question
  contract      junk in any field never crashes an agent or reads as a clean chit
"""

from __future__ import annotations

import copy
import random
from datetime import date, timedelta

from hypothesis import HealthCheck, assume, given, settings
from hypothesis import strategies as st

from drishti.agents.contract import AgentResult, Status
from drishti.agents.dup_split.agent import assess as dup
from drishti.agents.dup_split.repeat import RepeatIndex
from drishti.agents.site_progress.agent import assess as site
from drishti.agents.time_rules.agent import assess as timing
from drishti.pipeline.orchestrator import _run
from tests.agents.dup_split.test_dup_split import DEG, HALL, LAT, _filler, _form, _w
from tests.agents.site_progress.test_site_progress_v3 import AS_OF as SITE_AS_OF
from tests.agents.site_progress.test_site_progress_v3 import base, visit, work
from tests.agents.time_rules.test_time_rules import AS_OF, _visit, _work
from tests.agents.time_rules.test_time_rules import _form as _tform

FAST = settings(max_examples=40, deadline=None, suppress_health_check=[HealthCheck.too_slow])
ORDER = {"na": -1, "fits": 0, "edge": 1, "check": 2, "ask": 3}


def level(r: AgentResult) -> str:
    if r.status != Status.ASSESSED:
        return "na"
    top = max((f.risk for f in r.findings), default=0.0)
    return "ask" if top >= 0.4 else "check" if top >= 0.1 else "edge" if r.findings else "fits"


def counted(r: AgentResult) -> set[str]:
    return {f.code for f in r.findings if f.risk >= 0.1}


# ---- Duplicate Work ------------------------------------------------------------------------

def _pair(gap_m: float, jitter: tuple[float, float], agency: str = "Agency A",
          shift: int = 0):
    old = _w("OLD", HALL, rec=date(2023, 1, 10) + timedelta(days=shift),
             done=date(2024, 1, 10) + timedelta(days=shift), status="COMPLETED",
             form=_form(lat=LAT))
    new = _w("NEW", HALL, rec=date(2025, 3, 1) + timedelta(days=shift),
             form=_form(lat=LAT + (gap_m + jitter[0]) * DEG, lon=82.69 + jitter[1] * DEG))
    new["agency_name"] = agency
    return dup(new, RepeatIndex.build(_filler() + [old, new]))


@FAST
@given(gap=st.sampled_from([10.0, 25.0, 300.0, 600.0]),
       jitter=st.tuples(st.floats(-4, 4), st.floats(-4, 4)),
       agency=st.text(min_size=1, max_size=40))
def test_dup_ignores_the_agency_name_and_gps_jitter(gap, jitter, agency):
    plain = _pair(gap, (0.0, 0.0))
    moved = _pair(gap, jitter, agency)
    assert counted(moved) == counted(plain), (gap, jitter, moved.headline)


@FAST
@given(gap=st.sampled_from([10.0, 300.0]), shift=st.integers(-400, 400))
def test_dup_ignores_every_date_moved_by_the_same_days(gap, shift):
    assert counted(_pair(gap, (0, 0), shift=shift)) == counted(_pair(gap, (0, 0)))


# ---- Time & Rules --------------------------------------------------------------------------

def _finish(days_after: int, shift: int = 0, videos=()):
    # shifted in whole months, the sanction on the 1st: the form declares its start as a MONTH,
    # so a shift of days could move the start a day against the sanction (28 Feb -> "March"
    # counts from 1 March) and the two works would no longer be the same work moved in time
    m = 3 + shift
    san = date(2026 + (m - 1) // 12, (m - 1) % 12 + 1, 1)
    start = f"{san:%Y-%m}"
    w = _work(status="COMPLETED", recommended_date=san - timedelta(days=40), sanction_date=san,
              completed_date=san + timedelta(days=days_after),
              cost_form=_tform(months=4, start=start),
              site_visits=[_visit(san + timedelta(days=d + 0)) for d in videos])
    return timing(w, AS_OF + (san - date(2026, 3, 1)))


@FAST
@given(days=st.integers(1, 200), shift=st.integers(-24, 24))      # whole months, see _finish
def test_time_rules_ignore_every_date_moved_by_the_same_days(days, shift):
    assert counted(_finish(days, shift)) == counted(_finish(days)), days


@FAST
@given(a=st.integers(1, 200), b=st.integers(1, 200))
def test_a_faster_finish_never_lowers_time_rules(a, b):
    fast, slow = sorted((a, b))
    assert ORDER[level(_finish(fast))] >= ORDER[level(_finish(slow))], (fast, slow)


@FAST
@given(days=st.integers(10, 60), video_day=st.integers(1, 9))
def test_a_genuine_video_of_the_work_going_on_never_adds_a_time_finding(days, video_day):
    assume(video_day < days)
    assert counted(_finish(days, videos=(video_day,))) <= counted(_finish(days))


# ---- Site Progress -------------------------------------------------------------------------

def _honest(n: int) -> list[dict]:
    first = date(2026, 1, 5)
    out = [base()]
    out[0]["captured_at"] = first.isoformat()
    for i in range(n):
        out.append(visit(first + timedelta(days=30 * (i + 1)), claim=f"stage {i + 1} done"))
    return out


@FAST
@given(n=st.integers(2, 7), seed=st.integers(0, 10_000))
def test_site_progress_ignores_the_order_the_videos_arrive_in(n, seed):
    vs = _honest(n)
    shuffled = copy.deepcopy(vs)
    random.Random(seed).shuffle(shuffled)
    a, b = site(work(*vs), SITE_AS_OF), site(work(*shuffled), SITE_AS_OF)
    assert counted(a) == counted(b) and level(a) == level(b)


@FAST
@given(n=st.integers(2, 7))
def test_one_more_good_video_never_adds_a_site_finding(n):
    vs = _honest(n)
    more = vs + [visit(date(2026, 1, 5) + timedelta(days=30 * (n + 1)), claim="next stage done")]
    assert counted(site(work(*more), SITE_AS_OF)) <= counted(site(work(*vs), SITE_AS_OF))


@FAST
@given(n=st.integers(3, 7), which=st.integers(1, 7))
def test_one_poor_video_among_honest_ones_is_never_a_question(n, which):
    vs = _honest(n)
    i = min(which, n)
    vs[i]["readings"] = {**vs[i]["readings"], "quality_ok": False, "change": None,
                         "claim_verdict": None}
    assert level(site(work(*vs), SITE_AS_OF)) in ("fits", "edge"), i


# ---- the contract: junk never crashes and never reads as a clean chit ----------------------

JUNK = st.one_of(st.none(), st.booleans(), st.integers(-10**9, 10**9),
                 st.floats(allow_nan=True, allow_infinity=True), st.text(max_size=30),
                 st.lists(st.integers(), max_size=3), st.dictionaries(st.text(max_size=5),
                                                                      st.integers(), max_size=3))
FIELDS = ("description", "amount", "recommended_date", "sanction_date", "completed_date",
          "status", "work_type_code", "district_lgd", "cost_form", "site_visits", "agency_name")


@settings(max_examples=150, deadline=None)
@given(field=st.sampled_from(FIELDS), value=JUNK)
def test_junk_in_any_field_never_crashes_an_agent(field, value):
    w = _work(cost_form=_tform(), site_visits=[_visit(date(2026, 3, 1))])
    w[field] = value
    idx = RepeatIndex.build(_filler() + [w])
    for name, fn, args in (("dup_split", dup, (w, idx)), ("time_rules", timing, (w, AS_OF)),
                           ("site_progress", site, (w, AS_OF))):
        r = _run(name, fn, *args)
        assert r.status != Status.ERROR, (name, field, value, r.limitations)
        if r.status != Status.ASSESSED:
            assert r.risk == 0, (name, field, value)


# ---- Cost (T167's eval world) --------------------------------------------------------------

@settings(max_examples=25, deadline=None)
@given(a=st.floats(1.0, 2.5), b=st.floats(1.0, 2.5), name=st.sampled_from(["tight", "wide"]))
def test_more_padding_never_lowers_the_cost_level(a, b, name):
    from tests.agents.cost_estimate.test_cost_t167 import C, run, world
    low, high = sorted((a, b))
    lv = [run(C.finish(C.road(world(name), rate_up=x)), name).evidence["level"]
          for x in (low, high)]
    assert ORDER[lv[1]] >= ORDER[lv[0]], (low, high, lv)
