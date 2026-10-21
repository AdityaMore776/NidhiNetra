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


def earlier_from(work_id, visit_id, kind, kept, readings=None) -> vv.Earlier:
    return vv.Earlier(work_id, visit_id, kind,
                      {k: v["jpeg"] for k, v in kept["viewpoints"].items()}, kept["hashes"],
                      readings or {},
                      {k: {"spot": v.get("spot"), "facing": v.get("facing")}
                       for k, v in kept["viewpoints"].items()},
                      {k: v["jpeg"] for k, v in (kept.get("stretches") or {}).items()})


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


# ---- room for error (T136): an honest month done badly is "can't tell", never a trick ----------

def _partial_log(log: dict, keep: set[str]) -> dict:
    """The same video, but the person marked only some viewpoints."""
    return dict(log, viewpoints=[v for v in log["viewpoints"] if v["id"] in keep])


def test_a_viewpoint_missed_one_month_is_still_compared_the_next(site_a, tmp_path):
    _d, logs, base_r, base_k = site_a
    base = earlier_from("W1", "base", "baseline", base_k)
    base.readings = base_r
    # month 1 marks only v1 and v2; its kept frames are those two
    m1_log = _partial_log(logs["m1"][1], {"v1", "v2"})
    m1_r, m1_k = vv.read(logs["m1"][0], m1_log, SITE, [base], [], "monthly")
    assert set(m1_k["viewpoints"]) == {"v1", "v2"}
    m1 = earlier_from("W1", "m1", "monthly", m1_k)
    m1.readings = m1_r
    # month 2 is compared with all five viewpoints the site has had, not only month 1's two
    r, _ = vv.read(logs["m2"][0], logs["m2"][1], SITE, [base, m1], [], "monthly")
    assert r["viewpoints_expected"] == VIEWS and r["viewpoints_matched"] == VIEWS
    assert r["views_match_site"] is True and r["change"] == "changed"


def test_a_visit_that_did_not_match_never_becomes_the_reference(site_a):
    _d, _logs, base_r, base_k = site_a
    base = earlier_from("W1", "base", "baseline", base_k)
    base.readings = base_r
    elsewhere = earlier_from("W1", "odd", "monthly", base_k)
    elsewhere.viewpoints = {"v9": b"not a frame"}
    elsewhere.readings = {"views_match_site": False}
    assert set(vv.references([base, elsewhere])) == {f"v{k + 1}" for k in range(VIEWS)}


def test_a_dark_video_of_the_site_says_cant_tell_never_does_not_match(site_a, tmp_path):
    _d, logs, base_r, base_k = site_a
    base = earlier_from("W1", "base", "baseline", base_k)
    dark = tmp_path / "dark.mp4"
    log = film(dark, (scene(1).astype(np.float32) * 0.12).astype(np.uint8))
    r, _ = vv.read(dark, log, SITE, [base], [], "monthly",
                   judge=lambda claims, photos: [{"verdict": "not_shown"} for _ in claims],
                   claim="walls up to lintel level")
    assert r["quality_ok"] is False
    assert r["views_match_site"] is None and r["change"] == "cant_tell"
    assert r["claim_verdict"] in (None, "cant_tell")


def test_weak_gps_says_cant_tell_and_good_gps_counts_its_own_accuracy(site_a):
    _d, logs, _r, base_k = site_a
    base = earlier_from("W1", "base", "baseline", base_k)
    weak = dict(logs["m1"][1], gps=[dict(p, lat=25.7520, accuracy=90.0)
                                    for p in logs["m1"][1]["gps"]])          # 230 m off, +-90 m
    r, _ = vv.read(logs["m1"][0], weak, SITE, [base], [], "monthly")
    assert r["gps_weak"] is True and r["gps_inside"] is None
    assert r["gps_point"] is None                       # T160: a weak fix says nowhere
    # 40 m outside the 30 m site with a 35 m fix: inside, give or take the phone's own error
    near = dict(logs["m1"][1], gps=[dict(p, lat=25.75 + 70 / 111_195, accuracy=35.0)
                                    for p in logs["m1"][1]["gps"]])
    r, _ = vv.read(logs["m1"][0], near, SITE, [base], [], "monthly")
    assert r["gps_weak"] is False and r["gps_inside"] is True
    # T160: where it was filmed, for Duplicate Work, whatever the site circle says
    assert r["gps_point"]["lat"] == pytest.approx(25.75 + 70 / 111_195, abs=1e-6)
    # T168: how many fixes, and how accurate (Site Progress allows for it)
    assert r["gps_fixes"] == len(near["gps"]) and r["gps_accuracy_m"] == 35.0


def test_a_video_with_location_off_says_so(site_a):
    _d, logs, _r, base_k = site_a
    base = earlier_from("W1", "base", "baseline", base_k)
    r, _ = vv.read(logs["m1"][0], dict(logs["m1"][1], gps=[]), SITE, [base], [], "monthly")
    assert r["gps_fixes"] == 0 and r["gps_point"] is None and r["gps_accuracy_m"] is None


def test_a_viewpoint_skipped_with_a_reason_is_not_counted_against_the_visit(site_a):
    _d, logs, _r, base_k = site_a
    base = earlier_from("W1", "base", "baseline", base_k)
    log = dict(_partial_log(logs["m1"][1], {"v1"}),
               skipped=[{"id": v, "reason": "blocked"} for v in ("v2", "v3", "v4", "v5")])
    r, _ = vv.read(logs["m1"][0], log, SITE, [base], [], "monthly")
    assert r["viewpoints_skipped"] == ["v2", "v3", "v4", "v5"]
    assert r["views_match_site"] is True


def test_a_reader_answer_in_a_wrong_shape_does_not_crash(site_a):
    _d, logs, _r, base_k = site_a
    base = earlier_from("W1", "base", "baseline", base_k)
    for answers in (None, "yes", [None], [{"verdict": "maybe"}], [{"verdict": "shown",
                                                                   "reason": 7}]):
        r, _ = vv.read(logs["m1"][0], logs["m1"][1], SITE, [base], [], "monthly",
                       claim="walls", judge=lambda c, p, a=answers: a)
        assert r["claim_verdict"] in (None, "shown")


# ---- T158: the same spot every month, and the claim judged spot by spot ----

def with_compass(log: dict, width: float = 40.0, only: dict | None = None) -> dict:
    """The log with compass headings: at viewpoint k the phone pans from 60·k° across `width`°
    (or the (start, width) `only` gives for that viewpoint)."""
    heading = []
    for k, vp in enumerate(log["viewpoints"]):
        start, w = (only or {}).get(vp["id"], (60.0 * k, width))
        n = max(2, int((vp["t1"] - vp["t0"]) / 0.2))
        for i in range(n + 1):
            heading.append({"t": round(vp["t0"] + (vp["t1"] - vp["t0"]) * i / n, 2),
                            "h": round((start + w * i / n) % 360, 1), "p": -5.0})
    return dict(log, heading=heading)


def moved(log: dict, vid: str, dlat: float) -> dict:
    """The log with the GPS shifted north by `dlat` while at viewpoint `vid`."""
    vp = next(v for v in log["viewpoints"] if v["id"] == vid)
    gps = [dict(g, lat=g["lat"] + dlat) if vp["t0"] - 0.5 <= g["t"] <= vp["t1"] + 0.5 else g
           for g in log["gps"]]
    return dict(log, gps=gps)


@pytest.fixture(scope="module")
def compass_base(site_a):
    _d, logs, _r, _k = site_a
    log = with_compass(logs["base"][1])
    r, kept = vv.read(logs["base"][0], log, SITE, [], [], "baseline")
    return log, r, kept


def test_each_viewpoint_keeps_its_spot_facing_and_three_pictures(compass_base):
    _log, _r, kept = compass_base
    v2 = kept["viewpoints"]["v2"]
    assert v2["spot"]["lat"] == pytest.approx(25.75, abs=2e-4) and v2["spot"]["acc"] == 6
    assert v2["facing"]["from"] == pytest.approx(60) and v2["facing"]["width"] == pytest.approx(40)
    assert len(v2["pans"]) == 3 and all(j[:2] == b"\xff\xd8" for j in v2["pans"])  # JPEGs


def test_without_a_compass_there_is_no_facing_but_still_three_pictures(site_a):
    _d, _logs, _r, kept = site_a
    v1 = kept["viewpoints"]["v1"]
    assert v1["facing"] is None and len(v1["pans"]) == 3


def test_metres_from_the_box_and_the_share_of_last_times_view_panned(site_a, compass_base):
    _d, logs, _r, _k = site_a
    _log, base_r, base_k = compass_base
    prev = earlier_from("W1", "base", "baseline", base_k, base_r)
    log = moved(with_compass(logs["m1"][1], only={"v3": (120.0, 20.0)}), "v2", 0.0002)
    r, _ = vv.read(logs["m1"][0], log, SITE, [prev], [], "monthly")
    assert r["spot_offsets_m"]["v2"] == pytest.approx(22.2, abs=1.0)
    assert r["spot_offsets_m"]["v1"] < 8
    assert 0.5 <= r["spot_coverage"]["v3"] < 0.7          # half panned: under COVER_GOOD, warned
    assert r["spot_coverage"]["v1"] == pytest.approx(1.0)


def _judge_by_spot(verdicts: dict, asked: list):
    def judge(claims, photos):
        names = [n for n, _ in photos]
        asked.append(names)
        vid = names[-1].split("-", 1)[1]
        return [{"verdict": verdicts.get(vid, "shown"), "reason": f"at {vid}"} for _ in claims]
    return judge


def test_the_claim_is_judged_spot_by_spot_on_last_and_this_visits_pictures(site_a):
    _d, logs, _r, base_k = site_a
    prev = earlier_from("W1", "base", "baseline", base_k)
    asked = []
    r, _ = vv.read(logs["m1"][0], logs["m1"][1], SITE, [prev], [], "monthly",
                   claim="toilet block roof cast", judge=_judge_by_spot({"v2": "not_shown"}, asked))
    assert all(len(a) == 2 and a[0] == "before-" + a[1][4:] for a in asked)
    assert r["spot_verdicts"]["v2"] == "not_shown" and r["spot_verdicts"]["v1"] == "shown"
    assert r["claim_verdict"] == "shown"               # one part, shown at another spot
    assert r["spots_filmed"] == VIEWS


def test_a_whole_work_claim_contradicted_at_one_spot_is_not_shown(site_a):
    _d, logs, _r, base_k = site_a
    prev = earlier_from("W1", "base", "baseline", base_k)
    r, _ = vv.read(logs["m1"][0], logs["m1"][1], SITE, [prev], [], "monthly",
                   claim="walls up to lintel level in all rooms",
                   judge=_judge_by_spot({"v2": "not_shown"}, []))
    assert r["claim_verdict"] == "not_shown" and r["claim_spots_not_shown"] == ["v2"]
    assert r["claim_reason"] == "at v2"


def test_too_few_spots_for_a_big_work_cannot_say_not_shown(site_a):
    _d, logs, _r, base_k = site_a
    prev = earlier_from("W1", "base", "baseline", base_k)
    no = {f"v{k}": "not_shown" for k in range(1, VIEWS + 1)}
    r, _ = vv.read(logs["m1"][0], logs["m1"][1], SITE, [prev], [], "monthly",
                   claim="roof cast", judge=_judge_by_spot(no, []), spots_needed=12)
    assert r["spots_needed"] == 12 and r["claim_verdict"] == "cant_tell"
    r, _ = vv.read(logs["m1"][0], logs["m1"][1], SITE, [prev], [], "monthly",
                   claim="roof cast", judge=_judge_by_spot(no, []), spots_needed=8)
    assert r["claim_verdict"] == "not_shown"


LINE = sitemap.Site("linear", 25.75, 82.69, 12.5, 25.7517, 82.69)      # about 190 m: 4 stretches


def walked(log: dict) -> dict:
    """The log with the GPS walking the line from one end to the other."""
    n = len(log["gps"])
    return dict(log, gps=[dict(g, lat=25.75 + 0.0017 * i / (n - 1), lon=82.69)
                          for i, g in enumerate(log["gps"])])


def test_a_linear_work_keeps_a_picture_of_each_stretch_and_judges_them(site_a):
    _d, logs, _r, _k = site_a
    base_r, base_k = vv.read(logs["base"][0], walked(logs["base"][1]), LINE, [], [], "baseline")
    assert sorted(base_k["stretches"]) == ["s1", "s2", "s3", "s4"]
    assert base_r["spots_filmed"] == VIEWS + 4
    prev = earlier_from("W1", "base", "baseline", base_k, base_r)
    asked = []
    half = dict(walked(logs["m1"][1]))
    half["gps"] = [g for g in half["gps"] if g["lat"] < 25.7509]           # only s1 and s2
    r, _ = vv.read(logs["m1"][0], half, LINE, [prev], [], "monthly", claim="road surfaced",
                   judge=_judge_by_spot({}, asked), stretches_asked=["s1", "s4"])
    judged = {a[1][4:] for a in asked}
    assert {"s1", "s2"} <= judged and "s4" not in judged
    assert r["stretches_missed"] == ["s4"]
