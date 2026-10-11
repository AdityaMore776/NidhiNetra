r"""Reference file the Inspection Planner reads (T061): India Post offices with map positions.

  apps/engine/drishti/reference/post_offices.json.gz
      census district code (what works carry in `district_lgd`) ->
          {"name": outline name, "hq": [lat, lon, place] (the district's head office, else the
           outline's centre, place None), "offices": [[name, lat, lon], ...]}

Source: India Post's office directory with map positions, as packaged by `indiapins` on PyPI
(MIT). Each office is placed in a district by its POSITION inside the LGD outlines
(reference/district_outlines.json), never by joining names or codes. An office whose India
Post district name disagrees with the outline it falls in is kept only when its own state
agrees (districts split since the directory was made); the build prints both counts.

Run (the wheel or its pins.json.bz2, downloaded once with `pip download indiapins --no-deps`):
  apps\engine\.venv\Scripts\python.exe data\build_post_offices.py <indiapins-*.whl | pins.json.bz2>
"""

from __future__ import annotations

import bz2
import difflib
import gzip
import json
import re
import sys
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

from shapely.geometry import Point, shape
from shapely.strtree import STRtree

ROOT = Path(__file__).resolve().parents[1]
REF = ROOT / "apps" / "engine" / "drishti" / "reference"
OUT = REF / "post_offices.json.gz"
SHARED = 3          # offices on one exact position: from here on it is an area, not a village

# "Kothimir B.O", "Karur H.O", "Anand Bazar S.O", "Mumbai G.P.O", "X Sub Office"
SUFFIX = re.compile(r"\s+(?:b\.?\s*o|s\.?\s*o|h\.?\s*o|g\.?\s*p\.?\s*o|e\.?\s*d\.?\s*s\.?\s*o"
                    r"|sub\s+office|branch\s+office|head\s+office|mdg|ndg)\.?\s*$", re.I)


def office_name(raw: str) -> str:
    name = SUFFIX.sub("", raw.strip())
    name = re.sub(r"[^a-z ]+", " ", name.lower())
    return re.sub(r"\s+", " ", name).strip()


def _letters(s: str) -> str:
    return re.sub(r"[^a-z]", "", (s or "").lower())


def same_name(a: str, b: str) -> bool:
    a, b = _letters(a), _letters(b)
    if not a or not b:
        return False
    return a in b or b in a or difflib.SequenceMatcher(None, a, b).ratio() >= 0.8


def read_rows(src: Path) -> list[dict]:
    if src.suffix == ".whl":
        with zipfile.ZipFile(src) as z:
            name = next(n for n in z.namelist() if n.endswith("pins.json.bz2"))
            raw = bz2.decompress(z.read(name))
    else:
        raw = bz2.decompress(src.read_bytes())
    return [json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()]


def main(src: Path) -> None:
    outlines = json.loads((REF / "district_outlines.json").read_text(encoding="utf-8"))
    codes = list(outlines)
    shapes = [shape(outlines[c]["geometry"]) for c in codes]
    tree = STRtree(shapes)
    # the state each outline sits in, by majority of the offices inside it (filled below)
    rows = read_rows(src)
    placed: list[tuple[str, dict]] = []
    no_pos = outside = 0
    for r in rows:
        lat, lon = r.get("Latitude"), r.get("Longitude")
        if not isinstance(lat, float) or not isinstance(lon, float):
            no_pos += 1
            continue
        pt = Point(lon, lat)
        hit = [i for i in tree.query(pt) if shapes[i].contains(pt)]
        if not hit:
            outside += 1
            continue
        placed.append((codes[hit[0]], r))

    state_votes: dict[str, Counter] = defaultdict(Counter)
    for code, r in placed:
        state_votes[code][_letters(r.get("State"))] += 1
    state_of = {c: v.most_common(1)[0][0] for c, v in state_votes.items()}

    out: dict[str, dict] = {}
    agree = split_kept = dropped = 0
    heads: dict[str, list] = defaultdict(list)
    for code, r in placed:
        if same_name(r.get("District"), outlines[code]["name"]):
            agree += 1
        elif _letters(r.get("State")) == state_of[code]:
            split_kept += 1          # same state, district name differs: a newer district split
        else:
            dropped += 1             # another state's office: its position is not to be trusted
            continue
        name = office_name(r.get("Name", ""))
        if len(name) < 3:
            continue
        lat, lon = round(r["Latitude"], 5), round(r["Longitude"], 5)
        d = out.setdefault(code, {"name": outlines[code]["name"], "hq": None, "offices": []})
        d["offices"].append([name, lat, lon])
        if r.get("BranchType") == "HO":
            heads[code].append([lat, lon, name])

    pos_count = Counter((o[1], o[2]) for d in out.values() for o in d["offices"])
    hq_kinds = Counter()
    for code in codes:
        d = out.setdefault(code, {"name": outlines[code]["name"], "hq": None, "offices": []})
        d["offices"] = sorted({tuple(o) for o in d["offices"]})
        d["offices"] = [[n, la, lo, int(pos_count[(la, lo)] >= SHARED)] for n, la, lo in d["offices"]]
        named = [h for h in heads.get(code, []) if same_name(h[2], d["name"])]
        if named:
            d["hq"] = named[0]
            hq_kinds["head office named like the district"] += 1
        else:
            p = shapes[codes.index(code)].representative_point()
            d["hq"] = [round(p.y, 5), round(p.x, 5), None]
            hq_kinds["outline centre"] += 1

    blob = json.dumps(out, separators=(",", ":"), sort_keys=True).encode("utf-8")
    OUT.write_bytes(gzip.compress(blob, compresslevel=9, mtime=0))
    kept = sum(len(d["offices"]) for d in out.values())
    with_offices = sum(1 for d in out.values() if d["offices"])
    shared = sum(o[3] for d in out.values() for o in d["offices"])
    print(f"offices in the directory        {len(rows):,}")
    print(f"  no map position               {no_pos:,}")
    print(f"  position outside every outline {outside:,}")
    print(f"  inside, district name agrees  {agree:,}")
    print(f"  inside, same state, name differs (kept: newer districts) {split_kept:,}")
    print(f"  inside another state's outline (dropped) {dropped:,}")
    print(f"kept (distinct name + position) {kept:,} in {with_offices} of {len(codes)} districts")
    print(f"  on a position shared by {SHARED}+ offices (an area, not a village) {shared:,}")
    for k, v in hq_kinds.items():
        print(f"district start point: {k:40s} {v}")
    print(f"wrote {OUT.relative_to(ROOT)} ({OUT.stat().st_size / 1e6:.2f} MB)")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(Path(sys.argv[1]))
