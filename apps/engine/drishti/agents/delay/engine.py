"""Registers the Delay Prediction engine with the engine registry."""

from __future__ import annotations

from drishti.agents.delay import agent
from drishti.agents.registry import EngineSpec


def _assess(work: dict, ctx):
    return agent.assess(work, ctx.as_of)


# Shown on every open work, but not counted in the risk score: its measured AUC (0.71 on a
# strict time-based backtest, 0.59 in unseen districts) misses the blueprint's 0.80 target,
# and the project ships no weight without a met target (AGENTS.md rule 4).
ENGINE = EngineSpec(id=agent.AGENT, name="Delay Prediction", question=agent.QUESTION,
                    assess=_assess, weight=0.0,
                    weight_note="Shown, not counted: accuracy 0.71 against a 0.80 target.")
