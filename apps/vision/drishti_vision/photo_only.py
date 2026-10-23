"""T173: NidhiLens on photos alone (plan docs/plans/T173-photo-only-progress.md).

The owner, 21 Oct 2026: "If they are allowed to write a prompt, there are ways for it to be prompt
injected." So no text written by the agency reaches the model. The agency picks the stage reached
from a fixed list on the form (`PICKS`, reached now or since the last visit); the model only
describes the two photos (same place? stage in A, stage in B, permanent change?); code compares the
pick with what the photos show (`verdict`), by the same rules the training labels were made with
(vlmdata.mgnrega_items).

Two ways to ask, both with no agency text:
  photos only   - the prompt has the work type and nothing else (`observe_prompt`); code decides.
  fixed claim   - the prompt has a claim sentence written by code from the pick (`fixed_claim`),
                  so the model sees the format it was trained on; the model decides.
"""

from __future__ import annotations

import json
import re

from drishti_vision import vlmdata

PICKS = ("under way", "complete")           # the form's list: what stage the agency says it reached
KINDS = ("reached", "period")               # reached now / done since the last visit
FIELDS = ("same_place", "stage_A", "stage_B", "permanent_change")
_TEMPLATES = {("complete", "reached"): vlmdata.CLAIM_DONE,
              ("complete", "period"): vlmdata.CLAIM_DONE_PERIOD,
              ("under way", "reached"): vlmdata.CLAIM_STARTED,
              ("under way", "period"): vlmdata.CLAIM_STARTED_PERIOD}
# words that mark each template, in English, Hinglish and Hindi (vlmdata.CLAIM_*); the time-lapse
# claim "new construction work done since the last visit" (vlmdata.TL_CLAIM) asks for any progress,
# as "work started since the last visit" does
_DONE = ("completed", "poorn", "poora", "पूर्ण")
_STARTED = ("started", "chalu", "shuru", "प्रगति", "शुरू", "new construction", "naya nirmaan",
            "नया निर्माण")


def observe_prompt(work_type: str) -> str:
    """The question with no claim in it: only the work type, from the form's fixed list."""
    return (f"Work type: {work_type.replace('_', ' ')}. "
            f"Stages: {' -> '.join(vlmdata.LADDER)}.\n"
            "Describe only what the two photos show.\n"
            "Reply with JSON only: {\"same_place\": yes|no|unsure, "
            "\"stage_A\": <stage or unknown>, "
            "\"stage_B\": <stage or unknown>, \"permanent_change\": yes|no|cant_tell, "
            "\"reason\": <at most 25 words>}")


def fixed_claim(work_type: str, pick: str, kind: str) -> str:
    """The claim sentence code writes from the agency's pick (English, the generic work name)."""
    if (pick, kind) not in _TEMPLATES:
        raise ValueError(f"not on the form's list: {pick!r}, {kind!r}")
    return vlmdata.claim_text(_TEMPLATES[(pick, kind)], work_type, "", "en")


def pick_of_claim(claim: str) -> str | None:
    """Which pick a claim-ladder sentence stands for (to score the test set's written claims);
    None for anything that is not one of the ladder's sentences."""
    c = claim.lower()
    done = any(w in c for w in _DONE)
    started = any(w in c for w in _STARTED)
    if done == started:
        return None
    return "complete" if done else "under way"


_JSON = re.compile(r"\{.*\}", re.S)


def parse_observation(text: str) -> dict | None:
    m = _JSON.search(text or "")
    if not m:
        return None
    try:
        d = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None
    if not all(k in d for k in FIELDS):
        return None
    return {k: str(d[k]).strip().lower().replace("_", " ") if k.startswith("stage")
            else str(d[k]).strip().lower() for k in FIELDS} | {"reason": d.get("reason")}


def verdict(o: dict | None, pick: str, kind: str) -> str:
    """shown / not_shown / cant_tell: the agency's pick against what the photos show."""
    if not o or o.get("same_place") != "yes" or o.get("permanent_change") not in ("yes", "no"):
        return "cant_tell"
    b, changed = o.get("stage_B"), o["permanent_change"] == "yes"
    rung = {s: i for i, s in enumerate(vlmdata.LADDER)}
    need = {"under way": 1, "complete": 2}[pick]
    if kind == "reached":
        return "cant_tell" if b not in rung else ("shown" if rung[b] >= need else "not_shown")
    if not changed:
        return "not_shown"
    if pick == "under way":
        return "shown"
    return "cant_tell" if b not in rung else ("shown" if rung[b] >= need else "not_shown")
