r"""District and state outlines for the maps, from the Local Government Directory (LGD).

Source: yashveeeeeeer/india-geodata releases admin/districts and admin/states
(LGD_Districts.parquet, LGD_States.parquet; CC0-1.0 / CC-BY-4.0). LGD is the
Government of India's own directory, so the national outline is the official
one - the maps draw no third-party borders.

Writes simplified GeoJSON for the web app:
  apps/web/public/geo/districts.json   (feature property: lgd, name, state)
  apps/web/public/geo/states.json

Run: apps\engine\.venv\Scripts\python.exe data\boundaries.py
Then: data\district_crosswalk.py - it adds the works' district code ("code") to each outline.
The `lgd` property here is the real LGD code; the works' "district_lgd" is the Census-2011
code, so the two must never be joined by number.
"""

from __future__ import annotations

import json
from pathlib import Path

import geopandas as gpd
import pandas as pd

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw" / "geo"
OUT = HERE.parent / "apps" / "web" / "public" / "geo"
TOLERANCE_DEG = 0.012      # ~1.3 km; enough for a national/state map, small enough to ship


def _write(gdf: gpd.GeoDataFrame, path: Path) -> None:
    gdf = gdf.copy()
    gdf["geometry"] = gdf.geometry.simplify(TOLERANCE_DEG, preserve_topology=True)
    data = json.loads(gdf.to_json(drop_id=True))
    for f in data["features"]:          # 4 decimals ~ 11 m, halves the file
        f["geometry"] = json.loads(json.dumps(f["geometry"]),
                                   parse_float=lambda s: round(float(s), 4))
    path.write_text(json.dumps(data, separators=(",", ":")), encoding="utf-8")
    print(f"{path.name}: {len(gdf)} features, {path.stat().st_size / 1e6:.1f} MB")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    d = gpd.read_parquet(RAW / "LGD_Districts.parquet").to_crs(4326)
    d["lgd"] = d["dist_lgd"].astype(int).astype(str).str.zfill(3)
    works = pd.read_parquet(HERE / "build" / "districts.parquet")
    have = set(works.district_lgd)
    matched = have & set(d.lgd)
    print(f"works' districts with an LGD outline: {len(matched)} of {len(have)}")
    _write(d[["lgd", "dtname", "stname", "geometry"]].rename(
        columns={"dtname": "name", "stname": "state"}), OUT / "districts.json")
    s = gpd.read_parquet(RAW / "LGD_States.parquet").to_crs(4326)
    _write(s[["STNAME", "geometry"]].rename(columns={"STNAME": "name"}), OUT / "states.json")


if __name__ == "__main__":
    main()
