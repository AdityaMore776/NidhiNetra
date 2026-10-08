"""One site visit's readings (plan T120 §9.4), from its video and capture log.

The capture log (web /capture) travels with the video:
    {"in_app": true, "sealed_sha256": "<hash computed when filming ended>",
     "viewpoints": [{"id": "v1", "t0": 3.0, "t1": 9.5}, ...],      # seconds into the video
     "gps":        [{"t": 1.0, "lat": .., "lon": .., "accuracy": 6, "mock": false}, ...],
     "motion":     [{"t": 1.0, "rot": 12.5}, ...]}                   # rotation rate, deg/s

The six checks of the plan, as readings (agents/site_progress/visits.py names them):
    1 live, here, now   sealed (the file's hash = the sealed one), in_app, motion_consistent
    2 at this site      gps_inside, gps_distance_m, mock_location, views_match_site
    3 new footage       reused_from: a run of frames equal (fingerprints) to another video's
    4 zones shown       zones_shown, zones_new (viewpoints matched; stretches for a road)
    5 change            change: at the same viewpoints as the visit before
    6 the claim         claim_verdict (and asset_at_start, complete_shown) by an optional reader
    and same_place_as: this visit's views match another work's viewpoints

Room for error (T136): a person at a site gets things wrong, and an honest month must not look
like a trick.
    every viewpoint the site ever had is compared, from its last MAX_REFS good frames (a viewpoint
        missed one month is still compared the next, and an old frame stands in for a poor one);
        a visit whose views did not match the site never becomes the site's reference
    a dark, blurred or very short video says "can't tell" (views_match_site None, change
        "cant_tell"), never "does not match": poor light is not a proof of anything
    a GPS point counts with its own reported accuracy (up to GPS_POOR_M); when every point is
        poorer than that, the GPS says "can't tell"
    a viewpoint the person could not film says so in the log ("skipped": [{"id", "reason"}]) and
        is not counted against the visit

The same spot every month (T158, docs/plans/T158-same-spot-filming.md): the log also carries the
compass ("heading": [{"t", "h", "p"}]). Each viewpoint keeps where it was filmed from (`spot`),
which way the phone faced (`facing`) and three pictures across the pan (`pans`); a linear work
keeps a picture of each stretch it was filmed in (kept["stretches"]). The readings say how far
each viewpoint was from its anchor (`spot_offsets_m`), how much of the anchor's arc was panned
(`spot_coverage`), and the claim is judged spot by spot, on last visit's and this visit's
pictures of the same spot, then combined (spots.combine): `spot_verdicts`, `spots_needed`,
`spots_filmed`, `claim_spots_not_shown`, and `stretches_missed` for the stretches asked.
"""

from __future__ import annotations

import hashlib
import math
import statistics
from collections.abc import Callable
from dataclasses import dataclass, field

from drishti.agents.site_progress import spots as sp
from drishti.agents.site_progress.sitemap import GPS_MARGIN_M, MIN_SPOTS, Site
from drishti.video import reader as rd

VIEW_MATCH = 25           # matching points in one geometry: the same viewpoint as before
PLACE_MATCH = 40          # ... the same place as another work (agent.MIN_INLIERS)
CHANGE_MIN = 0.06         # a share of the view this large changed: "changed"
CHANGE_LOW = 0.02         # every matched view under this: "no change"
MIN_RUN = 3               # frames in a row equal to another video's: reused footage
FLOW_MOVING, FLOW_STILL = 4.0, 0.8      # image motion (px between sampled frames)
ROT_MOVING, ROT_STILL = 8.0, 1.5        # phone rotation (deg/s)
QUALITY_SHARE = 0.6       # usable frames needed for a video of good quality
MIN_USABLE = 8            # fewer usable frames than this (4 s): too short to judge
GPS_POOR_M = 50.0         # a fix less accurate than this says nothing about where the phone was
MIN_GOOD_FIXES = 3
MAX_REFS = 3              # earlier good frames of one viewpoint it is compared with
MAX_JUDGED_SPOTS = 12     # spots the claim is judged at (a long road asks 8 stretches + views)
FIX_NEAR_S = 2.0          # a GPS fix this close in time places a frame on a stretch

Judge = Callable[[list[str], list[tuple[str, bytes]]], list[dict]]


@dataclass
class Earlier:
    """An earlier visit: of this work (to compare with), or of another work (to check reuse and
    place). viewpoints: {id: jpeg bytes}; hashes: fingerprints of its sampled frames, in order;
    readings: what that visit read (a visit whose views did not match is never a reference);
    spots: {id: {"spot", "facing"}} (T158); stretches: {stretch id: jpeg bytes} (T158)."""
    work_id: str
    visit_id: str
    kind: str
    viewpoints: dict[str, bytes] = field(default_factory=dict)
    hashes: list[str] = field(default_factory=list)
    readings: dict = field(default_factory=dict)
    spots: dict[str, dict] = field(default_factory=dict)
    stretches: dict[str, bytes] = field(default_factory=dict)


def references(earlier: list[Earlier]) -> dict[str, list[bytes]]:
    """Every viewpoint the site has had, with its last MAX_REFS good frames, newest first. A
    visit whose views did not match the site, or that was filmed outside it, is left out."""
    out: dict[str, list[bytes]] = {}
    for e in reversed(earlier):
        r = e.readings or {}
        if r.get("views_match_site") is False or r.get("mock_location") is True \
                or r.get("gps_inside") is False:
            continue
        for vid, jpg in e.viewpoints.items():
            if jpg and len(out.setdefault(vid, [])) < MAX_REFS:
                out[vid].append(jpg)
    return {k: v for k, v in out.items() if v}


def stretch_references(earlier: list[Earlier]) -> dict[str, bytes]:
    """The newest picture of each stretch of a linear work, from visits filmed at the site."""
    out: dict[str, bytes] = {}
    for e in reversed(earlier):
        r = e.readings or {}
        if r.get("views_match_site") is False or r.get("mock_location") is True \
                or r.get("gps_inside") is False:
            continue
        for sid, jpg in e.stretches.items():
            if jpg:
                out.setdefault(sid, jpg)
    return out


def sha256(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def longest_run(mine: list[str], theirs: list[str], bits: int = rd.STRICT_BITS) -> int:
    """The longest run of consecutive frames of `mine` equal, in the same order, to consecutive
    frames of `theirs` (a copied video, re-encoded, keeps its frames in order)."""
    best, prev = 0, {}
    for h in mine:
        cur = {}
        for j, g in enumerate(theirs):
            if rd.bits_apart(h, g) <= bits:
                cur[j] = max(prev.get(j - 1, 0), prev.get(j - 2, 0)) + 1
        best = max(best, max(cur.values(), default=0))
        prev = cur
    return best


def _num(v) -> float | None:
    return (float(v) if isinstance(v, (int, float)) and not isinstance(v, bool)
            and math.isfinite(v) else None)


def _gps(log: dict, site: Site | None) -> dict:
    pts = [p for p in log.get("gps") or [] if isinstance(p, dict)
           and _num(p.get("lat")) is not None and _num(p.get("lon")) is not None
           and -90 <= p["lat"] <= 90 and -180 <= p["lon"] <= 180]
    mocks = [p.get("mock") for p in pts if isinstance(p.get("mock"), bool)]
    out = {"mock_location": (True if any(mocks) else False) if mocks else None,
           "gps_inside": None, "gps_distance_m": None, "gps_weak": None}
    # a fix with no accuracy is taken as good (older phones); one poorer than GPS_POOR_M is not
    good = [p for p in pts if (_num(p.get("accuracy")) or 0.0) <= GPS_POOR_M]
    if pts:
        out["gps_weak"] = len(good) < min(MIN_GOOD_FIXES, len(pts))
    if site and pts and not out["gps_weak"]:
        # each point is inside when it is, give or take its own reported accuracy
        inside = [site.outside_by(p["lat"], p["lon"]) - (_num(p.get("accuracy")) or 0.0)
                  <= GPS_MARGIN_M for p in good]
        out["gps_inside"] = sum(inside) / len(inside) >= 0.5
        out["gps_distance_m"] = round(statistics.median(site.outside_by(p["lat"], p["lon"])
                                                        for p in good), 1)
    return out



def _stretches(log: dict, site: Site | None) -> list[str]:
    if not site or site.kind != "linear":
        return []
    ids = {site.stretch_of(p["lat"], p["lon"]) for p in log.get("gps") or []
           if isinstance(p, dict) and isinstance(p.get("lat"), (int, float))
           and isinstance(p.get("lon"), (int, float))}
    return sorted(i for i in ids if i)


def _motion(frames: list[rd.Frame], log: dict) -> bool | None:
    """False when the picture moves while the phone is still (or the other way round) for most
    of the video: a screen being filmed, or a video that is not this phone's."""
    rots = [(m["t"], m["rot"]) for m in log.get("motion") or [] if isinstance(m, dict)
            and isinstance(m.get("t"), (int, float)) and isinstance(m.get("rot"), (int, float))]
    if len(rots) < 4 or len(frames) < 4:
        return None
    bad = n = 0
    for a, b in zip(frames, frames[1:], strict=False):
        window = [r for t, r in rots if a.t <= t <= b.t]
        if not window:
            continue
        f, r = rd.flow(a.grey, b.grey), sum(window) / len(window)
        if f <= FLOW_MOVING and r <= ROT_MOVING:
            continue                  # both still: says nothing either way
        n += 1
        bad += (f > FLOW_MOVING and r < ROT_STILL) or (f < FLOW_STILL and r > ROT_MOVING)
    return None if n < 3 else bad / n <= 0.5


def _keyframes(frames: list[rd.Frame], log: dict) -> dict[str, rd.Frame]:
    """The sharpest usable frame of each viewpoint the person marked while filming."""
    out = {}
    for vp in log.get("viewpoints") or []:
        if not isinstance(vp, dict) or not isinstance(vp.get("id"), str):
            continue
        t0, t1 = vp.get("t0"), vp.get("t1")
        if not isinstance(t0, (int, float)) or not isinstance(t1, (int, float)):
            continue
        cands = [f for f in frames if t0 <= f.t <= t1 and f.usable]
        if cands:
            out[vp["id"]] = max(cands, key=lambda f: f.sharpness)
    return out


def _windows(log: dict) -> dict[str, tuple[float, float]]:
    return {vp["id"]: (float(vp["t0"]), float(vp["t1"])) for vp in log.get("viewpoints") or []
            if isinstance(vp, dict) and isinstance(vp.get("id"), str)
            and isinstance(vp.get("t0"), (int, float)) and isinstance(vp.get("t1"), (int, float))}


def _stretch_frames(frames: list[rd.Frame], log: dict, site: Site | None) -> dict[str, rd.Frame]:
    """The sharpest usable frame filmed in each stretch of a linear work (placed by the GPS fix
    nearest in time)."""
    if not site or site.kind != "linear":
        return {}
    fixes = [(p["t"], p["lat"], p["lon"]) for p in log.get("gps") or [] if isinstance(p, dict)
             and all(_num(p.get(k)) is not None for k in ("t", "lat", "lon"))
             and (_num(p.get("accuracy")) or 0.0) <= GPS_POOR_M]
    out: dict[str, rd.Frame] = {}
    for f in frames:
        if not f.usable or not fixes:
            continue
        t, lat, lon = min(fixes, key=lambda x: abs(x[0] - f.t))
        sid = site.stretch_of(lat, lon) if abs(t - f.t) <= FIX_NEAR_S else None
        if sid and (sid not in out or f.sharpness > out[sid].sharpness):
            out[sid] = f
    return out


def _answer(answers, quality_ok: bool) -> tuple[str | None, str | None]:
    """The first answer of a reader as (verdict, reason); a wrong shape is no answer."""
    a = answers[0] if isinstance(answers, list) and answers else None
    a = a if isinstance(a, dict) else {}
    v = a.get("verdict") if a.get("verdict") in sp.VERDICTS else None
    reason = a.get("reason") if isinstance(a.get("reason"), str) and a.get("reason") else None
    if v == "not_shown" and not quality_ok:
        # the reader may simply not see it in a dark or blurred video
        v, reason = "cant_tell", "the video is too dark, blurred or short to judge the claim"
    return v, reason


def read(path, log: dict, site: Site | None, earlier: list[Earlier], others: list[Earlier],
         kind: str, claim: str | None = None, asset: str = "the work",
         judge: Judge | None = None, spots_needed: int | None = None,
         stretches_asked: list[str] | None = None) -> tuple[dict, dict]:
    """(readings, kept): kept = {"viewpoints": {id: {"jpeg", "hash", "t", "faces", "spot",
    "facing", "pans"}}, "stretches": {id: {"jpeg", "hash", "t", "faces"}}, "hashes": [...]}: what
    is stored after the video itself is deleted. spots_needed: sitemap.spots_needed for the work
    (default: the site's viewpoints so far, at least MIN_SPOTS); stretches_asked: the stretches of
    a linear work this visit was asked to film (sitemap.stretches_asked)."""
    log = log if isinstance(log, dict) else {}
    readings: dict = {"in_app": log.get("in_app") is True}
    sealed = log.get("sealed_sha256")
    readings["sealed"] = (sha256(path) == sealed) if isinstance(sealed, str) else None
    frames = rd.frames(path)
    usable = [f for f in frames if f.usable]
    readings["quality_ok"] = (bool(frames) and len(usable) / len(frames) >= QUALITY_SHARE
                              and len(usable) >= MIN_USABLE)
    readings.update(_gps(log, site))
    readings["motion_consistent"] = _motion(frames, log)
    skipped = sorted({s["id"] for s in log.get("skipped") or [] if isinstance(s, dict)
                      and isinstance(s.get("id"), str)})
    readings["viewpoints_skipped"] = skipped

    keys = _keyframes(frames, log)
    feats = {vid: rd.features(f.grey) for vid, f in keys.items()}
    pool = [rd.features(f.grey) for f in usable[::4]]       # unmarked frames, for re-finding views
    refs = references(earlier)
    before_of: dict[str, bytes] = {}

    matched, changes = [], []
    if refs:
        for vid, jpgs in refs.items():
            mine = [(feats[vid], keys[vid].grey)] if vid in feats else []
            best, h, grey, bg_best = 0, None, None, None
            for jpg in jpgs:                         # newest first: a tie keeps the newest
                before = rd.decode(jpg)
                if before is None:
                    continue
                bg = rd.cv2.cvtColor(before, rd.cv2.COLOR_BGR2GRAY)
                bf = rd.features(bg)
                for cand, frame in mine + [(f, None) for f in pool]:
                    n, hh = rd.match(bf, cand)
                    if n > best:
                        best, h, grey, bg_best = n, hh, frame, bg
                        before_of[vid] = jpg
            if best >= VIEW_MATCH:
                matched.append(vid)
                if h is not None and grey is not None:
                    changes.append(rd.change(bg_best, grey, h))
        expected = len(refs)
        counted = max(1, expected - len(set(skipped) & set(refs)))
        readings["viewpoints_expected"] = expected
        readings["viewpoints_matched"] = len(matched)
        need = max(1, math.ceil(counted / 2))
        views = True if len(matched) >= need else False if not matched else None
        # a dark, blurred or very short video cannot show that it is somewhere else
        readings["views_match_site"] = None if views is False and not readings["quality_ok"] \
            else views
        if changes and max(changes) >= CHANGE_MIN:
            readings["change"] = "changed"
        elif changes and max(changes) < CHANGE_LOW and readings["quality_ok"]:
            readings["change"] = "no_change"
        else:
            readings["change"] = "cant_tell"
        readings["zones_shown"] = sorted(set(matched) | set(_stretches(log, site)))
        readings["zones_new"] = sorted(set(keys) - set(refs))
    else:
        readings.update(viewpoints_expected=len(keys), viewpoints_matched=len(keys),
                        views_match_site=None, change=None,
                        zones_shown=sorted(set(keys) | set(_stretches(log, site))),
                        zones_new=sorted(keys))

    hashes = [rd.fingerprint(f.grey) for f in usable]
    reused = []
    for e in earlier + others:
        run = longest_run(hashes, e.hashes) if e.hashes else 0
        if run:
            reused.append({"work_id": e.work_id, "visit_id": e.visit_id, "frames": run})
    readings["reused_from"] = [r for r in reused if r["frames"] >= MIN_RUN]

    same: dict[str, int] = {}
    mine_all = list(feats.values()) or pool
    for e in others:
        best = 0
        for jpg in e.viewpoints.values():
            img = rd.decode(jpg)
            if img is None:
                continue
            of = rd.features(rd.cv2.cvtColor(img, rd.cv2.COLOR_BGR2GRAY))
            best = max([best] + [rd.match(of, m)[0] for m in mine_all])
        if best >= PLACE_MATCH:
            same[e.work_id] = max(best, same.get(e.work_id, 0))       # one entry per work
    readings["same_place_as"] = [{"work_id": k, "inliers": v} for k, v in sorted(same.items())]

    kept = {"viewpoints": {}, "stretches": {}, "hashes": hashes}
    win = _windows(log)
    for vid, f in keys.items():
        img, faces = rd.blur_faces(f.colour)
        t0, t1 = win[vid]
        facing = sp.arc(sp.headings(log, t0, t1))
        near = [x for x in usable if t0 <= x.t <= t1] or [f]
        pans = [rd.jpeg(rd.blur_faces(min(near, key=lambda x, t=t: abs(x.t - t)).colour)[0])
                for t in sp.pan_times(log, t0, t1, facing)]
        kept["viewpoints"][vid] = {"jpeg": rd.jpeg(img), "hash": rd.fingerprint(f.grey),
                                   "t": round(f.t, 2), "faces": faces,
                                   "spot": sp.spot(log.get("gps"), t0, t1, GPS_POOR_M),
                                   "facing": facing, "pans": pans}
    for sid, f in sorted(_stretch_frames(frames, log, site).items(),
                         key=lambda kv: int(kv[0][1:])):
        img, faces = rd.blur_faces(f.colour)
        kept["stretches"][sid] = {"jpeg": rd.jpeg(img), "hash": rd.fingerprint(f.grey),
                                  "t": round(f.t, 2), "faces": faces}

    # the same spot every month (T158): how far from the anchor, how much of its arc panned
    anchors = sp.anchors([{"readings": e.readings, "spots": e.spots} for e in earlier])
    offsets, coverage = {}, {}
    for vid in keys:
        a = anchors.get(vid)
        if a is None:
            continue
        off = sp.offset_m(a["box"], kept["viewpoints"][vid]["spot"])
        if off is not None:
            offsets[vid] = off
        cov = sp.covered(a["facing"], sp.headings(log, *win[vid]))
        if cov is not None:
            coverage[vid] = cov
    srefs = stretch_references(earlier)
    filmed_stretches = list(kept["stretches"])
    filmed = (len(matched) if refs else len(keys)) + len(filmed_stretches)
    needed = spots_needed if spots_needed is not None else max(MIN_SPOTS, len(refs))
    readings.update(spots_needed=needed, spots_filmed=filmed, spot_offsets_m=offsets,
                    spot_coverage=coverage, spot_verdicts={}, claim_spots_not_shown=[],
                    stretches_missed=None)
    if stretches_asked is not None:
        readings["stretches_missed"] = [s for s in stretches_asked if s not in filmed_stretches]

    readings.update(claim_verdict=None, claim_reason=None, asset_at_start=None,
                    complete_shown=None)
    if judge:
        now = [(f"now-{v}", kept["viewpoints"][v]["jpeg"]) for v in list(keys)[:3]]
        before = [(f"before-{v}", before_of[v]) for v in matched[:3] if v in before_of]
        if claim and (refs or srefs):
            asked = set(stretches_asked or ())
            pairs = [(v, before_of[v], kept["viewpoints"][v]["jpeg"]) for v in matched
                     if v in before_of and v in kept["viewpoints"]]
            pairs += [(s, srefs[s], kept["stretches"][s]["jpeg"])
                      for s in sorted(kept["stretches"], key=lambda s: (s not in asked,
                                                                         int(s[1:])))
                      if s in srefs]
            verdicts, reasons = {}, {}
            for sid, b, n in pairs[:MAX_JUDGED_SPOTS]:
                verdicts[sid], reasons[sid] = _answer(
                    judge([claim], [(f"before-{sid}", b), (f"now-{sid}", n)]),
                    readings["quality_ok"])
            if verdicts:
                v = sp.combine(verdicts, needed, filmed, sp.whole_claim(claim))
                readings["claim_verdict"] = v
                readings["claim_reason"] = next((reasons[k][:300] for k in verdicts
                                                 if verdicts[k] == v and reasons[k]), None)
                readings["spot_verdicts"] = {k: x for k, x in verdicts.items() if x}
                readings["claim_spots_not_shown"] = [k for k, x in verdicts.items()
                                                     if x == "not_shown"]
            elif now:
                # no spot seen both times: judged once on this visit's views (as before T158)
                v, reason = _answer(judge([claim], before + now), readings["quality_ok"])
                readings["claim_verdict"] = v
                readings["claim_reason"] = reason[:300] if reason else None
        questions = []
        if kind == "baseline":
            questions.append(("asset_at_start", f"{asset} is already built and standing"))
        if kind == "final":
            questions.append(("complete_shown", f"{asset} is finished in every part shown"))
        if questions and now:
            answers = judge([q for _k, q in questions], before + now)
            for (k, _q), a in zip(questions, answers if isinstance(answers, list) else [],
                                  strict=False):
                v, _reason = _answer([a], readings["quality_ok"])
                if v in ("shown", "not_shown"):
                    readings[k] = v == "shown"
    return readings, kept
