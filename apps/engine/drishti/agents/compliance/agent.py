"""Guideline Compliance engine: does the work follow the MPLADS guidelines?

Rules as code (reference/rules.json, the blueprint's R01-R11). Each rule names its
guideline paragraph, a severity and an English and Hindi message. The engine's signal is
the strongest rule broken; the evidence lists every broken rule with its value and limit.
A severity is a rule's ceiling: the timing rules grow toward it with how far past the limit
the work is (T051), the others score their severity (HIGH 1.0, MEDIUM 0.6, LOW 0.3).

Measured choices (real export, see data/trial/compliance_trial.py):
  R01  the 75-day sanction clock (para 3.12) leaves out days under a model code of conduct,
       as the paragraph itself says to; the periods are reference data (rules.json), and a
       wait running past the date that list was last checked is stated as a limitation.
       State assembly elections are not modelled (a limitation, stated). Signal 0.30 just
       past the clock, 0.60 at four times it.
  R02  the one-year norm (para 3.13) says "generally" and 7 in 10 works exceed it, so
       past one year is LOW (0.15 rising to 0.30 at the type's 98th percentile); past the
       type's own 98th percentile MEDIUM (0.30 rising to 0.60 at twice it).
  R06  an impossible date from a bulk-entry quarter is LOW, elsewhere MEDIUM
       (validation/timeline.py measured why).
  R07  the Eligibility v2 reader (56% precision on a fresh sample): MEDIUM, says "verify".
  R12  a big sum that does not say what or where (Rs 10 lakh+, above its type's national
       top, at most six words, no number, no place name): MEDIUM. R13 a construction of
       Rs 5 lakh+ recorded complete 0-14 days after recommendation, outside a bulk-entry
       quarter and not a backfilled older work: MEDIUM. Both replaced the Odd Overall engine
       (T053, owner's choice): read by eye 30/30 and 13/13 (data/trial/odd_rules_trial.py).
  R03 R04 R05 R09 R10 need expenditure, progress or SC/ST-area data that the public
       export does not carry: listed as "could not check", never as passed.

Wording never accuses (the contract enforces it). MPs are never scored.
"""

from __future__ import annotations

import json
import math
import re
import time
from datetime import date
from functools import cache
from pathlib import Path

from drishti import reference
from drishti.agents.compliance.eligibility import script
from drishti.agents.compliance.eligibility import v2 as inadmissible
from drishti.agents.contract import AgentResult, Finding, Status
from drishti.agents.dup_split.match import place_words
from drishti.agents.statistical.scope import GOODS, scope, undescribed
from drishti.validation.timeline import impossible_date, quarter_of

AGENT = "compliance"
VERSION = "compliance-1.2.0"
QUESTION = "Does the work follow the MPLADS guidelines?"
RULES_FILE = Path(reference.__file__).resolve().parent / "rules.json"

CONFIDENCE = 0.9

# T051: graded signals. A rule broken by a little and by a lot must not score the same (the
# real run gave 3 risk values for 2,09,993 works: 80 and 718 days waiting both scored 0.6).
R01_FULL_TIMES = 4.0         # R01 reaches its severity at four times the sanction clock
R02_LOW = (0.15, 0.30)       # one year .. the type's 98th percentile
R02_FULL_TIMES = 2.0         # R02 reaches MEDIUM at twice the type's 98th percentile

# R12 / R13: the record checks that replaced the Odd Overall engine (T053, owner's choice)
SCOPE_MIN_RS, SCOPE_MAX_WORDS = 1_000_000, 6
# a size written as a word is a stated size ("Purchase of Two Ambulance": read by eye, T053)
WORD_NUMBER = re.compile(r"\b(?:one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|"
                         r"twenty|thirty|forty|fifty|hundred|dozen|ek|do|teen|char|paanch)\b",
                         re.I)
FAST_MIN_RS, FAST_DAYS = 500_000, 14
CONSTRUCTION_TYPES = {"ROAD_CC", "ROAD_BT", "FOOTPATH", "CULVERT", "BRIDGE", "COMMUNITY_HALL",
                      "SCHOOL_BUILDING", "HEALTH_BUILDING", "LIBRARY", "BOUNDARY_WALL",
                      "TOILET_BLOCK", "DRAIN", "POND", "CHECK_DAM", "CREMATORIUM",
                      "PLAYGROUND", "BUS_SHELTER"}
OLD_FY = re.compile(r"\b(20[01]\d|202[0-3])\s*[-/]\s*(\d{2}|20\d{2})\b")   # "(2019-2020)"


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


@cache
def _pauses() -> dict:
    return json.loads(RULES_FILE.read_text(encoding="utf-8"))["election_pauses"]


@cache
def mcc_periods() -> tuple[tuple[date, date], ...]:
    """Model code of conduct periods (reference/rules.json), never a constant in code."""
    return tuple((date.fromisoformat(p["from"]), date.fromisoformat(p["to"]))
                 for p in _pauses()["periods"])


def calendar_checked_until() -> date:
    return date.fromisoformat(_pauses()["checked_until"])


def graded(value: float, start: float, full: float, lo: float, hi: float) -> float:
    """lo at `start`, rising on a log scale to hi at `full`, flat after."""
    if value <= start:
        return lo
    span = math.log(full / start)
    return lo + (hi - lo) * min(1.0, math.log(value / start) / span)


def mcc_days(start: date, end: date) -> int:
    """Days between start and end that fall under a model code of conduct."""
    total = 0
    for a, b in mcc_periods():
        lo, hi = max(start, a), min(end, b)
        if hi >= lo:
            total += (hi - lo).days + 1
    return total


def _clause(clause_id: str, key: str) -> float:
    return float(reference.clause(clause_id)["establishes"][key])


def _finding(rule_id: str, severity: str, text: str, text_hi: str, risk: float | None = None,
             **evidence) -> Finding:
    r = rules()[rule_id]
    return Finding(r["code"], text, hard=severity == "HIGH",
                   risk=signal_of()[severity] if risk is None else risk,
                   evidence={"rule": rule_id, "severity": severity, "title": r["title"],
                             "guideline_ref": r["guideline_ref"], "message_hi": text_hi,
                             **evidence})


def evaluate(work: dict, as_of: date, p98: float | None = None, timeline=None,
             type_top: float | None = None) -> list[Finding]:
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
            sev = signal_of()[r["severity"]]
            risk = graded(waited, limit, limit * R01_FULL_TIMES, signal_of()["LOW"], sev)
            fmt = {"days": f"{waited:,}", "limit": limit, "ref": r["guideline_ref"],
                   "over": f"{waited - limit:,}", "times": f"{waited / limit:.1f}"}
            out.append(_finding("R01", r["severity"], r["message_en"].format(**fmt),
                                r["message_hi"].format(**fmt), risk=risk, value=waited,
                                limit=limit, mcc_days_excluded=mcc_days(rec, as_of)))

    # R02 open too long
    if status == "SANCTIONED" and rec:
        days = (as_of - rec).days
        norm = int(_clause("COMPLETION_PERIOD", "completion_period_days"))
        r = rules()["R02"]
        type_name = reference.work_type_name(work.get("work_type_code"))
        if p98 is not None and days > p98:
            risk = graded(days, p98, p98 * R02_FULL_TIMES, R02_LOW[1], signal_of()["MEDIUM"])
            fmt = {"days": f"{days:,}", "limit": f"{p98:,.0f}", "type": type_name,
                   "over": f"{days - p98:,.0f}"}
            out.append(_finding("R02", "MEDIUM", r["message_en"].format(**fmt),
                                r["message_hi"].format(**fmt), risk=risk, value=days,
                                limit=p98))
        elif days > norm:
            # one year -> the type's own 98th percentile (or twice the norm when unknown)
            top = p98 if p98 is not None and p98 > norm else 2 * norm
            risk = graded(days, norm, top, *R02_LOW)
            fmt = {"days": f"{days:,}", "ref": "para 3.13", "over": f"{days - norm:,}",
                   "type": type_name,
                   "p98": f"{p98:,.0f} days" if p98 is not None else "a time not yet measured"}
            fmt_hi = {**fmt, "p98": f"{p98:,.0f} दिन" if p98 is not None else "अज्ञात अवधि"}
            out.append(_finding("R02", "LOW", r["low_message_en"].format(**fmt),
                                r["low_message_hi"].format(**fmt_hi), risk=risk, value=days,
                                limit=norm))

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

    # R12, R13: the two record checks that replaced the Odd Overall engine (T053)
    desc = work.get("description") or ""
    type_name = reference.work_type_name(work.get("work_type_code"))
    if (type_top and amount >= SCOPE_MIN_RS and amount >= type_top
            and len(desc.split()) <= SCOPE_MAX_WORDS and not re.search(r"\d", desc)
            and not WORD_NUMBER.search(desc)
            and not undescribed(desc) and not place_words(desc)):
        r = rules()["R12"]
        fmt = {"amount": inr(amount), "text": " ".join(desc.split()), "type": type_name,
               "top": inr(type_top)}
        out.append(_finding("R12", r["severity"], r["message_en"].format(**fmt),
                            r["message_hi"].format(**fmt), value=amount, limit=type_top))
    if (status == "COMPLETED" and rec and done and amount >= FAST_MIN_RS
            and work.get("work_type_code") in CONSTRUCTION_TYPES
            and scope(desc) != GOODS and 0 <= (done - rec).days <= FAST_DAYS
            and not OLD_FY.search(desc)
            and (timeline is None or timeline.distinctiveness(quarter_of(rec)) >= 0.8)):
        r = rules()["R13"]
        fmt = {"amount": inr(amount), "type": type_name, "days": (done - rec).days,
               "rec": rec.isoformat(), "done": done.isoformat()}
        out.append(_finding("R13", r["severity"], r["message_en"].format(**fmt),
                            r["message_hi"].format(**fmt), value=(done - rec).days,
                            limit=FAST_DAYS))
    return out


def not_checked() -> list[str]:
    return [f"{r['id']} {r['title']}: {r['needs']}." for r in rules().values()
            if not r["evaluable"]]


def assess(work: dict, as_of: date, p98: float | None = None, timeline=None,
           type_top: float | None = None) -> AgentResult:
    t0 = time.perf_counter()
    if not work.get("status"):
        return AgentResult(agent=AGENT, status=Status.NOT_ASSESSABLE, verdict="NOT_ASSESSABLE",
                           risk=0.0, confidence=0.0, hard=False, version=VERSION,
                           headline="Cannot be assessed: the record carries no status, so its "
                                    "stage cannot be checked against the guidelines. This is "
                                    "not a clean chit.",
                           duration_ms=int((time.perf_counter() - t0) * 1000))
    findings = evaluate(work, as_of, p98, timeline, type_top)
    names = ", ".join(p["name"] for p in _pauses()["periods"])
    limitations = ["Could not check (the public export does not carry the data): "
                   + " ".join(not_checked()),
                   f"The sanction clock leaves out election pauses ({names}), but not state "
                   "assembly elections."]
    if work.get("status") == "RECOMMENDED" and as_of > calendar_checked_until():
        limitations.append(f"The election calendar was last checked on "
                           f"{calendar_checked_until().isoformat()}; a pause after that date "
                           "is not left out of the sanction clock yet.")
    sc = script(work.get("description"))
    if sc == "other":
        limitations.append("The description is in a script the eligibility reader cannot read "
                           "yet, so R07 (works the guidelines do not allow) was not checked.")
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
        evidence={"rules_broken": broken, "description_script": sc,
                  "rules_checked": [r for r, v in rules().items() if v["evaluable"]
                                    and not (r == "R07" and sc == "other")],
                  "rules_not_checkable": [r for r, v in rules().items() if not v["evaluable"]]},
        duration_ms=int((time.perf_counter() - t0) * 1000))
