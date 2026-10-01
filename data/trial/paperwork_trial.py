r"""Paperwork engine (T110) on the real pilot evidence: does it reproduce FINDINGS B4 / C3?

Targets from data/trial/document_trial.py (results/document_trial.json): 431 certificates;
fields read: amount 99.8%, status 99.8%, vendor code 97.7%, sanction date 69.4%; 211 works with a
sanction date, 33 past 75 days (raw calendar), 1 sanctioned before recommended; 282 of 285
completed works whose own certificates all say "in progress"; 2 of 429 certification pages with
a box marked; Pratapgarh 261 works, 7 vendors, top 39%, top three 84%.

The engine's own reader and checks are used (agents/paperwork), on the facts written by
data/build_evidence.py. Writes results/paperwork_trial.json.
Run: apps\engine\.venv\Scripts\python.exe data\trial\paperwork_trial.py
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import date
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "data"))
from common import BUILD, clean  # noqa: E402
from drishti.agents.paperwork.agent import assess, own_certificates  # noqa: E402
from drishti.agents.paperwork.vendors import VendorIndex  # noqa: E402

OUT = ROOT / "data" / "trial" / "results"


def main() -> None:
    ev = pd.read_parquet(BUILD / "evidence_facts.parquet")
    facts = {r.work_id: json.loads(r.data) for r in ev.itertuples()}
    w = pd.read_parquet(BUILD / "works.parquet")
    works = [clean(r) | {"evidence": facts[r["work_id"]]}
             for r in w[w.work_id.isin(facts)].to_dict("records")]
    vendors = VendorIndex.build(works)

    certs = [c for x in works for f in x["evidence"]["files"] for c in f["certificates"]]
    share = {k: round(sum(1 for c in certs if c.get(k) not in (None, [])) / len(certs), 3)
             for k in ("sanction_date", "sanctioned_amount", "status", "payments",
                       "vendor_code", "location")}
    multi = sum(1 for c in certs if len(c.get("payments") or []) > 1)

    late_raw, before, n_dated, in_prog, completed_own = 0, 0, 0, 0, 0
    for x in works:
        own = own_certificates([c for f in x["evidence"]["files"] for c in f["certificates"]], x)
        dates = sorted(date.fromisoformat(c["sanction_date"]) for c in own if c.get("sanction_date"))
        rec = x.get("recommended_date")
        if dates and rec:
            n_dated += 1
            days = (dates[0] - rec).days
            late_raw += days > 75
            before += days < 0
        st = [c.get("status") for c in own if c.get("status")]
        if x.get("status") == "COMPLETED" and st:
            completed_own += 1
            in_prog += all(s == "inprogress" for s in st)
    cert_pages = [p for x in works for f in x["evidence"]["files"]
                  for p in f["certification_pages"]]

    results = [assess(x, vendors) for x in works]
    status = Counter(r.status.value for r in results)
    codes = Counter(f.code for r in results for f in r.findings)
    verdicts = Counter(r.verdict for r in results if r.status.value == "ASSESSED")
    prat = next((d for d in {str(x.get("district_lgd")) for x in works
                             if str(x.get("district_name") or "").upper() == "PRATAPGARH"}), None)
    res = {"works_with_files": len(works), "certificates": len(certs),
           "fields_read_share": share, "certificates_with_several_payments": multi,
           "sanction_delay": {"works_with_a_sanction_date": n_dated,
                              "past_75_days_raw_calendar": late_raw,
                              "sanctioned_before_recommended": before},
           "status": {"completed_works_with_own_certificate": completed_own,
                      "all_own_certificates_say_in_progress": in_prog},
           "certification_pages": len(cert_pages),
           "certification_pages_with_a_box_marked": sum(1 for p in cert_pages
                                                        if p.get("boxes_marked")),
           "pratapgarh_vendors": vendors.summary(prat) if prat else None,
           "engine": {"status": dict(status), "verdicts": dict(verdicts),
                      "findings": dict(codes)},
           "targets_from_document_trial": {
               "certificates": 431, "sanction_date_share": 0.694, "vendor_code_share": 0.977,
               "works_with_a_sanction_date": 211, "past_75_days": 33, "before": 1,
               "in_progress": "282 of 285", "boxes_marked": "2 of 429",
               "pratapgarh": "261 works, 7 vendors, top 0.391, top3 0.839"}}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "paperwork_trial.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
