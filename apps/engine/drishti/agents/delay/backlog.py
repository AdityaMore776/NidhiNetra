"""How many of an office's recommendations are still waiting for sanction (T410, from C2).

Built from the works given (the batch: all; the API: the work's district), so an office is
compared with its own district, the same way in both. Counts are taken at the assessment date:
only recommendations older than the sanction clock count.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date

from drishti.records import day


def norm(x) -> str:
    """Text compared the way a person reads it: case and spacing ignored."""
    return " ".join(str(x or "").split()).lower()


@dataclass
class OfficeBacklog:
    # (district, office) -> [(recommended_date, still_waiting)]
    offices: dict[tuple[str, str], list[tuple[date, bool]]] = field(default_factory=dict)
    districts: dict[str, list[tuple[date, bool]]] = field(default_factory=dict)

    @classmethod
    def build(cls, works) -> OfficeBacklog:
        off: dict = defaultdict(list)
        dis: dict = defaultdict(list)
        for w in works:
            rec = day(w.get("recommended_date"))
            if rec is None:
                continue
            d = str(w.get("district_lgd") or "NA")
            item = (rec, norm(w.get("status")) == "recommended")
            dis[d].append(item)
            if w.get("agency_name"):
                off[(d, str(w["agency_name"]))].append(item)
        return cls(offices=dict(off), districts=dict(dis))

    @staticmethod
    def _count(items, as_of: date, clock: int) -> tuple[int, int]:
        old = [waiting for rec, waiting in items if (as_of - rec).days > clock]
        return sum(old), len(old)

    def office(self, district, office, as_of: date, clock: int) -> tuple[int, int]:
        return self._count(self.offices.get((str(district or "NA"), str(office or "")), ()),
                           as_of, clock)

    def district(self, district, as_of: date, clock: int) -> tuple[int, int]:
        return self._count(self.districts.get(str(district or "NA"), ()), as_of, clock)
