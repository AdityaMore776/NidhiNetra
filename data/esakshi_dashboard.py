r"""Read the eSAKSHI public dashboard's own exports into the engine's work records.

The dashboard (mplads.mospi.gov.in) lets anyone download four tables: Works Recommended,
Works Sanctioned, Works Completed and the MPs' Allocated Limit. Unlike the 2,09,993-work research
export, they carry the SANCTION DATE, the money DISBURSED and whether completion photos were
uploaded. A copy downloaded on 2 Oct 2026 sits in data/raw/esakshi_dashboard/ (gitignored: the
tables name people in descriptions; never commit them).

One record per work id, from the furthest stage it reached:
  Completed   -> COMPLETED, completed_date, amount_disbursed, has_image
  Sanctioned  -> SANCTIONED (its "Work Status" is kept as dashboard_status)
  Recommended -> SANCTIONED when it has a sanction date, else RECOMMENDED
The recommended amount is the work's amount (the sanctioned amount equals it on every one of the
4,993 works in both tables); a work seen only as completed takes its disbursed amount.

  district   the IDA's district (the text before the bracket), keyed by state, as
             "<STATE>|<DISTRICT>" so two states' districts of one name never meet
  agency     the IDA (the implementing district authority); the dashboard does not name the
             implementing agency below it
  type       eSAKSHI's category -> work type (drishti/reference/esakshi_categories.yaml);
             categories not in that file are printed and mapped to OTHER
  dates      a work seen only in the Completed table has no recommendation date: it is left empty,
             never estimated (the work-id counter predicts it only for ids the Recommended table
             already covers, so an estimate would add nothing)

Run: apps\engine\.venv\Scripts\python.exe data\esakshi_dashboard.py   (prints a profile)
"""

from __future__ import annotations

import csv
import os
import re
import sys
import zlib
from collections import Counter
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "engine"))
from drishti import reference  # noqa: E402

RAW = Path(os.environ.get("DRISHTI_DASHBOARD_DIR", ROOT / "data" / "raw" / "esakshi_dashboard"))
FILES = {"recommended": "Works_Recommended.csv", "sanctioned": "Works_Sanctioned.csv",
         "completed": "Works_Completed.csv", "allocated": "Allocated_Limit_for_Honble_MPs.csv"}
WORK_ID = re.compile(r"^(WS/MP\d+/\d{4}-\d{4}/\d+|NOREF-\w+)-(.*)$")
SANCTIONED_STATES = {"Sanction", "Vendor Identification", "Physical Inspection", "Time Estimation",
                     "Work partially Completed"}


def _rows(name: str) -> list[dict]:
    path = RAW / FILES[name]
    if not path.exists():
        raise SystemExit(f"{path} not found: put the dashboard exports in {RAW} (team pack)")
    with path.open(encoding="utf-8-sig", newline="") as f:
        return [{(k or "").strip(): (v or "").strip() for k, v in r.items()}
                for r in csv.DictReader(f)]


def _col(row: dict, *starts: str) -> str:
    for s in starts:                 # an exact name first: "WORK" is not "Work category"
        if s in row:
            return row[s]
    for k, v in row.items():
        if any(k.lower().startswith(s.lower()) for s in starts):
            return v
    return ""


def _date(s: str) -> date | None:
    try:
        return datetime.strptime(s.strip(), "%d-%b-%Y").date()
    except ValueError:
        return None


def _amount(s: str) -> float | None:
    try:
        v = float(s.replace(",", ""))
    except ValueError:
        return None
    return v if v > 0 else None


def parse_work(text: str) -> tuple[str | None, str | None]:
    """("WS/MP620/2024-2025/133166", "Construction of ...") from the dashboard's Work column,
    whose id is sometimes broken by a tab ("WS/<tab> MP620/...")."""
    squashed = re.sub(r"^\s*WS/\s*MP", "WS/MP", text.replace("\t", " ").strip())
    m = WORK_ID.match(squashed)
    if not m:
        return None, None
    return re.sub(r"\s+", "", m.group(1)), " ".join(m.group(2).split())


def district_of(ida: str) -> str:
    return " ".join(ida.split("(")[0].split()).upper()


def _base(row: dict, wid: str, category: str) -> dict:
    state = " ".join(_col(row, "State").split())
    ida = " ".join(_col(row, "IDA").split())
    district = district_of(ida)
    desc = _col(row, "Work description")
    wtype = reference.esakshi_type(category, desc)
    return {"work_id": wid, "source": "REAL", "house": "Lok Sabha", "term": "18th Lok Sabha",
            "state_lgd": state.upper(), "state_name": state, "district_lgd": f"{state.upper()}|"
            f"{district}", "district_name": district.title(),
            "constituency": _col(row, "Constituency"), "mp_name": _col(row, "Hon'ble Members"),
            "agency_name": ida, "fy": None, "work_type_code": wtype or "OTHER",
            "esakshi_category": category, "category": _col(row, "Work category"),
            "description": desc or None, "amount": None, "recommended_date": None,
            "sanction_date": None, "completed_date": None, "status": None, "quantity": None,
            "quantity_unit": None, "is_outside_constituency": False,
            "amount_disbursed": None, "has_image": None, "dashboard_status": None,
            "seen_in": []}


def load(verbose: bool = False) -> tuple[list[dict], dict]:
    works: dict[str, dict] = {}
    unmapped: Counter = Counter()
    skipped = Counter()

    def get(row: dict, col: str) -> dict | None:
        text = _col(row, col)
        wid, cat = parse_work(text)
        if wid is None and text.startswith("NA-"):
            # a recommendation the dashboard lists without an id: the ones still waiting for
            # sanction. A stable id from what identifies it, so a re-run gives the same one.
            cat = " ".join(text[3:].split())
            key = "|".join((_col(row, "Constituency"), _col(row, "Recommended date"),
                            _col(row, "Work description"), _col(row, "RECOMMENDED AMOUNT"), cat))
            wid = f"NOID-{zlib.crc32(key.encode('utf-8')):08x}"
            skipped["no work id (kept, waiting for sanction)"] += 1
        if wid is None:
            skipped["no work id"] += 1
            return None
        if wid not in works:
            works[wid] = _base(row, wid, cat or "")
            if reference.esakshi_type(cat) is None:
                unmapped[cat] += 1
        return works[wid]

    for r in _rows("recommended"):
        w = get(r, "WORK")
        if w is None:
            continue
        w["seen_in"].append("recommended")
        w["recommended_date"] = _date(_col(r, "Recommended date"))
        w["amount"] = _amount(_col(r, "RECOMMENDED AMOUNT"))
        w["sanction_date"] = _date(_col(r, "Sanction Date"))
        w["status"] = "SANCTIONED" if w["sanction_date"] else "RECOMMENDED"
    for r in _rows("sanctioned"):
        w = get(r, "Work")
        if w is None:
            continue
        w["seen_in"].append("sanctioned")
        w["recommended_date"] = w["recommended_date"] or _date(_col(r, "Recommended date"))
        w["sanction_date"] = w["sanction_date"] or _date(_col(r, "Sanction Date"))
        w["amount"] = w["amount"] or _amount(_col(r, "Sanction Amount"))
        st = _col(r, "Work Status")
        w["dashboard_status"] = st
        w["status"] = "COMPLETED" if st == "Work Completed" else "SANCTIONED"
    for r in _rows("completed"):
        w = get(r, "Work")
        if w is None:
            continue
        w["seen_in"].append("completed")
        w["status"] = "COMPLETED"
        w["completed_date"] = _date(_col(r, "Completion Date"))
        w["amount_disbursed"] = _amount(_col(r, "Amount Disbursed"))
        w["amount"] = w["amount"] or w["amount_disbursed"]
        w["has_image"] = _col(r, "Image").lower().startswith("image")
        w["description"] = w["description"] or (_col(r, "Work Description") or None)
    allocated = {}
    for r in _rows("allocated"):
        a = _amount(_col(r, "Allocated"))
        if a and _col(r, "Constituency"):
            allocated[_col(r, "Constituency")] = a
    out = list(works.values())
    for w in out:
        if w["recommended_date"]:
            fy = w["recommended_date"].year - (w["recommended_date"].month < 4)
            w["fy"] = f"{fy}-{fy + 1}"
    as_of = max(d for w in out for d in (w["recommended_date"], w["sanction_date"],
                                         w["completed_date"]) if d)
    info = {"works": len(out), "as_of": as_of, "unmapped_categories": dict(unmapped),
            "skipped": dict(skipped), "allocated_constituencies": len(allocated),
            "status": dict(Counter(w["status"] for w in out)),
            "with_recommended_date": sum(bool(w["recommended_date"]) for w in out),
            "with_sanction_date": sum(bool(w["sanction_date"]) for w in out)}
    if verbose:
        for k, v in info.items():
            print(f"{k}: {v}")
    return out, info


if __name__ == "__main__":
    load(verbose=True)
