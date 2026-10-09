r"""T146: the construction-progress pipeline, measured on synthetic sites where the truth is known.

Synthetic timelapses (apps/vision/drishti_vision/synth.py) of five kinds of work (masonry, concrete
frame, wood, steel, road), each with people, vehicles, scaffolding, stacked materials, a sweeping
shadow, changing light, camera shake, a date stamp and a logo, covered work (plaster over brick)
and, on some sites, buried work (earth backfilled over footings). Every shot goes through the real
pipeline (dataset.prepare: overlays, alignment, masks, features; the hindsight teacher; pairs;
splits by site).

Part 1, the teacher against the truth: patch precision, recall and IoU of "progress"; pair labels;
the auto-calibrated thresholds against fixed ones; with and without stage marks; buried work.
Part 2, the masks and splits: date stamps found, people masked, re-uploads joined, no leaks.
Part 3, the student (PyTorch, CPU: a frozen hand-made feature backbone and the trained head),
measured against the TRUTH on sites it never saw:
  in-type     trained on some sites of every kind, tested on other sites of every kind
  no-augment  the same without augmentation (what augmentation buys)
  LOTO        trained on four kinds, tested on the fifth (the "wooden houses only" worry)

Numbers here are about the pipeline on synthetic pictures. They say nothing about real sites: a
frozen DINOv2 backbone on real timelapses (T148) is what the plan measures for that.

Writes results/vision_synth_trial.txt and .json. The dataset goes to data/cache/ (not in git).

Run:  python data/trial/vision_synth_trial.py [--seeds 6] [--epochs 10] [--no-student]
      (with numpy, opencv-python-headless and torch: pip install -e apps/vision[train])
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "apps" / "vision"))

from drishti_vision import synthset  # noqa: E402
from drishti_vision.features import patch_share  # noqa: E402
from drishti_vision.hindsight import Hindsight  # noqa: E402
from drishti_vision.overlays import overlay_mask  # noqa: E402
from drishti_vision.synth import KINDS, Site  # noqa: E402

RESULTS = ROOT / "data" / "trial" / "results"
CACHE = ROOT / "data" / "cache" / "vision_synth"


def _round(d: dict, n: int = 4) -> dict:
    return {k: (round(v, n) if isinstance(v, float) else v) for k, v in d.items()}


def teacher_part(built: list) -> dict:
    out = {"all": _round(synthset.teacher_scores(built, n=60))}
    by_kind = defaultdict(list)
    for b in built:
        by_kind[b.shot.kind].append(b)
    out["by_kind"] = {k: _round(synthset.teacher_scores(v, n=60)) for k, v in by_kind.items()}
    out["thresholds"] = {"lo_range": [round(min(b.teacher.lo for b in built), 3),
                                      round(max(b.teacher.lo for b in built), 3)]}
    # the shot's own noise (calibrate) against fixed thresholds, and without stage marks
    variants = {f"fixed lo={lo:.2f}": dict(lo=lo, hi=2 * lo) for lo in (0.1, 0.15, 0.2, 0.25)}
    variants["auto, no stage marks"] = {}
    for name, kw in variants.items():
        swapped = []
        for b in built:
            t = Hindsight(b.prep.feats, b.prep.valid, stages=None, **kw)
            swapped.append(synthset.Built(b.shot, b.prep, t, b.pairs, b.ref_raw, b.built,
                                          b.temporary))
        out[name] = _round(synthset.teacher_scores(swapped, n=60))
    return out


def masks_part(built: list, r: dict) -> dict:
    ious, people_cov, other_flag = [], [], []
    for b in built:
        sh = b.shot
        m = overlay_mask(sh.frames[b.prep.index])
        ious.append((m & sh.overlay).sum() / max(1, (m | sh.overlay).sum()))
        # people and passing trucks: temporary pixels that are not scaffolding, stacks or machines
        site = Site(sh.kind, sh.seed, n_frames=len(sh.stage), size=sh.frames.shape[1:3])
        lasting = np.zeros_like(sh.temporary)
        for o in site.temporaries:
            lasting[o.start:o.end] |= o.mask
        people = synthset._to_ref((sh.temporary & ~lasting)[b.prep.index].astype(np.uint8),
                                  sh.shake[b.ref_raw]) > 0
        moving = patch_share(people, b.prep.patch) > 0.3
        act = b.prep.activity.astype(np.float32) > 0.3
        if moving.any():
            people_cov.append(float((act & moving).sum() / moving.sum()))
        other_flag.append(float((act & ~moving).mean()))
    first = r["built"][0].shot.site_id
    return {"overlay_iou_mean": round(float(np.mean(ious)), 4),
            "overlay_iou_min": round(float(np.min(ious)), 4),
            "people_patches_masked": round(float(np.mean(people_cov)), 4),
            "other_patches_masked": round(float(np.mean(other_flag)), 4),
            "frames_aligned": round(float(np.mean([b.prep.report["aligned"] /
                                                   b.prep.report["usable"] for b in built])), 4),
            "reupload_joined": r["site_of"].get(f"{first}-reupload") == r["site_of"][first],
            "leaks": r["leaks"], "shots": len(r["built"]),
            "sites": len(set(r["site_of"].values()))}


def student_part(r: dict, data: Path, seeds: int, epochs: int, size: tuple[int, int]) -> dict:
    from drishti_vision.stages import N_ALL
    from drishti_vision.train import Store, TrainConfig, fit, measure

    kind_seed = {}
    for b in r["built"]:
        kind_seed.setdefault(r["site_of"][b.shot.site_id], (b.shot.kind, b.shot.seed % 1000))
    calib_seed, test_seeds = seeds - 3, {seeds - 2, seeds - 1}

    def sites(pred):
        return sorted(s for s, ks in kind_seed.items() if pred(*ks))

    folds = {
        "in-type": (sites(lambda k, s: s < calib_seed), sites(lambda k, s: s == calib_seed),
                    sites(lambda k, s: s in test_seeds), True),
        "in-type, no augmentation": (sites(lambda k, s: s < calib_seed),
                                     sites(lambda k, s: s == calib_seed),
                                     sites(lambda k, s: s in test_seeds), False),
    }
    for held in KINDS:
        folds[f"LOTO {held}"] = (
            sites(lambda k, s, h=held: k != h and s != calib_seed),
            sites(lambda k, s, h=held: k != h and s == calib_seed),
            sites(lambda k, s, h=held: k == h), True)
    out = {}
    nan = float("nan")
    for name, (train, calib, test, augment) in folds.items():
        t0 = time.time()
        cfg = TrainConfig(data=str(data), out=str(data / "runs" / name.replace(" ", "_")),
                          backbone="handcrafted", size=size, epochs=epochs, order_epochs=3,
                          batch=16, lr=1e-3, n_stages=N_ALL, train_sites=train,
                          eval_sites=calib, augment=augment)
        model, info = fit(cfg)
        test_m = measure(model, Store(data, sites=test), cfg, use_truth=True)
        train_m = measure(model, Store(data, sites=train), cfg, use_truth=True, audits=False)
        out[name] = {"train_sites": len(train), "test_sites": len(test),
                     "train_pairs": info["train_pairs"], "trainable_weights": info["trainable"],
                     "test": test_m, "train_auroc": train_m.get("auroc"),
                     "gap": round(train_m.get("auroc", nan) - test_m.get("auroc", nan), 4),
                     "minutes": round((time.time() - t0) / 60, 1)}
        print(name, json.dumps(out[name]), flush=True)
    return out


def report(res: dict) -> str:
    t, m = res["teacher"], res["masks"]
    lines = ["T146: the construction-progress pipeline on synthetic sites (truth known)", "",
             f"Sites: {m['sites']} ({m['shots']} shots, one a re-upload), "
             f"{res['args']['frames']} frames each, kinds {', '.join(KINDS)}.", "",
             "1. The hindsight teacher against the truth (random forward pairs):", ""]
    a = t["all"]
    lines += [f"  patch precision {a['patch_precision']:.3f}, recall {a['patch_recall']:.3f}, "
              f"IoU {a['patch_iou']:.3f}",
              f"  pairs labelled {a['pairs_labelled']:.1%}, "
              f"of which right {a['pair_accuracy']:.1%}",
              f"  buried patches called progress {a['buried_patches_called_progress']:.1%} "
              f"(no picture can show them; stage marks set those pairs)",
              f"  thresholds from each shot's own noise: lo {t['thresholds']['lo_range'][0]} to "
              f"{t['thresholds']['lo_range'][1]}", "", "  by kind:"]
    for k, v in t["by_kind"].items():
        lines.append(f"    {k:15s} precision {v['patch_precision']:.3f} recall "
                     f"{v['patch_recall']:.3f} pairs right {v['pair_accuracy']:.1%}")
    lines += ["", "  the auto thresholds against fixed ones (no stage marks unless auto):"]
    for name in [k for k in t if k.startswith("fixed") or k.startswith("auto")]:
        v = t[name]
        lines.append(f"    {name:22s} precision {v['patch_precision']:.3f} recall "
                     f"{v['patch_recall']:.3f} IoU {v['patch_iou']:.3f} pairs labelled "
                     f"{v['pairs_labelled']:.1%} right {v['pair_accuracy']:.1%}")
    lines += ["", "2. Masks and splits:", "",
              f"  date stamp and logo found: IoU mean {m['overlay_iou_mean']:.3f}, "
              f"lowest {m['overlay_iou_min']:.3f}",
              f"  patches with people or passing trucks masked: {m['people_patches_masked']:.1%}; "
              f"other patches masked {m['other_patches_masked']:.1%}",
              f"  frames aligned: {m['frames_aligned']:.1%}",
              f"  the re-upload joined its original's site: {m['reupload_joined']}; "
              f"leaks between splits: {len(m['leaks'])}"]
    if "student" in res:
        lines += ["", "3. The student against the truth, on sites it never saw "
                  "(frozen hand-made features + trained head, CPU):", "",
                  "  fold                       AUROC  gap   patchIoU  light  staged  bothways  "
                  "build-up tau"]
        for name, v in res["student"].items():
            s = v["test"]
            lines.append(f"  {name:26s} {s['auroc']:.3f}  {v['gap']:+.3f}  "
                         f"{s['patch_iou']:.3f}     {s['false_progress_short']:.3f}  "
                         f"{s['false_progress_staged']:.3f}   {s['both_ways']:.3f}     "
                         f"{s['build_up_tau']:.3f}")
        lines += ["",
                  "  gap: train AUROC minus test AUROC (memorising shows as a large gap).",
                  "  light: short-gap pairs with no work called progress. staged: no-work pairs "
                  "with people, machines, scaffolds and stacks pasted in, called progress.",
                  "  bothways: progress pairs also called progress when swapped."]
    lines += ["", "Synthetic pictures only: these numbers check the pipeline and its measures, "
              "not accuracy on real sites (T148)."]
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=6, help="sites of each kind")
    ap.add_argument("--frames", type=int, default=60)
    ap.add_argument("--pairs", type=int, default=60)
    ap.add_argument("--epochs", type=int, default=10)
    ap.add_argument("--size", default="96x128", help="the student's input, HxW")
    ap.add_argument("--no-student", action="store_true")
    args = ap.parse_args()
    t0 = time.time()
    r = synthset.make(str(CACHE), seeds=tuple(range(args.seeds)), n_frames=args.frames,
                      n_pairs=args.pairs)
    print(f"built {len(r['built'])} shots in {time.time() - t0:.0f} s", flush=True)
    res = {"args": vars(args), "teacher": teacher_part(r["built"]),
           "masks": masks_part(r["built"], r)}
    print(json.dumps(res["teacher"]["all"]), json.dumps(res["masks"]), flush=True)
    if not args.no_student:
        h, w = (int(x) for x in args.size.split("x"))
        res["student"] = student_part(r, CACHE, args.seeds, args.epochs, (h, w))
    res["minutes"] = round((time.time() - t0) / 60, 1)
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "vision_synth_trial.json").write_text(json.dumps(res, indent=1, default=str))
    text = report(res)
    (RESULTS / "vision_synth_trial.txt").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
