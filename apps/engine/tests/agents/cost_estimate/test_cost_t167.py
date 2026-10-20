"""T167: the Cost agent's levels, its leeway and the eval gate (plan docs/plans/T167-cost-eval.md).

The owner (19 Oct 2026): a fraud is never an edge case; at the least it is "check this". Every
case of the eval (data/eval/cost/: the cases the rules were built on, and two held-out sets) runs
here in both worlds; a fraud left at fits or edge, or an honest case asked when its label does not
allow it, fails the build. The rest pin each T167 rule on one filing."""

from __future__ import annotations

import sys
from functools import cache
from pathlib import Path

import pytest

from drishti.agents.cost_estimate import agent
from drishti.cost_form import norms

EVAL = Path(__file__).resolve().parents[5] / "data" / "eval" / "cost"
sys.path.insert(0, str(EVAL))
import cases as C  # noqa: E402
import holdout  # noqa: E402
import holdout2  # noqa: E402
import levels as L  # noqa: E402


@cache
def world(name: str) -> C.World:
    spread, seed = C.WORLDS[name]
    return C.build_world(name, spread, seed)


ALL = [(c, n) for c in C.cases() + holdout.holdout() + holdout2.holdout2() if c.scope == "cost"
       for n in C.WORLDS]


@pytest.mark.parametrize("case,name", ALL, ids=[f"{c.id}@{n}" for c, n in ALL])
def test_the_eval_case_gets_a_level_its_label_allows(case, name):
    r = case.run(world(name))
    got = L.level(r)
    assert got in case.allowed, (f"{case.truth} case got {got}: {r.headline[:300]}")


def test_a_fraud_never_allows_fits_or_edge_and_an_honest_case_never_asks_unless_labelled():
    for c, _n in ALL:
        if c.truth == "fraud":
            assert not {"fits", "edge"} & set(c.allowed), c.id
        elif "ask" in c.allowed:
            assert c.id == "edge_typo_extra_zero", c.id     # the one honest case asked: a typo


def run(p: dict, name: str = "tight"):
    return C.assess(world(name), p)


def test_level_and_leeway_are_in_the_evidence():
    r = run(C.finish(C.road(world("tight"), rate_up=1.07)))
    assert r.evidence["level"] == "edge" and not r.findings
    assert r.evidence["leeway"][0]["kind"] == "verified"
    assert "CPWD" in r.evidence["leeway"][0]["why"]
    honest = run(C.road(world("tight")))
    assert honest.evidence["level"] == "fits" and honest.evidence["leeway"] == []


def test_padding_beyond_cpwds_ten_percent_is_check_this_below_fifteen():
    r = run(C.finish(C.road(world("tight"), rate_up=1.12)))
    assert [f.code for f in r.findings] == ["ESTIMATE_ABOVE_FAIR_RANGE"]
    assert r.risk == pytest.approx(agent.CHECK_RISK) and r.evidence["level"] == "check"
    assert "CPWD" in r.findings[0].text


def test_a_claimed_hilly_site_softens_a_question_to_check_this_never_clears_it():
    def filed(up):
        return C.finish(C.road(world("tight"), rate_up=up, terrain="Hilly / steep",
                               site_access="Foot / manual carry required"))
    soft = run(filed(1.18))
    assert soft.evidence["level"] == "check"
    assert any(x["kind"] == "claimed" for x in soft.evidence["leeway"])
    assert run(filed(1.40)).evidence["level"] == "ask"         # beyond the claimed allowance
    assert run(C.finish(C.road(world("tight"), rate_up=1.18))).evidence["level"] == "ask"


def test_a_design_mix_is_held_to_is_456s_cement_ceiling():
    lo, hi = norms.cement_range_per_m3("M25")
    assert lo == pytest.approx(norms.cement_bags_per_m3("M20")) and hi == pytest.approx(9.0)
    size = {"length_m": 100, "width_m": 3, "cc_thickness_mm": 150, "concrete_grade": "M25",
            "base_type": "wbm"}
    need = norms.needs("ROAD_CC", size)[0]
    assert need["needed"] == pytest.approx(45 * 9 * norms.WASTAGE)
    assert norms.cement_range_per_m3("other") is None


def test_one_dear_line_is_checked_but_a_uniform_rise_within_ten_percent_is_not():
    w = world("tight")
    dear = run(C.finish(C.scale(C.road(w), 1.30, only=("Cement",))))
    assert "RATE_ABOVE_ALL_OTHERS" in [f.code for f in dear.findings] or \
        dear.evidence["level"] in ("check", "ask")
    rise = run(C.finish(C.road(w, rate_up=1.09)))
    assert rise.evidence["level"] == "edge"


def test_ghost_workers_are_checked_against_other_agencies_crews():
    p = C.road(world("tight"))
    for k in [k for k in p if k.startswith("lab_trade_") and p[k] == "beldar"]:
        n = k.removeprefix("lab_trade_")
        p[f"lab_workers_{n}"] = f"{float(p[f'lab_workers_{n}']) * 3:g}"
    r = run(C.finish(p))
    assert "LABOUR_DAYS_ABOVE_PEERS" in [f.code for f in r.findings]


def test_check_codes_are_in_the_reliability_table_at_the_check_risk():
    import json

    from drishti import reference
    table = json.loads((Path(reference.__file__).parent / "reliability.json")
                       .read_text(encoding="utf-8"))["codes"]
    for code in ("ESTIMATE_ABOVE_FAIR_RANGE", "PRICE_ABOVE_STANDARD", "RATE_ABOVE_ALL_OTHERS",
                 "MATERIAL_QUANTITY_ABOVE_NEED", "MATERIAL_QUANTITY_ABOVE_PEERS",
                 "LABOUR_RATE_ABOVE", "LABOUR_DAYS_ABOVE_PEERS", "DISTRICT_RATES_ABOVE_STATE"):
        row = table[f"cost_estimate:{code}"]
        assert row["ref_risk"] == pytest.approx(agent.CHECK_RISK), code
