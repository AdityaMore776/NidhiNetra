r"""Reference files the Photo Evidence engine reads (T310): district outlines and PIN -> district.

  apps/engine/drishti/reference/district_outlines.json
      census district code (what works carry in `district_lgd`) -> {lgd, name, geometry},
      from apps/web/public/geo/districts.json (LGD outlines; `code` added by
      data/district_crosswalk.py)
  apps/engine/drishti/reference/pin_district.json
      India Post PIN -> LGD district code (the public India Post / LGD mapping)

Run: apps\engine\.venv\Scripts\python.exe data\build_geo_reference.py
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
REF = ROOT / "apps" / "engine" / "drishti" / "reference"
GEO = ROOT / "apps" / "web" / "public" / "geo" / "districts.json"
PINS = Path.home() / "saakshya" / "data" / "raw" / "lgd" / "india-postal-lgd-mapping.csv"


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
    pins = pd.read_csv(PINS, dtype=str).dropna(subset=["district_lgd"]).drop_duplicates("pincode")
    pin = {r.pincode: str(int(r.district_lgd)) for r in pins.itertuples()}
    (REF / "pin_district.json").write_text(json.dumps(pin, separators=(",", ":")),
                                          encoding="utf-8")
    print(f"{len(out)} district outlines, {len(pin):,} PINs")


if __name__ == "__main__":
    main()
