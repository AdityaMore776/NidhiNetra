"""Registers Site Progress v3 (T124) in its core slot: it judges the read site visits attached to
the work (work["site_visits"], batch.with_visits). A work with no visit is NOT_APPLICABLE; its
findings count at the 1-in-4 prior of fusion v3 until the field trial (T126) measures them, so
none can queue a work on its own.
"""

from __future__ import annotations

from drishti.agents.registry import EngineSpec
from drishti.agents.site_progress import agent


def _assess(work: dict, ctx):
    return agent.assess(work, ctx.as_of)


ENGINE = EngineSpec(id=agent.AGENT, name=agent.NAME, question=agent.QUESTION, assess=_assess)
