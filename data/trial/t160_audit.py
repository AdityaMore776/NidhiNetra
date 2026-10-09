r"""T160: the agents audit (9 Oct 2026). Ways an agency could move a work past Duplicate Work,
replayed through the engine itself on made-up works (an earlier community hall, completed, and a
new work filed near it).

    1. the map pin typed some metres off the real site, with and without site videos filmed at
       the real site (the hall): which check asks, by how far the pin is off
    2. the same building filed under another work type

    apps\engine\.venv\Scripts\python.exe data\trial\t160_audit.py

Writes data/trial/results/t160_audit.txt.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "apps" / "engine"))

from drishti.agents.dup_split.agent import assess
from drishti.agents.dup_split.repeat import RepeatIndex

LAT, LON = 25.7500, 82.6900
DEG = 1 / 111_195            # one metre of latitude, in degrees
OUT = ROOT / "data" / "trial" / "results" / "t160_audit.txt"


def _w(work_id, desc, wtype="COMMUNITY_HALL", status="SANCTIONED", rec=date(2025, 1, 5),
       done=None, north=0.0):
    return {"work_id": work_id, "description": desc, "amount": 480_000.0,
            "recommended_date": rec, "completed_date": done, "sanction_date": None,
            "mp_name": "MP A", "work_type_code": wtype, "status": status, "district_lgd": "639",
            "cost_form": {"work": {"work_type": wtype, "nature": "new"},
                          "sites": [{"location": {"lat": LAT + north * DEG, "lon": LON}}]}}


def _filler():
    return [_w(f"F{i}", f"Construction of drain at Gaonpur{i} ward", wtype="DRAIN",
               rec=date(2023, 1, 1 + i), north=5000 + 300 * i) for i in range(12)]


def _visit(i, north):
    return {"visit_id": f"v{i}", "kind": "baseline" if i == 0 else "monthly",
            "captured_at": date(2025, 3 + i, 1), "claim": "walls up to lintel",
            "readings": {"sealed": True, "in_app": True, "motion_consistent": True,
                         "views_match_site": True, "gps_weak": False, "mock_location": False,
                         "gps_point": {"lat": LAT + north * DEG, "lon": LON}}}


OLD = _w("OLD", "Construction of community hall at Sirpur", status="COMPLETED",
         rec=date(2023, 3, 1), done=date(2024, 2, 1))


def run(new):
    r = assess(new, RepeatIndex.build(_filler() + [OLD, new]))
    asked = [f.code for f in r.findings if f.risk > 0]
    notes = [f.code for f in r.findings if f.risk == 0 and f.code != "LOOKS_LIKE_SANCTIONED_WORK"]
    return ", ".join(asked) or "-", ", ".join(notes) or "-"


def main() -> None:
    lines = [("T160: the agents audit, replayed through Duplicate Work (made-up works: an earlier "
              "community hall, completed, and a new work filed near it)"), "",
             ("1. The map pin typed some metres off the real site (the hall). 'videos' = three "
              "site videos filmed at the hall (within 8 m of its pin)."), "",
             f"{'pin off by':>10s}  {'videos':6s}  {'asked':34s}  notes"]
    for off in (0, 30, 49, 51, 60, 75, 90, 120, 150, 400):
        for filmed in (False, True):
            new = _w("NEW", "Construction of community hall at Sirpur", north=off)
            new["site_visits"] = [_visit(i, n) for i, n in enumerate((5, 8, 3))] if filmed else []
            asked, notes = run(new)
            lines.append(f"{off:>8d} m  {'yes' if filmed else 'no':6s}  {asked:34s}  {notes}")
    lines += ["", ("2. The same building, its pin 10 m from the hall's, filed under another work "
                   "type."), "", f"{'work type':18s}  {'asked':34s}  notes"]
    for wt in ("COMMUNITY_HALL", "SCHOOL_BUILDING", "LIBRARY", "OTHER"):
        asked, notes = run(_w("NEW", "Construction of multipurpose building at Sirpur",
                              wtype=wt, north=10))
        lines.append(f"{wt:18s}  {asked:34s}  {notes}")
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
