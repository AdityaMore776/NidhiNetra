"""Pre-sanction check (T064): every engine on a recommendation before it is sanctioned.

Since T051 each engine judges ANY recommendation from stored tables (no per-work answers),
so a recommendation typed into the form meets exactly the rules the 2,09,993 real works met:
Guideline Compliance (prohibited work, outside-area ceiling, a big sum that says nothing),
Cost (the comfort zone), Duplicate & Split (compared live with its district). The answer is
a colour with the engines' own sentences. It never blocks: the district authority decides.

  RED    the risk score reaches the review queue (HIGH or CRITICAL), or a serious rule
         breach (a hard finding, e.g. above the outside-area ceiling)
  AMBER  any engine raised a question (a finding with a risk), e.g. a possible repeat, a
         price above the comfort limit, a prohibited-work reading, a missing work type
  GREEN  nothing the checks can see; not a clean chit (the papers and the site are unseen)

A new recommendation is dated the data's "today", so the sanction clock (R01) has not run.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from drishti.agents import registry
from drishti.agents.contract import Status
from drishti.pipeline.orchestrator import Assessment

REVIEW_BANDS = ("CRITICAL", "HIGH")

ADVICE = {
    "RED": "Needs checking before sanction: at least one serious question below. This check "
           "never blocks a sanction; the district authority decides.",
    "AMBER": "Check the points below before sanction. They are questions, not findings.",
    "GREEN": "No question from the checks the record allows (rules, cost, repeats and splits). "
             "This is not a clean chit: the papers and the site are not seen here.",
}


@dataclass
class PreSanction:
    colour: str
    advice: str
    score: float
    band: str
    reasons: list[dict] = field(default_factory=list)
    not_checked: list[dict] = field(default_factory=list)


def judge(a: Assessment) -> PreSanction:
    names = {e.id: e.name for e in registry.engines()}
    reasons, not_checked, hard = [], [], False
    for r in a.agents:
        if r.status in (Status.NOT_ASSESSABLE, Status.ERROR):
            not_checked.append({"engine": names.get(r.agent, r.agent), "why": r.headline})
            continue
        if r.status != Status.ASSESSED:
            continue
        for f in r.findings:
            if f.risk <= 0:
                continue
            hard = hard or f.hard
            reasons.append({"engine": names.get(r.agent, r.agent), "code": f.code,
                            "text": f.text, "risk": round(f.risk, 3), "serious": f.hard})
    reasons.sort(key=lambda x: -x["risk"])
    if hard or a.fused.band in REVIEW_BANDS:
        colour = "RED"
    elif reasons:
        colour = "AMBER"
    else:
        colour = "GREEN"
    return PreSanction(colour=colour, advice=ADVICE[colour], score=round(a.fused.score, 4),
                       band=a.fused.band, reasons=reasons, not_checked=not_checked)
