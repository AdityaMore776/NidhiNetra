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

  ESTIMATE_ABOVE_FAIR_PRICE      the whole estimate against its fair price (whole.py, T121)
  LABOUR_RATE_FAR_ABOVE          (T141, labour.py) a trade's day rate at least twice what other
                                 agencies pay that trade here; how many workers or days is never
                                 judged
  LABOUR_DAYS_BEYOND_WORK        (T141) workers on site longer than the whole work lasts
  ESTIMATE_NOT_ITEMISED          (T135) a construction estimate (its size says how much cement,
                                 sand or stone it needs) that keeps more than NOT_ITEMISED_SHARE
                                 of its money in lump sums or in items no reader recognises as a
                                 known material: nothing can be priced, so the estimate itself
                                 is the question. Our own missing price data never counts here
                                 (that is a data gap, recorded, not a finding).

A form with something still to fix is not judged. Warnings the agency has not confirmed do not
switch the check off (T135: one unanswered warning was enough to): a line whose rate or unit looks
like a typing mistake is held out of the price check until it is answered; everything else is
judged, and the result says what was held.

Notes, never findings: above the standard item but not above the MP's amount; above the MP's
amount but in line with the standard; below the standard (may run short of money); what could
not be compared and why.

A reference group is compared only when (reference.py): it has 30+ real works, its own spread is
tight (it captures the size), and its unit is the form's full pricing size (a road priced per m2
is never compared with roads per metre: the records hold no width).

  NOT_APPLICABLE  no form for this work. The record alone carries no size or specification, and
                  no price question from it was certain: of 15 works a record-only check would
                  have questioned, 0 were real (5 misread counts, 9 bigger items, 1 grey;
                  data/trial/simple_certain_trial.py, T099). The old Cost Anomaly is retired.
  NOT_ASSESSABLE  the form is not complete, or nothing on it could be compared

T099 (3 Oct 2026): this is the Cost check of the core slot; its findings count at fusion v3's
1-in-4 prior until officers' verdicts are read (T098).
"""

from __future__ import annotations

import copy
import re
import time

from drishti.agents.contract import AgentResult, Finding, Status
from drishti.agents.cost_estimate import labour, rates, reference, whole
from drishti.cost_form import catalog, materials, norms
from drishti.cost_form.validate import validate

AGENT = "cost_estimate"
VERSION = "cost-estimate-0.3.0"
QUESTION = ("Is every line of the estimate fairly priced for this district, and is the whole "
            "estimate fair?")
WHOLE_RISK = 0.6
QUANTITY_MARGIN = 1.25      # a confirmed quantity this far above what the size needs
PRICE_MARGIN = 1.25         # price per unit this far above the standard item's 98th percentile
MP_MARGIN = 0.10            # the estimate this far above the MP's amount (the form's own rule)
QUANTITY_RISK = 0.6
PRICE_RISK = 0.5
NOT_ITEMISED_RISK = 0.4
NOT_ITEMISED_SHARE = 0.40   # of the lines' money in lump sums or unrecognised items
HOLD = ("rate_typo", "unit_for_material")   # unanswered, these keep a line out of pricing
_LINE = re.compile(r"sites\[(\d+)\]\.lines\[(\d+)\]")
SIZE_RISK = 0.5
SIZE_DIFFERS = 0.25         # the size field this far from what the form's own scope says
# a length or width the scope states in metres ("300 m long", "3.5 m wide", "width 3.5 m")
_UNIT = r"(?:m|mtr|mtrs|mt|metres?|meters?|rmt)\.?"
_SCOPE_SIZE = {
    "length_m": (re.compile(rf"(\d+(?:\.\d+)?)\s*{_UNIT}\s+(?:long|in\s+length)", re.I),
                 re.compile(rf"length\s*(?:of\s*)?(\d+(?:\.\d+)?)\s*{_UNIT}(?![a-z])", re.I)),
    "width_m": (re.compile(rf"(\d+(?:\.\d+)?)\s*{_UNIT}\s+(?:wide|in\s+width)", re.I),
                re.compile(rf"width\s*(?:of\s*)?(\d+(?:\.\d+)?)\s*{_UNIT}(?![a-z])", re.I)),
}
CONFIDENCE = 0.6
FORM_UNIT = {"STREET_LIGHT|solar": "nos", "STREET_LIGHT|grid": "nos", "HIGH_MAST": "nos"}
REF_UNIT_SIZE = {"per light": "nos", "per mast": "nos", "per unit": "nos", "per metre": "m"}
# the specification a higher price could come from, in words
SPEC_WORDS = {"led_w": "LED {:g} W", "battery_wh": "battery {:g} Wh", "panel_wp": "panel {:g} Wp",
              "pole_height_m": "pole {:g} m", "mast_height_m": "mast {:g} m",
              "lamps_per_mast": "{:g} lamps", "lamp_w": "lamps of {:g} W"}


HI_WHOLE = ("पूरा अनुमान इस आकार और इस ज़िले के उचित मूल्य से {share} अधिक है; अंतर बनाने वाली "
            "पंक्तियाँ विवरण में हैं। स्वीकृति से पहले जाँच करें।")


def _rs(v: float) -> str:
    return f"Rs {v / 1e5:,.2f} lakh" if v >= 1e5 else f"Rs {v:,.0f}"


def _scope_text(form: dict, work: dict) -> str:
    part = form.get("work") if isinstance(form.get("work"), dict) else {}
    for v in (part.get("description"), work.get("description")):
        if isinstance(v, str) and v.strip():
            return v
    return ""


def scope_size(text: str) -> dict[str, float]:
    """The length and width in metres the scope of work states, where it states one plainly."""
    out = {}
    for key, patterns in _SCOPE_SIZE.items():
        found = {float(m.group(1)) for p in patterns for m in p.finditer(text or "")}
        if len(found) == 1:                  # two different figures: no plain statement
            out[key] = found.pop()
    return out


def _size_against_scope(work_type, size: dict, confirmed: list, text: str) -> dict | None:
    """When the size fields differ from the scope's own figures by over SIZE_DIFFERS AND the
    quantities would be asked about at the scope's size: what to say, else None."""
    stated = scope_size(text)
    alt, form_bits, scope_bits = dict(size), [], []
    for key, word in (("length_m", "long"), ("width_m", "wide")):
        have = size.get(key)
        if key not in stated or not isinstance(have, (int, float)) or isinstance(have, bool) \
                or have <= 0 or abs(stated[key] - have) <= SIZE_DIFFERS * have:
            continue
        alt[key] = stated[key]
        form_bits.append(f"{have:g} m {word}")
        scope_bits.append(f"{stated[key]:g} m {word}")
    if not form_bits:
        return None
    worst = max((q for q in norms.check(work_type, alt, confirmed)
                 if q["ratio"] > QUANTITY_MARGIN), key=lambda q: q["ratio"], default=None)
    if worst is None:
        return None
    return {"form": " and ".join(form_bits), "scope": " and ".join(scope_bits),
            "material": worst["material"],
            "label": catalog.material(worst["material"])["label"].lower(),
            "quantity": worst["quantity"], "needed": worst["needed"], "unit": worst["unit"],
            "ratio": worst["ratio"]}


def _not_itemised(form: dict, lines_total: float) -> dict:
    """The money in lump sums and in lines no known material's name fits (confirmed or not:
    a recognisable item the agency left unconfirmed is itemised, only not priced). The agency's
    own form: our missing price data is never counted here."""
    amount, items = 0.0, []
    for site in form.get("sites") if isinstance(form.get("sites"), list) else []:
        for ln in (site.get("lines") or []) if isinstance(site, dict) else []:
            if not isinstance(ln, dict):
                continue
            if ln.get("unit") == "ls":
                v = ln.get("amount")
            elif not catalog.material(ln.get("material_id")) and not materials.match(
                    ln.get("item") if isinstance(ln.get("item"), str) else None,
                    labour=materials.LABOUR_BY_GROUP.get(ln.get("group"))):
                q, r = ln.get("quantity"), ln.get("rate")
                v = q * r if all(isinstance(x, (int, float)) and not isinstance(x, bool)
                                 for x in (q, r)) else None
            else:
                continue
            if isinstance(v, (int, float)) and not isinstance(v, bool) and v > 0:
                amount += v
                if isinstance(ln.get("item"), str) and ln["item"].strip():
                    items.append(ln["item"].strip()[:60])
    return {"amount": amount, "items": items,
            "share": amount / lines_total if lines_total > 0 else 0.0}


def _top(x: whole.Line) -> dict:
    """A line that makes the gap, as the officer's screen names it."""
    return {"line": x.index, "material": x.material, "label": x.label, "unit": x.unit,
            "quantity": round(x.quantity, 3), "rate": round(x.rate, 2),
            "fair_rate": None if x.fair_rate is None else round(x.fair_rate, 2),
            "fair_quantity": round(x.fair_quantity, 3), "extra": round(x.extra, 2)}


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


def _confirmed(lines: list) -> list[tuple[int, str | None, object, object, object]]:
    """Only materials the agency chose themselves ("Recognised as" confirmed), with the line's
    words (an aggregate line written for the slab, norms.for_slab)."""
    out = []
    for j, ln in enumerate(lines):
        if isinstance(ln, dict):
            mid = ln.get("material_id")
            mid = mid if isinstance(mid, str) and mid not in ("", "none") else None
            out.append((j, mid, ln.get("quantity"), ln.get("unit"), ln.get("item")))
    return out


def assess(work: dict, ctx) -> AgentResult:
    t0 = time.perf_counter()
    form = work.get("cost_form")
    if not isinstance(form, dict) or not form:
        return _result(Status.NOT_APPLICABLE, "No cost estimate form for this work yet. The "
                       "record gives no size or specification, so its cost is not judged from "
                       "the amount alone.", t0)
    as_of = getattr(ctx, "as_of", None)
    checked = validate(form, today=as_of) if as_of else validate(form)
    fixes = sum(1 for i in checked["issues"] if i["level"] == "fix")
    if fixes:
        return _result(Status.NOT_ASSESSABLE, f"Cannot be assessed: the cost estimate form is not "
                       f"complete ({fixes} field{'s' * (fixes != 1)} to fix). This is not a clean "
                       "chit.", t0)
    done = set(form.get("confirmed") or []) if isinstance(form.get("confirmed"), list) else set()
    pending = [i for i in checked["issues"] if i["level"] != "fix" and i["key"] not in done]
    held = {(int(m[1]), int(m[2])) for i in pending if i["key"].split(":")[0] in HOLD
            and (m := _LINE.match(i["field"]))}
    if held:                     # judged without them: a typing mistake is never a question
        form = copy.deepcopy(form)
        for i, j in held:
            form["sites"][i]["lines"][j]["material_id"] = "none"
            form["sites"][i]["lines"][j]["held"] = True     # not shown fair (whole._unread)

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
    if pending:
        limits.append(f"{len(pending)} warning{'s' * (len(pending) != 1)} on the form "
                      f"{'are' if len(pending) != 1 else 'is'} not answered yet"
                      + (f"; {len(held)} line{'s' * (len(held) != 1)} whose rate or unit looks "
                         "like a typing mistake were left out of the price check until answered"
                         if held else "") + ".")
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
                said = (any(k.startswith("more_than_size_needs:") and f"sites[{i}].lines[" in k
                            and any(f"lines[{j}]" in k for j in q["lines"]) for k in done)
                        or not any(x["key"].startswith("more_than_size_needs:")
                                   for x in pending))
                findings.append(Finding(
                    "MATERIAL_QUANTITY_ABOVE_SIZE",
                    f"{label.capitalize()}: {name}, "
                    f"{catalog.quantity_text(q['quantity'], q['unit'])} in the estimate, but the "
                    f"size needs {q['needed']:,.0f} ({q['why']}); "
                    + ("the agency confirmed the quantity when filling the form"
                       if said else "the form asked the agency to confirm the quantity, and it "
                       "has not") + ". Please check the estimate.",
                    hard=False, risk=QUANTITY_RISK,
                    evidence={"site": i, **{k: q[k] for k in ("material", "quantity", "needed",
                                                              "unit", "why")},
                              "ratio": round(q["ratio"], 3), "lines": q["lines"]}))

        # 1b. a size the form's own scope contradicts, that the quantities rest on (T135: a
        #     road claimed 7 m wide justified twice the cement; its scope said 3.5 m)
        if not any(f.code == "MATERIAL_QUANTITY_ABOVE_SIZE" and f.evidence.get("site") == i
                   for f in findings) and len(form.get("sites") or []) == 1:
            sized = _size_against_scope(work_type, size, _confirmed(lines),
                                        _scope_text(form, work))
            if sized:
                compared = True
                findings.append(Finding(
                    "SIZE_NOT_AS_DESCRIBED",
                    f"The form gives the size as {sized['form']}, but its own scope of work says "
                    f"{sized['scope']}. At the scope's size the estimate's "
                    f"{sized['label']} ({catalog.quantity_text(sized['quantity'], sized['unit'])}"
                    f") is {sized['ratio']:.1f} times what is needed ({sized['needed']:,.0f}): "
                    "check which size is right before sanction.",
                    hard=False, risk=SIZE_RISK,
                    evidence={"site": i, "form_size": sized["form"],
                              "scope_size": sized["scope"], "material": sized["material"],
                              "quantity": sized["quantity"], "needed": sized["needed"],
                              "unit": sized["unit"], "ratio": round(sized["ratio"], 3)}))

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

    # 3. every line against its fair rate, then the whole estimate (T121)
    sor = data.get("sor") if "sor" in data else rates.load_sor(work.get("state_name"))
    when = rates._form_month(form, as_of)
    w = whole.judge(form, c, work_type, sor, data.get("rates"), work.get("district_lgd"),
                    rates.agency_of(work), str(work.get("work_id")), when, rates._state(work))
    if w.lines:
        compared = True
    if w.gaps:
        limits.append("Not priced here, for want of reliable price data (recorded, so it can be "
                      "collected): " + "; ".join(g.text() for g in w.gaps) + ".")
    if w.fallbacks:
        notes.append("Priced from other agencies' forms across the state, 10% more leniently, as "
                     "the district has too few of its own: "
                     + "; ".join(g.text() for g in w.fallbacks) + ".")
    loose = _not_itemised(form, lines_total)
    civil = any(n["material"] in whole.CIVIL for site in form.get("sites") or []
                if isinstance(site, dict)
                for n in norms.needs(work_type, site.get("size") if isinstance(site.get("size"),
                                                                              dict) else {}))
    if civil and loose["share"] > NOT_ITEMISED_SHARE:
        compared = True
        findings.append(Finding(
            "ESTIMATE_NOT_ITEMISED",
            f"{loose['share']:.0%} of the estimate's lines ({_rs(loose['amount'])}) are lump sums "
            "or items no standard name fits"
            + (f" ({', '.join(loose['items'][:3])})" if loose["items"] else "")
            + ", so its price cannot be checked. A construction estimate names its cement, sand, "
            "stone, steel and labour: ask for the itemised estimate before sanction.",
            hard=False, risk=NOT_ITEMISED_RISK,
            evidence={"share": round(loose["share"], 4), "amount": round(loose["amount"], 2),
                      "items": loose["items"][:5]}))
    if w.verdict == "CANT_CHECK":
        limits.append(f"Only {w.judged:.0%} of the money is in lines with a fair rate or a "
                      f"known need (at least {whole.MIN_COVERAGE:.0%} is needed), so the whole "
                      "estimate was not judged.")
    else:
        # the whole estimate is judged on rates and quantities together. A confirmed quantity
        # far beyond what the size needs stays its own question: it is a certain fact, and on
        # its own it can be too little money to move the total (cost_whole_trial.py: a half
        # again of the cement adds about a tenth to a road's estimate)
        if w.verdict == "ASK":
            findings.append(Finding("ESTIMATE_ABOVE_FAIR_PRICE", whole.sentence(w), hard=False,
                                    risk=WHOLE_RISK,
                                    evidence={"gap": round(w.gap, 2),
                                              "unexplained": {k: round(v, 2) for k, v
                                                              in w.unexplained.items()},
                                              "gap_share": round(w.gap_share, 4),
                                              "fair_total": round(w.fair_grand, 2),
                                              "coverage": round(w.coverage, 4),
                                              "grand_total": round(w.grand, 2),
                                              "above_fair_rate": w.above_fair,
                                              "priced_lines": w.priced,
                                              "top": [_top(x) for x in w.top()],
                                              "message_hi": HI_WHOLE.format(
                                                  share=f"{w.gap_share:.0%}")}))
        else:
            notes.append(f"The whole estimate is {_rs(w.grand)} against a fair "
                         f"{_rs(w.fair_grand)} ({w.gap_share:+.1%}), pricing {w.coverage:.0%} "
                         "of the money: within the fair band.")
    # 4. labour, trade by trade: only blatant rates and days beyond the work (T141)
    lab = labour.judge(form, checked["issues"], done, sor, data.get("rates"),
                       work.get("district_lgd"), rates.agency_of(work), str(work.get("work_id")),
                       when, rates._state(work), held)
    if lab.compared or lab.beyond:
        compared = True
    if lab.asked:
        top = lab.asked[0]
        findings.append(Finding(
            "LABOUR_RATE_FAR_ABOVE", labour.rate_sentence(lab), hard=False, risk=labour.RATE_RISK,
            evidence={"rows": [r.to_json() for r in lab.asked],
                      "extra": round(sum(r.extra for r in lab.asked), 2),
                      "message_hi": labour.HI_RATE.format(times=f"{top.times:.1f}")}))
    elif lab.compared:
        notes.append(f"Labour: {len(lab.compared)} trade row{'s' * (len(lab.compared) != 1)} "
                     "compared with what others pay the same trade; none is at twice it.")
    if lab.beyond:
        findings.append(Finding(
            "LABOUR_DAYS_BEYOND_WORK", labour.days_sentence(lab), hard=False,
            risk=labour.DAYS_RISK,
            evidence={"rows": [{**b.row.to_json(), "work_days": round(b.work_days, 1),
                                "cost": round(b.cost, 2), "confirmed": b.confirmed}
                               for b in lab.beyond],
                      "message_hi": labour.HI_DAYS}))
    if lab.grade_above:
        notes.append("A grade above the trade's own was given for "
                     + ", ".join(dict.fromkeys(lab.grade_above))
                     + "; each is compared with what others pay for its trade.")
    if sor is None:
        limits.append("The state's Schedule of Rates is not loaded yet (T096): lines are compared "
                      "with other agencies' recent rates in the district where there are enough, "
                      "and quantities with what the size needs.")
    evidence = {"grand_total": grand, "mp_amount": mp, "mp_gap": c["mp_gap"],
                "reason_differs_from_mp": reason, "sites": sites_ev, "notes": notes,
                "whole": w.to_json(), "labour": lab.to_json(),
                "data_gaps": [g.to_json() for g in w.gaps + w.fallbacks],
                "held_lines": sorted(held),
                "reference": {k: (ref or {}).get(k) for k in ("state", "source", "years")}}
    if findings:
        findings.sort(key=lambda f: -f.risk)
        return _result(Status.ASSESSED, findings[0].text, t0, verdict=findings[0].code,
                       findings=findings, limitations=limits, **evidence)
    if not compared:
        return _result(Status.NOT_ASSESSABLE, "Could not compare this estimate with anything "
                       "yet: " + " ".join(limits) + " This is not a clean chit.",
                       t0, limitations=limits, **evidence)
    return _result(Status.ASSESSED, " ".join(notes) or "The quantities fit the size of the work.",
                   t0, verdict="ESTIMATE_FITS_SIZE", limitations=limits, **evidence)
