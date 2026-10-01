r"""Odd Overall, another method (T053): two plain rules instead of an Isolation Forest.

The forest's flags (214 works) read 9/30 worth a look on a random sample: mostly prefab bus
stops and ordinary jobs. The worth-a-look cases were of two kinds, so each becomes a rule an
officer can read:

  BIG_AMOUNT_NO_SCOPE   Rs 10 lakh or more, above the top (p90) of its work type nationally,
                        and the description does not say what or where: at most 6 words, no
                        number (count, length, plot), no place name (the Duplicate engine's
                        place words) - "Smart Boards" for Rs 1 crore
  BUILT_IN_DAYS         a construction type (building, road, drain, pond...) of Rs 5 lakh or
                        more recorded complete 0-14 days after recommendation, outside a
                        bulk-entry quarter, and not a backfilled older work (no earlier
                        financial year in the description)

Writes counts and a random 30 per rule for reading by eye to results/odd_rules_trial.json and
results/odd_rules_sample.csv. Run: apps\engine\.venv\Scripts\python.exe data\trial\odd_rules_trial.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "data"))
from common import BUILD, load_context, works_records  # noqa: E402
from drishti.agents.statistical.scope import GOODS, read  # noqa: E402

OUT = ROOT / "data" / "trial" / "results"
CONSTRUCTION = {"ROAD_CC", "ROAD_BT", "FOOTPATH", "CULVERT", "BRIDGE", "COMMUNITY_HALL",
                "SCHOOL_BUILDING", "HEALTH_BUILDING", "LIBRARY", "BOUNDARY_WALL",
                "TOILET_BLOCK", "DRAIN", "POND", "CHECK_DAM", "CREMATORIUM", "PLAYGROUND",
                "BUS_SHELTER"}
OLD_FY = re.compile(r"\b(20[01]\d|202[0-3])\s*[-/]\s*(\d{2}|20\d{2})\b")


def main() -> None:
    works = pd.read_parquet(BUILD / "works.parquet")
    ctx = load_context(works)
    idx = ctx.data["dup_split"]
    place = {r.work_id: r.place for v in idx.by_district.values() for r in v}
    cs = pd.read_parquet(BUILD / "cohort_stats.parquet")
    top = {r.work_type_code: 10 ** r.p90 for r in cs[cs.level == "type"].itertuples()}
    rates = ctx.stats.timeline
    rows = []
    for w in works_records(works):
        amt, t, desc = float(w.get("amount") or 0), w.get("work_type_code"), w.get("description")
        if not desc or not t or amt <= 0:
            continue
        rd = read(t, desc)
        rule = None
        words = desc.split()
        if (amt >= 1_000_000 and amt >= top.get(t, float("inf")) and len(words) <= 6
                and not re.search(r"\d", desc) and not place.get(w["work_id"])
                and not rd.undescribed):
            rule = "BIG_AMOUNT_NO_SCOPE"
        rec, done = w.get("recommended_date"), w.get("completed_date")
        if (rule is None and t in CONSTRUCTION and rd.scope != GOODS and amt >= 500_000
                and rec is not None and done is not None and 0 <= (done - rec).days <= 14
                and not OLD_FY.search(desc)
                and (rates is None or rates.distinctiveness(
                    f"{rec.year}-Q{(rec.month - 1) // 3 + 1}") >= 0.8)):
            rule = "BUILT_IN_DAYS"
        if rule:
            rows.append({"rule": rule, "work_id": w["work_id"], "type": t, "amount": amt,
                         "recommended": str(rec), "completed": str(done),
                         "status": w.get("status"), "district": w.get("district_name"),
                         "description": " ".join(str(desc).split())[:200]})
    df = pd.DataFrame(rows)
    sample = pd.concat([g.sample(min(30, len(g)), random_state=53) for _, g in df.groupby("rule")])
    OUT.mkdir(parents=True, exist_ok=True)
    sample.to_csv(OUT / "odd_rules_sample.csv", index=False)
    res = {"flagged": df.rule.value_counts().to_dict(), "works": int(len(df))}
    (OUT / "odd_rules_trial.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(json.dumps(res, indent=2))
    for r in sample.itertuples():
        print(f"{r.rule[:5]} | {r.type} Rs{r.amount:,.0f} rec {r.recommended} done {r.completed} "
              f"| {r.description[:110]}")


if __name__ == "__main__":
    main()
