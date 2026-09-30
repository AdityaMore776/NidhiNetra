"""Registers the Guideline Compliance engine with the engine registry."""

from __future__ import annotations

from drishti.agents.compliance import agent
from drishti.agents.registry import EngineSpec


def _assess(work: dict, ctx):
    return agent.assess(work, ctx.as_of, ctx.stats.p98(work.get("work_type_code")),
                        ctx.stats.timeline)


ENGINE = EngineSpec(id=agent.AGENT, name="Guideline Compliance", question=agent.QUESTION,
                    assess=_assess)
