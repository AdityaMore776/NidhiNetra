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
    r"\b(?:ration|fair\s*price|(?:public|pulic|publik|publick)\s+distribution|p\.?\s?d\.?\s?s?|fps|"
    r"amutham)"
    r"\s+(?:system\s+)?shops?\b", re.I)
AFTER_LANDMARK = re.compile(
    r"^[\s,.-]*(?:(?:k[ei]?\s+)?pa+s+\b|k[ei]?\s+sam(?:a)?ne|k[ei]?\s+pi(?:ch|chh)e|k[ei]?\s+nikat|"
    r"k[ei]?\s+a+n?ge\b|k[ei]?\s+bagal|se\b|tak\b|(?:main\s+)?road\b|marg\b|to\b|towards\b|street\b|"
    r"chowk\b|gali\b|ki\s+or\b|ki\s+taraf\b|area\b|side\b)", re.I)
INSTITUTION = re.compile(
    r"\b(?:shishu|sishu|vidya|vidhya|bidya|siksha|shiksha|gyan|jnana|bal|ranga?|kala|natya|sangeet|samaj)"
    r"\s+mandir\b|"
    r"\bmemorial\s+(?:senior\s+|higher\s+|secondary\s+|primary\s+|public\s+)*"
    r"(?:school|college|hospital|hall|library|vidyalaya|institution|institute|academy)\b|"
    r"\bmandir\s+(?:school|vidyalaya|inter\s+college)\b",
    re.I)
# A work FOR a private institution (Annexure-II item 2: works belonging to private organisations):
# "table of kitchen, private school" (10 works), "JAGAT PRIVETE ITI ME SOLAR PLANT". A private
# school named as a landmark or an end of a road ("near the private school", "road from Pvt
# School", "private ITI vai ... tak") is not the work (read on the dashboard tables, 2 Oct 2026).
PRIVATE_INSTITUTION = re.compile(
    r"\b(?:private|privete|pvt\.?)\s+(?:school|iti|college|hospital|institute|institution|"
    r"nursing\s+home|clinic)\b(?!\s+(?:k[ei]\s+)?(?:pa+s|samne|nikat|tak|se|vai|via)\b)", re.I)
ROUTE_BEFORE = re.compile(
    r"\b(?:near|opposite|beside|behind|outside|front\s+of|nikat|from|to|se|tak|via|vai|upto|"
    r"till)\b(?:\s+[\w.'-]+){0,4}\s*$", re.I)
WORSHIP = r"(?:temple|mandir|masjid|mosque|church|gurudwara|dargah|idgah|eidgah)"
PREMISES = re.compile(
    rf"\b(?:premises|campus|compound(?!\s+wall)|prangan|parisar|courtyard)\s+(?:of\s+)?(?:[\w.'-]+\s+){{0,3}}?"
    rf"{WORSHIP}\b|"
    rf"\b{WORSHIP}\s+(?:[\w.'-]+\s+)?(?:premises|campus|compound(?!\s+wall)|prangan|parisar|courtyard)\b"
    rf"(?!\s+(?:k[ei]\s+)?(?:nikat|pa+s|samne|bahar|near|samip|sameep|najdik|nazdik|nazdeek|"
    rf"bagal))", re.I)
# A road named after the place of worship it leads to or passes ("Puthiyakavu temple link road",
# "Pera - St. John's Church - Cheruvalloore Road"): the road is the work, the shrine a name.
# Read by eye on the eSAKSHI dashboard tables, 2 Oct 2026 (2 of 12 R07 flags).
ROAD_NAMED = re.compile(
    r"^[\s,.'-]*(?:[\w.'-]+[\s-]+){0,3}?(?:link\s+|approach\s+|connecting\s+|main\s+)?"
    r"(?:road|rd|marg|rasta|sadak|sarak|street|lane|gali|path)\b", re.I)
# Romanised Hindi puts the object before the verb: "shiv mandir ka saundaryikaran karya" (the
# beautification of a temple), "hanuman mandir nirman". Only the keyword followed at once by
# ka/ki/ke and a work verb counts: "... se Shiv mandir tak pcc nirman" is a road to the temple
# (8 of the 9 romanised candidates on the dashboard tables of 2 Oct 2026 were such roads).
HI_LATIN_OBJECT = re.compile(
    r"\b(?P<kw>mandir|masjid|gurudwara|gurdwara|girja\s*ghar|dargah|idgah|eidgah|devsthan|"
    r"devasthan|thakurbari|shivalaya?)\s+(?:(?:ka|ki|ke)\s+)?(?:nav\s*)?"
    r"(?:nirman|nirmaan|jirnoddhar|jirnodhar|jeernoddhar|punarnirman|saundaryikaran|"
    r"sundarikaran|sondaryikaran|saundarikaran|marammat|chahardiwari|chardiwari)\b", re.I)
# A structure built IN, FOR or OF a place of worship: "Construction of Toilet in Catholic Church",
# "Community Hall in Mandir", "boundary wall for Parvathi temple", "boundary wall of jama masjid".
# "at" is left out ("shed at Chinar Mandir" names a place), so are "in front of" and "near" (read
# on the dashboard tables, 2 Oct 2026: 4 of 18 candidates were works on a place of worship, the
# rest schools named "... Vidya Mandir", landmarks, or places called "eidgah").
ON_WORSHIP = re.compile(
    r"\b(?:boundary\s*wall|compound\s*wall|chahardiwari|chardiwari|toilets?|community\s+hall|"
    r"hall|platform|shed|rooms?|kitchen|flooring|roof|stage|gate)\s+(?:in|inside|within|for|of)"
    r"\s+(?:the\s+)?(?!front\b)(?:[\w.'-]+\s+){0,3}?(?:temple|mandir|masjid|mosque|church|"
    r"gurudwara|dargah)\b(?!\s+(?:area|hills?|colony|road|marg|samiti|trust\s+school))", re.I)
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
            if item["id"] == "RELIGIOUS" and ROAD_NAMED.search(t[m.end():]):
                continue
            if item["id"] == "COMMERCIAL" and PDS_SHOP.search(t):
                continue
            if item["id"] in ("RELIGIOUS", "NAMED_ASSET") and INSTITUTION.search(t):
                continue
            return Inadmissible(item["id"], str(item.get("annexure_ii_2016_item", "")), kw,
                                " ".join(item["text"].split()))
    m = PRIVATE_INSTITUTION.search(t)
    if m and not ROUTE_BEFORE.search(t[:m.start()]):
        for item, _kw, _rx in _patterns():
            if item["id"] == "PRIVATE_BUILDING":
                return Inadmissible("PRIVATE_BUILDING",
                                    str(item.get("annexure_ii_2016_item", "")),
                                    m.group(0).strip(), " ".join(item["text"].split()))
    m = HI_LATIN_OBJECT.search(t) or ON_WORSHIP.search(t)
    if m and not INSTITUTION.search(t):
        for item, _kw, _rx in _patterns():
            if item["id"] == "RELIGIOUS":
                return Inadmissible("RELIGIOUS", str(item.get("annexure_ii_2016_item", "")),
                                    m.group(0).strip(), " ".join(item["text"].split()))
    m = PREMISES.search(t)
    if m and not NEAR_BEFORE.search(t[:m.start()]) and not INSTITUTION.search(t):
        for item, _kw, _rx in _patterns():
            if item["id"] == "RELIGIOUS":
                return Inadmissible("RELIGIOUS", str(item.get("annexure_ii_2016_item", "")),
                                    m.group(0).strip(), " ".join(item["text"].split()))
        return Inadmissible("RELIGIOUS", "", m.group(0).strip(), "places of worship")
    return None
