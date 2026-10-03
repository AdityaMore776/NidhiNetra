"""Registers the Cost Estimate engine (Cost v3, T097) as the Cost check of the core slot (T099).

A work reaches it with the implementing agency's form attached (work["cost_form"], saved through
POST /api/v1/cost-forms); every other work is NOT_APPLICABLE. The slot keeps the blueprint weight;
its findings count at the 1-in-4 prior of fusion v3 until officers' verdicts are read (T098), so
none can queue a work on its own (project rule 4).
"""

from __future__ import annotations

from drishti.agents.cost_estimate import agent
from drishti.agents.registry import EngineSpec

ENGINE = EngineSpec(id=agent.AGENT, name="Cost", question=agent.QUESTION, assess=agent.assess)
