"""Cost Estimate engine (Cost v3, T097): is the agency's estimate right for this size of work here?

It reads the implementing agency's cost estimate form (work["cost_form"], docs/specs/
2026-10-03-cost-estimate-form.md) and asks a question only when it is certain the estimate is too
much for what is being built. Plan: docs/plans/T097-cost-agent-v3.md.

  MATERIAL_QUANTITY_ABOVE_SIZE   a material the agency CONFIRMED (not merely suggested) is given
                                 in a quantity more than 25% above what the size needs: more
                                 batteries than solar lights, paver blocks for twice the path's
                                 area, cement beyond the slab's volume (cost_form/norms.py). The
                                 form already asked the agency to confirm it, so it is no typo.
  ESTIMATE_ABOVE_STANDARD_AND_MP the price per unit of size is more than 25% above the 98th
                                 percentile of the same standard item in the district (or state),
                                 AND the estimate is more than 10% above the MP's amount. Two
                                 signals, because real works do not record wattage or height: a
                                 bigger item could explain a high price alone, and an MP's low
                                 guess could explain a gap alone.

Notes, never findings: above the standard item but not above the MP's amount; above the MP's
amount but in line with the standard; below the standard (may run short of money); what could
not be compared and why.

A reference group is compared only when (reference.py): it has 30+ real works, its own spread is
tight (it captures the size), and its unit is the form's full pricing size (a road priced per m2
is never compared with roads per metre: the records hold no width).

  NOT_APPLICABLE  no form for this work (the works before the form: Cost Anomaly applies)
  NOT_ASSESSABLE  the form is not complete, or nothing on it could be compared
"""

from __future__ import annotations

import time

from drishti.agents.contract import AgentResult, Finding, Status
from drishti.agents.cost_estimate import reference
from drishti.cost_form import catalog, norms
from drishti.cost_form.validate import validate

AGENT = "cost_estimate"
VERSION = "cost-estimate-0.1.0"
QUESTION = "Is the agency's cost estimate right for this size of work here?"
QUANTITY_MARGIN = 1.25      # a confirmed quantity this far above what the size needs
PRICE_MARGIN = 1.25         # price per unit this far above the standard item's 98th percentile
MP_MARGIN = 0.10            # the estimate this far above the MP's amount (the form's own rule)
QUANTITY_RISK = 0.6
PRICE_RISK = 0.5
CONFIDENCE = 0.6
FORM_UNIT = {"STREET_LIGHT|solar": "nos", "STREET_LIGHT|grid": "nos", "HIGH_MAST": "nos"}
REF_UNIT_SIZE = {"per light": "nos", "per mast": "nos", "per unit": "nos", "per metre": "m"}
# the specification a higher price could come from, in words
SPEC_WORDS = {"led_w": "LED {:g} W", "battery_wh": "battery {:g} Wh", "panel_wp": "panel {:g} Wp",
              "pole_height_m": "pole {:g} m", "mast_height_m": "mast {:g} m",
              "lamps_per_mast": "{:g} lamps", "lamp_w": "lamps of {:g} W"}


def _rs(v: float) -> str:
    return f"Rs {v / 1e5:,.2f} lakh" if v >= 1e5 else f"Rs {v:,.0f}"


def _result(status: Status, headline: str, t0: float, verdict: str | None = None,
            findings: list[Finding] | None = None, limitations: list[str] | None = None,
            **evidence) -> AgentResult:
    findings = findings or []
    risk = max((f.risk for f in findings), default=0.0)
    return AgentResult(agent=AGENT, status=status, verdict=verdict or status.value, risk=risk,
                       confidence=CONFIDENCE if findings else 0.0, hard=False,
                       headline=headline, version=VERSION, findings=findings,
                       limitations=limitations or [], evidence=evidence,
                       duration_ms=int((time.perf_counter() - t0) * 1000))


def _confirmed(lines: list) -> list[tuple[int, str | None, object, object]]:
    """Only materials the agency chose themselves ("Recognised as" confirmed)."""
    out = []
    for j, ln in enumerate(lines):
        if isinstance(ln, dict):
            mid = ln.get("material_id")
            mid = mid if isinstance(mid, str) and mid not in ("", "none") else None
            out.append((j, mid, ln.get("quantity"), ln.get("unit")))
    return out


def assess(work: dict, ctx) -> AgentResult:
    t0 = time.perf_counter()
    form = work.get("cost_form")
    if not isinstance(form, dict) or not form:
        return _result(Status.NOT_APPLICABLE, "No cost estimate form for this work: it came in "
                       "before the form, so Cost Anomaly checks its amount.", t0)
    as_of = getattr(ctx, "as_of", None)
    checked = validate(form, today=as_of) if as_of else validate(form)
    if not checked["ready"]:
        fixes = sum(1 for i in checked["issues"] if i["level"] == "fix")
        return _result(Status.NOT_ASSESSABLE, f"Cannot be assessed: the cost estimate form is not "
                       f"complete ({fixes} fields to fix, or a check not yet confirmed). This "
                       "is not a clean chit.", t0)

    c = checked["computed"]
    work_type = (form.get("work") or {}).get("work_type")
    grand, lines_total = c["grand_total"], c["lines_total"]
    rec = form.get("recommendation") or {}
    mp = rec.get("mp_amount") if isinstance(rec.get("mp_amount"), (int, float)) else None
    above_mp = c["mp_gap"] is not None and c["mp_gap"] > MP_MARGIN
    reason = (form.get("totals") or {}).get("reason_differs_from_mp")
    data = getattr(ctx, "data", None) or {}
    ref = data.get(AGENT) or reference.load(work.get("state_name"))
    district = work.get("district_name")

    findings: list[Finding] = []
    notes: list[str] = []
    limits: list[str] = []
    sites_ev = []
    compared = False
    for i, site in enumerate(form.get("sites") or []):
        site = site if isinstance(site, dict) else {}
        size = site.get("size") if isinstance(site.get("size"), dict) else {}
        lines = site.get("lines") if isinstance(site.get("lines"), list) else []
        label = f"site {i + 1}" if len(form.get("sites") or []) > 1 else "the work"

        # 1. quantities against what the size needs (confirmed materials only)
        for q in norms.check(work_type, size, _confirmed(lines)):
            compared = True
            if q["ratio"] > QUANTITY_MARGIN:
                name = catalog.material(q["material"])["label"].lower()
                findings.append(Finding(
                    "MATERIAL_QUANTITY_ABOVE_SIZE",
                    f"{label.capitalize()}: {name}, {q['quantity']:,.0f} {q['unit']} in the "
                    f"estimate, but the size needs {q['needed']:,.0f} ({q['why']}); the agency "
                    f"confirmed the quantity when filling the form. Please check the estimate.",
                    hard=False, risk=QUANTITY_RISK,
                    evidence={"site": i, **{k: q[k] for k in ("material", "quantity", "needed",
                                                              "unit", "why")},
                              "ratio": round(q["ratio"], 3), "lines": q["lines"]}))

        # 2. price per unit of size against the standard item here
        site_total = c["sites"][i]["lines_total"] if i < len(c["sites"]) else 0.0
        all_in = grand * site_total / lines_total if lines_total > 0 else 0.0
        key = reference.form_key(work_type, size)
        ev = {"site": i, "key": key[0] if key else None, "all_in": round(all_in, 2)}
        sites_ev.append(ev)
        if not key or not key[1]:
            limits.append(f"Price of {label}: no reference for this kind of work yet.")
            continue
        units = size.get(key[1])
        if not isinstance(units, (int, float)) or isinstance(units, bool) or units <= 0:
            limits.append(f"Price of {label}: its size is missing.")
            continue
        st, where, why = reference.group(ref, key[0], district)
        if st and REF_UNIT_SIZE.get(st["unit"]) != FORM_UNIT.get(key[0]):
            st, why = None, ("the real works record it per "
                             f"{reference.UNIT_TEXT.get(st['unit'], 'unit')}, but its price "
                             "depends on its area (the records hold no width)")
        if not st:
            limits.append(f"Price of {label}: could not check, because {why}.")
            continue
        compared = True
        price = all_in / units
        unit = reference.UNIT_TEXT.get(st["unit"], "unit")
        line = st["p98"] * PRICE_MARGIN
        ev.update(price_per_unit=round(price, 2), unit=unit, units=units, where=where,
                  reference={k: st[k] for k in ("n", "p10", "median", "p90", "p98")},
                  question_above=round(line, 2))
        standard = (f"98 in 100 of the {st['n']} similar works in {where} cost at most "
                    f"{_rs(st['p98'])} per {unit} (median {_rs(st['median'])})")
        if price > line and above_mp:
            spec = ", ".join(SPEC_WORDS[k].format(v) for k, v in size.items()
                             if k in SPEC_WORDS and isinstance(v, (int, float))
                             and not isinstance(v, bool))
            findings.append(Finding(
                "ESTIMATE_ABOVE_STANDARD_AND_MP",
                f"{label.capitalize()}: {_rs(price)} per {unit} ({units:g} of them, "
                f"{_rs(all_in)} with charges); {standard}. The estimate ({_rs(grand)}) is also "
                f"{c['mp_gap']:.0%} above the MP's recommended {_rs(mp)}"
                f"{f' (reason given: {reason!r})' if reason else ''}. Please check the estimate"
                f"{f' and whether its specification ({spec}) explains the price' if spec else ''}.",
                hard=False, risk=PRICE_RISK,
                evidence={"site": i, "price_per_unit": round(price, 2), "unit": unit,
                          "where": where, "p98": st["p98"], "median": st["median"],
                          "n": st["n"], "mp_amount": mp, "mp_gap": c["mp_gap"]}))
        elif price > line:
            notes.append(f"{label.capitalize()}: {_rs(price)} per {unit} is above the usual "
                         f"item ({standard}), but the MP's amount was as high, so it is not "
                         "raised as a question.")
        elif price < st["p10"]:
            notes.append(f"{label.capitalize()}: {_rs(price)} per {unit} is below 9 in 10 "
                         f"similar works in {where}: check nothing is left out, or the money "
                         "may run short.")
        else:
            notes.append(f"{label.capitalize()}: {_rs(price)} per {unit} is in line with "
                         f"similar works in {where} ({standard}).")

    if above_mp and not any(f.code == "ESTIMATE_ABOVE_STANDARD_AND_MP" for f in findings):
        notes.append(f"The estimate ({_rs(grand)}) is {c['mp_gap']:.0%} above the MP's "
                     f"recommended {_rs(mp)}"
                     f"{f' (reason given: {reason!r})' if reason else ''}; on its own that is "
                     "not a question: an MP's figure is a first guess.")
    limits.append("Line-by-line rates are not checked yet: they need the state's Schedule of "
                  "Rates (T096).")
    evidence = {"grand_total": grand, "mp_amount": mp, "mp_gap": c["mp_gap"],
                "reason_differs_from_mp": reason, "sites": sites_ev, "notes": notes,
                "reference": {k: (ref or {}).get(k) for k in ("state", "source", "years")}}
    if findings:
        findings.sort(key=lambda f: -f.risk)
        return _result(Status.ASSESSED, findings[0].text, t0, verdict=findings[0].code,
                       findings=findings, limitations=limits, **evidence)
    if not compared:
        return _result(Status.NOT_ASSESSABLE, "Could not compare this estimate with anything "
                       "yet: " + " ".join(limits[:-1] or limits) + " This is not a clean chit.",
                       t0, limitations=limits, **evidence)
    return _result(Status.ASSESSED, " ".join(notes) or "The quantities fit the size of the work.",
                   t0, verdict="ESTIMATE_FITS_SIZE", limitations=limits, **evidence)
