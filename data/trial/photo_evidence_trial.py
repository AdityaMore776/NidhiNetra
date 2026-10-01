r"""Photo Evidence engine (T310) on the real pilot: does it reproduce FINDINGS B2 / B3?

Targets (results/photo_trial.json, geo_trial.json):
  B3  190 stamped photos/pages on 170 works; 187 points inside the work's own district, 2 within
      5 km of its border, 0 further; 3 works whose own photos predate the recommendation
      (Sabar Kantha WS/.../7171, Chittaurgarh 124508 and 124252); PIN agrees 66, disagrees 3;
      one spot-and-day shared by two works
  B2  5 groups of works carrying a byte-identical file: the 2 read as "needs checking" (one road
      photo on two Pratapgarh roads; one Hindi completion certificate on two Narmadapuram works)
      flagged, the 3 combined files (Neemuch invoice, Betul certificate list, Anantnag contractor
      file) not; no edited copies in the pilot

Uses the engine's own readers and checks (agents/photo_evidence) on data/build_evidence.py's
facts. Writes results/photo_evidence_trial.json.
Run: apps\engine\.venv\Scripts\python.exe data\trial\photo_evidence_trial.py
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
from drishti.agents.photo_evidence import geo  # noqa: E402
from drishti.agents.photo_evidence.agent import assess  # noqa: E402
from drishti.agents.photo_evidence.index import PhotoIndex  # noqa: E402

OUT = ROOT / "data" / "trial" / "results"
AS_OF = date(2026, 9, 26)          # the evidence was downloaded 25-26 Sept 2026
NEEDS_CHECKING = {"WS/MP807/2023-2024/32921", "WS/MP807/2023-2024/32924",
                  "WS/MP18104/2025-2026/152189", "WS/MP18104/2025-2026/154228"}
COMBINED = {"WS/MP356/2023-2024/95025", "WS/MP356/2023-2024/95039", "WS/MP356/2023-2024/95050",
            "WS/MP444/2024-2025/146209", "WS/MP444/2024-2025/146217",
            "WS/MP602/2023-2024/72625", "WS/MP602/2023-2024/75517"}


def main() -> None:
    ev = pd.read_parquet(BUILD / "evidence_facts.parquet")
    facts = {r.work_id: json.loads(r.data) for r in ev.itertuples()}
    w = pd.read_parquet(BUILD / "works.parquet")
    works = [clean(r) | {"evidence": facts[r["work_id"]]}
             for r in w[w.work_id.isin(facts)].to_dict("records")]
    photos = PhotoIndex.build(works)
    results = {x["work_id"]: assess(x, AS_OF, photos) for x in works}

    inside = border = far = 0
    for x in works:
        o = geo.outlines().get(str(x.get("district_lgd") or "").zfill(3))
        for f in x["evidence"]["files"]:
            for s in f.get("stamps") or []:
                if o is None:
                    continue
                km = geo.km_outside(o["geometry"], s["lat"], s["lon"])
                inside += km == 0
                border += 0 < km <= geo.BORDER_KM
                far += km > geo.BORDER_KM
    codes = Counter(f.code for r in results.values() for f in r.findings)
    flagged = lambda code: sorted(wid for wid, r in results.items()  # noqa: E731
                                  if code in {f.code for f in r.findings})
    reuse = set(flagged("SAME_PHOTO_ON_ANOTHER_WORK")) | set(flagged("SAME_FILE_ON_ANOTHER_WORK"))
    res = {"works_with_files": len(works),
           "stamps": sum(len(f.get("stamps") or []) for x in works for f in x["evidence"]["files"]),
           "works_with_stamps": sum(1 for x in works
                                    if any(f.get("stamps") for f in x["evidence"]["files"])),
           "place": {"inside_own_district": inside, "within_5km_of_border": border,
                     "further_outside": far},
           "photo_before_recommendation": flagged("PHOTO_BEFORE_RECOMMENDATION"),
           "reuse_flagged": sorted(reuse),
           "reuse_check": {"needs_checking_flagged": len(NEEDS_CHECKING & reuse),
                           "needs_checking_total": len(NEEDS_CHECKING),
                           "combined_files_flagged": len(COMBINED & reuse),
                           "combined_files_total": len(COMBINED)},
           "engine": {"status": dict(Counter(r.status.value for r in results.values())),
                      "findings": dict(codes)}}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "photo_evidence_trial.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
