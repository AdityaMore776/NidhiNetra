"""Site Progress engine: was the work physically built as claimed? (T510: B1 + plaque + B5)

Merged from the 12-checker plan's B1 Site Progress (with the plaque check) and B5 Satellite
(T051, 12 -> 8): both ask whether the thing exists on the ground, and both need inputs the
project does not have yet. This is the frame: the rules are fixed and tested with a stand-in
provider; the engine stays OFF (NOT_ASSESSABLE, weight 0) until the owner adds a vision key
(T501) and a measured test on real evidence passes (AGENTS.md rule 4).

CLAIMS (the officer's own words, never a fixed checklist: AGENTS.md section 8)
  each claim is judged against the work's photos: shown / not shown / can't tell
  NOT_SHOWN      a claim the photos plainly do not show ("roof slab cast", no roof): 0.40
  CANT_TELL      the photos cannot decide it: a note (0.0), never a finding
  a reused photo (Photo Evidence: same photo on another work) voids every "shown": a picture
  that belongs to another work confirms nothing about this one
PLAQUE
  NO_PLAQUE      the claims say the work is complete and no photo shows the MPLADS plaque
                 (CAG found 4,918 works without one): a note (0.10)
SATELLITE (B5)   only for big works (a pond or check dam, a road over 1 km, a building over
                 Rs 50 lakh) and only after its go/no-go test passes (AGENTS.md rule 9): today
                 the engine says whether a work would qualify, and that the test has not passed

  NOT_APPLICABLE  no photo attached
  NOT_ASSESSABLE  photos attached, but no vision provider is set (today, always)
"""

from __future__ import annotations

import time

from drishti.agents.contract import AgentResult, Finding, Status
from drishti.agents.photo_evidence.index import PHOTO_EXT
from drishti.agents.site_progress.provider import VisionProvider, provider
from drishti.agents.statistical.text import stated_length

AGENT = "site_progress"
VERSION = "site-progress-0.1.0"
QUESTION = "Do the photos show what the officer says was built?"
CONFIDENCE = 0.5
BIG_TYPES = {"POND", "CHECK_DAM"}
BIG_BUILDINGS = {"COMMUNITY_HALL", "SCHOOL_BUILDING", "HEALTH_BUILDING", "LIBRARY"}
BIG_BUILDING_RS = 5_000_000
BIG_ROAD_M = 1_000
PLAQUE_CLAIM = "The MPLADS plaque naming the work is visible"


def satellite_eligible(work: dict) -> bool:
    t = work.get("work_type_code") or ""
    if t in BIG_TYPES:
        return True
    if t.startswith("ROAD"):
        length = stated_length(work.get("description"), allow_km=True)
        return length == length and length >= BIG_ROAD_M      # NaN-safe
    return t in BIG_BUILDINGS and float(work.get("amount") or 0) >= BIG_BUILDING_RS


def _quiet(status: Status, text: str, t0: float, **evidence) -> AgentResult:
    return AgentResult(agent=AGENT, status=status, verdict=status.value, risk=0.0,
                       confidence=0.0, hard=False, version=VERSION, headline=text,
                       evidence=evidence, duration_ms=int((time.perf_counter() - t0) * 1000))


def assess(work: dict, vision: VisionProvider | None = None,
           reused_photo: bool = False) -> AgentResult:
    t0 = time.perf_counter()
    vision = vision or provider()
    files = ((work.get("evidence") or {}).get("files")) or []
    photos = [f for f in files if f.get("ext") in PHOTO_EXT]
    sat = {"satellite_eligible": satellite_eligible(work),
           "satellite": "go/no-go test not passed: not used"}
    if not photos:
        return _quiet(Status.NOT_APPLICABLE, "No photo is attached, so what was built cannot be "
                      "seen. This is not a clean chit.", t0, **sat)
    if vision is None:
        return _quiet(Status.NOT_ASSESSABLE, "Cannot be assessed yet: judging photos against the "
                      "officer's claims needs an AI vision reader, which is not switched on. "
                      "This is not a clean chit.", t0, photos=len(photos), **sat)
    claims = [c for c in (work.get("claims") or []) if c and c.strip()]
    if not claims:
        return _quiet(Status.NOT_ASSESSABLE, "Cannot be assessed: the officer has not written "
                      "what was built, so there is nothing to compare the photos with. This is "
                      "not a clean chit.", t0, photos=len(photos), **sat)
    judged = vision.judge(claims + [PLAQUE_CLAIM], photos)
    findings: list[Finding] = []
    shown = []
    for j in judged:
        if j.claim == PLAQUE_CLAIM:
            continue
        if j.verdict == "not_shown":
            findings.append(Finding(
                "NOT_SHOWN",
                f"The photos do not show \"{j.claim}\": {j.reason}. Needs a site check.",
                hard=False, risk=0.40, evidence={"claim": j.claim, "reason": j.reason}))
        elif j.verdict == "shown":
            shown.append(j.claim)
    if reused_photo and shown:
        findings.append(Finding(
            "CONFIRMATION_VOID", "A photo of this work is also attached to another work, so what "
            "it shows cannot confirm this work's progress.", hard=False, risk=0.20,
            evidence={"voided": shown}))
        shown = []
    plaque = next((j for j in judged if j.claim == PLAQUE_CLAIM), None)
    complete = any("complete" in c.lower() for c in claims) or work.get("status") == "COMPLETED"
    if complete and plaque is not None and plaque.verdict == "not_shown":
        findings.append(Finding(
            "NO_PLAQUE", "No photo shows the MPLADS plaque on a work said to be complete.",
            hard=False, risk=0.10, evidence={"reason": plaque.reason}))
    findings.sort(key=lambda f: -f.risk)
    top = findings[0] if findings else None
    return AgentResult(
        agent=AGENT, status=Status.ASSESSED, verdict=top.code if top else "CLAIMS_SHOWN",
        risk=top.risk if top else 0.0, confidence=CONFIDENCE, hard=False,
        headline=top.text if top else f"The photos show {len(shown)} of {len(claims)} claim(s); "
        "none is contradicted.",
        version=VERSION, findings=findings,
        limitations=[f"Judged by {getattr(vision, 'name', 'a vision provider')}; a photo shows "
                     "one moment and one angle, so \"can't tell\" is never a finding."],
        evidence={"claims": len(claims), "shown": len(shown),
                  "judgements": [j.__dict__ for j in judged], **sat},
        duration_ms=int((time.perf_counter() - t0) * 1000))
