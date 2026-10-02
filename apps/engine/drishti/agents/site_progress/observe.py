"""What a photo shows, kept as scores: the stored reading behind Site Progress v2 (T510).

A photo is read once, offline, by a local zero-shot model (readers.py): it scores the photo
against every line of reference/site_concepts.yaml ("a photo of a finished cement concrete
road", "a photo of an unpaved dirt road", "a photo of a scanned document", ...). The reading
kept is, for every concept group, how much of the photo's score goes to "the finished asset",
"an unbuilt site" and "not a site photo" (a softmax over that group's lines and the not-a-site
lines). It does not depend on the work the photo is attached to, so any work, including one
whose type is corrected later, is judged against the same stored reading. No picture, face or
text is kept.

One photo, for the work's group, then reads as:
  shows       the finished asset takes at least SHOW_MIN of the score
  not_built   an unbuilt site takes at least NOT_BUILT_MIN and the asset at most NOT_BUILT_MAX
  not_site    a document, a meeting, a map: never evidence either way
  unclear     anything else
The cut-offs are set by design and measured by data/trial/site_progress_trial.py on the pilot's
real photos before the engine is switched on.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from functools import cache

from drishti import reference

VERSION = "site-obs-1"
SHOW_MIN = 0.50
NOT_BUILT_MIN = 0.70
NOT_BUILT_MAX = 0.15
NOT_SITE_MIN = 0.50
KINDS = ("built", "not_built", "not_site")


@dataclass(frozen=True)
class Prompt:
    group: str        # a concept group, or "*" for the not-a-site lines
    kind: str         # built | not_built | not_site
    text: str         # the line as the model reads it: "a photo of ..."


@cache
def groups() -> dict[str, dict]:
    return dict(reference.site_concepts()["groups"])


@cache
def _type_group() -> dict[str, str]:
    return {t: g for g, spec in groups().items() for t in spec.get("types") or ()}


def group_of(work_type: str | None) -> str | None:
    return _type_group().get(work_type or "")


@cache
def prompts() -> tuple[Prompt, ...]:
    c = reference.site_concepts()
    tpl = c.get("template") or "a photo of {}"
    out = [Prompt("*", "not_site", tpl.format(x)) for x in c.get("not_site") or ()]
    for g, spec in groups().items():
        for kind in ("built", "not_built"):
            out += [Prompt(g, kind, tpl.format(x)) for x in spec.get(kind) or ()]
    return tuple(out)


def observation(logits: dict[str, float], reader: str) -> dict:
    """The stored reading of one photo from the model's score for every prompt."""
    out: dict[str, dict] = {}
    for g in groups():
        mine = [p for p in prompts() if p.group in (g, "*") and p.text in logits]
        if not mine:
            continue
        top = max(logits[p.text] for p in mine)
        weights = [(p.kind, math.exp(logits[p.text] - top)) for p in mine]
        total = sum(w for _k, w in weights)
        out[g] = {k: round(sum(w for kk, w in weights if kk == k) / total, 4) for k in KINDS}
    return {"reader": reader, "version": VERSION, "groups": out}


def read(obs: dict | None, group: str | None) -> str | None:
    """shows / not_built / not_site / unclear for the work's group; None when never read."""
    if not obs or obs.get("version") != VERSION or not group:
        return None
    g = (obs.get("groups") or {}).get(group)
    if not g:
        return None
    built, not_built, not_site = (float(g.get(k) or 0.0) for k in KINDS)
    if not_site >= NOT_SITE_MIN:
        return "not_site"
    if built >= SHOW_MIN:
        return "shows"
    if not_built >= NOT_BUILT_MIN and built <= NOT_BUILT_MAX:
        return "not_built"
    return "unclear"
