"""Risk fusion v3: the score is the chance a work is worth a look, from by-eye reads."""

import json
import math
import re
from pathlib import Path

import pytest

from drishti import reference
from drishti.agents.contract import AgentResult, Finding, Status, not_built
from drishti.fusion import calibrated
from drishti.fusion.calibrated import CRITICAL, HIGH, MEDIUM, Reliability, band_of
from drishti.fusion.fuse import fuse, weights


@pytest.fixture(autouse=True)
def _v3(monkeypatch):
    monkeypatch.setenv("DRISHTI_FUSION", "v3")


def _r(agent, *findings, status=Status.ASSESSED):
    fs = [Finding(code, f"{agent} {code} sentence", hard=hard, risk=risk)
          for code, risk, hard in findings]
    return AgentResult(agent=agent, status=status, verdict=fs[0].code if fs else "X",
                       risk=max((f.risk for f in fs), default=0.0), confidence=0.9,
                       hard=any(f.hard for f in fs), headline=f"{agent} headline", version="t",
                       findings=fs)


def _all(*results):
    names = {r.agent for r in results}
    return list(results) + [not_built(a, "q") for a in weights() if a not in names]


def test_every_code_in_the_table_is_one_an_engine_can_report():
    table = json.loads((Path(reference.__file__).parent / "reliability.json").read_text("utf-8"))
    rules = json.loads((Path(reference.__file__).parent / "rules.json").read_text("utf-8"))
    agents = Path(calibrated.__file__).resolve().parents[1] / "agents"
    emitted = {r["code"] for r in rules["rules"]}
    for src in agents.rglob("*.py"):
        emitted |= set(re.findall(r'"([A-Z][A-Z_]{5,})"', src.read_text("utf-8")))
    engines = set(weights())
    for key in table["codes"]:
        engine, code = key.split(":")
        assert engine in engines, key
        assert code in emitted, key


def _rate(code):
    return Reliability.load().rate(code).hit_rate


def test_hit_rates_shrink_toward_one_in_four_until_read():
    rel = Reliability.load()
    r12 = rel.rate("compliance:NO_STATED_SCOPE")
    assert r12.basis == "measured" and r12.read >= 30
    assert r12.hit_rate == pytest.approx((r12.worth + 1) / (r12.read + 4))
    assert rel.rate("compliance:SANCTION_OVERDUE").basis == "design"
    unknown = rel.rate("compliance:SOMETHING_NEVER_READ")
    assert unknown.basis == "prior" and unknown.hit_rate == pytest.approx(0.25)


def test_one_well_measured_finding_is_high_but_never_critical_alone():
    f = fuse(_all(_r("compliance", ("NO_STATED_SCOPE", 0.6, False))))
    assert f.band == "HIGH" and f.score == pytest.approx(_rate("compliance:NO_STATED_SCOPE"))
    r = Reliability.load().rate("compliance:NO_STATED_SCOPE")
    assert f.reasons[0]["basis"] == "measured" and f.reasons[0]["read"] == [r.worth, r.read]


def test_two_engines_agreeing_strongly_is_critical():
    f = fuse(_all(_r("compliance", ("NO_STATED_SCOPE", 0.6, False)),
                  _r("statistical", ("COST_ABOVE_PEERS", 0.9, False))))
    p1, p2 = _rate("compliance:NO_STATED_SCOPE"), _rate("statistical:COST_ABOVE_PEERS")
    assert f.score == pytest.approx(1 - (1 - p1) * (1 - p2))
    assert f.band == "CRITICAL"


def test_a_wait_alone_never_reaches_high():
    f = fuse(_all(_r("compliance", ("SANCTION_OVERDUE", 0.6, False))))
    assert f.score == pytest.approx(0.40) and f.band == "MEDIUM"


def test_completed_before_recommended_queues_only_where_it_stands_out():
    """R06 was read by eye on the hosted data (T056): the cases that stand out reach the queue
    alone; a bulk-entry or office-habit records note (risk 0.10) stays LOW."""
    rate = Reliability.load().rate("compliance:IMPOSSIBLE_TIMELINE")
    assert rate.basis == "measured" and rate.read >= 10
    stands_out = fuse(_all(_r("compliance", ("IMPOSSIBLE_TIMELINE", 0.6, False))))
    assert stands_out.band == "HIGH" and stands_out.score == pytest.approx(rate.hit_rate)
    note = fuse(_all(_r("compliance", ("IMPOSSIBLE_TIMELINE", 0.10, False))))
    assert note.band == "LOW" and note.score == pytest.approx(rate.hit_rate * 0.10 / 0.6)
    assert note.score < 0.15                       # about the 0.125 it counted at the prior


def test_a_finding_never_read_cannot_queue_a_work_on_its_own():
    f = fuse(_all(_r("dup_split", ("REPAIR_SOON_AFTER_BUILT", 0.7, False))))
    assert f.score == pytest.approx(0.25) and f.band == "MEDIUM"


def test_weaker_flags_of_a_graded_kind_count_in_proportion():
    weak = fuse(_all(_r("statistical", ("COST_ABOVE_PEERS", 0.35, False))))
    strong = fuse(_all(_r("statistical", ("COST_ABOVE_PEERS", 0.9, False))))
    assert weak.score == pytest.approx(_rate("statistical:COST_ABOVE_PEERS") * 0.35 / 0.9)
    assert weak.score < strong.score and weak.band == "LOW"


def test_one_kind_counts_once_within_an_engine():
    one = fuse(_all(_r("dup_split", ("REPEATED_WHILE_OPEN", 0.7, False))))
    two = fuse(_all(_r("dup_split", ("REPEATED_WHILE_OPEN", 0.7, False),
                       ("REPEATED_WHILE_OPEN", 0.5, False))))
    assert one.score == pytest.approx(two.score)


def test_engines_shown_but_not_counted_add_nothing():
    f = fuse(_all(_r("delay", ("TERM_ENDED_UNSANCTIONED", 0.4, False)),
                  _r("paperwork", ("SANCTION_LATE", 0.6, False))))
    assert f.score == 0.0 and f.parts == [] and f.band == "LOW"


def test_parts_add_up_exactly_and_do_not_depend_on_order():
    rs = [_r("compliance", ("POSSIBLY_INADMISSIBLE", 0.6, False)),
          _r("dup_split", ("SPLIT_AT_ONE_SITE", 0.6, False)),
          _r("office_patterns", ("PRICED_AT_LIMIT", 0.3, False))]
    a, b = fuse(_all(*rs)), fuse(_all(*reversed(rs)))
    assert sum(p.contribution for p in a.parts) == pytest.approx(a.score, abs=1e-12)
    assert {p.source: p.contribution for p in a.parts} == pytest.approx(
        {p.source: p.contribution for p in b.parts})
    # each part is the engine's share of -ln(1 - p)
    logs = {p.source: p.contribution for p in a.parts}
    assert logs["compliance"] > logs["dup_split"] > logs["office_patterns"]


def test_an_office_habit_corroborates_but_never_queues_alone():
    alone = fuse(_all(_r("office_patterns", ("PRICED_AT_LIMIT", 0.3, False))))
    assert alone.band == "LOW"
    # a two-piece split just under the limit (risk 0.60): MEDIUM alone, HIGH with the habit
    split = fuse(_all(_r("dup_split", ("SPLIT_AT_ONE_SITE", 0.60, False))))
    both = fuse(_all(_r("dup_split", ("SPLIT_AT_ONE_SITE", 0.60, False)),
                     _r("office_patterns", ("PRICED_AT_LIMIT", 0.3, False))))
    assert split.band == "MEDIUM" and both.band == "HIGH"


def test_a_serious_breach_lifts_to_high_two_to_critical():
    one = fuse(_all(_r("compliance", ("OUTSIDE_AREA_CEILING", 1.0, True))))
    assert one.band == "HIGH" and one.score == pytest.approx(HIGH) and one.hard_trigger
    assert any(p.source == "floor" for p in one.parts)
    assert sum(p.contribution for p in one.parts) == pytest.approx(one.score, abs=1e-12)
    # two breaches of kinds never read count 1 in 4 each (0.44): the floor lifts to CRITICAL
    two = fuse(_all(_r("compliance", ("OUTSIDE_AREA_CEILING", 1.0, True),
                       ("SOME_OTHER_BREACH", 1.0, True))))
    assert two.band == "CRITICAL" and two.score == pytest.approx(CRITICAL)
    # when the evidence already passes the floor, nothing is added
    strong = fuse(_all(_r("compliance", ("OUTSIDE_AREA_CEILING", 1.0, True),
                          ("POSSIBLY_INADMISSIBLE", 1.0, True))))
    assert strong.band == "CRITICAL" and strong.score > CRITICAL
    assert not any(p.source == "floor" for p in strong.parts)


def test_officer_verdicts_move_the_score_without_retuning_a_cut_off():
    rel = Reliability.load().with_verdicts({"dup_split:REPAIR_SOON_AFTER_BUILT": (20, 22)})
    before = fuse(_all(_r("dup_split", ("REPAIR_SOON_AFTER_BUILT", 0.7, False))))
    after = fuse(_all(_r("dup_split", ("REPAIR_SOON_AFTER_BUILT", 0.7, False))),
                 reliability=rel)
    assert before.band == "MEDIUM" and after.band == "HIGH"
    assert after.score == pytest.approx((20 + 1) / (22 + 4))


def test_limited_and_bands():
    f = fuse(_all(_r("compliance"), _r("statistical", status=Status.NOT_ASSESSABLE),
                  _r("dup_split")))
    assert f.limited is True and f.band == "LOW"
    assert band_of(CRITICAL, engines_over=1) == "HIGH"
    assert band_of(CRITICAL, engines_over=2) == "CRITICAL"
    assert band_of(HIGH) == "HIGH" and band_of(MEDIUM) == "MEDIUM"
    assert band_of(math.nextafter(MEDIUM, 0)) == "LOW"
