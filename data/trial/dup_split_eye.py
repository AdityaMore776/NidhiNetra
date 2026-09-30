"""Share of the Duplicate & Split engine's flags that look real when read by eye (T030).

Reads the labels in dup_split_labels.py and writes results/dup_split_eye.json.
Run: .venv-trial\\Scripts\\python.exe data\\trial\\dup_split_eye.py
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import dup_split_labels as L

OUT = Path(__file__).resolve().parent / "results"


def share(labels: dict, yes: str) -> dict:
    n = len(labels)
    k = sum(v == yes for v in labels.values())
    return {"read": n, yes: k, "share": round(k / n, 3) if n else None}


def main() -> None:
    groups = Counter(L.GROUPS_TEST.values())
    site = {k: v for k, v in L.GROUPS_TEST.items() if v in ("split", "explained")}
    res = {
        "pairs_top50_dev": share(L.DEV, "same"),
        "pairs_random_test1_before_place_fix": share(L.TEST1, "same"),
        "pairs_random_test2_rules_frozen": share(L.TEST2, "same"),
        "groups_same_site_test": share(site, "split"),
        "groups_bulk_order_test": {"read": groups["series"], "read_as_series": groups["series"]},
    }
    (OUT / "dup_split_eye.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
