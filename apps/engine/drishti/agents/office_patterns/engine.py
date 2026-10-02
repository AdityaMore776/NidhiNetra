"""Registers the Office Patterns engine with the engine registry.

The office index (index.OfficeIndex) is given in the context as ctx.data["offices"]: the batch
builds it from every work, the API from the work's district with national rates from the whole
database (batch.with_index).
"""

from __future__ import annotations

from drishti.agents.office_patterns import agent
from drishti.agents.registry import EngineSpec


def _assess(work: dict, ctx):
    return agent.assess(work, (ctx.data or {}).get("offices"))


ENGINE = EngineSpec(id=agent.AGENT, name="Office Patterns", question=agent.QUESTION,
                    assess=_assess, weight=0.10, order=5,
                    weight_note="An office habit adds a little; the work's own engines decide.")
