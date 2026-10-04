"""The one list of engines, found by folder, so four people can build four engines apart.

DRISHTI has four agents (owner, 3 Oct 2026; T125): Cost, Duplicate Work, Time & Rules and Site
Progress. Each is a folder
`drishti/agents/<id>/` with a module `engine.py` that defines

    ENGINE = EngineSpec(id=..., name=..., question=..., assess=<fn(work, ctx)>)

and nothing else needs editing: `discover()` imports every such module. A core
slot whose folder has no `engine.py` yet still appears, as NOT_BUILT, so every
screen shows every engine from the start and nothing pretends to have been checked.

Stored ids are stable. Assessments saved before this registry used the deck's ids;
`canonical_id()` maps them, so old rows read the same as new ones.

`assess(work, ctx)` returns an `AgentResult` (agents/contract.py): its `risk` is
the blueprint's per-work `signal` 0..1 and `evidence` its evidence dict. An engine
that raises becomes an ERROR result in the orchestrator, never a finding.
"""

from __future__ import annotations

import importlib
import pkgutil
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from drishti.agents.contract import AgentResult

Assess = Callable[[dict, Any], AgentResult]


@dataclass(frozen=True)
class EngineSpec:
    id: str
    name: str
    question: str
    assess: Assess | None = None
    # blueprint risk-score weight (fusion reads it). None = the core slot's weight; an engine
    # sets 0.0 to be shown but not counted, e.g. until it meets its accuracy target
    weight: float | None = None
    order: int = 100             # display order; core engines first
    weight_note: str = ""        # why the weight differs from the blueprint, shown on screen


# The four agents (owner, 3 Oct 2026; plan docs/plans/T120-four-agents.md; T125). Fusion v3
# counts an engine whose weight is above 0; how much a finding counts comes from its measured
# hit rate (reference/reliability.json), and a kind of finding never read counts 1 in 4, so no
# new check can queue a work on its own (proof before launch).
CORE: tuple[EngineSpec, ...] = (
    EngineSpec("cost_estimate", "Cost",
               "Is every line of the estimate fairly priced for this district, and is the whole "
               "estimate fair?", weight=0.25, order=1),
    EngineSpec("dup_split", "Duplicate Work",
               "Is this work already sanctioned here, or one job cut to stay under a limit?",
               weight=0.25, order=2),
    EngineSpec("time_rules", "Time & Rules",
               "Was it sanctioned on time, and is it being finished in a believable time?",
               weight=0.25, order=3),
    EngineSpec("site_progress", "Site Progress",
               "Do the monthly site videos show real, new work, at this work's site, for this "
               "work only?", weight=0.25, order=4),
)

# Ids used by assessments stored before the registry (the deck's four agents).
LEGACY_IDS = {"duplicate_project": "dup_split", "image_reuse": "photo_forensics"}

# Engines no longer run, so results stored before they were retired still read by name until
# the next batch replaces them: id -> (name, question). Their code stays as libraries (Time &
# Rules reads Guideline Compliance's timing rules) and for re-running the trials in FINDINGS.
RETIRED = {
    "statistical": ("Cost Anomaly (retired)", "Is the project cost unusual for similar works?"),
    "compliance": ("Guideline Compliance (retired)", "Does the work follow the MPLADS guidelines?"),
    "delay": ("Fund Flow (retired)", "Is money stuck waiting for sanction?"),
    "office_patterns": ("Office Patterns (retired)",
                        "Does the office record works in an unusual way?"),
    "photo_evidence": ("Photo Evidence (retired)",
                       "Are the work's photos its own, from its place and time?"),
    "paperwork": ("Paperwork (retired)", "Do the work's papers agree with its record?"),
}


def canonical_id(agent_id: str) -> str:
    return LEGACY_IDS.get(agent_id, agent_id)


def _found(package: str) -> dict[str, EngineSpec]:
    pkg = importlib.import_module(package)
    out: dict[str, EngineSpec] = {}
    for info in pkgutil.iter_modules(pkg.__path__):
        if not info.ispkg:
            continue
        try:
            mod = importlib.import_module(f"{package}.{info.name}.engine")
        except ModuleNotFoundError as exc:
            if exc.name == f"{package}.{info.name}.engine":
                continue          # a folder that is not an engine (yet)
            raise
        spec = getattr(mod, "ENGINE", None)
        if isinstance(spec, EngineSpec):
            out[spec.id] = spec
    return out


def discover(package: str = "drishti.agents") -> tuple[EngineSpec, ...]:
    """Every engine: the core slots (built or not) then any extra engine folders."""
    found = _found(package)
    engines: list[EngineSpec] = []
    for slot in CORE:
        spec = found.pop(slot.id, None)
        if spec is None:
            engines.append(slot)
        else:
            # the folder supplies the code; the slot keeps its blueprint weight and order
            # unless the folder sets its own
            engines.append(EngineSpec(
                id=slot.id, name=spec.name or slot.name, question=spec.question or slot.question,
                assess=spec.assess,
                weight=slot.weight if spec.weight is None else spec.weight,
                order=slot.order, weight_note=spec.weight_note))
    engines.extend(sorted(found.values(), key=lambda s: (s.order, s.id)))
    return tuple(engines)


_CACHE: tuple[EngineSpec, ...] | None = None


def engines() -> tuple[EngineSpec, ...]:
    global _CACHE
    if _CACHE is None:
        _CACHE = discover()
    return _CACHE


def by_id() -> dict[str, EngineSpec]:
    return {e.id: e for e in engines()}
