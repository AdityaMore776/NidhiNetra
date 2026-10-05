"""A work's record, read one way by every index and engine (2 Oct 2026, foolproofing).

The engines each survive a malformed record on their own (an engine that raises becomes an
ERROR result, never a finding), but the cross-work indexes and the cohort statistics read every
record of the corpus in one pass: one row with a pandas NaN in a text column, a district code
loaded as a number, a datetime where a date was expected or an amount written "1,00,000"
stopped the whole build, and with it the batch (found by fuzzing,
tests/evaluation/test_random_environment.py). Here every column is checked once, the way
agents/evidence.py checks a work's evidence:

  text      text stays as written (no trimming, no case change); a whole number (a code read
            as a number) becomes its digits; anything else (NaN, a list, True) is no value
  amount,   a finite number ("1,00,000", the database's Decimal and numpy numbers read);
  quantity  anything else is no value
  dates     a date; a datetime gives its day; ISO text ("2024-02-01") and Indian day-first
            text ("01/02/2024", "01-02-2024") read; anything else is no date
  status    a coded value: upper case, single spaces ("completed " -> "COMPLETED"; "complete"
            and "completion" read as COMPLETED), so a clerk's casing never changes an answer
            (found by the T135 robustness loop: "completed" read as not complete)
  outside   True / False (also 1 / 0 and "yes" / "no"); anything else is no value
  signals   an object, else an empty one
Malformed values are dropped, never repaired by guessing. A clean record comes back as the
same object, so the batch's 2 lakh rows cost no copy.
"""

from __future__ import annotations

import math
import numbers
import re
from datetime import date, datetime

from drishti.agents.evidence import num

TEXT = ("work_id", "source", "house", "term", "state_lgd", "state_name", "district_lgd",
        "district_name", "constituency", "mp_name", "agency_name", "fy", "work_type_code",
        "category", "description", "quantity_unit")
NUMBERS = ("amount", "quantity")
DATES = ("recommended_date", "completed_date", "sanction_date")
YES = {"true", "yes", "y", "1"}
NO = {"false", "no", "n", "0"}
_DAY_FIRST = re.compile(r"(\d{1,2})[/.\-](\d{1,2})[/.\-](\d{4})")


def text(x) -> str | None:
    if isinstance(x, str):
        return x
    if isinstance(x, bool) or not isinstance(x, numbers.Real):
        return None
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return str(int(v)) if math.isfinite(v) and v.is_integer() else None


def day(x) -> date | None:
    """A date written as a date, a datetime, ISO text or Indian day-first text; else None."""
    try:
        if isinstance(x, datetime):
            d = x.date()
            return d if type(d) is date else None          # pandas NaT gives no real day
        if isinstance(x, date):
            return x
        if isinstance(x, str):
            s = x.strip()
            m = _DAY_FIRST.fullmatch(s)
            if m:
                return date(int(m[3]), int(m[2]), int(m[1]))
            return date.fromisoformat(s[:10])
    except (ValueError, TypeError, AttributeError):
        return None
    return None


STATUS_WORDS = {"COMPLETE": "COMPLETED", "COMPLETION": "COMPLETED"}


def status(x) -> str | None:
    t = text(x)
    if t is None:
        return None
    s = " ".join(t.split()).upper()
    return STATUS_WORDS.get(s, s) if s else t


def flag(x) -> bool | None:
    if x is None or isinstance(x, bool):
        return x
    if isinstance(x, str):
        s = x.strip().lower()
        return True if s in YES else False if s in NO else None
    try:                                    # 1 / 0, and a numpy bool from a pandas loader
        return True if x == 1 else False if x == 0 else None
    except (TypeError, ValueError):
        return None


def _same(a, b) -> bool:
    return a is b or (type(a) is type(b) and a == b)


def work(w: dict) -> dict:
    """The record with every column the engines read in its expected type (see the module
    note). Columns absent stay absent; other columns pass through untouched."""
    if not isinstance(w, dict):
        return {}
    changes = {}
    for keys, fn in ((TEXT, text), (NUMBERS, num), (DATES, day), (("status",), status),
                     (("is_outside_constituency",), flag)):
        for k in keys:
            if k in w:
                v = fn(w[k])
                if not _same(v, w[k]):
                    changes[k] = v
    if "signals" in w and not isinstance(w["signals"], dict):
        changes["signals"] = {}
    return {**w, **changes} if changes else w
