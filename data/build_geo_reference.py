r"""Reference file the Photo Evidence engine reads (T310): district outlines.

  apps/engine/drishti/reference/district_outlines.json
      census district code (what works carry in `district_lgd`) -> {lgd, name, geometry},
      from apps/web/public/geo/districts.json (LGD outlines; `code` added by
      data/district_crosswalk.py)

Run: apps\engine\.venv\Scripts\python.exe data\build_geo_reference.py
"""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REF = ROOT / "apps" / "engine" / "drishti" / "reference"
GEO = ROOT / "apps" / "web" / "public" / "geo" / "districts.json"


def main() -> None:
    feats = json.loads(GEO.read_text(encoding="utf-8"))["features"]
    out = {}
    for f in feats:
        p = f["properties"]
        if p.get("code"):
            out[str(p["code"])] = {"lgd": str(p["lgd"]), "name": p["name"],
                                   "geometry": f["geometry"]}
    (REF / "district_outlines.json").write_text(json.dumps(out, separators=(",", ":")),
                                               encoding="utf-8")
    print(f"{len(out)} district outlines")


if __name__ == "__main__":
    main()
