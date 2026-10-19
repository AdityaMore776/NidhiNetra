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

  RATE_TYPO_NOT_ANSWERED         (T164, the owner) a line held as a likely typing mistake (below)
                                 whose rate is above the form's guard and which, left unanswered,
                                 puts at least GAP_MIN_RS and GAP_SHARE more into the estimate
                                 than its fair rate here (else the guard's top): padding worse than
                                 the guard had asked nothing

A form with something still to fix is not judged. Warnings the agency has not confirmed do not
switch the check off (T135: one unanswered warning was enough to): a line whose rate or unit looks
like a typing mistake is held out of the price check until it is answered; everything else is
judged, and the result says what was held. The held line's money is still in the total: when it
is big, RATE_TYPO_NOT_ANSWERED asks for the rate to be corrected before sanction.

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
# T167 (the owner, 19 Oct 2026: a fraud is never an edge case; at the least "check this"), plan
# docs/plans/T167-cost-eval.md, measured by the eval in data/eval/cost/. Levels: fits, edge (a
# leeway explains something unusual: a note), check (CHECK_RISK, "check this"), ask (0.4+).
# Leeway the agent verifies itself can clear a case to "edge"; leeway that rests on the agency's
# word (a hilly site, a bigger specification, the MP agreeing) only softens "ask" to "check".
CHECK_RISK = 0.3
EDGE_SHARE = 0.05           # CPWD Works Manual 20.4.3.2: up to 5% over justified rates is ignored,
CHECK_SHARE = 0.10          # up to 10% allowed with recorded reasons, beyond it not accepted
CHECK_MIN_RS = 25_000       # below this the money is too small to check (half the ask floor)
QUANTITY_CHECK = 1.10       # a confirmed quantity this far above the need (with its room)
LABOUR_CHECK = 1.5          # a trade's day rate this many times others' (below labour's 2x ask)
DAYS_CHECK = 2.0            # a trade's person-days per unit of size, times other agencies'
ASK_LEVEL = 0.4             # a finding this risky or more is a question ("ask")
CLAIMED_ALLOWANCE = 0.15   # a hilly or head-load site: an ask below GAP_SHARE + this -> check
REMOTE = {"terrain": ("hilly",), "access": ("head_load_only",)}
FORM_UNIT ={"STREET_LIGHT|solar": "nos", "STREET_LIGHT|grid": "nos", "HIGH_MAST": "nos"}
REF_UNIT_SIZE = {"per light": "nos", "per mast": "nos", "per unit": "nos", "per metre": "m"}
# the specification a higher price could come from, in words
SPEC_WORDS = {"led_w": "LED {:g} W", "battery_wh": "battery {:g} Wh", "panel_wp": "panel {:g} Wp",
              "pole_height_m": "pole {:g} m", "mast_height_m": "mast {:g} m",
              "lamps_per_mast": "{:g} lamps", "lamp_w": "lamps of {:g} W"}


HI_WHOLE = ("पूरा अनुमान इस आकार और इस ज़िले के उचित मूल्य से {share} अधिक है; अंतर बनाने वाली "
            "पंक्तियाँ विवरण में हैं। स्वीकृति से पहले जाँच करें।")


HI_TYPO = ("एक दर टाइपिंग की गलती जैसी लगती है और इससे अनुमान में {extra} अधिक जुड़ता है; एजेंसी ने "
           "फ़ॉर्म की चेतावनी का उत्तर नहीं दिया। स्वीकृति से पहले दर ठीक करवाएँ या स्पष्ट करवाएँ।")


def _rs(v: float) -> str:
    return f"Rs {v / 1e5:,.2f} lakh" if v >= 1e5 else f"Rs {v:,.0f}"


def _held_typos(form: dict, held: set, sor, index, work: dict, when) -> list[dict]:
    """The lines held as a likely typing mistake whose rate is above the form's guard (T164),
    each with the money it adds over its fair rate here, else over the guard's top (the highest
    rate the form believes): a rate below the guard lowers the estimate, and is no question."""
    out = []
    sites = form.get("sites") if isinstance(form.get("sites"), list) else []
    for i, j in sorted(held):
        ln = sites[i]["lines"][j]
        mid = ln.get("material_id")
        if not isinstance(mid, str) or mid in ("", "none") or not catalog.material(mid):
            mid = materials.match(ln.get("item") if isinstance(ln.get("item"), str) else None,
                                  labour=materials.LABOUR_BY_GROUP.get(ln.get("group")))
        mat = catalog.material(mid) if mid else None
        if not mat or not mat.get("guard"):
            continue
        rate = rates.per_unit(mid, ln.get("rate"), ln.get("unit"))
        qty = norms.to_first_unit(mid, ln.get("quantity"), ln.get("unit"))
        if qty is None and catalog.is_labour(mid) and ln.get("quantity") in (None, ""):
            qty = catalog.person_days(ln)
        top = float(mat["guard"][1])
        if rate is None or qty is None or qty <= 0 or rate <= top:
            continue
        fair, _gap = rates.price_line(mid, ln, sor, index, work.get("district_lgd"),
                                      rates.agency_of(work), str(work.get("work_id")), when,
                                      rates._state(work))
        base, kind = (fair.rate, "fair") if fair else (top, "guard")
        out.append({"site": i, "line": j, "material": mid, "label": mat["label"],
                    "unit": mat["units"][0], "rate": round(rate, 2), "quantity": round(qty, 3),
                    "base_rate": round(base, 2), "base": kind,
                    "extra": round(qty * (rate - base), 2)})
    return sorted(out, key=lambda t: -t["extra"])


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
            "quantity": worst["quantity"], "low": worst["low"], "needed": worst["needed"],
            "unit": worst["unit"], "ratio": worst["ratio"]}


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


def _quantity_rs(lines: list, q: dict) -> float:
    """The money in a material's quantity beyond what the size needs, at the lines' own rate."""
    qty = rs = 0.0
    for j in q["lines"]:
        ln = lines[j] if 0 <= j < len(lines) and isinstance(lines[j], dict) else {}
        r = rates.per_unit(q["material"], ln.get("rate"), ln.get("unit"))
        x = norms.to_first_unit(q["material"], ln.get("quantity"), ln.get("unit"))
        if r is not None and x:
            qty, rs = qty + x, rs + x * r
    return max(0.0, q["quantity"] - q["needed"]) * rs / qty if qty > 0 else 0.0


def _check_sentence(w: whole.Whole) -> str:
    """whole.sentence without its closing call to check before sanction."""
    return whole.sentence(w).removesuffix(" Needs checking before sanction.")


def _remote(form: dict) -> str | None:
    """The site conditions the form claims that make carriage dearer, in words, or None."""
    words = []
    for site in form.get("sites") or []:
        cond = site.get("site_conditions") if isinstance(site, dict) else None
        if not isinstance(cond, dict):
            continue
        if cond.get("terrain") in REMOTE["terrain"]:
            words.append("hilly")
        if cond.get("access") in REMOTE["access"]:
            words.append("reached only on foot (materials carried by hand)")
    return " and ".join(dict.fromkeys(words)) or None


def _crew_against_peers(form: dict, work_type, lab, index, work: dict, when) -> list[dict]:
    """Labour rows with DAYS_CHECK times or more the person-days per unit of size other
    agencies' crews take for the same work type (rates.days_key: one agency, one vote)."""
    if index is None:
        return []
    out = []
    sites = form.get("sites") or []
    for r in lab.rows:
        size = sites[r.site].get("size") if r.site < len(sites) else None
        m = rates.size_measure(work_type, size)
        if not r.trade or not m:
            continue
        found, _gap = index.price(work.get("district_lgd"), rates._state(work),
                                  rates.days_key(work_type, r.trade), rates.agency_of(work),
                                  str(work.get("work_id")), when)
        if not found or found[0] <= 0:
            continue
        peer = found[0] * m[0]
        times = r.person_days / peer
        if times >= DAYS_CHECK:
            out.append({"site": r.site, "line": r.line, "trade": r.trade, "label": r.label,
                        "person_days": round(r.person_days, 1), "peer": round(peer, 1),
                        "times": round(times, 2), "where": found[2],
                        "extra": round((r.person_days - peer) * r.rate, 2)})
    return sorted(out, key=lambda x: -x["extra"])


def _district_above_state(w: whole.Whole, index, work: dict, when) -> dict | None:
    """The priced lines whose district rate sits above the rest of the state's plus its
    allowance, and what the estimate would lose at that cap (T167)."""
    if index is None:
        return None
    lines, extra, base = [], 0.0, 0.0
    for x in w.lines:
        if x.fair_source != "district" or x.fair_rate is None:
            continue
        v = index.rest_of_state(work.get("district_lgd"), rates._state(work), x.material,
                                rates.agency_of(work), str(work.get("work_id")), when)
        if v is None:
            continue
        cap = v.rate * (1 + rates.STATE_ALLOWANCE)
        if x.fair_rate > cap and x.rate > cap:
            extra += x.fair_quantity * (x.rate - cap)
            base += x.fair_quantity * cap
            lines.append({"material": x.material, "label": x.label, "unit": x.unit,
                          "rate": round(x.rate, 2), "district": round(x.fair_rate, 2),
                          "state": round(v.rate, 2), "cap": round(cap, 2)})
    if not lines or base <= 0:
        return None
    return {"lines": lines, "extra": round(extra, 2), "share": round(extra / base, 4)}


def _top(x: whole.Line) -> dict:
    """A line that makes the gap, as the officer's screen names it."""
    return {"line": x.index, "material": x.material, "label": x.label, "unit": x.unit,
            "quantity": round(x.quantity, 3), "rate": round(x.rate, 2),
            "fair_rate": None if x.fair_rate is None else round(x.fair_rate, 2),
            "fair_low": None if x.fair_low is None else round(x.fair_low, 2),
            "fair_high": None if x.fair_high is None else round(x.fair_high, 2),
            "needed": None if x.needed is None else round(x.needed, 3),
            "needed_low": None if x.needed_low is None else round(x.needed_low, 3),
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
    as_filed = form
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
    leeway: list[dict] = []     # T167: what was let through, and on whose word
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
            if QUANTITY_CHECK < q["ratio"] <= QUANTITY_MARGIN:
                # T167: beyond the usual room, below the question's 25%: check this when the
                # extra is real money (1.2 times a road's cement is about Rs 1 lakh)
                extra = _quantity_rs(lines, q)
                name = catalog.material(q["material"])["label"].lower()
                if extra >= CHECK_MIN_RS:
                    findings.append(Finding(
                        "MATERIAL_QUANTITY_ABOVE_NEED",
                        f"{label.capitalize()}: {name}, "
                        f"{catalog.quantity_text(q['quantity'], q['unit'])} in the estimate, "
                        f"{q['ratio'] - 1:.0%} more than this size takes "
                        f"({catalog.range_text(q['low'], q['needed'], q['unit'])}; {q['why']}): "
                        f"about {_rs(extra)} of material beyond it. Check this.",
                        hard=False, risk=CHECK_RISK,
                        evidence={"site": i, **{k: q[k] for k in ("material", "quantity", "low",
                                                                  "needed", "unit")},
                                  "ratio": round(q["ratio"], 3), "extra": round(extra, 2),
                                  "lines": q["lines"]}))
            if q["ratio"] > QUANTITY_MARGIN:
                name = catalog.material(q["material"])["label"].lower()
                said = (any(k.startswith("more_than_size_needs:") and f"sites[{i}].lines[" in k
                            and any(f"lines[{j}]" in k for j in q["lines"]) for k in done)
                        or not any(x["key"].startswith("more_than_size_needs:")
                                   for x in pending))
                findings.append(Finding(
                    "MATERIAL_QUANTITY_ABOVE_SIZE",
                    f"{label.capitalize()}: {name}, "
                    f"{catalog.quantity_text(q['quantity'], q['unit'])} in the estimate, but "
                    f"this size takes {catalog.range_text(q['low'], q['needed'], q['unit'])} "
                    f"({q['why']}); "
                    + ("the agency confirmed the quantity when filling the form"
                       if said else "the form asked the agency to confirm the quantity, and it "
                       "has not") + ". Please check the estimate.",
                    hard=False, risk=QUANTITY_RISK,
                    evidence={"site": i, **{k: q[k] for k in ("material", "quantity", "low",
                                                              "needed", "unit", "why")},
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
                    f") is {sized['ratio']:.1f} times what that size takes "
                    f"({catalog.range_text(sized['low'], sized['needed'], sized['unit'])}): "
                    "check which size is right before sanction.",
                    hard=False, risk=SIZE_RISK,
                    evidence={"site": i, "form_size": sized["form"],
                              "scope_size": sized["scope"], "material": sized["material"],
                              "quantity": sized["quantity"], "low": sized["low"],
                              "needed": sized["needed"],
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
        # T145: the range most similar works fall in, not one figure
        standard = (f"8 in 10 of the {st['n']} similar works in {where} cost "
                    f"{_rs(st['p10'])} to {_rs(st['p90'])} per {unit} (median "
                    f"{_rs(st['median'])}); 98 in 100 cost at most {_rs(st['p98'])}")
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
                          "p10": st["p10"], "p90": st["p90"],
                          "n": st["n"], "mp_amount": mp, "mp_gap": c["mp_gap"]}))
        elif price > line:
            # T167: the MP agreeing does not make a price fair (an MP's figure can follow the
            # agency's): no longer a note, but "check this", never a question on its own
            spec = ", ".join(SPEC_WORDS[k].format(v) for k, v in size.items()
                             if k in SPEC_WORDS and isinstance(v, (int, float))
                             and not isinstance(v, bool))
            leeway.append({"kind": "claimed", "what": "the MP's amount is as high",
                           "why": "softens a price question to 'check this', never clears it"})
            findings.append(Finding(
                "PRICE_ABOVE_STANDARD",
                f"{label.capitalize()}: {_rs(price)} per {unit} ({units:g} of them); {standard}. "
                f"It is {price / st['p98']:.1f} times the 98th percentile. The MP's amount is as "
                "high, so it is not asked as a question, but check this"
                f"{f': does the specification ({spec}) explain the price?' if spec else '.'}",
                hard=False, risk=CHECK_RISK,
                evidence={"site": i, "price_per_unit": round(price, 2), "unit": unit,
                          "where": where, "p98": st["p98"], "median": st["median"],
                          "p10": st["p10"], "p90": st["p90"], "n": st["n"], "mp_amount": mp,
                          "mp_gap": c["mp_gap"]}))
        elif price > st["p98"]:
            leeway.append({"kind": "verified", "what": f"{label}: {_rs(price)} per {unit}",
                           "why": f"above 98 in 100 similar works, but within "
                                  f"{PRICE_MARGIN - 1:.0%} of them"})
            notes.append(f"{label.capitalize()}: {_rs(price)} per {unit} is above 98 in 100 "
                         f"similar works in {where} but within {PRICE_MARGIN - 1:.0%} of them "
                         f"({standard}).")
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
        whole_ev = {"gap": round(w.gap, 2),
                    "unexplained": {k: round(v, 2) for k, v in w.unexplained.items()},
                    "gap_share": round(w.gap_share, 4), "fair_total": round(w.fair_grand, 2),
                    "fair_low": round(w.fair_low, 2), "fair_high": round(w.fair_high, 2),
                    "coverage": round(w.coverage, 4), "grand_total": round(w.grand, 2),
                    "above_fair_rate": w.above_fair, "priced_lines": w.priced,
                    "top": [_top(x) for x in w.top()],
                    "message_hi": HI_WHOLE.format(share=f"{w.gap_share:.0%}")}
        remote = _remote(form)
        loose_rs = sum(w.unexplained.values())
        # wages already asked about line by line (labour.py, twice the trade's rate) are not
        # counted again toward "check this"
        asked_rs = sum(x.extra for x in w.lines if catalog.is_labour(x.material)
                       and x.fair_rate and x.rate >= labour.RATE_MARGIN * x.fair_rate)
        base_rs = w.gap / w.gap_share if w.gap_share else 0.0
        net_share = (w.gap - asked_rs) / base_rs if base_rs > 0 else 0.0
        if w.verdict == "ASK" and remote and w.gap_share < whole.GAP_SHARE + CLAIMED_ALLOWANCE:
            # T167: a claimed hilly or head-load site softens the question, never clears it
            leeway.append({"kind": "claimed", "what": f"the form says the site is {remote}",
                           "why": f"carriage can cost up to {CLAIMED_ALLOWANCE:.0%} more; the "
                                  "site video shows the terrain"})
            findings.append(Finding(
                "ESTIMATE_ABOVE_FAIR_RANGE",
                _check_sentence(w) + f" The form says the site is {remote}, and carriage there "
                "can cost this much more, so it is not asked as a question: check the terrain on "
                "the site video before sanction.", hard=False, risk=CHECK_RISK,
                evidence={**whole_ev, "claimed": remote}))
        elif w.verdict == "ASK":
            findings.append(Finding("ESTIMATE_ABOVE_FAIR_PRICE", whole.sentence(w), hard=False,
                                    risk=WHOLE_RISK, evidence=whole_ev))
        elif ((net_share >= CHECK_SHARE and w.gap - asked_rs >= CHECK_MIN_RS
               and w.grand > w.fair_high) or loose_rs >= CHECK_MIN_RS):
            # T167: beyond CPWD's 10% and above the highest rates other agencies here charge,
            # or money no line explains beyond the usual shares: check this
            findings.append(Finding("ESTIMATE_ABOVE_FAIR_RANGE", _check_sentence(w) + (
                " Below the 15% for a question, but beyond the 10% the CPWD Works Manual allows "
                "over justified rates, and above the highest rates other agencies here charge: "
                "check this." if net_share >= CHECK_SHARE else " Check this: money no line "
                "explains, beyond what estimates usually carry."), hard=False, risk=CHECK_RISK,
                evidence=whole_ev))
        if not any(f.code in ("ESTIMATE_ABOVE_FAIR_PRICE", "ESTIMATE_ABOVE_FAIR_RANGE")
                   for f in findings):
            span = whole.rs_range(w.fair_low, w.fair_high)
            notes.append(f"The whole estimate is {_rs(w.grand)} against a fair "
                         f"{_rs(w.fair_grand)}"
                         + (f" ({span} at the lowest and highest rates other agencies here "
                            "charge)" if span != _rs(w.fair_grand) else "")
                         + f", {w.gap_share:+.1%}, pricing {w.coverage:.0%} of the money: within "
                         "the fair band"
                         + (", leaving out the line held as a likely typing mistake, which counts "
                            "at its own value" if held else "") + ".")
            if w.gap_share >= EDGE_SHARE and w.gap > 0:
                # T167: let through on what the agent can see for itself
                why = ("within the 10% the CPWD Works Manual allows over justified rates"
                       if w.gap_share < CHECK_SHARE else
                       "within the highest rates other agencies here charge"
                       if w.grand <= w.fair_high else
                       f"the gap ({_rs(w.gap)}) is too small to check")
                leeway.append({"kind": "verified", "what": f"the estimate is "
                               f"{w.gap_share:.0%} above its fair price", "why": why})
            if w.fallbacks and w.gap > 0:
                leeway.append({"kind": "verified", "what": "priced from the state's forms",
                               "why": f"{rates.STATE_ALLOWANCE:.0%} allowed for local prices"})
    # 3b. a rate held as a likely typing mistake still carries its money in the estimate's total
    #     (T164, the owner: worse padding than the form's guard went unasked)
    typo = _held_typos(as_filed, held, sor, data.get("rates"), work, when)
    extra = sum(t["extra"] for t in typo)
    if typo and extra >= whole.GAP_MIN_RS and extra >= whole.GAP_SHARE * (lines_total - extra):
        compared = True
        top = typo[0]
        base = (f"other agencies here charge {_rs(top['base_rate'])} a {top['unit']}"
                if top["base"] == "fair" else
                f"the form takes any rate above {_rs(top['base_rate'])} a {top['unit']} for a "
                "typing mistake")
        more = len(typo) - 1
        findings.append(Finding(
            "RATE_TYPO_NOT_ANSWERED",
            f"{top['label']} at {_rs(top['rate'])} a {top['unit']} ({base}) puts "
            f"{_rs(top['extra'])} more into this estimate"
            + (f", and {more} more such line{'s' * (more != 1)} {_rs(extra - top['extra'])}"
               if more else "")
            + f": {_rs(extra)} of its {_rs(grand)}. The form asked the agency whether the rate is "
            "a typing mistake, and it has not answered. Get the rate corrected or explained "
            "before sanction.",
            hard=False, risk=PRICE_RISK,
            evidence={"lines": typo, "extra": round(extra, 2),
                      "share": round(extra / max(lines_total - extra, 1.0), 4),
                      "message_hi": HI_TYPO.format(extra=_rs(extra))}))
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
    # 4b. T167: wages between LABOUR_CHECK and the question's margin, when they add real money
    #     (the same share of the margin when the rate comes from a grade's pool: an honest mason
    #     priced against labourers' pay is far above it, robustness loop)
    high = [r for r in lab.compared if r.times and r.margin
            and LABOUR_CHECK / labour.RATE_MARGIN * r.margin <= r.times < r.margin
            and (r.site, r.line) not in {(a.site, a.line) for a in lab.asked}]
    if high and sum(r.extra for r in high) >= CHECK_MIN_RS:
        findings.append(Finding(
            "LABOUR_RATE_ABOVE",
            "Wages above what other agencies here pay the same trade: "
            + "; ".join(f"{r.label.lower()} at {_rs(r.rate)} a day, {r.times:.1f} times "
                        f"{_rs(r.fair)}" for r in high[:3])
            + f". {_rs(sum(r.extra for r in high))} more over the work. Below twice the rate (a "
            "question), but no crew here earns this much more: check this.",
            hard=False, risk=CHECK_RISK,
            evidence={"rows": [r.to_json() for r in high],
                      "extra": round(sum(r.extra for r in high), 2)}))
    elif any(r.times and r.times >= 1.15 for r in lab.compared):
        leeway.append({"kind": "verified", "what": "a trade paid above others here",
                       "why": f"within {LABOUR_CHECK:g} times their rate: the agency's call"})
    # 4c. T167: a crew far larger than other agencies' for the same size (ghost workers)
    crowd = _crew_against_peers(form, work_type, lab, data.get("rates"), work, when)
    if crowd and sum(x["extra"] for x in crowd) >= CHECK_MIN_RS:
        findings.append(Finding(
            "LABOUR_DAYS_ABOVE_PEERS",
            "More labour than other agencies use for this size of work: "
            + "; ".join(f"{x['label'].lower()} {x['person_days']:,.0f} person-days, "
                        f"{x['times']:.1f} times the {x['peer']:,.0f} others' crews take "
                        f"({x['where']})" for x in crowd[:3])
            + f". {_rs(sum(x['extra'] for x in crowd))} of wages beyond them. Check the muster "
            "roll and the crew on the site video.", hard=False, risk=CHECK_RISK,
            evidence={"rows": crowd, "extra": round(sum(x["extra"] for x in crowd), 2)}))
    # 4d. T167: the district's own rates far above the rest of the state's (all agencies
    #     raising rates together lift the district's fair rate with them)
    lifted = _district_above_state(w, data.get("rates"), work, when)
    if lifted and lifted["extra"] >= CHECK_MIN_RS and lifted["share"] >= CHECK_SHARE:
        findings.append(Finding(
            "DISTRICT_RATES_ABOVE_STATE",
            "Other agencies in this district charge more than the rest of the state, and this "
            "estimate prices at the district's rates: "
            + "; ".join(f"{x['label'].lower()} {_rs(x['rate'])} a {x['unit']} against "
                        f"{_rs(x['state'])} in the state's other districts" for x in
                        lifted["lines"][:3])
            + f". At the state's rates plus {rates.STATE_ALLOWANCE:.0%} for local prices the "
            f"estimate would be {_rs(lifted['extra'])} ({lifted['share']:.0%}) lower. Check "
            "whether the district's rates are fair.", hard=False, risk=CHECK_RISK,
            evidence=lifted))
    if held and not any(f.code == "RATE_TYPO_NOT_ANSWERED" for f in findings):
        leeway.append({"kind": "verified", "what": "a likely typing mistake",
                       "why": "left out of the price check until the agency answers; the money "
                              "it adds is too small to ask"})
    if sor is None:
        limits.append("The state's Schedule of Rates is not loaded yet (T096): lines are compared "
                      "with other agencies' recent rates in the district where there are enough, "
                      "and quantities with what the size needs.")
    evidence = {"grand_total": grand, "mp_amount": mp, "mp_gap": c["mp_gap"],
                "reason_differs_from_mp": reason, "sites": sites_ev, "notes": notes,
                "whole": w.to_json(), "labour": lab.to_json(),
                "data_gaps": [g.to_json() for g in w.gaps + w.fallbacks],
                "held_lines": sorted(held),
                "reference": {k: (ref or {}).get(k) for k in ("state", "source", "years")},
                # T167: the level the officer sees, and what was let through on whose word
                "level": ("ask" if any(f.risk >= ASK_LEVEL for f in findings) else
                          "check" if findings else "edge" if leeway else "fits"),
                "leeway": leeway}
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
