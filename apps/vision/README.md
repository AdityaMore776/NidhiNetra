# DRISHTI vision (T146): seeing real construction progress

A dataset pipeline and a model that learns to tell **permanent work added** (a wall, a slab,
tiles over cement) from everything else on a site (people, machines, scaffolding, stacked
materials, light, shadows, a moving camera). The design and the reasons behind it are in
[`docs/plans/T146-site-progress-vision.md`](../../docs/plans/T146-site-progress-vision.md).

```
videos ─► manifest ─► shots ─► aligned, masked frames ─► hindsight teacher ─► pairs ─► splits by site
                                                                                         │
                                       student: two frames ─► progress map, yes/no, stage ◄┘
```

## The idea in one paragraph

A timelapse knows its own future. The **hindsight teacher** looks at a whole shot and calls a
change "progress" only if that place **never goes back** to how it looked before: scaffolding
comes down, bricks get used, people leave, shadows move on, but a wall stays (and tiles laid over
cement never turn back into bare ground). A **student** model then learns to give the same answer
from only **two** frames, which is all a monthly site visit has.

## Setup

```bash
cd apps/vision
python -m venv .venv
.venv/bin/pip install -e .[dev]          # Windows: .venv\Scripts\pip.exe install -e .[dev]
.venv/bin/pip install -e .[train]        # + PyTorch, for the model (Kaggle already has it)
.venv/bin/pytest -q
```

## The steps

| Step | Command | Where |
|---|---|---|
| 1. List videos | add rows to a `manifest.jsonl` (one a video: url, licence, attribution, channel, work type, material, camera) | by hand, or `python -m drishti_vision search "house construction timelapse"` (YouTube CC, needs `YOUTUBE_API_KEY`) |
| 2. Check | `python -m drishti_vision check manifest.jsonl` | refuses licences waiting for the owner |
| 3. Download | `python -m drishti_vision fetch manifest.jsonl --dest videos/` | records each file's sha256 |
| 4. Build the dataset | `python -m drishti_vision build manifest.jsonl --videos videos/ --out data/` | CPU works (`--backbone handcrafted`); DINOv2 is better and wants a GPU |
| 5. Mark stages (optional) | `marks.jsonl`: per shot, the frame where each stage begins (`stages.py`); re-run step 4 with `--marks` | frame numbers are those of the shot as stored |
| 6. Train | `python -m drishti_vision train --data data/ --out run/` | Kaggle's free GPU: `kaggle/train_on_kaggle.py` |
| 7. Measure | `python -m drishti_vision measure --data data/ --run run/best.pt --split test` | every number of plan §8 |

Videos, frames and the built dataset **never enter git** (the repo is public). Only the manifest,
the labels' code and the measured numbers do.

## What is in the package

| Module | Does |
|---|---|
| `manifest.py`, `fetch.py` | the manifest, the licence allow-list, polite downloads with checksums |
| `shots.py`, `frames.py`, `register.py` | cuts, still-camera shots, quality, alignment, moving-thing masks |
| `overlays.py`, `masks.py` | date stamps and logos; people and vehicles (motion, or a detector) |
| `features.py` | patch features: hand-made (CPU) or DINOv2 (`model.Dinov2Extractor`) |
| `hindsight.py` | the teacher: progress / temporary / none / unknown, per patch and per pair |
| `stages.py` | the stage lists, worded as agencies word claims |
| `pairs.py`, `splits.py`, `augment.py` | pairs, splits by site and channel, leave-one-type-out, augmentations |
| `dataset.py` | prepare a shot, write the tuned dataset with its card |
| `model.py`, `train.py`, `evaluate.py` | the student, its training, every measure and audit |
| `synth.py`, `synthset.py` | synthetic sites with exact truth, for testing all of the above |

## Measured so far

Only on synthetic sites (`data/trial/vision_synth_trial.py`, results in
`data/trial/results/vision_synth_trial.txt`). Those numbers check the pipeline, not accuracy on
real sites: that needs the real videos (T147) and a GPU run (T148).
