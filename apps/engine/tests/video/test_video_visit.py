"""The site video job's readings on made-up videos (T124, plan T120 §9.4).

A "site" is a wide drawn scene; a visit pans across it and stops at five viewpoints. The planted
tricks: the same file uploaded again, another site's video, a phone held still while the picture
moves (a filmed screen), a wall built between visits (real change), the GPS of another place.

Needs OpenCV (data/requirements-video.txt); skipped where it is not installed, as in the live
engine's CI. Run here with the video job's environment.
"""

from __future__ import annotations

import json
import shutil

import pytest

cv2 = pytest.importorskip("cv2")
np = pytest.importorskip("numpy")

from drishti.agents.site_progress import agent, sitemap  # noqa: E402
from drishti.video import reader as rd  # noqa: E402
from drishti.video import visit as vv  # noqa: E402

W, H = 480, 360
FPS = 10
VIEWS = 5
DWELL, PAN = 2.0, 1.0           # seconds still at a viewpoint, seconds panning to the next
SITE = sitemap.Site("compact", 25.75, 82.69, 30.0)


def scene(seed: int, wall: bool = False) -> np.ndarray:
    """A wide textured scene; `wall` adds a big new structure in the lower half."""
    rng = np.random.default_rng(seed)
    img = np.full((H, W * 4, 3), 150, np.uint8)
    img[: H // 3] = (200, 180, 140)                                     # sky band
    for _ in range(260):
        x, y = int(rng.integers(0, W * 4)), int(rng.integers(H // 3, H))
        colour = tuple(int(c) for c in rng.integers(0, 255, 3))
        if rng.random() < 0.5:
            cv2.rectangle(img, (x, y), (x + int(rng.integers(10, 70)),
                                        y + int(rng.integers(10, 60))), colour, -1)
        else:
            cv2.circle(img, (x, y), int(rng.integers(5, 30)), colour, -1)
    noise = rng.integers(0, 40, img.shape, dtype=np.uint8)
    img = cv2.add(img, noise)
    if wall:
        for k in range(VIEWS):
            x0 = int(k * (W * 3) / (VIEWS - 1)) + 60
            cv2.rectangle(img, (x0, H // 2), (x0 + 300, H - 20), (60, 60, 160), -1)
            for row in range(H // 2, H - 20, 24):                      # brick courses
                cv2.line(img, (x0, row), (x0 + 300, row), (230, 230, 230), 2)
    return img


def film(path, img: np.ndarray, still_phone: bool = False):
    """Pan across the scene, stopping at VIEWS viewpoints. Returns the capture log."""
    out = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), FPS, (W, H))
    t, vps, motion = 0.0, [], []
    xs = [int(k * (W * 3) / (VIEWS - 1)) for k in range(VIEWS)]
    for k, x in enumerate(xs):
        t0 = t
        for _ in range(int(DWELL * FPS)):
            out.write(img[:, x:x + W].copy())
            motion.append({"t": round(t, 2), "rot": 0.3})
            t += 1 / FPS
        vps.append({"id": f"v{k + 1}", "t0": round(t0, 2), "t1": round(t - 1 / FPS, 2)})
        if k + 1 < len(xs):
            steps = int(PAN * FPS)
            for s in range(steps):
                xx = int(x + (xs[k + 1] - x) * (s + 1) / steps)
                out.write(img[:, xx:xx + W].copy())
                motion.append({"t": round(t, 2), "rot": 0.3 if still_phone else 35.0})
                t += 1 / FPS
    out.release()
    gps = [{"t": i, "lat": 25.75 + 0.00005 * (i % 3), "lon": 82.69, "accuracy": 6, "mock": False}
           for i in range(int(t))]
    return {"in_app": True, "sealed_sha256": vv.sha256(path), "viewpoints": vps, "gps": gps,
            "motion": motion}


def earlier_from(work_id, visit_id, kind, kept) -> vv.Earlier:
    return vv.Earlier(work_id, visit_id, kind,
                      {k: v["jpeg"] for k, v in kept["viewpoints"].items()}, kept["hashes"])


@pytest.fixture(scope="module")
def site_a(tmp_path_factory):
    d = tmp_path_factory.mktemp("videos")
    logs = {}
    for name, img, still in (("base", scene(1), False), ("m1", scene(1), False),
                             ("m2", scene(1, wall=True), False), ("other", scene(2), False),
                             ("screen", scene(1), True)):
        logs[name] = (d / f"{name}.mp4", film(d / f"{name}.mp4", img, still))
    base_r, base_k = vv.read(logs["base"][0], logs["base"][1], SITE, [], [], "baseline")
    return d, logs, base_r, base_k


def test_the_first_visit_sets_the_viewpoints(site_a):
    _d, _logs, r, kept = site_a
    assert r["sealed"] is True and r["in_app"] and r["quality_ok"]
    assert r["gps_inside"] is True and r["mock_location"] is False
    assert r["viewpoints_expected"] == VIEWS and r["views_match_site"] is None
    assert len(kept["viewpoints"]) == VIEWS and kept["hashes"]
    assert r["reused_from"] == [] and r["motion_consistent"] is True


def test_an_honest_month_with_no_building_matches_and_shows_no_change(site_a):
    _d, logs, _r, base_k = site_a
    prev = earlier_from("W1", "base", "baseline", base_k)
    r, _ = vv.read(logs["m1"][0], logs["m1"][1], SITE, [prev], [], "monthly")
    assert r["views_match_site"] is True and r["viewpoints_matched"] == VIEWS
    assert r["change"] == "no_change"


def test_a_wall_built_between_visits_is_a_change(site_a):
    _d, logs, _r, base_k = site_a
    prev = earlier_from("W1", "base", "baseline", base_k)
    r, _ = vv.read(logs["m2"][0], logs["m2"][1], SITE, [prev], [], "monthly")
    assert r["views_match_site"] is True and r["change"] == "changed"


def test_the_same_video_uploaded_again_is_reused_footage(site_a):
    d, logs, _r, base_k = site_a
    copy = d / "copy.mp4"
    shutil.copy(logs["base"][0], copy)
    log = dict(logs["base"][1], sealed_sha256=vv.sha256(copy))
    prev = earlier_from("W1", "base", "baseline", base_k)
    r, _ = vv.read(copy, log, SITE, [prev], [], "monthly")
    assert r["reused_from"] and r["reused_from"][0]["frames"] >= vv.MIN_RUN
    judged = agent.assess({"work_id": "W1", "status": "SANCTIONED", "site_visits": [
        {"visit_id": "base", "kind": "baseline", "captured_at": "2026-03-01", "readings": _r},
        {"visit_id": "copy", "kind": "monthly", "captured_at": "2026-04-01", "readings": r}]},
        __import__("datetime").date(2026, 4, 2))
    assert judged.findings[0].code == "FOOTAGE_USED_BEFORE"


def test_a_new_film_of_the_site_is_not_reuse(site_a):
    _d, logs, _r, base_k = site_a
    prev = earlier_from("W1", "base", "baseline", base_k)
    # a new film with something built differs frame by frame. (A made-up site filmed twice with
    # nothing changed is the same pixels, like a tripod; a real hand-held refilm is not: how
    # close real refilms come is a measurement for the field trial, T126.)
    r, _ = vv.read(logs["m2"][0], logs["m2"][1], SITE, [prev], [], "monthly")
    assert r["reused_from"] == []


def test_another_sites_video_does_not_match_this_site(site_a):
    _d, logs, _r, base_k = site_a
    prev = earlier_from("W1", "base", "baseline", base_k)
    log = dict(logs["other"][1])
    log["gps"] = [dict(p, lat=25.76) for p in log["gps"]]              # 1.1 km away
    r, _ = vv.read(logs["other"][0], log, SITE, [prev], [], "monthly")
    assert r["views_match_site"] is False and r["gps_inside"] is False
    assert r["gps_distance_m"] > 1000


def test_this_site_filmed_for_another_work_is_the_same_place(site_a):
    _d, logs, _r, base_k = site_a
    other_work = earlier_from("W7", "w7-base", "baseline", base_k)
    r, _ = vv.read(logs["m1"][0], logs["m1"][1], SITE, [], [other_work], "baseline")
    assert r["same_place_as"] and r["same_place_as"][0]["work_id"] == "W7"
    assert r["same_place_as"][0]["inliers"] >= vv.PLACE_MATCH


def test_a_phone_held_still_while_the_picture_moves_is_not_consistent(site_a):
    _d, logs, _r, base_k = site_a
    r, _ = vv.read(logs["screen"][0], logs["screen"][1], SITE, [], [], "monthly")
    assert r["motion_consistent"] is False


def test_an_edited_file_breaks_the_seal(site_a):
    d, logs, _r, _k = site_a
    edited = d / "edited.mp4"
    shutil.copy(logs["m1"][0], edited)
    with open(edited, "ab") as f:
        f.write(b"\0")
    r, _ = vv.read(edited, logs["m1"][1], SITE, [], [], "monthly")
    assert r["sealed"] is False


def test_the_claim_reader_is_asked_with_before_and_after_views(site_a):
    _d, logs, _r, base_k = site_a
    prev = earlier_from("W1", "base", "baseline", base_k)
    asked = []

    def judge(claims, photos):
        asked.append((claims, [n for n, _ in photos]))
        return [{"verdict": "not_shown", "reason": "no wall in the views"} for _ in claims]

    r, _ = vv.read(logs["m1"][0], logs["m1"][1], SITE, [prev], [], "monthly",
                   claim="walls up to lintel level", judge=judge)
    assert r["claim_verdict"] == "not_shown" and r["claim_reason"] == "no wall in the views"
    assert asked[0][0] == ["walls up to lintel level"]
    assert any(n.startswith("before-") for n in asked[0][1])


def test_readings_are_json_and_faces_count_is_kept(site_a):
    _d, _logs, r, kept = site_a
    json.dumps(r)
    assert all("faces" in v and v["jpeg"] for v in kept["viewpoints"].values())


def test_longest_run_counts_frames_in_order():
    rng = np.random.default_rng(5)
    a = [rd.fingerprint(rng.integers(0, 255, (64, 64), dtype=np.uint8)) for _ in range(6)]
    assert vv.longest_run(a, a) == 6
    assert vv.longest_run(a, list(reversed(a))) <= 2
