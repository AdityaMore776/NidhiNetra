"""The peer-cost band: is this amount unusual for works of its type and place?

Measured on the real corpus (AD-106, 2026-09-09), and reproduced exactly by
data/build_stats.py:

  The spread is the p10-p90 range, NOT the median absolute deviation. 36.9%
  of sanctions are exact multiples of one lakh, so in many cohorts over half
  the works share one value and the MAD collapses; a robust z against it
  scored ordinary works at z = 50 and flagged 6.28% of the corpus.

  The spread is shrunk toward the work type's own spread, so a thin cohort
  cannot invent precision: sd = (n*sd_raw + K*sd_type) / (n + K), K = 12.

  z >= 3 flags 1.20% of assessable works after the bundle gate.

A cohort median is not a schedule of rates (AD-107), so every verdict here is
SOFT and capped at 0.45: it can say an amount is unusual, not that it is wrong.
"""

from __future__ import annotations

from dataclasses import dataclass

MIN_COHORT = 20
SHRINK_K = 12.0
P10_P90_SD = 2.563          # p90 - p10 spans 2.563 sd under a normal law
SD_FLOOR = 0.10
Z_FLAG = 3.0
SOFT_CAP = 0.45

LEVEL_WORDS = {
    "type_district": "works of the same type in this district",
    "type_state": "works of the same type in this state",
    "type": "works of this type across the scheme",
}


@dataclass(frozen=True)
class Cohort:
    level: str
    n: int
    p10: float      # all on log10(rupees)
    p50: float
    p90: float
    sd: float

    @property
    def description(self) -> str:
        return LEVEL_WORDS.get(self.level, self.level)

    def range_inr(self) -> tuple[float, float]:
        return 10 ** self.p10, 10 ** self.p90

    def median_inr(self) -> float:
        return 10 ** self.p50


def shrunk_sd(n: int, p10: float, p90: float, sd_type: float) -> float:
    sd_raw = (p90 - p10) / P10_P90_SD
    return max(SD_FLOOR, (n * sd_raw + SHRINK_K * sd_type) / (n + SHRINK_K))


def zscore(amount: float, cohort: Cohort) -> float:
    import math

    return (math.log10(amount) - cohort.p50) / cohort.sd


def cost_verdict(z: float, bundle: bool) -> str:
    if abs(z) < Z_FLAG:
        return "COST_TYPICAL"
    if bundle:
        # Many units under one work id, or a mispriced work: the description
        # suggests the first, and the verdict says so without asserting either.
        return "BUNDLED_SANCTION"
    return "COST_ABOVE_PEERS" if z > 0 else "COST_BELOW_PEERS"


def cost_risk(z: float, verdict: str | None = None) -> float:
    verdict = verdict or cost_verdict(z, bundle=False)
    if verdict == "BUNDLED_SANCTION":
        return 0.15
    if verdict == "COST_BELOW_PEERS":
        return 0.10   # under-costing tends to precede a revision, worth a look, no more
    if verdict != "COST_ABOVE_PEERS" or z < Z_FLAG:
        return 0.0
    if z <= 4.0:
        return 0.30 + 0.10 * (z - 3.0)
    return min(SOFT_CAP, 0.40 + 0.05 * (z - 4.0))
