"""Risk Fusion v2 (T050): the blueprint's weighted risk score, bands and top-3 reasons.

  score = 0.30 compliance + 0.20 cost + 0.20 duplicate/split + 0.20 delay + 0.10 outlier
          each term = the engine's signal (its risk, 0-1) when it ASSESSED the work, else 0.
          Weights come from the engine registry: an engine not built counts 0, and an
          engine below its accuracy target is registered "shown, not counted" (weight 0,
          today: Delay, AUC 0.70 against 0.80).
  floors  1 serious-rule breach (a hard finding, risk >= 0.6) lifts the score to the
          High cut; 2 or more to the Critical cut. The lift is its own part ("floor"), so
          the parts still add up exactly to the score.
  bands   cut-offs tuned on the real score distribution (all 2,09,993 works, re-tuned 1 Oct
          2026 for T051; data/dry_run.py -> results/risk_score_bands.json). The blueprint's
          40/70/85 cannot be used as written: with Delay at weight 0 and Outlier not built, the
          highest real score is 36 of 100. Since T051 the engines' signals grow with the
          evidence (a 76-day wait no longer scores like a 718-day one), so scores spread out
          (1,802 distinct values, was 55 in the whole queue) and the cut-offs sit where the
          evidence changes:
            CRITICAL >= 0.30  a guideline issue plus a strong repeat or split, or three
                              engines (54 works)
            HIGH     >= 0.22  two engines each with a meaningful signal; nothing scores this
                              high on one engine (448)
            MEDIUM   >= 0.15  one strong signal, e.g. waiting for sanction twice the limit
                              (14,140)
            LOW      otherwise
          Review queue = CRITICAL + HIGH: 502 works (0.24%). 30 random queue works read by
          eye: all 30 have a reason that survives reading, 27 a reason other than a delay
          (results/risk_score_eye.json; T050's queue of 1,524 read 24/30 on the first test).
          The blueprint's 5-10% High + Critical has no cut-off in the data.
  limited a LOW score where a counted engine could not assess the work is not a clean chit.
  reasons the top three contributions, each with the engine's own sentence in English and a
          Hindi sentence (the rule's own Hindi message for compliance, else reasons.py).

Data Validation issues are shown on the work page but no longer counted: Guideline
Compliance reports the same facts (R06 impossible dates, R11 missing data).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

from drishti.agents import registry
from drishti.agents.contract import AgentResult, Status
from drishti.fusion.reasons import hindi
from drishti.validation.checks import Issue

CRITICAL, HIGH, MEDIUM = 0.30, 0.22, 0.15
HARD_RISK = 0.60
MAX_REASONS = 3

LABELS = {**{e.id: e.name for e in registry.engines()}, "floor": "Serious rule breach"}


def weights() -> dict[str, float]:
    return {e.id: float(e.weight or 0.0) for e in registry.engines()}


@dataclass
class Part:
    source: str
    label: str
    weight: float          # the engine's blueprint weight
    contribution: float    # weight x signal: its share of the score


@dataclass
class Fused:
    score: float
    band: str
    limited: bool
    parts: list[Part]
    hard_trigger: str | None = None
    reasons: list[dict] = field(default_factory=list)

    def to_json(self) -> dict:
        return asdict(self)


def band_of(score: float) -> str:
    if score >= CRITICAL:
        return "CRITICAL"
    if score >= HIGH:
        return "HIGH"
    if score >= MEDIUM:
        return "MEDIUM"
    return "LOW"


def _reason(r: AgentResult, contribution: float) -> dict:
    top = max(r.findings, key=lambda f: f.risk, default=None)
    text = top.text if top else r.headline
    hi = (top.evidence or {}).get("message_hi") if top else None
    return {"source": r.agent, "label": LABELS.get(r.agent, r.agent),
            "contribution": contribution, "code": top.code if top else r.verdict,
            "text_en": text, "text_hi": hi or hindi(top.code if top else r.verdict)}


def fuse(results: list[AgentResult], issues: list[Issue],
         reliability: dict[str, float] | None = None) -> Fused:
    """`issues` and `reliability` are kept for the call signature: validation is shown,
    not counted, and learned reliability arrives with the learning loop (T070)."""
    w = weights()
    parts: list[Part] = []
    reasons: list[dict] = []
    for r in results:
        wt = w.get(r.agent, 0.0)
        if r.status != Status.ASSESSED or wt <= 0 or r.risk <= 0:
            continue
        c = wt * r.risk
        parts.append(Part(r.agent, LABELS.get(r.agent, r.agent), wt, c))
        reasons.append(_reason(r, c))
    raw = sum(p.contribution for p in parts)

    serious = [r for r in results if r.status == Status.ASSESSED
               for f in r.findings if f.hard and f.risk >= HARD_RISK]
    floor = CRITICAL if len(serious) >= 2 else HIGH if serious else 0.0
    hard_trigger = serious[0].agent if serious else None
    score = raw
    if floor > raw:
        parts.append(Part("floor", LABELS["floor"], 0.0, floor - raw))
        score = floor
    score = min(1.0, score)

    counted = [r for r in results if w.get(r.agent, 0.0) > 0 and r.status != Status.NOT_BUILT]
    limited = any(r.status in (Status.NOT_ASSESSABLE, Status.ERROR) for r in counted)
    parts.sort(key=lambda p: -p.contribution)
    reasons.sort(key=lambda x: -x["contribution"])
    return Fused(score=score, band=band_of(score), limited=limited, parts=parts,
                 hard_trigger=hard_trigger, reasons=reasons[:MAX_REASONS])
