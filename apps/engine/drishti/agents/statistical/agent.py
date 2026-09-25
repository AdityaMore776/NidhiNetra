"""Agent 04 - Statistical: is the project cost unusual for similar works?

Facets (design section 5, agent 04):
  cost vs peers       log-cost band per type x district, backing off to state and
                      country; soft, capped at 0.45 (AD-107)
  bundle reading      a count or a list in the description explains an outlier
  price per metre     ROAD_CC works with a stated length, vs the fitted curve and
                      published rural CC road rates
  ceiling             outside-constituency works over Rs 25 lakh (para 2.9) - the
                      only hard signal, because it is arithmetic against a clause
  delay               open works past their type's 98th-percentile duration
  money vs site       needs a verified progress reading from agent 01; until that
                      agent exists it is stated as a limitation, not skipped quietly
"""

from __future__ import annotations

import math
import time
from datetime import date

from drishti import reference
from drishti.agents.contract import AgentResult, Finding, Status
from drishti.agents.statistical.band import cost_risk, cost_verdict, zscore
from drishti.agents.statistical.cohort import StatsStore
from drishti.agents.statistical.text import reads_as_bundle, stated_length
from drishti.agents.statistical.timeline import delay_check
from drishti.agents.statistical.unit_rate import road_check

AGENT = "statistical"
VERSION = "statistical-1.0.0"
QUESTION = "Is the project cost unusual for similar works?"

OUTSIDE_CEILING_INR = 2_500_000.0      # para 2.9, verified clause OUTSIDE_CONSTITUENCY_CEILING
CEILING_RISK = 0.70
LEVEL_CONFIDENCE = {"type_district": 0.85, "type_state": 0.7, "type": 0.55}
COUNTABLE_CONFIDENCE = 0.6


def inr(v: float) -> str:
    if v >= 1e7:
        return f"Rs {v / 1e7:.2f} crore"
    if v >= 1e5:
        return f"Rs {v / 1e5:.2f} lakh"
    return f"Rs {v:,.0f}"


def _place(work: dict) -> str:
    return work.get("district_name") or "this district"


def _not_assessable(reason: str, t0: float) -> AgentResult:
    return AgentResult(agent=AGENT, status=Status.NOT_ASSESSABLE, verdict="NOT_ASSESSABLE",
                       risk=0.0, confidence=0.0, hard=False, version=VERSION,
                       headline=f"Cannot be assessed: {reason}. This is not a clean chit.",
                       duration_ms=int((time.perf_counter() - t0) * 1000))


def _length_m(work: dict) -> float:
    q, unit = work.get("quantity"), (work.get("quantity_unit") or "").lower()
    if q and unit in ("m", "metre", "meter", "metres", "meters", "rmt"):
        return float(q)
    if q and unit == "km":
        return float(q) * 1000.0
    return stated_length(work.get("description"), allow_km=True)


def assess(work: dict, stats: StatsStore, as_of: date) -> AgentResult:
    t0 = time.perf_counter()
    amount = work.get("amount")
    wtype = work.get("work_type_code")
    type_name = reference.work_type_name(wtype)
    if not amount or float(amount) <= 0:
        return _not_assessable("the record carries no amount", t0)
    amount = float(amount)
    if not wtype:
        return _not_assessable("the record carries no work type", t0)
    cohort = stats.cohort(wtype, work.get("district_lgd"), work.get("state_lgd"))
    if cohort is None:
        return _not_assessable(
            f"fewer than 20 comparable {type_name} works exist to compare against", t0)

    findings: list[Finding] = []
    limitations: list[str] = []

    # -- cost vs peers
    z = zscore(amount, cohort)
    bundle = reads_as_bundle(work.get("description"))
    verdict = cost_verdict(z, bundle)
    risk = cost_risk(z, verdict)
    ratio = amount / cohort.median_inr()
    lo, hi = cohort.range_inr()
    comparison = [{
        "metric": "Total cost", "unit": "Rs", "this_work": amount, "typical_low": lo,
        "typical_high": hi, "median": cohort.median_inr(),
        "deviation_pct": (ratio - 1.0) * 100.0,
    }]
    compared = f"compared with {cohort.n:,} {cohort.description}"
    countable = reference.is_countable(wtype)
    if verdict == "COST_ABOVE_PEERS":
        text = (f"Costs {ratio:.1f}x the typical amount for {type_name} works in "
                f"{_place(work)} ({compared}).")
        if countable:
            text += (" For items counted in units, this can also mean many units filed "
                     "as one work; the description does not say how many.")
        findings.append(Finding("COST_ABOVE_PEERS", text, hard=False, risk=risk,
                                evidence={"z": z, "ratio": ratio}))
    elif verdict == "COST_BELOW_PEERS":
        text = (f"Costs {ratio:.2f}x the typical amount, well below similar works; "
                f"under-costed works are often revised upward later ({compared}).")
        findings.append(Finding("COST_BELOW_PEERS", text, hard=False, risk=risk,
                                evidence={"z": z, "ratio": ratio}))
    elif verdict == "BUNDLED_SANCTION":
        text = (f"The amount is {ratio:.1f}x the typical {type_name} work, and the "
                "description lists many units: most likely several works filed as one, "
                "each of which escaped separate scrutiny.")
        findings.append(Finding("BUNDLED_SANCTION", text, hard=False, risk=risk,
                                evidence={"z": z, "ratio": ratio}))

    # -- price per metre (roads with a known length)
    model = stats.unit_models.get(wtype)
    length = _length_m(work) if model else math.nan
    if model and not math.isnan(length):
        rc = road_check(amount, length, model)
        spread = 2 * model.resid_sd
        comparison.append({
            "metric": "Cost per metre", "unit": "Rs/m", "this_work": rc["per_metre"],
            "typical_low": 10 ** (math.log10(rc["predicted"]) - spread) / length,
            "typical_high": 10 ** (math.log10(rc["predicted"]) + spread) / length,
            "median": rc["predicted"] / length,
            "deviation_pct": (amount / rc["predicted"] - 1.0) * 100.0,
            "anchor_low": model.anchor_low, "anchor_high": model.anchor_high,
        })
        if rc["verdict"] == "UNIT_RATE_ABOVE":
            findings.append(Finding(
                "UNIT_RATE_ABOVE",
                f"{inr(rc['per_metre'])} per metre for {length:,.0f} m, against a fitted "
                f"{inr(rc['predicted'] / length)} per metre and published rates of "
                f"Rs {model.anchor_low:,.0f}-{model.anchor_high:,.0f} per metre.",
                hard=False, risk=cost_risk(rc["z"], "COST_ABOVE_PEERS"), evidence=rc))

    # -- ceiling (hard, cited)
    if work.get("is_outside_constituency") and amount > OUTSIDE_CEILING_INR:
        findings.append(Finding(
            "CEILING_BREACH",
            f"A work outside the constituency is capped at Rs 25 lakh "
            f"({reference.citation('OUTSIDE_CONSTITUENCY_CEILING')}); this one is "
            f"{inr(amount)}.",
            hard=True, risk=CEILING_RISK, evidence={"ceiling": OUTSIDE_CEILING_INR}))

    # -- delay
    dc = delay_check(work.get("status"), work.get("recommended_date"), as_of,
                     stats.p98(wtype))
    if dc and dc["verdict"] == "DELAYED":
        findings.append(Finding(
            "DELAYED",
            f"Still open {dc['days']:,} days after recommendation; 98% of completed "
            f"{type_name} works finished within {dc['norm_days']:,.0f} days.",
            hard=False, risk=dc["risk"], evidence=dc))

    limitations.append(
        "Money released against verified site progress is checked once the Site Progress "
        "agent is built; the published export carries no payment dates.")
    if cohort.level != "type_district":
        limitations.append(f"Fewer than 20 such works in {_place(work)}, so the comparison "
                           f"uses {cohort.description}.")
    limitations.append("A peer median is not a schedule of rates: an unusual amount can "
                       "have an ordinary explanation (terrain, specification, scope).")

    confidence = LEVEL_CONFIDENCE[cohort.level]
    if countable and verdict == "COST_ABOVE_PEERS":
        # The unit count is missing, so the outlier is ambiguous between a mispriced
        # item and a bulk order; it is read with less confidence, not suppressed.
        confidence = min(confidence, COUNTABLE_CONFIDENCE)

    top = max(findings, key=lambda f: f.risk, default=None)
    if top is None:
        headline = (f"Cost is within the usual range for {type_name} works in "
                    f"{_place(work)} ({compared}).")
    else:
        headline = top.text
    return AgentResult(
        agent=AGENT, status=Status.ASSESSED,
        verdict=top.code if top else verdict,
        risk=top.risk if top else 0.0,
        confidence=confidence,
        hard=any(f.hard for f in findings),
        headline=headline, version=VERSION, findings=findings, limitations=limitations,
        evidence={"comparison": comparison,
                  "cohort": {"level": cohort.level, "description": cohort.description,
                             "n": cohort.n, "p10": cohort.p10, "p50": cohort.p50,
                             "p90": cohort.p90, "sd": cohort.sd, "z": z},
                  "work_type_name": type_name},
        duration_ms=int((time.perf_counter() - t0) * 1000))
