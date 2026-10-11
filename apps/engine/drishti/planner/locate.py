"""Where is a work? Its description's place names, matched to India Post offices (T061).

eSAKSHI records only a work's district. Its description usually names the village ("...on GHSS
Rachandar Thirumalai Village at Thokaimalai Panchayat"). The reference file
reference/post_offices.json.gz (data/build_post_offices.py) holds every India Post office with
a map position, placed in a district by that position inside the LGD outlines, keyed by the
census district code works carry. A work is matched only against its OWN district's offices.

Precision, always shown with the stop:
  village   a named office with its own position (positions in the directory are approximate)
  area      a named office whose position 3+ offices share (a branch given its parent's place)
  block     a named office next to a block word ("Taluk Ankola", "Pendlimarri (M)"): the work is
            somewhere in that taluka / mandal, not at the town itself
  district  nothing matched: the district's start point (its head office, else the outline's
            centre); a rough place, never a finding

Rules (tests/planner/test_locate.py): whole words only (a name written as two words matches a
one-word office); never a generic word, a name under 4 letters or the district's own name; a
name held by offices more than 5 km apart is ambiguous and never used; a name beside a district
word ("of Nellore District", "Dist. Ahmedabad") is the district written another way and never
used; of several names, one
next to a place word ("village", "at", "panchayat"...) wins, then one with no word beside it,
then one next to a block word; the first written breaks a tie.
"""

from __future__ import annotations

import gzip
import json
import math
import re
from dataclasses import dataclass
from functools import cache
from pathlib import Path

from drishti import reference

REF = Path(reference.__file__).resolve().parent
MAX_WORDS = 4                 # longest office name read, in words
MIN_LETTERS = 4
SPREAD_KM = 5.0               # one name, offices further apart than this: ambiguous
CUES = frozenset({"at", "in", "near", "village", "vill", "vil", "gram", "gaon", "panchayat",
                  "gp", "po", "mouza", "mauza", "ward", "v", "h"})       # (V) village, (H) hamlet
# a block word written before its name ("Tal. Gadhinglaj", "Taluka.purna") or after it
# ("Lingasugur Taluk", "Pendlimarri (M)"); "Tal"/"Tq" only ever come before
BLOCK_BEFORE = frozenset({"taluk", "taluka", "tal", "tq", "tehsil", "tahsil", "mandal", "block"})
BLOCK_AFTER = frozenset({"taluk", "taluka", "tehsil", "tahsil", "mandal", "m", "block",
                         "mandalam"})
# "of Nellore District", "Dist. Ahmedabad", "Sangareddy (D)": the district, written another way
DISTRICT_WORDS = frozenset({"district", "dist", "dt", "d", "zilla", "jilla", "zila", "jila"})
WORD = re.compile(r"[a-z]+")


@dataclass(frozen=True)
class Location:
    lat: float
    lon: float
    precision: str            # village | area | block | district
    place: str | None         # the matched office name; None at the district start


@dataclass(frozen=True)
class Match:
    place: str
    lat: float
    lon: float
    precision: str            # village | area | block


def km(a_lat: float, a_lon: float, b_lat: float, b_lon: float) -> float:
    """Great-circle distance in km."""
    p1, p2 = math.radians(a_lat), math.radians(b_lat)
    dp, dl = p2 - p1, math.radians(b_lon - a_lon)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * 6371.0 * math.asin(math.sqrt(min(1.0, h)))


def _key(name: str) -> str:
    return "".join(WORD.findall(name.lower()))


def index(offices: list[list]) -> dict[str, Match | None]:
    """Office rows [name, lat, lon, shared] -> joined name -> its place (None when ambiguous)."""
    groups: dict[str, list[list]] = {}
    for row in offices:
        groups.setdefault(_key(row[0]), []).append(row)
    out: dict[str, Match | None] = {}
    for key, rows in groups.items():
        first = rows[0]
        if any(km(first[1], first[2], r[1], r[2]) > SPREAD_KM for r in rows[1:]):
            out[key] = None
            continue
        shared = any(r[3] for r in rows)
        out[key] = Match(first[0], first[1], first[2], "area" if shared else "village")
    return out


def match(description: str | None, offices: dict[str, Match | None], *, district_name: str,
          generic: frozenset[str]) -> Match | None:
    """The work's place among its district's offices, or None."""
    words = WORD.findall((description or "").lower())
    own = _key(district_name)
    found: list[tuple[int, int, Match]] = []           # (rank: 0 place word, 1 none, 2 block)
    for i in range(len(words)):
        for n in range(MAX_WORDS, 0, -1):
            if i + n > len(words):
                continue
            key = "".join(words[i:i + n])
            if len(key) < MIN_LETTERS or key == own or key in generic:
                continue
            if n > 1 and all(w in generic for w in words[i:i + n]):
                continue
            hit = offices.get(key)
            if hit is None:
                continue
            before = words[i - 1] if i > 0 else ""
            after = words[i + n] if i + n < len(words) else ""
            if before in DISTRICT_WORDS or after in DISTRICT_WORDS:
                continue                              # the district itself, not a place in it
            beside = {before, after}
            if before in BLOCK_BEFORE or after in BLOCK_AFTER:
                hit = Match(hit.place, hit.lat, hit.lon, "block")
                rank = 2
            else:
                rank = 0 if beside & CUES else 1
            found.append((rank, i, hit))
            break                                     # the longest name starting here
    if not found:
        return None
    return min(found, key=lambda f: (f[0], f[1]))[2]


@cache
def _reference() -> dict[str, dict]:
    with gzip.open(REF / "post_offices.json.gz", "rt", encoding="utf-8") as f:
        return json.load(f)


@cache
def _district(code: str) -> tuple[str, dict[str, Match | None], Location] | None:
    d = _reference().get(code)
    if d is None:
        return None
    lat, lon, place = d["hq"]
    return d["name"], index(d["offices"]), Location(lat, lon, "district", place)


@cache
def _generic() -> frozenset[str]:
    text = (REF / "generic_words.txt").read_text(encoding="utf-8")
    return frozenset(w.strip() for w in text.splitlines() if w.strip() and not w.startswith("#"))


def district_start(code: str | None) -> Location | None:
    """Where a district's day starts and ends: its head office, else the outline's centre."""
    got = _district(code) if code else None
    return got[2] if got else None


def locate(code: str | None, description: str | None) -> Location | None:
    """A work's approximate place; None only when its district is unknown."""
    got = _district(code) if code else None
    if got is None:
        return None
    name, offices, start = got
    hit = match(description, offices, district_name=name, generic=_generic())
    if hit is None:
        return Location(start.lat, start.lon, "district", None)
    return Location(hit.lat, hit.lon, hit.precision, hit.place)
