"""Registers Time & Rules (T122) in its core slot.

It reads the bulk-entry quarters (ctx.stats.timeline, rule R06) and the office index
(ctx.data["offices"]: an office that records completions on the day of sanction routinely is
named once, rule R14).
"""

from __future__ import annotations

from drishti.agents.registry import EngineSpec
from drishti.agents.time_rules import agent


def _assess(work: dict, ctx):
    return agent.assess(work, ctx.as_of, getattr(ctx.stats, "timeline", None),
                        (ctx.data or {}).get("offices"))


ENGINE = EngineSpec(id=agent.AGENT, name="Time & Rules", question=agent.QUESTION, assess=_assess)
