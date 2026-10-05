"""Site Progress v3: do the monthly site videos show real, new work, at this work's site, for this
work only? (owner, 3 Oct 2026; plan docs/plans/T120-four-agents.md §9; task T124)

The implementing agency films the site in the capture page (web /capture): a first visit before
work starts, one visit a month from the same fixed viewpoints, and a final visit; an officer or
someone else films unannounced check visits. The video job (drishti/video/) reads each video
once and stores readings (visits.py); this agent judges the readings, live.

FINDINGS (only facts that are yes or no, or the agency's own claim failing twice)
  FOOTAGE_USED_BEFORE          frames of this video were already seen on another work, or on an
                               earlier visit of this work (fingerprints), MIN_REUSED_FRAMES or more
  SAME_PLACE_AS_ANOTHER_WORK   this site's viewpoints show the same physical place as another
                               work's (MIN_INLIERS matching points in one geometry), and the form
                               does not name that work as the one this work continues
  NOT_FILMED_AT_THIS_SITE      the GPS points are outside the site (or the phone reported a mock
                               location) AND the views do not match this site's earlier views:
                               two independent proofs; GPS error alone never fails a video
  CLAIM_NOT_SHOWN              the agency's claim for the month is "not shown" at the same
                               viewpoints on two visits in a row (one bad month is never enough)
  COMPLETE_NOT_SHOWN           "complete" is filmed or recorded, but the final video shows
                               unfinished zones
  ALREADY_BUILT_AT_START       the first visit shows the asset already standing, for a work the
                               form calls new
NOTES, never counted: a month missed, no change for a month or two, a zone not shown, "can't
tell", a video that was not sealed or not filmed in the app (it is not accepted: retake), GPS and
views disagreeing (one proof only).

  NOT_APPLICABLE  no site visit yet (the first is filmed before work starts)
  NOT_ASSESSABLE  visits filmed, none read yet
"""

from __future__ import annotations

import time
from datetime import date

from drishti.agents.contract import AgentResult, Finding, Status
from drishti.agents.site_progress import visits as site_visits

AGENT = "site_progress"
VERSION = "site-progress-3.0.0"
QUESTION = ("Do the monthly site videos show real, new work, at this work's site, for this "
            "work only?")
CONFIDENCE = 0.8
MIN_REUSED_FRAMES = 3
MIN_INLIERS = 40
MISSED_DAYS = 45
RISK = {"FOOTAGE_USED_BEFORE": 0.8, "SAME_PLACE_AS_ANOTHER_WORK": 0.7,
        "NOT_FILMED_AT_THIS_SITE": 0.8, "CLAIM_NOT_SHOWN": 0.5, "COMPLETE_NOT_SHOWN": 0.6,
        "ALREADY_BUILT_AT_START": 0.6}
HI = {
    "FOOTAGE_USED_BEFORE": "इस वीडियो के दृश्य पहले किसी अन्य वीडियो में देखे जा चुके हैं। साइट "
                           "वीडियो इसी साइट पर नया फ़िल्माया जाना चाहिए; जाँच करें।",
    "SAME_PLACE_AS_ANOTHER_WORK": "इस साइट के दृश्य किसी अन्य कार्य की साइट जैसे ही स्थान को "
                                  "दिखाते हैं। जाँचें कि एक ही स्थल दो कार्यों के लिए तो नहीं दिखाया गया।",
    "NOT_FILMED_AT_THIS_SITE": "वीडियो की जीपीएस स्थिति साइट से बाहर है और दृश्य भी इस साइट के पहले "
                               "के दृश्यों से मेल नहीं खाते। जाँच करें।",
    "CLAIM_NOT_SHOWN": "एजेंसी का बताया गया काम लगातार दो विज़िट में उन्हीं दृश्यों पर दिखाई नहीं "
                       "देता। साइट पर जाँच करें।",
    "COMPLETE_NOT_SHOWN": "कार्य पूर्ण बताया गया है, पर अंतिम वीडियो में साइट के कुछ भाग अधूरे "
                          "दिखते हैं। जाँच करें।",
    "ALREADY_BUILT_AT_START": "पहले वीडियो में ही परिसंपत्ति बनी हुई दिखती है, जबकि फ़ॉर्म इसे नया "
                              "कार्य बताता है। जाँचें कि कार्य स्वीकृति से पहले तो नहीं हुआ।",
}
CONTINUING = ("continuation", "extension", "upgrade", "reconstruction")


def _f(code: str, text: str, **evidence) -> Finding:
    return Finding(code, text, hard=False, risk=RISK[code],
                   evidence={"message_hi": HI[code], **evidence})


KIND_WORDS = {"baseline": "first", "monthly": "monthly", "check": "check", "final": "final"}


def _when(v: site_visits.Visit) -> str:
    return f"the {KIND_WORDS.get(v.kind, v.kind)} visit of {v.captured:%d %b %Y}"


def _when_cap(v: site_visits.Visit) -> str:
    """_when at the start of a sentence (str.capitalize would lower the month)."""
    s = _when(v)
    return s[:1].upper() + s[1:]


def _declared(work: dict) -> set[str]:
    """Works the form names as the one this work continues (they may share a place)."""
    form = work.get("cost_form") if isinstance(work.get("cost_form"), dict) else {}
    part = form.get("work") if isinstance(form.get("work"), dict) else {}
    out = {part["earlier_work_id"]} if isinstance(part.get("earlier_work_id"), str) else set()
    for row in form.get("earlier_works") if isinstance(form.get("earlier_works"), list) else []:
        if isinstance(row, dict) and row.get("answer") == "continues" \
                and isinstance(row.get("earlier_work"), str):
            out.add(row["earlier_work"])
    return out


def _nature(work: dict) -> str | None:
    form = work.get("cost_form") if isinstance(work.get("cost_form"), dict) else {}
    part = form.get("work") if isinstance(form.get("work"), dict) else {}
    return part.get("nature") if isinstance(part.get("nature"), str) else None


def judge(work: dict, vs: list[site_visits.Visit], as_of: date) -> tuple[list[Finding], list[str]]:
    findings: list[Finding] = []
    notes: list[str] = []
    own = str(work.get("work_id"))
    declared = _declared(work)
    trusted = []
    for v in vs:
        if v.get("sealed") is False or v.get("in_app") is False:
            notes.append(f"{_when_cap(v)} was not accepted (not sealed or not filmed in "
                         "the app): ask for a retake.")
            continue
        if v.get("motion_consistent") is False:
            notes.append(f"{_when_cap(v)} was not accepted: the phone's own motion does "
                         "not match the motion in the picture (a screen may have been filmed). "
                         "Ask for a retake at the site.")
            continue
        trusted.append(v)

    # 1. footage seen before (on any visit, trusted or not: the frames are a fact)
    for v in vs:
        reused = [r for r in v.get("reused_from") or [] if r["frames"] >= MIN_REUSED_FRAMES]
        if reused:
            r = max(reused, key=lambda x: x["frames"])
            where = ("an earlier visit of this same work" if r["work_id"] == own
                     else f"work {r['work_id']}")
            findings.append(_f("FOOTAGE_USED_BEFORE",
                               f"{_when_cap(v)} carries {r['frames']} frames already seen "
                               f"on {where}: the same footage, not new filming. A site video must "
                               "be filmed fresh at this site; needs checking.",
                               visit=v.visit_id, reused_from=reused))
            break

    # 2. the same place as another work
    for v in trusted:
        same = [s for s in v.get("same_place_as") or []
                if s["inliers"] >= MIN_INLIERS and s["work_id"] != own
                and s["work_id"] not in declared]
        if same:
            s = max(same, key=lambda x: x["inliers"])
            findings.append(_f("SAME_PLACE_AS_ANOTHER_WORK",
                               f"The viewpoints of {_when(v)} show the same place as the site "
                               f"videos of work {s['work_id']} ({s['inliers']} matching points in "
                               "one geometry), and this work's form does not say it continues "
                               "that work. Check that one site is not shown for two works.",
                               visit=v.visit_id, same_place_as=same))
            break

    # 3. not filmed at this site: GPS and views must both disagree
    for v in trusted:
        gps_out = v.get("mock_location") is True or v.get("gps_inside") is False
        views_out = v.get("views_match_site") is False
        if gps_out and views_out:
            why = ("the phone reported a mock location" if v.get("mock_location") else
                   f"its GPS points are {v.get('gps_distance_m') or 0:,.0f} m outside the site")
            findings.append(_f("NOT_FILMED_AT_THIS_SITE",
                               f"{_when_cap(v)}: {why}, and its views do not match this "
                               "site's earlier views. Needs checking where it was filmed.",
                               visit=v.visit_id, metres=v.get("gps_distance_m"),
                               mock_location=v.get("mock_location") is True))
            break
        if gps_out or views_out:
            notes.append(f"{_when_cap(v)}: "
                         + ("the GPS is outside the site but the views match this site (GPS "
                            "error)" if gps_out else
                            "the views do not match the earlier ones but the GPS is at the site")
                         + "; one proof only, not a finding.")

    # 4. the agency's claim not shown twice in a row
    monthly = [v for v in trusted if v.kind in ("monthly", "check", "final")]
    for a, b in zip(monthly, monthly[1:], strict=False):
        if a.claim_verdict == "not_shown" and b.claim_verdict == "not_shown":
            reason = b.get("claim_reason")
            findings.append(_f("CLAIM_NOT_SHOWN",
                               f"The agency's claim is not shown at the same viewpoints on two "
                               f"visits in a row ({a.captured:%d %b %Y}: {a.claim or 'no claim'}; "
                               f"{b.captured:%d %b %Y}: {b.claim or 'no claim'})"
                               + (f". Reader: {reason}" if reason else "")
                               + ". Check at the site.", visits=[a.visit_id, b.visit_id],
                               claims=[a.claim, b.claim]))
            break
    for v in monthly:
        if v.claim_verdict == "cant_tell":
            notes.append(f"{_when_cap(v)}: the claim could not be judged from the video.")

    # 5. complete, but not shown complete
    finals = [v for v in trusted if v.kind == "final"]
    if finals and finals[-1].get("complete_shown") is False:
        v = finals[-1]
        missing = [z for z in v.get("zones_shown") or []]
        findings.append(_f("COMPLETE_NOT_SHOWN",
                           f"{_when_cap(v)} does not show the work finished in every "
                           "part of the site" + (f" ({len(missing)} parts filmed)" if missing
                                                 else "") + ". Check before it is closed.",
                           visit=v.visit_id))
    elif work.get("status") == "COMPLETED" and trusted and not finals:
        notes.append("Recorded complete, but there is no final site video yet.")

    # 6. already built at the start
    base = [v for v in trusted if v.kind == "baseline"]
    if base and base[0].get("asset_at_start") is True:
        if _nature(work) in CONTINUING:
            notes.append("The first visit shows an existing asset, as the form says (it continues "
                         "or upgrades an earlier work).")
        else:
            findings.append(_f("ALREADY_BUILT_AT_START",
                               f"{_when_cap(base[0])}, filmed before work was to start, "
                               "already shows the asset standing, but the form calls the work new. "
                               "Check whether the work was done before sanction.",
                               visit=base[0].visit_id))

    # notes: missed months, standing still
    open_work = work.get("status") != "COMPLETED"
    for a, b in zip(trusted, trusted[1:], strict=False):
        if (b.captured - a.captured).days > MISSED_DAYS:
            notes.append(f"No visit between {a.captured:%d %b %Y} and {b.captured:%d %b %Y}.")
    if open_work and trusted and (as_of - trusted[-1].captured).days > MISSED_DAYS:
        notes.append(f"No site visit since {trusted[-1].captured:%d %b %Y}: this month's is due.")
    still = [v for v in monthly if v.change == "no_change"]
    if still:
        notes.append(f"No change at the same viewpoints on {len(still)} visit"
                     f"{'s' * (len(still) != 1)} (Time & Rules weighs a long stop).")
    return findings, notes


def assess(work: dict, as_of: date) -> AgentResult:
    t0 = time.perf_counter()

    def out(status, headline, findings=(), notes=(), limitations=(), **evidence):
        findings = sorted(findings, key=lambda f: -f.risk)
        top = findings[0] if findings else None
        return AgentResult(agent=AGENT, status=status,
                           verdict=top.code if top else (status.value if status != Status.ASSESSED
                                                         else "PROGRESS_AS_SHOWN"),
                           risk=top.risk if top else 0.0,
                           confidence=CONFIDENCE if status == Status.ASSESSED else 0.0,
                           hard=False, headline=headline, version=VERSION,
                           findings=list(findings), limitations=list(limitations),
                           evidence={"notes": list(notes), **evidence},
                           duration_ms=int((time.perf_counter() - t0) * 1000))

    vs = site_visits.of(work)
    if not vs:
        return out(Status.NOT_APPLICABLE, "No site video yet: Site Progress starts with the first "
                   "visit, filmed before work begins. This is not a clean chit.")
    read = [v for v in vs if any(x not in (None, [], "") for x in v.readings.values())]
    if not read:
        return out(Status.NOT_ASSESSABLE, f"{len(vs)} site video{'s' * (len(vs) != 1)} filmed, "
                   "none read yet. This is not a clean chit.", visits=len(vs))
    findings, notes = judge(work, read, as_of)
    summary = [{"visit": v.visit_id, "kind": v.kind, "captured": v.captured.isoformat(),
                "change": v.change, "claim": v.claim_verdict,
                "zones_shown": len(v.get("zones_shown") or []),
                "viewpoints": [v.get("viewpoints_matched"), v.get("viewpoints_expected")]}
               for v in read]
    if findings:
        headline = max(findings, key=lambda f: f.risk).text
    else:
        headline = (f"{len(read)} site video{'s' * (len(read) != 1)} read: nothing the videos "
                    "show needs checking.")
    limitations = []
    if any(v.get("mock_location") is None for v in read):
        limitations.append("Filmed in a phone's browser, which cannot report a mock location or "
                           "check the phone itself; the views must match the site's own earlier "
                           "views either way.")
    return out(Status.ASSESSED, headline, findings, notes, limitations, visits=summary)
