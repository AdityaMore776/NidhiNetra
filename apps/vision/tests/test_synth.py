"""The synthetic sites: deterministic, and their truth behaves like real work."""

import numpy as np
import pytest

from drishti_vision.stages import STAGES
from drishti_vision.synth import KINDS, Site, truth_pair


@pytest.fixture(scope="module")
def shot():
    return Site("masonry", 7, n_frames=30, size=(96, 128), bury=True).shot()


def test_the_same_seed_gives_the_same_shot(shot):
    again = Site("masonry", 7, n_frames=30, size=(96, 128), bury=True).shot()
    assert np.array_equal(shot.frames, again.frames)


def test_work_is_never_removed(shot):
    once = np.maximum.accumulate(shot.built > 0, axis=0)
    assert np.array_equal(once, shot.built > 0)


def test_stages_only_go_up(shot):
    assert np.all(np.diff(shot.stage) >= 0)
    assert shot.stage[-1] == len(STAGES["building"]) - 1


def test_the_overlay_sits_at_the_edges(shot):
    h = shot.overlay.shape[0]
    rows = np.nonzero(shot.overlay.any(axis=1))[0]
    assert shot.overlay.any()
    assert np.all((rows < h * 0.2) | (rows > h * 0.8))


def test_buried_work_is_marked(shot):
    assert shot.buried_ids
    assert any(e["buried"] for e in shot.elements)


def test_a_variant_shows_the_same_work_differently():
    s = Site("road", 3, n_frames=20, size=(96, 128))
    a, built_a, _, _ = s.render(15, 0)
    b, built_b, _, _ = s.render(15, 1)
    assert np.array_equal(built_a, built_b)
    assert not np.array_equal(a, b)


def test_truth_of_a_pair(shot):
    t1, t2 = 0, len(shot.stage) - 1
    tr, _ = truth_pair(shot, t1, t2, 16)
    assert (tr == 1).any()
    same, _ = truth_pair(shot, 5, 5, 16)
    assert not (same == 1).any()


@pytest.mark.parametrize("kind", KINDS)
def test_every_kind_builds(kind):
    s = Site(kind, 1, n_frames=12, size=(96, 128))
    sh = s.shot()
    assert sh.frames.shape == (12, 96, 128, 3)
    assert (sh.built[-1] > 0).sum() > (sh.built[0] > 0).sum()
