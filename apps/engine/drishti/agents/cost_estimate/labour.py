"""Labour, trade by trade (T141; plan docs/plans/T141-labour-schedule.md).

The owner (6 Oct 2026): "we just need to detect blatant irregularities, none of the 'can still be
made with lower amount of workers' or 'doesn't need this many'". So how many workers, how many
days within the work's own time, and labour's share of the estimate are never judged. Two
questions only:

  LABOUR_RATE_FAR_ABOVE     a trade's day rate is at least RATE_MARGIN times what other agencies
                            pay that trade here (rates.py: the district's recent forms, else the
                            state's), or POOL_MARGIN times what they pay every trade of its grade
                            when the trade itself has too few forms; and the extra comes to at
                            least MIN_RS over the work. Within one district honest wages for one
                            trade differ by tens of percent, not double.
  LABOUR_DAYS_BEYOND_WORK   a row's days on site go more than 10% beyond the work's own time to
                            completion (the form asked the agency to confirm them), and the days
                            beyond it cost at least MIN_RS. No one works on a work longer than it
                            lasts.

A row is judged as its trade, never the grade it declares: a helper called "highly skilled" is
compared with helpers. A trade not on the list ("Other") is compared with its declared grade's
pool: the only place a declared grade counts, and only at the wider POOL_MARGIN. When its grade
has too few forms here, the nearest grade that has them stands in (a lower one with GRADE_STEP
more room for each grade between them). A labour line
outside the labour table is judged the same way when its trade was chosen, so moving labour among
the estimate lines escapes nothing. The margins are starting values: real forms (T098) set the
final ones, with the owner's go-ahead.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from datetime import date

from drishti.agents.cost_estimate import rates
from drishti.cost_form import catalog
from drishti.cost_form.norms import to_first_unit

RATE_MARGIN = 2.0           # a trade's day rate this many times what others pay that trade here
POOL_MARGIN = 2.5           # ... or this many times every trade of its grade (too few of its own)
GRADE_STEP = 1.25           # ... or of the nearest grade with forms: a grade above it may earn
                            # this much more a step (the loop: an "Other" trade declared at a
                            # grade nobody here files escaped every comparison; at 1.5 a step,
                            # masons at 2.4x went unasked where only labourers had forms)
MIN_RS = 10_000             # the extra over the whole work, below which nothing is asked
DAYS_TOLERANCE = 1.10       # validate.py asks beyond this; the money counts from the work's time
DAYS_A_MONTH = 30.44
RATE_RISK = 0.5
DAYS_RISK = 0.4
TOP = 3
_LINE = re.compile(r"sites\[(\d+)\]\.lines\[(\d+)\]")

HI_RATE = ("मज़दूरी की दर इस ज़िले में उसी काम के लिए दूसरी एजेंसियों की दर से {times} गुना है। "
           "स्वीकृति से पहले जाँच करें।")
HI_DAYS = ("मज़दूरों के साइट पर दिन काम की पूरी अवधि से अधिक दिखाए गए हैं। स्वीकृति से पहले जाँच "
           "करें।")


def _num(v) -> float | None:
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
        return None
    return float(v)


def _rs(v: float) -> str:
    return f"Rs {v / 1e5:,.2f} lakh" if abs(v) >= 1e5 else f"Rs {v:,.0f}"


@dataclass
class Row:
    """One labour row (or a labour line among the estimate lines), per day."""
    site: int
    line: int
    trade: str | None          # the chosen trade, None for a trade not on the list
    grade: str
    label: str
    rate: float                # Rs a day
    person_days: float
    workers: float | None
    days: float | None
    fair: float | None = None
    margin: float | None = None
    level: str | None = None   # "trade" | "grade" (its grade's pool) | "other_grade"
    where: str | None = None
    pool: str | None = None    # the grade whose pool gave the fair rate

    @property
    def times(self) -> float | None:
        return self.rate / self.fair if self.fair else None

    @property
    def extra(self) -> float:
        return (self.rate - self.fair) * self.person_days if self.fair else 0.0

    def to_json(self) -> dict:
        return {"site": self.site, "line": self.line, "trade": self.trade, "grade": self.grade,
                "label": self.label, "rate": round(self.rate, 2),
                "person_days": round(self.person_days, 2), "workers": self.workers,
                "days": self.days,
                "fair_rate": None if self.fair is None else round(self.fair, 2),
                "times": None if self.times is None else round(self.times, 3),
                "margin": self.margin, "level": self.level, "where": self.where,
                "pool": self.pool,
                "extra": round(self.extra, 2)}


@dataclass
class Beyond:
    """A row whose days on site go beyond the work's own time."""
    row: Row
    work_days: float
    cost: float                # the days beyond the work's time x workers x rate
    confirmed: bool


@dataclass
class Labour:
    rows: list[Row] = field(default_factory=list)
    asked: list[Row] = field(default_factory=list)
    beyond: list[Beyond] = field(default_factory=list)
    grade_above: list[str] = field(default_factory=list)

    @property
    def compared(self) -> list[Row]:
        return [r for r in self.rows if r.fair]

    def to_json(self) -> dict:
        return {"rows": [r.to_json() for r in self.rows],
                "asked": [[r.site, r.line] for r in self.asked],
                "beyond": [{"site": b.row.site, "line": b.row.line, "days": b.row.days,
                            "work_days": round(b.work_days, 1), "cost": round(b.cost, 2),
                            "confirmed": b.confirmed} for b in self.beyond],
                "rule": {"rate_margin": RATE_MARGIN, "pool_margin": POOL_MARGIN,
                         "min_rs": MIN_RS, "days_tolerance": DAYS_TOLERANCE}}


def _s(v) -> str:
    return v.strip() if isinstance(v, str) else ""


def rows(form: dict, held=()) -> list[Row]:
    """Every labour row with a day rate and person-days; `held` lines (a rate that looks like a
    typing mistake, not answered yet) are left out until answered."""
    out = []
    sites = form.get("sites") if isinstance(form.get("sites"), list) else []
    for i, site in enumerate(sites):
        lines = site.get("lines") if isinstance(site, dict) else None
        for j, ln in enumerate(lines if isinstance(lines, list) else []):
            if not isinstance(ln, dict) or (i, j) in held:
                continue
            chosen = _s(ln.get("material_id"))
            trade = chosen if catalog.is_labour(chosen) else None
            if not trade and ln.get("group") != "labour":
                continue
            grade = catalog.grade_of(trade) if trade else _s(ln.get("grade"))
            if grade not in catalog.GRADES:
                continue
            unit_of = trade or catalog.grade_entry(grade)
            rate = rates.per_unit(unit_of, ln.get("rate"), ln.get("unit"))
            if rate is None or rate <= 0:
                continue
            w, d = _num(ln.get("workers")), _num(ln.get("days"))
            q = to_first_unit(unit_of, ln.get("quantity"), ln.get("unit"))
            if q is None and ln.get("quantity") in (None, ""):
                q = catalog.person_days(ln)
            if q is None or q <= 0:
                continue
            label = (catalog.material(trade)["label"] if trade else
                     f"{_s(ln.get('item')) or 'another trade'} "
                     f"({catalog.GRADE_WORDS[grade]})")
            out.append(Row(i, j, trade, grade, label, rate, q, w, d))
    return out


def _price(row: Row, ln: dict, sor, index, district, agency, work_id, when, state) -> None:
    if row.trade:
        fair, _gap = rates.price_line(row.trade, ln, sor, index, district, agency, work_id,
                                      when, state)
        if fair:
            row.fair, row.margin, row.level, row.where = fair.rate, RATE_MARGIN, "trade", fair.where
            return
    if index is None:
        return
    own = catalog.GRADES.index(row.grade)
    # its own grade, then the nearest grades (a higher one first: it earns at least as much)
    for g in sorted(catalog.GRADES, key=lambda g: (abs(catalog.GRADES.index(g) - own),
                                                  catalog.GRADES.index(g) < own)):
        found, _gap = index.price(district, state, rates.pool_key(g), agency, work_id, when)
        if found:
            below = max(0, own - catalog.GRADES.index(g))
            row.fair, row.where, row.pool = found[0], found[2], g
            row.margin = POOL_MARGIN * GRADE_STEP ** below
            row.level = "grade" if g == row.grade else "other_grade"
            return


def judge(form: dict, issues: list[dict], confirmed: set, sor, index, district, agency: str,
          work_id: str, when: date | None, state: str | None, held=()) -> Labour:
    out = Labour(rows=rows(form, held))
    sites = form.get("sites") or []
    for row in out.rows:
        ln = sites[row.site]["lines"][row.line]
        _price(row, ln, sor, index, district, agency, work_id, when, state)
        if row.fair and row.rate >= row.margin * row.fair and row.extra >= MIN_RS:
            out.asked.append(row)
    out.asked.sort(key=lambda r: -r.extra)

    timing = form.get("timing") if isinstance(form.get("timing"), dict) else {}
    months = _num(timing.get("duration_months"))
    by_place = {(r.site, r.line): r for r in out.rows}
    for issue in issues:
        code = issue.get("code")
        m = _LINE.match(issue.get("field") or "")
        row = by_place.get((int(m[1]), int(m[2]))) if m else None
        if not row:
            continue
        if code == "labour_grade_above_trade":
            out.grade_above.append(row.label.lower())
        elif code == "labour_days_beyond_work" and months and row.days and row.workers:
            work_days = months * DAYS_A_MONTH
            cost = (row.days - work_days) * row.workers * row.rate
            if cost >= MIN_RS:
                out.beyond.append(Beyond(row, work_days, cost, issue["key"] in confirmed))
    out.beyond.sort(key=lambda b: -b.cost)
    return out


def rate_sentence(lab: Labour) -> str:
    parts = []
    for r in lab.asked[:TOP]:
        whose = (f"the rate for {r.label.lower()} on {r.where}" if r.level == "trade" else
                 f"the rate for any {catalog.GRADE_WORDS[r.pool]} trade on {r.where}")
        parts.append(f"{r.label.lower()} at {_rs(r.rate)} a day, {r.times:.1f} times "
                     f"{_rs(r.fair)} ({whose}): {_rs(r.extra)} more over "
                     f"{r.person_days:,.0f} person-days")
    more = len(lab.asked) - TOP
    return ("Labour: " + "; ".join(parts) + (f"; and {more} more" if more > 0 else "")
            + ". How many workers and days a work needs is not judged, only the day rate. "
            "Please check the wages before sanction.")


def days_sentence(lab: Labour) -> str:
    parts = []
    for b in lab.beyond[:TOP]:
        r = b.row
        parts.append(f"{r.label.lower()} ({r.workers:g} on site {r.days:g} days each, the days "
                     f"beyond the work's time costing {_rs(b.cost)})")
    work_days = lab.beyond[0].work_days
    said = all(b.confirmed for b in lab.beyond[:TOP])
    return ("Labour on site longer than the whole work lasts (about "
            f"{work_days:,.0f} days): " + "; ".join(parts) + ". "
            + ("The agency confirmed the days when filling the form. " if said else
               "The form asked the agency to confirm the days, and it has not. ")
            + "Please check the labour days before sanction.")
