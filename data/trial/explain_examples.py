r"""The Visualization Engine's built-in examples (T092), run through the real engines.

Each example is a made-up work placed in a real district of the eSAKSHI dashboard tables (40,935
works, data/esakshi_dashboard.py), so the price bands, the district's other works and the rules
it meets are the real ones. The page (apps/web/src/app/explain) shows them to anyone, signed in
or not; a judge's own example goes to the live engine instead (POST /api/v1/explain).

Writes apps/web/public/explain/examples.json: per example, its title, a one-line story, what was
typed, and the trace (drishti/explain.py). Text is masked; no MP is named.

T099 + T100 (3 Oct 2026): the Cost and Duplicate checks answer from the implementing agency's cost
estimate form, so the "price", "two" and "repeat" examples carry a made-up form (a complete one,
as data/trial/cost_v3_holdout.py builds), and the repeat is a made-up completed work of the same
kind whose own form's map pin is 20 m away. No real work is given a form.

T125 (4 Oct 2026, four agents): the temple and the vague sum are gone (those guideline rules are no
longer checked). Time & Rules gets two examples ("fast": recorded complete days after sanction,
long before its own estimate allowed, with no site video; "late": a hall past its promised time
whose last three site videos show no change), and Site Progress one ("video": a first visit
whose footage was filmed for another hall, with the readings the video job made in
data/trial/capture_e2e.py). "two" is now the costly lights at the place of lights already paid for.

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
sys.path.insert(0, str(ROOT / "data" / "trial"))
sys.path.insert(0, str(ROOT / "apps" / "engine"))
from cost_v3_holdout import form as estimate_form  # noqa: E402
from esakshi_dashboard import load  # noqa: E402

from drishti.batch import indexes  # noqa: E402
from drishti.cost_form.validate import validate  # noqa: E402
from drishti.evaluation.stats import build_store  # noqa: E402
from drishti.explain import explain  # noqa: E402
from drishti.pipeline.orchestrator import Context  # noqa: E402

OUT = ROOT / "apps" / "web" / "public" / "explain" / "examples.json"
SUMMARY = ROOT / "data" / "trial" / "results" / "explain_examples.txt"


def _district(works: list[dict]) -> dict:
    """The district with the most works that carry a recommendation date (richest comparisons)."""
    n = Counter(w["district_lgd"] for w in works if w.get("recommended_date"))
    lgd = n.most_common(1)[0][0]
    return next(w for w in works if w["district_lgd"] == lgd)


LIGHTS, PRICE_EACH, MP_AMOUNT = 10, 48_000.0, 240_000.0
FAIR_EACH = 20_900.0               # about the district's median solar light
PIN = (25.7463, 82.6837)
METRE = 1 / 111_195


def _lights_form(as_of, each: float = PRICE_EACH, mp: float = MP_AMOUNT,
                 pin: tuple[float, float] | None = None) -> dict:
    """The agency's complete form for 10 solar street lights (at Rs 48,000 each against the MP's
    Rs 2.4 lakh, with its reason, unless told otherwise); every "looks unusual" check confirmed,
    as an agency would."""
    f = estimate_form("STREET_LIGHT|solar", LIGHTS, each, mp)
    if LIGHTS * each > 1.10 * mp:
        f["totals"]["reason_differs_from_mp"] = ("the MP's figure was a first estimate; the "
                                                 "survey found ten poles are needed")
    if pin:
        f["sites"][0]["location"].update(lat=pin[0], lon=pin[1])
    f["confirmed"] = [i["key"] for i in validate(f, today=as_of)["issues"]
                      if i["level"] == "confirm"]
    return f


def _pinned(work_type: str, lat: float, lon: float, nature: str = "new") -> dict:
    """The parts of a form the Duplicate check reads: the kind of asset, its map pin, its nature."""
    return {"work": {"work_type": work_type, "nature": nature},
            "sites": [{"location": {"lat": lat, "lon": lon}}]}


def _timed(work_type: str, start, months: float) -> dict:
    """The parts of a form Time & Rules reads: the kind of work and the agency's estimated time
    to completion (the rest is left empty, so Cost says the form is not ready)."""
    return {"work": {"work_type": work_type, "nature": "new"},
            "timing": {"start_month": f"{start:%Y-%m}", "duration_months": months}}


def _visit(n: int, kind: str, when, change: str | None = None, **more) -> dict:
    """A made-up site video as the video job leaves it: sealed, filmed in the app, at the site,
    at its five marked viewpoints."""
    readings = {"sealed": True, "in_app": True, "quality_ok": True, "gps_inside": True,
                "views_match_site": None if kind == "baseline" else True,
                "viewpoints_expected": 5, "viewpoints_matched": 5, "change": change, **more}
    return {"visit_id": f"V{n}", "kind": kind, "captured_at": when.isoformat(),
            "readings": readings}


def earlier_lights(base: dict, as_of) -> dict:
    """Made-up solar lights of the district, completed last year, with their form's map pin."""
    return {**base, "work_id": "EXAMPLE-0", "work_type_code": "STREET_LIGHT",
            "amount": LIGHTS * FAIR_EACH, "status": "COMPLETED",
            "description": "Installation of 10 solar street lights near Shiv Mandir chowk in "
                           "village Sikrara",
            "recommended_date": as_of - timedelta(days=520),
            "sanction_date": as_of - timedelta(days=470),
            "completed_date": as_of - timedelta(days=300),
            "cost_form": _pinned("STREET_LIGHT", *PIN)}


def _base(d: dict, as_of) -> dict:
    return {"source": "SCENARIO", "house": None, "term": None, "state_lgd": d.get("state_lgd"),
            "state_name": d.get("state_name"), "district_lgd": d["district_lgd"],
            "district_name": d.get("district_name"), "constituency": None, "mp_name": None,
            "agency_name": d.get("agency_name"), "fy": None, "category": None,
            "status": "RECOMMENDED", "recommended_date": as_of, "sanction_date": None,
            "completed_date": None, "quantity": None, "quantity_unit": None,
            "is_outside_constituency": False, "signals": {}}


def examples(works: list[dict], as_of) -> list[tuple[str, str, dict]]:
    base = _base(_district(works), as_of)
    lights = _lights_form(as_of)
    fast_sanction = as_of - timedelta(days=100)
    hall_sanction = as_of - timedelta(days=480)
    monthly = [_visit(1, "baseline", hall_sanction + timedelta(days=20))]
    for n in range(1, 16):                     # monthly visits: work, then a stop for 3 months
        monthly.append(_visit(n + 1, "monthly", hall_sanction + timedelta(days=20 + 30 * n),
                              "changed" if n <= 12 else "no_change"))
    return [
        ("ordinary", "An ordinary new road",
         {**base, "work_id": "EXAMPLE-1", "work_type_code": "ROAD_CC", "amount": 480000.0,
          "description": "Construction of CC road 250 mtr from Panchayat Bhawan to Primary "
                         "School in village Bhagwatipur, Ward No 4"}),
        ("price", "An estimate above the standard light and the MP's amount",
         {**base, "work_id": "EXAMPLE-4", "work_type_code": "STREET_LIGHT", "amount": MP_AMOUNT,
          "description": "Installation of 10 solar street lights from the bus stand to the "
                         "Primary School in village Sikrara", "cost_form": lights}),
        ("repeat", "A sanctioned work at the same site",
         {**base, "work_id": "EXAMPLE-6", "work_type_code": "STREET_LIGHT",
          "amount": LIGHTS * FAIR_EACH,
          "description": "Solar street light adhishthapan, Shiv Mandir chowk, gram Sikrara",
          "cost_form": _lights_form(as_of, FAIR_EACH, LIGHTS * FAIR_EACH,
                                    (PIN[0] + 20 * METRE, PIN[1]))}),
        ("dates", "Completed before it was recommended",
         {**base, "work_id": "EXAMPLE-5", "work_type_code": "ROAD_CC", "amount": 760000.0,
          "status": "COMPLETED", "recommended_date": as_of - timedelta(days=120),
          "sanction_date": None, "completed_date": as_of - timedelta(days=200),
          "description": "Construction of CC road 400 mtr from main road to cremation ground"}),
        ("fast", "Finished long before its own estimate allows",
         {**base, "work_id": "EXAMPLE-8", "work_type_code": "ROAD_CC", "amount": 690000.0,
          "status": "COMPLETED", "recommended_date": fast_sanction - timedelta(days=40),
          "sanction_date": fast_sanction, "completed_date": fast_sanction + timedelta(days=6),
          "description": "Construction of CC road 350 mtr from Anganwadi Kendra to the pond in "
                         "village Bhagwatipur",
          "cost_form": _timed("ROAD_CC", fast_sanction, 4)}),
        ("late", "Past its own promised time, and stopped",
         {**base, "work_id": "EXAMPLE-9", "work_type_code": "COMMUNITY_HALL",
          "amount": 1800000.0, "status": "SANCTIONED",
          "recommended_date": hall_sanction - timedelta(days=40), "sanction_date": hall_sanction,
          "description": "Construction of community hall with kitchen near the Panchayat "
                         "Bhawan in village Bhagwatipur",
          "cost_form": _timed("COMMUNITY_HALL", hall_sanction, 8),
          "site_visits": [v for v in monthly if v["captured_at"] <= as_of.isoformat()]}),
        ("video", "A site video filmed for another work",
         {**base, "work_id": "EXAMPLE-10", "work_type_code": "COMMUNITY_HALL",
          "amount": 1500000.0, "status": "SANCTIONED",
          "recommended_date": as_of - timedelta(days=100),
          "sanction_date": as_of - timedelta(days=60),
          "description": "Construction of community hall in village Sikrara",
          "cost_form": _timed("COMMUNITY_HALL", as_of - timedelta(days=60), 8),
          "site_visits": [_visit(1, "baseline", as_of - timedelta(days=45),
                                 reused_from=[{"work_id": "EXAMPLE-11", "visit_id": "V7",
                                               "frames": 42}],
                                 same_place_as=[{"work_id": "EXAMPLE-11", "inliers": 875}])]}),
        ("two", "Two checks agree",
         {**base, "work_id": "EXAMPLE-7", "work_type_code": "STREET_LIGHT", "amount": MP_AMOUNT,
          "description": "Installation of 10 solar street lights at Shiv Mandir chowk in village "
                         "Sikrara", "cost_form": _lights_form(as_of, pin=(PIN[0] + 20 * METRE,
                                                                          PIN[1]))}),
    ]


STORIES = {
    "ordinary": "A plain road with its length, both ends and its village named: what most works "
                "look like.",
    "price": "The MP recommended Rs 2.4 lakh for 10 solar street lights. The agency's cost form "
             "prices them at Rs 48,000 each, far above what 98 in 100 such lights cost in this "
             "district, and its estimate is twice the MP's amount: both signals, so it asks.",
    "repeat": "Ten new solar lights, fairly priced, whose form puts the map pin 20 m from ten "
              "lights the scheme already paid for and completed there; the form does not say it "
              "continues that work.",
    "dates": "The record says the road was finished 80 days before the MP recommended it.",
    "fast": "A 350 m road recorded complete 6 days after its sanction. The agency's own form "
            "promised 4 months, so its comfort window opens a month after the start, and no "
            "site video shows the road being built. (Only the form's timing is filled in here.)",
    "late": "A community hall the agency promised in 8 months, still open 16 months after its "
            "sanction. Its monthly site videos showed the walls rising, then the last three show "
            "no change at the same viewpoints: past its own time, and stopped.",
    "video": "The first site video of a new hall carries 42 frames already seen on another "
             "hall's video, and its viewpoints show that hall's place. (The readings are the ones "
             "the video job made in the team's end-to-end trial, filming one made-up site for "
             "two works.)",
    "two": "The same costly lights, now at the place where the scheme already paid for ten "
           "lights: two different checks each raise a question, and together they count for "
           "more than either alone.",
}


def main() -> None:
    works, info = load()
    as_of = info["as_of"]
    base = _base(_district(works), as_of)
    known = works + [earlier_lights(base, as_of)]   # the made-up earlier lights, with a pin
    ctx = Context(stats=build_store(works), as_of=as_of, data=indexes(known))
    out, lines = [], []
    for key, title, work in examples(works, as_of):
        trace = explain(work, ctx)
        out.append({"id": key, "title": title, "story": STORIES[key], "trace": trace})
        lines.append(f"{key:9} {trace['result']['band']:8} {trace['result']['score']:.3f} "
                     f"{trace['result']['colour']} "
                     f"{[f['code'] for c in trace['checks'] for f in c['findings']]}")
        print(lines[-1])
    SUMMARY.write_text(f"{len(works):,} dashboard works, as of {as_of}; district "
                       f"{out[0]['trace']['input']['district']}\n" + "\n".join(lines) + "\n",
                       encoding="utf-8")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"source": f"eSAKSHI dashboard tables, {len(works):,} works, "
                                         f"as of {as_of}", "examples": out},
                              ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)} ({OUT.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
