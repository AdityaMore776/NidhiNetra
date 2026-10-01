"""Delay & Fund Flow engine: is time or money stuck on this work? (stored id `delay`)

T410 merged the 12-checker plan's C2 Fund Flow into the Delay engine (T051, 12 -> 8): both ask
whether a work's time or money is stuck, from the same dates.

DELAY (open works under a year old). v2 (T051): the late-rate ladder in rates.py (office ->
district x type -> state x type -> type), computed for any work from stored counts. Measured
(results/delay_rates.json): strict backtest 0.705, unseen districts 0.685, both below the 0.80
target, so the engine is shown, not counted.
  signal   how much likelier to run late than the average work: (p - base) / (1 - base)
  finding  only when p reaches the riskiest tenth of open works (a cut stored with the
           counts, never below max(base + 0.15, 0.90)) AND the estimate rests on at least 30 past
           works; the sentence quotes those works' own record ("this office finished 3 of its
           212 past works within a year"), never a bare repeated percentage

FUND FLOW (works still waiting for sanction). From data/trial/fund_flow_trial.py (FINDINGS C2):
  TERM_ENDED_UNSANCTIONED  recommended under a Lok Sabha term that has ended (reference/
                           rules.json "terms") and still not sanctioned: the money of a dissolved
                           House waiting (3,331 works, Rs 169 crore in the export): 0.40
  OFFICE_SANCTION_BACKLOG  the implementing office still has at least twice its district's share
                           of old recommendations waiting (20+ of them): 0.20; the office's and
                           the district's counts are always given as facts
How long this work has waited is Guideline Compliance's R01, so it is not counted here again.

Wording never says a work "will be late"; it says how works like it have gone.

  NOT_APPLICABLE  completed works, and open works past one year with no fund-flow fact (their
                  delay is Guideline Compliance R02's)
  NOT_ASSESSABLE  no recommendation date, or no late-rate table loaded for an open young work
"""

from __future__ import annotations

import json
import time
from datetime import date
from functools import cache
from pathlib import Path

from drishti import reference
from drishti.agents.contract import AgentResult, Finding, Status
from drishti.agents.delay.backlog import OfficeBacklog
from drishti.agents.delay.rates import DelayRates

AGENT = "delay"
VERSION = "delay-fund-flow-1.0.0"
QUESTION = "Is time or money stuck on this work?"
HORIZON_DAYS = 365
FLAG_MARGIN, FLAG_FLOOR, FLAG_MIN_WORKS = 0.15, 0.90, 30
BACKLOG_TIMES, BACKLOG_MIN = 2.0, 20
CONFIDENCE = 0.6       # AUC ~0.70 on a strict backtest: a ranking aid, not a forecast


@cache
def ended_terms() -> dict[str, date]:
    path = Path(reference.__file__).resolve().parent / "rules.json"
    data = json.loads(path.read_text(encoding="utf-8"))["terms"]["ended"]
    return {k: date.fromisoformat(v["date"]) for k, v in data.items()}


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


def fund_flow(work: dict, as_of: date, backlog: OfficeBacklog | None) -> tuple[list[Finding],
                                                                             dict]:
    """Facts and findings for a work still waiting for sanction."""
    out: list[Finding] = []
    facts: dict = {}
    if work.get("status") != "RECOMMENDED":
        return out, facts
    rec = work.get("recommended_date")
    term = work.get("term")
    ended = ended_terms().get(term or "")
    if ended and rec and as_of > ended:
        out.append(Finding(
            "TERM_ENDED_UNSANCTIONED",
            f"Recommended under the {term}, whose term ended on {ended:%d %b %Y}; still not "
            f"sanctioned {(as_of - ended).days:,} days later. Check whether the work will go "
            "ahead or its money should be released.",
            hard=False, risk=0.40, evidence={"term": term, "term_ended": str(ended)}))
    if backlog is not None and work.get("agency_name"):
        clock = int(reference.clause("SANCTION_PERIOD")["establishes"]["sanction_period_days"])
        ow, on = backlog.office(work.get("district_lgd"), work.get("agency_name"), as_of, clock)
        dw, dn = backlog.district(work.get("district_lgd"), as_of, clock)
        facts = {"office_waiting": ow, "office_recommended": on, "district_waiting": dw,
                 "district_recommended": dn}
        o_share, d_share = (ow / on if on else 0.0), (dw / dn if dn else 0.0)
        if ow >= BACKLOG_MIN and d_share > 0 and o_share >= BACKLOG_TIMES * d_share:
            out.append(Finding(
                "OFFICE_SANCTION_BACKLOG",
                f"This implementing office still has {ow:,} of its {on:,} recommendations older "
                f"than {clock} days waiting for sanction ({o_share:.0%}); across the district "
                f"{dw:,} of {dn:,} ({d_share:.0%}). Check the office's sanction pipeline.",
                hard=False, risk=0.20, evidence=facts))
    return out, facts


def assess(work: dict, as_of: date, rates: DelayRates | None,
           backlog: OfficeBacklog | None = None) -> AgentResult:
    t0 = time.perf_counter()
    if work.get("status") == "COMPLETED":
        return _quiet(Status.NOT_APPLICABLE, "The work is complete; no time or money is "
                      "waiting on it.", t0)
    rec = work.get("recommended_date")
    if rec is None:
        return _quiet(Status.NOT_ASSESSABLE, "Cannot be assessed: the record carries no "
                      "recommendation date. This is not a clean chit.", t0)
    age = (as_of - rec).days
    findings, facts = fund_flow(work, as_of, backlog)
    limitations = []
    if work.get("status") == "RECOMMENDED" and work.get("house") == "Rajya Sabha":
        limitations.append("Rajya Sabha members' terms are individual and not in the data, so "
                           "an ended term is not checked for this work.")

    p = base = None
    est = None
    headline = None
    if age <= HORIZON_DAYS:
        est = rates.estimate(work) if rates is not None else None
        if est is None and not findings:
            return _quiet(Status.NOT_ASSESSABLE, "Cannot be assessed: no record of past "
                          "completion times is loaded. This is not a clean chit.", t0)
    if est is not None:
        base, p = rates.base, est.p_late
        signal = max(0.0, min(1.0, (p - base) / (1 - base))) if base < 1 else 0.0
        record = _record(est.level, est.n, est.rate, work)
        limitations.append("Learned from how past works went; it cannot see site conditions, "
                           "and most MPLADS works miss the one-year norm anyway.")
        if est.level != "office":
            limitations.append(f"No past record for this implementing office yet; the estimate "
                               f"uses {_whose(est.level, work)}.")
        cut = max(base + FLAG_MARGIN, FLAG_FLOOR, rates.flag_p or 0.0)
        if p >= cut and est.n >= FLAG_MIN_WORKS:
            findings.append(Finding(
                "LIKELY_LATE",
                f"Open {age:,} days. Works like it usually run past the one-year norm: "
                f"{record} (all works: {1 - base:.0%} within a year). Worth an early progress "
                "check.",
                hard=False, risk=signal,
                evidence={"p_late": p, "base_rate": base, "level": est.level, "n": est.n,
                          "rate": est.rate, "steps": [list(s) for s in est.steps]}))
        else:
            headline = (f"Open {age:,} days; {record}. Not among the works most likely to run "
                        "late.")
    elif not findings:
        return _quiet(Status.NOT_APPLICABLE, f"Already open {age:,} days, past the one-year "
                      "norm; Guideline Compliance reports how overdue it is.", t0)

    findings.sort(key=lambda f: -f.risk)
    top = findings[0] if findings else None
    risk = max([f.risk for f in findings] + ([signal] if est is not None else []))
    return AgentResult(
        agent=AGENT, status=Status.ASSESSED,
        verdict=top.code if top else "ORDINARY_DELAY_RISK",
        risk=risk, confidence=CONFIDENCE, hard=False,
        headline=top.text if top else headline, version=VERSION,
        findings=findings, limitations=limitations,
        evidence={"p_late": p, "base_rate": base, "level": est.level if est else None,
                  "n": est.n if est else None, "days_open": age, **facts},
        duration_ms=int((time.perf_counter() - t0) * 1000))
