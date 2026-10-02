"""Registers the Guideline Compliance engine with the engine registry."""

from __future__ import annotations

from drishti.agents.compliance import agent
from drishti.agents.registry import EngineSpec
from drishti.agents.statistical.scope import read


def type_top(work: dict, stats) -> float | None:
    """The top (p90) of what works of this type cost nationally, like for like (R12)."""
    t = work.get("work_type_code")
    if not t:
        return None
    chain = stats.chain(stats.peer_type(t, read(t, work.get("description")).scope), None, None)
    return chain[-1].range_inr()[1] if chain else None


def _assess(work: dict, ctx):
    return agent.assess(work, ctx.as_of, ctx.stats.timeline, type_top(work, ctx.stats),
                        (ctx.data or {}).get("offices"))


ENGINE = EngineSpec(id=agent.AGENT, name="Guideline Compliance", question=agent.QUESTION,
                    assess=_assess)
