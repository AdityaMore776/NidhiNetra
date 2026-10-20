r"""The prototype examples the public site shows: every one a filled work form, graded (T132, T142).

The owner (6 Oct 2026): "we are currently grading forms, so each of the risk examples should now
contain the form details and demonstrations". So the public view no longer shows eSAKSHI
recommendations rated from their records alone (T132 showed five, with the live engine's count of
every work). Each example is a filing of the website's work intelligence form (PSWIF v1.1): the
form as a made-up agency filled it, in the real district of Jaunpur, graded by the four agents
exactly as the live form check does. They are data/trial/work_form_examples.py's filings (its
apps/web/public/work-form/examples.json), so a work's page, the dashboard and the form page all
show the same filing and the same numbers:

  clean            an honest CC road: every agent looks, none asks
  cost_padded      every material about 25% above the district's rates
  cost_quantity    twice the cement the road's size can use
  cost_lights      solar lights at Rs 48,000 each, twice the MP's amount
  cost_labour      masons at 2.4 times the district's day rate (34 workers, not questioned)
  dup_pin          a "new" road pinned 20 m from a road completed last year
  dup_rebuild      a hall declared a rebuild of one finished 16 months earlier
  dup_split        one lane filed as three works, each just under Rs 5 lakh
  time_fast        a road recorded complete 6 days after sanction, never filmed
  time_late        eight months promised, sixteen months on, and stopped
  site_reused      the first site video was filmed for another work
  site_claim       "roof slab cast", twice, and the videos do not show it
  site_elsewhere   a monthly video filmed 2.4 km away

Each example's page reads its form from the work-form file (`showcase.form_example`); this file
carries the score, the reasons and the four checks in the work page's shape. Nothing here is a real
agency, person or work. Writes apps/web/public/showcase/examples.json and
results/showcase_examples.txt; stops if a filing no longer raises what its example says.

Run:  apps\engine\.venv\Scripts\python.exe data\trial\showcase_examples.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "data"))
sys.path.insert(0, str(ROOT / "data" / "trial"))
sys.path.insert(0, str(ROOT / "apps" / "engine"))
import work_form_examples as wf  # noqa: E402

from drishti.agents import registry  # noqa: E402
from drishti.agents.contract import check_plain_language  # noqa: E402

FILINGS = ROOT / "apps" / "web" / "public" / "work-form" / "examples.json"
OUT = ROOT / "apps" / "web" / "public" / "showcase" / "examples.json"
SUMMARY = ROOT / "data" / "trial" / "results" / "showcase_examples.txt"

# (filing, the checks it is about, why it is a textbook case). The order is the order the site
# lists them in.
EXAMPLES = [
    ("clean", ["cost_estimate", "dup_split", "time_rules", "site_progress"],
     "Most filings look like this one. Every check reads it and none asks: the prices are the "
     "district's, the quantities fit the road's size, nothing is sanctioned at its pin, and the "
     "first site videos show the work the agency claims. A check that stays quiet here keeps the "
     "review queue short."),
    # T170: more normal works, then edge cases, then suspected schemes (owner, 20 Oct 2026)
    ("ok_lights", ["cost_estimate"],
     "Lights are judged by the price of one light against what the district's own lights cost. "
     "Rs 21,000 a light is the district's usual price and the estimate matches the MP's amount, "
     "so Cost has nothing to ask."),
    ("ok_hall_done", ["time_rules", "site_progress"],
     "Finished inside the agency's own promise, with a video every month: Time & Rules finds the "
     "pace believable, and NidhiLens (Fine-Tuned Site Progress Model) sees every claim in the "
     "videos, up to the finished hall."),
    ("ok_next_lane", ["dup_split"],
     "Two roads 30 m apart look alike on a map, but this one runs beside the old road, never on "
     "it. Duplicate Work compares the line of each road, not only how near the pins are, so the "
     "next street over is never asked about."),
    ("ok_hindi_gst", ["cost_estimate"],
     "Honest forms are written in different ways. Cost reads item names in Hindi as the same "
     "materials, and counts GST added on top as tax when the form says its rates leave tax out, "
     "so neither raises a question."),
    ("edge_slow_sanction", ["time_rules"],
     "A slow sanction is how most offices work: 60% of works wait past 75 days. Time & Rules "
     "records it about the office as a small note, which never puts the work in the queue on its "
     "own."),
    ("edge_fast_filmed", ["time_rules", "site_progress"],
     "Speed alone is not a question. A road finished in 25 days is believed when videos filmed "
     "before the finish show it being built; with only a final video, or none, the speed would "
     "stay unexplained."),
    ("edge_rain_pause", ["site_progress"],
     "Two months with no change would look like a stopped site. Here the agency's own claim says "
     "the work paused for rain, the videos agree, and the earlier months show steady work, so "
     "nothing is asked."),
    ("edge_extension", ["dup_split"],
     "A road starting where a finished road ends could look like a repeat. The agency declares it "
     "an extension, names the earlier work, and it lies beyond the old road's end, so Duplicate "
     "Work notes the link and asks nothing."),
    ("edge_weak_gps", ["site_progress"],
     "Phones lose their position under trees. A video 110 m from the pin is allowed when the "
     "phone itself said it could be 45 m out and the views match the site; the same distance "
     "with a confident fix would be checked."),
    ("edge_price_rise", ["cost_estimate"],
     "Prices rise between filings. Rates 9% above older estimates sit inside the 10% the CPWD "
     "Works Manual allows with recorded reasons, so Cost asks nothing; a bigger gap would be "
     "checked."),
    ("edge_late_moving", ["time_rules", "site_progress"],
     "Most works finish late. Because every monthly video shows new work, Time & Rules asks only "
     "for a follow-up on progress; the same delay at a site that has stopped is a question (the "
     "example \"Eight months promised, sixteen months on, and stopped\")."),
    ("cost_padded", ["cost_estimate"],
     "No single line is far off. The question comes from the whole estimate, every line priced at "
     "what other agencies in the district pay for the same item. Wages within twice a trade's "
     "rate are the agency's call, so only the materials make the gap."),
    ("cost_quantity", ["cost_estimate"],
     "The rates are fair; the quantity is not. The road's own size on the form (300 m x 3.5 m x "
     "150 mm) says how much cement it can use, so twice that is a certain question, even with a "
     "reason written on the line."),
    ("cost_lights", ["cost_estimate"],
     "Neither signal alone asks: an estimate above the MP's amount can have a reason, and a costly "
     "light can have a better specification. Cost asks only when the price per light is far "
     "above the district's own range and the estimate is well above the MP's amount."),
    ("cost_labour", ["cost_estimate"],
     "Labour is judged trade by trade. The road's 34 workers, its helpers and its machine "
     "operators are the agency's call; only a day rate at twice what other agencies pay the same "
     "trade is a question."),
    ("dup_pin", ["dup_split"],
     "The words differ from the old road's, so a word match would miss it. The map pin on the "
     "agency's own form places it on top of a work the scheme already paid for."),
    ("dup_rebuild", ["dup_split"],
     "The agency declares the rebuild itself. A hall should not need rebuilding 16 months after it "
     "was completed, so the first work's completion and quality need checking."),
    ("dup_split", ["dup_split"],
     "Each piece is ordinary on its own; the question appears only when the pieces are read "
     "together. The agent asks only when every piece sits within 4% of a limit, the strictest "
     "test, so ordinary look-alike works never reach the queue."),
    ("time_fast", ["time_rules", "site_progress"],
     "The agency's own estimate on the form (about four months) is the yardstick, not a fixed "
     "rule. Recorded complete in 6 days with no site video at all, two checks point at the same "
     "work."),
    ("time_late", ["time_rules", "site_progress"],
     "Time & Rules judges the work by the agency's own promise plus a grace period, and the site "
     "videos say the work has stopped, not merely slowed. NidhiLens (Fine-Tuned Site Progress Model) itself asks nothing: the "
     "videos are genuine."),
    ("site_reused", ["site_progress"],
     "The video passes every check at the site. Only comparing it with every earlier video shows "
     "the footage was filmed for another work, at that work's place."),
    ("site_claim", ["site_progress"],
     "NidhiLens (Fine-Tuned Site Progress Model) judges the agency's own claims against its videos: shown, not shown or can't "
     "tell. A claim not shown twice in a row is a question; once could be a bad angle."),
    ("site_elsewhere", ["site_progress"],
     "A video counts as filmed elsewhere only when its GPS and its views both disagree with the "
     "site, so a weak GPS fix alone never asks."),
    ("dup_split_spread", ["dup_split"],
     "Filing the parts 35 days apart slips past the strict 30-day test. Duplicate Work also reads "
     "parts near a limit filed up to 90 days apart, a rule measured on the real works before it "
     "was added, and asks for a check."),
    ("dup_same_hall", ["dup_split"],
     "The pin is 120 m from the old hall, past the 50 m that makes two pins one site. The same "
     "words and the same size, with no earlier work named on the form, still ask for a check: "
     "the first site video will show whether the hall already stands."),
    ("site_no_first_visit", ["site_progress"],
     "Every work with a form is filmed before work starts. Without that first visit, a video of a "
     "finished hall cannot show the hall is new: it may have stood before the sanction, or been "
     "paid for under another scheme."),
    ("site_gps_off", ["site_progress"],
     "Every site video must record where it was filmed. One video without a location is forgiven; "
     "three in a row leave nothing to show any of them was filmed at this site, so it is a "
     "question."),
    ("time_filmed_last_day", ["time_rules", "site_progress"],
     "A video filmed on the day the work is called complete shows it finished, not being built. "
     "The 6-day finish stays unexplained, and the missing first visit is asked about too: two "
     "checks agree."),
    ("cost_other_charges", ["cost_estimate"],
     "Every line is fairly priced, so a line-by-line check passes it. Cost also compares the "
     "whole estimate, charges included, with the fair price for the road's size, and the extra "
     "20% shows there."),
    ("cost_claimed_reason", ["cost_estimate"],
     "A reason written on the form can soften a question to a check, never clear it. Nothing "
     "confirms the hilly, head-load site the form describes, and Jaunpur lies in the plains, so "
     "the 18% gap is checked."),
    ("cost_ghost_workers", ["cost_estimate"],
     "Wages can be fair while the number of workers is not. Cost compares the person-days with "
     "other agencies' crews on roads of this size; three times as many asks for a check of the "
     "muster roll and of the crew in the site video."),
]


def detail_of(ex: dict, district_lgd: str | None) -> dict:
    """A filing's stored trace (the same engines as the live form check) in the work page's
    shape: the work, its score, its reasons and the four checks."""
    t, form = ex["trace"], ex["form"]
    i, s, r = t["input"], t["scoring"], t["result"]
    work = {"work_id": form["recommendation_ref"], "source": "SCENARIO", "house": None,
            "term": None, "state_name": i["state"], "district_lgd": district_lgd,
            "district_name": i["district"], "constituency": None, "mp_name": None,
            "agency_name": i["office"], "fy": form.get("financial_year") or None,
            "work_type_code": i["work_type"], "category": None, "description": i["description"],
            "amount": i["amount"], "recommended_date": i["recommended"],
            "completed_date": i["completed"], "status": i["status"],
            "sanction_date": i["sanctioned"]}
    names = {c["id"]: c["name"] for c in t["checks"]}
    before, adds = 0.0, {}
    for step in s.get("chain", []):                 # each agent's share of the score
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
    alerts = [c["id"] for c in t["checks"] if any(f["risk"] > 0 for f in c["findings"])]
    assessment = {"work_id": work["work_id"], "assessed_at": t["as_of"], "score": r["score"],
                  "band": r["band"], "limited": r["limited"], "priority": r["score"],
                  "parts": {"parts": parts, "hard_trigger": None, "reasons": reasons},
                  "validation": [], "agents": agents, "alerts": alerts,
                  "headline": reasons[0]["text_en"] if reasons else None, "compact": False,
                  "case_id": None, "case_size": None}
    return {"work": work, "assessment": assessment}


def row(detail: dict) -> dict:
    """The list row (queue, all works) for a filing."""
    w, a = detail["work"], detail["assessment"]
    keys = ("work_id", "source", "district_lgd", "district_name", "state_name", "work_type_code",
            "description", "amount", "status", "recommended_date")
    return {**{k: w[k] for k in keys}, "band": a["band"], "score": a["score"],
            "priority": a["priority"], "limited": a["limited"], "alerts": a.get("alerts") or [],
            "headline": a.get("headline"), "case_id": a.get("case_id"),
            "case_size": a.get("case_size")}


def main() -> None:
    filings = json.loads(FILINGS.read_text(encoding="utf-8"))
    by_id = {e["id"]: e for e in filings["examples"]}
    if set(by_id) != {k for k, _a, _w in EXAMPLES}:
        sys.exit(f"the filings changed: {sorted(set(by_id) ^ {k for k, _a, _w in EXAMPLES})}")
    works, _info = wf.load()
    district_lgd = next(w["district_lgd"] for w in works if w.get("district_name") == wf.DISTRICT)

    out, lines, bad = [], [], []
    for n, (key, agents, why) in enumerate(EXAMPLES, 1):
        ex = by_id[key]
        check_plain_language(why)
        detail = detail_of(ex, district_lgd)
        a = detail["assessment"]
        fired = sorted(a["alerts"])
        meant = sorted({c for c, codes in (ex.get("codes") or {}).items() if codes}) \
            if ex.get("codes") else None
        asks = sorted(x["agent"] for x in a["agents"] if x["agent"] in agents
                      and any(f["risk"] > 0 for f in x["findings"]))
        kind = ex.get("kind", "suspected")
        if kind == "normal" and fired:
            bad.append(f"{key}: an honest filing raises {fired}")
        if kind == "edge" and a["band"] != "LOW":
            bad.append(f"{key}: an edge case reaches {a['band']}")
        if kind == "suspected" and not asks:
            bad.append(f"{key}: none of {agents} asks now")
        if meant is not None and meant != fired:
            bad.append(f"{key}: raises {fired}, meant {meant}")
        detail["showcase"] = {"n": n, "key": key, "title": ex["title"], "agents": agents,
                              "kind": kind,
                              # Step by step (/explain) walks through the same filings (T142)
                              "shows": ex["story"], "why": why, "explain": key,
                              "form_example": key, "later": ex["later"],
                              "form_ready": ex["form_ready"]}
        out.append({"key": key, "row": row(detail), "detail": detail})
        lines.append(f"{n:2} {key:15} {detail['work']['work_id']:14} {a['band']:6} "
                     f"{a['score']:.3f} asks={fired}")
        print(lines[-1])
    if bad:
        sys.exit("the examples no longer show what they say:\n" + "\n".join(bad))

    bands = {b: sum(1 for e in out if e["row"]["band"] == b)
             for b in ("CRITICAL", "HIGH", "MEDIUM", "LOW")}
    engines = registry.engines()
    alerts = {e.id: sum(1 for x in out if e.id in x["row"]["alerts"]) for e in engines}
    summary = {"works": len(out), "amount": sum(e["row"]["amount"] or 0 for e in out),
               "bands": bands, "snapshot_date": filings["as_of"],
               "agents": [{"id": e.id, "name": e.name, "question": e.question,
                           "built": e.assess is not None, "weight": e.weight,
                           "weight_note": e.weight_note, "alerts": alerts[e.id]}
                          for e in engines]}
    about = (f"{len(out)} prototype examples (T142): each a filing of the website's work "
             "intelligence form by a made-up agency in the real district of Jaunpur, graded by "
             "the four agents as the live form check does (data/trial/work_form_examples.py).")
    OUT.write_text(json.dumps({"about": about, "summary": summary, "examples": out},
                              ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    SUMMARY.write_text(f"{len(out)} form filings graded (as of {filings['as_of']}), "
                       f"bands {bands}\n" + "\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)} ({OUT.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
