"""Fair rates for each line of an estimate (T121, plan T120 §6.3), in this order:

1. The state's Schedule of Rates (SoR): reference/cost/sor/<state>.json, digitised by T096
   {"state", "edition", "source", "allowance",
    "items":     {"<SoR code>": {"material_id", "unit", "rate", "label"}},
    "materials": {"<material_id>": {"unit", "rate"}}}
   A line that cites an SoR code is held to that code's own rate: a fact check, not a judgement.
2. The district's own recent rates: what OTHER implementing agencies in the same district entered
   for the same confirmed material on submitted forms in the last 6 months, counted only with
   5+ forms from 3+ agencies, never the agency's own. Capped by the SoR (rate x (1 + allowance))
   when the SoR has the material, so agencies raising rates together cannot lift their baseline.
3. The state's recent rates (T135): when the district has too few forms, or they disagree, the
   other agencies' forms across the state, with 8+ forms from 4+ agencies, plus STATE_ALLOWANCE
   for local price differences (so a state-wide rate never asks where the district's would not).
4. None: the line is "not compared" and counts in the total at its own value, and the gap is
   recorded (`Gap`: which material, where, why: no forms, too few, too old, too spread) so the
   team knows which price data to collect. Never a guess.

Robustness (T135, data/trial/agent_robustness_loop.py):
  - one agency, one vote: the fair rate is the median of each agency's own median, so an agency
    filing ten forms counts once (it cannot drag the district's price up or down);
  - the agencies must agree: when the spread of their medians (interquartile range / median) is
    above MAX_SPREAD, the district's prices are not a fair rate for that material;
  - an agency is one agency however its name is written ("Gramin Path Nigam, Div-1" and
    "GRAMIN PATH NIGAM (Division 2)" are one, agency_key), so variants never count as others.

Every rate is per the material's first unit (cost_form.yaml `materials[].units[0]`).
"""

from __future__ import annotations

import json
import math
import re
import statistics
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from functools import cache
from pathlib import Path

from drishti import reference
from drishti.agents.cost_estimate.reference import slug
from drishti.cost_form import catalog, materials
from drishti.cost_form.norms import to_first_unit

SOR_DIR = Path(reference.__file__).resolve().parent / "cost" / "sor"
SOR_ALLOWANCE = 0.15          # the district band may sit at most this far above the SoR rate
MIN_FORMS, MIN_AGENCIES = 5, 3
RECENT_DAYS = 183
MAX_SPREAD = 0.30             # interquartile range of the agencies' medians / their median
STATE_MIN_FORMS, STATE_MIN_AGENCIES = 8, 4
STATE_ALLOWANCE = 0.10        # a state-wide rate is this much more lenient than a district's
# words that name a branch of an agency, not another agency
_BRANCH = {"the", "of", "and", "office", "offices", "division", "div", "dvn", "divn", "dept",
           "deptt", "department", "circle", "sub", "subdivision", "unit", "zone", "branch", "no",
           "ltd", "limited", "pvt", "private", "co", "i", "ii", "iii", "iv", "v", "vi", "vii",
           "viii", "ix", "x"}


def _num(v) -> float | None:
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
        return None
    return float(v)


def per_unit(material_id: str | None, rate, unit) -> float | None:
    """A line's rate per the material's first unit, or None."""
    mat = catalog.material(material_id) if material_id else None
    r = _num(rate)
    if not mat or r is None or r < 0 or not isinstance(unit, str) or unit == "ls":
        return None
    return materials.per_first_unit(mat, r, unit)


@cache
def load_sor(state: str | None) -> dict | None:
    p = SOR_DIR / f"{slug(state)}.json"
    return json.loads(p.read_text(encoding="utf-8")) if state and p.exists() else None


def sor_rate(sor: dict | None, material_id: str,
             code: str | None = None) -> tuple[float, str] | None:
    """(rate per first unit, where from) from the SoR: the cited code first, else the material."""
    if not sor:
        return None
    if code:
        item = (sor.get("items") or {}).get(code)
        if isinstance(item, dict) and item.get("material_id") == material_id:
            r = per_unit(material_id, item.get("rate"), item.get("unit"))
            if r is not None:
                return r, f"SoR item {code} ({sor.get('edition', 'current edition')})"
    m = (sor.get("materials") or {}).get(material_id)
    if isinstance(m, dict):
        r = per_unit(material_id, m.get("rate"), m.get("unit"))
        if r is not None:
            return r, f"the Schedule of Rates ({sor.get('edition', 'current edition')})"
    return None


def _form_month(form: dict, fallback) -> date | None:
    t = form.get("timing") if isinstance(form.get("timing"), dict) else {}
    m = t.get("estimate_month")
    # the website's form asks no price month: the day the agency filed it stands in (T134)
    for v in (m, form.get("filed_on")):
        if isinstance(v, str) and len(v) >= 7:
            try:
                return date(int(v[:4]), int(v[5:7]), 1)
            except ValueError:
                pass
    return fallback if isinstance(fallback, date) else None


def agency_key(name: str) -> str:
    """An agency's name with its branch words, numbers and punctuation set aside, so the ways
    one agency writes its name read as one agency."""
    words = [t for t in re.split(r"[^0-9a-z\u0900-\u097f]+", name.lower()) if t]
    keep = sorted({t for t in words if t not in _BRANCH and not t.isdigit()})
    return " ".join(keep) or " ".join(words) or name.strip().lower()


def agency_of(work: dict) -> str:
    """Who filed the form: the account that submitted it, else the implementing agency the form
    names (agency_key), else the work itself. An agency never counts in its own baseline."""
    meta = work.get("cost_form_meta") if isinstance(work.get("cost_form_meta"), dict) else {}
    v = meta.get("saved_by")
    if isinstance(v, str) and v.strip():
        return v.strip().lower()
    v = work.get("agency_name")
    if isinstance(v, str) and v.strip():
        return agency_key(v)
    return str(work.get("work_id"))


def confirmed_lines(form: dict):
    """(site index, line index, material id, rate per first unit, quantity per first unit,
    line dict) for every line whose material the agency CONFIRMED and which has a rate."""
    sites = form.get("sites") if isinstance(form.get("sites"), list) else []
    for i, site in enumerate(sites):
        lines = site.get("lines") if isinstance(site, dict) else None
        for j, ln in enumerate(lines if isinstance(lines, list) else []):
            if not isinstance(ln, dict):
                continue
            mid = ln.get("material_id")
            if not isinstance(mid, str) or mid in ("", "none") or not catalog.material(mid):
                continue
            r = per_unit(mid, ln.get("rate"), ln.get("unit"))
            if r is None:
                continue
            q = to_first_unit(mid, ln.get("quantity"), ln.get("unit"))
            if q is None or q <= 0:
                continue
            yield i, j, mid, r, q, ln


@dataclass
class Vote:
    """Other agencies' recent rates for one material in one place."""
    rate: float | None        # the median of the agencies' own medians
    forms: int
    agencies: int
    spread: float | None      # interquartile range of the agencies' medians / their median
    older: int                # forms left out for being older than RECENT_DAYS


def _vote(rows: list[tuple], agency: str, work_id: str, when: date | None) -> Vote:
    def recent(x):
        return when is None or x[3] is None or 0 <= (when - x[3]).days <= RECENT_DAYS
    own = {agency, agency_key(agency)} if isinstance(agency, str) else {agency}
    others = [x for x in rows if x[0] not in own and x[1] != work_id]
    keep = [x for x in others if recent(x)]
    by_agency: dict[str, list[float]] = defaultdict(list)
    for x in keep:
        by_agency[x[0]].append(x[2])
    meds = sorted(statistics.median(v) for v in by_agency.values())
    rate = statistics.median(meds) if meds else None
    spread = None
    if len(meds) >= 2 and rate:
        q1, _, q3 = statistics.quantiles(meds, n=4, method="inclusive")
        spread = (q3 - q1) / rate
    return Vote(rate, len({x[1] for x in keep}), len(meds), spread,
                len({x[1] for x in others}) - len({x[1] for x in keep}))


@dataclass
class Gap:
    """A material that could not be priced fairly here, and why (recorded to collect)."""
    material: str
    reason: str               # "none" | "too_few" | "too_old" | "too_spread"
    forms: int
    agencies: int
    spread: float | None
    where: str

    def to_json(self) -> dict:
        return {"material": self.material, "reason": self.reason, "forms": self.forms,
                "agencies": self.agencies,
                "spread": None if self.spread is None else round(self.spread, 3),
                "where": self.where,
                "needed": f"{MIN_FORMS}+ recent forms from {MIN_AGENCIES}+ other agencies whose "
                          f"rates agree (spread at most {MAX_SPREAD:.0%})"}

    def text(self) -> str:
        label = (catalog.material(self.material) or {}).get("label", self.material).lower()
        if self.reason == "too_spread":
            return (f"{label} (the {self.agencies} other agencies' rates disagree: spread "
                    f"{self.spread:.0%})")
        if self.reason == "too_old":
            return f"{label} (the other agencies' forms are over 6 months old)"
        if self.reason == "too_few":
            return (f"{label} ({self.forms} recent forms from {self.agencies} other agencies; "
                    f"{MIN_FORMS} from {MIN_AGENCIES} needed)")
        return f"{label} (no other agency's form yet)"


@dataclass
class RateIndex:
    """The confirmed rates on every submitted form, by (district, material) and by (state,
    material): (agency, work id, rate per first unit, month)."""
    by_key: dict[tuple[str, str], list[tuple[str, str, float, date | None]]] = field(
        default_factory=dict)
    by_state: dict[tuple[str, str], list[tuple[str, str, float, date | None]]] = field(
        default_factory=dict)

    @classmethod
    def build(cls, works) -> RateIndex:
        out: dict[tuple[str, str], list] = defaultdict(list)
        state: dict[tuple[str, str], list] = defaultdict(list)
        for w in works:
            form = w.get("cost_form")
            d = w.get("district_lgd")
            if not isinstance(form, dict) or not d:
                continue
            agency = agency_of(w)
            month = _form_month(form, (w.get("cost_form_meta") or {}).get("submitted_on"))
            st = _state(w)
            for _i, _j, mid, r, _q, _ln in confirmed_lines(form):
                row = (agency, str(w.get("work_id")), r, month)
                out[(str(d), mid)].append(row)
                if st:
                    state[(st, mid)].append(row)
        return cls(dict(out), dict(state))

    def district_rate(self, district, material_id: str, agency: str, work_id: str,
                      when: date | None) -> tuple[float, int, int] | None:
        """(fair rate, forms, agencies) from other agencies' recent forms in the district, or
        None: too few, or their rates disagree (module note)."""
        v = _vote(self.by_key.get((str(district), material_id), []), agency, work_id, when)
        if (v.rate is None or v.forms < MIN_FORMS or v.agencies < MIN_AGENCIES
                or (v.spread is not None and v.spread > MAX_SPREAD)):
            return None
        return v.rate, v.forms, v.agencies

    def price(self, district, state: str | None, material_id: str, agency: str, work_id: str,
              when: date | None) -> tuple[tuple[float, str, str] | None, Gap | None]:
        """((rate, "district" | "state", where), None), or (None, the gap)."""
        v = _vote(self.by_key.get((str(district), material_id), []), agency, work_id, when)
        enough = v.rate is not None and v.forms >= MIN_FORMS and v.agencies >= MIN_AGENCIES
        if enough and (v.spread is None or v.spread <= MAX_SPREAD):
            return (v.rate, "district", f"{v.forms} recent forms of {v.agencies} other agencies "
                    "in the district"), None
        reason = ("too_spread" if enough else "too_old" if not v.forms and v.older
                  else "too_few" if v.forms else "none")
        gap = Gap(material_id, reason, v.forms, v.agencies, v.spread, "the district")
        if state:
            s = _vote(self.by_state.get((state, material_id), []), agency, work_id, when)
            if (s.rate is not None and s.forms >= STATE_MIN_FORMS
                    and s.agencies >= STATE_MIN_AGENCIES
                    and (s.spread is None or s.spread <= MAX_SPREAD)):
                return (s.rate * (1 + STATE_ALLOWANCE), "state",
                        f"{s.forms} recent forms of {s.agencies} other agencies across the "
                        f"state, plus {STATE_ALLOWANCE:.0%} for local prices"), gap
        return None, gap


# the materials every construction district needs prices for, listed even before any form
CORE = ("cement", "sand", "aggregate", "steel_rebar", "brick", "granular_base",
        "labour_skilled", "labour_unskilled")


def coverage(index: RateIndex | None, district, state: str | None, when: date | None,
             sor: dict | None = None) -> list[dict]:
    """For each material: where its fair rate comes from here (the SoR, the district's forms,
    the state's), or the gap and what would close it. The team's list of price data to collect
    (T135: a price the agent cannot trust is switched off, and learned from here; every form
    an agency files joins the index, so a gap closes by itself once enough agree)."""
    seen = set(CORE)
    if index is not None:
        seen |= {m for (d, m) in index.by_key if d == str(district)}
        seen |= {m for (s, m) in index.by_state if s == state}
    out = []
    for m in sorted(x for x in seen if catalog.material(x)):
        sor_row = sor_rate(sor, m)
        found, gap = (index.price(district, state, m, "", "", when) if index is not None
                      else (None, Gap(m, "none", 0, 0, None, "the district")))
        row = {"material": m, "label": catalog.material(m)["label"],
               "unit": catalog.material(m)["units"][0]}
        if sor_row:
            row.update(source="sor", rate=round(sor_row[0], 2), where=sor_row[1])
        elif found:
            row.update(source=found[1], rate=round(found[0], 2), where=found[2])
        else:
            row.update(source=None, rate=None, where=None)
        row["gap"] = gap.to_json() if gap and not sor_row else None
        out.append(row)
    return out


def _state(w: dict) -> str | None:
    for k in ("state_lgd", "state_name"):
        v = w.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip().lower()
        if isinstance(v, int) and not isinstance(v, bool):
            return str(v)
    return None


@dataclass
class Fair:
    rate: float
    source: str           # "sor_code" | "sor" | "district"
    where: str


def fair_rate(material_id: str, line: dict, sor: dict | None, index: RateIndex | None,
              district, agency: str, work_id: str, when: date | None,
              state: str | None = None) -> Fair | None:
    return price_line(material_id, line, sor, index, district, agency, work_id, when, state)[0]


def price_line(material_id: str, line: dict, sor: dict | None, index: RateIndex | None,
               district, agency: str, work_id: str, when: date | None,
               state: str | None = None) -> tuple[Fair | None, Gap | None]:
    """The line's fair rate (module note), and the gap when the forms could not give one."""
    code = line.get("sor_code") if line.get("basis") == "sor" else None
    code = code.strip() if isinstance(code, str) and code.strip() else None
    s = sor_rate(sor, material_id, code)
    if s and code and s[1].startswith("SoR item"):
        return Fair(s[0], "sor_code", s[1]), None          # held to the code it cites
    if index is None:
        found, gap = None, Gap(material_id, "none", 0, 0, None, "the district")
    else:
        found, gap = index.price(district, state, material_id, agency, work_id, when)
    if found:
        rate, level, where = found
        if s and rate > s[0] * (1 + SOR_ALLOWANCE):
            return Fair(s[0] * (1 + SOR_ALLOWANCE), "sor",
                        f"{s[1]} plus {SOR_ALLOWANCE:.0%} (the forms' own rate is higher)"), None
        return Fair(rate, level, where), None if level == "district" else gap
    if s:
        return Fair(s[0], "sor", s[1]), None
    return None, gap
