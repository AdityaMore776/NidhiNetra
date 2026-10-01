"""What works described like this one usually cost: a word-price model any work can use (T051).

Version B of the cost engine (T020) learned the expected range from descriptions with
LightGBM, offline, and stored one answer per work, so a work recommended after that run was
judged by peers alone (a looser rule than the one measured). This model is linear and small
enough to ship as coefficients (data/build_price_model.py -> table engine_models), so the
engine computes the range for ANY description:

  log10(amount) ~ intercept + sum of word weights + work type + type x scope + state
                  + size (stated length, unit count) + reading (bundle, many sites) + year

Words count only if they appear in descriptions from at least 20 constituencies: the model
learns what "building", "books" or "two storey" mean everywhere, never one MP's habits or a
village's name. The 10%-90% range is the prediction plus each work type's own out-of-fold
residual quantiles (fitted constituency by constituency, so a new constituency is covered).
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from functools import lru_cache

from drishti.agents.statistical.scope import mast_count, read, stated_count
from drishti.agents.statistical.text import stated_length

WORD = re.compile(r"[a-z]{3,}|[ऀ-ॣ०-ॿ]{2,}")
YEAR0 = 2000


@lru_cache(maxsize=50_000)
def _words(text: str) -> tuple[str, ...]:
    return tuple(WORD.findall(re.sub(r"\d+", " ", text.lower())))


def features(work: dict) -> dict[str, float]:
    """The model's inputs for one work, by name (the same function builds the training data).

    Word pairs and word-within-type features were tried (price-linear-2, 1 Oct 2026): no
    better out of fold (typical miss 1.84x against 1.82x), so the model stays on words."""
    t = str(work.get("work_type_code") or "NA")
    desc = work.get("description") or ""
    rd = read(t, desc)
    f: dict[str, float] = {f"w={x}": 1.0 for x in _words(desc)}
    f[f"t={t}"] = 1.0
    f[f"ts={t}|{rd.scope}"] = 1.0
    f[f"st={work.get('state_lgd') or 'NA'}"] = 1.0
    length = stated_length(desc, allow_km=True)
    if not math.isnan(length):
        f["log_length"] = math.log10(length)
        f["has_length"] = 1.0
    count = rd.count or stated_count(desc) or mast_count(desc)
    if count:
        f["log_count"] = math.log10(count)
        f["has_count"] = 1.0
    for name, on in (("bundle", rd.bundle), ("many_sites", rd.many_sites),
                     ("undescribed", rd.undescribed)):
        if on:
            f[name] = 1.0
    rec = work.get("recommended_date")
    if rec is not None:
        f["year"] = float(getattr(rec, "year", YEAR0) - YEAR0)
    return f


@dataclass
class PriceModel:
    version: str
    intercept: float
    weights: dict[str, float]
    # per work type: (q10 offset, q90 offset) in log10 rupees, from out-of-fold residuals
    spread: dict[str, tuple[float, float]] = field(default_factory=dict)
    default_spread: tuple[float, float] = (-0.4, 0.4)

    @classmethod
    def from_json(cls, d: dict) -> PriceModel:
        return cls(version=d["version"], intercept=float(d["intercept"]),
                   weights={k: float(v) for k, v in d["weights"].items()},
                   spread={k: (float(a), float(b)) for k, (a, b) in d["spread"].items()},
                   default_spread=tuple(d.get("default_spread", (-0.4, 0.4))))

    def predict(self, work: dict) -> dict[str, float]:
        """{"q10", "q50", "q90"} in log10 rupees."""
        q50 = self.intercept + sum(self.weights.get(k, 0.0) * v
                                   for k, v in features(work).items())
        lo, hi = self.spread.get(str(work.get("work_type_code") or "NA"), self.default_spread)
        return {"q10": q50 + lo, "q50": q50, "q90": q50 + hi}
