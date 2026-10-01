"""Which vendors hold the certified works of a district (T110, from C3 Contractor Network).

The vendor's unique code on the certificate (V + 12 digits) is an exact identity: no name
matching, and no name is ever kept. Built from the evidence facts of every work given (the
batch: all works; the API: the work's district).
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field


@dataclass
class VendorIndex:
    by_district: dict[str, Counter] = field(default_factory=dict)

    @classmethod
    def build(cls, works) -> VendorIndex:
        from drishti.agents.paperwork.agent import belongs

        idx: dict[str, Counter] = defaultdict(Counter)
        for w in works:
            files = ((w.get("evidence") or {}).get("files")) or []
            codes = {c["vendor_code"] for f in files for c in f.get("certificates") or []
                     if c.get("vendor_code") and belongs(c, w)}
            for code in codes:
                idx[str(w.get("district_lgd") or "NA")][code] += 1
        return cls(by_district=dict(idx))

    def share(self, district, code: str) -> tuple[float, int]:
        c = self.by_district.get(str(district or "NA"))
        if not c:
            return 0.0, 0
        n = sum(c.values())
        return c[code] / n, n

    def summary(self, district) -> dict:
        c = self.by_district.get(str(district or "NA"), Counter())
        n = sum(c.values())
        top = c.most_common(3)
        return {"works": n, "vendors": len(c),
                "top_share": round(top[0][1] / n, 3) if n else 0.0,
                "top3_share": round(sum(k for _v, k in top) / n, 3) if n else 0.0}
