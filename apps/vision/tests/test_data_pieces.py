"""Manifest, fetching, stages, shots, pairs, splits, augmentation and measures."""

import http.server
import json
import threading
from functools import partial

import cv2
import numpy as np
import pytest

from drishti_vision import augment as aug
from drishti_vision import evaluate as ev
from drishti_vision import fetch, manifest, splits, stages
from drishti_vision.hindsight import Hindsight
from drishti_vision.pairs import sample, target_map
from drishti_vision.shots import find_cuts, split
from drishti_vision.synth import Site


def _row(**kw):
    base = dict(id="wm-1", url="https://example.org/a.mp4", source="university",
                licence="cc-by", attribution="A Maker", channel="maker", work_type="building",
                material="masonry", country="IN", camera="fixed")
    return manifest.Video(**{**base, **kw})


# -- manifest and fetching ----------------------------------------------------------------------

def test_licences_waiting_for_the_owner_are_refused():
    assert manifest.problems(_row()) == []
    assert "owner" in manifest.problems(_row(licence="cc-by-nd"))[0]
    assert "owner" in manifest.problems(_row(licence="cc-by-nc"))[0]
    assert manifest.problems(_row(attribution=""))
    assert manifest.problems(_row(licence="permission"))          # needs permission_ref
    assert manifest.problems(_row(material="glass"))
    assert manifest.problems(_row(channel=""))


def test_manifest_round_trip_and_duplicates(tmp_path):
    p = tmp_path / "m.jsonl"
    manifest.save(p, [_row(), _row(id="wm-2")])
    assert [v.id for v in manifest.load(p)] == ["wm-1", "wm-2"]
    manifest.save(p, [_row(), _row()])
    with pytest.raises(ValueError):
        manifest.load(p)


def test_commons_licences():
    assert fetch.commons_licence("CC BY-SA 4.0") == "cc-by-sa"
    assert fetch.commons_licence("CC BY 3.0") == "cc-by"
    assert fetch.commons_licence("CC BY-NC 4.0") is None
    assert fetch.commons_licence("Public domain") == "pd"
    info = {"query": {"pages": {"1": {"imageinfo": [{
        "url": "https://upload.wikimedia.org/x.webm",
        "extmetadata": {"LicenseShortName": {"value": "CC0"}}}]}}}}
    assert fetch.commons_file(info) == ("https://upload.wikimedia.org/x.webm", "cc0")


def test_youtube_waits_for_the_owner(tmp_path):
    with pytest.raises(PermissionError):
        fetch.fetch(_row(source="youtube", url="https://www.youtube.com/watch?v=x"), tmp_path)
    c = fetch.youtube_candidate({"id": {"videoId": "abc"}, "snippet": {
        "channelTitle": "Build Co", "channelId": "UC1", "title": "House timelapse"}})
    assert c["id"] == "yt-abc" and c["licence"] == "cc-by" and c["channel"] == "UC1"


@pytest.fixture()
def server(tmp_path):
    (tmp_path / "a.mp4").write_bytes(b"video bytes")
    handler = partial(http.server.SimpleHTTPRequestHandler, directory=str(tmp_path))
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}"
    httpd.shutdown()


def test_fetch_records_and_checks_the_checksum(server, tmp_path, monkeypatch):
    monkeypatch.setattr(fetch, "POLITE_S", 0)
    v = _row(url=f"{server}/a.mp4")
    out = fetch.fetch(v, tmp_path / "dl")
    assert out.read_bytes() == b"video bytes" and len(v.sha256) == 64
    v2 = _row(url=f"{server}/a.mp4", sha256="0" * 64)
    with pytest.raises(ValueError):
        fetch.fetch(v2, tmp_path / "dl")


# -- stages -------------------------------------------------------------------------------------

def test_stage_marks():
    marks = [(0, "cleared"), (5, "excavated"), (9, "footing")]
    pf = stages.per_frame(12, "building", marks)
    assert pf.tolist() == [0] * 5 + [1] * 4 + [2] * 3
    assert stages.check_marks("building", [(5, "footing"), (3, "plinth")])
    assert stages.check_marks("building", [(1, "roof"), (4, "walls")])
    assert stages.global_index("road", 1) == len(stages.STAGES["building"]) + 1
    assert stages.global_index("road", -1) == -1
    assert stages.describe("building", "roof") == "Roof slab cast"


# -- shots --------------------------------------------------------------------------------------

def test_cuts_titles_and_pans_are_found():
    a = Site("masonry", 1, n_frames=14, size=(192, 256)).shot().frames
    b = Site("road", 2, n_frames=14, size=(192, 256)).shot().frames
    title = np.zeros((4, 192, 256, 3), np.uint8)
    for f in title:
        cv2.putText(f, "OUR NEW HALL", (20, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    big = cv2.resize(Site("wood", 3, n_frames=1, size=(192, 256)).shot().frames[0], (640, 192))
    pan = np.stack([big[:, x:x + 256] for x in range(0, 14 * 25, 25)])
    frames = np.concatenate([a, title, b, pan])
    cuts = find_cuts(frames)
    assert 14 in cuts and 18 in cuts and 32 in cuts
    kept = [s for s in split(frames) if s.keep]
    assert [(s.start, s.end) for s in kept] == [(0, 14), (18, 32)]


# -- pairs --------------------------------------------------------------------------------------

def _teacher():
    f = np.zeros((20, 2, 2, 3), np.float32)
    f[:] = (1, 0, 0)
    f[10:, 0, 0] = (0, 1, 0)
    return Hindsight(f, np.ones((20, 2, 2), bool), lo=0.3, hi=0.6, radius=0)


def test_pairs_are_balanced_and_swapped_pairs_are_never_progress():
    ps = sample("s", _teacher(), 20, np.random.default_rng(0))
    fwd = [p for p in ps if p.kind != "swapped"]
    assert sum(p.label for p in fwd) == len(fwd) - sum(p.label for p in fwd)
    sw = [p for p in ps if p.kind == "swapped"]
    assert sw and all(p.label == 0 and p.a > p.b and (p.patches != 1).all() for p in sw)
    assert target_map(np.array([[1, 0], [2, -1]])).tolist() == [[1, 0], [0, -1]]


# -- splits -------------------------------------------------------------------------------------

def _info(sid, video, channel, material, sig):
    v = np.array(sig, float)
    return splits.ShotInfo(sid, video, channel, material, v / np.linalg.norm(v))


def test_duplicates_join_and_channels_stay_together():
    shots = [_info("a1", "va", "c1", "masonry", [1, 0, 0]),
             _info("a2", "va", "c1", "masonry", [0, 1, 0]),          # same video: same site
             _info("b1", "vb", "c2", "masonry", [1, 0.01, 0]),       # a re-upload of a1
             _info("c1", "vc", "c3", "wood", [0, 0, 1]),
             _info("d1", "vd", "c3", "road", [0, 1, 1])]             # same channel as c1
    site_of = splits.sites(shots)
    assert site_of["a1"] == site_of["a2"] == site_of["b1"]
    assert site_of["c1"] != site_of["d1"]
    split_of = splits.assign(shots, site_of, seed=1)
    assert split_of[site_of["c1"]] == split_of[site_of["d1"]]
    assert splits.leaks(shots, site_of, split_of) == []
    bad = dict(split_of)
    bad[site_of["d1"]] = "test" if split_of[site_of["c1"]] != "test" else "train"
    assert splits.leaks(shots, site_of, bad)
    loto = splits.leave_one_type_out(shots, site_of)
    assert site_of["d1"] not in loto["wood"]["train"]       # its channel has the held-out type
    assert loto["wood"]["test"] == [site_of["c1"]]


# -- augmentation -------------------------------------------------------------------------------

def test_labels_follow_the_picture():
    lab = np.zeros((4, 4), np.int8)
    lab[1, 1] = 1
    assert np.array_equal(aug.warp_patches(lab, np.eye(3), 16), lab)
    shift = np.array([[1, 0, 16], [0, 1, 0], [0, 0, 1]], float)
    moved = aug.warp_patches(lab, shift, 16)
    assert moved[1, 2] == 1 and (moved[:, 0] == -1).all()


def test_pasting_never_makes_progress_and_hides_what_it_covers():
    rng = np.random.default_rng(3)
    img = np.full((64, 64, 3), 120, np.uint8)
    lab = np.ones((4, 4), np.int8)
    lab[:, :2] = 0
    out, new, pasted = aug.paste_transients(img, lab, 16, rng, n=4)
    assert pasted.any()
    assert ((new == 1) <= (lab == 1)).all()
    assert (new[lab == 0] == 0).all()


def test_augmentation_is_repeatable_and_keeps_shapes():
    a = (np.random.default_rng(0).random((96, 128, 3)) * 255).astype(np.uint8)
    lab = np.zeros((6, 8), np.int8)
    r1 = aug.augment_pair(a, a, lab, 16, np.random.default_rng(5))
    r2 = aug.augment_pair(a, a, lab, 16, np.random.default_rng(5))
    assert all(np.array_equal(x, y) for x, y in zip(r1, r2, strict=True))
    assert r1[0].shape == a.shape and r1[2].shape == lab.shape
    e = aug.erase_corners(a, np.random.default_rng(1))
    assert np.array_equal(e[30:60, 40:90], a[30:60, 40:90])


# -- measures -----------------------------------------------------------------------------------

def test_measures():
    assert ev.auroc([0.1, 0.2, 0.8, 0.9], [0, 0, 1, 1]) == 1.0
    assert ev.auroc([0.9, 0.8, 0.2, 0.1], [0, 0, 1, 1]) == 0.0
    assert ev.auroc([0.5, 0.5], [0, 1]) == 0.5
    assert ev.kendall_tau([1, 2, 3], [10, 20, 30]) == pytest.approx(1.0)
    assert ev.kendall_tau([3, 2, 1], [10, 20, 30]) == pytest.approx(-1.0)
    acc, cover = ev.selective([0.1, 0.5, 0.9], [0, 1, 1])
    assert acc == 1.0 and cover == pytest.approx(2 / 3)
    assert ev.ece([0.0, 1.0], [0, 1]) == 0.0
    s = ev.patch_scores(np.array([[1, 0], [1, 0]], bool), np.array([[1, 1], [0, -1]]))
    assert (s["tp"], s["fp"], s["fn"]) == (1, 1, 1)
    assert ev.both_ways([0.9, 0.9], [0.8, 0.1]) == 0.5
    assert json.dumps(ev.false_progress([0.2, 0.7]))
