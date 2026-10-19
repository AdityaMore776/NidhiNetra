"""Time & Rules: was the work sanctioned on time, and is it being finished in a believable time?

One of the four agents (owner, 3 Oct 2026; plan docs/plans/T120-four-agents.md §8; task T122).
It keeps the measured timing rules of the retired Guideline Compliance engine and adds the comfort
window from the implementing agency's own estimated time to completion.

  SANCTION_OVERDUE           R01: still waiting for sanction past the 75-day clock (election-code
                             days left out), scored by how few works that old still wait (T054)
  SANCTIONED_LATE            sanctioned past the clock. A FACT about the office's pace, never a
                             finding about the work: 60% of the dashboard's works are sanctioned
                             late (data/build_time_bands.py). Risk 0.05; it never queues a work.
  IMPOSSIBLE_TIMELINE        R06: recorded complete before it was recommended (10 of 10 read)
  FINISHED_TOO_FAST          with a form: complete before the window's early line, and no site video
                             shows the work going on in between. A real fast finish is filmed, so
                             good work is never asked about.
  BUILT_IN_DAYS              R13 (no form): a construction of Rs 5 lakh+ complete 0-14 days after
                             recommendation (13 of 13 read)
  BUILT_RIGHT_AFTER_SANCTION R14 (no form): a construction of Rs 3 lakh+ complete within a week of
                             sanction (25 of 25 read); an office that does it routinely is named
                             once and its works score low
  PAST_PROMISED_TIME         with a form: not complete after the window's late line. A follow-up
                             (71-77% of works miss a year); it counts more when the site videos
                             show no change for three visits running.

What the site videos show of a work being built (ALREADY_BUILT_AT_START and the rest) is Site
Progress's to say; this agent only reads whether they show the work going on, so one observation
is never counted twice.
"""

from __future__ import annotations

import time
from datetime import date

from drishti import records, reference
from drishti.agents.compliance import agent as rules_lib
from drishti.agents.contract import AgentResult, Finding, Status
from drishti.agents.office_patterns.index import as_date, is_construction
from drishti.agents.site_progress import visits as site_visits
from drishti.agents.time_rules import window as win

AGENT = "time_rules"
VERSION = "time-rules-1.1.0"
QUESTION = "Was it sanctioned on time, and is it being finished in a believable time?"
CONFIDENCE = 0.9
KEEP_RULES = ("R01", "R06", "R13", "R14")      # the measured timing rules, from rules.json
LATE_FACT_RISK = 0.05
TOO_FAST_RISK = 0.6
OVERDUE_RISK, STALLED_RISK = 0.2, 0.4
STALLED_VISITS = 3

HI = {
    "SANCTIONED_LATE": "अनुशंसा के {days} दिन बाद स्वीकृत (सीमा {limit} दिन)। अधिकांश कार्य देर से "
                       "स्वीकृत होते हैं; यह कार्यालय की गति का तथ्य है, कार्य पर निष्कर्ष नहीं।",
    "FINISHED_TOO_FAST": "कार्य आरंभ के {days} दिन बाद ही पूर्ण दर्ज है, जबकि इस आकार का कार्य "
                         "{early} दिन से पहले नहीं बन सकता, और कोई साइट वीडियो निर्माण होते नहीं "
                         "दिखाता। पूर्णता की जाँच करें।",
    "SANCTIONED_BEFORE_RECOMMENDED": "सांसद की अनुशंसा से {days} दिन पहले स्वीकृत दर्ज: तिथियाँ "
                                     "असंभव क्रम में हैं। अभिलेख की तिथियाँ और स्वीकृति आदेश "
                                     "जाँचें।",
    "PAST_PROMISED_TIME": "एजेंसी द्वारा बताए समय (अनुग्रह अवधि सहित {late} तक) के {days} दिन बाद "
                          "भी पूर्ण नहीं। एजेंसी से प्रगति की जानकारी लें।",
}


def _limit() -> int:
    return int(float(reference.clause("SANCTION_PERIOD")["establishes"]["sanction_period_days"]))


def _share_late(limit: int) -> float | None:
    shares = (win.bands().get("sanction_lag") or {}).get("share_past") or {}
    v = shares.get(str(limit))
    return float(v) if isinstance(v, (int, float)) else None


def _days(n: float) -> str:
    n = round(n)
    return f"{n:,} day{'s' * (n != 1)}"


def _months(days: float) -> str:
    m = days / win.MONTH_DAYS
    n = f"{m:.1f}".removesuffix(".0") if m < 10 else f"{m:.0f}"
    return f"{n} month{'s' * (n != '1')}"


def sanctioned_late(work: dict) -> Finding | None:
    rec, san = as_date(work.get("recommended_date")), as_date(work.get("sanction_date"))
    if not rec or not san or san < rec:
        return None
    limit = _limit()
    off = rules_lib.mcc_days(rec, san)
    lag = (san - rec).days - off
    if lag <= limit:
        return None
    share = _share_late(limit)
    common = (f" {share:.0%} of the works on the eSAKSHI dashboard are sanctioned past the "
              f"{limit}-day limit" if share else " Late sanction is common")
    text = (f"Sanctioned {_days(lag)} after the MP's recommendation ({rec:%d %b %Y} to "
            f"{san:%d %b %Y}{f', {off} election-code days left out' if off else ''}); the "
            f"guidelines give {limit} days.{common}, so this is a fact about the office's pace "
            "and goes on its report card; it is not a finding about the work.")
    return Finding("SANCTIONED_LATE", text, hard=False, risk=LATE_FACT_RISK,
                   evidence={"value": lag, "limit": limit, "mcc_days_excluded": off,
                             "share_late": share,
                             "message_hi": HI["SANCTIONED_LATE"].format(days=lag, limit=limit)})


BEFORE_DAYS = 7               # as R06: a week's slack for dates typed in a hurry


def sanctioned_before_recommended(work: dict) -> Finding | None:
    """T168: sanctioned 7+ days before the MP recommended it, dates in an impossible order. A
    note (risk as SANCTIONED_LATE): how often this is a typing slip and how often backdated
    paperwork is not measured yet (no table with sanction dates on hand), so it never queues."""
    rec, san = as_date(work.get("recommended_date")), as_date(work.get("sanction_date"))
    if not rec or not san or (rec - san).days < BEFORE_DAYS:
        return None
    text = (f"Recorded as sanctioned {_days((rec - san).days)} before the MP recommended it "
            f"({san:%d %b %Y}, recommended {rec:%d %b %Y}): dates in an impossible order. Check "
            "the record's dates and the sanction order.")
    return Finding("SANCTIONED_BEFORE_RECOMMENDED", text, hard=False, risk=LATE_FACT_RISK,
                   evidence={"value": (rec - san).days, "limit": BEFORE_DAYS,
                             "message_hi": HI["SANCTIONED_BEFORE_RECOMMENDED"].format(
                                 days=(rec - san).days)})


def _first_work_seen(vs: list[site_visits.Visit]) -> date | None:
    return next((v.captured for v in vs if v.shows_work and site_visits.genuine(v)), None)


def too_fast(work: dict, w: win.Window, vs: list[site_visits.Visit]) -> Finding | None:
    done = as_date(work.get("completed_date"))
    if (work.get("status") != "COMPLETED" or done is None or w.early is None
            or done >= w.early or not is_construction(work)
            or float(work.get("amount") or 0) < float(win.floors().get("min_amount_rs", 0))):
        return None
    # T168: only a video of the work going on BEFORE the day it is called complete, never the
    # final video: one video filmed on the completion day cleared a road "built" in 6 days
    shown = [v for v in vs if v.shows_work and site_visits.genuine(v) and v.kind != "final"
             and v.captured < done]
    if shown:
        return None        # a real fast finish: the videos show the work going on
    # recorded complete before its own planned start month: count from the sanction instead
    sanctioned = as_date(work.get("sanction_date"))
    start = w.start if done >= w.start or not sanctioned or sanctioned > done else sanctioned
    took = (done - start).days
    type_name = reference.work_type_name(work.get("work_type_code"))
    type_name = type_name[:1].lower() + type_name[1:]       # mid-sentence
    early_days = (w.early - w.start).days
    filmed = ("No site video shows the work going on" if vs else
              "There are no site videos of the work")
    since = "the work could start" if start == w.start else "its sanction"
    text = (f"Recorded complete {_days(max(took, 0))} after {since} "
            f"({start:%d %b %Y} to {done:%d %b %Y}). The agency's own estimate was "
            f"{_months(w.estimate_days)}, and "
            f"a {type_name} work of this size is not finished in under {_days(early_days)} "
            f"(the early line of its comfort window). {filmed}. Check the completion: whether "
            "the work was done, or done before it was sanctioned.")
    return Finding("FINISHED_TOO_FAST", text, hard=False, risk=TOO_FAST_RISK,
                   evidence={"value": took, "limit": early_days, "early": w.early.isoformat(),
                             "videos": len(vs),
                             "message_hi": HI["FINISHED_TOO_FAST"].format(
                                 days=max(took, 0), early=early_days)})


def past_promised(work: dict, w: win.Window, vs: list[site_visits.Visit],
                  as_of: date) -> Finding | None:
    if work.get("status") == "COMPLETED" or as_of <= w.late:
        return None
    over = (as_of - w.late).days
    # T168: the last videos show no change, and at most one of them could not be read: one with
    # no change reading between still ones reset the count (as "can't tell" between two claims
    # not shown did, T135)
    recent = [v for v in vs if v.kind != "baseline"][-STALLED_VISITS:]
    stalled = (len(recent) == STALLED_VISITS
               and not any(v.change == "changed" for v in recent)
               and sum(v.change == "no_change" for v in recent) >= STALLED_VISITS - 1)
    parts = [f"{_months(w.accepted_days)} from {w.start:%d %b %Y}",
             f"{_days(w.grace_days)} of grace"]
    if w.lost_months:
        parts.append(f"{w.lost_months} declared lost month{'s' * (w.lost_months != 1)}")
    if w.extension_days:
        parts.append(f"a recorded extension of {_days(w.extension_days)}")
    text = (f"Not complete {_days(over)} after its own promised time: "
            f"{', '.join(parts)}, so due by {w.late:%d %b %Y}.")
    if stalled:
        text += (f" The last {STALLED_VISITS} site videos show no change at the same views. "
                 "Ask the agency why the work has stopped.")
    else:
        text += " Most works finish late; follow up with the agency on progress."
    return Finding("PAST_PROMISED_TIME", text, hard=False,
                   risk=STALLED_RISK if stalled else OVERDUE_RISK,
                   evidence={"value": over, "late": w.late.isoformat(), "stalled": stalled,
                             "message_hi": HI["PAST_PROMISED_TIME"].format(
                                 days=over, late=f"{w.late:%d-%m-%Y}")})


def assess(work: dict, as_of: date, timeline=None, offices=None) -> AgentResult:
    t0 = time.perf_counter()

    def done(status, headline, findings=(), limitations=(), **evidence) -> AgentResult:
        findings = sorted(findings, key=lambda f: -f.risk)
        top = findings[0] if findings and status == Status.ASSESSED else None
        return AgentResult(agent=AGENT, status=status,
                           verdict=top.code if top else (status.value if status != Status.ASSESSED
                                                         else "ON_TIME_AS_FAR_AS_CHECKED"),
                           risk=top.risk if top else 0.0,
                           confidence=CONFIDENCE if status == Status.ASSESSED else 0.0,
                           hard=False, headline=headline, version=VERSION,
                           findings=list(findings), limitations=list(limitations),
                           evidence=evidence, duration_ms=int((time.perf_counter() - t0) * 1000))

    work = records.work(work)      # dates as dates, the status in capitals, whoever calls it
    if not work.get("status"):
        return done(Status.NOT_ASSESSABLE, "Cannot be assessed: the record carries no status, "
                    "so its dates cannot be checked. This is not a clean chit.")
    form = work.get("cost_form") if isinstance(work.get("cost_form"), dict) else None
    vs = site_visits.of(work)
    part = (form or {}).get("work")
    work_type = part.get("work_type") if isinstance(part, dict) else None
    if not isinstance(work_type, str) or not work_type:
        work_type = work.get("work_type_code")
    w = win.window(form, work_type, as_date(work.get("sanction_date")), _first_work_seen(vs),
                   work.get("time_extension_days") or 0)

    findings: list[Finding] = []
    for f in rules_lib.evaluate(work, as_of, timeline, None, offices):
        rule = f.evidence.get("rule")
        if rule not in KEEP_RULES:
            continue
        if w is not None and rule in ("R13", "R14"):
            continue          # with a form, the comfort window asks the same question better
        findings.append(f)
    for f in (sanctioned_late(work), sanctioned_before_recommended(work)):
        if f:
            findings.append(f)
    limitations = []
    if w is not None:
        for f in (too_fast(work, w, vs), past_promised(work, w, vs, as_of)):
            if f:
                findings.append(f)
    elif form is None:
        limitations.append("No cost estimate form, so there is no promised time: the comfort "
                           "window (too fast, past its own time) was not checked; the record's "
                           "own timing rules were.")
    else:
        limitations.append("The cost estimate form gives no estimated time to completion, or "
                           "there is no sanction date or start month yet, so the comfort window "
                           "was not checked.")
    if work.get("status") == "COMPLETED" and not work.get("sanction_date"):
        limitations.append("The record carries no sanction date, so the time from sanction to "
                           "completion was not checked.")
    if work.get("status") == "COMPLETED" and not as_date(work.get("completed_date")):
        limitations.append("Recorded complete without a completion date, so how fast it was "
                           "finished could not be checked: ask for the date.")
    if w is not None:
        limitations += w.notes     # an estimate or start the window did not take as written
    counted = [f for f in findings if f.risk >= LATE_FACT_RISK * 2]
    if (work.get("status") == "COMPLETED" and not as_date(work.get("completed_date"))
            and not counted):
        # T168: the pace of a finished work cannot be judged without the day it finished:
        # "nothing found" would read as a clean chit
        return done(Status.NOT_ASSESSABLE, "Cannot be assessed: recorded complete without a "
                    "completion date, so how fast it was finished cannot be checked. This is not "
                    "a clean chit: ask for the date.", findings, limitations,
                    window=w.to_json() if w else None, videos=len(vs),
                    rules_checked=list(KEEP_RULES))
    headline = (max(findings, key=lambda f: f.risk).text if findings else
                "No timing problem the dates and the agency's own estimate can show.")
    return done(Status.ASSESSED, headline, findings, limitations,
                window=w.to_json() if w else None, videos=len(vs),
                rules_checked=list(KEEP_RULES))
