r"""Trial 6 - Photo Forensics on the real eSAKSHI evidence (pilot sample).

Two questions:
  A. Real reuse - which photos turn up on more than one work? Exact copies (same bytes), and
     near copies found by a 256-bit perceptual fingerprint or by feature matching (ORB).
     The closest pairs are written out and READ BY EYE; LABELS below records the verdicts.
  B. Robustness - does each method still recognise a photo after re-saving, resizing,
     cropping, brightening, a slight turn, a stamped band, a screenshot frame? Each method runs
     at the loosest setting that confuses no two DIFFERENT photos in the pilot (pairs the eye
     confirmed as the same photo are left out of that calculation - they are the findings).
     256-bit pHash (DRISHTI) + ORB against the 64-bit dHash a rival project uses.

Certificates are not fingerprinted: portal-generated forms look identical to any image hash
(59,054 false "matches" in a first run). Documents are compared by their text instead.

Run:  .venv-trial\Scripts\python.exe data\trial\photo_trial.py
"""

from __future__ import annotations

import io
import json
from collections import defaultdict
from itertools import combinations
from pathlib import Path

import cv2
import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageEnhance, ImageOps
from scipy.fftpack import dct

ROOT = Path(__file__).resolve().parents[2]
EVID = ROOT / "data" / "evidence"
OUT = ROOT / "data" / "trial" / "results"
CACHE = ROOT / "data" / "trial" / "cache"
PHOTO_EXT = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp", ".bmp"}
POP = np.array([bin(i).count("1") for i in range(256)], dtype=np.uint8)

# Closest cross-work pairs, read by eye (file a, file b) -> verdict.
#   "same_photo"  one photo on two works (possibly re-saved/cropped)
#   "same_scene"  the same place shot twice (e.g. two works on one street) - not reuse
#   "different"   look-alikes (two different lanes, two different lights)
# Read 2026-09-26: the 25 closest pairs are all DIFFERENT pictures that share a layout -
# photographed forms of one template (tanker checklists, delivery challans, Hindi completion
# certificates), handwritten photo sheets, numbered handpump prints, two smart-class projectors.
LABELS: dict[tuple[str, str], str] = {
    ("1654108.1713687.jpeg", "1595529.1651796.jpeg"): "different",
    ("598736.615272.png", "598630.615165.png"): "different",
    ("483978.494310.jpg", "484154.494575.jpg"): "different",
    ("2185526.2277320.jpg", "2185384.2277174.jpg"): "different",
    ("1927765.2002855.jpeg", "1927648.2002727.jpeg"): "different",
    ("2185001.2276770.jpg", "2186036.2277870.jpg"): "different",
    ("1654108.1713686.jpeg", "484154.494575.jpg"): "different",
    ("2185526.2277320.jpg", "2185595.2277391.jpg"): "different",
    ("2186017.2277851.jpg", "2185685.2277485.jpg"): "different",
    ("2185595.2277391.jpg", "2185384.2277174.jpg"): "different",
    ("2185994.2277825.jpg", "2185789.2277604.jpg"): "different",
    ("483978.494310.jpg", "1595529.1651795.jpeg"): "different",
    ("1595529.1651795.jpeg", "484154.494575.jpg"): "different",
    ("483978.494309.jpg", "484154.494574.jpg"): "different",
    ("1529322.1581613.jpg", "1595529.1651795.jpeg"): "different",
    ("1654108.1713688.jpeg", "1595529.1651797.jpeg"): "different",
    ("1529322.1581615.jpg", "1595529.1651797.jpeg"): "different",
    ("1529322.1581614.jpg", "1654108.1713687.jpeg"): "different",
    ("1529322.1581614.jpg", "1595529.1651796.jpeg"): "different",
    ("1654108.1713686.jpeg", "1595529.1651795.jpeg"): "different",
    ("1529322.1581615.jpg", "1654108.1713688.jpeg"): "different",
    ("2004591.2084138.jpeg", "2006112.2085721.jpeg"): "different",
    ("2004591.2084138.jpeg", "2006735.2086381.jpeg"): "different",
    ("2003411.2082898.jpeg", "2006769.2086418.jpeg"): "different",
    ("2000839.2080201.jpeg", "2006321.2085947.jpeg"): "different",
}


# ---------------------------------------------------------------- fingerprints
def phash256(img: Image.Image) -> np.ndarray:
    a = np.asarray(img.convert("L").resize((32, 32), Image.LANCZOS), dtype=np.float64)
    d = dct(dct(a, axis=1, norm="ortho"), axis=0, norm="ortho")[:16, :16].reshape(256)
    return np.packbits(d > np.median(d[1:]))


def dhash64(img: Image.Image) -> np.ndarray:
    a = np.asarray(img.convert("L").resize((9, 8), Image.LANCZOS), dtype=np.float64)
    return np.packbits((a[:, 1:] > a[:, :-1]).reshape(64))


def dist(a: np.ndarray, b: np.ndarray) -> int:
    return int(POP[np.bitwise_xor(a, b)].sum())


def pairwise(h: np.ndarray) -> np.ndarray:
    return POP[np.bitwise_xor(h[:, None, :], h[None, :, :])].sum(axis=2)


_orb = cv2.ORB_create(nfeatures=1000)
_bf = cv2.BFMatcher(cv2.NORM_HAMMING)


def orb_features(img: Image.Image):
    g = np.asarray(img.convert("L"))
    s = 800 / max(g.shape)
    if s < 1:
        g = cv2.resize(g, (int(g.shape[1] * s), int(g.shape[0] * s)), interpolation=cv2.INTER_AREA)
    return _orb.detectAndCompute(g, None)


def orb_inliers(fa, fb) -> int:
    """Geometrically consistent matches between two photos (0 = unrelated)."""
    (ka, da), (kb, db) = fa, fb
    if da is None or db is None or len(ka) < 8 or len(kb) < 8:
        return 0
    good = [m for m, n in (p for p in _bf.knnMatch(da, db, k=2) if len(p) == 2) if m.distance < 0.75 * n.distance]
    if len(good) < 8:
        return len(good)
    src = np.float32([ka[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
    dst = np.float32([kb[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)
    _, mask = cv2.findHomography(src, dst, cv2.RANSAC, 5.0)
    return int(mask.sum()) if mask is not None else 0


# ---------------------------------------------------------------- evidence
def load_photos() -> tuple[list[dict], dict]:
    photos, exact = [], defaultdict(set)
    for line in (EVID / "manifest.jsonl").read_text(encoding="utf-8").splitlines():
        rec = json.loads(line)
        for f in rec["files"]:
            exact[f["sha256"]].add(rec["work_id"])
            p = ROOT / f["path"].replace("\\", "/")
            if p.suffix.lower() not in PHOTO_EXT:
                continue
            try:
                img = ImageOps.exif_transpose(Image.open(p)).convert("RGB")
                if max(img.size) > 1600:
                    img.thumbnail((1600, 1600))
                photos.append({"work_id": rec["work_id"], "sample": rec["sample"], "file": p.name,
                               "sha256": f["sha256"], "img": img})
            except Exception:  # corrupt image: skipped (counted in the result)
                photos.append({"work_id": rec["work_id"], "sample": rec["sample"], "file": p.name,
                               "sha256": f["sha256"], "img": None})
    return photos, exact


def edits(img: Image.Image) -> dict[str, Image.Image]:
    w, h = img.size
    out = {
        "resaved_q40": Image.open(io.BytesIO(_jpeg(img, 40))),
        "half_size": img.resize((w // 2, h // 2)),
        "crop_8pct": img.crop((int(w * .04), int(h * .04), int(w * .96), int(h * .96))),
        "brighter_25pct": ImageEnhance.Brightness(img).enhance(1.25),
        "turned_2deg": img.rotate(2, resample=Image.BICUBIC, expand=False, fillcolor=(0, 0, 0)),
    }
    stamped = img.copy()
    ImageDraw.Draw(stamped).rectangle((0, int(h * .82), w, h), fill=(20, 20, 20))
    out["stamp_band_18pct"] = stamped
    shot = Image.new("RGB", (int(w * 1.1), int(h * 1.25)), (250, 250, 250))
    shot.paste(img, (int(w * .05), int(h * .12)))
    out["screenshot_frame"] = shot
    return out


def _jpeg(img: Image.Image, q: int) -> bytes:
    b = io.BytesIO()
    img.save(b, "JPEG", quality=q)
    return b.getvalue()


def main() -> None:
    photos, exact = load_photos()
    ok = list({p["sha256"]: p for p in photos if p["img"] is not None}.values())   # one per distinct file
    n = len(ok)
    P = np.stack([phash256(p["img"]) for p in ok])
    D = np.stack([dhash64(p["img"]) for p in ok])
    F = [orb_features(p["img"]) for p in ok]
    Mp, Md = pairwise(P), pairwise(D)

    orb_path = CACHE / "orb_inliers.npz"
    files = [p["file"] for p in ok]
    if orb_path.exists() and list(np.load(orb_path, allow_pickle=True)["files"]) == files:
        Mo = np.load(orb_path, allow_pickle=True)["m"]
    else:
        Mo = np.zeros((n, n), dtype=np.int32)
        for i, j in combinations(range(n), 2):
            if ok[i]["work_id"] != ok[j]["work_id"]:
                Mo[i, j] = Mo[j, i] = orb_inliers(F[i], F[j])
        CACHE.mkdir(parents=True, exist_ok=True)
        np.savez(orb_path, m=Mo, files=np.array(files, dtype=object))

    pairs = [(i, j) for i, j in combinations(range(n), 2) if ok[i]["work_id"] != ok[j]["work_id"]]
    rows = [{"a": files[i], "b": files[j], "work_a": ok[i]["work_id"], "work_b": ok[j]["work_id"],
             "phash_bits": int(Mp[i, j]), "dhash_bits": int(Md[i, j]), "orb_inliers": int(Mo[i, j])}
            for i, j in pairs]
    pr = pd.DataFrame(rows)
    pr["label"] = [LABELS.get((a, b), LABELS.get((b, a))) for a, b in zip(pr.a, pr.b)]
    closest = pd.concat([pr.nsmallest(15, "phash_bits"), pr.nlargest(15, "orb_inliers")]).drop_duplicates(["a", "b"])

    # thresholds: loosest setting that confuses no two photos the eye called different
    neg = pr[pr.label.isin(["different", "same_scene"]) | pr.label.isna()]
    neg = neg[neg.label != "same_photo"]
    tp, td, to = int(neg.phash_bits.min()) - 1, int(neg.dhash_bits.min()) - 1, int(neg.orb_inliers.max()) + 1

    ed = []
    for k, p in enumerate(ok):
        for name, e in edits(p["img"]).items():
            o = orb_inliers(F[k], orb_features(e))
            ph, dh = dist(P[k], phash256(e)) <= tp, dist(D[k], dhash64(e)) <= td
            ed.append({"edit": name, "dhash64": dh, "phash256": ph, "orb": o >= to, "drishti_phash_or_orb": ph or o >= to})
    r = pd.DataFrame(ed)
    cols = ["dhash64", "phash256", "orb", "drishti_phash_or_orb"]
    res = {
        "photos": len(photos), "unreadable": sum(1 for p in photos if p["img"] is None), "distinct_photos": n,
        "by_sample": pd.Series([p["sample"] for p in ok]).value_counts().to_dict(),
        "pairs_from_different_works": len(pr),
        "thresholds": {"phash256_max_bits": tp, "dhash64_max_bits": td, "orb_min_inliers": to},
        "robustness_caught_overall": r[cols].mean().round(3).to_dict(),
        "robustness_by_edit": r.groupby("edit")[cols].mean().round(3).reset_index().to_dict("records"),
        "exact_copies_across_works": [sorted(ws) for ws in exact.values() if len(ws) > 1],
        "near_copies_found": pr[(pr.phash_bits <= tp) | (pr.orb_inliers >= to)].to_dict("records"),
        "closest_pairs_for_reading": closest.to_dict("records"),
        "labels_so_far": pr.label.value_counts().to_dict(),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "photo_trial.json").write_text(json.dumps(res, indent=2, default=str), encoding="utf-8")
    print(json.dumps({k: v for k, v in res.items() if k not in ("closest_pairs_for_reading",)}, indent=1, default=str))
    print("closest pairs to read:")
    for c in closest.itertuples():
        print(f"  {c.a} | {c.b} | pHash {c.phash_bits} dHash {c.dhash_bits} ORB {c.orb_inliers} | {c.label}")


if __name__ == "__main__":
    main()
