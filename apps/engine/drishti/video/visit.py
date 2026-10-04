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
"""

from __future__ import annotations

import hashlib
import math
import statistics
from collections.abc import Callable
from dataclasses import dataclass, field

from drishti.agents.site_progress.sitemap import Site
from drishti.video import reader as rd

VIEW_MATCH = 25           # matching points in one geometry: the same viewpoint as before
PLACE_MATCH = 40          # ... the same place as another work (agent.MIN_INLIERS)
CHANGE_MIN = 0.06         # a share of the view this large changed: "changed"
CHANGE_LOW = 0.02         # every matched view under this: "no change"
MIN_RUN = 3               # frames in a row equal to another video's: reused footage
FLOW_MOVING, FLOW_STILL = 4.0, 0.8      # image motion (px between sampled frames)
ROT_MOVING, ROT_STILL = 8.0, 1.5        # phone rotation (deg/s)
QUALITY_SHARE = 0.6       # usable frames needed for a video of good quality

Judge = Callable[[list[str], list[tuple[str, bytes]]], list[dict]]


@dataclass
class Earlier:
    """An earlier visit: of this work (to compare with), or of another work (to check reuse and
    place). viewpoints: {id: jpeg bytes}; hashes: fingerprints of its sampled frames, in order."""
    work_id: str
    visit_id: str
    kind: str
    viewpoints: dict[str, bytes] = field(default_factory=dict)
    hashes: list[str] = field(default_factory=list)


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


def _gps(log: dict, site: Site | None) -> dict:
    pts = [p for p in log.get("gps") or [] if isinstance(p, dict)
           and isinstance(p.get("lat"), (int, float)) and isinstance(p.get("lon"), (int, float))]
    mocks = [p.get("mock") for p in pts if isinstance(p.get("mock"), bool)]
    out = {"mock_location": (True if any(mocks) else False) if mocks else None,
           "gps_inside": None, "gps_distance_m": None}
    if site and pts:
        inside = [site.inside(p["lat"], p["lon"]) for p in pts]
        out["gps_inside"] = sum(inside) / len(inside) >= 0.5
        out["gps_distance_m"] = round(statistics.median(site.outside_by(p["lat"], p["lon"])
                                                        for p in pts), 1)
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


def read(path, log: dict, site: Site | None, earlier: list[Earlier], others: list[Earlier],
         kind: str, claim: str | None = None, asset: str = "the work",
         judge: Judge | None = None) -> tuple[dict, dict]:
    """(readings, kept): kept = {"viewpoints": {id: {"jpeg", "hash", "t", "faces"}},
    "hashes": [...]}: what is stored after the video itself is deleted."""
    log = log if isinstance(log, dict) else {}
    readings: dict = {"in_app": log.get("in_app") is True}
    sealed = log.get("sealed_sha256")
    readings["sealed"] = (sha256(path) == sealed) if isinstance(sealed, str) else None
    frames = rd.frames(path)
    usable = [f for f in frames if f.usable]
    readings["quality_ok"] = bool(frames) and len(usable) / len(frames) >= QUALITY_SHARE
    readings.update(_gps(log, site))
    readings["motion_consistent"] = _motion(frames, log)

    keys = _keyframes(frames, log)
    feats = {vid: rd.features(f.grey) for vid, f in keys.items()}
    pool = [rd.features(f.grey) for f in usable[::4]]       # unmarked frames, for re-finding views
    prev = next((e for e in reversed(earlier) if e.viewpoints), None)

    matched, changes = [], []
    if prev:
        for vid, jpg in prev.viewpoints.items():
            before = rd.decode(jpg)
            if before is None:
                continue
            bg = rd.cv2.cvtColor(before, rd.cv2.COLOR_BGR2GRAY)
            bf = rd.features(bg)
            mine = [feats[vid]] if vid in feats else []
            best, h, grey = 0, None, None
            for cand, frame in [(f, keys[vid].grey) for f in mine] + [(f, None) for f in pool]:
                n, hh = rd.match(bf, cand)
                if n > best:
                    best, h, grey = n, hh, frame
            if best >= VIEW_MATCH:
                matched.append(vid)
                if h is not None and grey is not None:
                    changes.append(rd.change(bg, grey, h))
        expected = len(prev.viewpoints)
        readings["viewpoints_expected"] = expected
        readings["viewpoints_matched"] = len(matched)
        need = max(1, math.ceil(expected / 2))
        readings["views_match_site"] = (True if len(matched) >= need else
                                        False if not matched else None)
        if changes and max(changes) >= CHANGE_MIN:
            readings["change"] = "changed"
        elif changes and max(changes) < CHANGE_LOW:
            readings["change"] = "no_change"
        else:
            readings["change"] = "cant_tell"
        readings["zones_shown"] = sorted(set(matched) | set(_stretches(log, site)))
        readings["zones_new"] = sorted(set(keys) - set(prev.viewpoints))
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

    same = []
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
            same.append({"work_id": e.work_id, "inliers": best})
    readings["same_place_as"] = same

    kept = {"viewpoints": {}, "hashes": hashes}
    for vid, f in keys.items():
        img, faces = rd.blur_faces(f.colour)
        kept["viewpoints"][vid] = {"jpeg": rd.jpeg(img), "hash": rd.fingerprint(f.grey),
                                   "t": round(f.t, 2), "faces": faces}

    readings.update(claim_verdict=None, claim_reason=None, asset_at_start=None,
                    complete_shown=None)
    if judge:
        now = [(f"now-{v}", kept["viewpoints"][v]["jpeg"]) for v in list(keys)[:3]]
        before = [(f"before-{v}", prev.viewpoints[v]) for v in matched[:3]] if prev else []
        questions = []
        if claim and prev:
            questions.append(("claim", claim))
        if kind == "baseline":
            questions.append(("asset_at_start", f"{asset} is already built and standing"))
        if kind == "final":
            questions.append(("complete_shown", f"{asset} is finished in every part shown"))
        if questions and now:
            answers = judge([q for _k, q in questions], before + now)
            for (k, _q), a in zip(questions, answers, strict=False):
                v = a.get("verdict")
                if k == "claim":
                    readings["claim_verdict"] = v
                    readings["claim_reason"] = a.get("reason") or None
                elif v in ("shown", "not_shown"):
                    readings[k] = v == "shown"
    return readings, kept
