r"""Five filings from form to risk score, end to end (T136).

The owner (5 Oct 2026): "create an end to end loop example (set of 5), of everything from form
filling, all the way to agent risk on the form, then create a placeholder for the site progress
agent ... put some legit values, then also put some things in other examples that will be flagged
by the agents".

Each filing is the website form (PSWIF v1.1) as an implementing agency fills it, in the real
district of Jaunpur, Uttar Pradesh. It runs through the same code as the live check
(POST /api/v1/work-form/check): the website form to the engine's cost form
(drishti/cost_form/pswif.py), the form's own check (validate.py), the four agents and the risk
score (drishti/explain.py over pipeline.assess_work). Site Progress is a placeholder here: it
starts with the first site video after sanction, and its field trial (T126) comes first.

  legit_road    an honest 300 m CC road at the district's rates           -> nothing to check
  legit_lights  20 solar street lights at Jaunpur's real median price      -> nothing to check
  cost_hidden   the honest road with Rs 5.5 lakh in a line nobody prices   -> Cost asks
  dup_pieces    one lane filed as three pieces laid end to end, each just under Rs 5 lakh,
                this one described in other words                          -> Duplicate asks
  many_flags    a "new" hall pinned 20 m from a hall finished 14 months ago, every material 40%
                high, and still not sanctioned 100 days on                 -> three agents ask

The honest values are set against what real works cost in Uttar Pradesh
(data/trial/up_real_check.py: reference/cost/uttar_pradesh.json, built from the eSAKSHI dashboard
tables): the page shows each filing's price per metre or per light beside the real works'.
Every agency, village and filing is made up; the district's 1,038 real works and the other demo
filings (data/trial/work_form_examples.py) are the record they are compared with.

Writes apps/web/public/end-to-end/examples.json and results/end_to_end_examples.txt; stops if a
filing no longer raises exactly what it is meant to.

Run:  apps\engine\.venv\Scripts\python.exe data\trial\end_to_end_examples.py
"""

from __future__ import annotations

import json
import statistics
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "data"))
sys.path.insert(0, str(ROOT / "data" / "trial"))
sys.path.insert(0, str(ROOT / "apps" / "engine"))
import work_form_examples as wf  # noqa: E402

from drishti.agents.cost_estimate import labour as labour_rules  # noqa: E402
from drishti.agents.cost_estimate import rates, whole  # noqa: E402
from drishti.agents.cost_estimate.agent import assess as cost_assess  # noqa: E402
from drishti.agents.time_rules import window as time_window  # noqa: E402
from drishti.batch import indexes  # noqa: E402
from drishti.cost_form import catalog, pswif  # noqa: E402
from drishti.cost_form.validate import validate  # noqa: E402
from drishti.evaluation.stats import build_store  # noqa: E402
from drishti.explain import explain  # noqa: E402
from drishti.pipeline.orchestrator import Context  # noqa: E402

OUT = ROOT / "apps" / "web" / "public" / "end-to-end" / "examples.json"
SUMMARY = ROOT / "data" / "trial" / "results" / "end_to_end_examples.txt"
UP_PRICES = ROOT / "apps" / "engine" / "drishti" / "reference" / "cost" / "uttar_pradesh.json"
METRE = wf.METRE
AGENCIES = ["Gramodaya Nirman Samiti", "Surya Prakash Urja Agency", "Path Pragati Works",
            "Sanyukt Vikas Agency", "Bhawan Nirman Ikai"]
VILLAGES = ["Rajepur", "Khutahan", "Dharmapur", "Madiyahun Khurd", "Barsathi Kalan",
            "Sujanganj"]


def build(as_of: date) -> tuple[list[dict], list[dict]]:
    """(the five filings, the background they add): each filing = {key, title, story, codes,
    form, record}."""
    m = lambda days: as_of - timedelta(days=days)  # noqa: E731
    out, bg = [], []

    def add(key, title, story, codes, p, **record):
        out.append({"key": key, "title": title, "story": story, "codes": codes, "form": p,
                    "record": record})

    # 1. an honest road, at the district's own rates (work_form_examples.RATE)
    p = wf.road("E2E-ROAD-1", AGENCIES[0], VILLAGES[0], 14, m(20), None)
    add("legit_road", "An honest 300 m CC road",
        "Every rate is what other agencies in Jaunpur pay; every quantity is what the road's "
        "size needs.", {}, p)

    # 2. honest solar street lights, at Jaunpur's real median price (up_real_check.py: 136 works)
    each = 20_900
    p = wf.lights("E2E-LIGHT-1", AGENCIES[1], VILLAGES[1], 15, m(15), each, 20 * each)
    p.update({"boq_qty_1": "20", "energy_quantity": "20", "rate_deviation_notes": "",
              "technical_estimate": f"{20 * each:.2f}", "mplads_share": f"{20 * each:.0f}",
              "work_title": f"20 solar street lights along the main lane, {VILLAGES[1]}",
              "scope_of_work": p["scope_of_work"].replace("10 standalone", "20 standalone")})
    add("legit_lights", "20 solar street lights at the usual price",
        f"Rs {each:,} a light: what 136 real solar street lights in Jaunpur cost.", {}, p)

    # 3. the honest road, with Rs 5.5 lakh more in equipment hire (a line no reader prices)
    p = wf.road("E2E-ROAD-2", AGENCIES[2], VILLAGES[2], 16, m(25), None)
    for n in range(1, 20):
        if "mixer" in str(p.get(f"boq_desc_{n}", "")).lower():
            p[f"boq_qty_{n}"] = "250"
            p[f"boq_just_{n}"] = "Mixer and vibrator on site for the whole season"
    total = wf.estimate_total(p)
    p.update(technical_estimate=f"{total:.2f}", mplads_share=f"{total:.0f}",
             mp_recommended_amount=f"{round(total, -3):.0f}")
    add("cost_hidden", "Rs 5.5 lakh hidden in equipment hire",
        "A mixer hired for 250 days on a road poured in about 30: every other line is honest.",
        {"cost_estimate": ["ESTIMATE_ABOVE_FAIR_PRICE"]}, p)

    # 4. one lane in three pieces laid end to end, each just under the Rs 5 lakh limit; the
    #    checked piece is described in other words (the wording rule alone would miss it)
    lat0, lon0 = wf.pin(17)
    pieces = []
    for i in range(3):
        piece = wf.road(f"E2E-LANE-{i + 1}", AGENCIES[3], VILLAGES[3], 17, m(40 - 4 * i), None,
                        length=95, width=3.5,
                        work_title=f"CC road in {VILLAGES[3]}, part {i + 1}",
                        latitude=f"{lat0 + 100 * i * METRE:.6f}",
                        start_lat=f"{lat0 + 100 * i * METRE:.6f}",
                        end_lat=f"{lat0 + (100 * i + 92) * METRE:.6f}")
        piece["mp_recommended_amount"] = str(492_000 + 3_000 * i)
        pieces.append(piece)
    words = "Concrete surface for the approach to the basti from the pucca road"
    pieces[1].update(work_title=words,
                     scope_of_work=f"{words} in village {VILLAGES[3]}: 95 m long, 3.5 m wide, "
                                   "150 mm of M20 concrete over a 100 mm WBM base, replacing a "
                                   "muddy track.")
    for piece in (pieces[0], pieces[2]):
        bg.append(pswif.to_work(piece, today=as_of))
    add("dup_pieces", "One lane filed as three pieces, each just under Rs 5 lakh",
        "Three pieces of one lane, end to end on the map, filed within 8 days; this one is "
        "described in other words.", {"dup_split": ["SPLIT_JUST_UNDER_LIMIT"]}, pieces[1])

    # 5. a "new" hall 20 m from one finished 14 months ago, materials 40% high, waiting 100
    #    days (T141: its crews' wages, a little high, are the agency's call and add nothing)
    old = wf.hall("E2E-OLD-HALL", AGENCIES[4], VILLAGES[4], 18, m(900), m(850))
    bg.append(pswif.to_work(old, today=as_of, status="COMPLETED",
                            completed_date=wf.d(m(425))))
    lat, lon = wf.pin(18)
    p = wf.hall("E2E-HALL-2", AGENCIES[4], VILLAGES[4], 18, m(100), None,
                latitude=f"{lat + 20 * METRE:.6f}", longitude=f"{lon:.6f}")
    for n in range(1, 20):
        if f"boq_rate_{n}" in p and p.get(f"boq_source_{n}") == "District recent rates":
            p[f"boq_rate_{n}"] = f"{round(float(p[f'boq_rate_{n}']) * 1.4):g}"
    total = wf.estimate_total(p)
    p.update(technical_estimate=f"{total:.2f}", mplads_share=f"{total:.0f}",
             mp_recommended_amount=f"{round(total, -3):.0f}")
    add("many_flags", "A \"new\" hall where a hall already stands",
        "Pinned 20 m from a hall finished 14 months ago, every material 40% above the "
        "district's, and still waiting for sanction 100 days on.",
        {"cost_estimate": ["ESTIMATE_ABOVE_FAIR_PRICE"],
         "dup_split": ["SANCTIONED_WORK_AT_THIS_SITE"], "time_rules": ["SANCTION_OVERDUE"]}, p)
    return out, bg


# ---- what the page shows at each step ------------------------------------------------------------

def typed(p: dict) -> list[dict]:
    """Step 1, the form as the agency fills it: the answers that matter, section by section."""
    def f(label, *keys, unit=""):
        vals = [str(p.get(k) or "").strip() for k in keys]
        v = " to ".join(x for x in vals if x) if len(keys) > 1 else vals[0]
        return [label, f"{v} {unit}".strip()] if v else None

    size = (p.get("road_length_m") and [f("Length", "road_length_m", unit="m"),
                                         f("Width", "road_width_m", unit="m"),
                                         f("Concrete", "pavement_thickness_mm", unit="mm"),
                                         f("Grade", "road_material_grade")]) \
        or (p.get("builtup_area") and [f("Built-up area", "builtup_area", unit="m²"),
                                       f("Floors", "floors"), f("Structure", "structure_type")]) \
        or [f("Lights", "energy_quantity"), f("Each", "watt_per_unit", unit="W LED"),
            f("Pole", "pole_height_m", unit="m")]
    pin = (f"{p.get('start_lat')}, {p.get('start_lon')} to {p.get('end_lat')}, "
           f"{p.get('end_lon')}" if p.get("start_lat") else
           f"{p.get('latitude')}, {p.get('longitude')}")
    sections = [
        ("A. Who files it", [f("Implementing agency", "implementing_agency"),
                             f("Recommendation", "recommendation_ref"),
                             f("Recommended on", "mp_recommendation_date")]),
        ("B. What", [f("Work", "work_title"), f("Nature", "work_nature")]),
        ("C. Where", [f("Village", "village_ward"), f("District", "district"),
                      ["Map pin", pin]]),
        ("Size", size),
        ("D. Earlier works nearby", [f("Declared", "nearby_work_relationship"),
                                     f("Work IDs", "known_nearby_work_ids")]),
        ("G. Timeline", [f("Start", "expected_start_date"),
                         f("Estimated time", "estimated_duration_days", unit="days")]),
    ]
    return [{"section": s, "fields": [x for x in rows if x]} for s, rows in sections]


def boq(p: dict) -> list[dict]:
    """The estimate lines, then the labour schedule's rows (T141), numbered in the order the
    engine reads them; each names the form fields that hold its rate and quantity."""
    out = []
    for n in range(1, 40):
        if f"boq_desc_{n}" not in p:
            break
        q, r = float(p[f"boq_qty_{n}"]), float(p[f"boq_rate_{n}"])
        out.append({"n": n, "item": p[f"boq_desc_{n}"], "unit": p[f"boq_unit_{n}"],
                    "qty": q, "rate": r, "amount": round(q * r, 2),
                    "source": p.get(f"boq_source_{n}") or "",
                    "rate_field": f"boq_rate_{n}", "qty_field": f"boq_qty_{n}"})
    for k in range(1, 40):
        if f"lab_trade_{k}" not in p:
            break
        w, days, r = (float(p[f"lab_{x}_{k}"]) for x in ("workers", "days", "rate"))
        trade = catalog.material(f"labour_{p[f'lab_trade_{k}']}")
        out.append({"n": len(out) + 1,
                    "item": f"{trade['label'] if trade else p[f'lab_name_{k}']}: "
                            f"{w:g} workers x {days:g} days ({p.get(f'lab_task_{k}', '')})",
                    "unit": "day", "qty": w * days, "rate": r, "amount": round(w * days * r, 2),
                    "source": p.get(f"lab_source_{k}") or "",
                    "rate_field": f"lab_rate_{k}", "qty_field": f"lab_days_{k}"})
    return out


def check_of(form: dict, as_of: date, p: dict) -> dict:
    """Step 2, the form's own check before it can be filed."""
    v = validate(form, today=as_of)
    c = v.get("computed") or {}
    grand = c.get("grand_total") or float(p.get("technical_estimate") or 0)
    mp = float(p.get("mp_recommended_amount") or 0)
    return {"ready": v["ready"],
            "fix": [i["message"] for i in v["issues"] if i["level"] == "fix"],
            "confirm": [i["message"] for i in v["issues"] if i["level"] == "confirm"],
            "lines_total": c.get("lines_total"), "grand_total": grand, "mp_amount": mp,
            "mp_gap": round(grand / mp - 1, 4) if mp else None,
            "passed": ["Every section answered", "The lines add up to the estimate",
                       "The estimate matches the MP's amount" if mp and abs(grand / mp - 1) <= 0.1
                       else "The gap to the MP's amount is explained",
                       "The quantities fit the size, or the agency confirmed them"]}


def time_plan(form: dict, work_type: str | None, as_of: date) -> dict | None:
    """Step 3, Time & Rules before sanction: the window it will watch if sanctioned today."""
    w = time_window.window(form, work_type, as_of)
    return w.to_json() if w else None


def yardstick(key: str, p: dict, ref: dict) -> dict | None:
    """The filing's price per unit of size beside real works in Uttar Pradesh."""
    total = float(p.get("technical_estimate") or 0)
    if p.get("road_length_m"):
        g, per = ref["groups"].get("ROAD_CC"), total / float(p["road_length_m"])
        unit = "metre"
    elif p.get("energy_quantity"):
        g, per = ref["groups"].get("STREET_LIGHT|solar"), total / float(p["energy_quantity"])
        unit = "light"
    else:
        return {"note": "Real UP community halls are too few (under 30) to give a price per m²."}
    if not g:
        return None
    s = g["state"]
    d = g["districts"].get(wf.DISTRICT)
    inside = s["p10"] <= per <= s["p90"]
    return {"per": round(per), "unit": unit, "works": s["n"], "p10": s["p10"],
            "median": s["median"], "p90": s["p90"], "inside": inside,
            "district": {"works": d["n"], "median": d["median"]} if d else None}


def _others_range(index, key: tuple, agency: str, work_id: str, when) -> dict | None:
    """What the other agencies pay: the lowest and highest of their own median rates (the same
    recent forms rates._vote takes the fair rate from)."""
    own = {agency, rates.agency_key(agency)}
    by: dict[str, list[float]] = {}
    for a, wid, r, month in index.get(key, []):
        if a in own or wid == work_id:
            continue
        if when is not None and month is not None and not 0 <= (when - month).days <= rates.RECENT_DAYS:
            continue
        by.setdefault(a, []).append(r)
    if not by:
        return None
    meds = sorted(statistics.median(v) for v in by.values())
    return {"low": round(meds[0], 2), "high": round(meds[-1], 2), "agencies": len(meds),
            "forms": sum(len(v) for v in by.values())}


def _situations(p: dict, n: int) -> list[dict]:
    """What on the website form could honestly raise a line's cost, and whether it applies here.
    Read straight from the form; the Cost agent itself does not discount for them, so a yes is
    for the officer to weigh."""
    terrain = str(p.get("terrain") or "").strip()
    access = str(p.get("site_access") or "").strip()
    far = float(p.get("motorable_access_distance_m") or 0)
    remote = bool(terrain and terrain.lower() != "plain") or (
        bool(access) and not access.lower().startswith("motorable")) or far > 0
    where = ", ".join(x for x in (terrain or None, access.lower() or None,
                                  f"{far:g} m from a motorable road" if far else None) if x)
    reason = str(p.get(f"boq_just_{n}") or "").strip()
    source = str(p.get(f"boq_source_{n}") or "").strip()
    code = str(p.get(f"boq_code_{n}") or "").strip()
    return [
        {"label": "Hard-to-reach site", "applies": remote, "note": where or "not stated"},
        {"label": "Agency's reason for this line", "applies": bool(reason),
         "note": f"“{reason}”" if reason else "none given"},
        {"label": "Official rate cited", "applies": bool(code) and "sor" in source.lower(),
         "note": (f"SoR item {code}" if code else source or "not stated")
                 + "; the state's rate book is not loaded yet (T096)"},
    ]


def cost_lines(w: dict, ctx, p: dict) -> dict:
    """Step 3, the Cost agent's reading of each estimate line (T138): the rate and quantity it
    calls usual here, how far the line is above them, and what on the form could explain it.
    Every figure is the agent's own (its evidence) or the form's."""
    res = cost_assess(w, ctx)
    ev = res.evidence
    wh = ev.get("whole") or {}
    form = w["cost_form"]
    agency, wid = rates.agency_of(w), str(w.get("work_id"))
    when = rates._form_month(form, ctx.as_of)
    idx = (ctx.data or {}).get("rates")
    judged = {(x["site"], x["line"]): x for x in wh.get("lines", [])}
    # T141: labour within twice its trade's rate is settled (the agency's call), not in `lines`
    settled = {(x["site"], x["line"]): x for x in wh.get("settled_lines", [])}
    gaps = {g["material"]: g for g in ev.get("data_gaps", [])}
    form_lines = (form.get("sites") or [{}])[0].get("lines") or []
    lines_total = sum(r["amount"] for r in boq(p)) or 1.0
    site = (ev.get("sites") or [{}])[0]
    out = []
    for r in boq(p):
        j = r["n"] - 1
        ln = form_lines[j] if j < len(form_lines) else {}
        mid = ln.get("material_id")
        mat = catalog.material(mid) if mid else None
        x = judged.get((0, j))
        row = {"n": r["n"], "situations": _situations(p, r["n"]), "extra": 0.0,
               "rate_field": r["rate_field"], "qty_field": r["qty_field"]}
        if (0, j) in settled:
            sx = settled[(0, j)]
            row.update(state="labour", fair_rate=sx["fair_rate"], unit="day", level="ok",
                       fair_low=sx.get("fair_low"), fair_high=sx.get("fair_high"),
                       pct=round(sx["rate"] / sx["fair_rate"] - 1, 4),
                       limit=round(sx["fair_rate"] * labour_rules.RATE_MARGIN, 2))
        elif x and x.get("fair_rate") is not None:
            fair = x["fair_rate"]
            key = ((str(w.get("district_lgd")), mid) if x["fair_source"] == "district"
                   else (rates._state(w), mid))
            book = idx.by_key if x["fair_source"] == "district" else idx.by_state
            rng = _others_range(book, key, agency, wid, when) if idx else None
            if rng and x.get("fair_low") is not None:
                # T145: the engine's own range (a state-wide one carries its leeway)
                rng.update(low=x["fair_low"], high=x["fair_high"])
            pct = x["rate"] / fair - 1
            row.update(state="rate", fair_rate=fair, pct=round(pct, 4), range=rng,
                       where=x["fair_source"], unit=x["unit"],
                       level=("high" if rng and x["rate"] > rng["high"] * 1.005
                              else "watch" if pct > 0.005 else "ok"))
        elif x and site.get("price_per_unit") is None:
            row.update(state="quantity_only", unit=x["unit"], level="ok")
        elif mid is None and r["unit"] != "ls" and lines_total:
            over = (wh.get("unexplained") or {}).get("unread_items", 0.0)
            row.update(state="unread", level="high" if over else "ok", over=round(over, 2),
                       share=round(r["amount"] / lines_total, 4))
        elif mid in gaps:
            g = gaps[mid]
            row.update(state="no_data", level="none", forms=g["forms"], agencies=g["agencies"],
                       need=f"{rates.MIN_FORMS} forms from {rates.MIN_AGENCIES} agencies")
        # a goods work (solar lights) is priced as a whole item, per light: that reading leads
        if row.get("state") in (None, "no_data", "quantity_only")                 and site.get("price_per_unit") is not None:
            row.pop("forms", None), row.pop("agencies", None), row.pop("need", None)
            ref = site["reference"]
            per = site["price_per_unit"]
            row.update(state="whole_item", level="high" if per > site["question_above"] else "ok",
                       per=per, per_unit=site["unit"], median=ref["median"], p98=ref["p98"],
                       p10=ref.get("p10"), p90=ref.get("p90"),
                       works=ref["n"], where_text=site["where"], limit=site["question_above"],
                       pct=round(per / ref["median"] - 1, 4))
        if "state" not in row:
            row.update(state="no_data", level="none", forms=0, agencies=0,
                       need=f"{rates.MIN_FORMS} forms from {rates.MIN_AGENCIES} agencies")
        if x:
            needed = x.get("needed")
            if needed is not None:
                low = x.get("needed_low")
                row.update(needed=round(needed, 1),
                           needed_low=round(low if low is not None else needed, 1),
                           allowed=round(needed * whole.QTY_TOLERANCE, 1),
                           qty_ratio=round(x["quantity"] / needed, 3) if needed else None)
                if x["quantity"] > needed * whole.QTY_TOLERANCE:
                    row["level"] = "high"
            row["extra"] = round(x["extra"], 2)
        if mat:
            row["material"] = mat["label"]
        out.append(row)
    unread = wh.get("unexplained", {})
    summary = {"verdict": wh.get("verdict"), "grand": wh.get("grand_total"),
               "fair": wh.get("fair_total"), "fair_low": wh.get("fair_low"),
               "fair_high": wh.get("fair_high"), "gap": wh.get("gap"), "share": wh.get("gap_share"),
               "coverage": wh.get("coverage"), "limit_share": whole.GAP_SHARE,
               "limit_rs": whole.GAP_MIN_RS, "qty_slack": round(whole.QTY_TOLERANCE - 1, 4),
               "unread_allowed": whole.UNREAD_SHARE, "unexplained": unread,
               "lines_total": lines_total, "headline": res.headline,
               "asks": any(f.code == "ESTIMATE_ABOVE_FAIR_PRICE" for f in res.findings)}
    return {"lines": out, "summary": summary}


def decision(band: str) -> str:
    return {"LOW": "Nothing for the officer to check: ready for sanction.",
            "MEDIUM": "Sanction after the officer checks what is flagged.",
            "HIGH": "Goes to the review queue: check before sanction.",
            "CRITICAL": "Goes to the top of the review queue: check before sanction."}[band]


def main() -> None:
    works, info = wf.load()
    as_of = info["as_of"]
    dist = next(w for w in works if w.get("district_name") == wf.DISTRICT)
    place = {"district_lgd": dist["district_lgd"], "state_lgd": dist.get("state_lgd"),
             "state_name": dist.get("state_name"), "district_name": wf.DISTRICT}
    demo, demo_bg = wf.build(as_of)
    world = demo_bg + [pswif.to_work(e["form"], today=as_of, **e["record"]) for e in demo]
    filings, bg = build(as_of)
    for w in world + bg:
        w.update(place)
    records = []
    for e in filings:
        w = pswif.to_work(e["form"], today=as_of, **e["record"])
        w.update(place)
        records.append(w)
    district = [w for w in works if w.get("district_lgd") == place["district_lgd"]]
    ref = json.loads(UP_PRICES.read_text(encoding="utf-8"))
    out, lines, bad = [], [], []
    for e, w in zip(filings, records, strict=True):
        # the district's real works and every other filing, never the filing itself twice
        ctx = Context(stats=build_store(works), as_of=as_of,
                      data=indexes(district + world + bg + [w]))
        trace = explain(w, ctx)
        fired = {c["id"]: sorted(f["code"] for f in c["findings"] if f["risk"] > 0)
                 for c in trace["checks"]}
        fired = {k: v for k, v in fired.items() if v}
        if fired != {k: sorted(v) for k, v in e["codes"].items()}:
            bad.append(f"{e['key']}: raises {fired}, meant {e['codes']}")
        check = check_of(w["cost_form"], as_of, e["form"])
        if not check["ready"]:
            bad.append(f"{e['key']}: the form is not ready: {check['fix'][:2]}")
        band = trace["result"]["band"]
        lines.append(f"{e['key']:13} {band:8} {trace['result']['score'] * 100:5.1f} "
                     f"ready {check['ready']!s:5} {fired}")
        print(lines[-1])
        out.append({"id": e["key"], "title": e["title"], "story": e["story"],
                    "flagged": bool(fired), "form": e["form"], "typed": typed(e["form"]),
                    "boq": boq(e["form"]), "check": check,
                    "time_plan": time_plan(w["cost_form"], w["work_type_code"], as_of),
                    "yardstick": yardstick(e["key"], e["form"], ref),
                    "decision": decision(band), "cost": cost_lines(w, ctx, e["form"]),
                    "trace": trace})
    if bad:
        sys.exit("the end-to-end filings no longer show what they say:\n" + "\n".join(bad))
    SUMMARY.write_text(f"{len(works):,} dashboard works, as of {as_of}; {wf.DISTRICT}, "
                       f"{len(district):,} real works and {len(world) + len(bg)} demo filings "
                       "around the five\n" + "\n".join(lines) + "\n", encoding="utf-8")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "source": f"eSAKSHI dashboard tables, {len(works):,} works, as of {as_of}; made-up "
                  f"filings in {wf.DISTRICT}, Uttar Pradesh",
        "as_of": str(as_of), "district": f"{wf.DISTRICT}, Uttar Pradesh",
        "real_works": len(district), "examples": out}, ensure_ascii=False, indent=1,
        default=str), encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)} ({OUT.stat().st_size // 1024} KB)")


def cost_only() -> None:
    """Add the Cost agent's line-by-line reading to the examples already written, without the
    dashboard tables (the Cost agent reads only the forms: the district's real works carry none).
    Stops unless the agent says exactly what the stored trace says for every filing."""
    data = json.loads(OUT.read_text(encoding="utf-8"))
    as_of = date.fromisoformat(data["as_of"])
    state, district = "UTTAR PRADESH", wf.DISTRICT.upper()
    place = {"district_lgd": f"{state}|{district}", "state_lgd": state,
             "state_name": "Uttar Pradesh", "district_name": wf.DISTRICT}
    demo, demo_bg = wf.build(as_of)
    world = demo_bg + [pswif.to_work(e["form"], today=as_of, **e["record"]) for e in demo]
    filings, bg = build(as_of)
    for x in world + bg:
        x.update(place)
    stored = {e["id"]: e for e in data["examples"]}
    bad = []
    for e in filings:
        w = pswif.to_work(e["form"], today=as_of, **e["record"])
        w.update(place)
        ctx = Context(stats=None, as_of=as_of, data=indexes(world + bg + [w]))
        ex = stored[e["key"]]
        if ex["form"] != e["form"]:
            bad.append(f"{e['key']}: the filing changed since the examples were written")
            continue
        reading = cost_lines(w, ctx, e["form"])
        want = next(c for c in ex["trace"]["checks"] if c["id"] == "cost_estimate")["headline"]
        if reading["summary"]["headline"] != want:
            bad.append(f"{e['key']}: Cost now says {reading['summary']['headline']!r}, "
                       f"the stored trace {want!r}")
        ex["cost"] = reading
        print(f"{e['key']:13} {reading['summary']['verdict']}  "
              + " ".join(f"{x['n']}:{x['state']}/{x['level']}" for x in reading["lines"]))
    if bad:
        sys.exit("the Cost reading does not match the stored examples:\n" + "\n".join(bad))
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1, default=str),
                   encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)} ({OUT.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    cost_only() if "--cost-only" in sys.argv else main()
