"""Registers the Paperwork engine (Document + Contractor Network, T110) with the registry.

The work's evidence facts arrive with the work (work["evidence"], table evidence_facts); the
vendor index of its district in ctx.data["vendors"] (batch: every work; API: its district).
"""

from __future__ import annotations

from drishti.agents.paperwork import agent
from drishti.agents.registry import EngineSpec


def _assess(work: dict, ctx):
    return agent.assess(work, (ctx.data or {}).get("vendors"))


# Shown, not counted: papers exist for the 837-work pilot only (one district + 400 random), so
# a weight would rank pilot works above every other work for having papers at all.
ENGINE = EngineSpec(id=agent.AGENT, name="Paperwork", question=agent.QUESTION,
                    assess=_assess, weight=0.0, order=6,
                    weight_note="Shown, not counted: papers read for the 837 pilot works only.")
