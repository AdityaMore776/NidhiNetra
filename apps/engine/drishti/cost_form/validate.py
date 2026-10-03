"""The checks made WHILE the cost estimate form is filled (T093). None of them is ever a flag.

A normal mistake (a missing field, a typo, an extra zero, the wrong unit) must be caught here,
on the agency's own screen, not turned into a question for an officer later. Every check gives
one of two answers:

  fix       the form cannot be submitted until it is corrected: a required field is empty, a
            value is impossible (a road 37 m wide), the amount is not quantity x rate, the lines
            do not add up to the estimate document's total
  confirm   it looks like a typing mistake but could be right (a road 14 m wide, cement at Rs
            4,200 a bag): the person corrects it or confirms it, and a confirmed value stands

validate(form) returns every issue, the totals worked out from the lines, and `ready` (no fix
left and every confirm acknowledged). It never shows or uses a reference price.

The form, as JSON (docs/specs/2026-10-03-cost-estimate-form.md):
  {"recommendation": {...}, "work": {...},
   "sites": [{"location": {...}, "size": {...}, "site_conditions": {...}, "lines": [{...}]}],
   "charges": {...}, "timing": {...}, "totals": {...}, "prepared": {...},
   "declarations": {...}, "confirmed": ["<code>:<field>", ...],
   "earlier_works": [{"earlier_work": "<work id>", "answer": "same|continues|different",
                      "difference": "..."}]}            (T100: the agency's answers, see _earlier)
"""

from __future__ import annotations

import math
import re
from datetime import date

from drishti.cost_form import catalog, materials, norms

FIX, CONFIRM = "fix", "confirm"
LINE_TOLERANCE = 0.01       # an amount may differ from quantity x rate by rounding only
TOTAL_TOLERANCE = 0.005     # the lines against the estimate document's grand total
LUMP_SUM_SHARE = 0.20       # above this share in lump sums, ask for a breakdown
OTHER_SHARE = 0.10          # above this share in "anything else", ask for a breakdown
GST_RATES = {0, 5, 12, 18, 28, 40}
GST_TOLERANCE = 0.02
STALE_MONTHS = 18
INDIA = {"lat": (6.0, 37.7), "lon": (68.0, 97.5)}
# words that may mean a cost MPLADS does not pay for: asked, never blocked (a false match must
# not stop a form)
NOT_PAYABLE = ("land purchase", "land cost", "cost of land", "compensation", "maintenance",
               "amc", "salary", "salaries", "fuel", "rent")
_MONTH = re.compile(r"^(\d{4})-(\d{2})$")
_DATE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")
_PIN = re.compile(r"^[1-9]\d{5}$")


class _Issues:
    def __init__(self) -> None:
        self.items: list[dict] = []

    def add(self, level: str, code: str, field: str, message: str) -> None:
        self.items.append({"level": level, "code": code, "field": field, "message": message,
                           "key": f"{code}:{field}"})


def _s(v) -> str:
    """A field meant to hold text or an id, as a string ("" for anything else)."""
    return v if isinstance(v, str) else ""


def _empty(v) -> bool:
    return v is None or (isinstance(v, (str, list, dict)) and not v)


def _number(v) -> float | None:
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v) if math.isfinite(v) else None
    if isinstance(v, str):
        try:
            x = float(v.replace(",", "").strip())
        except ValueError:
            return None
        return x if math.isfinite(x) else None
    return None


def _month(v) -> tuple[int, int] | None:
    m = _MONTH.match(v) if isinstance(v, str) else None
    if not m or not 1 <= int(m.group(2)) <= 12:
        return None
    return int(m.group(1)), int(m.group(2))


def _rs(x: float) -> str:
    return f"Rs {x:,.0f}"


class _Ctx:
    """What decides which fields apply."""

    def __init__(self, form: dict) -> None:
        work = form.get("work") or {}
        work = work if isinstance(work, dict) else {}
        self.work_type = _s(work.get("work_type")) or None
        self.goods = catalog.is_goods(self.work_type, _s(work.get("nature")))
        self.linear = catalog.is_linear(self.work_type)
        self.group: str | None = None
        sites = form.get("sites") if isinstance(form.get("sites"), list) else []
        self.any_sor = any(isinstance(ln, dict) and ln.get("basis") == "sor"
                           for s in sites if isinstance(s, dict)
                           for ln in (s.get("lines") if isinstance(s.get("lines"), list) else []))
        self.mp_gap: float | None = None


def _applies(f: dict, values: dict, ctx: _Ctx) -> bool:
    if f.get("types") and ctx.work_type not in f["types"]:
        return False
    if f.get("construction_only") and ctx.goods:
        return False
    if f.get("linear_only") and not ctx.linear:
        return False
    if f.get("goods_only") and ctx.group != "goods":
        return False
    if f.get("when_any_line_basis") and not ctx.any_sor:
        return False
    if "when_mp_gap_over" in f and (ctx.mp_gap is None or abs(ctx.mp_gap) <= f["when_mp_gap_over"]):
        return False
    cond = f.get("when")
    if cond:
        other = values.get(cond["field"])
        if other is None or isinstance(other, (list, dict)):
            return False                # the field it depends on reports its own problem
        if "in" in cond and other not in cond["in"]:
            return False
        if "not_in" in cond and other in cond["not_in"]:
            return False
        if "gt" in cond and not ((_number(other) or 0) > cond["gt"]):
            return False
    return True


def _choices(f: dict) -> list | None:
    fid = f["id"]
    if fid == "work_type":
        return [t for fam in catalog.load()["families"].values() for t in fam["types"]]
    if fid == "unit":
        return list(catalog.load()["units"])
    if fid == "material_id":
        return [m["id"] for m in catalog.materials()] + ["none"]
    return f.get("choices")


def _check_value(out: _Issues, f: dict, v, path: str, values: dict) -> None:
    kind, label = f["kind"], f["label"]
    if kind in ("number", "gps"):
        x = _number(v)
        if x is None:
            out.add(FIX, "not_a_number", path, f"{label}: enter a number.")
            return
        if kind == "gps":
            lo, hi = INDIA["lat" if "lat" in f["id"] else "lon"]
            if not lo <= x <= hi:
                out.add(FIX, "gps_outside_india", path, f"{label}: {x} is outside India.")
            return
        unit = f" {f['unit']}" if f.get("unit") not in (None, "ls", "percent") else ""
        hard, soft = f.get("hard"), f.get("soft")
        if hard and not hard[0] <= x <= hard[1]:
            out.add(FIX, "impossible", path,
                    f"{label}: {x:g}{unit} is not possible (allowed {hard[0]:g} to {hard[1]:g}).")
        elif soft and not soft[0] <= x <= soft[1]:
            out.add(CONFIRM, "unusual", path,
                    f"{label}: {x:g}{unit} is unusual (most are {soft[0]:g} to {soft[1]:g}). "
                    "Correct it, or confirm it is right.")
    elif kind == "choice":
        allowed = _choices(f)
        if allowed is not None and (isinstance(v, (list, dict)) or v not in allowed):
            out.add(FIX, "not_a_choice", path, f"{label}: choose one of the options.")
        elif v == "other" and _empty(values.get(f"{f['id']}_other")):
            out.add(FIX, "other_unnamed", f"{path}_other",
                    f"{label}: you chose Other; write what it is.")
    elif kind == "multi":
        allowed = f.get("choices") or []
        if not isinstance(v, list) or any(x not in allowed for x in v):
            out.add(FIX, "not_a_choice", path, f"{label}: choose from the options.")
    elif kind == "bool":
        if not isinstance(v, bool):
            out.add(FIX, "not_yes_no", path, f"{label}: answer yes or no.")
        elif "must_be" in f and v is not f["must_be"]:
            out.add(FIX, "declaration", path, f"{label}: this must be true to submit the form.")
    elif kind == "text":
        if not isinstance(v, str):
            out.add(FIX, "not_text", path, f"{label}: enter text.")
            return
        if f["id"] == "pin" and not _PIN.match(v.strip()):
            out.add(FIX, "bad_pin", path, f"{label}: a PIN code is 6 digits.")
        if f.get("min_words") and len(v.split()) < f["min_words"]:
            out.add(FIX, "too_short", path,
                    f"{label}: write at least {f['min_words']} words ({len(v.split())} so far).")
    elif kind == "month":
        if _month(v) is None:
            out.add(FIX, "bad_month", path, f"{label}: give the month as YYYY-MM.")
    elif kind == "date":
        if not (isinstance(v, str) and _DATE.match(v)):
            out.add(FIX, "bad_date", path, f"{label}: give the date as YYYY-MM-DD.")
    elif kind == "file":
        if not isinstance(v, str):
            out.add(FIX, "no_file", path, f"{label}: attach the file.")


def _section(out: _Issues, fields: list[dict], values, path: str, ctx: _Ctx) -> None:
    values = values if isinstance(values, dict) else {}
    for f in fields:
        if not _applies(f, values, ctx):
            continue
        v = values.get(f["id"])
        if _empty(v):
            if f.get("required", True):
                out.add(FIX, "required", f"{path}.{f['id']}", f"{f['label']}: required.")
            continue
        _check_value(out, f, v, f"{path}.{f['id']}", values)


def _metres_between(a_lat, a_lon, b_lat, b_lon) -> float:
    r = 6_371_000.0
    p1, p2 = math.radians(a_lat), math.radians(b_lat)
    dp, dl = p2 - p1, math.radians(b_lon - a_lon)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


def _line(out: _Issues, ln: dict, path: str, ctx: _Ctx) -> dict:
    """Checks one expense line; returns its worked-out amount and material."""
    data = catalog.load()
    ctx.group = _s(ln.get("group")) or None
    if ctx.group not in {g["id"] for g in data["line_groups"]}:
        out.add(FIX, "no_group", f"{path}.group", "Choose which part of the estimate this line is.")
    item = _s(ln.get("item"))
    _section(out, data["line_fields"], ln, path, ctx)
    q, r, a = _number(ln.get("quantity")), _number(ln.get("rate")), _number(ln.get("amount"))
    unit = _s(ln.get("unit"))
    amount = None
    if unit == "ls":
        amount = a
        if a is None:
            out.add(FIX, "required", f"{path}.amount", "A lump sum needs its amount.")
    elif q is not None and r is not None:
        amount = q * r
        if a is not None and abs(a - amount) > max(1.0, LINE_TOLERANCE * amount):
            out.add(FIX, "line_arithmetic", f"{path}.amount",
                    f"{item or 'This line'}: {q:g} x {_rs(r)} = {_rs(amount)}, but the amount says "
                    f"{_rs(a)}. Correct the quantity, the rate or the amount.")
    elif a is not None:
        amount = a
        out.add(FIX, "line_incomplete", f"{path}.rate",
                f"{item or 'This line'}: give the quantity and the rate (or make it a lump sum).")
    suggested = materials.match(item)
    chosen = _s(ln.get("material_id"))
    mat_id = chosen or suggested
    mat = catalog.material(mat_id) if mat_id != "none" else None
    if mat and unit and unit != "ls" and unit in catalog.units():
        if unit not in mat["units"]:
            out.add(CONFIRM, "unit_for_material", f"{path}.unit",
                    f"{mat['label']} is usually given in {', '.join(mat['units'])}, not {unit}. "
                    "Check the unit, or confirm it.")
        elif r is not None and mat.get("guard"):
            per = materials.per_first_unit(mat, r, unit)
            lo, hi = mat["guard"]
            if per is not None and not lo <= per <= hi:
                out.add(CONFIRM, "rate_typo", f"{path}.rate",
                        f"{_rs(per)} per {mat['units'][0]} of {mat['label'].lower()} looks like a "
                        "typing mistake (an extra zero, or paise for rupees). Correct it, or "
                        "confirm it.")
    low = item.lower()
    if any(re.search(r"(?<![a-z])" + re.escape(w) + r"(?![a-z])", low) for w in NOT_PAYABLE):
        out.add(CONFIRM, "maybe_not_payable", f"{path}.item",
                f"{item}: MPLADS does not pay for land, maintenance or running costs. Remove it, "
                "or confirm it is part of building the work.")
    quotes = _number(ln.get("quotations_nos")) or 0
    if ctx.group == "goods" and not ln.get("gem_id") and quotes < 3:
        out.add(FIX, "goods_price_basis", f"{path}.gem_id",
                f"{item or 'This item'}: give its GeM product ID, or attach 3 quotations.")
    return {"amount": amount, "material_id": mat_id if mat else None,
            "material_suggested": suggested, "group": ctx.group}


CONTINUING = ("continuation", "extension", "upgrade", "reconstruction")


def _earlier(out: _Issues, fields: list[dict], form: dict, work: dict, earlier, ctx) -> None:
    """The agency's answers about the sanctioned works the Duplicate check found at this site or
    in the same words (T100): each must be answered, "same" stops the form (that work is already
    sanctioned), "continues" must match the nature and the earlier work ID, "different" says what
    differs. A continuation names the work it continues."""
    nature = _s(work.get("nature"))
    named = _s(work.get("earlier_work_id")).strip()
    if nature == "continuation" and not named:
        out.add(FIX, "continuation_needs_id", "work.earlier_work_id",
                "A continuation must name the earlier work it continues (its eSAKSHI work ID).")
    rows = form.get("earlier_works")
    rows = rows if isinstance(rows, list) else []
    answered = set()
    for i, row in enumerate(rows):
        path = f"earlier_works[{i}]"
        row = row if isinstance(row, dict) else {}
        _section(out, fields, row, path, ctx)
        wid, answer = _s(row.get("earlier_work")).strip(), _s(row.get("answer"))
        answered.add(wid)
        if answer == "same":
            out.add(FIX, "same_as_sanctioned", f"{path}.answer",
                    f"You say this is the same work as {wid}, which is already sanctioned: it "
                    "cannot be estimated again. Withdraw it, or change the answer if it is a "
                    "different work.")
        elif answer == "continues" and (nature not in CONTINUING or named != wid):
            out.add(FIX, "continues_mismatch", f"{path}.answer",
                    f"You say this work continues {wid}: set the nature of the work to "
                    "continuation, extension, upgrade or reconstruction, and the earlier work ID "
                    f"to {wid}.")
    for wid in earlier:
        if wid not in answered:
            out.add(FIX, "earlier_unanswered", "earlier_works",
                    f"Sanctioned work {wid} looks like this one (the same site or the same "
                    "words): say whether this is the same work, continues it, or is a different "
                    "work.")


def validate(form: dict, today: date | None = None, earlier=None) -> dict:
    """`earlier`: the ids of the sanctioned works the agency must answer about (the Duplicate
    check's candidates for this work, given by the API); None checks only the answers given."""
    today = today or date.today()
    data = catalog.load()
    out = _Issues()
    form = form if isinstance(form, dict) else {}
    ctx = _Ctx(form)
    work = form.get("work") if isinstance(form.get("work"), dict) else {}

    _section(out, data["recommendation"], form.get("recommendation"), "recommendation", ctx)
    _section(out, data["work"], work, "work", ctx)
    if isinstance(work, dict) and work.get("land_free") is False:
        out.add(FIX, "land_not_free", "work.land_free",
                "MPLADS cannot pay for land: the work must be on land that costs nothing.")

    sites = form.get("sites")
    if not isinstance(sites, list) or not sites:
        out.add(FIX, "no_site", "sites", "Add the site (one per place the work is done).")
        sites = []
    site_out, lines_total, ls_total, other_total = [], 0.0, 0.0, 0.0
    for i, site in enumerate(sites):
        site = site if isinstance(site, dict) else {}
        p = f"sites[{i}]"
        _section(out, data["location"], site.get("location"), f"{p}.location", ctx)
        size = site.get("size") if isinstance(site.get("size"), dict) else {}
        if catalog.family_of(ctx.work_type):
            _section(out, catalog.type_fields(ctx.work_type), size, f"{p}.size", ctx)
        if not ctx.goods:
            _section(out, data["site_conditions"], site.get("site_conditions"),
                     f"{p}.site_conditions", ctx)
        loc = site.get("location") or {}
        ends = [_number(loc.get(k)) for k in ("lat", "lon", "end_lat", "end_lon")] \
            if isinstance(loc, dict) else [None]
        if ctx.linear and all(x is not None for x in ends):
            d = _metres_between(*ends)
            length = _number(size.get("length_m"))
            if length is not None and length < 0.9 * d - 30:
                out.add(FIX, "shorter_than_ends", f"{p}.size.length_m",
                        f"The length ({length:,.0f} m) is shorter than the straight distance "
                        f"between its two ends on the map ({d:,.0f} m). Check the length or the "
                        "map points.")
            elif length is not None and length > 5 * d + 100:
                out.add(CONFIRM, "much_longer_than_ends", f"{p}.size.length_m",
                        f"The length ({length:,.0f} m) is more than 5 times the straight distance "
                        f"between its ends ({d:,.0f} m). Check the map points, or confirm.")
        lines = site.get("lines") if isinstance(site.get("lines"), list) else []
        done, seen, site_total = [], set(), 0.0
        for j, ln in enumerate(lines):
            ln = ln if isinstance(ln, dict) else {}
            res = _line(out, ln, f"{p}.lines[{j}]", ctx)
            done.append(res)
            amt = res["amount"] or 0.0
            site_total += amt
            if ln.get("unit") == "ls":
                ls_total += amt
            if res["group"] == "other":
                other_total += amt
            key = (" ".join(materials.tokens(_s(ln.get("item")))), _s(ln.get("unit")), res["group"])
            if key[0] and key in seen:
                out.add(CONFIRM, "duplicate_line", f"{p}.lines[{j}].item",
                        f"{ln.get('item')} appears twice. Remove one, or confirm both are needed.")
            seen.add(key)
        used = [(j, r["material_id"], lines[j].get("quantity"), lines[j].get("unit"))
                for j, r in enumerate(done) if isinstance(lines[j], dict)]
        for q in norms.check(ctx.work_type, size, used):
            if q["ratio"] > 1.0 + 1e-9:
                out.add(CONFIRM, "more_than_size_needs", f"{p}.lines[{q['lines'][0]}].quantity",
                        f"The lines have {q['quantity']:,.0f} {q['unit']} of "
                        f"{catalog.material(q['material'])['label'].lower()}; the size needs "
                        f"{q['needed']:,.0f} ({q['why']}). Check the quantity, or confirm it.")
        groups = {r["group"] for r in done}
        if ctx.goods and "goods" not in groups:
            out.add(FIX, "no_goods_lines", f"{p}.lines", "Add each item bought as a goods line.")
        if not ctx.goods and not (groups - {"goods", None}):
            out.add(FIX, "no_lines", f"{p}.lines", "Add the expense lines for this site.")
        lines_total += site_total
        site_out.append({"pricing": _pricing(ctx.work_type, size),
                         "lines_total": round(site_total, 2), "lines": done})

    charges = form.get("charges") if isinstance(form.get("charges"), dict) else {}
    _section(out, data["charges"], charges, "charges", ctx)
    cont = lines_total * (_number(charges.get("contingency_percent")) or 0) / 100
    esc = lines_total * (_number(charges.get("escalation_percent")) or 0) / 100
    gst_pct, gst_amt = _number(charges.get("gst_percent")), _number(charges.get("gst_amount"))
    if gst_pct is not None and gst_pct not in GST_RATES:
        out.add(CONFIRM, "gst_rate", "charges.gst_percent",
                f"GST at {gst_pct:g}% is not a usual rate. Check it, or confirm.")
    if gst_pct is not None and gst_amt is not None:
        expect = (lines_total + cont + esc) * gst_pct / 100
        if abs(gst_amt - expect) > max(1.0, GST_TOLERANCE * max(expect, 1.0)):
            out.add(CONFIRM, "gst_amount", "charges.gst_amount",
                    f"GST of {gst_pct:g}% on {_rs(lines_total + cont + esc)} would be "
                    f"{_rs(expect)}; the form says {_rs(gst_amt)}. Check it, or confirm (some "
                    "estimates charge GST on part of the work).")
    fees = sum(_number(charges.get(k)) or 0 for k in ("gst_amount", "labour_cess_amount",
                                                       "royalty_amount", "other_fees_amount"))
    grand = lines_total + cont + esc + fees

    timing = form.get("timing") if isinstance(form.get("timing"), dict) else {}
    _section(out, data["timing"], timing, "timing", ctx)
    est, start = _month(timing.get("estimate_month")), _month(timing.get("start_month"))
    now = (today.year, today.month)
    if est and est > now:
        out.add(FIX, "future_estimate", "timing.estimate_month",
                "The prices cannot be from a future month.")
    elif est and (now[0] - est[0]) * 12 + now[1] - est[1] > STALE_MONTHS:
        out.add(CONFIRM, "old_prices", "timing.estimate_month",
                f"These prices are more than {STALE_MONTHS} months old. Update them, or confirm.")
    if est and start and start < est:
        out.add(CONFIRM, "start_before_estimate", "timing.start_month",
                "The work starts before the month its prices are from. Check, or confirm.")
    dur = _number(timing.get("duration_months"))
    if esc > 0 and (dur is None or dur <= 12):
        out.add(FIX, "escalation_short_work", "charges.escalation_percent",
                "A price rise reserve is only for works longer than 12 months.")

    rec = form.get("recommendation") if isinstance(form.get("recommendation"), dict) else {}
    mp = _number(rec.get("mp_amount"))
    ctx.mp_gap = (grand - mp) / mp if mp and mp > 0 and grand > 0 else None
    totals = form.get("totals") if isinstance(form.get("totals"), dict) else {}
    _section(out, data["totals"], totals, "totals", ctx)
    doc = _number(totals.get("total_as_per_document"))
    if doc is not None and grand > 0 and abs(doc - grand) > TOTAL_TOLERANCE * grand:
        out.add(FIX, "total_mismatch", "totals.total_as_per_document",
                f"The lines and charges add up to {_rs(grand)}, but the estimate document says "
                f"{_rs(doc)}. Find the missing or extra amount.")
    if lines_total > 0 and ls_total / lines_total > LUMP_SUM_SHARE:
        out.add(CONFIRM, "lump_sums", "sites",
                f"{ls_total / lines_total:.0%} of the lines are lump sums. Break the large ones "
                "into quantity x rate, or confirm.")
    if lines_total > 0 and other_total / lines_total > OTHER_SHARE:
        out.add(CONFIRM, "other_share", "sites",
                f"{other_total / lines_total:.0%} is under 'anything else'. Move items to their "
                "group, or confirm.")

    _section(out, data["prepared"], form.get("prepared"), "prepared", ctx)
    _section(out, data["declarations"], form.get("declarations"), "declarations", ctx)
    _earlier(out, data["earlier_works"], form, work, earlier or (), ctx)

    confirmed = {c for c in form.get("confirmed") or [] if isinstance(c, str)} \
        if isinstance(form.get("confirmed"), list) else set()
    fixes = [i for i in out.items if i["level"] == FIX]
    open_confirms = [i for i in out.items if i["level"] == CONFIRM and i["key"] not in confirmed]
    return {
        "ready": not fixes and not open_confirms,
        "issues": out.items,
        "computed": {"lines_total": round(lines_total, 2), "contingency_amount": round(cont, 2),
                     "escalation_amount": round(esc, 2), "charges_total": round(fees, 2),
                     "grand_total": round(grand, 2),
                     "mp_gap": None if ctx.mp_gap is None else round(ctx.mp_gap, 4),
                     "sites": site_out},
    }


def _pricing(work_type, size: dict) -> dict | None:
    got = catalog.pricing_size(work_type, {k: _number(v) if _number(v) is not None else v
                                           for k, v in size.items()})
    return {"unit": got[0], "value": round(got[1], 4)} if got else None
