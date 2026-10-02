"""Mask personal details in text an officer or the public site shows.

eSAKSHI descriptions sometimes name private people and carry their phone numbers:
"near the house of Sanjay Kumar S/o Shivaji Singh", "contact person ... 90612xxxxx",
"new connection to <name> wife <name>". The site shows the work, not the people, so
before a description leaves the engine:

  phone numbers (10-digit Indian mobiles)        -> [phone]
  11-18 digit runs (bank accounts)                -> [number]
  a relation marker and the name after it         -> "S/o [name]"
    (S/o, W/o, D/o, C/o-less forms: son of, wife of, daughter of, wife, husband)
  an honorific and the name after it              -> "Shri [name]"
    (Shri, Sh., Smt, Shrimati, Kumari, Mr, Mrs, Late)
  "house of <name>" / "H/O <name>"                -> "house of [name]"

Place names, work ids, amounts and dates are left alone. The same patterns are used by
data/trial/sanitize_results.py for anything committed from the trials.
"""

from __future__ import annotations

import re

PHONE = re.compile(r"(?<![\d/V.])(?:\+91[\s-]?)?[6-9]\d{9}(?![\d.])")
ACCOUNT = re.compile(r"(?<![\d/V.])\d{11,18}(?![\d.])")
# a name: one to three words; stops at punctuation, digits and place words ("Ward No 9")
_STOP = (r"(?:ward|village|vill|gram|road|near|to|in|at|of|ke|ki|ka|se|tak|panchayat|block|"
         r"dist|district|school|house|mandir|temple|masjid|and|with|for|the|no|gp|tehsil|"
         r"taluk|po|ps|colony|nagar|street|lane|main|k|kul|son|wife|daughter|husband)\b")
_NAME = r"(?:\s+(?!" + _STOP + r")[A-Za-z][A-Za-z.'-]*){1,3}"
RELATION = re.compile(
    r"\b(S\s*[/\\]\s*[Oo0]|W\s*[/\\]\s*[Oo0]|D\s*[/\\]\s*[Oo0]|son\s+of|wife\s+of|"
    r"daughter\s+of|husband\s+of|contact\s+person)\b\.?" + _NAME, re.I)
# Bare "Shri" is left alone: it usually names a deity or an institution ("Shri Ram Mandir").
HONORIFIC = re.compile(r"\b(Sh\.|Smt\.?|Shrimati|Kumari|Mr\.?|Mrs\.?|Late|Lt\.)" + _NAME)
HOUSE = re.compile(r"\b(house\s+of|H\s*[/\\]\s*O|residence\s+of|request\s+of|requested\s+by)"
                   r"\b\.?" + _NAME, re.I)
# "from <name>'s house to ..." (2 Oct 2026, read on the dashboard queue): one to three
# capitalised words before 's and a home word; a place word or "from" stops the name
_CAP = r"(?!(?i:" + _STOP + r"|from|road|the)\b)[A-Z][A-Za-z.-]*"
POSSESSIVE = re.compile(r"\b(?:" + _CAP + r"\s+){0,2}" + _CAP
                        + r"'[sS](\s+(?i:house|home|residence|field|farm|land|shop))\b")
# the Hindi and Gujarati forms, "<name> ke ghar ke pas", "<NAME> K GHAR", "<name> na ghar":
# up to three words before the genitive and a home word; place words and "me/mein" stop the name
# (T056: "k ghar" 1,332 times and "na ghar" 339 times on the dashboard's descriptions)
_HI_WORD = r"(?!(?:" + _STOP + r"|me|mein|men|bhawan|bhavan)\b)[A-Za-z][A-Za-z.-]*"
_GENITIVE = r"(?:ke|ki|ka|k|kai|na|ni|nu|no|naa)"
HI_HOME = re.compile(r"\b(?:" + _HI_WORD + r"\s+){0,2}" + _HI_WORD
                     + r"(\s+" + _GENITIVE + r"\s+(?:ghar|khet|makan|dukan|bari)\b)", re.I)
# "<name> house" with no possessive: "PCC road from <name> house to <name> house" (T056, the
# dashboard's 57,508 descriptions: "mahto house" 301 times, "singh house" 219). Up to three words
# before a home word are a name unless the word before it is an ordinary one: these were read by
# eye among the 450 commonest words before such nouns ("guest house", "panchayat land", "ration
# shop", "barat ghar" a wedding hall, "old age home").
# (not "kothi", "haveli", "bungalow": on real works they are mostly parts of place names)
_HOME = r"(?:house|home|residence|makan|ghar|farm|field|land|shop|dukan|khet|bari)"
_COMMON = (r"(?:the|a|an|his|her|their|our|own|old|new|said|this|that|its|private|public|"
           r"government|govt|owned|open|vacant|waste|low|forest|aabadi|abadi|populated|agricultural|agriculture|"
           r"cultivation|paddy|wrc|guest|pump|rest|circuit|light|ware|power|green|store|club|court|"
           r"slaughter|engine|gate|glass|boat|dak|pack|out|cow|cattle|milk|dairy|poultry|fish|"
           r"piggery|goat|mushroom|nursery|seed|solar|wind|tea|coffee|sweet|kirana|grocery|ration|"
           r"rashan|price|pd|pds|distribution|dealer|wine|liquor|medical|medicine|chemist|mobile|"
           r"cycle|photo|photos|tv|food|fair|hardware|cloth|vegetable|fruit|meat|hotel|dhaba|"
           r"market|bazar|bazaar|bus|petrol|cooperative|society|community|samaj|barat|baarat|"
           r"panchyat|panchayati|gram|sabha|guru|bathing|nursing|age|marriage|faith|juvenile|"
           r"children|orphan|shelter|care|model|awas|awaas|aawas|pmay|iay|sports|play|ground|"
           r"football|cricket|brick|tile|tiles|agri|agro|crop|rice|sugarcane|cotton|wheat|maize|"
           r"farm|form|toilet|bath|wash|watchman|chowkidar|chokidar|tola|basti|mohalla|sc|st|bpl|"
           r"church|gurudwara|dharamshala|kabristan|kabrastan|shamshan|cemetery|burial|graveyard|"
           r"railway|canal|river|pond|talab|nala|nallah|hospital|college|office|bank|post|police|"
           r"fire|water|pani|tank|tube|bore|well|motor|mill|oil|ice|cold|mhip|ywa|row|towords|"
           r"sadak|sarak|marg|rasta|raasta|path|pul|puliya|nali|naali|kuan|khadanja|kharanja|"
           r"nirman|drain|drains|cultural|culture|white|upper|lower|tent|ncc|army|bar|shop|"
           r"sarkari|chai|alongwith|antargat|kali|harijan|dc|"
           r"via|toward|towards|from|fromthe|upto|till|on|by|me|mein|wale|wala|wali|"
           r"ke|ki|ka|k|kai|na|ni|nu|no|naa)")
_OWNER = r"(?!(?:" + _STOP + r"|" + _COMMON + r"\b))[A-Za-z][A-Za-z.'’-]*"
# not right after an apostrophe (straight or curly): "[name]'s house" is already masked
OWNER_HOME = re.compile(r"(?<!['’])\b(?:" + _OWNER + r"\s+){0,2}" + _OWNER + r"(\s+"
                        + _HOME + r")\b", re.I)
# the person named BEFORE a relation marker, "<name> S/O [name]" (T056: the marker's own rule
# masked only the father's name; 4 of 40 unmasked home-word spans read this way)
_MARKER = (r"(?:S\s*[/\\]\s*[Oo0]|W\s*[/\\]\s*[Oo0]|D\s*[/\\]\s*[Oo0]|son\s+of|wife\s+of|"
           r"daughter\s+of|husband\s+of)\b")
BEFORE_RELATION = re.compile(r"(?<!['’])\b(?:" + _OWNER + r"\s+){0,2}" + _OWNER
                             + r"(?=\s+" + _MARKER + r")", re.I)
# a name masked in two steps ("S/O [name] [name] K GHAR") reads as one
_REPEATED = re.compile(r"\[name\](?:\s+\[name\])+")


def mask(text: str | None) -> str | None:
    if not text:
        return text
    t = PHONE.sub("[phone]", text)
    t = ACCOUNT.sub("[number]", t)
    t = RELATION.sub(lambda m: f"{m.group(1)} [name]", t)
    t = HONORIFIC.sub(lambda m: f"{m.group(1)} [name]", t)
    t = HOUSE.sub(lambda m: f"{m.group(1)} [name]", t)
    t = POSSESSIVE.sub(lambda m: f"[name]'s{m.group(1)}", t)
    t = HI_HOME.sub(lambda m: f"[name]{m.group(1)}", t)
    t = OWNER_HOME.sub(lambda m: f"[name]{m.group(1)}", t)
    t = BEFORE_RELATION.sub("[name]", t)
    return _REPEATED.sub("[name]", t)
