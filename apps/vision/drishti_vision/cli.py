"""The pipeline from the command line (plan §3). `python -m drishti_vision <step> ...`

  check    MANIFEST                          every row's problems (licence, fields)
  search   "QUERY" [--max 25]                YouTube Creative Commons candidates (needs
                                             YOUTUBE_API_KEY), as manifest rows to check by hand
  fetch    MANIFEST --dest DIR               download, record sha256 (YouTube waits for the owner)
  build    MANIFEST --videos DIR --out DATA  shots -> clean frames -> teacher -> pairs -> splits
  synth    --out DATA                        a synthetic dataset (truth attached), for testing
  train    --data DATA --out RUN             the student (plan §7)
  measure  --data DATA --run RUN/best.pt     plan §8.1 on a split
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np

from drishti_vision import dataset, fetch, manifest, pairs, splits, stages, synthset
from drishti_vision.features import Handcrafted
from drishti_vision.frames import read_video
from drishti_vision.shots import split as split_shots


def _extractor(name: str, device: str):
    if name == "handcrafted":
        return Handcrafted(16)
    from drishti_vision.model import Dinov2Extractor
    return Dinov2Extractor(name, device)


def _fit_width(frames: np.ndarray, width: int, patch: int) -> np.ndarray:
    """Resize so both sides are multiples of the patch (DINOv2's is 14)."""
    h, w = frames.shape[1:3]
    nw = width // patch * patch
    nh = max(patch, round(h * nw / w) // patch * patch)
    return np.stack([cv2.resize(f, (nw, nh), interpolation=cv2.INTER_AREA) for f in frames])


def cmd_check(a) -> int:
    rows = manifest.load(a.manifest)
    bad = manifest.check(rows)
    for vid, probs in bad.items():
        print(f"{vid}: " + "; ".join(probs))
    print(f"{len(rows)} rows, {len(bad)} with problems")
    return 1 if bad else 0


def cmd_search(a) -> int:
    token = None
    got = 0
    while got < a.max:
        rows, token = fetch.youtube_cc_search(a.query, min(50, a.max - got), page_token=token)
        for r in rows:
            print(json.dumps(r, ensure_ascii=False))
        got += len(rows)
        if not token or not rows:
            break
    return 0


def cmd_fetch(a) -> int:
    rows = manifest.load(a.manifest)
    failed = 0
    for v in rows:
        try:
            p = fetch.fetch(v, a.dest, allow_youtube=a.allow_youtube)
            print(f"{v.id}: {p.name} {v.sha256[:12]}")
        except (ValueError, PermissionError, OSError, RuntimeError) as e:
            failed += 1
            print(f"{v.id}: NOT fetched: {e}", file=sys.stderr)
    manifest.save(a.manifest, rows)                       # with the checksums
    return 1 if failed else 0


def cmd_build(a) -> int:
    rows = [v for v in manifest.load(a.manifest) if not manifest.problems(v)]
    marks = stages.load_marks(a.marks) if a.marks else {}
    ex = _extractor(a.backbone, a.device)
    rng = np.random.default_rng(a.seed)
    prepared, pair_sets, infos, shot_rows, stage_of = {}, {}, [], [], {}
    for v in rows:
        files = sorted(Path(a.videos).glob(f"{v.id}.*"))
        if not files:
            print(f"{v.id}: no video in {a.videos}", file=sys.stderr)
            continue
        raw, _ = read_video(str(files[0]), n=a.read)
        for k, sh in enumerate(split_shots(raw)):
            sid = f"{v.id}-s{k}"
            if not sh.keep:
                print(f"{sid}: left out ({sh.reason})")
                continue
            frames = raw[sh.start:sh.end]
            if len(frames) > a.frames:
                frames = frames[np.linspace(0, len(frames) - 1, a.frames).astype(int)]
            frames = _fit_width(frames, a.width, ex.patch)
            prep = dataset.prepare(sid, frames, ex)
            if prep is None:
                print(f"{sid}: left out (too few usable, aligned frames)")
                continue
            st = None
            if sid in marks:
                st = stages.per_frame(len(frames), marks[sid]["work_type"], marks[sid]["marks"])
                stage_of[sid] = st
            teacher = dataset.label(prep, stages=st)
            prepared[sid] = prep
            pair_sets[sid] = pairs.sample(sid, teacher, a.pairs, rng)
            infos.append(splits.ShotInfo(sid, v.id, v.channel, v.material,
                                         splits.signature(prep.feats)))
            shot_rows.append({"shot_id": sid, "video_id": v.id, "channel": v.channel,
                              "material": v.material, "work_type": v.work_type,
                              "licence": v.licence, "lo": round(teacher.lo, 4),
                              "hi": round(teacher.hi, 4)})
            print(f"{sid}: {len(prep.index)} frames, {len(pair_sets[sid])} pairs, "
                  f"lo {teacher.lo:.3f}")
    if not shot_rows:
        print("no shot survived", file=sys.stderr)
        return 1
    site_of = splits.sites(infos)
    split_of = splits.assign(infos, site_of, seed=a.seed)
    for r in shot_rows:
        r["site_id"] = site_of[r["shot_id"]]
        r["split"] = split_of[r["site_id"]]
    leaks = splits.leaks(infos, site_of, split_of)
    if leaks:
        print("leaks: " + "; ".join(leaks), file=sys.stderr)
        return 1
    out = dataset.write(a.out, shot_rows, prepared, pair_sets, stage_of)
    (Path(out) / "folds.json").write_text(json.dumps(
        {"leave_one_type_out": splits.leave_one_type_out(infos, site_of)}, indent=1))
    print(f"wrote {out}")
    return 0


def cmd_synth(a) -> int:
    r = synthset.make(a.out, seeds=tuple(range(a.seeds)), n_frames=a.frames)
    print(json.dumps({k: round(v, 4) for k, v in synthset.teacher_scores(r["built"]).items()}))
    return 0


def cmd_train(a) -> int:
    from drishti_vision.train import TrainConfig, fit
    h, w = (int(x) for x in a.size.split("x"))
    cfg = TrainConfig(data=a.data, out=a.out, backbone=a.backbone, size=(h, w), epochs=a.epochs,
                      order_epochs=a.order_epochs, batch=a.batch, lr=a.lr, device=a.device,
                      lora_blocks=a.lora_blocks, n_stages=stages.N_ALL if a.stages else 0,
                      workers=a.workers)
    _, info = fit(cfg)
    print(json.dumps(info))
    return 0


def cmd_measure(a) -> int:
    import torch

    from drishti_vision.model import build
    from drishti_vision.train import Store, TrainConfig, measure
    ck = torch.load(a.run, map_location=a.device, weights_only=False)
    c = ck["config"]
    cfg = TrainConfig(**{**c, "size": tuple(c["size"]), "device": a.device, "log": []})
    model = build(cfg.backbone, cfg.n_stages, cfg.head_dim, cfg.layers, cfg.lora_blocks)
    model.load_state_dict(ck["state"])
    model.to(a.device)
    print(json.dumps(measure(model, Store(a.data, split=a.split), cfg, use_truth=a.truth),
                     indent=1))
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="drishti_vision", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("check")
    s.add_argument("manifest")
    s = sub.add_parser("search")
    s.add_argument("query")
    s.add_argument("--max", type=int, default=25)
    s = sub.add_parser("fetch")
    s.add_argument("manifest")
    s.add_argument("--dest", required=True)
    s.add_argument("--allow-youtube", action="store_true",
                   help="only once the owner has decided YouTube downloads are allowed")
    s = sub.add_parser("build")
    s.add_argument("manifest")
    s.add_argument("--videos", required=True)
    s.add_argument("--out", required=True)
    s.add_argument("--marks", help="stage marks, marks.jsonl (stages.load_marks)")
    s.add_argument("--backbone", default="dinov2_vitb14_reg",
                   help="the teacher's features: a DINOv2 hub name, or handcrafted (CPU)")
    s.add_argument("--device", default="cpu")
    s.add_argument("--read", type=int, default=900, help="frames read from each video")
    s.add_argument("--frames", type=int, default=200, help="at most this many a shot")
    s.add_argument("--width", type=int, default=448)
    s.add_argument("--pairs", type=int, default=60, help="pairs a shot")
    s.add_argument("--seed", type=int, default=0)
    s = sub.add_parser("synth")
    s.add_argument("--out", required=True)
    s.add_argument("--seeds", type=int, default=4)
    s.add_argument("--frames", type=int, default=60)
    s = sub.add_parser("train")
    s.add_argument("--data", required=True)
    s.add_argument("--out", required=True)
    s.add_argument("--backbone", default="dinov2_vitb14_reg")
    s.add_argument("--size", default="224x308", help="HxW, multiples of the patch")
    s.add_argument("--epochs", type=int, default=10)
    s.add_argument("--order-epochs", type=int, default=2)
    s.add_argument("--batch", type=int, default=32)
    s.add_argument("--lr", type=float, default=3e-4)
    s.add_argument("--lora-blocks", type=int, default=0)
    s.add_argument("--stages", action="store_true", help="train the stage head (marked shots)")
    s.add_argument("--device", default="cuda")
    s.add_argument("--workers", type=int, default=2)
    s = sub.add_parser("measure")
    s.add_argument("--data", required=True)
    s.add_argument("--run", required=True)
    s.add_argument("--split", default="test")
    s.add_argument("--truth", action="store_true", help="synthetic data: use the true labels")
    s.add_argument("--device", default="cpu")
    a = p.parse_args(argv)
    return {"check": cmd_check, "search": cmd_search, "fetch": cmd_fetch, "build": cmd_build,
            "synth": cmd_synth, "train": cmd_train, "measure": cmd_measure}[a.cmd](a)
