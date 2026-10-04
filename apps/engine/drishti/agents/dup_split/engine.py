"""Registers the Duplicate Work engine (stored id `dup_split`) with the engine registry.

The comparison index (repeat.RepeatIndex) is given in the context as ctx.data["dup_split"]: the
batch builds it once from every work, the API from the work's district. Without it the engine
says it could not compare, never "nothing found".
"""

from __future__ import annotations

from drishti.agents.dup_split import agent
from drishti.agents.registry import EngineSpec


def _assess(work: dict, ctx):
    return agent.assess(work, (ctx.data or {}).get("dup_split"))


ENGINE = EngineSpec(id=agent.AGENT, name="Duplicate Work", question=agent.QUESTION,
                    assess=_assess)
