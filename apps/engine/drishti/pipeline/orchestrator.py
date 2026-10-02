"""The pipeline for one work: run every engine, fuse.

    ENGINES (agents/registry.py: compliance, cost, duplicate & split, fund flow, then any
    extra engine folders: paperwork, photo evidence) -> RISK FUSION

T053 removed the separate Data Validation step: it was shown, not counted, and repeated
Guideline Compliance (R06 impossible dates, R11 missing data) with the older prohibited-work
matcher (12% precision against R07's 56%). Stored rows keep an empty `validation` list.

Engines that are not built yet report NOT_BUILT, so every screen shows every
slot from the first milestone and nothing pretends to have been checked.

An agent that raises becomes an ERROR result with the exception's type in its
limitations. It never takes the whole assessment down, and an error never
carries weight in fusion: a failure to look is not a finding.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from drishti import records
from drishti.agents import registry
from drishti.agents.contract import AgentResult, Status, not_built
from drishti.agents.statistical.cohort import StatsStore
from drishti.fusion.fuse import Fused, fuse

AGENT_ORDER = tuple(e.id for e in registry.engines())
QUESTIONS = {e.id: e.question for e in registry.engines()}
PIPELINE_VERSION = "pipeline-0.3.0"


@dataclass
class Context:
    stats: StatsStore
    as_of: date
    reliability: dict[str, float] = field(default_factory=dict)
    # Engine-specific stores (loaded once per process), keyed by engine id.
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class Assessment:
    work_id: str
    validation: list
    agents: list[AgentResult]
    fused: Fused
    priority: float

    def to_row(self) -> dict:
        return {
            "work_id": self.work_id,
            "score": self.fused.score,
            "band": self.fused.band,
            "limited": self.fused.limited,
            "priority": self.priority,
            "parts": {"parts": [p.__dict__ for p in self.fused.parts],
                      "hard_trigger": self.fused.hard_trigger,
                      "reasons": self.fused.reasons},
            "validation": list(self.validation),
            "agents": [r.to_json() for r in self.agents],
            "versions": {"pipeline": PIPELINE_VERSION,
                         **{r.agent: r.version for r in self.agents}},
        }


def priority(score: float, amount) -> float:
    """Score weighted by money at stake: Rs 1 lakh x1, 10 lakh x2, 1 crore x3, 10 crore x4."""
    try:
        money = max(0.0, min(3.0, math.log10(float(amount) / 1e5)))
    except (TypeError, ValueError):
        money = 0.0
    return score * (1.0 + money)


def _run(agent: str, fn, *args) -> AgentResult:
    t0 = time.perf_counter()
    try:
        return fn(*args)
    except Exception as exc:  # an agent failure must never become a finding
        return AgentResult(agent=agent, status=Status.ERROR, verdict="ERROR", risk=0.0,
                           confidence=0.0, hard=False, version="error",
                           headline="This check could not run; it is not a finding.",
                           limitations=[f"{type(exc).__name__} while running the check"],
                           duration_ms=int((time.perf_counter() - t0) * 1000))


def assess_work(work: dict, ctx: Context) -> Assessment:
    work = records.work(work)        # the same column types the indexes were built from
    results = []
    for engine in registry.engines():
        if engine.assess is None:
            results.append(not_built(engine.id, engine.question))
        else:
            results.append(_run(engine.id, engine.assess, work, ctx))
    fused = fuse(results, [], ctx.reliability)
    return Assessment(work_id=work["work_id"], validation=[], agents=results,
                      fused=fused, priority=priority(fused.score, work.get("amount")))
