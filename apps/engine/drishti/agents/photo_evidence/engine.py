"""Registers the Photo Evidence engine (Photo Forensics + Geo-Location + citizen photos, T310).

The work's photo facts arrive with the work (work["evidence"]); every work's files and stamps,
for reuse, in ctx.data["photos"] (batch: all works; API: all works with evidence).
"""

from __future__ import annotations

from drishti.agents.photo_evidence import agent
from drishti.agents.registry import EngineSpec


def _assess(work: dict, ctx):
    return agent.assess(work, ctx.as_of, (ctx.data or {}).get("photos"))


# Shown, not counted: photos exist for the 837-work pilot only.
ENGINE = EngineSpec(id=agent.AGENT, name="Photo Evidence", question=agent.QUESTION,
                    assess=_assess, weight=0.0, order=7,
                    weight_note="Shown, not counted: photos read for the 837 pilot works only.")
