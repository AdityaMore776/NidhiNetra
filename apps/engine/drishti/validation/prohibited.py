"""Does a description read as one of the works MPLADS prohibits (Annexure-II)?

MEASURED BEFORE BUILT (2026-09-25, on the 209,993 real works)

    Plain keyword presence is useless here. "temple" and "mandir" alone occur
    in ~17,000 descriptions, nearly all of them landmarks ("CC road near
    Maruteshwar temple") or school names ("Vidya Mandir"). So a keyword counts
    only when it is the OBJECT of the work - "<verb> of [up to three words]
    <keyword>" with no landmark preposition in between. That cut the matches to
    ~640.

    Reading those 640 showed they are still mostly legitimate: ration (PDS)
    shops, roads leading to a temple, road repairs. So a match is an INFO note
    for the officer to read against Annexure-II, with a small soft weight. It
    can never put a work in the review queue on its own.

Items marked superseded_likely in the reference file are never checked: the
scheme's own live category list now funds them.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache

from drishti import reference

VERB = (r"(?:construction|constructing|construct|c/o|installation|installing|renovation|"
        r"repair(?:s|ing)?|erection|development|beautification|nirman|purchase|supply|"
        r"providing|provision|maintenance|improvement)")
LANDMARK = re.compile(r"\b(?:near|from|to|till|upto|up to|towards|in front of|infront of|"
                      r"behind|opposite|beside|around|at|in|of|ke|se|tak|pas|samne)\b", re.I)


@dataclass(frozen=True)
class ProhibitedMatch:
    item_id: str
    annexure_item: str
    keyword: str
    text: str
    exceptions: tuple[str, ...]


@lru_cache(maxsize=1)
def _patterns() -> list[tuple[dict, str, re.Pattern]]:
    out = []
    for item in reference.prohibited_items():
        if item.get("superseded_likely"):
            continue
        for kw in item.get("keywords") or []:
            rx = re.compile(
                rf"\b{VERB}\b(?:\s+work)?\s+(?:of|for)?\s*(?:the\s+|a\s+|new\s+)?"
                rf"((?:[\w.'-]+\s+){{0,3}}?){re.escape(kw)}\b", re.I)
            out.append((item, kw, rx))
    return out


def match(description: str | None) -> ProhibitedMatch | None:
    text = description or ""
    for item, kw, rx in _patterns():
        m = rx.search(text)
        if m and not LANDMARK.search(m.group(1) or ""):
            return ProhibitedMatch(
                item_id=item["id"], annexure_item=str(item.get("annexure_ii_2016_item", "")),
                keyword=kw, text=" ".join(item["text"].split()),
                exceptions=tuple(" ".join(e.split()) for e in item.get("exceptions") or ()))
    return None
