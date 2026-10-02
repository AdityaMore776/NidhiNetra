"""Fund Flow engine: is money stuck waiting for sanction? (stored id `delay`)

T053 (1 Oct 2026). This slot held the blueprint's Delay Prediction, then Delay & Fund Flow
(T410). The prediction was removed: two methods (LightGBM, then a late-rate ladder) both
ranked works at about 0.70 AUC against a 0.80 target, and with 73% of works finishing late
anyway, "likely to run late" told an officer little that Guideline Compliance R02 (how
overdue an open work really is) does not. What stays is what was exact on real data
(data/trial/delay_fund_flow_trial.py, FINDINGS C2):

  TERM_ENDED_UNSANCTIONED  recommended under a Lok Sabha term that has ended (reference/
                           rules.json "terms") and still not sanctioned: the money of a
                           dissolved House waiting (3,331 works, Rs 168.9 crore): 0.40
  OFFICE_SANCTION_BACKLOG  the implementing office still has at least twice its district's
                           share of recommendations older than the sanction clock waiting
                           (20+ of them): 0.20; the counts are always given as facts
How long this work has waited is Guideline Compliance's R01, so it is not counted again.

  NOT_APPLICABLE  sanctioned or completed works: no money is waiting for sanction
  NOT_ASSESSABLE  a recommended work with no readable recommendation date, or one after the
                  data's own date (one of the two is wrong, so the wait cannot be counted)
Foolproofing (2 Oct 2026): status, term and house are read in any case and spacing, and a
date written as text reads as the date (backlog.day / backlog.norm).
"""

from __future__ import annotations

import json
import time
from datetime import date
from functools import cache
from pathlib import Path

from drishti import reference
from drishti.agents.contract import AgentResult, Finding, Status
from drishti.agents.delay.backlog import OfficeBacklog, day, norm

AGENT = "delay"
VERSION = "fund-flow-1.0.0"
QUESTION = "Is money stuck waiting for sanction?"
BACKLOG_TIMES, BACKLOG_MIN = 2.0, 20
CONFIDENCE = 0.9       # dates and counts from the record, no prediction


@cache
def ended_terms() -> dict[str, date]:
    path = Path(reference.__file__).resolve().parent / "rules.json"
    data = json.loads(path.read_text(encoding="utf-8"))["terms"]["ended"]
    return {k: date.fromisoformat(v["date"]) for k, v in data.items()}


@cache
def _terms_by_key() -> dict[str, tuple[str, date]]:
    return {norm(k): (k, v) for k, v in ended_terms().items()}


def _quiet(status: Status, text: str, t0: float) -> AgentResult:
    return AgentResult(agent=AGENT, status=status, verdict=status.value, risk=0.0,
                       confidence=0.0, hard=False, version=VERSION, headline=text,
                       duration_ms=int((time.perf_counter() - t0) * 1000))


def assess(work: dict, as_of: date, backlog: OfficeBacklog | None = None) -> AgentResult:
    t0 = time.perf_counter()
    if norm(work.get("status")) != "recommended":
        return _quiet(Status.NOT_APPLICABLE, "Sanctioned or complete: no money is waiting for "
                      "sanction on this work.", t0)
    rec = day(work.get("recommended_date"))
    if rec is None:
        return _quiet(Status.NOT_ASSESSABLE, "Cannot be assessed: the record carries no "
                      "readable recommendation date. This is not a clean chit.", t0)
    if rec > as_of:
        return _quiet(Status.NOT_ASSESSABLE, f"Cannot be assessed: the recommendation date "
                      f"({rec.isoformat()}) is after the data's own date ({as_of.isoformat()}), "
                      "so one of them is wrong and the wait cannot be counted. This is not a "
                      "clean chit.", t0)
    findings: list[Finding] = []
    facts: dict = {"days_waiting": (as_of - rec).days}
    limitations: list[str] = []
    term, ended = _terms_by_key().get(norm(work.get("term")), (work.get("term"), None))
    if ended and as_of > ended:
        findings.append(Finding(
            "TERM_ENDED_UNSANCTIONED",
            f"Recommended under the {term}, whose term ended on {ended:%d %b %Y}; still not "
            f"sanctioned {(as_of - ended).days:,} days later. Check whether the work will go "
            "ahead or its money should be released.",
            hard=False, risk=0.40, evidence={"term": term, "term_ended": str(ended)}))
    if norm(work.get("house")) == "rajya sabha":
        limitations.append("Rajya Sabha members' terms are individual and not in the data, so "
                           "an ended term is not checked for this work.")
    clock = int(reference.clause("SANCTION_PERIOD")["establishes"]["sanction_period_days"])
    sentence = ""
    if backlog is not None and work.get("agency_name"):
        ow, on = backlog.office(work.get("district_lgd"), work.get("agency_name"), as_of, clock)
        dw, dn = backlog.district(work.get("district_lgd"), as_of, clock)
        facts |= {"office_waiting": ow, "office_recommended": on, "district_waiting": dw,
                  "district_recommended": dn}
        o_share, d_share = (ow / on if on else 0.0), (dw / dn if dn else 0.0)
        sentence = (f"This implementing office still has {ow:,} of its {on:,} recommendations "
                    f"older than {clock} days waiting for sanction ({o_share:.0%}); across the "
                    f"district {dw:,} of {dn:,} ({d_share:.0%}).")
        if ow >= BACKLOG_MIN and d_share > 0 and o_share >= BACKLOG_TIMES * d_share:
            findings.append(Finding("OFFICE_SANCTION_BACKLOG",
                                    sentence + " Check the office's sanction pipeline.",
                                    hard=False, risk=0.20, evidence=dict(facts)))
    findings.sort(key=lambda f: -f.risk)
    top = findings[0] if findings else None
    headline = top.text if top else (
        f"Waiting {facts['days_waiting']:,} days for sanction (Guideline Compliance judges the "
        "wait); its term has not ended" + (f". {sentence}" if sentence else "."))
    return AgentResult(
        agent=AGENT, status=Status.ASSESSED,
        verdict=top.code if top else "NOTHING_STUCK_BEYOND_THE_WAIT",
        risk=top.risk if top else 0.0, confidence=CONFIDENCE, hard=False, headline=headline,
        version=VERSION, findings=findings, limitations=limitations, evidence=facts,
        duration_ms=int((time.perf_counter() - t0) * 1000))
