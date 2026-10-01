r"""Trial (T054, 1 Oct 2026) - how long do works really wait? The curves behind R01 and R02.

The owner asked whether the guideline checker flags too much: most works are past the 75-day
sanction limit, and a work a few days past scored half the rule's maximum. The public export
has no sanction date (the "sanctioned" row repeats the recommendation date), so the wait is
read from the snapshot instead: of the works recommended N days before the data was taken,
what share is still waiting for sanction (R01), and of the sanctioned ones, what share is
still open (R02)?

  R01 curve  works not of an ended term (the 17th Lok Sabha's leftovers are their own case,
             para 3.15), wait counted the way R01 counts it (less model code of conduct days)
  R02 curve  works sanctioned or completed, age from recommendation (the export has nothing
             later); the share still open at each age

Writes results/wait_curves.json. The anchor points are copied into reference/rules.json
("wait_curves"), where the engine reads them.

Run:  apps\engine\.venv\Scripts\python.exe data\trial\wait_curves_trial.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "data"))

from common import BUILD  # noqa: E402
from drishti import config  # noqa: E402
from drishti.agents.compliance.agent import mcc_days  # noqa: E402

OUT = ROOT / "data" / "trial" / "results"
POINTS = (75, 90, 120, 150, 180, 240, 300, 365, 450, 540, 730, 900, 1100)
HALF = 15          # each point is the share among works within +-15 days of it


def curve(age: pd.Series, still: pd.Series) -> list[dict]:
    out = []
    for d in POINTS:
        m = (age >= d - HALF) & (age <= d + HALF)
        if m.sum() >= 100:
            out.append({"days": d, "works": int(m.sum()),
                        "share": round(float(still[m].mean()), 3)})
    return out


def main() -> None:
    w = pd.read_parquet(BUILD / "works.parquet")
    as_of = config.snapshot_date()
    rec = pd.to_datetime(w.recommended_date).dt.date
    w = w[rec.notna()].copy()
    w["rec"] = rec[rec.notna()]
    age = w.rec.map(lambda d: (as_of - d).days)

    cur = w.term != "17th Lok Sabha"
    wait = w[cur].rec.map(lambda d: (as_of - d).days - mcc_days(d, as_of))
    r01 = curve(wait, w[cur].status == "RECOMMENDED")

    started = w.status != "RECOMMENDED"
    r02 = curve(age[started], w[started].status == "SANCTIONED")

    ended = w[(w.term == "17th Lok Sabha") & (w.status == "RECOMMENDED")]
    res = {"as_of": as_of.isoformat(), "window_days": HALF,
           "r01_still_waiting": r01, "r02_still_open": r02,
           "ended_term_still_waiting": int(len(ended)),
           "reading": "R01: at 75 days most works still wait; a wait is unusual only when few "
                      "works that old still wait. R02: at every age past a year a large share "
                      "is still open, so a long-open work is common in this data."}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "wait_curves.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
