"""Share of the risk score's review queue worth an officer's time, read by eye (T050).

Reads risk_score_labels.py and writes results/risk_score_eye.json.
Run: .venv-trial\\Scripts\\python.exe data\\trial\\risk_score_eye.py
"""

from __future__ import annotations

import json
from pathlib import Path

import risk_score_labels as L

OUT = Path(__file__).resolve().parent / "results"


def main() -> None:
    n = len(L.QUEUE)
    k = sum(v == "worth_checking" for v in L.QUEUE.values())
    res = {"queue_random_sample": {"read": n, "worth_checking": k, "share": round(k / n, 3)}}
    (OUT / "risk_score_eye.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
