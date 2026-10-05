r"""Build a Schedule of Rates file for the Cost agent from a digitised rate book (T096).

The rate books are scanned PDFs (no text layer), so their numbers are typed by hand into
apps/engine/drishti/reference/cost/sor_source/<book>.csv, one row per printed rate, each with
the PDF page it is on. This script checks that table and writes the engine's SoR format
(agents/cost_estimate/rates.py: load_sor / sor_rate) to

    apps/engine/drishti/reference/cost/sor_candidates/<book>.json

NOT to reference/cost/sor/, the folder the engine reads. Switching a rate book on changes what
the Cost agent says, and it waits for three things (docs/team/log, T096):
  1. the engine must take an SoR per circle (district), not per state: UP PWD issues one per
     circle, and a Jaunpur rate is not a Lucknow rate;
  2. SoR rates exclude GST, while agencies' forms mostly quote rates with tax: the comparison
     must add GST first, or every honest line looks high;
  3. the owner's go-ahead (T098).

Only rows with a material_id are mapped (`materials`); a row superseded by a later revision is
kept for the record but never mapped. Every row keeps its basis (GST excluded, carriage included,
at the quarry) and its source page.

Run:  apps\engine\.venv\Scripts\python.exe data\build_sor.py [book]   (default: every book)
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "engine"))
from drishti.agents.cost_estimate import rates  # noqa: E402
from drishti.cost_form import catalog  # noqa: E402

REF = ROOT / "apps" / "engine" / "drishti" / "reference" / "cost"
SOURCE = REF / "sor_source"
OUT = REF / "sor_candidates"

BOOKS = {
    "up_pwd_jaunpur_ghazipur_2025-26": {
        "state": "Uttar Pradesh",
        "circle": "Jaunpur-Ghazipur circle, PWD Uttar Pradesh",
        "districts": ["Jaunpur", "Ghazipur"],
        "edition": "UP PWD Schedule of Rates 2025-26, Jaunpur-Ghazipur circle "
                   "(from 01.05.2025; revised 15.10.2025)",
        "sources": {
            "SOR25-26": "https://uppwd.gov.in/site/writereaddata/siteContent/SOR/"
                        "202507091534027988Jaunpur_SOR25-26.pdf",
            "Circle-2025-10": "https://uppwd.gov.in/site/writereaddata/siteContent/SOR/"
                              "202510301745103558Jaunpur_Gazipur_Circle.pdf",
        },
        "gst": "excluded",
    },
}
COLUMNS = ["row", "chapter", "sl_no", "item", "unit", "rate", "material_id", "mapped_unit",
           "basis", "effective_from", "superseded_by", "source", "pdf_page", "printed_page",
           "note"]
BASES = {"gst_excluded", "cartage_8km_included", "at_quarry"}


def read(book: str) -> list[dict]:
    with (SOURCE / f"{book}.csv").open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    if rows and list(rows[0]) != COLUMNS:
        raise ValueError(f"{book}: columns are {list(rows[0])}, expected {COLUMNS}")
    return rows


def check(book: str, rows: list[dict]) -> list[str]:
    """Every problem with the table, or []."""
    meta = BOOKS[book]
    ids = [r["row"] for r in rows]
    bad = [f"duplicate row ids: {sorted({i for i in ids if ids.count(i) > 1})}"] \
        if len(set(ids)) != len(ids) else []
    mapped: dict[str, str] = {}
    for r in rows:
        where = f"{book} row {r['row']}"
        if r["source"] not in meta["sources"]:
            bad.append(f"{where}: unknown source {r['source']!r}")
        if not r["pdf_page"].isdigit():
            bad.append(f"{where}: no PDF page")
        if not set(filter(None, r["basis"].split(";"))) <= BASES:
            bad.append(f"{where}: unknown basis {r['basis']!r}")
        for s in filter(None, r["superseded_by"].split(";")):
            if s not in ids:
                bad.append(f"{where}: superseded by unknown row {s!r}")
        if r["rate"]:
            try:
                if float(r["rate"]) <= 0:
                    bad.append(f"{where}: rate must be positive")
            except ValueError:
                bad.append(f"{where}: rate {r['rate']!r} is not a number")
        mid = r["material_id"]
        if not mid:
            continue
        if not catalog.material(mid):
            bad.append(f"{where}: unknown material {mid!r}")
        elif rates.per_unit(mid, float(r["rate"] or 0), r["mapped_unit"]) is None:
            bad.append(f"{where}: {r['mapped_unit']!r} is not a unit of {mid}")
        if r["superseded_by"]:
            bad.append(f"{where}: a superseded rate cannot be mapped")
        if "at_quarry" in r["basis"]:
            bad.append(f"{where}: a price at the quarry is not a delivered price")
        if mid in mapped:
            bad.append(f"{where}: {mid} already mapped by row {mapped[mid]}")
        mapped[mid] = r["row"]
    return bad


def build(book: str, rows: list[dict]) -> dict:
    meta = BOOKS[book]
    materials = {}
    for r in rows:
        if r["material_id"]:
            materials[r["material_id"]] = {
                "rate": float(r["rate"]), "unit": r["mapped_unit"],
                "basis": r["basis"].split(";"), "effective_from": r["effective_from"],
                "source": f"{r['source']} p.{r['pdf_page']} (printed {r['printed_page']}), "
                          f"item {r['sl_no']}: {r['item']}",
                "note": r["note"] or None}
    return {"state": meta["state"], "circle": meta["circle"], "districts": meta["districts"],
            "edition": meta["edition"], "gst": meta["gst"], "sources": meta["sources"],
            "status": "candidate: not read by the engine (see data/build_sor.py)",
            "materials": dict(sorted(materials.items())), "items": {},
            "rows": [{k: v for k, v in r.items() if v != ""} for r in rows]}


def main(books: list[str]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for book in books:
        rows = read(book)
        bad = check(book, rows)
        if bad:
            sys.exit("\n".join(bad))
        sor = build(book, rows)
        path = OUT / f"{book}.json"
        path.write_text(json.dumps(sor, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(f"{book}: {len(rows)} rows, mapped {', '.join(sor['materials'])} -> "
              f"{path.relative_to(ROOT)}")


if __name__ == "__main__":
    main(sys.argv[1:] or list(BOOKS))
