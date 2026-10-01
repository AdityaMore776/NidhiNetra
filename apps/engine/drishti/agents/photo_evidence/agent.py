"""Photo Evidence engine: are this work's photos new, from its place, and from its time?

T310, merged from the 12-checker plan's B2 Photo Forensics, B3 Geo-Location and D1 Citizen
Verification (T051, 12 -> 8): all three judge the same photos. The facts come from the
engine's own readers (stamp.py over local OCR of the photo's printed GPS band, fingerprint.py),
so a photo uploaded later (by an officer or, as a demo, a citizen: `source: "citizen"`) meets
the same checks. Measured on the pilot (data/trial/photo_evidence_trial.py, FINDINGS B2/B3).

REUSE (another work carries the same file or picture)
  F1 SAME_PHOTO_ON_ANOTHER_WORK   byte-identical photo, or the same picture by fingerprint
                                  (<= 51 of 256 bits apart) on another work: 0.50
  F2 SAME_FILE_ON_ANOTHER_WORK    a byte-identical PAPER on another work: 0.40, unless it reads
                                  as a combined file (3+ pages or 50+ lines of text: a bulk
                                  invoice, a list of works), which is normal. That rule rests on
                                  5 pilot cases read by eye: stated as such.
PLACE (the stamp's coordinates against the work's own district outline)
  G1 PHOTO_OUTSIDE_DISTRICT       more than 5 km outside: 0.50 (0 of 187 pilot points)
                                  within 5 km: "at the border", never a finding
TIME (the stamp's date against the record)
  T1 PHOTO_BEFORE_RECOMMENDATION  a stamped date 7+ days before recommendation: 0.40
                                  (3 pilot works: their own photos show them finished before
                                  the MP recommended them)
Removed in T053, as notes an officer could not act on: a PIN of another district, a camera
clock ahead of the data date, a photo long after completion, the same spot the same day.

  NOT_APPLICABLE  no photo and no stamped page attached
  ASSESSED        otherwise; a photo without a readable stamp is still checked for reuse
"""

from __future__ import annotations

import time
from datetime import date

from drishti.agents.contract import AgentResult, Finding, Status
from drishti.agents.photo_evidence import geo
from drishti.agents.photo_evidence.index import PHOTO_EXT, PhotoIndex

AGENT = "photo_evidence"
VERSION = "photo-evidence-1.1.0"
QUESTION = "Are the work's photos new, from its place and from its time?"
CONFIDENCE = 0.7
EARLY_DAYS = 7
COMBINED_PAGES, COMBINED_LINES = 3, 50


def _d(x) -> date | None:
    if x is None or isinstance(x, date):
        return x
    try:
        return date.fromisoformat(str(x)[:10])
    except ValueError:
        return None


def _quiet(status: Status, text: str, t0: float) -> AgentResult:
    return AgentResult(agent=AGENT, status=status, verdict=status.value, risk=0.0,
                       confidence=0.0, hard=False, version=VERSION, headline=text,
                       duration_ms=int((time.perf_counter() - t0) * 1000))


def combined(f: dict) -> bool:
    return (f.get("pages") or 0) >= COMBINED_PAGES or (f.get("text_lines") or 0) >= COMBINED_LINES


def _reuse(work: dict, files: list[dict], photos: PhotoIndex | None) -> list[Finding]:
    out: list[Finding] = []
    if photos is None:
        return out
    me = work["work_id"]
    for f in files:
        others = [w for w in photos.same_file(f.get("sha256")) if w != me]
        is_photo = f.get("ext") in PHOTO_EXT
        if others and is_photo:
            out.append(Finding(
                "SAME_PHOTO_ON_ANOTHER_WORK",
                f"The same photo file is attached to work {', '.join(sorted(others)[:3])}. "
                "Check which work it shows and ask for a photo of this one.",
                hard=False, risk=0.50, evidence={"file": f.get("id"), "others": sorted(others),
                                                 "how": "identical file"}))
            continue
        if others and not combined(f):
            out.append(Finding(
                "SAME_FILE_ON_ANOTHER_WORK",
                f"The same paper is attached to work {', '.join(sorted(others)[:3])}, and it "
                "does not read as a combined list of works. Check which work it belongs to.",
                hard=False, risk=0.40, evidence={"file": f.get("id"), "others": sorted(others)}))
            continue
        if is_photo and f.get("phash"):
            near = [w for w in photos.same_picture(f["phash"]) if w != me]
            if near:
                out.append(Finding(
                    "SAME_PHOTO_ON_ANOTHER_WORK",
                    f"The same picture, re-saved or edited, is attached to work "
                    f"{', '.join(sorted(near)[:3])}. Check which work it shows.",
                    hard=False, risk=0.50, evidence={"file": f.get("id"), "others": sorted(near),
                                                     "how": "fingerprint"}))
    return out


def _place_time(work: dict, stamps: list[dict], as_of: date,
                photos: PhotoIndex | None) -> tuple[list[Finding], dict]:
    out: list[Finding] = []
    facts = {"stamped": len(stamps), "inside": 0, "at_border": 0}
    code = str(work.get("district_lgd") or "").zfill(3)
    outline = geo.outlines().get(code)
    rec = _d(work.get("recommended_date"))
    for s in stamps:
        lat, lon, when = s.get("lat"), s.get("lon"), _d(s.get("date"))
        if lat is not None and outline is not None:
            km = geo.km_outside(outline["geometry"], lat, lon)
            if km == 0:
                facts["inside"] += 1
            elif km <= geo.BORDER_KM:
                facts["at_border"] += 1
            else:
                where = geo.district_of_point(lat, lon) or "another place"
                out.append(Finding(
                    "PHOTO_OUTSIDE_DISTRICT",
                    f"The photo's printed GPS stamp ({lat:.5f}, {lon:.5f}) is {km:,.0f} km outside "
                    f"the work's district, in {where}. Check where the photo was taken.",
                    hard=False, risk=0.50, evidence={"lat": lat, "lon": lon, "km": round(km, 1)}))
        if when is None or when > as_of:
            continue                 # no date, or a camera clock ahead of the data: not judged
        if rec and (rec - when).days >= EARLY_DAYS:
            out.append(Finding(
                "PHOTO_BEFORE_RECOMMENDATION",
                f"The work's own photo is stamped {when.isoformat()}, {(rec - when).days:,} days "
                f"before the MP recommended it ({rec.isoformat()}). Check whether the work was "
                "already built, or the photo shows another work.",
                hard=False, risk=0.40, evidence={"date": str(when), "recommended": str(rec)}))
    # T053: weak notes removed (a PIN of another district, a clock after the data date, a
    # photo long after completion, the same spot the same day as another work): none said
    # anything an officer could act on.
    return out, facts


def assess(work: dict, as_of: date, photos: PhotoIndex | None = None) -> AgentResult:
    t0 = time.perf_counter()
    files = ((work.get("evidence") or {}).get("files")) or []
    stamps = [s for f in files for s in f.get("stamps") or []]
    photo_files = [f for f in files if f.get("ext") in PHOTO_EXT]
    if not files:
        return _quiet(Status.NOT_APPLICABLE, "No photo or paper is attached to this work on "
                      "eSAKSHI. This is not a clean chit.", t0)
    # every attached file is checked for reuse (a paper on two works too: Narmadapuram)
    findings = _reuse(work, files, photos)
    more, facts = _place_time(work, stamps, as_of, photos)
    findings += more
    findings.sort(key=lambda f: -f.risk)
    top = findings[0] if findings else None
    if not photo_files and not stamps and (top is None or top.risk == 0):
        return AgentResult(
            agent=AGENT, status=Status.ASSESSED, verdict="NO_PHOTO", risk=0.0, confidence=0.3,
            hard=False, version=VERSION,
            headline="No photo or GPS-stamped page is attached; the papers were checked for "
                     "reuse on other works and none was found.",
            limitations=["Without a photo, place and time cannot be checked."],
            evidence={"photos": 0, **facts},
            duration_ms=int((time.perf_counter() - t0) * 1000))
    if top is None or top.risk == 0:
        bits = [f"{len(photo_files)} photo(s)"]
        if stamps:
            bits.append(f"{facts['inside'] + facts['at_border']} of {len(stamps)} GPS stamp(s) "
                        "inside the work's district")
        headline = (", ".join(bits) + "; no reuse found, and the stamped dates fit the record."
                    if stamps else ", ".join(bits) + "; no reuse found. No GPS stamp to check "
                    "place or time.")
    else:
        headline = top.text
    limitations = ["eSAKSHI removes the phone's own GPS data, so place and time are read from "
                   "a GPS-camera stamp printed into the photo, when there is one.",
                   "Edited copies are matched by fingerprint (70% of edited copies in the trial); "
                   "a cropped or screenshot copy can be missed."]
    if photos is None:
        limitations.append("Other works' photos were not loaded, so reuse was not checked.")
    if any(f.get("source") == "citizen" for f in files):
        limitations.append("Includes a citizen's photo (demo): checked the same way, never "
                           "enough on its own.")
    return AgentResult(
        agent=AGENT, status=Status.ASSESSED,
        verdict=top.code if top and top.risk > 0 else "PHOTOS_FIT_THE_RECORD",
        risk=top.risk if top else 0.0, confidence=CONFIDENCE, hard=False, headline=headline,
        version=VERSION, findings=findings, limitations=limitations,
        evidence={"photos": len(photo_files), **facts},
        duration_ms=int((time.perf_counter() - t0) * 1000))
