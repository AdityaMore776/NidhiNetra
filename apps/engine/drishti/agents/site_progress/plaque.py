"""Read an MPLADS plaque from the text found in a site photo (Site Progress v2, T510).

The guidelines want every MPLADS asset to carry a plaque naming the scheme (CAG found 4,918
works without one). A plaque is often painted or carved with the work's dates: the pilot's
Chittaurgarh cremation-ground wall carries "work started 1 Oct 2023, finished 31 Dec 2023"
although the MP recommended it on 11 Mar 2024 (FINDINGS B3). The photo's text comes from the
same local OCR the team already runs (data/trial/ocr_pages.py), read over the whole photo.

Kept: whether the scheme is named, and each date with its label (start / completion /
sanction, or none). Never kept: the text itself, names (a plaque names the MP: never stored,
never scored), amounts.

A date followed by a time is a GPS-camera stamp, not a plaque date (the rule stamp.py uses the
other way round).
"""

from __future__ import annotations

import re
from datetime import date

# Local OCR often drops spaces ("MPLADS2023-24", "SANSADNIDHI"), so the compact forms need no
# word boundary; the spaced form "M.P. LAD" must not start inside a word.
SCHEME = re.compile(
    r"MPLADS?"
    r"|(?<![a-z])M\s*\.?\s*P\s*[.\s-]+\s*L\s*\.?\s*A\s*\.?\s*D"
    r"|member\s*of\s*parliament\s*local\s*area"
    r"|sansad\s*(?:nidhi|kosh)"
    r"|(?<![a-z])m\s*\.?\s*p\s*\.?\s*(?:fund|nidhi)(?![a-z])"
    r"|सांसद\s*(?:निधि|स्थानीय|कोष)", re.I)
DATE = re.compile(r"(?<!\d)(\d{1,2})\s*[./-]\s*(\d{1,2})\s*[./-]\s*(20\d{2})(?!\d)")
TIME_AFTER = re.compile(r"^\s*,?\s*\d{1,2}\s*:\s*\d{2}")
LABELS = (
    ("start", re.compile(r"start|commence|began|begin|prarambh|aarambh|shuru|प्रारं|आरंभ|शुरू",
                         re.I)),
    ("completion", re.compile(r"complet|finish|samapt|purn|पूर्ण|समाप्त", re.I)),
    ("sanction", re.compile(r"sanction|swikrit|स्वीकृ", re.I)),
)
LABEL_WINDOW = 40
EARLIEST = date(2000, 1, 1)


def _label(before: str) -> str | None:
    """The label nearest before a date, within LABEL_WINDOW characters."""
    window = before[-LABEL_WINDOW:]
    best, at = None, -1
    for name, rx in LABELS:
        for m in rx.finditer(window):
            if m.start() > at:
                best, at = name, m.start()
    return best


def read(text: str | None) -> dict:
    """{"scheme": bool, "dates": [{"label": start|completion|sanction|None, "date": iso}]}."""
    t = " ".join((text or "").split())
    out: dict = {"scheme": bool(SCHEME.search(t)), "dates": []}
    for m in DATE.finditer(t):
        if TIME_AFTER.match(t[m.end():]):
            continue                                   # a camera stamp's date and time
        d, mo, y = (int(x) for x in m.groups())
        try:
            when = date(y, mo, d)
        except ValueError:
            continue
        if when < EARLIEST:
            continue
        item = {"label": _label(t[:m.start()]), "date": when.isoformat()}
        if item not in out["dates"]:
            out["dates"].append(item)
    return out
