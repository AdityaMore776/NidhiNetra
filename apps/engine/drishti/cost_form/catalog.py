"""The form's fields, read once from reference/cost_form.yaml (T093).

Everything the web form renders and everything validate.py checks comes from that one file, so
the form, the checks and the spec cannot drift apart (tests/cost_form/test_catalog.py).
"""

from __future__ import annotations

from functools import cache
from pathlib import Path

import yaml

PATH = Path(__file__).resolve().parents[1] / "reference" / "cost_form.yaml"
SECTIONS = ("recommendation", "location", "work", "site_conditions", "line_fields", "charges",
            "timing", "totals", "prepared", "declarations")


@cache
def load() -> dict:
    with PATH.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def units() -> dict[str, tuple[str, float]]:
    return {k: (v[0], float(v[1])) for k, v in load()["units"].items()}


def family_of(work_type: str | None) -> tuple[str, dict] | None:
    for name, fam in load()["families"].items():
        if work_type in fam["types"]:
            return name, fam
    return None


def type_fields(work_type: str | None) -> list[dict]:
    """The size fields for one work type (its family's, minus those for other types)."""
    found = family_of(work_type)
    if not found:
        return []
    return [f for f in found[1]["fields"] if not f.get("types") or work_type in f["types"]]


def is_goods(work_type: str | None, nature: str | None = None) -> bool:
    found = family_of(work_type)
    return bool(found and found[1].get("goods")) or nature == "purchase"


def is_linear(work_type: str | None) -> bool:
    found = family_of(work_type)
    return bool(found and found[1].get("linear"))


def materials() -> list[dict]:
    return load()["materials"]


def material(material_id: str | None) -> dict | None:
    return next((m for m in materials() if m["id"] == material_id), None)


def for_type(work_type: str | None) -> dict:
    """What the web form shows for one work type: every section, the size fields of its family,
    the line groups, the materials it suggests and the units."""
    data = load()
    found = family_of(work_type)
    return {
        "version": data["version"],
        "work_type": work_type,
        "family": found[0] if found else None,
        "linear": is_linear(work_type),
        "goods": is_goods(work_type),
        "pricing": found[1]["pricing"] if found else None,
        "size_fields": type_fields(work_type),
        **{s: data[s] for s in SECTIONS},
        "line_groups": data["line_groups"],
        "materials": [{k: m[k] for k in ("id", "label", "units")} for m in materials()],
        "units": list(data["units"]),
    }


def pricing_size(work_type: str | None, size: dict) -> tuple[str, float] | None:
    """The size the agent prices this work by (e.g. ("m2", 937.5) for a road 250 m x 3.75 m),
    or None when the size fields it needs are missing or not numbers."""
    found = family_of(work_type)
    if not found:
        return None
    rules = found[1]["pricing"]
    for rule in rules if isinstance(rules, list) else [rules]:
        cond = rule.get("when")
        if cond and size.get(cond["field"]) not in cond.get("in", []):
            continue
        if rule.get("per_line"):
            return None                     # goods: priced line by line
        names = rule.get("product") or rule.get("sum") or []
        vals = [size.get(n) for n in names]
        if not names or any(not isinstance(v, (int, float)) or isinstance(v, bool) for v in vals):
            return None
        if rule.get("product"):
            value = 1.0
            for v in vals:
                value *= float(v)
        else:
            value = float(sum(vals))
        value *= float(rule.get("factor", 1))
        unit = rule["unit"] if rule["unit"] != "other" else str(size.get("size_unit") or "other")
        return (unit, value) if value > 0 else None
    return None
