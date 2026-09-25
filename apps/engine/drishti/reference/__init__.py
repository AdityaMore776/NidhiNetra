"""Reference data shipped with the engine: taxonomy, prohibited works, clauses."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent


@lru_cache(maxsize=None)
def _load(name: str) -> dict:
    return yaml.safe_load((HERE / name).read_text(encoding="utf-8"))


def work_types() -> dict[str, dict]:
    return {w["code"]: w for w in _load("work_types.yaml")["work_types"]}


def work_type_name(code: str | None) -> str:
    if not code:
        return "unclassified"
    spec = work_types().get(code)
    return spec["name"] if spec else code.replace("_", " ").title()


def prohibited_items() -> list[dict]:
    return _load("prohibited_works.yaml")["items"]


def clause(clause_id: str) -> dict:
    for c in _load("guidelines_clauses.yaml")["clauses"]:
        if c["id"] == clause_id:
            return c
    raise KeyError(clause_id)


def citation(clause_id: str) -> str:
    return f"MPLADS Guidelines (June 2016), para {clause(clause_id)['paragraph']}"


def is_countable(code: str | None) -> bool:
    """Items bought in units (lights, borewells, computers): a work's amount depends
    on a count the published export does not carry."""
    spec = work_types().get(code or "")
    return bool(spec) and spec.get("unit") == "nos"
