"""How each office records its works, against the whole scheme (counted live, like the backlog).

An office is (district, implementing office). In the research export the office is the
implementing agency; in the eSAKSHI dashboard tables it is the implementing district authority
(IDA), the finest office those tables name. Built from the works given (the batch: all of them;
the API: the work's district against the batch's national rates), so a new recommendation meets
the same counts. Never an MP: offices only (AGENTS.md rule 5).

Two habits, each measured on the dashboard tables of 2 Oct 2026 (data/trial/dashboard_facts.py):

  priced just under a limit   96-100% of Rs 5 or 10 lakh, the limit itself not included (a whole
                              Rs 5,00,000 is round pricing). 42.6x more works sit just under
                              Rs 5 lakh than just over; one district authority priced 130 of its
                              141 works there. Amounts pile up below these sums nationally
                              (reference/rules.json split_limits).
  built right after sanction  a construction (not a purchase) recorded complete 0-7 days after its
                              sanction date: 7.1% of construction works nationally, 72% in one
                              office. A hall or road is not built in a week, so either it was built
                              before the sanction or the dates are wrong.

An office "does this routinely" when it has enough works (30 priced, 15 constructions with both
dates) and the lower Wilson bound of its share is at least three times the national share: the
same test validation/timeline.py uses for impossible dates (T18).
"""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from functools import cache
from pathlib import Path

from drishti import reference
from drishti.agents.statistical.scope import GOODS, scope
from drishti.validation.timeline import _wilson_lower

JUST_UNDER = 0.96            # share of a limit from which an amount counts as just under it
AFTER_SANCTION_DAYS = 7
MIN_PRICED, MIN_BUILT = 30, 15
MIN_LIFT = 3.0
# buildings, roads, drains, walls and other works built on site (not purchases)
CONSTRUCTION_TYPES = frozenset({
    "ROAD_CC", "ROAD_BT", "FOOTPATH", "CULVERT", "BRIDGE", "COMMUNITY_HALL", "SCHOOL_BUILDING",
    "HEALTH_BUILDING", "LIBRARY", "BOUNDARY_WALL", "TOILET_BLOCK", "DRAIN", "POND", "CHECK_DAM",
    "CREMATORIUM", "PLAYGROUND", "BUS_SHELTER", "EMBANKMENT", "WATER_SUPPLY"})


@cache
def limits() -> tuple[float, ...]:
    path = Path(reference.__file__).resolve().parent / "rules.json"
    return tuple(float(x) for x in json.loads(path.read_text(encoding="utf-8"))
                 ["split_limits"]["rupees"])


def limit_just_above(amount) -> float | None:
    """The limit an amount sits just under (96-100%, the limit itself excluded), else None."""
    try:
        a = float(amount or 0)
    except (TypeError, ValueError):
        return None
    for lim in limits():
        if JUST_UNDER * lim <= a < lim:
            return lim
    return None


def as_date(x) -> date | None:
    if x is None or isinstance(x, date):
        return x
    try:
        return date.fromisoformat(str(x)[:10])
    except ValueError:
        return None


def is_construction(work: dict) -> bool:
    return (work.get("work_type_code") in CONSTRUCTION_TYPES
            and scope(work.get("description")) != GOODS)


def days_after_sanction(work: dict) -> int | None:
    """Days from sanction to completion, for a completed work with both dates."""
    s, d = as_date(work.get("sanction_date")), as_date(work.get("completed_date"))
    if work.get("status") != "COMPLETED" or s is None or d is None:
        return None
    return (d - s).days


def built_right_after_sanction(work: dict) -> bool:
    lag = days_after_sanction(work)
    return lag is not None and lag <= AFTER_SANCTION_DAYS and is_construction(work)


@dataclass(frozen=True)
class Habit:
    count: int
    total: int
    share: float
    national: float
    lift: float
    routine: bool             # enough works, and the lower bound >= 3x the national share


@dataclass
class OfficeIndex:
    # (district, office) -> [works priced, of them just under a limit,
    #                        constructions with both dates, of them built right after sanction]
    offices: dict[tuple[str, str], list[int]] = field(default_factory=dict)
    national: list[int] = field(default_factory=lambda: [0, 0, 0, 0])

    @classmethod
    def build(cls, works) -> OfficeIndex:
        idx = cls(offices=defaultdict(lambda: [0, 0, 0, 0]))
        for w in works:
            key = cls.key(w)
            row = idx.offices[key] if key else None
            add = [0, 0, 0, 0]
            if float(w.get("amount") or 0) > 0:
                add[0] = 1
                add[1] = int(limit_just_above(w.get("amount")) is not None)
            lag = days_after_sanction(w)
            if lag is not None and is_construction(w):
                add[2] = 1
                add[3] = int(lag <= AFTER_SANCTION_DAYS)
            for i, v in enumerate(add):
                idx.national[i] += v
                if row is not None:
                    row[i] += v
        idx.offices = dict(idx.offices)
        return idx

    @staticmethod
    def key(work: dict) -> tuple[str, str] | None:
        office = work.get("agency_name")
        if not office:
            return None
        return (str(work.get("district_lgd") or "NA"), str(office))

    def covers(self, work: dict) -> bool:
        return self.key(work) in self.offices

    def _habit(self, work: dict, i: int, minimum: int) -> Habit | None:
        row = self.offices.get(self.key(work) or ("", ""))
        total, count = (row[i], row[i + 1]) if row else (0, 0)
        if total == 0 or self.national[i] == 0:
            return None
        nat = self.national[i + 1] / self.national[i]
        share = count / total
        routine = (total >= minimum and nat > 0
                   and _wilson_lower(count, total) >= MIN_LIFT * nat)
        return Habit(count=count, total=total, share=share, national=nat,
                     lift=(share / nat) if nat else 0.0, routine=routine)

    def limit_pricing(self, work: dict) -> Habit | None:
        return self._habit(work, 0, MIN_PRICED)

    def after_sanction(self, work: dict) -> Habit | None:
        return self._habit(work, 2, MIN_BUILT)

    def routine_offices(self) -> list[dict]:
        """Every office with a routine habit, for the dashboard: listed once, worst first."""
        out = []
        for district, office in self.offices:
            w = {"district_lgd": district, "agency_name": office}
            for name, h in (("priced just under a limit", self.limit_pricing(w)),
                            ("built right after sanction", self.after_sanction(w))):
                if h and h.routine:
                    out.append({"district_lgd": district, "office": office, "habit": name,
                                "count": h.count, "total": h.total, "share": round(h.share, 3),
                                "national": round(h.national, 4), "lift": round(h.lift, 1)})
        return sorted(out, key=lambda r: (-r["count"], -r["lift"]))
