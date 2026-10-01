"""Registers the Fund Flow engine (stored id `delay`; the delay prediction was removed in T053)."""

from __future__ import annotations

from drishti.agents.delay import agent
from drishti.agents.registry import EngineSpec


def _assess(work: dict, ctx):
    return agent.assess(work, ctx.as_of, (ctx.data or {}).get("backlog"))


# Shown, not counted: every work it flags is already waiting past the sanction clock, which
# Guideline Compliance R01 counts; counting it here too would count one wait twice.
ENGINE = EngineSpec(id=agent.AGENT, name="Fund Flow", question=agent.QUESTION,
                    assess=_assess, weight=0.0,
                    weight_note="Shown, not counted: the wait itself is Guideline Compliance's "
                                "R01.")
