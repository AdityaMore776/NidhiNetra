"""Office Patterns engine: does this work's office price or close works in an unusual way?

A single work priced at Rs 4.98 lakh says little: amounts pile up just under Rs 5 lakh across the
whole scheme. An office that prices almost every work there is a different matter: works sized to
stay under a limit (the inspection, technical-sanction or tender threshold) is the "splitting and
just-below-threshold pricing" the audit literature lists (playbook classes C4 and D1). The
question is asked of the OFFICE (index.py), and a work carries it only when the work itself shows
the habit. Offices only, never an MP.

  PRICED_AT_LIMIT        this work sits 96-100% of Rs 5 or 10 lakh, and its office prices works
                         there routinely (lower Wilson bound >= 3x the national share, 30+ works)
  built after sanction   (the office side of Guideline Compliance R14) the office records
                         constructions complete within 7 days of their sanction routinely: stated
                         as a fact, never a finding, because R14 already asks about the work

Signals are small (0.30): a habit of the office is a reason to look at the office's works
together, not proof about one of them. The counts are always given as facts.

  NOT_APPLICABLE  the record names no office (nothing to compare)
  NOT_ASSESSABLE  no office index was given, or the office has too few works to judge
"""

from __future__ import annotations

import time

from drishti.agents.contract import AgentResult, Finding, Status
from drishti.agents.office_patterns.index import (
    MIN_BUILT,
    MIN_PRICED,
    OfficeIndex,
    built_right_after_sanction,
    limit_just_above,
)

AGENT = "office_patterns"
VERSION = "office-patterns-1.0.0"
QUESTION = "Does this work's office price or close works in an unusual way?"
CONFIDENCE = 0.7
LIMIT_RISK = 0.30


def _lakh(v: float) -> str:
    return f"Rs {v / 1e5:,.2f} lakh"


def _quiet(status: Status, text: str, t0: float, **evidence) -> AgentResult:
    return AgentResult(agent=AGENT, status=status, verdict=status.value, risk=0.0,
                       confidence=0.0, hard=False, version=VERSION, headline=text,
                       evidence=evidence, duration_ms=int((time.perf_counter() - t0) * 1000))


def assess(work: dict, index: OfficeIndex | None) -> AgentResult:
    t0 = time.perf_counter()
    if not work.get("agency_name"):
        return _quiet(Status.NOT_APPLICABLE, "The record names no implementing office, so its "
                      "habits cannot be compared.", t0)
    if index is None or not index.covers(work):
        return _quiet(Status.NOT_ASSESSABLE, "Cannot be assessed: the office's other works were "
                      "not available to compare with. This is not a clean chit.", t0)
    price = index.limit_pricing(work)
    built = index.after_sanction(work)
    facts: dict = {}
    if price:
        facts["priced_just_under_a_limit"] = {"office": price.count, "of": price.total,
                                              "share": round(price.share, 3),
                                              "national_share": round(price.national, 4)}
    if built:
        facts["built_within_a_week_of_sanction"] = {"office": built.count, "of": built.total,
                                                    "share": round(built.share, 3),
                                                    "national_share": round(built.national, 4)}
    if (price is None or price.total < MIN_PRICED) and (built is None or built.total < MIN_BUILT):
        return _quiet(Status.NOT_ASSESSABLE, f"Cannot be assessed: the office has only "
                      f"{price.total if price else 0} works on record, too few to tell a habit "
                      "from chance. This is not a clean chit.", t0, **facts)

    findings: list[Finding] = []
    lim = limit_just_above(work.get("amount"))
    if lim and price and price.routine:
        findings.append(Finding(
            "PRICED_AT_LIMIT",
            f"Priced at {_lakh(float(work['amount']))}, just under the {_lakh(lim)} limit, by an "
            f"office that priced {price.count:,} of its {price.total:,} works just under a limit "
            f"({price.share:.0%}, against {price.national:.1%} across the scheme). Check whether "
            "works are being sized to stay under the limit, for example by splitting one job.",
            hard=False, risk=LIMIT_RISK,
            evidence={"limit": lim, **facts["priced_just_under_a_limit"]}))
    notes = []
    if built and built.routine and built_right_after_sanction(work):
        # the same fact as Guideline Compliance R14 (which names the office's habit): stated
        # here, never counted twice
        notes.append(f"This office recorded {built.count:,} of its {built.total:,} constructions "
                     f"complete within a week of their sanction ({built.share:.0%}, against "
                     f"{built.national:.1%} across the scheme); Guideline Compliance R14 asks "
                     "about this work.")
    findings.sort(key=lambda f: -f.risk)
    top = findings[0] if findings else None
    if top is None:
        bits = []
        if price:
            bits.append(f"{price.count:,} of {price.total:,} works priced just under a limit "
                        f"({price.share:.0%}; scheme {price.national:.1%})")
        if built and built.total:
            bits.append(f"{built.count:,} of {built.total:,} constructions complete within a "
                        f"week of sanction ({built.share:.0%}; scheme {built.national:.1%})")
        headline = (" ".join(notes) if notes else
                    "Nothing unusual about this work's office: " + "; ".join(bits) + ".")
    else:
        headline = top.text
    return AgentResult(
        agent=AGENT, status=Status.ASSESSED,
        verdict=top.code if top else "OFFICE_AS_USUAL", risk=top.risk if top else 0.0,
        confidence=CONFIDENCE, hard=False, headline=headline, version=VERSION,
        findings=findings, evidence=facts,
        limitations=["A habit of the office, not proof about this work: look at the office's "
                     "works together.",
                     "The limits are Rs 5 and 10 lakh (reference/rules.json); a state's own "
                     "tender limits are not modelled."],
        duration_ms=int((time.perf_counter() - t0) * 1000))
