"""The engines' stored statistics, built from any list of works without pandas.

The same method as data/build_stats.py (which builds them from the real export and asserts
it reproduces the AD-106 measurements): v2 peer bands of log10 amount per (peer type x district
/ state / scheme) from clean works only, completion-time percentiles, the CC-road length curve
and the impossible-date counts per quarter and office. Quantiles interpolate linearly, as
pandas does, so a corpus gives the same bands either way.

Used by the synthetic evaluation and the tests: a fresh corpus gets fresh statistics, so the
engines are judged on districts they have never seen.
"""

from __future__ import annotations

import math
from collections import defaultdict
from datetime import date

from drishti import records
from drishti.agents.statistical.band import MIN_COHORT, P10_P90_SD, SD_FLOOR, SHRINK_K
from drishti.agents.statistical.cohort import StatsStore
from drishti.agents.statistical.scope import GOODS, MAST, WORKS, read
from drishti.agents.statistical.text import stated_length

SPLIT_MIN_N, SPLIT_MIN_RATIO = 50, 2.0


def quantile(sorted_values: list[float], q: float) -> float:
    n = len(sorted_values)
    if n == 1:
        return sorted_values[0]
    pos = q * (n - 1)
    lo = int(math.floor(pos))
    hi = min(lo + 1, n - 1)
    return sorted_values[lo] + (sorted_values[hi] - sorted_values[lo]) * (pos - lo)


def std(values: list[float]) -> float:
    n = len(values)
    if n < 2:
        return 0.0
    m = sum(values) / n
    return math.sqrt(sum((v - m) ** 2 for v in values) / (n - 1))


def _median(values: list[float]) -> float:
    return quantile(sorted(values), 0.5)


def cohort_rows(works: list[dict]) -> list[dict]:
    """v2 peer bands (scope-aware peer types, clean works only), n >= MIN_COHORT."""
    clean: list[tuple[dict, str, float]] = []
    for w in works:
        amount, t = float(w.get("amount") or 0), w.get("work_type_code")
        if amount <= 0 or not t:
            continue
        rd = read(t, w.get("description"))
        if rd.clean:
            clean.append((w, rd.scope, math.log10(amount)))
    by_scope: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for w, sc, lv in clean:
        if sc != MAST:
            by_scope[w["work_type_code"]][sc].append(lv)
    split = {t for t, s in by_scope.items()
             if len(s[GOODS]) >= SPLIT_MIN_N and len(s[WORKS]) >= SPLIT_MIN_N
             and abs(_median(s[GOODS]) - _median(s[WORKS])) >= math.log10(SPLIT_MIN_RATIO)}

    def peer(w: dict, sc: str) -> str:
        t = w["work_type_code"]
        return f"{t}|{sc}" if (sc == MAST or t in split) else t

    groups: dict[tuple[str, str, str], list[float]] = defaultdict(list)
    by_type: dict[str, list[float]] = defaultdict(list)
    for w, sc, lv in clean:
        p = peer(w, sc)
        by_type[p].append(lv)
        groups[("type_district", p, str(w.get("district_lgd") or ""))].append(lv)
        groups[("type_state", p, str(w.get("state_lgd") or ""))].append(lv)
        groups[("type", p, "")].append(lv)
    sd_type = {p: std(v) for p, v in by_type.items()}
    rows = []
    for (level, p, key), vals in groups.items():
        if len(vals) < MIN_COHORT or (level != "type" and not key):
            continue
        s = sorted(vals)
        p10, p50, p90 = quantile(s, 0.10), quantile(s, 0.50), quantile(s, 0.90)
        raw = (p90 - p10) / P10_P90_SD
        st = sd_type.get(p) or raw
        sd = max(SD_FLOOR, (len(s) * raw + SHRINK_K * st) / (len(s) + SHRINK_K))
        rows.append({"level": level, "work_type_code": p, "key": key, "n": len(s), "p10": p10,
                     "p50": p50, "p90": p90, "sd": sd})
    return rows


def duration_rows(works: list[dict]) -> list[dict]:
    days: dict[str, list[float]] = defaultdict(list)
    for w in works:
        rec, done = w.get("recommended_date"), w.get("completed_date")
        if w.get("status") == "COMPLETED" and rec and done and (done - rec).days > 0:
            days[w.get("work_type_code") or ""].append(float((done - rec).days))
    out = []
    for t, v in days.items():
        if t and len(v) >= MIN_COHORT:
            s = sorted(v)
            out.append({"work_type_code": t, "n": len(s), "p50": quantile(s, 0.5),
                        "p90": quantile(s, 0.9), "p98": quantile(s, 0.98)})
    return out


def road_curve_rows(works: list[dict]) -> list[dict]:
    xs, ys = [], []
    for w in works:
        if w.get("work_type_code") != "ROAD_CC" or not (w.get("amount") or 0) > 0:
            continue
        length = stated_length(w.get("description"))
        if not math.isnan(length) and length > 0:
            xs.append(math.log10(length))
            ys.append(math.log10(float(w["amount"])))
    if len(xs) < MIN_COHORT:
        return []
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    sxx = sum((x - mx) ** 2 for x in xs)
    slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys, strict=True)) / sxx
    intercept = my - slope * mx
    resid = [y - (slope * x + intercept) for x, y in zip(xs, ys, strict=True)]
    sd = math.sqrt(sum(r * r for r in resid) / len(resid))
    return [{"work_type_code": "ROAD_CC", "unit": "m", "n": len(xs), "slope": slope,
             "intercept": intercept, "resid_sd": sd, "anchor_low": 4000.0,
             "anchor_high": 6500.0, "anchor_label": "published rural single-lane CC road rates"}]


def _quarter(d: date) -> str:
    return f"{d.year}-Q{(d.month - 1) // 3 + 1}"


def timeline_rows(works: list[dict]) -> tuple[list[dict], list[dict]]:
    q: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    a: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for w in works:
        rec, done = w.get("recommended_date"), w.get("completed_date")
        if not rec or not done:
            continue
        bad = int((rec - done).days >= 7)
        q[_quarter(rec)][0] += 1
        q[_quarter(rec)][1] += bad
        if w.get("agency_name"):
            a[w["agency_name"]][0] += 1
            a[w["agency_name"]][1] += bad
    return ([{"quarter": k, "n": n, "bad": b} for k, (n, b) in q.items()],
            [{"agency_name": k, "completed": n, "bad": b} for k, (n, b) in a.items()])


def build_store(works: list[dict], models: list[dict] | None = None) -> StatsStore:
    works = [records.work(w) for w in works]          # one malformed row must not stop it
    quarters, agencies = timeline_rows(works)
    return StatsStore.from_rows(cohort_rows(works), duration_rows(works), road_curve_rows(works),
                                quarters, agencies, (), models or [])
