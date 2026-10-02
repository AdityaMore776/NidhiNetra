"""What the record says was built, in its own words: the claims Site Progress checks (T510).

Never a fixed checklist (AGENTS.md section 8). The claims are the record's and the officer's own
words, each kept with where it came from:

  asset    a work recorded complete claims its asset exists: the work type, with the
           description quoted ("Community hall / bhavan built: "Construction of community hall
           at Rampur ward 4"")
  length   a completed work whose description states a length claims it ("300 m as described")
  count    ... a count of units ("10 units as described")
  field    each sentence the site officer wrote about progress (work["field_notes"], from the
           field app, T063): "Roof slab cast", "Plastering done on all walls"

An open work claims nothing built yet: only its officer's notes are checked. A length or a count
is never judged from a zero-shot reading (a model that names what a photo shows cannot measure
or count): it stays "can't tell" unless a vision-language reader judged it.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from drishti import reference
from drishti.agents.site_progress.observe import group_of
from drishti.agents.statistical.scope import stated_count
from drishti.agents.statistical.text import stated_length

QUOTE_MAX = 140
COMPLETE = "COMPLETED"


@dataclass(frozen=True)
class Claim:
    kind: str                 # asset | length | count | field
    text: str
    source: str               # record | field notes
    group: str | None = None  # the concept group an asset claim is pictured by


def _complete(work: dict) -> bool:
    return str(work.get("status") or "").strip().upper() == COMPLETE


def claims_of(work: dict) -> list[Claim]:
    out: list[Claim] = []
    desc = " ".join(str(work.get("description") or "").split())
    wtype = work.get("work_type_code")
    if _complete(work):
        group = group_of(wtype)
        if group and desc:
            quote = desc if len(desc) <= QUOTE_MAX else desc[:QUOTE_MAX].rsplit(" ", 1)[0] + " ..."
            out.append(Claim("asset", f"{reference.work_type_name(wtype)} built: \"{quote}\"",
                             "record", group))
        metres = stated_length(desc, allow_km=True)
        if not math.isnan(metres) and metres > 0:
            out.append(Claim("length", f"{metres:,.0f} m as described", "record"))
        n = stated_count(desc, wtype)
        if n and n >= 2:
            out.append(Claim("count", f"{n} units as described", "record"))
    for note in work.get("field_notes") or ():
        note = " ".join(str(note or "").split())
        if note:
            out.append(Claim("field", note, "field notes"))
    return out
