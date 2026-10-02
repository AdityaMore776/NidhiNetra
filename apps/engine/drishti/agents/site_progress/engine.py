"""Registers the Site Progress engine (v2, T510) only when it is switched on.

Off by default: T053 removed v1 because it could only say "cannot be assessed", and AGENTS.md
rule 4 keeps a checker off until it is measured. Switch it on for a trial or, once
data/trial/site_progress_trial.py passes its go/no-go, for the live batch:

    $env:DRISHTI_SITE_PROGRESS="on"     (PowerShell)

Even then it is shown, not counted (weight 0) until its findings have been read by eye.
"""

from __future__ import annotations

import os

from drishti.agents.registry import EngineSpec
from drishti.agents.site_progress import agent


def _assess(work: dict, ctx):
    return agent.assess(work, ctx.as_of, (ctx.data or {}).get("photos"))


ENGINE = (EngineSpec(id=agent.AGENT, name="Site Progress", question=agent.QUESTION,
                     assess=_assess, weight=0.0, order=8,
                     weight_note="Shown, not counted: switched on for a trial, not yet measured "
                                 "on real photos.")
          if os.environ.get("DRISHTI_SITE_PROGRESS", "").strip().lower() == "on" else None)
