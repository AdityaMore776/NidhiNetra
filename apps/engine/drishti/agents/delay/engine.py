"""Registers the Delay & Fund Flow engine (stored id `delay`; Fund Flow merged in T410)."""

from __future__ import annotations

from drishti.agents.delay import agent
from drishti.agents.registry import EngineSpec


def _assess(work: dict, ctx):
    return agent.assess(work, ctx.as_of, ctx.stats.delay, (ctx.data or {}).get("backlog"))


# Shown on every open work, but not counted in the risk score: its measured AUC (0.70 on a
# strict time-based backtest, 0.68 in unseen districts; results/delay_rates.json) misses the
# blueprint's 0.80 target, and the project ships no weight without a met target (AGENTS.md
# rule 4).
ENGINE = EngineSpec(id=agent.AGENT, name="Delay & Fund Flow", question=agent.QUESTION,
                    assess=_assess, weight=0.0,
                    weight_note="Shown, not counted: accuracy 0.70 against a 0.80 target.")
