"""How often works like this one finished more than a year after recommendation (T051).

v1 scored open works offline with a LightGBM model and stored one number per work, so a work
recommended after that run had no score, and in districts the model had not seen its ranking
fell to 0.59 (0.5 = chance). v2 is a ladder of past late rates, each pulled toward the step
above it when it rests on few works (empirical Bayes):

    country x type  ->  state x type  ->  district x type  ->  implementing office

Every step is a stored count (data/build_delay_rates.py -> table delay_rates), so any work can
be scored: a new office borrows its district's record for the work type, a new district its
state's, and the engine says which step its estimate rests on.
"""

from __future__ import annotations

from dataclasses import dataclass, field

SHRINK = 20.0          # pseudo-works pulling a thin record toward the step above it
LEVELS = ("type", "state_type", "district_type", "office")


@dataclass(frozen=True)
class Estimate:
    p_late: float
    level: str             # the finest step that had any record
    n: int                 # works behind that step
    rate: float            # that step's own raw late rate
    steps: tuple[tuple[str, int, float], ...]   # (level, n, shrunk p) from coarse to fine


@dataclass
class DelayRates:
    base: float = 0.0
    n_base: int = 0
    rows: dict[tuple[str, str], tuple[int, int]] = field(default_factory=dict)
    # the estimate above which a work is among the riskiest tenth of open works, stored with
    # the counts (level "flag", key "p90", late / n) so any new work meets the same cut
    flag_p: float | None = None

    @classmethod
    def from_rows(cls, rows) -> DelayRates:
        r = cls()
        for row in rows:
            n, late = int(row["n"]), int(row["late"])
            if row["level"] == "all":
                r.base, r.n_base = (late / n if n else 0.0), n
            elif row["level"] == "flag":
                r.flag_p = late / n if n else None
            else:
                r.rows[(row["level"], row["key"])] = (n, late)
        return r

    @staticmethod
    def keys(work: dict) -> dict[str, str]:
        t = str(work.get("work_type_code") or "NA")
        return {"type": t, "state_type": f"{work.get('state_lgd') or 'NA'}|{t}",
                "district_type": f"{work.get('district_lgd') or 'NA'}|{t}",
                "office": str(work.get("agency_name") or "")}

    def estimate(self, work: dict) -> Estimate | None:
        if not self.n_base:
            return None
        keys = self.keys(work)
        p, level, n_at, raw = self.base, "all", self.n_base, self.base
        steps = []
        for lv in LEVELS:
            if lv == "office" and not keys[lv]:
                continue
            n, late = self.rows.get((lv, keys[lv]), (0, 0))
            if n == 0:
                continue
            p = (late + SHRINK * p) / (n + SHRINK)
            level, n_at, raw = lv, n, late / n
            steps.append((lv, n, p))
        return Estimate(p_late=p, level=level, n=n_at, rate=raw, steps=tuple(steps))
