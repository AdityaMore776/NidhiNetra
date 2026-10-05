"""Other forms the agents read, and the engine fields each one never asks (T134).

The engine's own cost estimate form (reference/cost_form.yaml) asks for everything the agents
can use. The website's Pre-Sanction Work Intelligence Form (PSWIF v1.0, apps/web/forms/) asks
for less: no soil or groundwater, no contingency percentage, no drawings, only the size fields a
work type is priced by. A field that form never asks cannot be "missing" on it, so validate.py
does not require it when it is empty; when the adapter (pswif.py) does fill it, it is checked as
usual. Nothing here is ever a flag.
"""

from __future__ import annotations

from functools import cache

from drishti.cost_form import catalog

PSWIF = "PSWIF v1.0"


def _pricing_fields(family: dict) -> set[str]:
    pricing = family.get("pricing")
    rules = pricing if isinstance(pricing, list) else [pricing] if pricing else []
    out: set[str] = set()
    for r in rules:
        out |= set(r.get("product") or []) | set(r.get("sum") or [])
    return out


@cache
def not_asked(version: str | None) -> frozenset[str]:
    """Engine field ids a form version never asks (empty = not required)."""
    if version != PSWIF:
        return frozenset()
    size = set()
    for fam in catalog.load()["families"].values():
        priced = _pricing_fields(fam)
        size |= {f["id"] for f in fam.get("fields") or [] if f["id"] not in priced}
    return frozenset(size | {
        # where: the district comes from the record, not a typed code
        "district_lgd", "block", "pin", "area_type",
        # the work: asked differently or not at all
        "outside_reason", "existing_description", "existing_age_years", "existing_condition",
        "earlier_scheme", "design_standard",
        # site conditions it does not ask
        "soil", "groundwater_shallow", "site_water", "site_power", "road_distance_m",
        "demolition_m3", "utility_shifting_nos", "trees_nos",
        # lines: the item code is optional there
        "sor_code", "spec",
        # charges: it asks lump sums, other charges and how tax is treated, not percentages
        "contingency_percent", "gst_percent", "gst_amount", "labour_cess_amount",
        "royalty_amount", "other_fees_amount",
        # timing: it asks the SoR year, not the month of the prices
        "estimate_month", "sor_edition",
        # prepared: references, not uploads
        "prepared_by_role", "prepared_by_designation", "checked_by_designation",
        "estimate_pdf", "drawings", "site_photo_before", "land_noc",
    })
