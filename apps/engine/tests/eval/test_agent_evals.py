"""The T168 eval cases gate every pull request (data/eval/, plan docs/plans/T168-agent-evals.md).

Every labelled case of Duplicate Work, Time & Rules and Site Progress, in both worlds, gets a level
its label allows; every case through all four agents gets a band its label allows (a fraud in the
review queue, an honest filing kept out). Cases scoped "other" (another agent's job) or "limit" (a
known edge of a measured rule) are listed by report.py and not gated here. The Cost agent's cases
are gated by tests/agents/cost_estimate/test_cost_t167.py."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

COMMON = Path(__file__).resolve().parents[4] / "data" / "eval" / "common"
sys.path.insert(0, str(COMMON))
import world as W  # noqa: E402,I001  (first: it sets the paths)
import grade as G  # noqa: E402
import report as R  # noqa: E402

AGENTS = ("dup_split", "time_rules", "site_progress", "pipeline")
ALL = [(agent, set_name, c, world)
       for agent in AGENTS
       for set_name, cases in R.case_sets(agent).items()
       for c in cases if c.scope == "self"
       for world in W.WORLDS]


@pytest.mark.parametrize("agent,set_name,case,world", ALL,
                         ids=[f"{a}:{s}:{c.id}@{w}" for a, s, c, w in ALL])
def test_every_eval_case_passes(agent, set_name, case, world):
    row = R.judge(case, W.world(world))
    assert row["verdict"] == "pass", (f"{case.truth} case got {row['got']} (allowed "
                                      f"{'/'.join(case.allowed)}): {row['codes']} "
                                      f"{row['headline']}")


def test_labels_keep_the_one_rule():
    """A fraud never allows a clean level; an honest case never allows a question; broken data
    never allows a clean chit."""
    for agent, _s, c, _w in ALL:
        if agent == "pipeline":
            continue
        if c.truth in G.FRAUDS:
            assert not {"fits", "edge"} & set(c.allowed), c.id
        elif c.truth in ("honest", "edge"):
            assert "ask" not in c.allowed, c.id
        else:
            assert "fits" not in c.allowed, c.id


def test_every_agent_has_a_held_out_set():
    for agent in AGENTS:
        assert set(R.case_sets(agent)) >= {"main", "holdout"}, agent
