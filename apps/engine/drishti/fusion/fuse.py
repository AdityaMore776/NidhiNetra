"""Risk Fusion v2 (T050): the blueprint's weighted risk score, bands and top-3 reasons.

  score = 0.30 compliance + 0.20 cost + 0.20 duplicate/split + 0.20 fund flow
          (the blueprint's 0.10 outlier slot became Guideline Compliance R12 and R13, T053)
          each term = the engine's signal (its risk, 0-1) when it ASSESSED the work, else 0.
          Weights come from the engine registry: an engine not built counts 0, and an
          engine below its accuracy target is registered "shown, not counted" (weight 0,
          today: Fund Flow, whose wait is already R01's; Paperwork and Photo Evidence, pilot
          evidence only).
  floors  1 serious-rule breach (a hard finding, risk >= 0.6) lifts the score to the
          High cut; 2 or more to the Critical cut. The lift is its own part ("floor"), so
          the parts still add up exactly to the score.
  bands   cut-offs tuned on the real score distribution (all 2,09,993 works, re-tuned 1 Oct
          2026 for T051; data/dry_run.py -> results/risk_score_bands.json). The blueprint's
          40/70/85 cannot be used as written: with Fund Flow at weight 0 and no outlier slot, the
          highest real score is 36 of 100. Since T051 the engines' signals grow with the
          evidence (a 76-day wait no longer scores like a 718-day one), so scores spread out
          (1,802 distinct values, was 55 in the whole queue) and the cut-offs sit where the
          evidence changes:
            CRITICAL >= 0.30  a guideline issue plus a strong repeat or split, or three
                              engines (5 works)
            HIGH     >= 0.22  two engines each with a meaningful signal; nothing scores this
                              high on one engine (126)
            MEDIUM   >= 0.15  one strong signal, e.g. a near-certain repeat, or a wait that
                              1 in 25 works that old share (2,197)
            LOW      otherwise
          Review queue = CRITICAL + HIGH: 493 works (0.23%). T053 removed the cost notes
          that were almost never a real price question (several sites 0/48, far bigger
          project 3/18: 502 -> 442) and added Guideline Compliance R12/R13 (-> 493; 15/15 of
          the queue works they lift read as worth checking). Of 30 random queue works read by
          eye for T051 (all 30 with a reason that survives reading, 27 beyond a delay), 22
          are still queued and 19 of those have
          a reason beyond a delay; the 8 that left were big projects carried only by "far
          bigger than usual" plus a sanction wait (results/risk_score_eye.json).
          T054 scored the timing rules by how unusual the wait is (a few days past the limit
          is the norm): queue 493 -> 131, a fresh 30 read 28/30 worth checking (QUEUE_T054).
          The blueprint's 5-10% High + Critical has no cut-off in the data.
  limited a LOW score where a counted engine could not assess the work is not a clean chit.
  reasons the top three contributions, each with the engine's own sentence in English and a
          Hindi sentence (the rule's own Hindi message for compliance, else reasons.py).

The separate Data Validation step was removed (T053): Guideline Compliance reports the same
facts (R06 impossible dates, R11 missing data) with the better prohibited-work reader.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

from drishti.agents import registry
from drishti.agents.contract import AgentResult, Status
from drishti.fusion.reasons import hindi

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


def fuse(results: list[AgentResult], issues: list | tuple = (),
         reliability: dict[str, float] | None = None) -> Fused:
    """`issues` and `reliability` are kept for the call signature: the Data Validation step
    was removed (T053), and learned reliability arrives with the learning loop (T070)."""
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
