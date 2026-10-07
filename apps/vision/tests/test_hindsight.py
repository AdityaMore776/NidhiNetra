"""The hindsight teacher on hand-made features, where every right answer is obvious."""

import numpy as np
import pytest

from drishti_vision.hindsight import (
    NONE,
    PROGRESS,
    TEMPORARY,
    UNKNOWN,
    Hindsight,
    calibrate,
)

T = 24
E = np.eye(4, dtype=np.float32)          # four clearly different looks


def _feats():
    """2x3 patches over 24 frames:
    (0,0) never changes                       -> none
    (0,1) a wall appears at 8 and stays       -> progress
    (0,2) scaffolding from 5 to 10, then gone -> temporary
    (1,0) cement at 8, tiles over it at 14    -> progress (covered work never goes back)
    (1,1) something appears at 22             -> unknown (no future to check)
    (1,2) masked in every frame               -> unknown
    """
    f = np.zeros((T, 2, 3, 4), np.float32)
    f[:] = E[0]
    f[8:, 0, 1] = E[1]
    f[5:10, 0, 2] = E[2]
    f[8:, 1, 0] = E[1]
    f[14:, 1, 0] = E[3]
    f[22:, 1, 1] = E[2]
    valid = np.ones((T, 2, 3), bool)
    valid[:, 1, 2] = False
    return f, valid


def _teacher(**kw):
    f, v = _feats()
    return Hindsight(f, v, lo=0.3, hi=0.6, radius=0, **kw)


def test_progress_lasts_and_temporary_goes_back():
    p = _teacher().patches(2, 9)
    assert p[0, 0] == NONE
    assert p[0, 1] == PROGRESS
    assert p[0, 2] == TEMPORARY
    assert p[1, 0] == PROGRESS


def test_covered_work_is_still_progress():
    """Tiles over cement: from cement (t1=10) to tiles (t2=16) is progress; from bare ground to
    tiles too. The final scene never looks like the cement, and never needs to."""
    h = _teacher()
    assert h.patches(10, 16)[1, 0] == PROGRESS
    assert h.patches(2, 16)[1, 0] == PROGRESS


def test_the_end_of_the_shot_is_unknown_and_masked_patches_too():
    p = _teacher().patches(2, 22)
    assert p[1, 1] == UNKNOWN            # appeared at 22: only 2 frames left to check
    assert p[1, 2] == UNKNOWN            # masked throughout


def test_pair_labels():
    h = _teacher()
    assert h.label(2, 9).label == 1
    assert h.label(0, 4).label == 0      # nothing happened yet
    assert h.label(11, 13).label == 0    # the scaffold came and went before 11


def test_stage_marks_overrule_what_cannot_be_seen():
    """Buried work: the pictures say nothing changed, the marks say a stage was done."""
    stages = np.zeros(T, np.int16)
    stages[3:] = 2
    h = _teacher(stages=stages)
    lab = h.label(0, 4)
    assert lab.label == 1 and lab.by_stage


def test_smoothing_ignores_a_single_frame_blip():
    f, v = _feats()
    f[12, 0, 0] = E[3]                   # one frame of something passing
    h = Hindsight(f, v, lo=0.3, hi=0.6, radius=1)
    assert h.patches(10, 12)[0, 0] == NONE


def test_bad_arguments():
    h = _teacher()
    with pytest.raises(ValueError):
        h.patches(5, 5)
    f, v = _feats()
    with pytest.raises(ValueError):
        Hindsight(f, v, lo=0.5, hi=0.4)


def test_calibration_follows_the_noise():
    rng = np.random.default_rng(0)
    base = rng.normal(size=(1, 4, 4, 16)).astype(np.float32)
    quiet = base + rng.normal(scale=0.02, size=(40, 4, 4, 16))
    noisy = base + rng.normal(scale=0.3, size=(40, 4, 4, 16))
    v = np.ones((40, 4, 4), bool)

    def unit(x):
        return x / np.linalg.norm(x, axis=-1, keepdims=True)

    lo_q, hi_q = calibrate(unit(quiet), v, floor=0.0)
    lo_n, hi_n = calibrate(unit(noisy), v, floor=0.0)
    assert hi_q == pytest.approx(2 * lo_q)
    assert lo_n > lo_q
