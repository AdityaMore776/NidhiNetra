"""The Cost agent's answer as one level (T167, plan docs/plans/T167-cost-eval.md §2).

  fits   ASSESSED, no finding, no leeway used
  edge   ASSESSED, no finding, but a leeway explained something unusual (evidence["leeway"])
  check  a finding below ASK_RISK: "check this"
  ask    a finding at ASK_RISK or above: a question before sanction
  na     NOT_ASSESSABLE / NOT_APPLICABLE: could not judge (a status, never a clean chit)

An agent that predates evidence["level"] is read the same way from its findings, and its notes
stand in for the leeway (a note that excuses something: above the usual, MP as high, held).
"""

from __future__ import annotations

from drishti.agents.contract import AgentResult, Status

ASK_RISK = 0.4
EXCUSING_NOTES = ("above the usual", "not raised as a question", "held as a likely typing",
                  "leaving out the line held", "on its own that is not a question",
                  "priced from other agencies' forms across the state")


def level(r: AgentResult) -> str:
    if r.status != Status.ASSESSED:
        return "na"
    ev = r.evidence or {}
    if isinstance(ev.get("level"), str):
        return ev["level"]
    risks = [f.risk for f in r.findings if f.risk > 0]
    if risks:
        return "ask" if max(risks) >= ASK_RISK else "check"
    notes = " ".join(ev.get("notes") or []) + " " + r.headline
    return "edge" if any(n in notes for n in EXCUSING_NOTES) else "fits"


def verdict(truth: str, allowed: tuple[str, ...], got: str) -> str:
    """pass | soft (an honest case asked to be checked, a fraud not judged) | hard (a fraud
    excused, an honest case asked)."""
    if got in allowed:
        return "pass"
    if truth == "fraud":
        return "hard" if got in ("fits", "edge") else "soft"
    return "hard" if got == "ask" else "soft"
