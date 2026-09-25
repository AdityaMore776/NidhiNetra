"""What a work's description says about its size.

Ported from ~/saakshya/docs/visual/analyse_costs.py, where every pattern was
measured against the real corpus (AD-106): 8.8% of descriptions read as a
bundle, 7.3% state a length. Widened on 2026-09-25 after the first dry run
over all real works: the top of the ranking was bulk light orders the first
patterns missed ("217 DIFFRENT PLACES", "810 location", "as per list").

A sanction that names a count or a list is many works filed as one. At 100x
its peers it is either mispriced or many units under one work id, and the
agent reports which the description suggests, asserting neither.
"""

from __future__ import annotations

import math
import re

LENGTH = re.compile(
    r"(\d[\d,]*\.?\d*)\s*(mtr|mtrs|metre|metres|meter|meters|mt|rmt)\b", re.I)

COUNTABLE = (r"(?:solar|street\s*light|streetlight|light|lamp|mast|high\s*mast|highmast|"
             r"pole|hand\s*pump|handpump|bore\s*well|borewell|tube\s*well|fan|cooler|"
             r"computer|bench|desk|chair|table|cctv|camera|bulb|led|transformer|shed|"
             r"toilet|urinal|nos?|nag|adad|units?|sets?|pcs)")
BULK_COUNT = re.compile(r"\b(\d{1,4})\b(?:\s*\([^)]{0,40}\))?[\s\-,]{0,12}"
                        r"(?:\w+[\s\-]){0,3}?" + COUNTABLE, re.I)
BULK_WORDS = re.compile(r"\b(?:one|two|three|four|five|six|seven|eight|nine|ten|twenty|"
                        r"thirty|forty|fifty|sixty|seventy|eighty|ninety)\s+hundred\b", re.I)

# The corpus spells these "DIFFRENT PLACES", "60 DIFFERENT PLACE", "810 location".
DIFFERENT = r"diff?e?rent"
PLACES = r"(?:places?|locations?|sites?)"
BULK_LIST = re.compile(
    r"(?:sl\.?\s*no\.?|from)\s*\.?\s*\d+\s*(?:to|-)\s*\d+"
    r"|as\s+per\s+(?:the\s+)?(?:enclosed\s+|attached\s+)?list"
    r"|list\s+(?:enclosed|attached)"
    r"|\b\d{1,4}\s+(?:" + DIFFERENT + r"\s+)?" + PLACES + r"\b"
    r"|at\s+" + DIFFERENT + r"\s+" + PLACES,
    re.I)

# Below 10 m a number is a width or a diameter; above 10 km it is a typo or a
# corridor, not one village road.
MIN_LENGTH_M, MAX_LENGTH_M = 10.0, 10_000.0


def reads_as_bundle(text: str | None) -> bool:
    t = text or ""
    m = BULK_COUNT.search(t)
    if m:
        try:
            if int(m.group(1)) >= 2:
                return True
        except ValueError:
            pass
    return bool(BULK_WORDS.search(t) or BULK_LIST.search(t))


def stated_length(text: str | None) -> float:
    """Metres named in the description, or NaN when none is usable."""
    m = LENGTH.search(text or "")
    if not m:
        return math.nan
    try:
        v = float(m.group(1).replace(",", ""))
    except ValueError:
        return math.nan
    return v if MIN_LENGTH_M <= v <= MAX_LENGTH_M else math.nan
