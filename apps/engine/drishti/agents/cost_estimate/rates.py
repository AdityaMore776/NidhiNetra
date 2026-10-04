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
3. None: the line is "not compared" and counts in the total at its own value.

Every rate is per the material's first unit (cost_form.yaml `materials[].units[0]`).
"""

from __future__ import annotations

import json
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


def _num(v) -> float | None:
    if isinstance(v, bool) or not isinstance(v, (int, float)) or v != v:
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
    if isinstance(m, str) and len(m) >= 7:
        try:
            return date(int(m[:4]), int(m[5:7]), 1)
        except ValueError:
            pass
    return fallback if isinstance(fallback, date) else None


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
class RateIndex:
    """The confirmed rates on every submitted form, by (district, material)."""
    by_key: dict[tuple[str, str], list[tuple[str, str, float, date | None]]] = field(
        default_factory=dict)

    @classmethod
    def build(cls, works) -> RateIndex:
        out: dict[tuple[str, str], list] = defaultdict(list)
        for w in works:
            form = w.get("cost_form")
            d = w.get("district_lgd")
            if not isinstance(form, dict) or not d:
                continue
            agency = str((w.get("cost_form_meta") or {}).get("saved_by") or w.get("work_id"))
            month = _form_month(form, (w.get("cost_form_meta") or {}).get("submitted_on"))
            for _i, _j, mid, r, _q, _ln in confirmed_lines(form):
                out[(str(d), mid)].append((agency, str(w.get("work_id")), r, month))
        return cls(dict(out))

    def district_rate(self, district, material_id: str, agency: str, work_id: str,
                      when: date | None) -> tuple[float, int, int] | None:
        """(median rate, forms, agencies) from other agencies' recent forms, or None."""
        rows = [x for x in self.by_key.get((str(district), material_id), [])
                if x[0] != agency and x[1] != work_id
                and (when is None or x[3] is None or 0 <= (when - x[3]).days <= RECENT_DAYS)]
        forms = {x[1] for x in rows}
        agencies = {x[0] for x in rows}
        if len(forms) < MIN_FORMS or len(agencies) < MIN_AGENCIES:
            return None
        return statistics.median(x[2] for x in rows), len(forms), len(agencies)


@dataclass
class Fair:
    rate: float
    source: str           # "sor_code" | "sor" | "district"
    where: str


def fair_rate(material_id: str, line: dict, sor: dict | None, index: RateIndex | None,
              district, agency: str, work_id: str, when: date | None) -> Fair | None:
    code = line.get("sor_code") if line.get("basis") == "sor" else None
    code = code.strip() if isinstance(code, str) and code.strip() else None
    s = sor_rate(sor, material_id, code)
    if s and code and s[1].startswith("SoR item"):
        return Fair(s[0], "sor_code", s[1])          # held to the code it cites
    d = index.district_rate(district, material_id, agency, work_id, when) if index else None
    if d:
        rate, forms, agencies = d
        where = f"{forms} recent forms of {agencies} other agencies in the district"
        if s and rate > s[0] * (1 + SOR_ALLOWANCE):
            return Fair(s[0] * (1 + SOR_ALLOWANCE), "sor",
                        f"{s[1]} plus {SOR_ALLOWANCE:.0%} (the district's own rate is higher)")
        return Fair(rate, "district", where)
    if s:
        return Fair(s[0], "sor", s[1])
    return None
