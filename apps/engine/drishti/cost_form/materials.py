"""Recognise a typed expense item as one of the form's known materials (T093).

The implementing agency types items freely ("OPC cement 43 grade", "sariya", "balu"). This
suggests which known material an item is; the form shows "Recognised as: <material>" and the
person confirms or changes it. Only a confirmed match is ever compared with a reference (T097),
so a wrong suggestion can never become a flag.

Matching is by whole words (a name of several words must appear as that phrase), in English and
in the Hindi words used on Indian estimates. When names of two different materials match equally
well, nothing is suggested: the person chooses.
"""

from __future__ import annotations

import re

from drishti.cost_form import catalog

# splits on spaces and ASCII punctuation only, so Hindi words stay whole
_SPLIT = re.compile(r"[\s,.;:()\[\]{}/\\_+*&|'\"!?=<>#@%-]+")


def tokens(text: str | None) -> list[str]:
    return [t for t in _SPLIT.split(text.lower() if isinstance(text, str) else "") if t]


def _has_phrase(words: list[str], phrase: list[str]) -> bool:
    n = len(phrase)
    return any(words[i:i + n] == phrase for i in range(len(words) - n + 1))


# which names a line of each group is read against (T141): a labour row only trades, a machine
# hired only materials ("JCB with operator" is a machine), anything else every name
LABOUR_BY_GROUP = {"labour": True, "machinery": False}


def match(item: str | None, labour: bool | None = None) -> str | None:
    """The id of the known material this typed item is, or None (unknown or ambiguous).
    `labour`: True looks only at the labour trades (a labour row: "painter for distemper" is a
    painter), False never at them (a machine hired "with operator"), None at everything."""
    words = tokens(item)
    if not words:
        return None
    best: dict[str, int] = {}
    for m in catalog.materials():
        if labour is not None and labour != (m.get("grade") in catalog.GRADES):
            continue
        for name in m["names"]:
            phrase = tokens(name)
            if phrase and _has_phrase(words, phrase):
                score = sum(len(w) for w in phrase)
                best[m["id"]] = max(best.get(m["id"], 0), score)
    if not best:
        return None
    # a generic entry (a labour grade: "skilled") only when nothing more specific fits, so
    # "skilled mason" is a mason and "semi skilled helper" a helper (T141)
    specific = {k: v for k, v in best.items() if not (catalog.material(k) or {}).get("generic")}
    best = specific or best
    # stone named for a road's base course is the base, not concrete's aggregate (T144):
    # "40 mm aggregate for WBM", "ballast for base course"; priced and sized as the base
    if "aggregate" in best and "granular_base" in best:
        return "granular_base"
    top = max(best.values())
    winners = [k for k, v in best.items() if v == top]
    return winners[0] if len(winners) == 1 else None


def per_first_unit(material: dict, rate: float, unit: str) -> float | None:
    """The rate restated per the material's first unit (e.g. Rs 8 per kg of cement -> Rs 400 per
    bag), or None when the unit cannot be converted to it."""
    table = catalog.units()
    first = material["units"][0]
    if not isinstance(unit, str) or unit not in table or first not in table:
        return None
    (dim_u, f_u), (dim_f, f_f) = table[unit], table[first]
    if dim_u != dim_f or f_u <= 0:
        return None
    return rate * f_f / f_u
