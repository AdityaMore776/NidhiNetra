"""Delay Prediction engine: is this open work likely to miss the one-year norm?

The model (data/build_delay_model.py, LightGBM on facts known when the work was
recommended: the office's and district's past records, the office's backlog, type, size,
month) is trained offline; each open work's score and its three strongest reasons are
stored in work_signals["delay"]. This engine only reads them.

Measured honestly (FINDINGS, results/delay_model.json): the model ranks better than the
office's own record, but most MPLADS works miss the one-year norm anyway, so the score is
read as a RANK among open works, not as a verdict:

  signal = max(0, (rank - 0.5) / 0.5)   # the riskier half of open works, 0..1
  finding only for the riskiest 10% of open works

Wording never says a work "will be late"; it says how it compares and why.

  NOT_APPLICABLE  completed works (nothing to predict), and open works already past one
                  year (they are overdue, which Guideline Compliance R02 reports)
  NOT_ASSESSABLE  an open work under a year old with no stored score
"""

from __future__ import annotations

import time
from datetime import date

from drishti.agents.contract import AgentResult, Finding, Status

AGENT = "delay"
VERSION = "delay-1.0.0"
QUESTION = "Is this work likely to run late?"
HORIZON_DAYS = 365
FLAG_RANK = 0.90
CONFIDENCE = 0.6       # AUC ~0.7 on a strict backtest: a ranking aid, not a forecast


def _quiet(status: Status, text: str, t0: float) -> AgentResult:
    return AgentResult(agent=AGENT, status=status, verdict=status.value, risk=0.0,
                       confidence=0.0, hard=False, version=VERSION, headline=text,
                       duration_ms=int((time.perf_counter() - t0) * 1000))


def assess(work: dict, as_of: date) -> AgentResult:
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
    s = (work.get("signals") or {}).get("delay")
    if not s or s.get("p_late") is None or s.get("rank_pct") is None:
        return _quiet(Status.NOT_ASSESSABLE, "Cannot be assessed: no delay score has been "
                      "computed for this work yet. This is not a clean chit.", t0)
    p, rank, base = float(s["p_late"]), float(s["rank_pct"]), float(s.get("base_rate") or 0)
    reasons = list(s.get("reasons") or [])
    signal = max(0.0, (rank - 0.5) / 0.5)
    findings = []
    if rank >= FLAG_RANK:
        why = "; ".join(reasons) if reasons else "the combination of its facts"
        findings.append(Finding(
            "LIKELY_LATE",
            f"Among the {100 - int(rank * 100) or 1}% of open works most likely to miss the "
            f"one-year norm: works like it finished late {p:.0%} of the time, against "
            f"{base:.0%} for all works. Main reasons: {why}. Worth an early progress check.",
            hard=False, risk=signal,
            evidence={"p_late": p, "rank_pct": rank, "base_rate": base, "reasons": reasons}))
        headline = findings[0].text
    else:
        headline = (f"Likelihood of missing the one-year norm is {p:.0%} (all works: "
                    f"{base:.0%}); not among the riskiest open works.")
    return AgentResult(
        agent=AGENT, status=Status.ASSESSED,
        verdict="LIKELY_LATE" if findings else "ORDINARY_DELAY_RISK",
        risk=signal, confidence=CONFIDENCE, hard=False, headline=headline, version=VERSION,
        findings=findings,
        limitations=["A ranking learned from past works, tested on later ones; it cannot see "
                     "site conditions, and most MPLADS works miss the one-year norm anyway."],
        evidence={"p_late": p, "rank_pct": rank, "base_rate": base, "reasons": reasons,
                  "days_open": age},
        duration_ms=int((time.perf_counter() - t0) * 1000))
