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
         r"taluk|po|ps|colony|nagar|street|lane|main|k|kul)\b")
_NAME = r"(?:\s+(?!" + _STOP + r")[A-Za-z][A-Za-z.'-]*){1,3}"
RELATION = re.compile(
    r"\b(S\s*[/\\]\s*[Oo0]|W\s*[/\\]\s*[Oo0]|D\s*[/\\]\s*[Oo0]|son\s+of|wife\s+of|"
    r"daughter\s+of|husband\s+of|contact\s+person)\b\.?" + _NAME, re.I)
# Bare "Shri" is left alone: it usually names a deity or an institution ("Shri Ram Mandir").
HONORIFIC = re.compile(r"\b(Sh\.|Smt\.?|Shrimati|Kumari|Mr\.?|Mrs\.?|Late|Lt\.)" + _NAME)
HOUSE = re.compile(r"\b(house\s+of|H\s*[/\\]\s*O|residence\s+of)\b\.?" + _NAME, re.I)


def mask(text: str | None) -> str | None:
    if not text:
        return text
    t = PHONE.sub("[phone]", text)
    t = ACCOUNT.sub("[number]", t)
    t = RELATION.sub(lambda m: f"{m.group(1)} [name]", t)
    t = HONORIFIC.sub(lambda m: f"{m.group(1)} [name]", t)
    t = HOUSE.sub(lambda m: f"{m.group(1)} [name]", t)
    return t
