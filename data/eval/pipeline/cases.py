"""The four agents together (T168): the risk score's band for every case of the three agents' sets.

Every case of data/eval/{dup_split,time_rules,site_progress}/ runs through all four agents and the
risk fusion (orchestrator.assess_work), so another agent's finding on the same filing counts too.
The band must say what the case is:

  fraud / evasion                      MEDIUM or above (in the review queue)
  honest / edge, never "check this"    LOW (another agent must not drag an honest filing in)
  honest / edge that may be checked    LOW or MEDIUM (a follow-up), never HIGH or CRITICAL
  broken                               any band: "couldn't check" carries no weight
"""

from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
import world as W  # noqa: E402

QUEUE = ("MEDIUM", "HIGH", "CRITICAL")
AGENTS = ("dup_split", "time_rules", "site_progress")


def _bands(c: W.Case) -> tuple[str, ...]:
    if c.truth in ("fraud", "evasion"):
        return QUEUE
    if c.truth == "broken":
        return ("LOW", *QUEUE)
    return ("LOW", "MEDIUM") if "check" in c.allowed else ("LOW",)


def _from(set_name: str) -> list[W.Case]:
    out = []
    for agent in AGENTS:
        folder = W.ROOT / "data" / "eval" / agent
        mod = "cases" if set_name == "main" else set_name
        if not (folder / f"{mod}.py").exists():
            continue
        for c in W.load(folder / f"{mod}.py", f"{agent}_{mod}").cases():
            if c.scope != "self":
                continue
            bands = _bands(c)
            out.append(replace(c, id=f"P:{c.id}", agent="pipeline", allowed=bands,
                               ideal=bands[0] if c.truth not in ("fraud", "evasion")
                               else "MEDIUM"))
    return out


def cases() -> list[W.Case]:
    return _from("main")
