"""The demonstration data of the website's work intelligence form (T134).

No agency has filed the website's form yet, so the form page's demo compares a filled form with
made-up example data: other agencies' filings (their rates are the district's prices), the earlier
works the examples repeat or split, and what the record shows after sanction (the dates, and the
site videos as the video job reads them). data/trial/work_form_examples.py writes this file, and
the page's own plain-words copy of it (apps/web/public/work-form/examples.json, "data"), so the
page shows exactly what the agents compared with.

Used only when a request asks for the demo (POST /work-form/check?demo=true); never stored, never
mixed into the batch or any other route.
"""

from __future__ import annotations

import json
from datetime import date
from functools import cache
from pathlib import Path

FILE = Path(__file__).parent / "reference" / "demo" / "work_form.json"
PLACE = ("district_lgd", "district_name", "state_lgd", "state_name")


@cache
def _text() -> str:
    try:
        return FILE.read_text(encoding="utf-8")
    except OSError:
        return "{}"


def _data() -> dict:
    # parsed afresh each time: the engines may annotate a work, and the cached text stays clean
    try:
        data = json.loads(_text())
    except ValueError:
        data = {}
    return data if isinstance(data, dict) else {}


def records(work: dict) -> list[dict]:
    """The example works and filings, placed in this work's district, without the work itself."""
    own = str(work.get("work_id") or "")
    place = {k: work.get(k) for k in PLACE}
    return [{**r, **place} for r in _data().get("records") or []
            if isinstance(r, dict) and str(r.get("work_id") or "") != own]


def as_of() -> date | None:
    """The day the example data is written for (T164): the filings' dates and what their record
    shows after sanction are set against it. None when the file gives none."""
    v = _data().get("as_of")
    try:
        return date.fromisoformat(v) if isinstance(v, str) else None
    except ValueError:
        return None


def later(work_id: str | None) -> dict:
    """What the record shows after sanction for this example filing (status, dates, site
    videos); {} for any other work."""
    found = (_data().get("later") or {}).get(str(work_id or ""))
    return found if isinstance(found, dict) else {}
