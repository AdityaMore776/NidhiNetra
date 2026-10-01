"""Registers the Odd Overall engine (#63) in the blueprint's outlier slot.

Its statistics and forest come from engine_models "outlier_stats" (data/build_outlier.py),
loaded into the stats store like the cost engine's price model.
"""

from __future__ import annotations

from drishti.agents.outlier import agent
from drishti.agents.registry import EngineSpec


def _assess(work: dict, ctx):
    return agent.assess(work, ctx.stats.outlier)


# Shown, not counted: 30 random works at the 1.5% cut read 3/30 worth a look
# (data/trial/outlier_labels.py); it reports only the oddest 0.1%.
ENGINE = EngineSpec(id=agent.AGENT, name="Odd Overall", question=agent.QUESTION,
                    assess=_assess, weight=0.0,
                    weight_note="Shown, not counted: its flags mostly have ordinary "
                                "explanations (3/30 random flags worth a look).")
