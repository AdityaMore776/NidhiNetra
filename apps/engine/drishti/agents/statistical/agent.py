"""Cost Anomaly engine (stored id `statistical`): is the cost unusual for the same kind of work?

v2 (T020, 30 Sept 2026). v1 compared every work with the median of its work type in its
district and flagged three spreads above it. On the real corpus that produced the owner's
complaint: a library building judged against book orders ("typical Rs 10,000", 1,000x),
2,582 flags of which 179 read exactly 5.0x and 138 exactly 2.0x, and every queued work
at the same score. v2 changes what is compared and how:

  what it buys   peers are the same kind of work: a type is split into GOODS / WORKS
                 where the two differ in price (scope.py, data/build_stats.py)
  can it judge   an undescribed sanction ("Letter as per attached") is NOT_ASSESSABLE;
                 a many-site sanction (whole constituency, "various villages") is a
                 bundle, not a mark-up
  scale          roads with a stated length are judged per metre; counted items
                 ("50 nos street lights") per unit, against single-unit works
  how high       flagged only above twice the TOP of the usual range (p90) of its
                 district peers AND above the top for the state (or country): a round
                 Rs 5 lakh road next to Rs 1 lakh district peers is not a mark-up when
                 Rs 5 lakh is ordinary for the state
  how far        far above every similar work (25x the median) is worded as a scope
                 question ("check what it covers and that its type is right"), not a
                 mark-up: at that distance it is almost always a bigger or different job

The signal (risk) grows with how far above the top of the range the work sits, so
flags no longer all score the same. A peer range is not a schedule of rates: every
finding here is soft, and says "check", never that the amount is wrong.

The outside-constituency ceiling and the overdue check moved to Guideline Compliance
(R08, R02, T011); `as_of` stays in the signature for the engine contract.
"""

from __future__ import annotations

import math
import time
from datetime import date

from drishti import reference
from drishti.agents.contract import AgentResult, Finding, Status
from drishti.agents.statistical.band import Cohort
from drishti.agents.statistical.cohort import StatsStore
from drishti.agents.statistical.scope import read
from drishti.agents.statistical.text import stated_length
from drishti.agents.statistical.unit_rate import road_check

AGENT = "statistical"
VERSION = "statistical-2.1.0"
QUESTION = "Is the project cost unusual for similar works?"

LEVEL_CONFIDENCE = {"type_district": 0.85, "type_state": 0.7, "type": 0.55}

TOP_FACTOR = 2.0          # flag above 2x the top (p90) of the usual range
SCOPE_RATIO = 10.0        # this far above the median it is a scope question
LOW_FACTOR = 3.0          # below a third of the bottom (p10) of the range
BUNDLE_RISK = 0.15
SCOPE_RISK = 0.35
BELOW_RISK = 0.10
UNIT_TOP_FACTOR = 2.0     # per unit, against single-unit works of the type
MODEL_TOP_FACTOR = 2.0    # version B: above twice the learned top (q90) for the description
USE_PEERS = True          # trial switch (cost_trial_v2.py): False = judge by the model alone
# How a type's GOODS peers are named in officer-facing text (scope.py splits them off).
GOODS_LABEL = {"LIBRARY": "library book and equipment purchase",
               "STREET_LIGHT": "street light purchase",
               "ROAD_CC": "road equipment purchase"}


def inr(v: float) -> str:
    if v >= 1e7:
        return f"Rs {v / 1e7:.2f} crore"
    if v >= 1e5:
        return f"Rs {v / 1e5:.2f} lakh"
    return f"Rs {v:,.0f}"


def above_risk(top_ratio: float) -> float:
    """0.35 at twice the top of the range, rising to 0.9 at 16x (log scale)."""
    if top_ratio < TOP_FACTOR:
        return 0.0
    return min(0.9, 0.35 + 0.183 * math.log2(top_ratio / TOP_FACTOR))


def _place(work: dict) -> str:
    return work.get("district_name") or "this district"


def _where(cohort: Cohort, work: dict) -> str:
    return {"type_district": f"in {_place(work)}", "type_state": "in this state",
            "type": "across the scheme"}.get(cohort.level, "")


def _not_assessable(reason: str, t0: float, **extra) -> AgentResult:
    return AgentResult(agent=AGENT, status=Status.NOT_ASSESSABLE, verdict="NOT_ASSESSABLE",
                       risk=0.0, confidence=0.0, hard=False, version=VERSION,
                       headline=f"Cannot be assessed: {reason}. This is not a clean chit.",
                       evidence=extra, duration_ms=int((time.perf_counter() - t0) * 1000))


def _length_m(work: dict) -> float:
    q, unit = work.get("quantity"), (work.get("quantity_unit") or "").lower()
    if q and unit in ("m", "metre", "meter", "metres", "meters", "rmt"):
        return float(q)
    if q and unit == "km":
        return float(q) * 1000.0
    return stated_length(work.get("description"), allow_km=True)


def _expected(work: dict, stats: StatsStore) -> dict | None:
    """Version B's range for what works described like this cost.

    T051: computed for ANY work from the word-price model (price_model.py) when it is
    loaded. A range handed in with the work (`cost_expected`, the planted test) wins, so the
    trial can give out-of-fold ranges; the per-work LightGBM answers stored by the T020
    job are no longer read, because a new work never had one."""
    exp = work.get("cost_expected")
    if not exp and stats.price_model is not None:
        exp = stats.price_model.predict(work)
    if not exp or any(exp.get(k) is None for k in ("q10", "q50", "q90")):
        return None
    return exp


def _range_text(c: Cohort) -> str:
    lo, hi = c.range_inr()
    return f"{inr(lo)} to {inr(hi)}"


def _row(metric: str, amount: float, c: Cohort, unit: str = "Rs") -> dict:
    lo, hi = c.range_inr()
    return {"metric": metric, "unit": unit, "this_work": amount, "typical_low": lo,
            "typical_high": hi, "median": c.median_inr(),
            "deviation_pct": (amount / c.median_inr() - 1.0) * 100.0}


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
    desc = work.get("description")

    findings: list[Finding] = []
    limitations: list[str] = []
    comparison: list[dict] = []
    rd = read(wtype, desc)
    ptype = stats.peer_type(wtype, rd.scope)
    chain = stats.chain(ptype, work.get("district_lgd"), work.get("state_lgd"))
    reading = "total"
    if rd.undescribed:
        reading = "undescribed"
    elif rd.bundle:
        reading = "bundle"
    count = rd.count
    if ptype.endswith("|GOODS"):
        type_name = GOODS_LABEL.get(wtype, f"{type_name} (items bought)")
    elif ptype.endswith("|MAST"):
        type_name = "high mast light"
    model = stats.unit_models.get(wtype)
    length = _length_m(work) if model else math.nan
    if model and not math.isnan(length):
        reading = "per_metre"
    elif count:
        reading = "per_unit"

    # The outside-constituency ceiling and the overdue check moved to Guideline Compliance
    # (R08, R02): carrying them here too counted one fact twice in the risk score.
    if reading == "undescribed":
        return _not_assessable("the description does not say what is built or bought, so "
                               "its cost cannot be compared with anything", t0)
    if not chain:
        return _not_assessable(
            f"fewer than 20 comparable {type_name} works exist to compare against", t0)

    local, broad = chain[0], (chain[1] if len(chain) > 1 else None)
    top_local = amount / local.range_inr()[1]
    comparison.append(_row("Total cost", amount, local))
    peers = f"{local.n:,} similar works {_where(local, work)}"
    verdict = "COST_TYPICAL"

    if reading == "per_metre":
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
            verdict = "UNIT_RATE_ABOVE"
            findings.append(Finding(
                "UNIT_RATE_ABOVE",
                f"{inr(rc['per_metre'])} per metre for {length:,.0f} m, against a usual "
                f"{inr(rc['predicted'] / length)} per metre for roads of this length and "
                f"published rates of Rs {model.anchor_low:,.0f}-{model.anchor_high:,.0f} "
                f"per metre. Check the length and the specification.",
                hard=False, risk=above_risk(amount / rc["predicted"] / (10 ** model.resid_sd)),
                evidence={**rc, "reading": reading}))
        limitations.append(f"Judged per metre for {length:,.0f} m; the total is not compared "
                           "with roads of other lengths.")
    elif reading == "per_unit":
        single = (stats.chain(ptype, None, work.get("state_lgd")) or chain)[0]
        per_unit = amount / count
        unit_top = per_unit / single.range_inr()[1]
        comparison.append(_row("Cost per unit", per_unit, single, unit="Rs/unit"))
        if unit_top >= UNIT_TOP_FACTOR and per_unit >= 3 * single.median_inr():
            verdict = "UNIT_PRICE_ABOVE"
            findings.append(Finding(
                "UNIT_PRICE_ABOVE",
                f"{inr(per_unit)} per unit for the {count} units the description names; a "
                f"single-unit {type_name} work usually costs {_range_text(single)} "
                f"{_where(single, work)}. Check the specification and the count.",
                hard=False, risk=above_risk(unit_top),
                evidence={"count": count, "per_unit": per_unit, "top_ratio": unit_top,
                          "reading": reading}))
        limitations.append(f"Priced per unit for the {count} units named in the description.")
    elif reading == "bundle":
        if top_local >= TOP_FACTOR:
            verdict = "BUNDLED_SANCTION"
            findings.append(Finding(
                "BUNDLED_SANCTION",
                f"{inr(amount)} for what the description says covers several sites or "
                f"units; one {type_name} work usually costs {_range_text(local)} "
                f"{_where(local, work)}. The cost per site cannot be judged until the list "
                f"of sites is checked.",
                hard=False, risk=BUNDLE_RISK,
                evidence={"top_ratio": top_local, "reading": reading}))
        limitations.append("The description covers several sites or units, so the total is "
                           "not read as a price.")
    else:
        broad_ok = broad is None or amount > broad.range_inr()[1]
        ratio_med = amount / local.median_inr()
        exp = _expected(work, stats)
        if exp is None:
            limitations.append("The description-based price check is not loaded, so the cost "
                               "was compared with similar works only.")
        model_top = None
        if exp is not None:
            lo_b, mid_b, hi_b = (10 ** exp["q10"], 10 ** exp["q50"], 10 ** exp["q90"])
            model_top = amount / hi_b
            comparison.append({"metric": "Expected for this description", "unit": "Rs",
                               "this_work": amount, "typical_low": lo_b, "typical_high": hi_b,
                               "median": mid_b, "deviation_pct": (amount / mid_b - 1.0) * 100})
            # the peers and the description-based range must agree before anything is said
            broad_ok = broad_ok and model_top >= MODEL_TOP_FACTOR
        if not USE_PEERS and model_top is not None:      # trial switch: model alone
            top_local, broad_ok = model_top * TOP_FACTOR / MODEL_TOP_FACTOR, True
        if top_local >= TOP_FACTOR and broad_ok and ratio_med >= SCOPE_RATIO:
            verdict = "SCOPE_FAR_LARGER"
            findings.append(Finding(
                "SCOPE_FAR_LARGER",
                f"{inr(amount)} is far above any usual {type_name} work {_where(local, work)} "
                f"(most cost {_range_text(local)}; {peers}). A work this large is more often "
                f"a bigger or different kind of project than a price problem: check what it "
                f"covers and that its type is right.",
                hard=False, risk=SCOPE_RISK,
                evidence={"top_ratio": top_local, "median_ratio": ratio_med,
                          "reading": reading}))
        elif top_local >= TOP_FACTOR and broad_ok:
            verdict = "COST_ABOVE_PEERS"
            wider = "" if broad is None else (
                f", and above the usual top for {_where(broad, work).replace('in ', '')} "
                f"({inr(broad.range_inr()[1])})")
            learned = "" if model_top is None else (
                f" Works described like this one usually cost up to {inr(amount / model_top)}.")
            findings.append(Finding(
                "COST_ABOVE_PEERS",
                f"{inr(amount)}: similar {type_name} works {_where(local, work)} usually cost "
                f"{_range_text(local)} ({peers}). This is {top_local:.1f} times the top of "
                f"that range{wider}.{learned} Check the estimate and what it includes.",
                hard=False, risk=above_risk(min(top_local, model_top or top_local) if
                                            model_top else top_local),
                evidence={"top_ratio": top_local, "median_ratio": ratio_med,
                          "model_top_ratio": model_top, "reading": reading}))
        elif amount * LOW_FACTOR < local.range_inr()[0] and (
                broad is None or amount < broad.range_inr()[0]):
            verdict = "COST_BELOW_PEERS"
            findings.append(Finding(
                "COST_BELOW_PEERS",
                f"{inr(amount)} is well below similar works {_where(local, work)} "
                f"(usually {_range_text(local)}); under-costed works are often revised "
                f"upward later.",
                hard=False, risk=BELOW_RISK, evidence={"reading": reading}))

    if local.level != "type_district":
        limitations.append(f"Fewer than 20 such works in {_place(work)}, so the comparison "
                           f"uses works {_where(local, work)}.")
    limitations.append("A peer range is not a schedule of rates: an unusual amount can have an "
                       "ordinary explanation (terrain, specification, scope).")
    return _result(findings, limitations, comparison, local, type_name, work, t0, verdict,
                   LEVEL_CONFIDENCE[local.level], peers=peers, reading=reading, ptype=ptype)


def _result(findings, limitations, comparison, cohort, type_name, work, t0, verdict,
            confidence, peers=None, reading=None, ptype=None) -> AgentResult:
    top = max(findings, key=lambda f: f.risk, default=None)
    if top is not None:
        headline = top.text
    elif cohort is not None:
        headline = (f"Cost is within the usual range for similar {type_name} works "
                    f"{_where(cohort, work)} ({peers}).")
    else:
        headline = "Cost not compared."
    evidence = {"comparison": comparison, "work_type_name": type_name, "reading": reading,
                "peer_type": ptype}
    if cohort is not None:
        evidence["cohort"] = {"level": cohort.level, "description": cohort.description,
                              "n": cohort.n, "p10": cohort.p10, "p50": cohort.p50,
                              "p90": cohort.p90, "sd": cohort.sd}
    return AgentResult(
        agent=AGENT, status=Status.ASSESSED,
        verdict=top.code if top else verdict,
        risk=top.risk if top else 0.0,
        confidence=confidence,
        hard=any(f.hard for f in findings),
        headline=headline, version=VERSION, findings=findings, limitations=limitations,
        evidence=evidence, duration_ms=int((time.perf_counter() - t0) * 1000))
