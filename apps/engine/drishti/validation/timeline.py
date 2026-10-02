"""Impossible dates, judged against how common the same mistake was at the time.

Ported from ~/saakshya/core/rules/lifecycle.py (T16 and T18), where it was measured.

A work recorded as completed before it was recommended has one wrong date. How much
that says about the WORK depends on when it was entered. When eSAKSHI opened (April
2023), offices bulk-entered works that were already finished, giving them a
recommendation date from the day of entry. Measured on the real export (2026-09-25):
1.28% of works with both dates carry the defect, but 2.22% of those recommended in
2023-Q3 and 1.77% in 2024-Q1, against 0.48% in 2024-Q3 and 0.15% in 2025-Q1.

So each case is compared with its own recommendation quarter:

  distinctiveness = min(1, national rate / quarter rate)

A case from a bulk-entry quarter (distinctiveness < 0.8) is a records note (risk 0.10).
A case from a quarter where the defect is no more common than nationally is individually
worth a check (risk 0.30, enough to enter the review queue on its own). In between, the
risk rises linearly and stays below the queue. Without this, 582 of the first 847 queued
works were bulk-entry artefacts, 85 of them from one office in one quarter.

A quarter with few works has its rate pulled toward the national rate (200 pseudo-works),
so eleven bad dates among 49 works read as a bulk-entry quarter, not as noise.

Offices where the defect is concentrated (at least 30 completed works, and a Wilson lower
bound at least 3x the national rate) are named in the note: that is a recording practice,
and the office's completion dates need checking as a whole (T18).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date

MIN_GAP_DAYS = 7
SHRINK_WORKS = 200
NOISY_BELOW = 0.8
NOISY_RISK = 0.10
CLEAN_RISK = 0.30
AGENCY_MIN_COMPLETED = 30
AGENCY_MIN_LIFT = 3.0


def quarter_of(d: date) -> str:
    return f"{d.year}-Q{(d.month - 1) // 3 + 1}"


def _wilson_lower(successes: int, trials: int, z: float = 1.96) -> float:
    if trials == 0:
        return 0.0
    p = successes / trials
    denom = 1 + z * z / trials
    centre = p + z * z / (2 * trials)
    margin = z * math.sqrt(p * (1 - p) / trials + z * z / (4 * trials * trials))
    return max(0.0, (centre - margin) / denom)


@dataclass(frozen=True)
class Concentration:
    bad: int
    completed: int
    rate: float
    lift: float


@dataclass
class TimelineRates:
    overall: float
    quarters: dict[str, tuple[int, int]] = field(default_factory=dict)
    agencies: dict[str, tuple[int, int]] = field(default_factory=dict)

    @classmethod
    def from_counts(cls, quarters: dict[str, tuple[int, int]],
                    agencies: dict[str, tuple[int, int]],
                    overall: tuple[int, int] | None = None) -> TimelineRates:
        n, bad = overall or (sum(v[0] for v in quarters.values()),
                             sum(v[1] for v in quarters.values()))
        return cls(overall=(bad / n) if n else 0.0, quarters=dict(quarters),
                   agencies=dict(agencies))

    def cohort_rate(self, quarter: str) -> float:
        n, bad = self.quarters.get(quarter, (0, 0))
        return (bad + self.overall * SHRINK_WORKS) / (n + SHRINK_WORKS)

    def distinctiveness(self, quarter: str) -> float:
        rate = self.cohort_rate(quarter)
        return 1.0 if rate <= 0 else min(1.0, self.overall / rate)

    def agency_concentration(self, agency: str | None) -> Concentration | None:
        if not agency or agency not in self.agencies or self.overall <= 0:
            return None
        completed, bad = self.agencies[agency]
        if completed < AGENCY_MIN_COMPLETED or bad == 0:
            return None
        if _wilson_lower(bad, completed) < self.overall * AGENCY_MIN_LIFT:
            return None
        rate = bad / completed
        return Concentration(bad=bad, completed=completed, rate=rate, lift=rate / self.overall)

    def concentrated_offices(self) -> list[dict]:
        """Every office whose completion dates need checking as a whole, worst first."""
        out = []
        for agency in self.agencies:
            c = self.agency_concentration(agency)
            if c:
                out.append({"agency_name": agency, "completed": c.completed, "bad": c.bad,
                            "rate": c.rate, "lift": c.lift})
        return sorted(out, key=lambda r: (-r["bad"], -r["lift"]))


def risk_for(distinctiveness: float) -> float:
    if distinctiveness < NOISY_BELOW:
        return NOISY_RISK
    span = (distinctiveness - NOISY_BELOW) / (1.0 - NOISY_BELOW)
    return min(CLEAN_RISK, NOISY_RISK + (CLEAN_RISK - NOISY_RISK) * span)


@dataclass(frozen=True)
class ImpossibleDate:
    gap_days: int
    risk: float
    message: str


def impossible_date(recommended: date | None, completed: date | None, agency: str | None,
                    rates: TimelineRates | None) -> ImpossibleDate | None:
    if not recommended or not completed or completed >= recommended:
        return None
    gap = (recommended - completed).days
    if gap < MIN_GAP_DAYS:
        return None
    msg = (f"Recorded as completed {gap:,} days before it was recommended; "
           "one of the two dates is wrong.")
    if rates is None:
        return ImpossibleDate(gap, CLEAN_RISK, msg + " Check the completion certificate.")
    q = quarter_of(recommended)
    d = rates.distinctiveness(q)
    rate = rates.cohort_rate(q)
    if rates.overall <= 0:
        # no other work carries the defect (a small or partial data set): no share to quote
        msg += (" No other work in the data carries this defect, so bulk entry does not explain "
                "it; check the completion certificate against the portal record.")
    elif d < NOISY_BELOW:
        msg += (f" {rate:.1%} of works recommended in {q} carry the same defect (against "
                f"{rates.overall:.2%} across the scheme), which points to bulk entry of works "
                "that were already finished rather than to this work; treat it as a records "
                "issue for the office.")
    else:
        msg += (f" Only {rate:.2%} of works recommended in {q} carry this defect (against "
                f"{rates.overall:.2%} across the scheme), so bulk entry does not explain it; "
                "check the completion certificate against the portal record.")
    risk = risk_for(d)
    c = rates.agency_concentration(agency)
    if c:
        # A recording practice is one finding about the office, listed once on the
        # dashboard - not one queue item per work (Nizamabad and Gandhinagar each put
        # about twenty such works in the first queue).
        msg += (f" This office recorded {c.bad} of {c.completed} completed works this way "
                f"({c.rate:.1%}, {c.lift:.0f} times the national rate), so its completion "
                "dates need checking as a whole.")
        risk = NOISY_RISK
    return ImpossibleDate(gap, risk, msg)
