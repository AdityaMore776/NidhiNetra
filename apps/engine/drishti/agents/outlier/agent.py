"""Odd Overall engine: is this record unusual taken as a whole? (#63, the blueprint's 0.10 slot)

Three fields within the work type (model.py): amount, how fast it was completed, how much the
description says. An Isolation Forest on their per-type z values, stored as numbers and scored
in plain Python, so any work is scored the same way (T051).

Measured (data/build_outlier.py -> results/outlier_trial.json): at 1.5% of real works flagged,
the forest caught 100% / 75% / 100% of three kinds of planted two-field oddities (amount x5 +
done in 2 days; amount x5 + description cut to one word; both) against 51% / 51% / 100% for a
robust z on the same fields, and only 6% of a single odd field (price alone is the cost
engine's). Read by eye (data/trial/outlier_labels.py): the 30 oddest real works 22/30 worth a
look; 30 random works at the 1.5% cut 3/30. So the engine raises a finding only for the oddest
0.1% (the stored threshold) and is shown, not counted.

  ODD_COMBINATION  the oddest 0.1%: 0.30 rising to 0.70 at the oddest record; the sentence
                   names this work's two most unusual fields against its type's usual range
  NOT_ASSESSABLE   no statistics loaded, or fewer than two of the three fields known
"""

from __future__ import annotations

import time

from drishti import reference
from drishti.agents.contract import AgentResult, Finding, Status
from drishti.agents.outlier.model import OutlierStats

AGENT = "outlier"
VERSION = "outlier-1.0.0"
QUESTION = ("Do the amount, the days taken to finish and the description look wrong together "
            "(e.g. a big amount finished in days with almost no description)?")
CONFIDENCE = 0.5


def _quiet(status: Status, text: str, t0: float) -> AgentResult:
    return AgentResult(agent=AGENT, status=status, verdict=status.value, risk=0.0,
                       confidence=0.0, hard=False, version=VERSION, headline=text,
                       duration_ms=int((time.perf_counter() - t0) * 1000))


def _inr(v: float) -> str:
    return f"Rs {v / 1e7:.2f} crore" if v >= 1e7 else (f"Rs {v / 1e5:.2f} lakh" if v >= 1e5
                                                      else f"Rs {v:,.0f}")


def _describe(f: str, work: dict, lo: float, hi: float) -> str:
    if f == "amount":
        return (f"an amount of {_inr(float(work['amount']))} (most cost {_inr(10 ** lo)} to "
                f"{_inr(10 ** hi)})")
    if f == "speed":
        days = (work["completed_date"] - work["recommended_date"]).days
        return (f"completed {days:,} days after recommendation (most take {10 ** lo - 1:,.0f} "
                f"to {10 ** hi - 1:,.0f} days)")
    n = len((work.get("description") or "").strip())
    return f"a description of {n:,} characters (most have {10 ** lo:,.0f} to {10 ** hi:,.0f})"


def _usual(work: dict, type_name: str) -> str:
    bits = [f"amount {_inr(float(work['amount']))}"] if work.get("amount") else []
    rec, done = work.get("recommended_date"), work.get("completed_date")
    if rec is not None and done is not None and done >= rec:
        bits.append(f"finished {(done - rec).days:,} days after recommendation")
    n = len((work.get("description") or "").strip())
    if n:
        bits.append(f"a description of {n:,} characters")
    return (f"Checked together against other {type_name} works ({', '.join(bits)}): nothing "
            "looks wrong together.")


def assess(work: dict, stats: OutlierStats | None) -> AgentResult:
    t0 = time.perf_counter()
    if stats is None or stats.forest is None:
        return _quiet(Status.NOT_ASSESSABLE, "Cannot be assessed: the statistics of usual "
                      "records are not loaded. This is not a clean chit.", t0)
    z = stats.zscores(work)
    if len(z) < 2:
        return _quiet(Status.NOT_ASSESSABLE, "Cannot be assessed: fewer than two of amount, "
                      "completion time and description are on record. This is not a clean "
                      "chit.", t0)
    score = stats.forest.score(stats.vector(work))
    cut, top_score = stats.forest.threshold, max(stats.forest.threshold + 1e-9, 0.8)
    type_name = reference.work_type_name(work.get("work_type_code"))
    two = sorted(z, key=lambda f: -abs(z[f]))[:2]
    findings = []
    if score >= cut:
        parts = []
        for f in two:
            rng = stats.range_of(work.get("work_type_code"), f)
            if rng:
                parts.append(_describe(f, work, *rng))
        risk = 0.30 + 0.40 * min(1.0, (score - cut) / (top_score - cut))
        findings.append(Finding(
            "ODD_COMBINATION",
            f"Looks wrong together for a {type_name} work: " + " and ".join(parts)
            + ". Records like this are often entered wrongly or after the work was done: "
            "check the dates, the amount and what was built against the files.",
            hard=False, risk=risk, evidence={"score": score, "z": z, "threshold": cut}))
    return AgentResult(
        agent=AGENT, status=Status.ASSESSED,
        verdict="ODD_COMBINATION" if findings else "USUAL_RECORD",
        risk=findings[0].risk if findings else 0.0, confidence=CONFIDENCE, hard=False,
        headline=findings[0].text if findings else
        _usual(work, type_name),
        version=VERSION, findings=findings,
        limitations=["Judges three fields of the record against works of the same type; an "
                     "unusual record often has an ordinary explanation (a list of sites, a "
                     "backfilled old work)."],
        evidence={"score": score, "z": z, "fields": sorted(z)},
        duration_ms=int((time.perf_counter() - t0) * 1000))
