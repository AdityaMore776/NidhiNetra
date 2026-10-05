"""The website's work intelligence form, read by the four agents (T134).

The Pre-Sanction Work Intelligence Form (PSWIF v1.0, apps/web/forms/) is what an implementing
agency fills on the website. Its "Export Structured JSON" (and its saved drafts) are one flat
object of field names: `work_type`, `road_length_m`, `latitude`, `boq_desc_3`, ... This module
turns that object into the two things the agents read:

  to_cost_form(p)   the engine's cost estimate form (reference/cost_form.yaml): the work, its
                    site and map pins, its size, its expense lines, timing and totals, and the
                    agency's answers about nearby works. Cost judges its lines and its whole,
                    Duplicate Work its map pins and declarations, Time & Rules its estimated time.
  to_work(p, ...)   the work record the pipeline assesses, with that form attached.

Rules of the mapping, so nothing is invented:
  - a field is filled only from what the agency wrote; a field the website form never asks is
    left out, and validate.py does not require it (versions.not_asked);
  - a line's material is recognised from its description by materials.match (unknown or
    ambiguous: left unrecognised, still counted in the total);
  - the website form has no "confirm" step, so a check that asks the agency to confirm a line
    counts as confirmed when that line carries a written justification, and a check on the
    whole estimate when the rate-deviation notes are filled;
  - the estimated duration already includes the days lost to weather, so no lost months are
    added to it.
"""

from __future__ import annotations

import math
import re
from datetime import date

from drishti.cost_form import catalog, materials, versions
from drishti.cost_form.validate import CONFIRM, validate

MONTH_DAYS = 30.44

# ---- the form's choices to the engine's codes --------------------------------------------------

_ROAD = {"CC road": "ROAD_CC", "Bituminous road": "ROAD_BT", "Paver block road": "FOOTPATH",
         "Pathway": "FOOTPATH", "Bridge": "BRIDGE", "Culvert": "CULVERT"}
_WATER = {"Overhead tank": "WATER_TANK", "Ground reservoir": "WATER_TANK",
          "Pipeline": "WATER_SUPPLY", "Water treatment": "WATER_SUPPLY",
          "Public tap / standpost": "WATER_SUPPLY", "Borewell / source": "BOREWELL",
          "Sanitation asset": "TOILET_BLOCK"}
_ENERGY = {"Street lights": "STREET_LIGHT", "Solar street lights": "STREET_LIGHT",
           "High mast": "HIGH_MAST", "Solar rooftop": "SOLAR_PLANT",
           "Distribution / electrification": "ELECTRICITY"}
_NATURE = {"New asset": "new", "Extension / additional component": "extension",
           "Continuation / next phase": "continuation", "Repair / renovation": "upgrade",
           "Reconstruction / rebuild": "reconstruction",
           "Replacement of movable asset": "purchase"}
_LAND = {"Central Government": "central_govt", "State / UT Government": "state_govt",
         "Local Government / Panchayat / ULB": "panchayat",
         "Government-controlled institution": "public_institution",
         "Eligible Society/Trust long-term lease": "other", "Private": "other",
         "Religious body / religious land": "other", "Unknown / disputed": "other"}
_TERRAIN = {"Plain": "plain", "Rolling": "rolling", "Hilly / steep": "hilly",
            "Riverine / flood-prone": "floodplain", "Coastal": "coastal", "Dense urban": "plain",
            "Remote / difficult access": "rolling"}
_ACCESS = {"Motorable all-weather": "truck", "Narrow road / limited vehicle": "tractor_only",
           "Foot / manual carry required": "head_load_only", "Seasonal access": "tractor_only",
           "Boat / special access": "head_load_only"}
_BASIS = {"State/Dept SoR": "sor", "CPWD/standard schedule": "sor",
          "District recent rates": "market_rate", "GeM / rate contract": "gem",
          "Approved quotation": "quotation", "Other benchmark": "other"}
_EXISTING_ROAD = {"New alignment": "new_alignment", "Earthen": "earth",
                  "Existing base retained": "wbm"}
_STRUCTURE = {"RCC framed": "rcc_frame", "Load-bearing masonry": "load_bearing",
              "Steel / prefab": "steel", "Mixed": "other", "Other": "other"}
_RELATION = {"Same asset, separate phase": "continues", "Rebuild / replacement": "continues",
             "Different asset at same campus/site": "different",
             "Parallel / adjacent infrastructure": "different"}
# units as typed on estimates -> the engine's unit ids
_UNITS = {
    "m": "m", "mtr": "m", "metre": "m", "meter": "m", "rm": "rm", "rmt": "rm", "running m": "rm",
    "km": "km", "mm": "mm", "ft": "ft", "sqm": "m2", "sq m": "m2", "m2": "m2", "sq.m": "m2",
    "sqmt": "m2", "sq mt": "m2", "sqft": "sqft", "sq ft": "sqft", "cum": "m3", "cu m": "m3",
    "cu.m": "m3", "m3": "m3", "cumt": "m3", "cft": "cft", "brass": "brass", "kg": "kg",
    "kgs": "kg", "qtl": "quintal", "quintal": "quintal", "t": "t", "mt": "t", "tonne": "t",
    "ton": "t", "bag": "bag", "bags": "bag", "nos": "nos", "no": "nos", "no.": "nos",
    "each": "nos", "pcs": "nos", "pair": "pair", "set": "set", "sets": "set",
    "thousand": "thousand", "1000 nos": "thousand", "day": "day", "days": "day",
    "manday": "day", "man-day": "day", "mandays": "day", "hour": "hour", "hr": "hour",
    "hrs": "hour", "l": "l", "ltr": "l", "litre": "l", "kl": "kl", "w": "w", "kw": "kw",
    "kwp": "kwp", "wp": "wp", "kva": "kva", "wh": "wh", "kwh": "kwh", "hp": "hp",
    "ls": "ls", "lump sum": "ls", "lumpsum": "ls", "l.s.": "ls", "job": "ls",
}


def _s(v) -> str:
    return v.strip() if isinstance(v, str) else ""


def _n(v) -> float | None:
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v) if math.isfinite(v) else None
    try:
        x = float(_s(v).replace(",", ""))
    except ValueError:
        return None
    return x if math.isfinite(x) else None


def _date(v) -> str | None:
    s = _s(v)[:10]
    try:
        return date.fromisoformat(s).isoformat()
    except ValueError:
        return None


def _put(d: dict, key: str, value) -> None:
    """Set only what the agency wrote."""
    if value is not None and value != "":
        d[key] = value


def _words(*texts) -> str:
    return " ".join(_s(t).lower() for t in texts)


def work_type(p: dict) -> str:
    """The engine's work type code for the form's type and subtype."""
    kind = _s(p.get("work_type"))
    text = _words(p.get("work_title"), p.get("scope_of_work"), p.get("equipment_category"))
    if kind == "road":
        return _ROAD.get(_s(p.get("road_subtype")), "OTHER")
    if kind == "building":
        # the title names the building; the scope often names landmarks ("opposite the school")
        title = _words(p.get("work_title"))
        for words, code in ((("hall", "bhawan", "bhavan", "chaupal"), "COMMUNITY_HALL"),
                            (("school", "classroom"), "SCHOOL_BUILDING"),
                            (("health", "phc", "dispensary", "hospital"), "HEALTH_BUILDING"),
                            (("library",), "LIBRARY"), (("cremat", "shamshan"), "CREMATORIUM"),
                            (("toilet", "sulabh"), "TOILET_BLOCK"),
                            (("bus shelter", "bus stand"), "BUS_SHELTER")):
            if any(w in title for w in words):
                return code
        sector = _s(p.get("sector"))
        return {"Education": "SCHOOL_BUILDING", "Public health": "HEALTH_BUILDING"}.get(
            sector, "COMMUNITY_HALL")
    if kind == "water":
        return _WATER.get(_s(p.get("water_system_type")), "OTHER")
    if kind == "drainage":
        if "check dam" in text:
            return "CHECK_DAM"
        if "pond" in text or "talab" in text:
            return "POND"
        return "DRAIN"
    if kind == "energy":
        return _ENERGY.get(_s(p.get("energy_asset_type")), "OTHER")
    if kind == "equipment":
        for words, code in ((("cctv", "camera"), "CCTV"), (("ambulance",), "AMBULANCE"),
                            (("computer", "laptop"), "COMPUTER"), (("furniture", "bench"),
                                                                    "FURNITURE"),
                            (("sport", "gym"), "SPORTS_EQUIPMENT"),
                            (("medical", "x-ray", "ecg"), "MEDICAL_EQUIPMENT"),
                            (("vehicle", "tractor", "van"), "VEHICLE")):
            if any(w in text for w in words):
                return code
        return "OTHER"
    if kind == "park":
        return "PLAYGROUND"
    return "OTHER"


def _battery_wh(spec: str) -> float | None:
    m = re.search(r"(\d+(?:\.\d+)?)\s*wh\b", spec, re.I)
    if m:
        return float(m.group(1))
    ah = re.search(r"(\d+(?:\.\d+)?)\s*ah\b", spec, re.I)
    volts = re.search(r"(\d+(?:\.\d+)?)\s*v\b", spec, re.I)
    return float(ah.group(1)) * float(volts.group(1)) if ah and volts else None


def _size(p: dict, code: str) -> dict:
    s: dict = {}
    if code in ("ROAD_CC", "ROAD_BT"):
        _put(s, "length_m", _n(p.get("road_length_m")) or _n(p.get("route_length_m")))
        _put(s, "width_m", _n(p.get("road_width_m")))
        thick = _n(p.get("pavement_thickness_mm"))
        _put(s, "cc_thickness_mm" if code == "ROAD_CC" else "bt_thickness_mm", thick)
        grade = re.search(r"\bM\s?(\d{2})\b", _s(p.get("road_material_grade")), re.I)
        if grade and code == "ROAD_CC":
            g = f"M{grade.group(1)}"
            s["concrete_grade"] = g if g in ("M10", "M15", "M20", "M25", "M30", "M35",
                                             "M40") else "other"
        base = (_n(p.get("base_thickness_mm")) or 0) + (_n(p.get("subbase_thickness_mm")) or 0)
        if base > 0:
            spec = _words(p.get("road_layer_spec"))
            s["base_type"] = next((b for b in ("wmm", "wbm", "gsb", "pcc") if b in spec),
                                  "brick_soling" if "brick" in spec else "other")
            s["base_thickness_mm"] = base
        existing = _s(p.get("existing_road_condition"))
        if existing == "Damaged paved road":
            s["existing_surface"] = "old_cc" if code == "ROAD_CC" else "old_bt"
        else:
            _put(s, "existing_surface", _EXISTING_ROAD.get(existing))
        _put(s, "shoulder_width_m", _n(p.get("shoulder_width_m")))
        _put(s, "side_drain_m", _n(p.get("road_drain_length_m")))
        _put(s, "cross_drains_nos", _n(p.get("culvert_count")))
    elif code == "FOOTPATH":
        _put(s, "length_m", _n(p.get("road_length_m")) or _n(p.get("route_length_m")))
        _put(s, "width_m", _n(p.get("road_width_m")))
        t = _n(p.get("pavement_thickness_mm"))
        if t is not None:
            s["paver_thickness_mm"] = f"{t:g}" if f"{t:g}" in ("60", "80", "100") else "other"
    elif code in ("COMMUNITY_HALL", "SCHOOL_BUILDING", "HEALTH_BUILDING", "LIBRARY",
                  "CREMATORIUM"):
        _put(s, "built_up_area_m2", _n(p.get("builtup_area")))
        _put(s, "floors_nos", _n(p.get("floors")))
        _put(s, "rooms_nos", _n(p.get("rooms")))
        _put(s, "floor_height_m", _n(p.get("floor_height")))
        _put(s, "structure", _STRUCTURE.get(_s(p.get("structure_type"))))
        roof = _words(p.get("roof_type"))
        if roof:
            s["roof"] = "rcc_slab" if "rcc" in roof or "slab" in roof else \
                "sheet_on_truss" if "sheet" in roof else "other"
        found = _words(p.get("foundation_type"))
        if found:
            s["foundation"] = next((f for f in ("raft", "pile", "strip") if f in found),
                                   "isolated_footing" if "isolated" in found or "footing" in found
                                   else "other")
    elif code == "STREET_LIGHT":
        _put(s, "lights_nos", _n(p.get("energy_quantity")))
        solar = _s(p.get("energy_asset_type")) == "Solar street lights" or \
            (_n(p.get("solar_wp")) or 0) > 0
        s["light_power"] = "solar_standalone" if solar else "grid"
        _put(s, "led_w", _n(p.get("watt_per_unit")))
        _put(s, "pole_height_m", _n(p.get("pole_height_m")))
        if solar:
            _put(s, "panel_wp", _n(p.get("solar_wp")))
            spec = _s(p.get("battery_spec"))
            _put(s, "battery_wh", _battery_wh(spec))
            low = spec.lower()
            if low:
                s["battery_type"] = "lifepo4" if "lifepo4" in low or "lfp" in low else \
                    "li_ion" if "lithium" in low or "li-ion" in low else \
                    "lead_acid" if "lead" in low or "tubular" in low else "other"
        else:
            _put(s, "cable_m", _n(p.get("cabling_length_m")))
    elif code == "HIGH_MAST":
        _put(s, "masts_nos", _n(p.get("energy_quantity")))
        _put(s, "mast_height_m", _n(p.get("pole_height_m")))
        _put(s, "lamp_w", _n(p.get("watt_per_unit")))
        _put(s, "cable_m", _n(p.get("cabling_length_m")))
    elif code == "WATER_TANK":
        kl = _n(p.get("storage_capacity_kl"))
        if kl:
            s["tanks_nos"] = 1
            s["capacity_l"] = kl * 1000
        _put(s, "connecting_pipe_m", _n(p.get("pipeline_length_m")))
    elif code == "WATER_SUPPLY":
        _put(s, "length_m", _n(p.get("pipeline_length_m")))
        _put(s, "pipe_dia_mm", _n(p.get("pipeline_diameter_mm")))
        _put(s, "house_connections_nos", _n(p.get("connections_users")))
    elif code == "DRAIN":
        _put(s, "length_m", _n(p.get("drain_length_m")))
        _put(s, "inner_width_m", _n(p.get("drain_width_m")))
        _put(s, "inner_depth_m", _n(p.get("drain_depth_m")))
        dt = _words(p.get("drain_type"))
        if dt:
            s["drain_cover"] = "covered" if "cover" in dt else "open"
    elif code == "PLAYGROUND":
        _put(s, "area_m2", _n(p.get("park_area")) or _n(p.get("developed_area")))
        _put(s, "fencing_m", _n(p.get("fencing_length")))
        _put(s, "flood_lights_nos", _n(p.get("park_lighting_count")))
    elif code == "OTHER":
        _put(s, "size_measure", _s(p.get("other_primary_unit")))
        _put(s, "size_value", _n(p.get("other_primary_qty")))
        _put(s, "specification", _s(p.get("other_technical_spec")))
    return s


def _boq_rows(p: dict) -> list[dict]:
    """The BOQ table's rows, in order (the form numbers them boq_desc_1, boq_desc_2, ...)."""
    nums = sorted({int(m.group(1)) for k in p if (m := re.fullmatch(r"boq_desc_(\d+)", k))})
    rows = []
    for n in nums:
        row = {f: p.get(f"boq_{f}_{n}") for f in ("code", "desc", "unit", "qty", "rate",
                                                   "source", "measure_ref", "just")}
        if _s(row["desc"]) or _n(row["qty"]) or _n(row["rate"]):
            rows.append(row)
    return rows


def _lines(p: dict, goods: bool) -> list[dict]:
    lines = []
    for row in _boq_rows(p):
        item = _s(row["desc"])
        mid = materials.match(item)
        unit = _UNITS.get(_s(row["unit"]).lower().rstrip("."), _s(row["unit"]).lower() or None)
        group = ("labour" if mid and mid.startswith("labour") else
                 "goods" if goods and not mid else "materials")
        ln: dict = {"group": group, "item": item}
        _put(ln, "material_id", mid)
        _put(ln, "unit", unit)
        _put(ln, "quantity", _n(row["qty"]))
        _put(ln, "rate", _n(row["rate"]))
        basis = _BASIS.get(_s(row["source"]))
        _put(ln, "basis", basis)
        if basis == "sor":
            _put(ln, "sor_code", _s(row["code"]))
        if basis == "gem":
            _put(ln, "gem_id", _s(row["code"]) or _s(row["measure_ref"]))
        if group == "goods":
            _put(ln, "spec", _s(p.get("equipment_spec")))
        _put(ln, "justification", _s(row["just"]))
        lines.append(ln)
    lump = _n(p.get("lumpsum_components"))
    if lump:
        lines.append({"group": "other", "item": "Lump-sum components (as on the estimate)",
                      "unit": "ls", "amount": lump, "basis": "other",
                      # the website form asks no source for it (T135: without one, a filing
                      # with any lump sum could never be judged)
                      "basis_other": "Lump sum on the agency's estimate (section F)"})
    return lines


def _location(p: dict, linear: bool) -> dict:
    loc: dict = {}
    _put(loc, "block", _s(p.get("block_tehsil")))
    _put(loc, "gp_or_ward", _s(p.get("village_ward")))
    _put(loc, "village", _s(p.get("village_ward")))
    _put(loc, "pin", _s(p.get("pincode")))
    lat, lon = _n(p.get("latitude")), _n(p.get("longitude"))
    s_lat, s_lon = _n(p.get("start_lat")), _n(p.get("start_lon"))
    e_lat, e_lon = _n(p.get("end_lat")), _n(p.get("end_lon"))
    if linear and s_lat is not None and s_lon is not None:
        lat, lon = s_lat, s_lon
    _put(loc, "lat", lat)
    _put(loc, "lon", lon)
    if linear:
        _put(loc, "end_lat", e_lat)
        _put(loc, "end_lon", e_lon)
    return loc


def _earlier(p: dict) -> list[dict]:
    """The agency's answer about nearby sanctioned works it names (section D)."""
    ids = [x.strip() for x in re.split(r"[,;\s]+", _s(p.get("known_nearby_work_ids"))) if x.strip()]
    answer = _RELATION.get(_s(p.get("nearby_work_relationship")))
    if not ids or not answer:
        return []
    rows = []
    for wid in ids:
        row = {"earlier_work": wid, "answer": answer}
        if answer == "different":
            _put(row, "difference", _s(p.get("overlap_declaration")))
        rows.append(row)
    return rows


def to_cost_form(p: dict, today: date | None = None) -> dict:
    """The engine's cost estimate form for a PSWIF export (module note)."""
    p = p if isinstance(p, dict) else {}

    code = work_type(p)
    nature = _NATURE.get(_s(p.get("work_nature")))
    goods = catalog.is_goods(code, nature)
    linear = catalog.is_linear(code)

    work: dict = {"work_type": code}
    if code == "OTHER":
        _put(work, "other_type_name", _s(p.get("work_title")))
    jur = _s(p.get("recommendation_jurisdiction"))
    if jur:
        work["inside_constituency"] = jur.startswith("Normal")
        if not work["inside_constituency"]:
            _put(work, "outside_reason", _s(p.get("special_case_ref")) or jur)
    _put(work, "land_owner", _LAND.get(_s(p.get("land_ownership"))))
    if "no_land_acquisition" in p:
        work["land_free"] = bool(p.get("no_land_acquisition"))
    _put(work, "nature", nature)
    if nature in ("continuation", "extension", "upgrade", "reconstruction"):
        _put(work, "earlier_work_id", _s(p.get("prior_work_id")) or _s(p.get("parent_project_id")))
        _put(work, "existing_description", _s(p.get("baseline_existing_condition")))
    _put(work, "description", _s(p.get("scope_of_work")))

    conditions: dict = {}
    if not goods:
        _put(conditions, "terrain", _TERRAIN.get(_s(p.get("terrain"))))
        _put(conditions, "access", _ACCESS.get(_s(p.get("site_access"))))
        _put(conditions, "road_distance_m", _n(p.get("motorable_access_distance_m")))

    rec: dict = {}
    _put(rec, "work_id", _s(p.get("recommendation_ref")))
    _put(rec, "mp_amount", _n(p.get("mp_recommended_amount")))
    rec["recommended_type"] = code
    _put(rec, "recommended_description", _s(p.get("work_title")))
    _put(rec, "recommended_date", _date(p.get("mp_recommendation_date")))

    charges: dict = {}
    if _s(p.get("tax_treatment")) in ("Included in rates", "Not applicable / exempt"):
        charges["gst_percent"] = 0
        charges["gst_amount"] = 0
    _put(charges, "other_fees_amount", _n(p.get("other_charges")))

    timing: dict = {}
    start = _date(p.get("expected_start_date"))
    if start:
        timing["start_month"] = start[:7]
    days = _n(p.get("estimated_duration_days"))
    if days:
        timing["duration_months"] = round(days / MONTH_DAYS, 2)
    sor = " ".join(x for x in (_s(p.get("sor_name")), _s(p.get("sor_year"))) if x)
    _put(timing, "sor_edition", sor)

    totals: dict = {}
    _put(totals, "total_as_per_document", _n(p.get("technical_estimate")))
    _put(totals, "reason_differs_from_mp", _s(p.get("rate_deviation_notes"))
         or _s(p.get("mp_additional_consent_ref")))

    prepared: dict = {}
    if _s(p.get("estimate_engineer")):
        prepared["prepared_by_role"] = "ia_engineer"
    _put(prepared, "prepared_by_designation", _s(p.get("preparing_designation")))
    _put(prepared, "site_photo_before", _s(p.get("presanction_site_evidence")))
    _put(prepared, "land_noc", _s(p.get("land_proof_ref")))

    certified = bool(p.get("certify_accuracy"))
    declarations = {
        "decl_no_land_cost": bool(p.get("no_land_acquisition")),
        "decl_no_maintenance": bool(p.get("no_om_funding")),
        # the form asks every funding share outright, and the agency certifies them
        "decl_not_funded_elsewhere": certified,
        "decl_actuals": bool(p.get("consent_agent_verification")),
    }

    site = {"location": _location(p, linear), "size": _size(p, code), "lines": _lines(p, goods)}
    if conditions:
        site["site_conditions"] = conditions
    filed = _date(p.get("ida_received_date")) or _date(p.get("mp_recommendation_date"))
    form = {"form_version": versions.PSWIF, "filed_on": filed,
            "recommendation": rec, "work": work, "sites": [site],
            "charges": charges, "timing": timing, "totals": totals, "prepared": prepared,
            "declarations": declarations, "earlier_works": _earlier(p)}
    form["confirmed"] = _confirmed(form, p, today)
    return form


def _confirmed(form: dict, p: dict, today: date | None) -> list[str]:
    """The checks the agency has answered in writing (module note)."""
    lines = form["sites"][0]["lines"]
    justified = {j for j, ln in enumerate(lines) if ln.get("justification")}
    notes = bool(_s(p.get("rate_deviation_notes")))
    out = []
    for issue in validate(form, today=today)["issues"]:
        if issue["level"] != CONFIRM:
            continue
        m = re.match(r"sites\[0\]\.lines\[(\d+)\]", issue["field"])
        if (m and int(m.group(1)) in justified) or (not m and notes):
            out.append(issue["key"])
    return out


def status(p: dict) -> str:
    return "SANCTIONED" if _s(p.get("sanction_decision")) == "Sanction" and \
        _date(p.get("sanction_date")) else "RECOMMENDED"


def to_work(p: dict, district_lgd: str | None = None, today: date | None = None,
            **record) -> dict:
    """The work record the pipeline assesses, its form attached. `record` overrides or adds
    what happened after the form was filed (status, completed_date, site_visits, ...)."""
    p = p if isinstance(p, dict) else {}
    form = to_cost_form(p, today)
    meta = p.get("__meta") if isinstance(p.get("__meta"), dict) else {}
    village = _s(p.get("village_ward"))
    title = _s(p.get("work_title"))
    work = {
        "work_id": _s(p.get("recommendation_ref")) or _s(meta.get("work_id")) or "FORM",
        "source": "SCENARIO",
        "state_name": _s(p.get("state")) or None,
        "district_name": _s(p.get("district")) or None,
        "district_lgd": district_lgd,
        "constituency": None,
        "mp_name": None,          # never scored, never shown
        "agency_name": _s(p.get("implementing_agency")) or None,
        "work_type_code": form["work"]["work_type"],
        "description": f"{title} in {village}" if title and village and village.lower()
        not in title.lower() else title,
        "amount": _n(p.get("mp_recommended_amount")),
        "status": status(p),
        "recommended_date": _date(p.get("mp_recommendation_date")),
        "sanction_date": _date(p.get("sanction_date")) if status(p) == "SANCTIONED" else None,
        "completed_date": None,
        "is_outside_constituency": form["work"].get("inside_constituency") is False,
        "cost_form": form,
    }
    work.update(record)
    return work
