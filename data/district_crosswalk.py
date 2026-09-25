r"""Crosswalk between the two district code systems DRISHTI touches.

  works / cohorts / PIN file : "district_lgd" is really the Census-2011 district code
                               (Kupwara 001, Badgam 002, ... New Delhi 094, Pratapgarh UP 173)
  map outlines (districts.json): the official LGD district code
                               (Anantnag 1, Budgam 2, ... Pilibhit 173, Pratapgarh UP 174)

Joining one to the other by number paints the wrong district. This file matches them by
state + district name (spelling variants and renamed districts handled), writes
data/build/district_crosswalk.parquet, and adds a "code" property (the works' code) to every
outline in districts.json, which is what the web map joins on. Outlines of districts created
after 2011 get no code and draw as "no works recorded".

Run after data/boundaries.py (which rewrites districts.json):
      .venv-trial\Scripts\python.exe data\district_crosswalk.py
"""

from __future__ import annotations

import difflib
import json
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "data" / "build"
GEO = ROOT / "apps" / "web" / "public" / "geo" / "districts.json"

# Names that refer to the same district (renamed, respelt, or with/without a prefix)
SAME = [
    {"prayagraj", "allahabad"}, {"ayodhya", "faizabad"}, {"gurugram", "gurgaon"}, {"nuh", "mewat"},
    {"bhadohi", "sant ravidas nagar bhadohi", "sant ravidas nagar"}, {"kasganj", "kanshiram nagar"},
    {"amroha", "jyotiba phule nagar"}, {"hathras", "mahamaya nagar"}, {"hapur", "panchsheel nagar"},
    {"shamli", "prabuddh nagar"}, {"maharajganj", "mahrajganj"}, {"kheri", "lakhimpur kheri"},
    {"narmadapuram", "hoshangabad"}, {"khandwa", "east nimar"}, {"khargone", "west nimar"},
    {"chhatrapati sambhaji nagar", "chhatrapati sambhajinagar", "aurangabad"},
    {"dharashiv", "osmanabad"}, {"ahilyanagar", "ahmednagar", "ahmadnagar"},
    {"bengaluru urban", "bangalore urban", "bangalore"}, {"bengaluru rural", "bangalore rural"},
    {"kalaburagi", "gulbarga"}, {"belagavi", "belgaum"}, {"vijayapura", "bijapur"}, {"shivamogga", "shimoga"},
    {"tumakuru", "tumkur"}, {"chikkamagaluru", "chikmagalur"}, {"mysuru", "mysore"}, {"ballari", "bellary"},
    {"hooghly", "hugli"}, {"howrah", "haora"}, {"darjeeling", "darjiling"}, {"cooch behar", "koch bihar"},
    {"purulia", "puruliya"}, {"malda", "maldah"}, {"budgam", "badgam"}, {"poonch", "punch"},
    {"rajouri", "rajauri"}, {"baramulla", "baramula"}, {"bandipora", "bandipura"}, {"shopian", "shupiyan"},
    {"leh ladakh", "leh"}, {"ysr", "y s r", "ysr kadapa", "kadapa", "cuddapah"},
    {"spsr nellore", "sri potti sriramulu nellore", "nellore"}, {"ranga reddy", "rangareddy"},
    {"s a s nagar", "sas nagar", "sahibzada ajit singh nagar"}, {"ferozepur", "firozpur"},
    {"sri muktsar sahib", "muktsar"}, {"rayagada", "rayagarha"}, {"sribhumi", "karimganj"},
    {"thoothukudi", "tuticorin"}, {"dantewada", "dakshin bastar dantewara", "south bastar dantewada"},
    {"kanker", "uttar bastar kanker", "north bastar kanker"}, {"dohad", "dahod"},
    {"konaseema", "dr b r ambedkar konaseema", "b r ambedkar konaseema"},
    {"baleshwar", "balasore"}, {"sonepur", "subarnapur"}, {"kamrup", "kamrup rural"},
    {"south salmara mancachar", "south salmara"}, {"kumuram bheem asifabad", "kumuram bheem"},
    {"pondicherry", "puducherry"}, {"kabirdham", "kawardha"}, {"kendujhar", "keonjhar"},
    {"anantapur", "ananthapuramu"}, {"nuapada", "nuaparha"}, {"reasi", "riasi"}, {"dholpur", "dhaulpur"},
    {"narsinghpur", "narsimhapur"}, {"sivasagar", "sibsagar"},
]
DIRECTION = {"paschim": "west", "purba": "east", "purbi": "east", "uttar": "north", "dakshin": "south",
             "paraganas": "parganas", "twenty": "", "four": "24"}


def norm(s: str) -> str:
    s = (s or "").lower().replace("&", " and ")
    s = re.sub(r"\b(district|dist)\b", " ", s)
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def squash(s: str) -> str:
    return norm(s).replace(" ", "").replace("and", "")


def tokens(s: str) -> frozenset:
    return frozenset(t for t in (DIRECTION.get(w, w) for w in norm(s).split()) if t and t != "and")


def variants(name: str) -> set[str]:
    """The name, the parts inside/outside brackets, and every known equivalent."""
    out = {norm(name)}
    m = re.match(r"^(.*?)\((.*?)\)\s*$", name or "")
    if m:
        out |= {norm(m.group(1)), norm(m.group(2))}
    for v in list(out):
        for group in SAME:
            if v in group:
                out |= group
    return {v for v in out if v}


def score(a: str, b: str) -> float:
    best = 0.0
    for va in variants(a):
        for vb in variants(b):
            if squash(va) == squash(vb) or tokens(va) == tokens(vb):
                return 1.0
            best = max(best, difflib.SequenceMatcher(None, squash(va), squash(vb)).ratio())
    return best


def state_key(s: str) -> str:
    s = norm(s)
    if "dadra" in s or "daman" in s:
        return "dnhdd"
    if "andaman" in s:
        return "andaman"
    if "jammu" in s:
        return "jammukashmir"
    return {"nct of delhi": "delhi"}.get(s, s).replace(" ", "").replace("and", "")


def main() -> None:
    b = pd.read_parquet(BUILD / "districts.parquet")
    g = pd.DataFrame([f["properties"] for f in json.loads(GEO.read_text(encoding="utf-8"))["features"]])
    b["sk"], g["sk"] = b.state_name.map(state_key), g.state.map(state_key)
    rows = []
    for x in b.itertuples():
        cand = g[g.sk == x.sk]
        best, top = None, 0.0
        for y in cand.itertuples():
            sc = score(x.name, y.name)
            if sc > top:
                best, top = y, sc
        rows.append({"census_code": x.district_lgd, "lgd_code": best.lgd if best is not None and top >= 0.85 else None,
                     "name": x.name, "state": x.state_name, "lgd_name": best.name if best is not None else None,
                     "score": round(top, 3)})
    cw = pd.DataFrame(rows)
    cw.to_parquet(BUILD / "district_crosswalk.parquet", index=False)
    ok = cw.lgd_code.notna()
    if cw[ok].lgd_code.duplicated().any():
        raise SystemExit("two census districts matched one outline - fix SAME before writing the map")

    geo = json.loads(GEO.read_text(encoding="utf-8"))
    code_of = {r.lgd_code: r.census_code for r in cw[ok].itertuples()}
    for f in geo["features"]:
        f["properties"]["code"] = code_of.get(f["properties"]["lgd"])
    GEO.write_text(json.dumps(geo, separators=(",", ":")), encoding="utf-8")
    print(f"districts.json: {sum(1 for f in geo['features'] if f['properties']['code'])} of "
          f"{len(geo['features'])} outlines carry a works code")
    print(f"matched {int(ok.sum())} of {len(cw)}; exact {int((cw.score == 1).sum())}")
    print(cw[~ok | (cw.score < 0.93)].sort_values("score").to_string(max_rows=80))
    dup = cw[ok].lgd_code.value_counts()
    print("LGD codes used twice:", cw[cw.lgd_code.isin(dup[dup > 1].index)].to_string())


if __name__ == "__main__":
    main()
