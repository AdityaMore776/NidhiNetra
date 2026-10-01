r"""Evidence facts per work, read with the ENGINE's own readers (T110 Paperwork; T310 adds photos).

For every work in data/evidence/manifest.jsonl (the eSAKSHI pilot: 837 works), each attached
file's OCR pages (data/trial/cache/ocr/, written by data/trial/ocr_pages.py) go through
drishti.agents.paperwork.reader.read_file. Only derived facts are kept: page kinds, sanction
dates, amounts, payments, status, the vendor's CODE, the certificate's location line (it names
the site, as the public description does). Never kept: file bytes, OCR text, vendor names,
bank accounts, phone numbers.

The same reader runs on a new work's papers (live upload, field app): the job only saves the
batch path the time of reading 1,600 pages.

Writes data/build/evidence_facts.parquet (work_id, data JSON, version) -> table evidence_facts.
Run: apps\engine\.venv\Scripts\python.exe data\build_evidence.py
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "engine"))
from drishti.agents.paperwork.reader import read_file  # noqa: E402

EVID = ROOT / "data" / "evidence"
OCR = ROOT / "data" / "trial" / "cache" / "ocr"
BUILD = ROOT / "data" / "build"
VERSION = "evidence-1"


def _json(x):
    if isinstance(x, date):
        return x.isoformat()
    if isinstance(x, (list, tuple)):
        return [_json(v) for v in x]
    if isinstance(x, dict):
        return {k: _json(v) for k, v in x.items()}
    return x


def ocr_pages() -> dict[str, list[dict]]:
    pages: dict[str, list[dict]] = defaultdict(list)
    for p in sorted(OCR.glob("*.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        pages[Path(d["file"]).stem].append(d)
    return pages


def paper_facts(pages: list[dict]) -> dict:
    pdf = sorted((p for p in pages if p.get("kind") == "pdf_page"), key=lambda p: p["page"])
    if not pdf:
        return {"pages": 0, "kinds": [], "readable": False, "certificates": [],
                "certification_pages": []}
    r = read_file(pdf)
    keep = ("page", "sanction_date", "sanction_date_from", "sanctioned_amount", "status",
            "payments", "vendor_code", "location")
    return {"pages": len(pdf), "kinds": r["kinds"], "readable": r["readable"],
            "certificates": [{k: c.get(k) for k in keep if c.get(k) is not None}
                             for c in r["certificates"]],
            "certification_pages": r["certification_pages"]}


def main() -> None:
    pages = ocr_pages()
    rows = []
    for line in (EVID / "manifest.jsonl").read_text(encoding="utf-8").splitlines():
        rec = json.loads(line)
        files = []
        for f in rec["files"]:
            stem = Path(f["path"].replace("\\", "/")).stem
            ext = Path(f["path"]).suffix.lower().lstrip(".")
            facts = {"id": f["attach_id"], "ext": ext, "sha256": f["sha256"]}
            if ext == "pdf":
                facts |= paper_facts(pages.get(stem, []))
            else:
                facts |= {"pages": 0, "kinds": ["photo"], "readable": False,
                          "certificates": [], "certification_pages": []}
            files.append(facts)
        if files:
            rows.append({"work_id": rec["work_id"],
                         "data": json.dumps(_json({"files": files, "sample": rec["sample"]})),
                         "version": VERSION})
    out = pd.DataFrame(rows)
    out.to_parquet(BUILD / "evidence_facts.parquet", index=False)
    certs = sum(len(f["certificates"]) for r in rows for f in json.loads(r["data"])["files"])
    print(f"{len(out):,} works with files, {certs:,} certificates read -> "
          f"{BUILD / 'evidence_facts.parquet'}")


if __name__ == "__main__":
    main()
