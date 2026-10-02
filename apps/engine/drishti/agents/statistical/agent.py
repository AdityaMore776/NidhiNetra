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
  how far        far above every similar work (10x the median) is a bigger or different
                 job, said and not flagged

T053 (1 Oct 2026), the owner: "it always flags the money as high even on low-risk works".
The card coloured anything above the usual top red although the engine asks nothing there,
and three kinds of flag were almost never a real price question when read by eye:
"several sites in one amount" 0/48, "far above every similar work" 3/18, "per unit above"
0/3; "well below similar works" was never shown to matter. Those four are now plain
statements with no risk. What is left:

  COST_ABOVE_PEERS  above the COMFORT LIMIT: the highest of twice the district's usual top,
                    the state's (or country's) top, and twice the top for works described
                    like this. Up to it is the comfort zone: room for a bigger scope or a
                    contingency margin, never questioned. 54/128 read as real price questions.
  UNIT_RATE_ABOVE   a road's cost per metre far above the length curve and published rates.
  2 Oct 2026: "far bigger than every similar work" stays a statement EXCEPT when the description
  names a single unit of the type's own kind ("one high mast light", scope.single_unit): one unit
  cannot be a bigger project, so it is asked as COST_ABOVE_PEERS (owner question 2, T080).

Every result carries `comfort_high` (per comparison row and overall), so the card shows
the usual range, the comfort zone and only beyond it a question. The signal grows with how
far above the range the work sits. A peer range is not a schedule of rates: every finding
says "check", never that the amount is wrong.

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
from drishti.agents.statistical.scope import read, single_unit
from drishti.agents.statistical.text import stated_length
from drishti.agents.statistical.unit_rate import Z_FLAG, road_check

AGENT = "statistical"
VERSION = "statistical-2.3.0"
QUESTION = "Is the project cost unusual for similar works?"

LEVEL_CONFIDENCE = {"type_district": 0.85, "type_state": 0.7, "type": 0.55}

TOP_FACTOR = 2.0          # flag above 2x the top (p90) of the usual range
SCOPE_RATIO = 10.0        # this far above the median it is a bigger project, not a price
Z_ROAD = Z_FLAG           # the per-metre flag line, in residual spreads above the curve
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
    total_row = _row("Total cost", amount, local)
    comparison.append(total_row)
    peers = f"{local.n:,} similar works {_where(local, work)}"
    verdict = "COST_TYPICAL"
    comfort = None

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
            # the per-metre flag line (z >= 3 against the road-length curve)
            "comfort_high": 10 ** (math.log10(rc["predicted"])
                                   + Z_ROAD * model.resid_sd) / length,
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
        # T053: a per-unit price flag read 0/3 as a real price question (a count misread, a
        # different unit); the per-unit cost is shown, never flagged
        single = (stats.chain(ptype, None, work.get("state_lgd")) or chain)[0]
        per_unit = amount / count
        comparison.append(_row("Cost per unit", per_unit, single, unit="Rs/unit"))
        verdict = "PRICED_PER_UNIT"
        limitations.append(f"Priced per unit for the {count} units named in the description; "
                           "the total is not compared with single-unit works.")
    elif reading == "bundle":
        # T053: "several sites in one amount" read 0/48 as a real price question; it is a
        # statement of what was not judged, never a flag
        verdict = "SEVERAL_SITES_NOT_PRICED"
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
                               "median": mid_b, "deviation_pct": (amount / mid_b - 1.0) * 100,
                               "comfort_high": MODEL_TOP_FACTOR * hi_b})
            # the peers and the description-based range must agree before anything is said
            broad_ok = broad_ok and model_top >= MODEL_TOP_FACTOR
        # The comfort zone: everything up to the line where a question is asked. Twice the
        # top of the district's usual range, the state's (or country's) own top, and twice the
        # top for works described like this, whichever is highest: room for a bigger scope or
        # a contingency margin without a question.
        comfort = max([TOP_FACTOR * local.range_inr()[1]]
                      + ([broad.range_inr()[1]] if broad is not None else [])
                      + ([MODEL_TOP_FACTOR * hi_b] if exp is not None else []))
        total_row["comfort_high"] = comfort
        if not USE_PEERS and model_top is not None:      # trial switch: model alone
            top_local, broad_ok = model_top * TOP_FACTOR / MODEL_TOP_FACTOR, True
        one = single_unit(wtype, desc)
        if top_local >= TOP_FACTOR and broad_ok and ratio_med >= SCOPE_RATIO and not one:
            # T053: "far above every similar work" read 3/18 as a real price question: it is
            # almost always a bigger or different project. Said, never flagged.
            verdict = "BIGGER_PROJECT_THAN_PEERS"
            limitations.append(
                f"{inr(amount)} is far above every usual {type_name} work "
                f"{_where(local, work)}; at that distance it is almost always a bigger or "
                "different project, so it is not treated as a price question.")
        elif top_local >= TOP_FACTOR and broad_ok:
            verdict = "COST_ABOVE_PEERS"
            wider = "" if broad is None else (
                f", and above the usual top for {_where(broad, work).replace('in ', '')} "
                f"({inr(broad.range_inr()[1])})")
            learned = "" if model_top is None else (
                f" Works described like this one usually cost up to {inr(amount / model_top)}.")
            if one and ratio_med >= SCOPE_RATIO:
                learned += (" The description names a single unit, so a bigger project does not "
                            "explain the amount.")
            findings.append(Finding(
                "COST_ABOVE_PEERS",
                f"{inr(amount)}: similar {type_name} works {_where(local, work)} usually cost "
                f"{_range_text(local)} ({peers}). This is {top_local:.1f} times the top of "
                f"that range{wider}, and {amount / comfort:.1f} times the comfort limit of "
                f"{inr(comfort)}.{learned} Check the estimate and what it includes.",
                hard=False, risk=above_risk(min(top_local, model_top or top_local) if
                                            model_top else top_local),
                evidence={"top_ratio": top_local, "median_ratio": ratio_med,
                          "model_top_ratio": model_top, "comfort_high": comfort,
                          "reading": reading, "single_unit": one}))
        # T053: "well below similar works" was never shown to be a real problem; removed

    if local.level != "type_district":
        limitations.append(f"Fewer than 20 such works in {_place(work)}, so the comparison "
                           f"uses works {_where(local, work)}.")
    limitations.append("A peer range is not a schedule of rates: an unusual amount can have an "
                       "ordinary explanation (terrain, specification, scope).")
    return _result(findings, limitations, comparison, local, type_name, work, t0, verdict,
                   LEVEL_CONFIDENCE[local.level], peers=peers, reading=reading, ptype=ptype,
                   comfort=comfort)


def _headline(verdict: str, work: dict, cohort: Cohort, type_name: str, peers: str,
              comfort: float | None) -> str:
    amount = float(work["amount"])
    where = _where(cohort, work)
    if verdict == "SEVERAL_SITES_NOT_PRICED":
        return (f"{inr(amount)} covers several sites or units, so it is not compared as one "
                f"price; one {type_name} work usually costs {_range_text(cohort)} {where}.")
    if verdict == "PRICED_PER_UNIT":
        return "Priced per unit for the units the description names; nothing to question."
    if verdict == "BIGGER_PROJECT_THAN_PEERS":
        return (f"{inr(amount)} is far bigger than usual {type_name} works {where} (most cost "
                f"{_range_text(cohort)}): a bigger project, not treated as a price question.")
    if comfort is None:
        return f"Cost is within the usual range for similar {type_name} works {where}."
    lo, hi = cohort.range_inr()
    zone = ("inside the usual range" if amount <= hi else "above the usual range but inside "
            "the comfort zone")
    return (f"{inr(amount)} is {zone} for similar {type_name} works {where} (most cost "
            f"{inr(lo)} to {inr(hi)}; {peers}). DRISHTI asks only above {inr(comfort)}, which "
            "leaves room for a bigger scope or a contingency margin.")


def _result(findings, limitations, comparison, cohort, type_name, work, t0, verdict,
            confidence, peers=None, reading=None, ptype=None, comfort=None) -> AgentResult:
    top = max(findings, key=lambda f: f.risk, default=None)
    if top is not None:
        headline = top.text
    elif cohort is not None:
        headline = _headline(verdict, work, cohort, type_name, peers or "", comfort)
    else:
        headline = "Cost not compared."
    evidence = {"comparison": comparison, "work_type_name": type_name, "reading": reading,
                "peer_type": ptype, "comfort_high": comfort}
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
