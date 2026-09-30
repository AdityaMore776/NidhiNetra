"""Eligibility v2: does a description read as a work MPLADS does not allow (Annexure-II)?

Ported unchanged from data/trial/eligibility_trial.py (`v2`), where it was measured by
reading real matches (26 Sept 2026): on a FRESH sample of 50 matches, 56% plainly read as
a prohibited work and 80% were worth an officer's look (v1, the matcher in
validation/prohibited.py, was 12%; plain keywords 5%). It builds on v1 with fixes found by
reading its matches:

  * ration / fair-price / public-distribution shops are government PDS outlets
  * landmark words AFTER the keyword ("mandir ke pas", "temple to ...") mean a landmark
  * "Shishu Mandir", "Vidya Mandir", "... Memorial School" are institutions
  * works inside temple premises ("mandir prangan") are caught even when the verb is far

A match says "verify": 44% of matches are still legitimate works.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from drishti.validation.prohibited import LANDMARK, _patterns

PDS_SHOP = re.compile(
    r"\b(?:ration|fair\s*price|public\s+distribution|p\.?\s?d\.?\s?s?|fps|amutham)"
    r"\s+(?:system\s+)?shops?\b", re.I)
AFTER_LANDMARK = re.compile(
    r"^[\s,.-]*(?:(?:k[ei]?\s+)?pa+s+\b|k[ei]?\s+sam(?:a)?ne|k[ei]?\s+pi(?:ch|chh)e|k[ei]?\s+nikat|"
    r"k[ei]?\s+a+n?ge\b|k[ei]?\s+bagal|se\b|tak\b|(?:main\s+)?road\b|marg\b|to\b|towards\b|street\b|"
    r"chowk\b|gali\b|ki\s+or\b|ki\s+taraf\b|area\b|side\b)", re.I)
INSTITUTION = re.compile(
    r"\b(?:shishu|sishu|vidya|vidhya|bidya|siksha|shiksha|gyan|jnana|bal|ranga?|kala|natya|sangeet|samaj)"
    r"\s+mandir\b|"
    r"\bmemorial\s+(?:senior\s+|higher\s+|secondary\s+|primary\s+|public\s+)*"
    r"(?:school|college|hospital|hall|library|vidyalaya)\b|\bmandir\s+(?:school|vidyalaya|inter\s+college)\b",
    re.I)
WORSHIP = r"(?:temple|mandir|masjid|mosque|church|gurudwara|dargah|idgah|eidgah)"
PREMISES = re.compile(
    rf"\b(?:premises|campus|compound(?!\s+wall)|prangan|parisar|courtyard)\s+(?:of\s+)?(?:[\w.'-]+\s+){{0,3}}?"
    rf"{WORSHIP}\b|"
    rf"\b{WORSHIP}\s+(?:[\w.'-]+\s+)?(?:premises|campus|compound(?!\s+wall)|prangan|parisar|courtyard)\b"
    rf"(?!\s+(?:k[ei]\s+)?(?:nikat|pa+s|samne|bahar|near))", re.I)
NEAR_BEFORE = re.compile(
    r"\b(?:near|opposite|beside|behind|outside|in front of|nikat)\b(?:\s+[\w.'-]+){0,3}\s*$", re.I)


@dataclass(frozen=True)
class Inadmissible:
    item_id: str
    annexure_item: str
    keyword: str
    text: str


def v2(text: str | None) -> Inadmissible | None:
    """The Annexure-II item a description reads as, else None."""
    t = text or ""
    for item, kw, rx in _patterns():
        for m in rx.finditer(t):
            if LANDMARK.search(m.group(1) or ""):
                continue
            if AFTER_LANDMARK.search(t[m.end():]):
                continue
            if item["id"] == "COMMERCIAL" and PDS_SHOP.search(t):
                continue
            if item["id"] in ("RELIGIOUS", "NAMED_ASSET") and INSTITUTION.search(t):
                continue
            return Inadmissible(item["id"], str(item.get("annexure_ii_2016_item", "")), kw,
                                " ".join(item["text"].split()))
    m = PREMISES.search(t)
    if m and not NEAR_BEFORE.search(t[:m.start()]) and not INSTITUTION.search(t):
        for item, _kw, _rx in _patterns():
            if item["id"] == "RELIGIOUS":
                return Inadmissible("RELIGIOUS", str(item.get("annexure_ii_2016_item", "")),
                                    m.group(0).strip(), " ".join(item["text"].split()))
        return Inadmissible("RELIGIOUS", "", m.group(0).strip(), "places of worship")
    return None
