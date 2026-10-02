r"""The Visualization Engine's built-in examples (T092), run through the real engines.

Each example is a made-up work placed in a real district of the eSAKSHI dashboard tables (40,935
works, data/esakshi_dashboard.py), so the price bands, the district's other works and the rules
it meets are the real ones. The page (apps/web/src/app/explain) shows them to anyone, signed in
or not; a judge's own example goes to the live engine instead (POST /api/v1/explain).

Writes apps/web/public/explain/examples.json: per example, its title, a one-line story, what was
typed, and the trace (drishti/explain.py). Text is masked; no MP is named.

Run:  apps\engine\.venv\Scripts\python.exe data\trial\explain_examples.py
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "data"))
sys.path.insert(0, str(ROOT / "apps" / "engine"))
from esakshi_dashboard import load  # noqa: E402

from drishti.batch import indexes  # noqa: E402
from drishti.evaluation.stats import build_store  # noqa: E402
from drishti.explain import explain  # noqa: E402
from drishti.pipeline.orchestrator import Context  # noqa: E402

OUT = ROOT / "apps" / "web" / "public" / "explain" / "examples.json"


def _district(works: list[dict]) -> dict:
    """The district with the most works that carry a recommendation date (richest comparisons)."""
    n = Counter(w["district_lgd"] for w in works if w.get("recommended_date"))
    lgd = n.most_common(1)[0][0]
    return next(w for w in works if w["district_lgd"] == lgd)


def _repeat_of(works: list[dict], lgd: str, as_of, ctx) -> dict | None:
    """A real work of the district, with a place named, that the Duplicate & Split check flags
    when it is typed in again as a new recommendation: the repeat it looks for."""
    from drishti.agents.dup_split.match import place_words
    from drishti.pipeline.orchestrator import assess_work

    for w in sorted(works, key=lambda w: str(w["work_id"])):
        rec = w.get("recommended_date") or w.get("completed_date")
        if (w["district_lgd"] != lgd or not rec or not 60 < (as_of - rec).days < 700
                or not place_words(w.get("description")) or float(w.get("amount") or 0) < 1e5):
            continue
        again = {**w, "work_id": "PROBE", "status": "RECOMMENDED", "recommended_date": as_of,
                 "sanction_date": None, "completed_date": None}
        dup = next(r for r in assess_work(again, ctx).agents if r.agent == "dup_split")
        if any(f.risk > 0 for f in dup.findings):
            return w
    return None


def examples(works: list[dict], as_of, ctx) -> list[tuple[str, str, dict]]:
    d = _district(works)
    base = {"source": "SCENARIO", "house": None, "term": None, "state_lgd": d.get("state_lgd"),
            "state_name": d.get("state_name"), "district_lgd": d["district_lgd"],
            "district_name": d.get("district_name"), "constituency": None, "mp_name": None,
            "agency_name": d.get("agency_name"), "fy": None, "category": None,
            "status": "RECOMMENDED", "recommended_date": as_of, "sanction_date": None,
            "completed_date": None, "quantity": None, "quantity_unit": None,
            "is_outside_constituency": False, "signals": {}}
    out = [
        ("ordinary", "An ordinary new road",
         {**base, "work_id": "EXAMPLE-1", "work_type_code": "ROAD_CC", "amount": 480000.0,
          "description": "Construction of CC road 250 mtr from Panchayat Bhawan to Primary "
                         "School in Ward No 4"}),
        ("temple", "A temple as the work itself",
         {**base, "work_id": "EXAMPLE-2", "work_type_code": "COMMUNITY_HALL", "amount": 900000.0,
          "description": "Construction of temple and boundary wall at Shiv Mandir campus, "
                         "near Ramdev Bhagat house"}),
        ("vague", "A large sum that says nothing",
         {**base, "work_id": "EXAMPLE-3", "work_type_code": "COMMUNITY_HALL",
          "amount": 2600000.0, "description": "As per recommendation letter attached"}),
        ("price", "One light, priced like many",
         {**base, "work_id": "EXAMPLE-4", "work_type_code": "STREET_LIGHT", "amount": 495000.0,
          "description": "Installation of 1 solar street light at the bus stand"}),
        ("dates", "Completed before it was recommended",
         {**base, "work_id": "EXAMPLE-5", "work_type_code": "ROAD_CC", "amount": 760000.0,
          "status": "COMPLETED", "recommended_date": as_of - timedelta(days=120),
          "sanction_date": None, "completed_date": as_of - timedelta(days=200),
          "description": "Construction of CC road 400 mtr from main road to cremation ground"}),
    ]
    again = _repeat_of(works, d["district_lgd"], as_of, ctx)
    if again:
        out.append(("repeat", "The same work asked for again",
                    {**base, "work_id": "EXAMPLE-6", "work_type_code": again["work_type_code"],
                     "amount": float(again["amount"]), "description": again["description"],
                     "agency_name": again.get("agency_name"), "mp_name": again.get("mp_name")}))
    return out


STORIES = {
    "ordinary": "A plain road with its length and both ends named: what most works look like.",
    "temple": "The description reads as building a temple, which the guidelines do not allow; the "
              "same words as a landmark ('road near the temple') would pass.",
    "vague": "Rs 26 lakh with no word on what or where: nobody could check it on the ground.",
    "price": "One solar light for nearly Rs 5 lakh: compared with what similar lights cost here.",
    "dates": "The record says the road was finished four months before the MP recommended it.",
    "repeat": "A real work of this district (finished or still open), typed in again as a new "
              "recommendation.",
}


def main() -> None:
    works, info = load()
    as_of = info["as_of"]
    ctx = Context(stats=build_store(works), as_of=as_of, data=indexes(works))
    out = []
    for key, title, work in examples(works, as_of, ctx):
        trace = explain(work, ctx)
        out.append({"id": key, "title": title, "story": STORIES[key], "trace": trace})
        print(f"{key:9} {trace['result']['band']:8} {trace['result']['score']:.3f} "
              f"{trace['result']['colour']} "
              f"{[f['code'] for c in trace['checks'] for f in c['findings']]}")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"source": f"eSAKSHI dashboard tables, {len(works):,} works, "
                                         f"as of {as_of}", "examples": out},
                              ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)} ({OUT.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
