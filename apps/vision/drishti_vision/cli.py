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
import random
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
    raw_of = {}        # the kept frames as filmed (resized only): what the claim judge is shown
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
            if a.keep_raw:
                raw_of[sid] = frames[prep.index]
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
    out = dataset.write(a.out, shot_rows, prepared, pair_sets, stage_of, raw=raw_of)
    (Path(out) / "folds.json").write_text(json.dumps(
        {"leave_one_type_out": splits.leave_one_type_out(infos, site_of)}, indent=1))
    print(f"wrote {out}")
    return 0


def cmd_mgnrega(a) -> int:
    from drishti_vision import geomgnrega as mg
    names = a.places.split(",") if a.places else list(mg.PLACES)
    boxes = []
    for n in names:
        lat, lon = mg.PLACES[n]
        boxes += mg.boxes_around(n, lat, lon, half=a.half, grid=a.grid)
    cats = a.categories.split(",") if a.categories else list(mg.CATEGORIES)
    out = Path(a.out)
    stats = mg.harvest(boxes, cats, out / "photos", out / "assets.jsonl", per_box=a.per_box,
                       max_assets=a.max, log=lambda s: print(s, flush=True))
    print(json.dumps(stats))
    return 0


def cmd_ytcollect(a) -> int:
    """CC BY candidates from many queries -> manifest rows (licence read from each watch page)."""
    from drishti_vision import youtube as yt
    out = Path(a.out)
    have = {v.id for v in manifest.load(out)} if out.exists() else set()
    seen, new = set(have), 0
    with open(out, "a", encoding="utf-8") as f:        # one row written as soon as it is found
        for q in (a.queries.split("|") if a.queries else yt.QUERIES):
            try:
                cands = [c for c in yt.search(q, a.per_query) if yt.plausible(c)]
            except Exception as e:  # noqa: BLE001 (a failed search must not stop the others)
                print(f"{q!a}: search failed ({e})", flush=True)
                continue
            kept = 0
            for c in cands:
                vid = f"yt-{c['id']}"
                if vid in seen or len(have) + new >= a.max:
                    continue
                seen.add(vid)
                try:
                    m = yt.meta(c["id"])
                except Exception as e:  # noqa: BLE001
                    print(f"{vid}: no metadata ({e})", flush=True)
                    continue
                if m["license"] != yt.CC_BY or yt.NOT_REAL.search(m["title"]):
                    continue
                f.write(json.dumps(yt.manifest_row(c, m), ensure_ascii=False) + "\n")
                f.flush()
                kept += 1
                new += 1
            print(f"{q!a}: {len(cands)} plausible, {kept} CC BY kept", flush=True)
    print(f"{new} new rows -> {out}")
    return 0


def cmd_vlmbuild(a) -> int:
    """GeoMGNREGA assets -> certainty scores -> cut-outs (training districts only) -> claim-ladder
    items -> dataset card (vlmdata.py, change.py, cutouts.py)."""
    from drishti_vision import change, cutouts, vlmdata
    root, out = Path(a.root), Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    assets = [json.loads(line) for line in Path(a.assets).read_text(encoding="utf-8").splitlines()
              if line.strip()]
    cache_p = out / "change.jsonl"
    cache = {}
    if cache_p.exists():
        for line in cache_p.read_text(encoding="utf-8").splitlines():
            r = json.loads(line)
            cache[r["id"]] = r["change"]
    emb = None
    with open(cache_p, "a", encoding="utf-8") as f:
        for x in assets:
            if x["id"] not in cache:
                emb = emb or change.Embedder(a.device)
                try:
                    cache[x["id"]] = change.asset_change(x, root / a.photo_rel, emb)
                except FileNotFoundError:
                    continue
                f.write(json.dumps({"id": x["id"], "change": cache[x["id"]]}) + "\n")
            x["change"] = cache.get(x["id"])
    scored = out / "assets.jsonl"
    with open(scored, "w", encoding="utf-8") as f:
        for x in assets:
            if x.get("change"):
                f.write(json.dumps(x, ensure_ascii=False) + "\n")
    lib = out / "cutouts"
    if a.synthetic and not any(lib.glob("*.png")):
        photos = [root / a.photo_rel / p["file"] for x in assets
                  if vlmdata.split_of(x["district_code"]) == "train"
                  for p in x["photos"] if p.get("file") and p["stage"] == 2]
        print(f"cut-outs from {len(photos)} training 'during' photos", flush=True)
        cutouts.build_library(photos, lib, a.device, limit=a.cutouts)
    cut = cutouts.load_library(lib) if a.synthetic else []
    made_rel = str((out / "made").relative_to(root)).replace("\\", "/")
    items = vlmdata.build_mgnrega(scored, root, a.photo_rel, made_rel, cut, seed=a.seed,
                                  synthetic=a.synthetic)
    for tl in a.timelapse:              # T146 builds made with --keep-raw (real frames)
        frames_rel = str((out / "frames" / Path(tl).name).relative_to(root)).replace("\\", "/")
        got = vlmdata.timelapse_items(tl, root, frames_rel, random.Random(a.seed))
        print(f"{tl}: {len(got)} timelapse items", flush=True)
        items += got
    vlmdata.write_items(items, out / "items.jsonl")
    (out / "card.md").write_text(vlmdata.card(items), encoding="utf-8")
    print(vlmdata.card(items))
    return 0


def cmd_vlmtrain(a) -> int:
    from drishti_vision import vlm
    cfg = vlm.TrainConfig(base=a.base, items=a.items, root=a.root, out=a.out, quant4=a.quant4,
                          rank=a.rank, alpha=2 * a.rank, lr=a.lr, epochs=a.epochs,
                          accum=a.accum, max_items=a.max_items, seed=a.seed,
                          edited_share=a.edited_share, real_only=a.real_only,
                          eval_every=a.save_every)
    info = vlm.fit(cfg, log=lambda s: print(s, flush=True))
    print(json.dumps({k: info[k] for k in ("items", "steps", "minutes", "peak_gpu_gb",
                                           "trainable_m")}))
    return 0


def cmd_vlmeval(a) -> int:
    from drishti_vision import vlm, vlmeval
    from drishti_vision.vlmdata import read_items
    items = [i for i in read_items(a.items) if i.split == a.split]
    if a.real_only:
        items = [i for i in items if i.real]
    if a.limit:
        items = items[: a.limit]
    if a.provider == "claude":
        from drishti_vision.flagship_claude import ClaudeJudge
        L = ClaudeJudge(a.model or "claude-opus-5-5", a.effort)
    elif a.provider in ("gemini", "openai"):
        from drishti_vision import flagship_other as fo
        cls = fo.GeminiJudge if a.provider == "gemini" else fo.OpenAIJudge
        L = cls(a.model, a.price_in, a.price_out)
    else:
        L = vlm.load(a.base, quant4=a.quant4, adapter=a.adapter or None)
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    rows = vlmeval.predict(L, items, Path(a.root), out,
                           log=lambda s: print(s, flush=True))
    res = vlmeval.score(rows)
    res["model"] = L.name
    res["split"] = a.split
    Path(str(out).replace(".jsonl", "_score.json")).write_text(json.dumps(res, indent=1))
    print(json.dumps(res["headline_real_only"], indent=1))
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
    s.add_argument("--keep-raw", action="store_true",
                   help="also keep the frames as filmed (for the claim judge, T153)")
    s.add_argument("--seed", type=int, default=0)
    s = sub.add_parser("mgnrega", help="GeoMGNREGA before/during/after photos (geomgnrega.py)")
    s.add_argument("--out", required=True, help="folder on D: (photos/ and assets.jsonl)")
    s.add_argument("--places", default="", help="comma list of geomgnrega.PLACES names")
    s.add_argument("--categories", default="", help="comma list of MGNREGA category ids")
    s.add_argument("--max", type=int, default=50)
    s.add_argument("--per-box", type=int, default=8)
    s.add_argument("--half", type=float, default=0.04)
    s.add_argument("--grid", type=int, default=2)
    s = sub.add_parser("ytcollect", help="YouTube CC BY candidates as manifest rows (youtube.py)")
    s.add_argument("--out", required=True, help="manifest.jsonl to append to")
    s.add_argument("--queries", default="", help="'|'-separated; default youtube.QUERIES")
    s.add_argument("--per-query", type=int, default=40)
    s.add_argument("--max", type=int, default=250)
    s = sub.add_parser("vlmbuild", help="claim-ladder items for the VLM (vlmdata.py)")
    s.add_argument("--assets", required=True, help="GeoMGNREGA assets.jsonl")
    s.add_argument("--root", required=True, help="the data folder every image path is under")
    s.add_argument("--photo-rel", required=True, help="the photos folder, relative to --root")
    s.add_argument("--out", required=True)
    s.add_argument("--no-synthetic", dest="synthetic", action="store_false",
                   help="real, unedited photos only (no pasted people, light, dark, blocked)")
    s.add_argument("--cutouts", type=int, default=800)
    s.add_argument("--timelapse", action="append", default=[],
                   help="a `build --keep-raw` output folder; real timelapse pairs are added")
    s.add_argument("--device", default="cuda")
    s.add_argument("--seed", type=int, default=0)
    s = sub.add_parser("vlmtrain", help="LoRA fine-tuning of the claim judge (vlm.py)")
    s.add_argument("--base", default="Qwen/Qwen3-VL-4B-Instruct")
    s.add_argument("--items", required=True)
    s.add_argument("--root", required=True)
    s.add_argument("--out", required=True)
    s.add_argument("--quant4", action="store_true")
    s.add_argument("--rank", type=int, default=16)
    s.add_argument("--lr", type=float, default=1e-4)
    s.add_argument("--epochs", type=float, default=2.0)
    s.add_argument("--accum", type=int, default=8)
    s.add_argument("--max-items", type=int, default=0)
    s.add_argument("--edited-share", type=float, default=0.2)
    s.add_argument("--real-only", action="store_true", help="the ablation: no edited items")
    s.add_argument("--save-every", type=int, default=500)
    s.add_argument("--seed", type=int, default=0)
    s = sub.add_parser("vlmeval", help="SiteClaim-Bench scoring (vlmeval.py)")
    s.add_argument("--base", default="Qwen/Qwen3-VL-4B-Instruct")
    s.add_argument("--adapter", default="")
    s.add_argument("--quant4", action="store_true")
    s.add_argument("--items", required=True)
    s.add_argument("--root", required=True)
    s.add_argument("--split", default="test")
    s.add_argument("--real-only", action="store_true")
    s.add_argument("--limit", type=int, default=0)
    s.add_argument("--out", required=True, help="predictions .jsonl (resumable)")
    s.add_argument("--provider", default="local", choices=("local", "claude", "gemini", "openai"),
                   help="a flagship model through its API (keys from the environment)")
    s.add_argument("--model", default="", help="the provider's model name")
    s.add_argument("--effort", default="high", help="Claude's effort setting")
    s.add_argument("--price-in", type=float, default=None, help="USD per million input tokens")
    s.add_argument("--price-out", type=float, default=None, help="USD per million output tokens")
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
            "mgnrega": cmd_mgnrega, "ytcollect": cmd_ytcollect, "vlmbuild": cmd_vlmbuild,
            "vlmtrain": cmd_vlmtrain, "vlmeval": cmd_vlmeval, "synth": cmd_synth,
            "train": cmd_train,
            "measure": cmd_measure}[a.cmd](a)
