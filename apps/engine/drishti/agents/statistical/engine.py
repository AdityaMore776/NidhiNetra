"""Registers the cost engine (stored id `statistical`) with the engine registry."""

from __future__ import annotations

from drishti.agents.registry import EngineSpec
from drishti.agents.statistical import agent


def _assess(work: dict, ctx):
    return agent.assess(work, ctx.stats, ctx.as_of)


ENGINE = EngineSpec(id=agent.AGENT, name="Cost Anomaly", question=agent.QUESTION,
                    assess=_assess)
