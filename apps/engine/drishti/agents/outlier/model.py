"""What is usual for a work type, field by field: the Odd Overall engine's stored statistics.

Three fields, each on a log scale, with each work type's own 10th / 50th / 90th percentiles
(data/build_outlier.py -> engine_models "outlier_stats"):

  amount   rupees sanctioned
  speed    days from recommendation to completion (completed works only)
  words    characters in the description

A field's oddness is a robust z: (x - p50) / ((p90 - p10) / 2.563), the same spread the cost
engine uses (band.py), floored so a type where every work looks alike cannot make a small
difference look huge. A type with fewer than 20 works borrows the whole scheme's statistics.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

P10_P90_SD = 2.563
SD_FLOOR = 0.08
FIELDS = ("amount", "speed", "words")


def features(work: dict) -> dict[str, float]:
    out: dict[str, float] = {}
    amount = work.get("amount")
    if amount and float(amount) > 0:
        out["amount"] = math.log10(float(amount))
    rec, done = work.get("recommended_date"), work.get("completed_date")
    if rec is not None and done is not None and done >= rec:
        out["speed"] = math.log10((done - rec).days + 1)
    desc = (work.get("description") or "").strip()
    if desc:
        out["words"] = math.log10(len(desc))
    return out


@dataclass
class OutlierStats:
    version: str
    # type -> field -> (p10, p50, p90); "*" is the whole scheme
    quantiles: dict[str, dict[str, tuple[float, float, float]]] = field(default_factory=dict)
    threshold: float = 3.0          # the second-largest |z| above which a record is odd

    forest: Forest | None = None

    @classmethod
    def from_json(cls, d: dict) -> OutlierStats:
        return cls(version=d["version"],
                   quantiles={t: {f: tuple(v) for f, v in fs.items()}
                              for t, fs in d["quantiles"].items()},
                   threshold=float(d["threshold"]),
                   forest=Forest.from_json(d["forest"]) if d.get("forest") else None)

    def vector(self, work: dict) -> list[float]:
        z = self.zscores(work)
        return [z.get(f, 0.0) for f in FIELDS]

    def _q(self, work_type: str | None, f: str) -> tuple[float, float, float] | None:
        q = self.quantiles.get(work_type or "", {}).get(f)
        return q or self.quantiles.get("*", {}).get(f)

    def zscores(self, work: dict) -> dict[str, float]:
        out = {}
        for f, x in features(work).items():
            q = self._q(work.get("work_type_code"), f)
            if q is None:
                continue
            p10, p50, p90 = q
            sd = max(SD_FLOOR, (p90 - p10) / P10_P90_SD)
            out[f] = (x - p50) / sd
        return out

    def range_of(self, work_type: str | None, f: str) -> tuple[float, float] | None:
        q = self._q(work_type, f)
        return (q[0], q[2]) if q else None


def odd_score(z: dict[str, float]) -> float:
    """The second-largest |z|: high only when two fields are unusual at once (the robust-z
    method; it lost the planted test to the forest below, results/outlier_trial.json)."""
    a = sorted((abs(v) for v in z.values()), reverse=True)
    return a[1] if len(a) >= 2 else 0.0


EULER = 0.5772156649015329


def avg_path(n: float) -> float:
    """Expected path length of an unsuccessful search in a binary tree of n points (as sklearn)."""
    if n <= 1:
        return 0.0
    if n == 2:
        return 1.0
    return 2.0 * (math.log(n - 1.0) + EULER) - 2.0 * (n - 1.0) / n


@dataclass
class Forest:
    """An Isolation Forest stored as numbers and scored in plain Python, so any work can be
    scored live (T051). Trained in data/build_outlier.py; the engine's scores equal sklearn's
    (checked there to 1e-9)."""
    max_samples: int
    trees: list[dict]               # {"feature", "threshold", "left", "right", "n", "cols"}
    threshold: float                # score above which a record is odd (1.5% of real works)

    @classmethod
    def from_json(cls, d: dict) -> Forest:
        return cls(max_samples=int(d["max_samples"]), trees=d["trees"],
                   threshold=float(d["threshold"]))

    def score(self, x: list[float]) -> float:
        total = 0.0
        for t in self.trees:
            cols = t["cols"]
            node, depth = 0, 0
            while t["left"][node] != -1:
                v = x[cols[t["feature"][node]]]
                node = t["left"][node] if v <= t["threshold"][node] else t["right"][node]
                depth += 1
            total += depth + avg_path(t["n"][node])
        mean = total / len(self.trees)
        return 2.0 ** (-mean / avg_path(self.max_samples))
