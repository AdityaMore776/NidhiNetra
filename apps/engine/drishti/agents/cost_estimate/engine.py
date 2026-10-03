"""Registers the Cost Estimate engine (Cost v3, T097) with the engine registry.

Shown, not counted, until T098 proves it on read flags (project rule 4). A work reaches it only
with the implementing agency's form attached (work["cost_form"]); every other work gets
NOT_APPLICABLE and keeps the Cost Anomaly check.
"""

from __future__ import annotations

from drishti.agents.cost_estimate import agent
from drishti.agents.registry import EngineSpec

ENGINE = EngineSpec(id=agent.AGENT, name="Cost Estimate", question=agent.QUESTION,
                    assess=agent.assess, weight=0.0, order=9,
                    weight_note="Shown, not counted, until measured on real estimates (T098).")
