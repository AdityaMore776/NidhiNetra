"""Step 4 of the deck: Risk Fusion - combine the checks into one score.

Ported from ~/saakshya/core/fusion/case_builder.py and calibration.py:

  weight      = risk x confidence x reliability(agent)
                soft findings are capped at 0.45 - an unusual number can raise a
                work for review, never make it HIGH on its own
  score       = strongest weight + 0.45 x (sum of the others)
                0.45 is the corroboration uplift the old build calibrated: a
                second, independent kind of evidence adds, but does not simply sum
  attribution the parts add up EXACTLY to the score, so an officer can see why a
              work sits where it does and disagree with any single part

Bands (deck: Low / Medium / High):
  HIGH    score >= 0.60, or any single HARD finding with risk >= 0.60 from an
          agent reading it at confidence >= 0.70 (a reused photo, an overlapping
          earlier sanction, a ceiling breach)
  MEDIUM  score >= 0.30
  LOW     otherwise; "limited evidence" when two or more agents could not assess,
          because a low score built on one agent is not a clean chit

RELIABILITY is a placeholder prior of 0.8 per agent until evaluation (M4) and
officer decisions replace it with measured values.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from drishti.agents import registry
from drishti.agents.contract import AgentResult, Status
from drishti.validation.checks import Issue

SOFT_CAP = 0.45
VALIDATION_CAP = 0.30
CORROBORATION = 0.45
HIGH, MEDIUM = 0.60, 0.30
HARD_RISK, HARD_CONFIDENCE = 0.60, 0.70
DEFAULT_RELIABILITY = 0.8
PRIOR_RELIABILITY = {e.id: DEFAULT_RELIABILITY for e in registry.engines()}

LABELS = {**{e.id: e.name for e in registry.engines()}, "validation": "Data Validation"}


@dataclass
class Part:
    source: str
    label: str
    weight: float
    contribution: float


@dataclass
class Fused:
    score: float
    band: str
    limited: bool
    parts: list[Part]
    hard_trigger: str | None = None

    def to_json(self) -> dict:
        return asdict(self)


def _weight(r: AgentResult, reliability: float) -> float:
    if r.status != Status.ASSESSED:
        return 0.0
    w = r.risk * r.confidence * reliability
    return w if r.hard else min(w, SOFT_CAP)


def fuse(results: list[AgentResult], issues: list[Issue],
         reliability: dict[str, float] | None = None) -> Fused:
    rel = {**PRIOR_RELIABILITY, **(reliability or {})}
    weights: dict[str, float] = {}
    for r in results:
        weights[r.agent] = _weight(r, rel.get(r.agent, DEFAULT_RELIABILITY))
    weights["validation"] = min(VALIDATION_CAP, sum(i.risk for i in issues))

    ranked = sorted(weights.items(), key=lambda kv: kv[1], reverse=True)
    parts: list[Part] = []
    for i, (source, w) in enumerate(ranked):
        contribution = w if i == 0 else CORROBORATION * w
        parts.append(Part(source, LABELS.get(source, source), w, contribution))
    total = sum(p.contribution for p in parts)
    if total > 1.0:
        for p in parts:
            p.contribution /= total
        total = 1.0

    hard_trigger = None
    for r in results:
        if r.status != Status.ASSESSED or r.confidence < HARD_CONFIDENCE:
            continue
        if any(f.hard and f.risk >= HARD_RISK for f in r.findings):
            hard_trigger = r.agent
            break

    if total >= HIGH or hard_trigger:
        band = "HIGH"
    elif total >= MEDIUM:
        band = "MEDIUM"
    else:
        band = "LOW"
    limited = sum(1 for r in results if r.status != Status.ASSESSED) >= 2
    return Fused(score=total, band=band, limited=limited,
                 parts=[p for p in parts if p.weight > 0], hard_trigger=hard_trigger)
