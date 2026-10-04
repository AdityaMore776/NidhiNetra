r"""Build the Time & Rules agent's "longest usual time" per work type (T122, plan T120 §8.2).

For each eSAKSHI work type, the 90th percentile of sanction-to-completion days on the dashboard
works that finished (data/raw/esakshi_dashboard, through data/esakshi_dashboard.py). Types with
fewer than 30 finished works use the figure for all works. Aggregates only.

The figure is generous on purpose: it includes the wait for a contractor, and slow works that
had not finished by the snapshot are not in it (so the true figure is longer). The agent uses
it only as the cap on an agency's own estimate, so that padding an estimate buys no time.

Writes apps/engine/drishti/reference/time_bands.json.

Run: apps\engine\.venv\Scripts\python.exe data\build_time_bands.py
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "data"))
import esakshi_dashboard  # noqa: E402

OUT = ROOT / "apps" / "engine" / "drishti" / "reference" / "time_bands.json"
MIN_WORKS = 30


def p(xs: list[int], q: float) -> float:
    s = sorted(xs)
    k = (len(s) - 1) * q / 100
    lo = int(k)
    hi = min(lo + 1, len(s) - 1)
    return round(s[lo] + (s[hi] - s[lo]) * (k - lo), 1)


def main() -> None:
    works, info = esakshi_dashboard.load()
    by_type: dict[str, list[int]] = defaultdict(list)
    for w in works:
        s, c = w["sanction_date"], w["completed_date"]
        if s and c and c >= s:
            by_type[w["work_type_code"]].append((c - s).days)
    every = [d for v in by_type.values() for d in v]
    lags = [(w["sanction_date"] - w["recommended_date"]).days for w in works
            if w["recommended_date"] and w["sanction_date"]
            and w["sanction_date"] >= w["recommended_date"]]
    out = {
        "source": ("data/build_time_bands.py on the eSAKSHI dashboard tables of 2 Oct 2026 "
                   f"(snapshot {info['as_of']}): sanction to completion of finished works"),
        "note": ("p90 = the longest usual time (9 in 10 finished works of the type took no longer). "
                 "Generous: it includes the wait for a contractor, and works still open at the "
                 "snapshot are not in it."),
        "min_works": MIN_WORKS,
        "all": {"works": len(every), "p50": p(every, 50), "p90": p(every, 90)},
        "sanction_lag": {"works": len(lags), "p50": p(lags, 50),
                         "share_past": {str(d): round(sum(x > d for x in lags) / len(lags), 3)
                                        for d in (45, 75)}},
        "types": {t: {"works": len(v), "p50": p(v, 50), "p90": p(v, 90)}
                  for t, v in sorted(by_type.items()) if len(v) >= MIN_WORKS},
    }
    OUT.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(f"{OUT.relative_to(ROOT)}: {len(out['types'])} types; all works p90 {out['all']['p90']} days")


if __name__ == "__main__":
    main()
