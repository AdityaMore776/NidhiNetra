"""Registers the Duplicate & Split-Work engine with the engine registry."""

from __future__ import annotations

from drishti.agents.dup_split import agent
from drishti.agents.registry import EngineSpec


def _assess(work: dict, ctx):
    return agent.assess(work, "dup_split" in ctx.stats.signals_built)


ENGINE = EngineSpec(id=agent.AGENT, name="Duplicate & Split Work", question=agent.QUESTION,
                    assess=_assess)
