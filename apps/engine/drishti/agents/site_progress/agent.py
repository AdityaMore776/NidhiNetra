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
                               two independent proofs; GPS error alone never fails a video,
                               and the GPS must be FAR_M+ out (T137: jitter near the site with
                               lost views is unusable, not "elsewhere")
  CLAIM_NOT_SHOWN              the agency's claim for the month is "not shown" at the same
                               viewpoints on two visits in a row (one bad month is never enough)
  COMPLETE_NOT_SHOWN           "complete" is filmed or recorded, but the final video shows
                               unfinished zones
  ALREADY_BUILT_AT_START       the first visit shows the asset already standing, for a work the
                               form calls new
  NO_SITE_VIDEO                (T135) a work with a form, sanctioned, NO_VIDEO_DAYS past its
                               planned start, and not one video accepted (never filmed, or every
                               upload unsealed): never filming was the way past every other check
  SITE_NOT_AT_FORM_PIN         (T135) two or more videos, each filmed about the same distance
                               (100 m or more) from the form's map pin, at views that match the
                               site's own: the work is not where the form says, and the form's pin
                               is what Duplicate Work compared
  SITE_VIDEOS_UNUSABLE         (T136, T137) 4 of the last 5 accepted videos (or every one so
                               far, from the third) cannot show this site's progress (too dark
                               or short, the fixed viewpoints not filmed, or views that do not
                               match while the GPS is at or near the site): a poor video now and
                               then is forgiven, filming badly every month would dodge every check
  COMPLETE_NOT_FILMED          (T137) recorded complete FINAL_GRACE_DAYS+ ago, videos filmed, but
                               no final video showing the finished work
  FIRST_FILMED_FINISHED        (T139) no first visit before work, and the first video accepted is
                               the final one (or already shows the work complete or standing),
                               for a work the form calls new: nothing shows the asset is new
ROOM FOR ERROR (T136): a dark or short video, weak GPS, a viewpoint missed or skipped, a month
missed, are notes; a poor video is never a proof that work is not there, nor that it was filmed
elsewhere.
A claim "not shown" twice with only "can't tell" between counts as twice in a row (T135: slipping
a "can't tell" between them reset the count). Videos dated after today are not counted.
NOTES, never counted: a month missed, no change for a month or two, a zone not shown, "can't
tell", a video that was not sealed or not filmed in the app (it is not accepted: retake), GPS and
views disagreeing (one proof only).

  NOT_APPLICABLE  no site visit yet (the first is filmed before work starts)
  NOT_ASSESSABLE  visits filmed, none read yet
"""

from __future__ import annotations

import re
import statistics
import time
from datetime import date, timedelta

from drishti.agents.contract import AgentResult, Finding, Status
from drishti.agents.site_progress import spots
from drishti.agents.site_progress import visits as site_visits

AGENT = "site_progress"
VERSION = "site-progress-3.4.0"
QUESTION = ("Do the monthly site videos show real, new work, at this work's site, for this "
            "work only?")
CONFIDENCE = 0.8
MIN_REUSED_FRAMES = site_visits.MIN_REUSED_FRAMES
MIN_INLIERS = site_visits.MIN_INLIERS
MISSED_DAYS = 45
NO_VIDEO_DAYS = 60            # past the planned start (capped) with no accepted video
NO_VIDEO_RISK = 0.4
PIN_OFF_METRES = 100.0        # filmed this far from the pin, consistently: the pin is elsewhere
PIN_OFF_RISK = 0.5
START_CAP_DAYS = 183          # a declared start counts at most this long after the sanction
UNUSABLE_OF, UNUSABLE_LAST = 4, 5   # this many of the latest videos cannot show the site (T137)
UNUSABLE_ALL_FROM = 3         # ... or every video so far, from the third
UNUSABLE_RISK = 0.4           # as NO_SITE_VIDEO: the same way past every other check
FINAL_GRACE_DAYS = 30         # recorded complete: the final video is due within this many days
OFF_SPOT_M = 20.0             # T158: a viewpoint filmed this far from its spot is noted
RISK = {"FOOTAGE_USED_BEFORE": 0.8, "SAME_PLACE_AS_ANOTHER_WORK": 0.7,
        "NOT_FILMED_AT_THIS_SITE": 0.8, "CLAIM_NOT_SHOWN": 0.5, "COMPLETE_NOT_SHOWN": 0.6,
        "ALREADY_BUILT_AT_START": 0.6, "NO_SITE_VIDEO": NO_VIDEO_RISK,
        "SITE_NOT_AT_FORM_PIN": PIN_OFF_RISK, "SITE_VIDEOS_UNUSABLE": UNUSABLE_RISK,
        "COMPLETE_NOT_FILMED": NO_VIDEO_RISK, "FIRST_FILMED_FINISHED": NO_VIDEO_RISK}
HI = {
    "FIRST_FILMED_FINISHED": "पहला साइट वीडियो ही कार्य को पूरा दिखाता है, और कार्य शुरू होने से "
                             "पहले कोई वीडियो नहीं फ़िल्माया गया: कुछ भी नहीं दिखाता कि परिसंपत्ति "
                             "नई है। जाँचें कि यह स्वीकृति से पहले या किसी अन्य योजना में तो नहीं "
                             "बनी।",
    "COMPLETE_NOT_FILMED": "कार्य पूर्ण दर्ज है, पर तब से कोई अंतिम साइट वीडियो पूरा कार्य नहीं "
                           "दिखाता। अंतिम वीडियो माँगें और बंद करने से पहले जाँच करें।",
    "SITE_VIDEOS_UNUSABLE": "हाल के अधिकांश साइट वीडियो से साइट की प्रगति नहीं देखी जा सकती (बहुत "
                            "अँधेरा, बहुत छोटा, या तय दृश्य-बिंदु नहीं फ़िल्माए गए)। एजेंसी से दिन के उजाले में "
                            "हर तय दृश्य-बिंदु का वीडियो माँगें।",
    "NO_SITE_VIDEO": "स्वीकृति और नियोजित आरंभ के बाद भी कोई साइट वीडियो स्वीकार नहीं हुआ। एजेंसी "
                     "से वीडियो माँगें और स्थल की जाँच करें।",
    "SITE_NOT_AT_FORM_PIN": "साइट वीडियो फ़ॉर्म के मानचित्र पिन से लगभग एक ही दूरी पर फ़िल्माए गए "
                            "हैं: कार्य फ़ॉर्म में बताए स्थान पर नहीं है। स्थान की जाँच करें।",
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
# a claim that names no stage or quantity: the video can neither show it nor not
VAGUE = re.compile(r"^(?:the\s+)?(?:works?\s+)?(?:is\s+)?(?:in\s+progress|on\s*going|going\s+on|"
                   r"progress(?:ing)?|as\s+per\s+(?:plan|schedule|estimate)|continu\w*|"
                   r"under\s+(?:construction|progress)|started|in\s+hand|na|n/a|nil|none|"
                   r"work|progress|-+)$", re.IGNORECASE)


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


def _at(v: site_visits.Visit) -> str:
    """" at spot v2" / " at spots v2, v3": where a claim was not shown (T158)."""
    ids = v.get("claim_spots_not_shown") or []
    return f" at spot{'s' * (len(ids) > 1)} {', '.join(ids)}" if ids else ""


def _int(n) -> int | None:
    return int(n) if isinstance(n, float) else None


def _spot_notes(v: site_visits.Visit) -> list[str]:
    """T158: fewer spots than the work needs, a viewpoint filmed far from its spot, a short pan,
    road stretches asked but not filmed. Each a note: the pictures decide, never these."""
    out = []
    needed, filmed = v.get("spots_needed"), v.get("spots_filmed")
    if needed and filmed is not None and filmed < needed:
        out.append(f"{_when_cap(v)}: {filmed:.0f} of the {needed:.0f} spots this work needs were "
                   "filmed (its size needs a pair of spots for every 40 m), so part of the work "
                   "was not judged. Ask for the missing spots on the next visit.")
    for vid, m in sorted((v.get("spot_offsets_m") or {}).items()):
        if m > OFF_SPOT_M:
            out.append(f"{_when_cap(v)}: viewpoint {vid} was filmed about {m:.0f} m from where it "
                       "was first filmed (GPS); its pictures decide whether it is the same view.")
    for vid, c in sorted((v.get("spot_coverage") or {}).items()):
        if c < spots.COVER_GOOD:
            out.append(f"{_when_cap(v)}: at viewpoint {vid}, {c:.0%} of the first visit's view "
                       "was panned across; film the whole view next time.")
    missed = v.get("stretches_missed") or []
    if missed:
        out.append(f"{_when_cap(v)}: stretch{'es' * (len(missed) > 1)} {', '.join(missed)} "
                   "of the line, asked for when filming started, were not filmed.")
    return out


def _no_video(work: dict, as_of: date, vs: list[site_visits.Visit]) -> Finding | None:
    """NO_SITE_VIDEO (module note), or None."""
    form = work.get("cost_form")
    san = _day(work.get("sanction_date"))
    if not isinstance(form, dict) or san is None or any(site_visits.accepted(v) for v in vs):
        return None
    timing = form.get("timing") if isinstance(form.get("timing"), dict) else {}
    declared = _month_start(timing.get("start_month"))
    start = san if declared is None else max(san, min(declared,
                                                       san + timedelta(days=START_CAP_DAYS)))
    late = (as_of - start).days
    filmed = (f" ({len(vs)} filmed, none accepted: not sealed, or not filmed in the app)"
              if vs else "")
    done = _day(work.get("completed_date"))
    if done is not None and san <= done <= as_of:
        # recorded complete with not one accepted video: no wait (T136: "complete" just past
        # Time & Rules' early line, checked the next day, went unasked for two months)
        return _f("NO_SITE_VIDEO",
                  f"Recorded complete on {done:%d %b %Y}, {(done - san).days:,} days after its "
                  f"sanction, but no site video was ever accepted{filmed}. A work with a form "
                  "is filmed before it starts and every month: ask the agency for the videos, "
                  "and check the site before it is closed.", days=max(late, 0),
                  filmed=len(vs), completed=done.isoformat())
    if late <= NO_VIDEO_DAYS:
        return None
    return _f("NO_SITE_VIDEO",
              f"Sanctioned on {san:%d %b %Y} and {late:,} days past its planned start "
              f"({start:%d %b %Y}), but no site video has been accepted yet{filmed}. The first "
              "visit is filmed before work begins and then every month: ask the agency for the "
              "videos, and check the site.", days=late, filmed=len(vs))


def _day(v) -> date | None:
    if isinstance(v, date):
        return v
    if isinstance(v, str) and len(v) >= 10:
        try:
            return date.fromisoformat(v[:10])
        except ValueError:
            return None
    return None


def _month_start(v) -> date | None:
    if isinstance(v, str) and len(v) >= 7:
        try:
            return date(int(v[:4]), int(v[5:7]), 1)
        except ValueError:
            return None
    return None


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

    # 3. not filmed at this site: GPS and views must both disagree (a poor video proves nothing;
    #    the GPS must be far out, T137: near the site it is jitter, and the views are unusable)
    for v in trusted:
        gps_out = v.get("mock_location") is True or v.get("gps_inside") is False
        views_out = v.get("views_match_site") is False and v.get("quality_ok") is not False
        if site_visits.far_out(v) and views_out:
            why = ("the phone reported a mock location" if v.get("mock_location") else
                   f"its GPS points are {v.get('gps_distance_m') or 0:,.0f} m outside the site")
            findings.append(_f("NOT_FILMED_AT_THIS_SITE",
                               f"{_when_cap(v)}: {why}, and its views do not match this "
                               "site's earlier views. Needs checking where it was filmed.",
                               visit=v.visit_id, metres=v.get("gps_distance_m"),
                               mock_location=v.get("mock_location") is True))
            break
        if gps_out and v.get("views_match_site") is not False:
            # (views out with the GPS at the site is told in the room-for-error notes below)
            notes.append(f"{_when_cap(v)}: the GPS is outside the site but the views do not "
                         "say it is elsewhere (GPS error); one proof only, not a finding.")

    # 4. the agency's claim not shown twice in a row ("can't tell" between them does not reset)
    monthly = [v for v in trusted if v.kind in ("monthly", "check", "final")]
    prev = None
    for b in monthly:
        if b.claim_verdict == "shown":
            prev = None
            continue
        if b.claim_verdict != "not_shown" or b.get("quality_ok") is False:
            continue                    # a dark or short video cannot show a claim is missing
        if prev is None:
            prev = b
            continue
        a, reason = prev, b.get("claim_reason")
        findings.append(_f("CLAIM_NOT_SHOWN",
                           f"The agency's claim is not shown at the same viewpoints on two "
                           f"visits in a row ({a.captured:%d %b %Y}: {a.claim or 'no claim'}"
                           f"{_at(a)}; {b.captured:%d %b %Y}: {b.claim or 'no claim'}{_at(b)})"
                           + (f". Reader: {reason}" if reason else "")
                           + ". Check at the site.", visits=[a.visit_id, b.visit_id],
                           claims=[a.claim, b.claim]))
        break
    for v in monthly:
        if v.claim_verdict == "cant_tell":
            notes.append(f"{_when_cap(v)}: the claim could not be judged from the video.")
    vague = [v for v in monthly if v.claim and VAGUE.match(v.claim.strip(" .!"))]
    if len(vague) >= 2:
        notes.append(f"{len(vague)} monthly claims are vague ({vague[0].claim!r}): ask the agency "
                     "to name what was built since the last visit (a stage or a quantity), so "
                     "the video can show it or not.")

    # 4b. filmed somewhere other than the form's pin, every time (T135)
    off = [v for v in trusted if v.get("gps_inside") is False and v.get("mock_location") is not True
           and v.get("views_match_site") is not False
           and (v.get("gps_distance_m") or 0) >= PIN_OFF_METRES]
    gps_read = [v for v in trusted if v.get("gps_inside") is not None]
    if len(off) >= 2 and len(off) * 2 >= len(gps_read):
        ds = [v.get("gps_distance_m") for v in off]
        mid = statistics.median(ds)
        if all(abs(d - mid) <= 0.3 * mid + 30 for d in ds):
            findings.append(_f("SITE_NOT_AT_FORM_PIN",
                               f"{len(off)} site videos ({', '.join(v.visit_id for v in off)}) are "
                               f"each filmed about {mid:,.0f} m from the form's map pin, at views "
                               "that match one another: the work is not where the form puts it. "
                               "Check the location (the form's pin decides which earlier works it "
                               "was compared with).", visits=[v.visit_id for v in off],
                               metres=round(mid, 1)))

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
        done = _day(work.get("completed_date"))
        if done is not None and (as_of - done).days > FINAL_GRACE_DAYS:
            # T137: two honest months filmed, then "complete" with no final video was a note
            findings.append(_f("COMPLETE_NOT_FILMED",
                               f"Recorded complete on {done:%d %b %Y}, but in the "
                               f"{(as_of - done).days:,} days since, no final site video has "
                               "shown the finished work (every fixed viewpoint). The last video "
                               f"is {_when(trusted[-1])}. Ask for the final video, and check "
                               "before it is closed.", days=(as_of - done).days,
                               visit=trusted[-1].visit_id))
        else:
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
    elif not base and trusted and _nature(work) not in CONTINUING:
        # 6b. first filmed already finished (T139): on Jaunpur's real dates a light is installed
        #     and closed within the month, and with no first video "already built at the start"
        #     could never be asked: an old asset filmed once, as the final video, passed as new
        first = trusted[0]
        if (first.kind == "final" or first.get("complete_shown") is True
                or first.get("asset_at_start") is True):
            findings.append(_f("FIRST_FILMED_FINISHED",
                               f"The first site video ({_when(first)}) already shows the work "
                               "finished, and none was filmed before work started, so nothing "
                               "shows the asset is new. Check that it was not built before "
                               "sanction or under another scheme.", visit=first.visit_id))

    # 7. room for error (T136): one poor video is a note; the latest two in a row are a question
    poor = [(v, site_visits.unusable(v)) for v in trusted]
    for v, why in poor:
        if why:
            notes.append(f"{_when_cap(v)} cannot show the site's progress ({why}): the next "
                         "visit should film every fixed viewpoint in daylight, walking slowly. "
                         "One such video is not a finding.")
        elif v.get("viewpoints_expected") and v.get("viewpoints_matched") is not None \
                and v.get("viewpoints_matched") < v.get("viewpoints_expected"):
            notes.append(f"{_when_cap(v)} found {v.get('viewpoints_matched'):.0f} of the site's "
                         f"{v.get('viewpoints_expected'):.0f} viewpoints again; the others are "
                         "compared next time.")
        if v.get("viewpoints_skipped"):
            notes.append(f"{_when_cap(v)}: viewpoint{'s' * (len(v.get('viewpoints_skipped')) > 1)}"
                         f" {', '.join(v.get('viewpoints_skipped'))} could not be filmed, the "
                         "person said (blocked or unsafe).")
        if v.get("gps_weak") is True:
            notes.append(f"{_when_cap(v)}: the phone's GPS was too weak to place it; the views "
                         "decide where it was filmed.")
        notes.extend(_spot_notes(v))
    # T137: UNUSABLE_OF of the last UNUSABLE_LAST (two in a row asked 1 honest work in 4 a year,
    # checked monthly at the assumed error rates), or every video so far from the third
    last = poor[-UNUSABLE_LAST:]
    bad = [(v, why) for v, why in last if why]
    every = len(poor) >= UNUSABLE_ALL_FROM and all(why for _v, why in poor)
    if (len(bad) >= UNUSABLE_OF or every) \
            and not any(f.code == "NOT_FILMED_AT_THIS_SITE" for f in findings):
        which = (f"all {len(poor)} site videos so far" if every and len(poor) < UNUSABLE_LAST
                 else f"{len(bad)} of the last {len(last)} site videos")
        findings.append(_f("SITE_VIDEOS_UNUSABLE",
                           f"{which[:1].upper()}{which[1:]} cannot show this site's progress ("
                           + "; ".join(f"{v.captured:%d %b %Y}: {why}" for v, why in bad)
                           + "). A poor video now and then is forgiven; this many leave the work "
                           "unchecked. Ask the agency to film every fixed viewpoint in daylight, "
                           "and check the site.", visits=[v.visit_id for v, _w in bad],
                           why=[why for _v, why in bad]))

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
    early = [f"{_when_cap(v)} is dated after today, so it is not counted: check the phone's "
             "clock or the upload." for v in vs if v.captured > as_of]
    vs = [v for v in vs if v.captured <= as_of]
    missing = _no_video(work, as_of, vs)
    if not vs:
        if missing:
            return out(Status.ASSESSED, missing.text, [missing], early)
        return out(Status.NOT_APPLICABLE, "No site video yet: Site Progress starts with the first "
                   "visit, filmed before work begins. This is not a clean chit.", notes=early)
    read = [v for v in vs if any(x not in (None, [], "", {}) for x in v.readings.values())]
    if not read:
        return out(Status.NOT_ASSESSABLE, f"{len(vs)} site video{'s' * (len(vs) != 1)} filmed, "
                   "none read yet. This is not a clean chit.", visits=len(vs))
    findings, notes = judge(work, read, as_of)
    notes = early + notes
    if missing:
        findings.append(missing)
    summary = [{"visit": v.visit_id, "kind": v.kind, "captured": v.captured.isoformat(),
                "change": v.change, "claim": v.claim_verdict,
                "zones_shown": len(v.get("zones_shown") or []),
                "viewpoints": [v.get("viewpoints_matched"), v.get("viewpoints_expected")],
                "spots": {"needed": _int(v.get("spots_needed")),
                          "filmed": _int(v.get("spots_filmed")),
                          "verdicts": v.get("spot_verdicts") or {}}}
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
