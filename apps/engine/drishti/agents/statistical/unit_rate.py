"""Price per metre, for the one slice of the corpus where scale is real.

ROAD_CC works whose description states a length (4,065 of them) follow
log10(cost) = 0.6309 * log10(len_m) + 4.5381 with a residual sd of 0.2772:
a 10x longer road costs about 4.3x more, the fixed-mobilisation effect an
engineer would expect. The curve is checked against published rural CC road
rates (Rs 4,000-6,500 per metre) so it is not only the corpus judging itself.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

Z_FLAG = 3.0


@dataclass(frozen=True)
class UnitRateModel:
    work_type_code: str
    unit: str
    n: int
    slope: float
    intercept: float
    resid_sd: float
    anchor_low: float | None = None
    anchor_high: float | None = None
    anchor_label: str | None = None

    def predict(self, quantity: float) -> float:
        return 10 ** (self.intercept + self.slope * math.log10(quantity))


def road_check(amount: float, length_m: float, model: UnitRateModel) -> dict:
    predicted = model.predict(length_m)
    z = (math.log10(amount) - math.log10(predicted)) / model.resid_sd
    per_metre = amount / length_m
    out = {
        "length_m": length_m,
        "predicted": predicted,
        "z": z,
        "per_metre": per_metre,
        "verdict": "UNIT_RATE_ABOVE" if z >= Z_FLAG else "UNIT_RATE_TYPICAL",
        "anchor": (model.anchor_low, model.anchor_high),
        "above_anchor_x": per_metre / model.anchor_high if model.anchor_high else None,
        "n": model.n,
    }
    return out
