"""The pipeline on a synthetic shot, the dataset on disk, and the model (when torch is there)."""

import json

import numpy as np
import pytest

from drishti_vision import dataset, synthset
from drishti_vision.features import Handcrafted
from drishti_vision.synth import Site


@pytest.fixture(scope="module")
def small_set(tmp_path_factory):
    out = tmp_path_factory.mktemp("ds")
    r = synthset.make(str(out), kinds=("masonry", "road"), seeds=(0, 1), n_frames=26,
                      n_pairs=16, reupload=True)
    return out, r


def test_prepare_a_shot():
    sh = Site("steel", 4, n_frames=20, size=(192, 256)).shot()
    prep = dataset.prepare(sh.site_id, sh.frames, Handcrafted(16))
    assert prep is not None
    assert prep.feats.shape[:3] == prep.valid.shape == (len(prep.index), 12, 16)
    assert 0.5 < prep.valid.mean() <= 1.0
    assert prep.report["aligned"] == len(prep.index)


def test_too_few_frames_are_dropped():
    sh = Site("steel", 4, n_frames=8, size=(192, 256)).shot()
    assert dataset.prepare(sh.site_id, sh.frames, Handcrafted(16)) is None


def test_the_dataset_on_disk(small_set):
    out, r = small_set
    rows = [json.loads(x) for x in (out / "shots.jsonl").read_text().splitlines()]
    assert {x["shot_id"] for x in rows} == {b.shot.site_id for b in r["built"]}
    assert (out / "card.md").read_text().startswith("# Synthetic")
    assert r["leaks"] == []
    # the re-upload of the first site joined it
    first = r["built"][0].shot.site_id
    assert r["site_of"][first] == r["site_of"][f"{first}-reupload"]
    with np.load(out / "labels" / f"{first}.npz") as z:
        assert {"a", "b", "label", "kind", "patches", "truth", "truth_label"} <= set(z.files)


def test_the_teacher_agrees_with_the_truth(small_set):
    _, r = small_set
    s = synthset.teacher_scores(r["built"], n=20)
    assert s["pair_accuracy"] > 0.85 and s["patch_precision"] > 0.8


torch = pytest.importorskip("torch")


def test_model_shapes_and_gradients():
    from drishti_vision.model import build, trainable
    from drishti_vision.stages import N_ALL
    from drishti_vision.train import TrainConfig, order_loss, pair_losses

    m = build("tiny", n_stages=N_ALL)
    a, b = torch.rand(2, 3, 96, 128), torch.rand(2, 3, 96, 128)
    out = m(a, b)
    assert out["map"].shape == (2, 6, 8) and out["pair"].shape == (2,)
    assert out["stage_a"].shape == (2, N_ALL)
    batch = {"map": torch.tensor(np.full((2, 6, 8), -1)), "label": torch.tensor([1, 0]),
             "order": torch.tensor([1, 0]), "stage_a": torch.tensor([0, -1]),
             "stage_b": torch.tensor([3, -1])}
    batch["map"][0, 2, 3] = 1
    ls = pair_losses(out, batch, TrainConfig(data="", out=""))
    ls["total"].backward()
    assert all(torch.isfinite(v) for v in ls.values()) and trainable(m) > 0
    good = order_loss(torch.tensor([[0.0, 1.0, 2.0]]), torch.tensor([[0.0, 0.5, 1.0]]))
    bad = order_loss(torch.tensor([[2.0, 1.0, 0.0]]), torch.tensor([[0.0, 0.5, 1.0]]))
    assert good < bad


def test_handcrafted_backbone_is_frozen():
    from drishti_vision.model import build, trainable

    m = build("handcrafted")
    f = m.encode(torch.rand(1, 3, 96, 128))
    assert f.shape == (1, 6, 8, m.backbone.dim) and not f.requires_grad
    assert trainable(m.backbone) == 0


def test_labels_resample_to_the_students_grid():
    from drishti_vision.train import resample

    lab = np.arange(12, dtype=np.int8).reshape(3, 4)
    assert np.array_equal(resample(lab, (48, 64), 16, (3, 4)), lab)
    assert resample(lab, (48, 64), 16, (6, 8))[5, 7] == lab[2, 3]


def test_a_short_fit_runs_and_measures(small_set, tmp_path):
    from drishti_vision.stages import N_ALL
    from drishti_vision.train import Store, TrainConfig, fit, measure

    out, r = small_set
    sites = sorted(set(r["site_of"].values()))
    cfg = TrainConfig(data=str(out), out=str(tmp_path / "run"), backbone="tiny", size=(96, 128),
                      epochs=1, order_epochs=1, batch=8, n_stages=N_ALL,
                      train_sites=sites[:-1], eval_sites=sites[-1:])
    model, info = fit(cfg)
    assert (tmp_path / "run" / "best.pt").exists() and info["train_pairs"] > 0
    m = measure(model, Store(cfg.data, sites=sites[-1:]), cfg, use_truth=True)
    for k in ("auroc", "false_progress_short", "false_progress_staged", "both_ways",
              "build_up_tau"):
        assert k in m
