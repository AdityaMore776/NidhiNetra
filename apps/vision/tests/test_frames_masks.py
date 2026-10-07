"""Frames, masks, overlays, alignment and features on small pictures."""

import cv2
import numpy as np
import pytest

from drishti_vision.features import Handcrafted, patch_share, smooth
from drishti_vision.frames import (
    daylight_normalise,
    motion_mask,
    quality,
    read_video,
    temporal_median,
    write_video,
)
from drishti_vision.masks import COCO_TRANSIENT, MotionMasker, keep_transient
from drishti_vision.overlays import corner_bands, overlay_mask
from drishti_vision.register import align_shot
from drishti_vision.synth import Site


def _textured(seed=0, h=96, w=128):
    rng = np.random.default_rng(seed)
    small = rng.integers(0, 255, (h // 8, w // 8, 3), dtype=np.uint8)
    return cv2.resize(small, (w, h), interpolation=cv2.INTER_NEAREST)


def test_quality_flags_dark_and_blurred_frames():
    img = _textured()
    assert quality(img).usable
    assert not quality((img * 0.1).astype(np.uint8)).usable
    assert not quality(cv2.GaussianBlur(img, (0, 0), 6)).usable


def test_temporal_median_removes_a_passer_by():
    frames = np.repeat(_textured()[None], 5, axis=0)
    frames[2, 40:60, 50:60] = (255, 120, 0)
    out = temporal_median(frames, 1)
    assert np.array_equal(out[2], frames[0])


def test_motion_mask_sees_a_person_not_the_light_or_a_shadow():
    base = _textured()
    frames = np.repeat(base[None], 5, axis=0).astype(np.float32)
    frames[2] *= 0.7                                   # a dull moment
    frames[3, :, :64] *= 0.6                           # half the view in shadow
    frames = np.clip(frames, 0, 255).astype(np.uint8)
    frames[1, 40:56, 60:66] = (255, 120, 0)            # a worker
    m = motion_mask(frames, 1)
    assert m[1, 44:52, 61:65].all()
    assert m[2].mean() < 0.02 and m[3].mean() < 0.06
    assert MotionMasker().masks(frames).shape == frames.shape[:3]


def test_daylight_normalise_evens_a_dull_frame():
    base = _textured()
    frames = np.stack([base, (base * 0.6).astype(np.uint8)])
    out = daylight_normalise(frames).astype(float)
    assert abs(out[0].mean() - out[1].mean()) < 6


def test_video_round_trip(tmp_path):
    frames = np.stack([_textured(i) for i in range(6)])
    p = tmp_path / "v.mp4"
    write_video(str(p), frames, fps=5)
    back, fps = read_video(str(p), n=3, width=128)
    assert back.shape == (3, 96, 128, 3) and fps == pytest.approx(5, abs=0.5)


def test_detector_keeps_only_listed_confident_things():
    labels = np.array([1, 3, 15, 1])                   # person, car, bench, person
    scores = np.array([0.9, 0.8, 0.99, 0.3])
    assert keep_transient(labels, scores).tolist() == [True, True, False, False]
    assert 1 in COCO_TRANSIENT


@pytest.fixture(scope="module")
def site_shot():
    return Site("concrete_frame", 2, n_frames=14, size=(192, 256)).shot()


def test_overlays_found_where_the_stamp_is(site_shot):
    m = overlay_mask(site_shot.frames)
    truth = site_shot.overlay
    iou = (m & truth).sum() / (m | truth).sum()
    assert iou > 0.5
    h = m.shape[0]
    assert not m[int(h * 0.3):int(h * 0.7)].any()     # never the work in the middle
    assert corner_bands(100, 200).sum() > 0


def test_alignment_undoes_the_shake(site_shot):
    sh = site_shot
    _, valid, rep = align_shot(sh.frames, ref=0, mask=~overlay_mask(sh.frames))
    assert all(a.ok for a in rep)
    p = np.array([[[80, 60]], [[180, 140]]], np.float32)
    for t, a in enumerate(rep):
        got = cv2.perspectiveTransform(cv2.transform(p, sh.shake[t]), a.homography)
        want = cv2.transform(p, sh.shake[0])
        assert np.abs(got - want).max() < 1.5
    assert valid[1].mean() > 0.8


def test_alignment_refuses_another_place(site_shot):
    other = Site("road", 9, n_frames=2, size=(192, 256)).shot().frames[:1]
    frames = np.concatenate([site_shot.frames[:3], other])
    _, _, rep = align_shot(frames, ref=0)
    assert not rep[3].ok


def test_features_are_unit_length_and_steady_under_light():
    img = _textured()
    ex = Handcrafted(16)
    f = ex.extract(np.stack([img, np.clip(img * 0.7, 0, 255).astype(np.uint8),
                             _textured(5)]))
    assert np.allclose(np.linalg.norm(f, axis=-1), 1, atol=1e-4)
    same = (1 - (f[0] * f[1]).sum(-1)).mean()
    other = (1 - (f[0] * f[2]).sum(-1)).mean()
    assert same < other / 3


def test_patch_share_and_smooth():
    m = np.zeros((2, 32, 32), bool)
    m[0, :16, :16] = True
    s = patch_share(m, 16)
    assert s.shape == (2, 2, 2) and s[0, 0, 0] == 1 and s[1].sum() == 0
    f = np.zeros((3, 1, 1, 2), np.float32)
    f[:, 0, 0] = (1, 0)
    f[1, 0, 0] = (0, 1)                                 # masked in frame 1
    v = np.ones((3, 1, 1), bool)
    v[1] = False
    out = smooth(f, v, 1)
    assert np.allclose(out[1, 0, 0], (1, 0))
