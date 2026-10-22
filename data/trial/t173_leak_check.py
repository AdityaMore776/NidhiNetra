r"""T173 part 1: has NidhiLens seen the test photos, or their answers, before? (plan docs/plans/T173-photo-only-progress.md)

Re-derives the 2,924 training items exactly as the training run did (vlm.training_items: split train,
real_only), then checks them against the release test 883, fresh 785 and probe 93:
  1. the same site, district, image file or (site, claim);
  2. the same picture under another name: exact bytes (md5), perceptual hash (pHash, Hamming <= 8),
     and CLIP image embeddings (cosine), with the closest pairs written out to look at by eye;
  3. the answers: a test reference reason copied word for word into a training target, and test photos
     that a model (Gemini, v7/gem_queue.jsonl) labelled.

  D:\nidhinetra-data\venv\Scripts\python.exe data\trial\t173_leak_check.py

Writes data/trial/results/t173_leak_check.txt and t173_closest_pairs.json (paths only, no photos).
"""

from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
DATA = Path(r"D:\nidhinetra-data")
REL = DATA / "release" / "siteclaim_test_v1"
TRAIN_FILE = DATA / "vlm" / "v6" / "items_eye.jsonl"
GEM_QUEUE = DATA / "vlm" / "v7" / "gem_queue.jsonl"
OUT = ROOT / "data" / "trial" / "results" / "t173_leak_check.txt"
PAIRS = ROOT / "data" / "trial" / "results" / "t173_closest_pairs.json"
PHASH_NEAR = 8          # Hamming distance out of 64: the usual "same picture" line
CLIP_NEAR = 0.95        # cosine; construction scenes all look alike to CLIP, so the bar is high

sys.path.insert(0, str(ROOT / "apps" / "vision"))
from drishti_vision.vlm import TrainConfig, training_items


def _read(path: Path) -> list[dict]:
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


def _key(rel: str) -> str:
    """One name for a photo whichever folder it sits in: the release copies live under images/."""
    rel = rel.replace("\\", "/")
    return rel.removeprefix("images/")


def _photos(items: list[dict], root: Path) -> dict[str, Path]:
    out = {}
    for r in items:
        for side in ("image_a", "image_b"):
            out[_key(r[side])] = root / r[side]
    return out


_DCT = None


def phash(path: Path) -> int:
    """64-bit perceptual hash: the sign of the low 8x8 DCT of a 32x32 grey copy against its median."""
    global _DCT
    if _DCT is None:
        n = 32
        k = np.arange(n)
        _DCT = np.cos(np.pi * (2 * k[None, :] + 1) * k[:, None] / (2 * n))
    g = np.asarray(Image.open(path).convert("L").resize((32, 32), Image.LANCZOS), dtype=np.float64)
    low = (_DCT @ g @ _DCT.T)[:8, :8].ravel()
    bits = low > np.median(low[1:])
    return int("".join("1" if b else "0" for b in bits), 2)


def md5(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def clip_embed(paths: list[Path]) -> np.ndarray:
    import torch
    from transformers import CLIPModel, CLIPProcessor
    name = "openai/clip-vit-base-patch32"
    model = CLIPModel.from_pretrained(name).eval()
    proc = CLIPProcessor.from_pretrained(name)
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    model.to(dev)
    out = []
    with torch.no_grad():
        for i in range(0, len(paths), 64):
            ims = [Image.open(p).convert("RGB") for p in paths[i:i + 64]]
            x = proc(images=ims, return_tensors="pt").to(dev)
            e = model.get_image_features(**x)
            if not isinstance(e, torch.Tensor):     # newer transformers return an output object
                e = e.pooler_output
            out.append(torch.nn.functional.normalize(e, dim=-1).cpu().numpy())
    return np.concatenate(out)


def main() -> None:
    lines: list[str] = []
    say = lines.append
    cfg = TrainConfig(base="Qwen/Qwen3-VL-4B-Instruct", items=str(TRAIN_FILE), root=str(DATA),
                      out="", real_only=True, seed=0)
    train = training_items(str(TRAIN_FILE), cfg)
    sets = {"test": _read(REL / "items_test.jsonl"), "fresh": _read(REL / "items_fresh.jsonl"),
            "probe": _read(REL / "items_probe.jsonl")}
    say(f"T173 leak check: training items re-derived = {len(train)} (training run says 2,924)")
    say("sets: " + ", ".join(f"{k} {len(v)}" for k, v in sets.items()))
    say("")

    # 1. the same site, district, file, (site, claim)
    tr_sites = {r["site"] for r in train}
    tr_dist = {r["district"] for r in train}
    tr_photos = _photos(train, DATA)
    tr_site_claim = {(r["site"], r["claim"].strip().lower()) for r in train}
    say("1. Shared names (training vs each set)")
    for name, items in sets.items():
        ph = _photos(items, REL)
        say(f"  {name}: sites in training {sum(r['site'] in tr_sites for r in items)}/{len(items)}"
            f" | districts in training {sorted({r['district'] for r in items} & tr_dist)}"
            f" | photo files in training {len(set(ph) & set(tr_photos))}/{len(ph)}"
            f" | (site, claim) in training "
            f"{sum((r['site'], r['claim'].strip().lower()) in tr_site_claim for r in items)}")
    test_sites = {k: {r["site"] for r in v} for k, v in sets.items()}
    say(f"  between sets: test & fresh sites {len(test_sites['test'] & test_sites['fresh'])},"
        f" test & probe {len(test_sites['test'] & test_sites['probe'])}")
    say("")

    # 3. the answers
    say("3. Answers")
    tr_reasons = Counter(r["target"]["reason"].strip().lower() for r in train)
    for name, items in sets.items():
        ref = [r.get("reference_answer") or {} for r in items]
        same = [x for x in ref if x.get("reason", "").strip().lower() in tr_reasons]
        say(f"  {name}: reference reasons also a training target word for word {len(same)}/{len(items)}"
            + (f" (e.g. {same[0]['reason'][:90]!r})" if same else ""))
        say(f"  {name}: labels checked by eye {sum(bool(r.get('label_checked_by_eye')) for r in items)}"
            f"/{len(items)}")
    if GEM_QUEUE.exists():
        gq = _read(GEM_QUEUE)
        gq_photos = {_key(r.get(s, "")) for r in gq for s in ("image_a", "image_b") if r.get(s)}
        for name, items in sets.items():
            say(f"  {name}: photos also in the Gemini label queue (v7) "
                f"{len(set(_photos(items, REL)) & gq_photos)}")
    say(f"  training labels by method: {dict(Counter(r.get('label_check') for r in train))}")
    say("")

    # 2. the same picture under another name
    say("2. The same picture under another name")
    all_test = {}
    for name, items in sets.items():
        for k, p in _photos(items, REL).items():
            all_test.setdefault(k, (name, p))
    tr_keys = sorted(tr_photos)
    te_keys = sorted(all_test)
    missing = [k for k in tr_keys if not tr_photos[k].exists()] + \
              [k for k in te_keys if not all_test[k][1].exists()]
    say(f"  photos: training {len(tr_keys)}, test+fresh+probe {len(te_keys)}, missing on disk {len(missing)}")
    tr_keys = [k for k in tr_keys if tr_photos[k].exists()]
    te_keys = [k for k in te_keys if all_test[k][1].exists()]

    tr_md5 = {md5(tr_photos[k]): k for k in tr_keys}
    same_bytes = [(k, tr_md5[h]) for k in te_keys if (h := md5(all_test[k][1])) in tr_md5]
    say(f"  exact same bytes: {len(same_bytes)}")

    tr_h = np.array([phash(tr_photos[k]) for k in tr_keys], dtype=np.uint64)
    te_h = np.array([phash(all_test[k][1]) for k in te_keys], dtype=np.uint64)
    near = []
    best_ph = []
    for i, h in enumerate(te_h):
        x = np.bitwise_xor(tr_h, h)
        d = np.array([bin(int(v)).count("1") for v in x])
        j = int(d.argmin())
        best_ph.append((int(d[j]), te_keys[i], tr_keys[j]))
        if d[j] <= PHASH_NEAR:
            near.append((int(d[j]), te_keys[i], tr_keys[j]))
    by_set = Counter(all_test[k][0] for _, k, _ in near)
    say(f"  pHash within {PHASH_NEAR}/64 of a training photo: {len(near)} ({dict(by_set)})")
    say(f"  pHash distance to the closest training photo: {_dist([b[0] for b in best_ph])}")

    tr_e = clip_embed([tr_photos[k] for k in tr_keys])
    te_e = clip_embed([all_test[k][1] for k in te_keys])
    sim = te_e @ tr_e.T
    j = sim.argmax(axis=1)
    best_cl = [(float(sim[i, j[i]]), te_keys[i], tr_keys[j[i]]) for i in range(len(te_keys))]
    cl_near = [b for b in best_cl if b[0] >= CLIP_NEAR]
    say(f"  CLIP cosine >= {CLIP_NEAR} to a training photo: {len(cl_near)}"
        f" ({dict(Counter(all_test[k][0] for _, k, _ in cl_near))})")
    say(f"  CLIP cosine to the closest training photo: {_dist([b[0] for b in best_cl], 3)}")
    tt = te_e @ te_e.T
    np.fill_diagonal(tt, -1)
    say(f"  for scale, CLIP closest other test photo (median): {np.median(tt.max(axis=1)):.3f}")

    pairs = {"phash_closest": [dict(d=d, test=t, set=all_test[t][0], train=r)
                               for d, t, r in sorted(best_ph)[:30]],
             "clip_closest": [dict(cos=round(c, 4), test=t, set=all_test[t][0], train=r)
                              for c, t, r in sorted(best_cl, reverse=True)[:30]]}
    PAIRS.write_text(json.dumps(pairs, indent=1), encoding="utf-8")
    say(f"  closest 30 pairs of each kind -> {PAIRS.name} (look at them by eye)")

    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


def _dist(xs: list[float], nd: int = 0) -> str:
    q = np.percentile(xs, [0, 1, 5, 50])
    f = (lambda v: f"{v:.{nd}f}") if nd else (lambda v: f"{int(v)}")
    return f"min {f(q[0])}, 1% {f(q[1])}, 5% {f(q[2])}, median {f(q[3])}"


if __name__ == "__main__":
    main()
