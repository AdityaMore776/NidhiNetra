"""An agent's answer as one level, for every agent (T168; Cost's own reading is T167's levels.py).

  fits   ASSESSED, no finding at all
  edge   ASSESSED, only notes (risk 0) or a fact that never queues a work (risk < FACT_RISK,
         e.g. Time & Rules' SANCTIONED_LATE, an office's pace)
  check  a finding from FACT_RISK up to ASK_RISK: worth checking
  ask    a finding at ASK_RISK or above: a question
  na     NOT_ASSESSABLE / NOT_APPLICABLE / ERROR: could not judge (a status, never a clean chit)

The Cost agent writes its own level (evidence["level"], T167); it is read as written.
"""

from __future__ import annotations

from drishti.agents.contract import AgentResult, Status

ASK_RISK = 0.4
FACT_RISK = 0.1
LEVELS = ("fits", "edge", "check", "ask", "na")
FRAUDS = ("fraud", "evasion")


def level(r: AgentResult | None) -> str:
    if r is None or r.status != Status.ASSESSED:
        return "na"
    ev = r.evidence or {}
    if isinstance(ev.get("level"), str):
        return ev["level"]
    risks = [f.risk for f in r.findings]
    top = max(risks, default=0.0)
    if top >= ASK_RISK:
        return "ask"
    if top >= FACT_RISK:
        return "check"
    return "edge" if r.findings else "fits"


def codes(r: AgentResult | None, counted: bool = True) -> list[str]:
    if r is None:
        return []
    return sorted(f.code for f in r.findings if (f.risk >= FACT_RISK) == counted)


def verdict(truth: str, allowed: tuple[str, ...], got: str) -> str:
    """pass | soft | hard. Hard: a fraud excused (fits/edge), an honest case asked when its
    label does not allow it, broken data read as clean (fits)."""
    if got in allowed:
        return "pass"
    if truth in FRAUDS:
        return "hard" if got in ("fits", "edge") else "soft"
    if truth == "broken":
        return "hard" if got == "fits" else "soft"
    return "hard" if got == "ask" else "soft"


def scores(truth: str, allowed: tuple[str, ...], ideal: str, got: str) -> dict[str, float]:
    """The per-case metrics (NaN where a metric does not apply): each a mean over the cases."""
    nan = float("nan")
    fraud = truth in FRAUDS
    honest = truth in ("honest", "edge")
    return {
        "pass": float(got in allowed),
        "fraud_caught": float(got in ("check", "ask")) if fraud else nan,
        "fraud_excused": float(got in ("fits", "edge")) if fraud else nan,
        "honest_clear": float(got in ("fits", "edge")) if honest else nan,
        "honest_asked": float(got == "ask" and "ask" not in allowed) if honest else nan,
        "broken_cleared": float(got == "fits") if truth == "broken" else nan,
        "ideal": float(got == ideal),
    }
