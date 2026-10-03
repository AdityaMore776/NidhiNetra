"""The one list of engines, found by folder, so four people can build four engines apart.

The NidhiNetra blueprint has four detection engines (its "odd overall" outlier slot was
replaced by two Guideline Compliance rules, R12 and R13, in T053). Each is a folder
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


# The blueprint's slots. Weights from the spec: 0.30 / 0.20 / 0.20 / 0.20.
CORE: tuple[EngineSpec, ...] = (
    EngineSpec("compliance", "Guideline Compliance",
               "Does the work follow the MPLADS guidelines?", weight=0.30, order=1),
    # T099 (3 Oct 2026): the Cost slot is the cost estimate form's check; the old Cost Anomaly
    # (stored id `statistical`) compared amounts without a size and is retired (RETIRED below)
    EngineSpec("cost_estimate", "Cost",
               "Is the agency's cost estimate right for this size of work here?", weight=0.20,
               order=2),
    EngineSpec("dup_split", "Duplicate Work",
               "Is this work already sanctioned here, or one job cut to stay under a limit?",
               weight=0.20, order=3),
    EngineSpec("delay", "Fund Flow",          # was Delay Prediction; prediction removed (T053)
               "Is money stuck waiting for sanction?", weight=0.20, order=4),
)

# Ids used by assessments stored before the registry (the deck's four agents).
LEGACY_IDS = {"duplicate_project": "dup_split", "image_reuse": "photo_forensics"}

# Engines no longer run, so results stored before they were retired still read by name until
# the next batch replaces them: id -> (name, question).
RETIRED = {"statistical": ("Cost Anomaly (retired)",
                           "Is the project cost unusual for similar works?")}


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
