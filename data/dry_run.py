r"""Assess every real work locally (no database) and report what the queue would hold.

Read the top of the list by eye before trusting it: in the old build the first
ranking of every new sweep surfaced filing conventions, not problems (AD-103,
AD-106).

Saves data/trial/results/risk_score_bands.json (band shares, queue size) and
risk_score_queue_sample.csv (30 random works from the review queue, with the score's
reasons, for reading by eye; labels in data/trial/risk_score_labels.py).

Run: apps\engine\.venv\Scripts\python.exe data\dry_run.py
"""

from __future__ import annotations

import json
import time
from collections import Counter
from pathlib import Path

import pandas as pd

from common import BUILD, load_context, works_records  # noqa: E402
from drishti.fusion import fuse  # noqa: E402
from drishti.pipeline.orchestrator import assess_work  # noqa: E402

OUT = Path(__file__).resolve().parent / "trial" / "results"
REVIEW = ("CRITICAL", "HIGH")


def main() -> None:
    works = pd.read_parquet(BUILD / "works.parquet")
    ctx = load_context(works)
    t0 = time.time()
    rows = []
    bands, issues = Counter(), Counter()
    for w in works_records(works):
        a = assess_work(w, ctx)
        bands[a.fused.band] += 1
        for i in a.validation:
            issues[i.code] += 1
        rows.append({"priority": a.priority, "score": round(a.fused.score * 100, 1),
                     "band": a.fused.band, "work_id": w["work_id"], "amount": w["amount"],
                     "district": w["district_name"],
                     "description": str(w["description"])[:200],
                     "reasons": " | ".join(f"{r['label']}: {r['text_en'][:160]}"
                                           for r in a.fused.reasons)})
    n = len(rows)
    print(f"assessed {n:,} works in {time.time() - t0:.0f}s")
    print("bands:", dict(bands))
    print("validation issues (shown, not counted):", dict(issues))
    df = pd.DataFrame(rows)
    queue = df[df.band.isin(REVIEW)]
    res = {"works": n, "cutoffs": {"CRITICAL": fuse.CRITICAL, "HIGH": fuse.HIGH,
                                   "MEDIUM": fuse.MEDIUM},
           "weights": fuse.weights(),
           "bands": {b: int(bands.get(b, 0)) for b in ("CRITICAL", "HIGH", "MEDIUM", "LOW")},
           "shares": {b: round(bands.get(b, 0) / n, 5) for b in ("CRITICAL", "HIGH", "MEDIUM",
                                                                   "LOW")},
           "review_queue": int(len(queue)), "review_share": round(len(queue) / n, 5),
           "max_score": float(df.score.max())}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "risk_score_bands.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
    # the sample is labelled by eye (risk_score_labels.py): a re-run must not redraw it
    sample_path = OUT / "risk_score_queue_sample.csv"
    if not sample_path.exists():
        queue.sample(n=min(30, len(queue)), random_state=50).sort_values(
            "priority", ascending=False).to_csv(sample_path, index=False)
    print(json.dumps(res, indent=2))
    for r in queue.sort_values("priority", ascending=False).head(25).itertuples():
        print(f"{r.band:8} {r.score:5.1f} p={r.priority:.2f} Rs{r.amount:>12,.0f} "
              f"{r.district!s:18} | {r.description[:90]}")


if __name__ == "__main__":
    main()
