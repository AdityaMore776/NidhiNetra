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


# ---- Devanagari descriptions (T051) --------------------------------------------------
# The export garbles Hindi to "????", so the corpus has no Devanagari text, but a live
# recommendation can carry it. Hindi puts the object before the verb: "मंदिर का निर्माण"
# (construction of a temple), "मंदिर परिसर में शेड" (a shed inside the temple premises). The
# keyword must be followed by a verb or a premises word, and NOT by a landmark postposition
# ("मंदिर के पास सड़क" = a road near the temple). Python's \b breaks inside Devanagari words
# (vowel signs are not alphanumeric), so word edges are written as explicit lookarounds.
DEV = "ऀ-ॿ"
_EDGE_L, _EDGE_R = rf"(?<![{DEV}])", rf"(?![{DEV}])"
HI_VERB = (r"(?:नव\s*)?(?:निर्माण|पुनर्निर्माण|जीर्णोद्धार|मरम्मत|सौंदर्यीकरण|सुंदरीकरण|सौन्दर्यीकरण|"
           r"विस्तार|स्थापना)")
HI_PREMISES = r"(?:परिसर|प्रांगण|प्रागंण|अहाते|आंगन)"
HI_LANDMARK = re.compile(r"^\s*(?:के\s+(?:पास|सामने|पीछे|निकट|बगल)|से|तक|की\s+(?:ओर|तरफ)|"
                         r"मार्ग|रोड|गली|चौक|वाली\s+सड़क)" + _EDGE_R)
HI_INSTITUTION = re.compile(rf"(?:शिशु|विद्या|सरस्वती|ज्ञान|बाल)\s*मंदिर{_EDGE_R}")


def _hi_patterns() -> list[tuple[dict, str, re.Pattern]]:
    from drishti import reference

    out = []
    for item in reference.prohibited_items():
        if item.get("superseded_likely"):
            continue
        for kw in item.get("keywords_hi") or []:
            words = r"\s*".join(re.escape(w) for w in kw.split())
            out.append((item, kw, re.compile(
                rf"{_EDGE_L}(?P<kw>{words}){_EDGE_R}\s*(?:[{DEV}]+\s+){{0,2}}?(?:(?:का|की|के)\s+)?"
                rf"(?:{HI_VERB}|{HI_PREMISES}){_EDGE_R}")))
    return out


def script(text: str | None) -> str:
    """'latin', 'devanagari', 'other' (a script this reader cannot read) or 'none'."""
    t = text or ""
    latin = sum(ch.isascii() and ch.isalpha() for ch in t)
    dev = sum("ऀ" <= ch <= "ॿ" for ch in t)
    other = sum(ch.isalpha() and not ch.isascii() and not ("ऀ" <= ch <= "ॿ")
                for ch in t)
    if not (latin or dev or other):
        return "none"
    best = max((latin, "latin"), (dev, "devanagari"), (other, "other"))
    return best[1]


def v2_hindi(text: str | None) -> Inadmissible | None:
    t = text or ""
    if HI_INSTITUTION.search(t):
        return None
    for item, kw, rx in _hi_patterns():
        for m in rx.finditer(t):
            # a landmark right after the keyword ("मंदिर के पास ... निर्माण") is not the object
            if HI_LANDMARK.search(t[m.end("kw"):]):
                continue
            return Inadmissible(item["id"], str(item.get("annexure_ii_2016_item", "")), kw,
                                " ".join(item["text"].split()))
    return None


def v2(text: str | None) -> Inadmissible | None:
    """The Annexure-II item a description reads as, else None."""
    t = text or ""
    if re.search(f"[{DEV}]", t):
        hit = v2_hindi(t)
        if hit:
            return hit
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
