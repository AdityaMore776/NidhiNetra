"""Guideline Compliance engine: does the work follow the MPLADS guidelines?

Rules as code (reference/rules.json, the blueprint's R01-R11). Each rule names its
guideline paragraph, a severity and an English and Hindi message. The engine's signal is
the highest severity broken (HIGH 1.0, MEDIUM 0.6, LOW 0.3); the evidence lists every
broken rule with its value and limit.

Measured choices (real export, see data/trial/compliance_trial.py):
  R01  the 75-day sanction clock (para 3.12) leaves out days under the 2024 general
       election's model code of conduct, as the paragraph itself says to; state
       assembly elections are not modelled (a limitation, stated).
  R02  the one-year norm (para 3.13) says "generally" and 7 in 10 works exceed it, so
       past one year is LOW; MEDIUM only past the type's own 98th percentile.
  R06  an impossible date from a bulk-entry quarter is LOW, elsewhere MEDIUM
       (validation/timeline.py measured why).
  R07  the Eligibility v2 reader (56% precision on a fresh sample): MEDIUM, says "verify".
  R03 R04 R05 R09 R10 need expenditure, progress or SC/ST-area data that the public
       export does not carry: listed as "could not check", never as passed.

Wording never accuses (the contract enforces it). MPs are never scored.
"""

from __future__ import annotations

import json
import time
from datetime import date
from functools import cache
from pathlib import Path

from drishti import reference
from drishti.agents.compliance.eligibility import v2 as inadmissible
from drishti.agents.contract import AgentResult, Finding, Status
from drishti.agents.statistical.scope import undescribed
from drishti.validation.timeline import impossible_date

AGENT = "compliance"
VERSION = "compliance-1.0.0"
QUESTION = "Does the work follow the MPLADS guidelines?"
RULES_FILE = Path(reference.__file__).resolve().parent / "rules.json"

# 2024 Lok Sabha election: model code of conduct from the schedule's announcement to its
# withdrawal (Election Commission of India press notes, 16 March and 6 June 2024).
MCC_PERIODS = ((date(2024, 3, 16), date(2024, 6, 6)),)
CONFIDENCE = 0.9


@cache
def rules() -> dict[str, dict]:
    data = json.loads(RULES_FILE.read_text(encoding="utf-8"))
    return {r["id"]: r for r in data["rules"]}


@cache
def signal_of() -> dict[str, float]:
    return json.loads(RULES_FILE.read_text(encoding="utf-8"))["severity_signal"]


def inr(v: float) -> str:
    if v >= 1e7:
        return f"Rs {v / 1e7:.2f} crore"
    if v >= 1e5:
        return f"Rs {v / 1e5:.2f} lakh"
    return f"Rs {v:,.0f}"


def mcc_days(start: date, end: date) -> int:
    """Days between start and end that fall under a model code of conduct."""
    total = 0
    for a, b in MCC_PERIODS:
        lo, hi = max(start, a), min(end, b)
        if hi >= lo:
            total += (hi - lo).days + 1
    return total


def _clause(clause_id: str, key: str) -> float:
    return float(reference.clause(clause_id)["establishes"][key])


def _finding(rule_id: str, severity: str, text: str, text_hi: str, **evidence) -> Finding:
    r = rules()[rule_id]
    return Finding(r["code"], text, hard=severity == "HIGH", risk=signal_of()[severity],
                   evidence={"rule": rule_id, "severity": severity, "title": r["title"],
                             "guideline_ref": r["guideline_ref"], "message_hi": text_hi,
                             **evidence})


def evaluate(work: dict, as_of: date, p98: float | None = None, timeline=None) -> list[Finding]:
    out: list[Finding] = []
    status = work.get("status")
    rec, done = work.get("recommended_date"), work.get("completed_date")
    amount = float(work.get("amount") or 0)

    # R01 waiting for sanction
    if status == "RECOMMENDED" and rec:
        limit = int(_clause("SANCTION_PERIOD", "sanction_period_days"))
        waited = (as_of - rec).days - mcc_days(rec, as_of)
        if waited > limit:
            r = rules()["R01"]
            fmt = {"days": f"{waited:,}", "limit": limit, "ref": r["guideline_ref"]}
            out.append(_finding("R01", r["severity"], r["message_en"].format(**fmt),
                                r["message_hi"].format(**fmt), value=waited, limit=limit,
                                mcc_days_excluded=mcc_days(rec, as_of)))

    # R02 open too long
    if status == "SANCTIONED" and rec:
        days = (as_of - rec).days
        norm = int(_clause("COMPLETION_PERIOD", "completion_period_days"))
        r = rules()["R02"]
        type_name = reference.work_type_name(work.get("work_type_code"))
        if p98 is not None and days > p98:
            fmt = {"days": f"{days:,}", "limit": f"{p98:,.0f}", "type": type_name}
            out.append(_finding("R02", "MEDIUM", r["message_en"].format(**fmt),
                                r["message_hi"].format(**fmt), value=days, limit=p98))
        elif days > norm:
            fmt = {"days": f"{days:,}", "ref": "para 3.13"}
            out.append(_finding("R02", "LOW", r["low_message_en"].format(**fmt),
                                r["low_message_hi"].format(**fmt), value=days, limit=norm))

    # R06 impossible order of dates
    imp = impossible_date(rec, done, work.get("agency_name"), timeline)
    if imp:
        sev = "MEDIUM" if imp.risk >= 0.30 else "LOW"
        hi = (f"कार्य अनुशंसा ({rec}) से पहले पूर्ण ({done}) दर्ज है; तारीखों की जाँच आवश्यक।")
        out.append(_finding("R06", sev, imp.message, hi, recommended=str(rec), completed=str(done)))
    if done and done > as_of:
        out.append(_finding(
            "R06", "LOW",
            f"Completion date {done.isoformat()} is after the data was published "
            f"({as_of.isoformat()}); the date needs correcting.",
            f"पूर्णता तिथि {done.isoformat()} डेटा प्रकाशन ({as_of.isoformat()}) के बाद की है; "
            f"तिथि सुधार आवश्यक।", completed=str(done)))

    # R07 possibly inadmissible
    m = inadmissible(work.get("description"))
    if m:
        r = rules()["R07"]
        fmt = {"keyword": m.keyword, "item": m.annexure_item or "-", "text": m.text}
        out.append(_finding("R07", r["severity"], r["message_en"].format(**fmt),
                            r["message_hi"].format(**fmt), item=m.item_id,
                            annexure_item=m.annexure_item))

    # R08 outside the constituency above the ceiling
    ceiling = _clause("OUTSIDE_CONSTITUENCY_CEILING", "outside_constituency_ceiling_inr")
    if work.get("is_outside_constituency") and amount > ceiling:
        r = rules()["R08"]
        fmt = {"limit": inr(ceiling), "amount": inr(amount), "ref": "para 2.9"}
        out.append(_finding("R08", r["severity"], r["message_en"].format(**fmt),
                            r["message_hi"].format(**fmt), value=amount, limit=ceiling))

    # R11 key data missing
    missing, missing_hi = [], []
    if amount <= 0:
        missing.append("an amount")
        missing_hi.append("राशि")
    if not work.get("work_type_code"):
        missing.append("a work type")
        missing_hi.append("कार्य का प्रकार")
    if not rec:
        missing.append("a recommendation date")
        missing_hi.append("अनुशंसा तिथि")
    if undescribed(work.get("description")):
        missing.append("a description of what is built or bought")
        missing_hi.append("क्या बनाया या खरीदा गया इसका विवरण")
    if missing:
        r = rules()["R11"]
        out.append(_finding("R11", "LOW",
                            r["message_en"].format(missing=", ".join(missing)),
                            r["message_hi"].format(missing_hi=", ".join(missing_hi)),
                            missing=missing))
    return out


def not_checked() -> list[str]:
    return [f"{r['id']} {r['title']}: {r['needs']}." for r in rules().values()
            if not r["evaluable"]]


def assess(work: dict, as_of: date, p98: float | None = None, timeline=None) -> AgentResult:
    t0 = time.perf_counter()
    if not work.get("status"):
        return AgentResult(agent=AGENT, status=Status.NOT_ASSESSABLE, verdict="NOT_ASSESSABLE",
                           risk=0.0, confidence=0.0, hard=False, version=VERSION,
                           headline="Cannot be assessed: the record carries no status, so its "
                                    "stage cannot be checked against the guidelines. This is "
                                    "not a clean chit.",
                           duration_ms=int((time.perf_counter() - t0) * 1000))
    findings = evaluate(work, as_of, p98, timeline)
    limitations = ["Could not check (the public export does not carry the data): "
                   + " ".join(not_checked()),
                   "The sanction clock leaves out the 2024 general election's model code of "
                   "conduct, but not state assembly elections."]
    top = max(findings, key=lambda f: f.risk, default=None)
    broken = sorted({f.evidence["rule"] for f in findings})
    return AgentResult(
        agent=AGENT, status=Status.ASSESSED,
        verdict=top.code if top else "COMPLIANT_AS_FAR_AS_CHECKED",
        risk=top.risk if top else 0.0, confidence=CONFIDENCE,
        hard=any(f.hard for f in findings),
        headline=top.text if top else
        "No guideline rule that the public data can check is broken.",
        version=VERSION, findings=findings, limitations=limitations,
        evidence={"rules_broken": broken,
                  "rules_checked": [r for r, v in rules().items() if v["evaluable"]],
                  "rules_not_checkable": [r for r, v in rules().items() if not v["evaluable"]]},
        duration_ms=int((time.perf_counter() - t0) * 1000))
