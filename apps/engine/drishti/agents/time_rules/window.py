"""The comfort window: when finishing is normal for this work (plan T120 §8.2, T122).

From the implementing agency's cost estimate form:
    timing.duration_months   "Estimated time to completion" (the field once called "Expected
                             duration"); timing.start_month the expected start;
    sites[].site_conditions.lost_months   months when work cannot happen (declared before sanction)

Step A, is the estimate believable for this kind and size of work?
    shortest believable time  reference/time_floors.json, per family of the form (construction only)
    longest usual time        reference/time_bands.json, the 90th percentile of days from
                              sanction to completion of finished works of the type (generous)
    shorter than the shortest -> the window uses the shortest; longer than the usual -> it uses the
    usual, so padding the estimate buys no time. Neither is a finding.

Step B, the window
    start       the later of the sanction date and the declared start month, or the first site
                video that shows work going on, if that is earlier (never before the sanction)
    early line  start + the later of the shortest believable time and a quarter of the accepted
                estimate (construction families only)
    late line   start + the accepted estimate + grace (half the estimate, at least 2 months)
                + the declared lost months + any extension the district recorded
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date, timedelta
from functools import cache
from pathlib import Path

from drishti import reference
from drishti.cost_form import catalog

MONTH_DAYS = 30.44
GRACE_SHARE = 0.5
GRACE_MIN_DAYS = 61
EARLY_SHARE = 0.25
REF = Path(reference.__file__).resolve().parent


@cache
def floors() -> dict:
    return json.loads((REF / "time_floors.json").read_text(encoding="utf-8"))


@cache
def bands() -> dict:
    return json.loads((REF / "time_bands.json").read_text(encoding="utf-8"))


def longest_usual(work_type: str | None) -> tuple[float, str]:
    """The 90th percentile of finished works of the type, or of all works for a rare type."""
    b = bands()
    row = (b.get("types") or {}).get(work_type or "")
    if row:
        return float(row["p90"]), f"9 in 10 of the {row['works']:,} finished works of this type"
    return float(b["all"]["p90"]), f"9 in 10 of all {b['all']['works']:,} finished works"


def floor_of(work_type: str | None) -> dict | None:
    fam = catalog.family_of(work_type)
    return (floors().get("families") or {}).get(fam[0]) if fam else None


def _num(v) -> float | None:
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) and v == v else None


def _month(v) -> date | None:
    if isinstance(v, str) and len(v) >= 7:
        try:
            y, m = int(v[:4]), int(v[5:7])
            return date(y, m, 1) if 1 <= m <= 12 and 1900 < y < 2200 else None
        except ValueError:
            return None
    return None


@dataclass
class Window:
    start: date
    estimate_days: float           # what the agency wrote
    accepted_days: float           # after step A
    shortest_days: float | None    # the physical minimum (construction families)
    longest_days: float
    early: date | None             # None: a fast finish is never asked about
    late: date
    grace_days: float
    lost_months: int
    extension_days: float
    notes: list[str] = field(default_factory=list)

    def to_json(self) -> dict:
        return {"start": self.start.isoformat(), "estimate_days": round(self.estimate_days),
                "accepted_days": round(self.accepted_days),
                "shortest_days": self.shortest_days, "longest_days": self.longest_days,
                "early": self.early.isoformat() if self.early else None,
                "late": self.late.isoformat(), "grace_days": round(self.grace_days),
                "lost_months": self.lost_months, "extension_days": self.extension_days,
                "notes": list(self.notes)}


def lost_months(form: dict) -> int:
    months: set[str] = set()
    sites = form.get("sites")
    for site in sites if isinstance(sites, list) else []:
        sc = site.get("site_conditions") if isinstance(site, dict) else None
        lm = sc.get("lost_months") if isinstance(sc, dict) else None
        months |= {m for m in lm if isinstance(m, str)} if isinstance(lm, list) else set()
    return len(months)


def window(form: dict | None, work_type: str | None, sanctioned: date | None,
           first_work_seen: date | None = None, extension_days: float = 0.0) -> Window | None:
    """The comfort window, or None when the form gives no estimate or there is no start."""
    if not isinstance(form, dict):
        return None
    timing = form.get("timing") if isinstance(form.get("timing"), dict) else {}
    months = _num(timing.get("duration_months"))
    if months is None or months <= 0:
        return None
    declared = _month(timing.get("start_month"))
    if sanctioned is None and declared is None:
        return None
    start = max(d for d in (sanctioned, declared) if d)
    if first_work_seen and first_work_seen < start:
        start = max(first_work_seen, sanctioned) if sanctioned else first_work_seen
    est = months * MONTH_DAYS
    fl = floor_of(work_type)
    shortest = float(fl["days"]) if fl else None
    longest, longest_why = longest_usual(work_type)
    notes = []
    accepted = est
    if shortest is not None and est < shortest:
        accepted = shortest
        notes.append(f"The estimate ({months:g} months) is shorter than the shortest believable "
                     f"time for this kind of work ({shortest:g} days); the window uses the "
                     "shortest.")
    elif est > longest:
        accepted = longest
        notes.append(f"The estimate ({months:g} months) is longer than {longest_why} took "
                     f"({longest:g} days); the window uses that, so a long estimate buys no "
                     "extra time.")
    grace = max(GRACE_SHARE * accepted, GRACE_MIN_DAYS)
    lost = lost_months(form)
    ext = max(0.0, float(extension_days or 0))
    late = start + timedelta(days=round(accepted + grace + lost * MONTH_DAYS + ext))
    early = (start + timedelta(days=round(max(shortest, EARLY_SHARE * accepted)))
             if shortest is not None else None)
    return Window(start, est, accepted, shortest, longest, early, late, grace, lost, ext, notes)
