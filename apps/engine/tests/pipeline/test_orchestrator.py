from datetime import date

import pytest

from drishti.agents.contract import Status
from drishti.agents.statistical.cohort import StatsStore
from drishti.pipeline import orchestrator
from drishti.pipeline.orchestrator import AGENT_ORDER, Context, assess_work


@pytest.fixture()
def ctx():
    stats = StatsStore.from_rows(
        cohorts=[{"level": "type", "work_type_code": "ROAD_CC", "key": "", "n": 1000,
                  "p10": 4.9, "p50": 5.2, "p90": 5.5, "sd": 0.2}],
        durations=[], unit_models=[])
    return Context(stats=stats, as_of=date(2026, 5, 26))


def _work(**kw):
    w = {"work_id": "W1", "work_type_code": "ROAD_CC", "district_lgd": "1", "state_lgd": "2",
         "district_name": "X", "amount": 158_000.0, "description": "CC road in village Y",
         "status": "SANCTIONED", "recommended_date": date(2026, 1, 1), "completed_date": None,
         "quantity": None, "quantity_unit": None, "is_outside_constituency": False}
    w.update(kw)
    return w


def test_four_agents_in_deck_order(ctx):
    a = assess_work(_work(), ctx)
    assert [r.agent for r in a.agents] == list(AGENT_ORDER)
    assert AGENT_ORDER == ("site_progress", "image_reuse", "duplicate_project", "statistical")
    status = {r.agent: r.status for r in a.agents}
    assert status["statistical"] == Status.ASSESSED
    assert status["site_progress"] == Status.NOT_BUILT


def test_clean_work_is_low_with_limited_evidence(ctx):
    a = assess_work(_work(), ctx)
    assert a.fused.band == "LOW" and a.fused.limited


def test_an_agent_that_crashes_becomes_an_error_not_a_crash(ctx, monkeypatch):
    def boom(*_a, **_k):
        raise RuntimeError("disk on fire")

    monkeypatch.setattr(orchestrator.statistical, "assess", boom)
    a = assess_work(_work(), ctx)
    r = next(r for r in a.agents if r.agent == "statistical")
    assert r.status == Status.ERROR
    assert "RuntimeError" in r.limitations[0]
    assert a.fused.score == 0.0


def test_priority_grows_with_money(ctx):
    small = assess_work(_work(amount=1_000_000.0, description="CC road"), ctx)
    big = assess_work(_work(amount=10_000_000.0, description="CC road"), ctx)
    assert small.fused.score > 0 and big.fused.score > 0
    assert big.priority / big.fused.score > small.priority / small.fused.score


def test_row_is_json_ready(ctx):
    import json

    row = assess_work(_work(), ctx).to_row()
    json.dumps(row["agents"]), json.dumps(row["parts"]), json.dumps(row["validation"])
    assert row["band"] in ("HIGH", "MEDIUM", "LOW")
