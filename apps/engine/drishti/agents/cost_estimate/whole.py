"""Judge the whole estimate (T121, plan T120 §6.5): "one costly line can be honest; every line a
little costly is a pattern".

    fair estimate = every compared line at the quantity the size needs (the stated quantity, at
                    most QTY_TOLERANCE above the need) x its fair rate (rates.py), every other
                    line at the agency's own value, and the charges in the agency's proportion
    gap           = the agency's grand total - the fair estimate

A line is compared when it has a fair rate, or when the size says how much of it is needed (then
only its extra quantity counts, at the agency's own rate). The verdict:

    CANT_CHECK  compared lines carry less than MIN_COVERAGE of the money (a status, not a score)
    ASK         the gap is at least GAP_SHARE of the fair price of what was priced (T135: of the
                fair estimate, a line left unpriced counted at its own value on both sides and
                watered the share down, so one padded line given an odd unit hid the rest) AND
                at least GAP_MIN_RS
    FAIR        otherwise

The thresholds are the plan's starting values; the planted-form trial and the first real
estimates (T098) set the final ones.

Money that is not shown to be fair (T135, the robustness loop: padding moved out of the priced
lines was invisible): in a construction estimate (one whose size says how much cement, sand or
stone it needs) lump sums beyond LUMP_SHARE of the lines, and "other" charges or contingency
beyond OTHER_SHARE / CONTINGENCY_SHARE of the lines, are not part of the fair estimate; nor (T136:
an equipment-hire line raised from 30 days to 250 hid Rs 5.5 lakh) are items no reader recognises
beyond UNREAD_SHARE of the lines (plant hire, earthwork, shuttering and curing of an honest CC road
come to well under it). The officer's sentence names them. A material that could not be priced
here records its gap (rates.Gap): the check is off for that price, never guessed, and the team
knows what to collect.
"""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date

from drishti.agents.cost_estimate import rates
from drishti.cost_form import catalog, materials, norms

QTY_TOLERANCE = 1.10
MIN_COVERAGE = 0.60
GAP_SHARE = 0.15
GAP_MIN_RS = 50_000
TOP_LINES = 3
LUMP_SHARE = 0.02             # lump sums a construction estimate may carry unitemised
OTHER_SHARE = 0.05            # "other" charges, beyond taxes the form names
OTHER_SHARE_NO_TAX = 0.23     # ... when the form says nothing of GST (it may sit in "other")
CONTINGENCY_SHARE = 0.05      # CPWD allows 3%; 5% is the form's own soft limit
UNREAD_SHARE = 0.15           # items no reader recognises, in a construction estimate (T136)
CIVIL = {"cement", "sand", "aggregate", "steel_rebar", "brick", "granular_base", "bitumen"}


def _rs(v: float) -> str:
    return f"Rs {v / 1e5:,.2f} lakh" if abs(v) >= 1e5 else f"Rs {v:,.0f}"


@dataclass
class Line:
    site: int
    index: int
    material: str
    label: str
    unit: str
    quantity: float
    rate: float
    fair_rate: float | None
    fair_source: str | None
    fair_where: str | None
    needed: float | None
    fair_quantity: float
    sor_code: str | None = None

    @property
    def amount(self) -> float:
        return self.quantity * self.rate

    @property
    def fair_amount(self) -> float:
        return self.fair_quantity * (self.fair_rate if self.fair_rate is not None else self.rate)

    @property
    def extra(self) -> float:
        return self.amount - self.fair_amount

    def to_json(self) -> dict:
        return {"site": self.site, "line": self.index, "material": self.material,
                "unit": self.unit, "quantity": round(self.quantity, 3), "rate": round(self.rate, 2),
                "fair_rate": None if self.fair_rate is None else round(self.fair_rate, 2),
                "fair_source": self.fair_source, "needed": None if self.needed is None
                else round(self.needed, 3), "fair_quantity": round(self.fair_quantity, 3),
                "extra": round(self.extra, 2), "sor_code": self.sor_code}


@dataclass
class Whole:
    verdict: str                     # "ASK" | "FAIR" | "CANT_CHECK"
    grand: float
    fair_grand: float
    gap: float
    gap_share: float
    coverage: float
    lines: list[Line] = field(default_factory=list)
    above_fair: int = 0
    priced: int = 0
    sources: list[str] = field(default_factory=list)
    sor_mismatch: list[dict] = field(default_factory=list)
    gaps: list[rates.Gap] = field(default_factory=list)        # not priced at all
    fallbacks: list[rates.Gap] = field(default_factory=list)   # priced from the state instead
    unexplained: dict = field(default_factory=dict)   # {"lump_sums", "other_charges", ...: Rs}

    def top(self) -> list[Line]:
        return sorted((x for x in self.lines if x.extra > 0), key=lambda x: -x.extra)[:TOP_LINES]

    def to_json(self) -> dict:
        return {"verdict": self.verdict, "grand_total": round(self.grand, 2),
                "fair_total": round(self.fair_grand, 2), "gap": round(self.gap, 2),
                "gap_share": round(self.gap_share, 4), "coverage": round(self.coverage, 4),
                "above_fair_rate": self.above_fair, "priced_lines": self.priced,
                "sources": self.sources, "sor_mismatch": self.sor_mismatch,
                "lines": [x.to_json() for x in self.lines],
                "data_gaps": [g.to_json() for g in self.gaps],
                "priced_from_state": [g.to_json() for g in self.fallbacks],
                "unexplained": {k: round(v, 2) for k, v in self.unexplained.items()},
                "rule": {"min_coverage": MIN_COVERAGE, "gap_share": GAP_SHARE,
                         "gap_min_rs": GAP_MIN_RS, "qty_tolerance": QTY_TOLERANCE}}


def _num(v) -> float:
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) \
        and math.isfinite(v) else 0.0


def _unread(ln) -> bool:
    """A priced line (not a lump sum) whose item no known material's name fits."""
    if not isinstance(ln, dict) or ln.get("unit") == "ls":
        return False
    item = ln.get("item") if isinstance(ln.get("item"), str) else None
    return not catalog.material(ln.get("material_id")) and not materials.match(item)


def _line_value(ln: dict) -> float:
    q, r = _num(ln.get("quantity")), _num(ln.get("rate"))
    return q * r if q > 0 and r > 0 else max(0.0, _num(ln.get("amount")))


def unexplained(form: dict, computed: dict, civil: bool) -> dict:
    """Money in the estimate that is not shown to be fair (module note), by kind."""
    lines_total = _num(computed.get("lines_total"))
    if lines_total <= 0:
        return {}
    out = {}
    if civil:
        ls = 0.0
        for site in form.get("sites") if isinstance(form.get("sites"), list) else []:
            for ln in (site.get("lines") or []) if isinstance(site, dict) else []:
                if isinstance(ln, dict) and ln.get("unit") == "ls":
                    ls += max(0.0, _num(ln.get("amount")))
        out["lump_sums"] = max(0.0, ls - LUMP_SHARE * lines_total)
        unread = sum(_line_value(ln) for site in form.get("sites") or [] if isinstance(site, dict)
                     for ln in site.get("lines") or [] if _unread(ln))
        out["unread_items"] = max(0.0, unread - UNREAD_SHARE * lines_total)
    charges = form.get("charges") if isinstance(form.get("charges"), dict) else {}
    taxed = any(isinstance(charges.get(k), (int, float)) for k in ("gst_percent", "gst_amount"))
    other = max(0.0, _num(charges.get("other_fees_amount")))
    out["other_charges"] = max(0.0, other - (OTHER_SHARE if taxed else OTHER_SHARE_NO_TAX)
                               * lines_total)
    cont = max(0.0, _num(computed.get("contingency_amount")))
    out["contingency"] = max(0.0, cont - CONTINGENCY_SHARE * lines_total)
    return {k: v for k, v in out.items() if v >= 1}


def judge(form: dict, computed: dict, work_type: str | None, sor: dict | None,
          index: rates.RateIndex | None, district, agency: str, work_id: str,
          when: date | None, state: str | None = None) -> Whole:
    grand = float(computed.get("grand_total") or 0.0)
    lines_total = float(computed.get("lines_total") or 0.0)
    sites = form.get("sites") if isinstance(form.get("sites"), list) else []
    confirmed = list(rates.confirmed_lines(form))

    # what each site's size needs, shared over the lines of that material in proportion
    stated: dict[tuple[int, str], float] = defaultdict(float)
    for i, _j, mid, _r, q, _ln in confirmed:
        stated[(i, mid)] += q
    need: dict[tuple[int, str], float] = {}
    for i, site in enumerate(sites):
        size = site.get("size") if isinstance(site, dict) else None
        for n in norms.needs(work_type, size if isinstance(size, dict) else {}):
            need[(i, n["material"])] = float(n["needed"])

    out: list[Line] = []
    mismatch: list[dict] = []
    sources: set[str] = set()
    gaps: dict[str, rates.Gap] = {}
    fallbacks: dict[str, rates.Gap] = {}
    for i, j, mid, r, q, ln in confirmed:
        fair, gap = rates.price_line(mid, ln, sor, index, district, agency, work_id, when, state)
        if gap:
            (fallbacks if fair else gaps).setdefault(mid, gap)
        total_need = need.get((i, mid))
        needed = (total_need * q / stated[(i, mid)]) if total_need is not None else None
        fair_q = q if needed is None else min(q, needed * QTY_TOLERANCE)
        if fair is None and needed is None:
            continue                      # not compared: counts at its own value
        mat = catalog.material(mid)
        code = ln.get("sor_code") if isinstance(ln.get("sor_code"), str) else None
        line = Line(i, j, mid, mat["label"], mat["units"][0], q, r,
                    fair.rate if fair else None, fair.source if fair else None,
                    fair.where if fair else None, needed, fair_q, code)
        out.append(line)
        if fair:
            sources.add(fair.where)
            if fair.source == "sor_code" and r > fair.rate * 1.005:
                mismatch.append({"site": i, "line": j, "code": code, "rate": round(r, 2),
                                 "sor_rate": round(fair.rate, 2), "unit": mat["units"][0]})

    compared = sum(x.amount for x in out)
    coverage = compared / lines_total if lines_total > 0 else 0.0
    civil = any(m in CIVIL for (_i, m) in need)
    extra = unexplained(form, computed, civil)
    lump = extra.get("lump_sums", 0.0) + extra.get("unread_items", 0.0)
    charged = extra.get("other_charges", 0.0) + extra.get("contingency", 0.0)
    fair_lines = lines_total - compared + sum(x.fair_amount for x in out) - lump
    fair_grand = (fair_lines * ((grand - charged) / lines_total) if lines_total > 0
                  else grand)
    gap = grand - fair_grand
    # the share of the fair price of what was priced (module note); the same as of the whole
    # fair estimate when everything is priced
    ratio = (grand - charged) / lines_total if lines_total > 0 else 1.0
    base = sum(x.fair_amount for x in out) * ratio
    share = gap / base if base > 0 else 0.0
    priced = [x for x in out if x.fair_rate is not None]
    above = sum(1 for x in priced if x.rate > x.fair_rate)
    if coverage < MIN_COVERAGE or not out:
        verdict = "CANT_CHECK"
    elif share >= GAP_SHARE and gap >= GAP_MIN_RS:
        verdict = "ASK"
    else:
        verdict = "FAIR"
    return Whole(verdict, grand, fair_grand, gap, share, coverage, out, above, len(priced),
                 sorted(sources), mismatch, list(gaps.values()), list(fallbacks.values()), extra)


def sentence(w: Whole, label: str = "this size of work in this district") -> str:
    """The officer's sentence for an ASK verdict."""
    parts = []
    for x in w.top():
        why = []
        if x.fair_rate is not None and x.rate > x.fair_rate:
            why.append(f"{_rs(x.rate)} a {x.unit} against {_rs(x.fair_rate)}")
        if x.needed is not None and x.quantity > x.needed * QTY_TOLERANCE:
            why.append(f"{catalog.quantity_text(x.quantity, x.unit)} where the size needs "
                       f"{x.needed:,.0f}")
        parts.append(f"{x.label.lower()} +{_rs(x.extra)}" + (f" ({'; '.join(why)})" if why else ""))
    of = ("" if w.coverage >= 0.995 else
          f", {w.gap_share:.0%} above the fair price of the {w.coverage:.0%} of the money that "
          "could be priced")
    text = (f"The estimate ({_rs(w.grand)}) is {_rs(w.gap)}"
            + (f" ({w.gap_share:.0%})" if not of else "")
            + f" above the fair price for {label} ({_rs(w.fair_grand)}){of}")
    words = {"lump_sums": f"lump sums beyond {LUMP_SHARE:.0%} of the lines",
             "other_charges": "'other' charges beyond the usual share",
             "contingency": f"contingency beyond {CONTINGENCY_SHARE:.0%}",
             "unread_items": f"items no reader can price beyond {UNREAD_SHARE:.0%} of the lines"}
    parts += [f"{words[k]} +{_rs(v)} (not itemised)" for k, v in w.unexplained.items()
              if k in words]
    text += f". Most of the gap: {', '.join(parts)}." if parts else "."
    if w.priced >= 3:
        text += (f" {w.above_fair} of the {w.priced} priced lines are above their fair rate.")
    for m in w.sor_mismatch[:2]:
        text += (f" A line cites SoR item {m['code']} at {_rs(m['rate'])} a {m['unit']}; that "
                 f"item's rate is {_rs(m['sor_rate'])}.")
    return text + " Needs checking before sanction."
