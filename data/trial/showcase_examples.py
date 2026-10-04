r"""The ten prototype examples the public site shows (T132), instead of all 2,09,993 works.

Judges see ten works, each a textbook case of one agent (or two agreeing) doing its job, with the
same detail page as any work: the score, the reasons and what each of the four checks said. The
public view reads them from apps/web/public/showcase/examples.json, a static file, so the pages
open without waiting for the engine to start. Signed-in staff still get every work from the engine.

Five are REAL eSAKSHI works, taken as the live engine assessed them (GET /api/v1/works/<id>):
  clean   an ordinary road where the checks ran and found nothing (most works look like this)
  fast    a Rs 41.5 lakh classroom block recorded complete 13 days after it was recommended
  wait    a school laboratory waiting 598 days for sanction, graded by the measured wait curve
  split   one hill road filed as four works, each a few hundred rupees under the Rs 5 lakh limit
  park    two alike works at the Rs 10 lakh limit that have also waited 496 days: two checks agree
Five are MADE-UP works, because no real work has a cost estimate form or a site video yet, and
Cost and Site Progress read only those. They are the Visualization Engine's examples
(data/trial/explain_examples.py, run through the real engines on the eSAKSHI dashboard tables);
this script reuses their stored traces from apps/web/public/explain/examples.json, so the numbers
match the Step by step page exactly:
  price, repeat, late, video, two

Picked by eye (4 Oct 2026) from the live review queue (217 cases), the Medium works and a random
sample of clean completed roads; descriptions that name a private person or carry a political
name were passed over. Descriptions go through the site's masker and no MP is named.

Run:  apps\engine\.venv\Scripts\python.exe data\trial\showcase_examples.py [--base URL]
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "apps" / "engine"))
from drishti.validation.pii import mask  # noqa: E402

EXPLAIN = ROOT / "apps" / "web" / "public" / "explain" / "examples.json"
OUT = ROOT / "apps" / "web" / "public" / "showcase" / "examples.json"
SUMMARY = ROOT / "data" / "trial" / "results" / "showcase_examples.txt"
BASE = "https://nidhinehtra.vercel.app/api/v1"

# (key, source, work id or explain example id, title, agents it shows, what it shows, why it is a
# textbook case). The order is the order the site lists them in.
EXAMPLES = [
    ("clean", "REAL", "WS/MP347/2024-2025/129604",
     "An ordinary village road: nothing to ask",
     ["dup_split", "time_rules"],
     "A 200 m road in Alappuzha, completed about six months after it was recommended. Duplicate "
     "Work compared it with the district's 261 other works and Time & Rules checked its dates: no "
     "question. Cost and Site Progress say plainly that they had nothing to read yet.",
     "Most works look like this one. A check that stays quiet here, and says \"not checked\" "
     "instead of giving a false all-clear, is what keeps the review queue short."),
    ("fast", "REAL", "WS/MP736/2023-2024/46796",
     "A Rs 41.5 lakh classroom block recorded complete in 13 days",
     ["time_rules"],
     "Two classrooms worth Rs 41.5 lakh are recorded complete 13 days after the MP recommended "
     "them. Time & Rules knows how long a construction of this kind and size needs, so it asks "
     "for the completion certificate and the dates.",
     "Nothing in the record looks wrong on its own: the dates are in order and the amount is "
     "normal. The question comes from comparing the time taken with what the work needs. Flags "
     "of this kind were worth a look 13 times in 13 when read by eye."),
    ("wait", "REAL", "NOREF-6e3fa16301ff14",
     "A school laboratory waiting 598 days for sanction",
     ["time_rules"],
     "The guidelines give 75 days from recommendation to sanction. This work has waited 598 "
     "days, and only 4 in 100 works recommended that long ago were still waiting.",
     "Thousands of works pass 75 days, so the rule alone would bury an officer. Time & Rules "
     "grades each wait against how long other works of the same time really waited, and a long "
     "wait on its own stays Medium: it asks the office, but does not jump the queue."),
    ("split", "REAL", "WS/MP18003/2024-2025/157519",
     "One hill road filed as four works, each just under Rs 5 lakh",
     ["dup_split"],
     "Four works with almost the same words, at one place, recommended on the same day, each "
     "between Rs 4,99,844 and Rs 4,99,976: Rs 20 lakh together. Duplicate Work asks whether one "
     "job was cut into pieces to stay under the Rs 5 lakh limit.",
     "Each piece is ordinary on its own; the question appears only when the pieces are read "
     "together. The agent asks only when every piece sits within 4% of a limit, the strictest "
     "test, so ordinary look-alike works stay notes and never reach the queue."),
    ("park", "REAL", "NOREF-ad21b676867cba",
     "Two checks agree: a park filed twice at the limit, waiting 496 days",
     ["dup_split", "time_rules"],
     "Duplicate Work finds two alike Rs 10 lakh park works filed on the same day at one place, "
     "each at the Rs 10 lakh limit. Time & Rules finds the work has waited 496 days for "
     "sanction, longer than 93 in 100 works of its time.",
     "Two different checks, reading different facts, point at the same work. Each adds its own "
     "measured chance (pieces like these were worth a look 12 times in 14), so together they "
     "rank the work higher than either would alone."),
    ("price", "SCENARIO", "price",
     "Solar lights at Rs 48,000 each, twice the MP's amount",
     ["cost_estimate"],
     "The MP recommended Rs 2.4 lakh for 10 solar street lights. The agency's cost estimate form "
     "prices them at Rs 48,000 each, while 98 in 100 of the 136 similar works in the district "
     "cost at most Rs 20,896 a light, and its estimate is twice the MP's amount.",
     "Neither signal alone asks: an estimate above the MP's amount can have a good reason (this "
     "one gives one), and a costly light can have a better specification. Cost asks only when "
     "the price per light is far above the district's own range and the estimate is well above "
     "the MP's amount."),
    ("repeat", "SCENARIO", "repeat",
     "New lights 20 m from lights the scheme already paid for",
     ["dup_split"],
     "Ten new solar lights, fairly priced, whose form puts the map pin 20 m from ten lights of the "
     "same kind completed there last year. The form does not say it continues that work.",
     "The words differ (\"adhishthapan\", \"gram Sikrara\"), so a word match would miss it, and "
     "the price is fair, so Cost is quiet. Only the map pin on the agency's own form places it "
     "on top of a completed work."),
    ("late", "SCENARIO", "late",
     "A community hall past its own promised time, and stopped",
     ["time_rules", "site_progress"],
     "The agency promised the hall in 8 months. Sixteen months after sanction it is still open, "
     "and its last three monthly site videos show no change at the same viewpoints.",
     "Time & Rules judges the work by the agency's own promise, not a fixed rule, and uses the "
     "site videos to say the work has stopped. Site Progress raises nothing itself: the videos "
     "are genuine and nobody claimed progress they do not show."),
    ("video", "SCENARIO", "video",
     "A first site video filmed at another hall",
     ["site_progress"],
     "The first site video of a new hall is sealed, GPS-stamped and filmed in the app, yet 42 of "
     "its frames were already filed for another hall, and its viewpoints show that hall's place.",
     "The video passes every at-site check (sealed, in the app, inside the site). Only comparing "
     "it with every earlier video shows it is old footage of another work."),
    ("two", "SCENARIO", "two",
     "Two checks agree: costly lights at a place already paid for",
     ["cost_estimate", "dup_split"],
     "The same costly lights as the price example, now pinned 20 m from the ten lights the scheme "
     "already paid for. Cost and Duplicate Work each raise a question.",
     "Two different checks, each reading a different part of the form, point at the same work, "
     "and together they count for more than either alone."),
]

# the checks that must raise a question on each example (Site Progress reads the "late" hall's
# videos but asks nothing: the videos are genuine)
FIRES = {"clean": [], "fast": ["time_rules"], "wait": ["time_rules"], "split": ["dup_split"],
         "park": ["dup_split", "time_rules"], "price": ["cost_estimate"], "repeat": ["dup_split"],
         "late": ["time_rules"], "video": ["site_progress"], "two": ["cost_estimate", "dup_split"]}

WORK_KEYS = ("work_id", "source", "house", "term", "state_name", "district_lgd", "district_name",
             "constituency", "agency_name", "fy", "work_type_code", "category", "description",
             "amount", "recommended_date", "completed_date", "status", "sanction_date")


def get(base: str, path: str) -> dict:
    url = base + urllib.parse.quote(path, safe="/?=&")
    with urllib.request.urlopen(url, timeout=180) as r:
        return json.load(r)


def real(base: str, work_id: str) -> dict:
    """A real work as the live engine assessed it, without the MP's name."""
    d = get(base, f"/works/{work_id}")
    work = {k: d["work"].get(k) for k in WORK_KEYS}
    work["mp_name"] = None
    work["description"] = mask(work["description"])
    a = d["assessment"]
    a.pop("versions", None)
    return {"work": work, "assessment": a}


def scenario(ex: dict, district_lgd: str | None) -> dict:
    """A made-up work's stored trace (Visualization Engine) in the work page's shape."""
    t = ex["trace"]
    i, s, r = t["input"], t["scoring"], t["result"]
    work = {"work_id": f"EXAMPLE-{ex['id'].upper()}", "source": "SCENARIO", "house": None,
            "term": None, "state_name": i["state"], "district_lgd": district_lgd,
            "district_name": i["district"], "constituency": None, "mp_name": None,
            "agency_name": i["office"], "fy": None, "work_type_code": i["work_type"],
            "category": None, "description": i["description"], "amount": i["amount"],
            "recommended_date": i["recommended"], "completed_date": i["completed"],
            "status": i["status"], "sanction_date": i["sanctioned"]}
    names = {c["id"]: c["name"] for c in t["checks"]}
    before, adds = 0.0, {}
    for step in s.get("chain", []):                 # each engine's share of the score
        adds[step["engine"]] = step["score"] - before
        before = step["score"]
    parts = [{"source": e, "label": names.get(e, e), "weight": round(adds[e], 4),
              "contribution": adds[e]} for e in adds]
    codes = {e["engine"]: e["findings"][0]["code"] for e in s.get("engines", []) if e["findings"]}
    by_name = {v: k for k, v in names.items()}
    reasons = []
    for x in r.get("reasons", []):
        e = by_name.get(x["engine"], x["engine"])
        reasons.append({"source": e, "label": x["engine"], "contribution": adds.get(e, 0.0),
                        "code": codes.get(e, ""), "text_en": x["text"], "text_hi": x["text_hi"],
                        "chance": x.get("chance"), "hit_rate": x.get("chance"),
                        "basis": x.get("basis"), "read": x.get("read")})
    agents = [{"agent": c["id"], "name": c["name"], "question": c["question"],
               "status": c["status"], "verdict": c["verdict"], "risk": c["risk"],
               "confidence": 0.0, "hard": False, "headline": c["headline"], "version": "",
               "findings": [{"code": f["code"], "text": f["text"], "hard": f.get("hard", False),
                             "risk": f["risk"], "evidence": {}} for f in c["findings"]],
               "limitations": c["limitations"], "evidence": {}, "duration_ms": 0}
              for c in t["checks"]]
    alerts = [c["id"] for c in t["checks"] if c["findings"]]
    assessment = {"work_id": work["work_id"], "assessed_at": t["as_of"], "score": r["score"],
                  "band": r["band"], "limited": r["limited"], "priority": r["score"],
                  "parts": {"parts": parts, "hard_trigger": None, "reasons": reasons},
                  "validation": [], "agents": agents, "alerts": alerts,
                  "headline": reasons[0]["text_en"] if reasons else None, "compact": False,
                  "case_id": None, "case_size": None}
    return {"work": work, "assessment": assessment}


def row(detail: dict) -> dict:
    """The list row (queue, all works) for a work."""
    w, a = detail["work"], detail["assessment"]
    keys = ("work_id", "source", "district_lgd", "district_name", "state_name", "work_type_code",
            "description", "amount", "status", "recommended_date")
    return {**{k: w[k] for k in keys}, "band": a["band"], "score": a["score"],
            "priority": a["priority"], "limited": a["limited"], "alerts": a.get("alerts") or [],
            "headline": a.get("headline"), "case_id": a.get("case_id"),
            "case_size": a.get("case_size")}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=BASE, help="the engine's /api/v1 to read the real works from")
    base = ap.parse_args().base.rstrip("/")

    live = get(base, "/dashboard/summary")
    districts = {(d["name"], d["state"]): d["district_lgd"]
                 for d in get(base, "/dashboard/districts")}
    explain = {e["id"]: e for e in json.loads(EXPLAIN.read_text(encoding="utf-8"))["examples"]}

    out, lines = [], []
    for n, (key, source, ref, title, agents, shows, why) in enumerate(EXAMPLES, 1):
        if source == "REAL":
            detail = real(base, ref)
        else:
            i = explain[ref]["trace"]["input"]
            detail = scenario(explain[ref], districts.get((i["district"], i["state"])))
        a = detail["assessment"]
        fired = sorted({x["agent"] for x in a["agents"]
                        if any(f["risk"] > 0 for f in x["findings"])})
        if fired != FIRES[key]:                     # the example must still show what it says
            sys.exit(f"{key}: the engine now raises {fired}, not {FIRES[key]}; pick again")
        detail["showcase"] = {"n": n, "key": key, "title": title, "agents": agents,
                              "shows": shows, "why": why,
                              "explain": ref if source == "SCENARIO" else None}
        out.append({"key": key, "row": row(detail), "detail": detail})
        lines.append(f"{n:2} {key:7} {source:8} {detail['work']['work_id']:30} {a['band']:6} "
                     f"{a['score']:.3f} fired={fired}")
        print(lines[-1])

    bands = {b: sum(1 for e in out if e["row"]["band"] == b)
             for b in ("CRITICAL", "HIGH", "MEDIUM", "LOW")}
    alerts = {aid: sum(1 for e in out if aid in (e["row"]["alerts"] or [])) for aid in
              (a["id"] for a in live["agents"])}
    summary = {"works": len(out), "amount": sum(e["row"]["amount"] or 0 for e in out),
               "bands": bands, "snapshot_date": live["snapshot_date"],
               "agents": [{**a, "alerts": alerts.get(a["id"], 0)} for a in live["agents"]]}
    scale = {"works": live["works"], "amount": live["amount"], "bands": live["bands"],
             "snapshot_date": live["snapshot_date"]}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    about = ("Ten prototype examples (T132): 5 real eSAKSHI works as the live engine assessed "
             "them, 5 made-up works for the checks that need a cost form or site video.")
    OUT.write_text(json.dumps({"about": about, "summary": summary, "scale": scale,
                               "examples": out},
                              ensure_ascii=False, indent=1), encoding="utf-8")
    SUMMARY.write_text(f"Live engine {base}, data up to {live['snapshot_date']}; "
                       f"{live['works']:,} works on the live site\n" + "\n".join(lines) + "\n"
                       f"bands {bands}\n", encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)} ({OUT.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
