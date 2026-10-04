"""Site Progress v2 engine: do the work's photos show what its record says was built? (T510)

v1 (1 Oct 2026) was a frame waiting for a paid vision key, so it could only ever say "cannot be
assessed" and was removed in T053. v2 reads photos with free, local models, offline, once per
photo (readers.py, data/build_site_observations.py), and keeps only readings: what the photo
shows for every kind of asset (observe.py), and an MPLADS plaque's dates (plaque.py). This
engine judges the record's own words (claims.py) against those readings, live, for any work.

PHOTOS THAT CONFIRM NOTHING (Photo Evidence's own facts, so the two engines never disagree)
  on another work                the same file or picture is attached to another work
  outside the district           its GPS stamp is more than 5 km outside the work's district
  stamped before recommendation  its stamp is 7+ days before the MP recommended the work
  Such a photo neither shows the asset nor counts against it.

CLAIMS (shown / not shown / can't tell; "can't tell" is never a finding)
  asset   shown      any usable photo shows the finished asset
          not shown  recorded complete, at least 2 usable photos read as an unbuilt site (bare
                     ground, work in progress), none shows the asset, and none of those 2 is a
                     progress photo stamped 30+ days before completion
                     -> ASSET_NOT_SHOWN, 0.40
          for lights, pumps, goods and grounds the asset may simply be out of frame: never
          "not shown" from a zero-shot reading
  field / length / count   judged only by a vision-language reader (the owner's key, T501);
                     its "not shown" -> CLAIM_NOT_SHOWN, 0.40; otherwise "can't tell"
PLAQUE
  a plaque naming the scheme, dated (start or completion) 7+ days before the recommendation
                     -> PLAQUE_DATED_BEFORE_RECOMMENDATION, 0.40 (FINDINGS B3, Chittaurgarh)
  no plaque in any photo is a fact in the headline, never a finding: a photo may not frame it

  NOT_APPLICABLE  no photo attached
  NOT_ASSESSABLE  photos attached, none read yet
Shown, not counted (weight 0) and switched off (engine.py) until data/trial/site_progress_trial.py
measures it on the pilot's real photos (AGENTS.md rule 4).
"""

from __future__ import annotations

import time
from datetime import date

from drishti import reference
from drishti.agents import evidence
from drishti.agents.contract import AgentResult, Finding, Status, check_plain_language
from drishti.agents.photo_evidence import geo
from drishti.agents.photo_evidence.index import PhotoIndex
from drishti.agents.site_progress import observe
from drishti.agents.site_progress.claims import Claim, claims_of

AGENT = "site_progress"
VERSION = "site-progress-2.0.0"
QUESTION = "Do the work's photos show what its record says was built?"
CONFIDENCE = 0.5
NOT_SHOWN_RISK = 0.40
PLAQUE_RISK = 0.40
MIN_NOT_BUILT = 2
PROGRESS_DAYS = 30
EARLY_DAYS = 7


def _d(x) -> date | None:
    if x is None or isinstance(x, date):
        return x
    try:
        return date.fromisoformat(str(x)[:10])
    except ValueError:
        return None


def _quiet(status: Status, text: str, t0: float, **evidence) -> AgentResult:
    return AgentResult(agent=AGENT, status=status, verdict=status.value, risk=0.0,
                       confidence=0.0, hard=False, version=VERSION, headline=text,
                       evidence=evidence, duration_ms=int((time.perf_counter() - t0) * 1000))


def km_outside(work: dict, lat: float, lon: float) -> float | None:
    outline = geo.outlines().get(str(work.get("district_lgd") or "").zfill(3))
    return None if outline is None else geo.km_outside(outline["geometry"], lat, lon)


def void_reason(work: dict, f: dict, photos: PhotoIndex | None) -> str | None:
    """Why a photo cannot speak for this work, from Photo Evidence's facts; None if it can."""
    me = work.get("work_id")
    if photos is not None:
        if any(w != me for w in photos.same_file(f.get("sha256"))):
            return "on another work"
        if f.get("phash") and any(w != me for w in photos.same_picture(f["phash"])):
            return "on another work"
    rec = _d(work.get("recommended_date"))
    for s in f.get("stamps") or ():
        if s.get("lat") is not None and s.get("lon") is not None:
            km = km_outside(work, s["lat"], s["lon"])
            if km is not None and km > geo.BORDER_KM:
                return "outside the district"
        when = _d(s.get("date"))
        if rec and when and (rec - when).days >= EARLY_DAYS:
            return "stamped before the recommendation"
    return None


def _stamp_date(f: dict) -> date | None:
    days = [_d(s.get("date")) for s in f.get("stamps") or ()]
    days = [d for d in days if d]
    return max(days) if days else None


def _asset(claim: Claim, usable: list[dict], done: date | None) -> tuple[str, dict]:
    reads = {f["id"]: observe.read(f.get("site"), claim.group) for f in usable}
    if any(r == "shows" for r in reads.values()):
        return "shown", reads
    can_be_absent = bool(observe.groups().get(claim.group, {}).get("not_built"))
    against = []
    for f in usable:
        if reads[f["id"]] != "not_built":
            continue
        when = _stamp_date(f)
        if done and when and (done - when).days >= PROGRESS_DAYS:
            continue                       # a progress photo: the site before it was finished
        against.append(f["id"])
    if can_be_absent and len(against) >= MIN_NOT_BUILT:
        return "not_shown", reads
    return "cant_tell", reads


def _plain(text: str, fallback: str) -> str:
    """A reader's reason, if it is plain language; the fallback otherwise."""
    try:
        return check_plain_language(text) if text else fallback
    except ValueError:
        return fallback


def assess(work: dict, as_of: date, photos: PhotoIndex | None = None) -> AgentResult:
    t0 = time.perf_counter()
    files = evidence.photos(work)           # every part checked once (agents/evidence.py)
    judged = {j["claim"]: j for j in evidence.judgements(work)}
    if not files:
        return _quiet(Status.NOT_APPLICABLE, "No photo is attached, so what was built cannot "
                      "be seen. This is not a clean chit.", t0)
    read = [f for f in files if (f["site"] or {}).get("version") == observe.VERSION]
    if not read and not judged:
        return _quiet(Status.NOT_ASSESSABLE, "The work's photos have not been read yet, so what "
                      "they show cannot be compared with the record. This is not a clean chit.",
                      t0, photos=len(files))

    voided = {f["id"]: why for f in files if (why := void_reason(work, f, photos))}
    usable = [f for f in read if f["id"] not in voided]
    done = _d(work.get("completed_date"))
    rec = _d(work.get("recommended_date"))
    wname = reference.work_type_name(work.get("work_type_code")).lower()
    findings: list[Finding] = []
    verdicts: dict = {}
    reads: dict = {}

    for c in claims_of(work):
        j = judged.get(c.text)
        if c.kind == "asset":
            v, reads = _asset(c, usable, done)
            if j and j.get("verdict") in ("shown", "not_shown") and v != "shown":
                v = j["verdict"]                    # a reader that saw the claim itself
            verdicts["asset"] = v
            if v == "not_shown":
                n = len(usable)
                bare = sum(1 for r in reads.values() if r == "not_built")
                findings.append(Finding(
                    "ASSET_NOT_SHOWN",
                    f"Recorded complete, but none of the {n} usable site photo(s) shows the "
                    f"{wname}; {bare} read as an unbuilt site (bare ground or work in progress). "
                    "Needs a site check before the work is closed.",
                    hard=False, risk=NOT_SHOWN_RISK,
                    evidence={"claim": c.text, "photos": n, "unbuilt": bare}))
            continue
        v = j.get("verdict") if j and j.get("verdict") in ("shown", "not_shown") else "cant_tell"
        verdicts.setdefault(c.kind, {})[c.text] = v
        if v == "not_shown":
            reason = _plain(str(j.get("reason") or ""), "the photos do not show it")
            findings.append(Finding(
                "CLAIM_NOT_SHOWN",
                f"The photos do not show \"{c.text}\": {reason}. Needs a site check.",
                hard=False, risk=NOT_SHOWN_RISK,
                evidence={"claim": c.text, "reader": j.get("reader"), "reason": reason}))

    plaques = [f["site"]["plaque"] for f in usable if (f.get("site") or {}).get("plaque")]
    seen = [p for p in plaques if p.get("scheme")]
    for p in seen:
        # a completion date before the recommendation says most: the work was already done
        dates = sorted(p.get("dates") or (), key=lambda x: x.get("label") != "completion")
        for item in dates:
            when = _d(item.get("date"))
            if item.get("label") not in ("start", "completion") or not (rec and when):
                continue
            if (rec - when).days >= EARLY_DAYS:
                findings.append(Finding(
                    "PLAQUE_DATED_BEFORE_RECOMMENDATION",
                    f"The MPLADS plaque in the photo gives the {item['label']} date "
                    f"{when.isoformat()}, {(rec - when).days:,} days before the MP recommended "
                    f"the work ({rec.isoformat()}). Check whether the portal entry was late or a "
                    "finished work was put forward as a new one.",
                    hard=False, risk=PLAQUE_RISK,
                    evidence={"label": item["label"], "date": when.isoformat(),
                              "recommended": rec.isoformat()}))
                break
    plaque = "shown" if seen else "not seen"

    findings.sort(key=lambda f: -f.risk)
    top = findings[0] if findings else None
    if top is not None:
        headline = top.text
    else:
        asset = verdicts.get("asset")
        bits = [f"{len(usable)} of {len(files)} photo(s) read and usable"]
        if asset == "shown":
            bits.append(f"they show the {wname}")
        elif asset == "cant_tell":
            bits.append(f"they neither show the {wname} clearly nor show it missing")
        elif asset is None:
            bits.append("the record does not yet say anything was built")
        bits.append("the MPLADS plaque is visible" if seen else
                    "no photo shows the MPLADS plaque (ask for one at inspection)")
        headline = "; ".join(bits) + "."
    limitations = [
        "Photos are read by a local model that names what a photo shows; it cannot count or "
        "measure, so lengths and counts stay \"can't tell\" unless a vision-language reader "
        "judged them.",
        "A photo shows one moment from one angle: \"can't tell\" is never a finding."]
    if voided:
        limitations.append(f"{len(voided)} photo(s) not used: they are on another work, outside "
                           "the district or stamped before the recommendation (see Photo "
                           "Evidence).")
    if photos is None:
        limitations.append("Other works' photos were not loaded, so reuse was not ruled out.")
    return AgentResult(
        agent=AGENT, status=Status.ASSESSED,
        verdict=top.code if top else "NOTHING_CONTRADICTED", risk=top.risk if top else 0.0,
        confidence=CONFIDENCE, hard=False, headline=headline, version=VERSION,
        findings=findings, limitations=limitations,
        evidence={"photos": len(files), "read": len(read), "usable": len(usable),
                  "voided": voided, "claims": verdicts, "plaque": plaque,
                  "readings": {k: v for k, v in reads.items() if v}},
        duration_ms=int((time.perf_counter() - t0) * 1000))
