"""Is an unfinished work taking far longer than works of its kind?

The norm is each work type's own 98th percentile of recommendation-to-
completion time on the real corpus, not the 90th: the median completion is
over a year, and at p90 a third of the scheme would be "late", which is a
description of MPLADS rather than a finding (old build, AD-47).
"""

from __future__ import annotations

from datetime import date

DELAY_RISK = 0.20


def delay_check(status: str | None, recommended: date | None, as_of: date,
                p98: float | None) -> dict | None:
    if status == "COMPLETED" or recommended is None or p98 is None:
        return None
    days = (as_of - recommended).days
    late = days > p98
    return {"verdict": "DELAYED" if late else "ON_TIME", "days": days, "norm_days": p98,
            "risk": DELAY_RISK if late else 0.0}
