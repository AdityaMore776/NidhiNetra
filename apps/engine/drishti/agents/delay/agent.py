"""Delay Prediction engine: is this open work likely to miss the one-year norm?

v2 (T051). The estimate is the late-rate ladder in rates.py (office -> district x type ->
state x type -> type), computed for any work from stored counts. v1 read one LightGBM score
per work stored by an offline job: a work recommended after that job had none, and in
districts it had not seen its ranking fell to 0.59. Measured the same way
(results/delay_rates.json): strict backtest 0.705 (v1 0.710), unseen districts 0.685 (v1
0.588). Both below the 0.80 target, so the engine is shown, not counted.

  signal   how much likelier to run late than the average work: (p - base) / (1 - base)
  finding  only when p >= max(base + 0.15, 0.90) AND the estimate rests on at least 30 past
           works; the sentence quotes those works' own record, e.g. "this office finished 3 of
           its 212 past works within a year", never a bare repeated percentage

Wording never says a work "will be late"; it says how works like it have gone.

  NOT_APPLICABLE  completed works (nothing to predict), and open works already past one
                  year (they are overdue, which Guideline Compliance R02 reports)
  NOT_ASSESSABLE  no recommendation date, or no late-rate table loaded
"""

from __future__ import annotations

import time
from datetime import date

from drishti import reference
from drishti.agents.contract import AgentResult, Finding, Status
from drishti.agents.delay.rates import DelayRates

AGENT = "delay"
VERSION = "delay-2.0.0"
QUESTION = "Is this work likely to run late?"
HORIZON_DAYS = 365
FLAG_MARGIN, FLAG_FLOOR, FLAG_MIN_WORKS = 0.15, 0.90, 30
CONFIDENCE = 0.6       # AUC ~0.70 on a strict backtest: a ranking aid, not a forecast


def _quiet(status: Status, text: str, t0: float) -> AgentResult:
    return AgentResult(agent=AGENT, status=status, verdict=status.value, risk=0.0,
                       confidence=0.0, hard=False, version=VERSION, headline=text,
                       duration_ms=int((time.perf_counter() - t0) * 1000))


def _whose(level: str, work: dict) -> str:
    t = reference.work_type_name(work.get("work_type_code"))
    return {"office": "this implementing office",
            "district_type": f"{t} works in this district",
            "state_type": f"{t} works in this state",
            "type": f"{t} works across the scheme"}.get(level, "all works")


def _record(level: str, n: int, rate: float, work: dict) -> str:
    on_time = round(n * (1 - rate))
    if level == "office":
        return (f"{_whose(level, work)} finished {on_time:,} of its {n:,} past works within a "
                "year of recommendation")
    return f"{on_time:,} of {n:,} past {_whose(level, work)} finished within a year"


def assess(work: dict, as_of: date, rates: DelayRates | None) -> AgentResult:
    t0 = time.perf_counter()
    if work.get("status") == "COMPLETED":
        return _quiet(Status.NOT_APPLICABLE, "The work is complete; there is no delay to "
                      "predict.", t0)
    rec = work.get("recommended_date")
    if rec is None:
        return _quiet(Status.NOT_ASSESSABLE, "Cannot be assessed: the record carries no "
                      "recommendation date. This is not a clean chit.", t0)
    age = (as_of - rec).days
    if age > HORIZON_DAYS:
        return _quiet(Status.NOT_APPLICABLE, f"Already open {age:,} days, past the one-year "
                      "norm; Guideline Compliance reports how overdue it is.", t0)
    est = rates.estimate(work) if rates is not None else None
    if est is None:
        return _quiet(Status.NOT_ASSESSABLE, "Cannot be assessed: no record of past "
                      "completion times is loaded. This is not a clean chit.", t0)
    base = rates.base
    p = est.p_late
    signal = max(0.0, min(1.0, (p - base) / (1 - base))) if base < 1 else 0.0
    record = _record(est.level, est.n, est.rate, work)
    limitations = ["Learned from how past works went; it cannot see site conditions, and most "
                   "MPLADS works miss the one-year norm anyway."]
    if est.level != "office":
        limitations.append(f"No past record for this implementing office yet; the estimate "
                           f"uses {_whose(est.level, work)}.")
    findings = []
    if p >= max(base + FLAG_MARGIN, FLAG_FLOOR) and est.n >= FLAG_MIN_WORKS:
        findings.append(Finding(
            "LIKELY_LATE",
            f"Open {age:,} days. Works like it usually run past the one-year norm: "
            f"{record} (all works: {1 - base:.0%} within a year). Worth an early progress "
            "check.",
            hard=False, risk=signal,
            evidence={"p_late": p, "base_rate": base, "level": est.level, "n": est.n,
                      "rate": est.rate, "steps": [list(s) for s in est.steps]}))
        headline = findings[0].text
    else:
        headline = (f"Open {age:,} days; {record}. Not among the works most likely to run "
                    "late.")
    return AgentResult(
        agent=AGENT, status=Status.ASSESSED,
        verdict="LIKELY_LATE" if findings else "ORDINARY_DELAY_RISK",
        risk=signal, confidence=CONFIDENCE, hard=False, headline=headline, version=VERSION,
        findings=findings, limitations=limitations,
        evidence={"p_late": p, "base_rate": base, "level": est.level, "n": est.n,
                  "days_open": age},
        duration_ms=int((time.perf_counter() - t0) * 1000))
