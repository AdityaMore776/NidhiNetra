r"""Example filings of the website's work intelligence form, each caught by one agent (T134).

The site's form (/work-form, the Pre-Sanction Work Intelligence Form PSWIF v1.1) is what an
implementing agency fills before sanction. Judges cannot see a real filing yet: no agency has
filed one. So this script writes MADE-UP filings, every field as an agency would fill it, by
made-up agencies in the real district of Jaunpur (the eSAKSHI dashboard tables, 1,038 works), and
runs each through the real engines exactly as the live check does (POST /api/v1/work-form/check:
drishti/cost_form/pswif.py, then the four agents). Some also carry what the record shows after
sanction (a completion date, monthly site videos as the video job reads them), because Time &
Rules and Site Progress judge what happens next.

  clean           an honest CC road: all four agents look, nothing to ask
  cost_padded     every material 25% above what other agencies in the district pay (its
                  crews at the district's wages: within twice a trade's rate, wages are the
                  agency's call, T141)
  cost_quantity   twice the cement the road's size needs, "justified" on the line
  cost_lights     solar lights at Rs 48,000 each, twice the MP's amount
  cost_labour     masons at 2.4 times the district's day rate; 34 workers on the road is fine
  dup_pin         a "new" road pinned 20 m from a road sanctioned last year
  dup_rebuild     a hall declared as a rebuild of one completed 16 months earlier
  dup_split       one village road filed as three works, each just under Rs 5 lakh
  time_fast       a road recorded complete 6 days after sanction, no site video
  time_late       a hall 8 months promised, open 16 months on, the site standing still
  site_reused     the first site video carries footage filmed for another work
  site_claim      "roof slab cast" claimed twice; the videos do not show it
  site_elsewhere  a monthly video filmed 2.4 km away, at a site that is not this one

Background filings (honest CC roads by five other made-up agencies) give the district rates
the Cost agent compares lines with. Nothing here is a real agency, person or work; village names
are invented. Writes apps/web/public/work-form/examples.json and results/work_form_examples.txt;
stops if an example no longer raises exactly what it is meant to show.

Run:  apps\engine\.venv\Scripts\python.exe data\trial\work_form_examples.py
"""

from __future__ import annotations

import json
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "data"))
sys.path.insert(0, str(ROOT / "apps" / "engine"))
from esakshi_dashboard import load  # noqa: E402

from drishti import demo  # noqa: E402
from drishti.agents.cost_estimate import labour as labour_rules  # noqa: E402
from drishti.agents.cost_estimate import whole  # noqa: E402
from drishti.agents.dup_split import agent as dup_agent  # noqa: E402
from drishti.agents.dup_split import repeat  # noqa: E402
from drishti.agents.time_rules import window  # noqa: E402
from drishti.batch import indexes  # noqa: E402
from drishti.cost_form import catalog, norms, pswif  # noqa: E402
from drishti.cost_form.validate import validate  # noqa: E402
from drishti.evaluation.stats import build_store  # noqa: E402
from drishti.explain import explain  # noqa: E402
from drishti.pipeline.orchestrator import Context  # noqa: E402

OUT = ROOT / "apps" / "web" / "public" / "work-form" / "examples.json"
SUMMARY = ROOT / "data" / "trial" / "results" / "work_form_examples.txt"
DEMO = ROOT / "apps" / "engine" / "drishti" / "reference" / "demo" / "work_form.json"
PLACE_KEYS = ("district_lgd", "district_name", "state_lgd", "state_name")
DISTRICT = "Jaunpur"
BASE = (25.7463, 82.6837)               # the district, near its headquarters
METRE = 1 / 111_195

# the district's honest rates (Rs per unit), what the background filings pay around
RATE = {"cement": 380.0, "sand": 1800.0, "aggregate": 2100.0, "granular_base": 1450.0,
        "mason": 750.0, "beldar": 420.0}


def d(x: date) -> str:
    return x.isoformat()


def pin(k: int) -> tuple[float, float]:
    """Example k's site: about 1.5 km apart, so no two examples share a place by accident."""
    return round(BASE[0] + (k // 4) * 0.014, 6), round(BASE[1] + (k % 4) * 0.015, 6)


# ---- one filing, every section as an agency fills it -----------------------------------------

def common(ref: str, agency: str, village: str, rec: date, sanction: date | None,
           start: date, days: int, total: float, mp: float) -> dict:
    """Sections A, F (totals), G, H, I and K: the parts every filing has."""
    end = start + timedelta(days=days)
    return {
        # A. recommendation and administrative identity (no MP is ever named)
        "recommendation_ref": ref, "mp_recommendation_date": d(rec),
        "ida_received_date": d(rec + timedelta(days=6)), "mp_name": "", "mp_house": "Lok Sabha",
        "constituency_state": "Uttar Pradesh", "financial_year": "2026-27",
        "nodal_district_authority": "District Planning Office, Jaunpur",
        "implementing_district_authority": "District Rural Development Agency, Jaunpur",
        "implementing_agency": agency,
        "recommendation_jurisdiction": "Normal constituency / permitted State jurisdiction",
        "preparing_designation": "Assistant Engineer",
        # B (shared parts)
        "indicative_list_status": "Listed / clearly covered by permissible category",
        "mandatory_domain_agency": "No / not applicable",
        "user_agency": f"Gram Panchayat {village}",
        "public_access": "Unrestricted public/community access",
        "beneficiary_type": "Government / Local Government", "priority_area": "General",
        # C (shared parts)
        "state": "Uttar Pradesh", "district": DISTRICT, "block_tehsil": "Sadar",
        "village_ward": village, "pincode": "222001",
        "land_ownership": "Local Government / Panchayat / ULB",
        "land_proof_ref": f"Khatauni extract, gram sabha land, {village}",
        "site_legal_status": "Authorized / approved", "gps_accuracy": "4.8",
        "terrain": "Plain", "site_access": "Motorable all-weather",
        "motorable_access_distance_m": "0",
        "presanction_site_evidence": "Geo-tagged photos PS-1 to PS-4 of the site before work",
        # D (none declared unless an example says so)
        "part_of_larger_project": "No", "existing_asset_same_site": "No",
        "nearby_work_relationship": "None known",
        # F totals
        "sor_name": "UP PWD Schedule of Rates", "sor_year": "2025-26",
        "estimate_engineer": "Assistant Engineer (Civil)", "lumpsum_components": "0",
        "other_charges": "0", "tax_treatment": "Included in rates",
        "technical_estimate": f"{total:.2f}", "mp_recommended_amount": f"{mp:.0f}",
        "mplads_share": f"{total:.0f}", "other_govt_share": "0",
        "major_material_sources": "Cement and steel from the district depot; sand from the "
                                  "Gomti ghat; aggregate from the nearest crusher.",
        # G. timeline
        "sanction_decision": "Sanction" if sanction else "", "sanction_date":
            d(sanction) if sanction else "",
        "expected_start_date": d(start), "estimated_duration_days": str(days),
        "expected_completion_date": d(end), "working_days": str(round(days * 0.8)),
        "lost_days": str(days - round(days * 0.8)),
        "lost_days_reason": "Monsoon weeks and festival holidays",
        "milestone_name_1": "Site cleared and set out",
        "milestone_date_1": d(start + timedelta(days=round(days * 0.15))),
        "milestone_pct_1": "10", "milestone_evidence_1": "Monthly site video",
        "milestone_name_2": "Main structure done",
        "milestone_date_2": d(start + timedelta(days=round(days * 0.7))),
        "milestone_pct_2": "70", "milestone_evidence_2": "Monthly site video",
        "milestone_name_3": "Complete and handed over", "milestone_date_3": d(end),
        "milestone_pct_3": "100", "milestone_evidence_3": "Completion video and certificate",
        # H. eligibility and clearances
        **{k: True for k in ("durable_public_asset", "no_om_funding", "not_residential",
                             "not_private_commercial", "no_land_acquisition",
                             "not_reimbursement", "no_csr_pooling", "not_religious",
                             "not_welcome_gate", "authorized_colony", "not_named_person",
                             "accessibility_considered")},
        "below_min_threshold": "No", "om_undertaking_status": "Obtained",
        "om_undertaking_ref": f"Gram Panchayat {village} resolution",
        "technical_feasibility_ref": f"TF/{ref}", "technical_sanction_ref": f"TS/{ref}",
        "admin_financial_sanction_ref": f"AFS/{ref}" if sanction else "",
        "procurement_method": "Open tender / e-procurement", "plaque_provision": "Yes",
        "handover_plan": f"Handed to Gram Panchayat {village} for upkeep",
        "land_clearance_app": "Yes", "land_clearance_status": "Obtained",
        "land_clearance_authority": "Gram Panchayat", "land_clearance_ref": f"NOC/{ref}",
        # I. site progress baseline
        "site_changed": "No", "baseline_capture_required": "Yes", "fixed_viewpoint_count": "5",
        "capture_responsible_role": "Junior Engineer of the agency",
        "viewpoint_plan_ref": "Five fixed spots marked on the first visit",
        "baseline_video_date": d(start), "capture_frequency": "Monthly",
        "random_check_enabled": "Yes", "completion_capture_required": "Yes",
        "completion_evidence_definition": "Every viewpoint shows the finished work",
        "baseline_existing_condition": "Open ground / earthen track before work",
        "anti_substitution_notes": "Viewpoints matched to the first visit every month",
        # K. certification
        "certify_accuracy": True, "consent_agent_verification": True,
    }


def boq(rows: list[tuple]) -> tuple[dict, float]:
    """BOQ rows (desc, unit, qty, rate, source[, justification]) as the form's numbered fields."""
    out, total = {}, 0.0
    for n, r in enumerate(rows, start=1):
        desc, unit, qty, rate, source = r[:5]
        out.update({f"boq_code_{n}": "", f"boq_desc_{n}": desc, f"boq_unit_{n}": unit,
                    f"boq_qty_{n}": f"{qty:g}", f"boq_rate_{n}": f"{rate:g}",
                    f"boq_source_{n}": source, f"boq_measure_ref_{n}": f"MB p.{n}",
                    f"boq_just_{n}": r[5] if len(r) > 5 else ""})
        total += qty * rate
    return out, round(total, 2)


def labour(rows: list[tuple]) -> tuple[dict, float]:
    """Labour schedule rows (trade, workers, days each, day rate, source, what they do, BOQ
    lines) as the form's numbered fields (PSWIF v1.1, T141): one row per trade."""
    out, total = {}, 0.0
    for n, (trade, workers, days, rate, source, task, lines) in enumerate(rows, start=1):
        out.update({f"lab_trade_{n}": trade, f"lab_name_{n}": "",
                    f"lab_grade_{n}": catalog.grade_of(f"labour_{trade}"),
                    f"lab_workers_{n}": f"{workers:g}", f"lab_days_{n}": f"{days:g}",
                    f"lab_rate_{n}": f"{rate:g}", f"lab_task_{n}": task,
                    f"lab_lines_{n}": lines, f"lab_source_{n}": source})
        total += workers * days * rate
    return out, round(total, 2)


def crew(person_days: float, workers: int) -> tuple[int, float]:
    """`workers` on site for the days that give about `person_days` (to the half day)."""
    return workers, max(0.5, round(person_days / workers * 2) / 2)


def estimate_total(p: dict) -> float:
    """The BOQ lines and the labour schedule, as the form adds them up."""
    total = 0.0
    for k in p:
        if k.startswith("boq_qty_"):
            n = k.removeprefix("boq_qty_")
            total += float(p[k] or 0) * float(p.get(f"boq_rate_{n}") or 0)
        elif k.startswith("lab_workers_"):
            n = k.removeprefix("lab_workers_")
            total += (float(p[k] or 0) * float(p.get(f"lab_days_{n}") or 0)
                      * float(p.get(f"lab_rate_{n}") or 0))
    return round(total, 2)


def road(ref: str, agency: str, village: str, k: int, rec: date, sanction: date | None,
         length: float = 300, width: float = 3.5, rate_up: float = 1.0, cement_x: float = 1.0,
         jitter: float = 0.0, mp_x: float = 1.0, just: str = "", days: int = 120,
         start: date | None = None, labour_x: dict | None = None,
         more_labour: tuple = (), **over) -> dict:
    """A CC road, M20, 150 mm on a 100 mm WBM base, with honest quantities for its size."""
    size = {"length_m": length, "width_m": width, "cc_thickness_mm": 150,
            "concrete_grade": "M20", "base_type": "wbm", "base_thickness_mm": 100}
    vol = length * width * 0.15
    need = norms.needs("ROAD_CC", size)[0]["needed"]
    f = (1 + jitter) * rate_up

    def r(m):
        # `rate_up` pads the materials; the crews keep the honest spread (T141)
        return round(RATE[m] * (f if m not in ("mason", "beldar") else 1 + jitter))

    rows = [("Cement OPC 43 grade", "bag", round(need * 0.98 * cement_x), r("cement"),
             "District recent rates") + ((just,) if just else ()),
            ("Coarse sand", "cum", round(vol * 0.44), r("sand"), "District recent rates"),
            ("Stone aggregate 20 mm", "cum", round(vol * 0.86), r("aggregate"),
             "District recent rates"),
            ("WBM base, graded stone", "cum", round(length * width * 0.10), r("granular_base"),
             "District recent rates"),
            ("Concrete mixer and vibrator hire", "day", 30, 2500, "Approved quotation")]
    lines, total = boq(rows)
    x = labour_x or {}
    crews, labour_total = labour([
        ("mason", *crew(vol * 0.75, 4), round(r("mason") * x.get("mason", 1.0)),
         "District recent rates", "Laying, levelling and finishing the concrete", "1-3"),
        ("beldar", *crew(vol * 3.5, 12), round(r("beldar") * x.get("beldar", 1.0)),
         "District recent rates", "Earthwork, WBM base and carrying concrete", "1-4"),
        *more_labour])
    lines.update(crews)
    total += labour_total
    lat, lon = pin(k)
    start = start or ((sanction or rec) + timedelta(days=14))
    p = common(ref, agency, village, rec, sanction, start, days, total, round(total * mp_x,
                                                                               -3))
    p.update(lines)
    p.update({
        "work_title": f"CC road from the primary school to the panchayat bhawan, {village}",
        "sector": "Railways / roads / bridges / pathways", "work_type": "road",
        "work_nature": "New asset",
        "scope_of_work": f"Construction of a {length:g} m long, {width:g} m wide cement concrete "
                         f"road, 150 mm thick in M20 over a 100 mm WBM base, from the primary "
                         f"school gate to the panchayat bhawan in village {village}, replacing "
                         "an earthen track that floods every monsoon.",
        "public_need": "Children and patients cannot use the track for three months a year.",
        "site_address": f"Primary school gate to panchayat bhawan, {village}",
        "land_parcel_no": f"Gata {300 + k}", "site_geometry_type": "Linear asset / alignment",
        "latitude": f"{lat:.6f}", "longitude": f"{lon:.6f}",
        "start_lat": f"{lat:.6f}", "start_lon": f"{lon:.6f}",
        "end_lat": f"{lat + length * 0.97 * METRE:.6f}", "end_lon": f"{lon:.6f}",
        "start_accuracy": "4.6", "end_accuracy": "5.1", "route_length_m": f"{length:g}",
        "road_subtype": "CC road", "road_length_m": f"{length:g}", "road_width_m": f"{width:g}",
        "pavement_thickness_mm": "150", "base_thickness_mm": "100",
        "road_material_grade": "M20", "existing_road_condition": "Earthen",
        "road_layer_spec": "M20 PCC 150 mm over WBM base 100 mm",
        "road_drain_length_m": "0", "culvert_count": "0",
    })
    p.update(over)
    return p


def hall(ref: str, agency: str, village: str, k: int, rec: date, sanction: date | None,
         area: float = 180, days: int = 240, start: date | None = None, **over) -> dict:
    """A single-storey community hall, RCC frame, brick walls."""
    rows = [("Cement OPC 43 grade", "bag", round(area * 7.5), 380, "District recent rates"),
            ("Coarse sand", "cum", round(area * 0.45), 1800, "District recent rates"),
            ("Stone aggregate 20 mm", "cum", round(area * 0.35), 2100, "District recent rates"),
            ("TMT steel Fe 500", "kg", round(area * 32), 68, "State/Dept SoR"),
            ("Bricks, first class", "nos", round(area * 220), 8, "District recent rates"),
            ("Vitrified floor tiles", "sqm", round(area * 0.95), 650, "Approved quotation"),
            ("Doors and windows, steel frame", "nos", 12, 9500, "Approved quotation")]
    lines, total = boq(rows)
    crews, labour_total = labour([
        ("mason", *crew(area * 2.2, 6), 750, "District recent rates",
         "Brickwork, concrete, plaster and tiling", "1-6"),
        ("beldar", *crew(area * 6, 12), 420, "District recent rates",
         "Excavation, mixing and carrying material", "1-5")])
    lines.update(crews)
    total += labour_total
    lat, lon = pin(k)
    start = start or ((sanction or rec) + timedelta(days=21))
    p = common(ref, agency, village, rec, sanction, start, days, total, round(total, -3))
    p.update(lines)
    p.update({
        "work_title": f"Community hall at the panchayat ground, {village}",
        "sector": "Public & community building", "work_type": "building",
        "work_nature": "New asset",
        "scope_of_work": f"Construction of a single-storey community hall of {area:g} sq m "
                         f"built-up area with an RCC frame, brick walls, a kitchen and a ramp, "
                         f"on gram sabha land at the panchayat ground of village {village}, for "
                         "meetings, weddings and relief camps.",
        "public_need": "The village has no covered public space for meetings or relief camps.",
        "site_address": f"Panchayat ground, {village}", "land_parcel_no": f"Gata {500 + k}",
        "site_geometry_type": "Point asset",
        "latitude": f"{lat:.6f}", "longitude": f"{lon:.6f}",
        "building_site_area": f"{area * 2:g}", "builtup_area": f"{area:g}", "floors": "1",
        "rooms": "2", "structure_type": "RCC framed", "foundation_type": "Isolated footing",
        "roof_type": "RCC slab", "floor_height": "3.2",
        "accessibility_provisions": "Ramp at the entrance",
    })
    p.update(over)
    return p


def lights(ref: str, agency: str, village: str, k: int, rec: date, each: float,
           mp: float, **over) -> dict:
    rows = [("Solar street light set: 12 W LED, 40 Wp panel, LiFePO4 battery, 6 m GI pole, "
             "installed", "nos", 10, each, "Approved quotation")]
    lines, total = boq(rows)
    lat, lon = pin(k)
    p = common(ref, agency, village, rec, None, rec + timedelta(days=40), 60, total, mp)
    p.update(lines)
    p.update({
        "work_title": f"10 solar street lights from the bus stand to the primary school, "
                      f"{village}",
        "sector": "Energy supply / distribution", "work_type": "energy",
        "work_nature": "New asset",
        "scope_of_work": f"Supply and installation of 10 standalone solar street lights, each "
                         f"a 12 W LED with a 40 Wp panel and a LiFePO4 battery on a 6 m GI pole, "
                         f"along the lane from the bus stand to the primary school in village "
                         f"{village}, with a five-year warranty.",
        "public_need": "The lane is unlit and unsafe after dark.",
        "site_address": f"Bus stand to primary school lane, {village}",
        "site_geometry_type": "Multiple discrete points",
        "latitude": f"{lat:.6f}", "longitude": f"{lon:.6f}",
        "energy_asset_type": "Solar street lights", "energy_quantity": "10",
        "watt_per_unit": "12", "pole_height_m": "6", "spacing_m": "30", "solar_wp": "40",
        "battery_spec": "LiFePO4 12.8 V 30 Ah", "warranty_requirement": "5 years",
        "rate_deviation_notes": "Survey found ten poles are needed, not five.",
        "sanction_decision": "",
    })
    p.update(over)
    return p


def visit(n: int, kind: str, when: date, change: str | None = None, claim: str | None = None,
          verdict: str | None = None, **more) -> dict:
    """A site video as the video job leaves its readings: sealed, filmed in the app, at the
    site, at its five marked viewpoints, unless an example says otherwise."""
    readings = {"sealed": True, "in_app": True, "quality_ok": True, "gps_inside": True,
                "views_match_site": None if kind == "baseline" else True,
                "viewpoints_expected": 5, "viewpoints_matched": 5, "change": change,
                "claim_verdict": verdict, **more}
    return {"visit_id": f"V{n}", "kind": kind, "captured_at": d(when), "claim": claim,
            "readings": readings}


# ---- the examples ------------------------------------------------------------------------------

AG = ["Nirman Seva Agency", "Gramin Path Nigam", "Jan Suvidha Works", "Prakash Urja Agency",
      "Sahyog Construction Cell", "Lok Nirman Mandal", "Sadak Vikas Prakoshth",
      "Nagar Seva Kendra", "Gram Unnati Agency", "Shramik Works Cooperative"]
# made-up villages; the examples' names are ones the Duplicate check reads as a place (a name it
# takes for a misspelt common word, like "Belwa", names no place for it)
VILLAGES = ["Bhawanipur", "Kusumi", "Nayagaon", "Madhopur", "Sonbarsa", "Ujarpur", "Pratappur",
            "Siddhipur", "Barauli", "Lalganj Khurd", "Harihar Tola", "Sarkoni", "Patarahi",
            "Belahari"]
BG_VILLAGES = ["Rampur Kalan", "Sarai Khas", "Dhanapur", "Mirpur", "Chandpur", "Tilwari",
               "Karanja"]


def build(as_of: date) -> tuple[list[dict], list[dict]]:
    """(examples, background works): each example = {key, agent, codes, title, story, later,
    form, record}."""
    m = lambda days: as_of - timedelta(days=days)  # noqa: E731
    bg_works, ex = [], []

    # background: honest CC roads by five other agencies, filed over the last five months
    for i, (ag, jit) in enumerate(zip(AG[5:10] * 2, (-0.03, 0.02, 0.04, -0.02, 0.01, 0.03,
                                                      -0.04), strict=False)):
        rec = m(150 - 18 * i)
        p = road(f"WF-BG-{i + 1}", ag, BG_VILLAGES[i], 20 + i, rec, rec + timedelta(days=40),
                 length=250 + 40 * i, jitter=jit)
        bg_works.append(pswif.to_work(p, today=as_of, status="SANCTIONED"))

    def add(key, agent, codes, title, story, later, p, **record):
        ex.append({"key": key, "agent": agent, "codes": codes, "title": title, "story": story,
                   "later": later, "form": p, "record": record})

    # --- clean ---
    rec = m(110)
    san = rec + timedelta(days=35)
    p = road("WF-CLEAN-1", AG[0], VILLAGES[0], 0, rec, san)
    start = san + timedelta(days=14)
    add("clean", None, {}, "An honest CC road: every agent looks, none asks",
        "A 300 m village road, priced and sized honestly.",
        [f"Sanctioned {san:%d %b %Y}, 35 days after the recommendation",
         "Three site videos so far: the first visit, then new work at the same viewpoints "
         "each month, the agency's claim shown"],
        p, status="SANCTIONED",
        site_visits=[visit(1, "baseline", start),
                     visit(2, "monthly", start + timedelta(days=30), "changed",
                           "base laid on the first 150 m", "shown"),
                     visit(3, "monthly", start + timedelta(days=60), "changed",
                           "concrete laid on 200 m", "shown")])

    # --- Cost ---
    rec = m(60)
    p = road("WF-COST-1", AG[1], VILLAGES[1], 1, rec, None, rate_up=1.25, mp_x=1.0)
    add("cost_padded", "cost_estimate", {"cost_estimate": ["ESTIMATE_ABOVE_FAIR_PRICE"]},
        "Every material a little high: the whole estimate is not",
        "Every material is priced about 25% above what other agencies in the district "
        "charge.",
        ["Not sanctioned yet: this is the check before sanction"], p)
    rec = m(55)
    p = road("WF-COST-2", AG[2], VILLAGES[2], 2, rec, None, cement_x=2.0, mp_x=1.0,
             just="Extra cement for the approach ramps and the kerbs")
    add("cost_quantity", "cost_estimate",
        {"cost_estimate": ["ESTIMATE_ABOVE_FAIR_PRICE", "MATERIAL_QUANTITY_ABOVE_SIZE"]},
        "Twice the cement the road can use",
        "2,614 bags of cement for a road that needs about 1,330.",
        ["Not sanctioned yet: this is the check before sanction"], p)
    p = lights("WF-COST-3", AG[3], VILLAGES[3], 3, m(40), 48_000, 240_000)
    add("cost_lights", "cost_estimate", {"cost_estimate": ["ESTIMATE_ABOVE_STANDARD_AND_MP"]},
        "Solar lights at more than twice the usual price",
        "10 solar street lights at Rs 48,000 each; the MP recommended Rs 2.4 lakh.",
        ["Not sanctioned yet: this is the check before sanction"], p)

    # T141: labour judged trade by trade. 34 workers is the agency's call (never asked);
    # masons at 2.4 times what other agencies here pay masons is a blatant rate
    p = road("WF-COST-4", AG[2], VILLAGES[10], 19, m(48), None, labour_x={"mason": 2.4},
             more_labour=(("helper", 16, 30, 430, "District recent rates",
                           "Feeding the mixer and carrying concrete", "1-3"),
                          ("operator", 2, 30, 950, "Approved quotation",
                           "Running the concrete mixer and vibrator", "5")))
    add("cost_labour", "cost_estimate", {"cost_estimate": ["LABOUR_RATE_FAR_ABOVE"]},
        "Masons at more than twice the district's wage",
        "Masons at Rs 1,800 a day where other agencies pay about Rs 750; the 34 workers on the "
        "road are not questioned.",
        ["Not sanctioned yet: this is the check before sanction"], p)

    # --- Duplicate Work ---
    old = road("WF-OLD-ROAD", AG[6], VILLAGES[4], 4, m(520), m(470))
    bg_works.append(pswif.to_work(old, today=as_of, status="COMPLETED",
                                  completed_date=d(m(330))))
    lat, lon = pin(4)
    rec = m(50)
    p = road("WF-DUP-1", AG[4], VILLAGES[4], 5, rec, None,
             latitude=f"{lat + 20 * METRE:.6f}", longitude=f"{lon:.6f}",
             start_lat=f"{lat + 20 * METRE:.6f}", start_lon=f"{lon:.6f}",
             end_lat=f"{lat + 311 * METRE:.6f}", end_lon=f"{lon:.6f}")
    add("dup_pin", "dup_split", {"dup_split": ["SANCTIONED_WORK_AT_THIS_SITE"]},
        "A \"new\" road on top of one the scheme already paid for",
        "A new road pinned 20 m from a road completed last year. The form does not mention it.",
        ["Not sanctioned yet: this is the check before sanction",
         "Earlier road WF-OLD-ROAD: sanctioned, completed 11 months ago, pinned 20 m away"], p)

    old_hall = hall("WF-OLD-HALL", AG[7], VILLAGES[5], 6, m(980), m(930))
    bg_works.append(pswif.to_work(old_hall, today=as_of, status="COMPLETED",
                                  completed_date=d(m(540))))
    # rebuilt where the old hall stands (its own pin: the form says the hall is on the site)
    p = hall("WF-DUP-2", AG[0], VILLAGES[5], 6, m(45), None,
             work_nature="Reconstruction / rebuild", prior_work_id="WF-OLD-HALL",
             prior_completion_date=d(m(540)), existing_asset_same_site="Yes",
             repeat_reason="Cracks in the walls after the last monsoon",
             known_nearby_work_ids="WF-OLD-HALL",
             nearby_work_relationship="Rebuild / replacement",
             baseline_existing_condition="The hall built under WF-OLD-HALL stands on the site")
    add("dup_rebuild", "dup_split", {"dup_split": ["REBUILT_SOON_AFTER_COMPLETION"]},
        "Rebuilding a hall finished 16 months earlier",
        "The agency says this rebuilds a hall that was finished 16 months earlier.",
        ["Not sanctioned yet: this is the check before sanction",
         f"Earlier hall WF-OLD-HALL: completed {m(540):%d %b %Y}"], p)

    pieces = []
    for i in range(3):
        rec = m(70 - 4 * i)
        piece = road(f"WF-SPLIT-{i + 1}", AG[1], VILLAGES[6], 8, rec, None, length=95,
                     width=3.5,
                     work_title=f"CC road in village {VILLAGES[6]}, part {i + 1}",
                     scope_of_work=f"Construction of a CC road in village {VILLAGES[6]}, part "
                                   f"{i + 1} of the lane from the main road to the harijan "
                                   "basti, 95 m long, 3.5 m wide, 150 mm thick in M20 over "
                                   "a WBM base.",
                     **{"start_lat": f"{pin(8)[0] + 100 * i * METRE:.6f}",
                        "end_lat": f"{pin(8)[0] + (100 * i + 92) * METRE:.6f}",
                        "latitude": f"{pin(8)[0] + 100 * i * METRE:.6f}"})
        piece["mp_recommended_amount"] = str(493_000 + 2_500 * i)
        pieces.append(piece)
    for piece in pieces[::2]:
        bg_works.append(pswif.to_work(piece, today=as_of))
    add("dup_split", "dup_split", {"dup_split": ["SPLIT_JUST_UNDER_LIMIT"]},
        "One lane filed as three works, each just under Rs 5 lakh",
        "One lane filed as parts 1, 2 and 3, each just under the Rs 5 lakh limit.",
        ["Not sanctioned yet: this is the check before sanction",
         "The other parts: WF-SPLIT-1 and WF-SPLIT-3"], pieces[1])

    # --- Time & Rules ---
    rec = m(140)
    san = rec + timedelta(days=40)
    p = road("WF-TIME-1", AG[2], VILLAGES[7], 9, rec, san, length=350, days=120)
    add("time_fast", "time_rules", {"time_rules": ["FINISHED_TOO_FAST"],
                                     # never filmed, 100 days after sanction (T135)
                                     "site_progress": ["NO_SITE_VIDEO"]},
        "A 350 m road \"complete\" 6 days after sanction",
        "Promised in 120 days; recorded complete 6 days after sanction.",
        [f"Sanctioned {san:%d %b %Y}",
         f"Recorded complete {san + timedelta(days=6):%d %b %Y}, 6 days later",
         "No site video filmed"],
        p, status="COMPLETED", completed_date=d(san + timedelta(days=6)))

    rec = m(530)
    san = rec + timedelta(days=40)
    start = san + timedelta(days=21)
    p = hall("WF-TIME-2", AG[3], VILLAGES[8], 10, rec, san, days=240, start=start)
    vs = [visit(1, "baseline", start)]
    for n in range(1, 15):
        when = start + timedelta(days=30 * n)
        if when > as_of:
            break
        still = n >= 12
        vs.append(visit(n + 1, "monthly", when, "no_change" if still else "changed",
                        "plastering in progress" if still else f"walls at stage {n}",
                        "cant_tell" if still else "shown"))
    add("time_late", "time_rules", {"time_rules": ["PAST_PROMISED_TIME"]},
        "Eight months promised, sixteen months on, and stopped",
        "Promised in 8 months; 16 months later it is not finished and the site is still.",
        [f"Sanctioned {san:%d %b %Y}", "Still not complete",
         "The last three monthly videos show no change"], p,
        status="SANCTIONED", site_visits=vs)

    # --- Site Progress ---
    rec = m(140)
    san = rec + timedelta(days=30)
    start = san + timedelta(days=20)
    p = hall("WF-SITE-1", AG[4], VILLAGES[9], 11, rec, san, start=start)
    add("site_reused", "site_progress", {"site_progress": ["FOOTAGE_USED_BEFORE",
                                                           "SAME_PLACE_AS_ANOTHER_WORK"]},
        "The first site video was filmed for another work",
        "The first site video reuses footage from another hall's video.",
        [f"Sanctioned {san:%d %b %Y}", f"First site video {start:%d %b %Y}"], p,
        status="SANCTIONED",
        site_visits=[visit(1, "baseline", start,
                           reused_from=[{"work_id": "WF-TIME-2", "visit_id": "V3",
                                         "frames": 42}],
                           same_place_as=[{"work_id": "WF-TIME-2", "inliers": 875}])])

    rec = m(200)
    san = rec + timedelta(days=30)
    start = san + timedelta(days=20)
    p = hall("WF-SITE-2", AG[0], VILLAGES[11], 12, rec, san, start=start)
    add("site_claim", "site_progress", {"site_progress": ["CLAIM_NOT_SHOWN"]},
        "\"Roof slab cast\", twice, and the videos don't show it",
        '"Roof slab cast" claimed in two monthly videos that show no slab.',
        [f"Sanctioned {san:%d %b %Y}", "Four site videos: the claim matches the first two, "
         "not the last two"], p, status="SANCTIONED",
        site_visits=[visit(1, "baseline", start),
                     visit(2, "monthly", start + timedelta(days=30), "changed",
                           "foundation done", "shown"),
                     visit(3, "monthly", start + timedelta(days=60), "changed",
                           "walls up to lintel", "shown"),
                     visit(4, "monthly", start + timedelta(days=90), "changed",
                           "roof slab cast", "not_shown",
                           claim_reason="no slab visible at viewpoints 2-4; walls only"),
                     visit(5, "monthly", start + timedelta(days=120), "no_change",
                           "roof slab cast, plaster started", "not_shown",
                           claim_reason="the same walls, no slab, no plaster")])

    rec = m(160)
    san = rec + timedelta(days=30)
    start = san + timedelta(days=20)
    p = road("WF-SITE-3", AG[2], VILLAGES[13], 13, rec, san, start=start)
    add("site_elsewhere", "site_progress", {"site_progress": ["NOT_FILMED_AT_THIS_SITE"]},
        "A monthly video filmed 2.4 km away",
        "The third monthly video was filmed 2.4 km from the road.",
        [f"Sanctioned {san:%d %b %Y}", "Three site videos: the third filmed elsewhere"], p,
        status="SANCTIONED",
        site_visits=[visit(1, "baseline", start),
                     visit(2, "monthly", start + timedelta(days=30), "changed",
                           "base laid", "shown"),
                     visit(3, "monthly", start + timedelta(days=60), None,
                           "concrete laid on 200 m", None, gps_inside=False,
                           gps_distance_m=2400, views_match_site=False,
                           viewpoints_matched=0)])
    return ex, bg_works


# ---- the page's Data tab, in plain words, and the engine's copy of the same data ---------------

KIND = {"baseline": "First visit", "monthly": "Monthly visit", "check": "Surprise check",
        "final": "Final visit"}
VERDICT = {"shown": "shown", "not_shown": "not shown", "cant_tell": "can't tell"}


def day(x) -> str:
    return date.fromisoformat(str(x)[:10]).strftime("%d %b %Y")


def video(v: dict) -> dict:
    """One site video, as the video job's readings say, in plain words."""
    r, bits = v["readings"], []
    for x in r.get("reused_from") or []:
        bits.append(f"{x['frames']} frames already seen in {x['work_id']}'s video")
    for x in r.get("same_place_as") or []:
        bits.append(f"same place as {x['work_id']}'s site")
    if r.get("gps_inside") is False:
        bits.append(f"GPS {(r.get('gps_distance_m') or 0) / 1000:.1f} km outside the site")
    if r.get("views_match_site") is False:
        bits.append("views don't match the site")
    if v.get("claim"):
        said = VERDICT.get(r.get("claim_verdict"))
        bits.append(f"claim \"{v['claim']}\"" + (f": {said}" if said else ""))
    if r.get("change") == "no_change":
        bits.append("no change since last month")
    return {"visit": v["visit_id"], "date": day(v["captured_at"]), "kind": KIND[v["kind"]],
            "reading": "; ".join(bits) or "at the site, all 5 viewpoints marked"}


def videos(vs: list[dict]) -> list[dict]:
    """A long run of ordinary monthly visits is told in one line."""
    rows = [video(v) for v in vs]
    plain = [i for i, v in enumerate(vs) if v["kind"] == "monthly"
             and v["readings"].get("change") == "changed"
             and v["readings"].get("claim_verdict") == "shown"]
    if len(rows) <= 5 or len(plain) < 3:
        return rows
    a, b = plain[0], plain[-1]
    run = {"visit": f"{rows[a]['visit']} to {rows[b]['visit']}", "date": "monthly",
           "kind": "Monthly visits", "reading": "new work each month; the claim shown"}
    return rows[:a] + [run] + rows[b + 1:]


def plain_data(examples: list[dict], records: list[dict], traces: dict) -> dict:
    """What the agents compare the filings with in this demo, as the Data tab shows it."""
    # rates other agencies filed: every priced line of every filing, by item
    paid: dict[tuple, list] = {}
    for w in records:
        for site in (w.get("cost_form") or {}).get("sites") or []:
            for ln in site.get("lines") or []:
                if ln.get("material_id") and ln.get("rate"):
                    paid.setdefault((ln["item"], ln["unit"]), []).append(
                        (float(ln["rate"]), w["agency_name"], w["work_id"]))
    rates = []
    for (item, unit), xs in paid.items():
        forms = {x[2] for x in xs}
        if len(forms) < 5:
            continue
        vals = sorted(x[0] for x in xs)
        rates.append({"item": item, "unit": unit, "usual": vals[len(vals) // 2],
                      "low": vals[0], "high": vals[-1], "forms": len(forms),
                      "agencies": len({x[1] for x in xs})})
    standard = []
    for c in traces["cost_lights"]["checks"]:
        for site in (c["picture"] or {}).get("sites") or [] if c["id"] == "cost_estimate" else []:
            ref = site.get("reference")
            if ref:
                standard.append({"item": "Solar street light, 12 W LED, 40 Wp panel",
                                 "unit": "light", "usual": ref["median"],
                                 "ask_above": site["question_above"], "works": ref["n"],
                                 "where": f"real eSAKSHI works in {site['where']}"})
    floors = {f["code"]: f["facts"] for c in traces["time_fast"]["checks"]
              for f in c["findings"]}
    quantity = {f["code"]: f["facts"] for c in traces["cost_quantity"]["checks"]
                for f in c["findings"]}
    rules = [
        {"agent": "cost_estimate", "text": "Cement in M20 concrete: "
         + quantity["MATERIAL_QUANTITY_ABOVE_SIZE"]["why"].split(", ", 1)[1]},
        {"agent": "cost_estimate", "text": f"The whole estimate is asked about when it is "
         f"{whole.GAP_SHARE:.0%}+ and Rs {whole.GAP_MIN_RS:,}+ above the fair price"},
        {"agent": "cost_estimate", "text": f"A trade's day rate is asked about at "
         f"{labour_rules.RATE_MARGIN:g} times what other agencies here pay that trade; how many "
         "workers a work needs is never judged"},
        {"agent": "dup_split", "text": f"Map pins within {repeat.PIN_METRES:.0f} m of a "
         "sanctioned work of the same kind are one site"},
        {"agent": "dup_split", "text": f"A rebuild within {dup_agent.REBUILT_WITHIN.days // 365}"
         " years of completion is asked about"},
        {"agent": "dup_split", "text": f"Split: 2 to {repeat.SPLIT_MAX} alike pieces, every one "
         f"{repeat.SPLIT_SHARE:.0%} to 100% of a limit (Rs 5 or 10 lakh)"},
        {"agent": "time_rules", "text": f"A 350 m CC road takes at least "
         f"{floors['FINISHED_TOO_FAST']['limit']} days"},
        {"agent": "time_rules", "text": f"Late after the promised time plus half of it again "
         f"(at least {window.GRACE_MIN_DAYS} days)"},
        {"agent": "site_progress", "text": "Not filmed here only when the GPS and the views "
         "both disagree"},
        {"agent": "site_progress", "text": "A claim not shown on two monthly videos in a row"},
    ]
    ids = {e["form"]["recommendation_ref"] for e in examples}
    works = [{"id": w["work_id"], "what": w["description"], "agency": w["agency_name"],
              "amount": w["amount"],
              "state": (f"Completed {day(w['completed_date'])}" if w.get("completed_date")
                        else "Recommended" if w["status"] == "RECOMMENDED" else "Sanctioned")}
             for w in records if w["work_id"] not in ids and not w["work_id"].startswith("WF-BG")]
    filings = [{"id": w["work_id"], "what": w["description"], "agency": w["agency_name"],
                "amount": w["amount"], "filed": day(w["recommended_date"])}
               for w in records if w["work_id"].startswith("WF-BG")]
    return {
        "where": f"{DISTRICT}, Uttar Pradesh",
        "rates": sorted(rates, key=lambda r: -r["forms"]), "standard": standard,
        "rules": rules, "works": works, "filings": filings,
        "after": {e["key"]: e["later"] for e in examples},
        "videos": {e["key"]: videos(e["record"]["site_visits"]) for e in examples
                   if e["record"].get("site_visits")},
    }


def demo_file(examples: list[dict], records: list[dict]) -> dict:
    """The engine's copy (drishti/demo.py): every example record, without its district (the
    demo places it in the checked form's), and each example's record after sanction."""
    return {"about": "Made-up example data for the work intelligence form's demo (T134), "
                     "written by data/trial/work_form_examples.py. Not real works.",
            "records": [{k: v for k, v in w.items() if k not in PLACE_KEYS} for w in records],
            "later": {e["form"]["recommendation_ref"]: e["record"] for e in examples
                      if e["record"]}}


def main() -> None:
    works, info = load()
    as_of = info["as_of"]
    dist = next(w for w in works if w.get("district_name") == DISTRICT)
    place = {"district_lgd": dist["district_lgd"], "state_lgd": dist.get("state_lgd"),
             "state_name": dist.get("state_name"), "district_name": DISTRICT}
    examples, background = build(as_of)
    for w in background:
        w.update(place)
    records = []
    for e in examples:
        w = pswif.to_work(e["form"], today=as_of, **e["record"])
        w.update(place)
        records.append(w)
    # every filing is known to the district: the background, and each example to the others
    ctx = Context(stats=build_store(works), as_of=as_of,
                  data=indexes(works + background + records))
    out, lines, bad, traces = [], [], [], {}
    for e, w in zip(examples, records, strict=True):
        checked = validate(w["cost_form"], today=as_of)
        trace = explain(w, ctx)
        fired = {c["id"]: sorted(f["code"] for f in c["findings"] if f["risk"] > 0)
                 for c in trace["checks"]}
        fired = {k: v for k, v in fired.items() if v}
        want = {k: sorted(v) for k, v in e["codes"].items()}
        if fired != want:
            bad.append(f"{e['key']}: raises {fired}, meant {want}")
        traces[e["key"]] = trace
        statuses = {c["id"]: c["status"] for c in trace["checks"]}
        lines.append(f"{e['key']:15} {trace['result']['band']:7} {trace['result']['score']:.3f} "
                     f"form ready {checked['ready']!s:5} {fired} {statuses}")
        print(lines[-1])
        out.append({"id": e["key"], "agent": e["agent"], "title": e["title"],
                    # the questions it is meant to raise (the public examples check them, T142)
                    "codes": e["codes"],
                    "story": e["story"], "later": e["later"], "form": e["form"],
                    "form_ready": checked["ready"],
                    "form_issues": [i["message"] for i in checked["issues"]
                                    if i["level"] == "fix"],
                    "trace": trace})
    if bad:
        sys.exit("examples no longer show what they say:\n" + "\n".join(bad))
    # the engine's demo data, and the live check's path through it (POST /work-form/check?demo=
    # true): the district's real works, the demo records, the form with its record after sanction
    DEMO.parent.mkdir(parents=True, exist_ok=True)
    DEMO.write_text(json.dumps(demo_file(examples, background + records), ensure_ascii=False,
                               separators=(",", ":"), default=str), encoding="utf-8")
    demo._text.cache_clear()
    district = [w for w in works if w.get("district_lgd") == place["district_lgd"]]
    for e, o in zip(examples, out, strict=True):
        w = pswif.to_work(e["form"], today=as_of, **demo.later(e["form"]["recommendation_ref"]))
        w.update(place)
        live = explain(w, Context(stats=ctx.stats, as_of=as_of,
                                  data=indexes(district + demo.records(w) + [w])))
        asked = sorted(f["code"] for c in live["checks"] for f in c["findings"] if f["risk"] > 0)
        if asked != sorted(f["code"] for c in o["trace"]["checks"] for f in c["findings"]
                           if f["risk"] > 0):
            bad.append(f"{e['key']}: the demo check raises {asked}")
    if bad:
        sys.exit("the demo check differs from the examples:\n" + "\n".join(bad))
    SUMMARY.write_text(f"{len(works):,} dashboard works, as of {as_of}; district {DISTRICT}; "
                       f"{len(background)} background filings\n" + "\n".join(lines) + "\n",
                       encoding="utf-8")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"source": f"eSAKSHI dashboard tables, {len(works):,} works, "
                                         f"as of {as_of}; made-up filings in {DISTRICT}",
                               "as_of": str(as_of), "examples": out,
                               "data": plain_data(examples, background + records, traces)},
                              ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)} ({OUT.stat().st_size // 1024} KB) and "
          f"{DEMO.relative_to(ROOT)} ({DEMO.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
