"""Registers the Site Progress engine (B1 + plaque + B5 satellite, T510).

Off until the owner switches on a vision provider (T501) and its measured test passes: it
reports NOT_ASSESSABLE on works with photos and carries no weight.
"""

from __future__ import annotations

from drishti.agents.registry import EngineSpec
from drishti.agents.site_progress import agent


def _assess(work: dict, ctx):
    photos = (ctx.data or {}).get("photos")
    reused = False
    if photos is not None:
        me = work.get("work_id")
        for f in ((work.get("evidence") or {}).get("files")) or []:
            if any(w != me for w in photos.same_file(f.get("sha256"))):
                reused = True
    return agent.assess(work, reused_photo=reused)


ENGINE = EngineSpec(id=agent.AGENT, name="Site Progress", question=agent.QUESTION,
                    assess=_assess, weight=0.0, order=8,
                    weight_note="Off: needs the owner's AI vision key and a measured test.")
