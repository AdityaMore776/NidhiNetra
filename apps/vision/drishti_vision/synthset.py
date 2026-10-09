"""A tuned dataset made of synthetic sites, with the truth attached (plan §9).

Each synthetic shot goes through the same pipeline as a real one (dataset.prepare: overlays,
alignment, masks, features; the hindsight teacher; pairs; splits by site). Every pair also carries
the TRUE map and label, moved into the aligned frames' position, so the teacher and the student
can both be measured against the truth.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import cv2
import numpy as np

from drishti_vision import dataset, pairs, splits
from drishti_vision.features import Extractor, Handcrafted
from drishti_vision.hindsight import PROGRESS, UNKNOWN, Hindsight
from drishti_vision.synth import KINDS, Site, SynthShot


@dataclass
class Built:
    shot: SynthShot
    prep: dataset.Prepared
    teacher: Hindsight
    pairs: list[pairs.Pair]
    ref_raw: int                       # the raw frame the shot was aligned onto
    built: np.ndarray = field(repr=False, default=None)      # (T, H, W) truth, aligned position
    temporary: np.ndarray = field(repr=False, default=None)


def _to_ref(maps: np.ndarray, shake: np.ndarray) -> np.ndarray:
    """Truth maps from the reference position into the camera position of the aligned shot."""
    h, w = maps.shape[1:]
    return np.stack([cv2.warpAffine(m, shake, (w, h), flags=cv2.INTER_NEAREST,
                                    borderMode=cv2.BORDER_REPLICATE) for m in maps])


def truth(b: Built, t1: int, t2: int, patch: int, min_share: float = 0.25,
          ) -> tuple[np.ndarray, np.ndarray]:
    """(true patch map, buried-only patches) for kept frames t1, t2 in the aligned position."""
    built, temp = b.built, b.temporary
    new = built[t2] != built[t1]
    buried = new & np.isin(built[t2], list(b.shot.buried_ids))
    visible = new & ~buried & ~temp[t2]
    h, w = new.shape
    gh, gw = h // patch, w // patch

    def share(m):
        return m[:gh * patch, :gw * patch].reshape(gh, patch, gw, patch).mean(axis=(1, 3))

    s, bur = share(visible), share(buried)
    out = np.where(s >= min_share, 1, np.where(s == 0, 0, -1)).astype(np.int8)
    if t2 < t1:                           # work disappearing is never progress
        out = np.where(out == -1, -1, 0).astype(np.int8)
    return out, (bur >= min_share) & (s < min_share)


def build_site(kind: str, seed: int, n_frames: int, size: tuple[int, int], n_pairs: int,
               extractor: Extractor, stage_marks: bool, rng: np.random.Generator,
               site: Site | None = None, variant: int = 0) -> Built | None:
    site = site or Site(kind, seed, n_frames=n_frames, size=size)
    sh = site.shot(variant)
    prep = dataset.prepare(sh.site_id, sh.frames, extractor)
    if prep is None:
        return None
    teacher = dataset.label(prep, stages=sh.stage if stage_marks else None)
    ref_raw = int(prep.index[len(prep.index) // 2])
    b = Built(sh, prep, teacher, [], ref_raw)
    b.built = _to_ref(sh.built[prep.index].astype(np.int16), sh.shake[ref_raw])
    b.temporary = _to_ref(sh.temporary[prep.index].astype(np.uint8), sh.shake[ref_raw]) > 0
    ps = pairs.sample(sh.site_id, teacher, n_pairs, rng)
    for p in ps:
        t, _ = truth(b, p.a, p.b, prep.patch)
        p.truth = t
        p.truth_label = int((t == 1).any()) if p.b > p.a else 0
    b.pairs = ps
    return b


def teacher_scores(items: list[Built], n: int = 80, seed: int = 0) -> dict:
    """The teacher against the truth on random forward pairs of each shot."""
    rng = np.random.default_rng(seed)
    tp = fp = fn = kept = right = total = 0
    buried_called = buried_total = 0
    for b in items:
        T = b.teacher.T
        for _ in range(n):
            t1, t2 = sorted(int(x) for x in rng.choice(T, 2, replace=False))
            lab = b.teacher.label(t1, t2)
            tr, bur = truth(b, t1, t2, b.prep.patch)
            k = (lab.patches != UNKNOWN) & (tr != -1) & ~bur
            pred, true = lab.patches == PROGRESS, tr == 1
            tp += int((pred & true & k).sum())
            fp += int((pred & ~true & k).sum())
            fn += int((~pred & true & k).sum())
            buried_total += int(bur.sum())
            buried_called += int((bur & (lab.patches == PROGRESS)).sum())
            total += 1
            if lab.label != -1:
                kept += 1
                right += int(lab.label == int(((tr == 1) & ~bur).any() or lab.by_stage))
    return {"patch_precision": tp / max(1, tp + fp), "patch_recall": tp / max(1, tp + fn),
            "patch_iou": tp / max(1, tp + fp + fn), "pairs_labelled": kept / max(1, total),
            "pair_accuracy": right / max(1, kept),
            "buried_patches_called_progress": buried_called / max(1, buried_total),
            "pairs": total}


def make(out: str, kinds=KINDS, seeds=(0, 1, 2, 3), n_frames: int = 60,
         size: tuple[int, int] = (192, 256), n_pairs: int = 40, extractor: Extractor | None = None,
         stage_marks: bool = True, reupload: bool = True, seed: int = 0) -> dict:
    """Builds the synthetic tuned dataset in `out`; returns what was built, for measuring."""
    extractor = extractor or Handcrafted(16)
    rng = np.random.default_rng(seed)
    built: list[Built] = []
    infos: list[splits.ShotInfo] = []
    rows: list[dict] = []
    for kind in kinds:
        for s in seeds:
            b = build_site(kind, 1000 * KINDS.index(kind) + s, n_frames, size, n_pairs, extractor,
                           stage_marks, rng)
            if b is None:
                continue
            built.append(b)
            # one channel per site, except two masonry sites that share an uploader
            shared = kind == "masonry" and s in seeds[:2]
            channel = "ch-shared" if shared else f"ch-{b.shot.site_id}"
            rows.append({"shot_id": b.shot.site_id, "video_id": f"v-{b.shot.site_id}",
                         "channel": channel, "material": kind, "work_type": b.shot.work_type,
                         "licence": "own", "lo": round(b.teacher.lo, 4),
                         "hi": round(b.teacher.hi, 4)})
            infos.append(splits.ShotInfo(b.shot.site_id, f"v-{b.shot.site_id}", channel, kind,
                                         splits.signature(b.prep.feats)))
    if reupload and built:
        # the same place uploaded again by someone else: it must join the original's site
        orig = built[0]
        again = Site(orig.shot.kind, orig.shot.seed, n_frames=n_frames, size=size,
                     site_id=f"{orig.shot.site_id}-reupload")
        b = build_site(orig.shot.kind, orig.shot.seed, n_frames, size, n_pairs, extractor,
                       stage_marks, rng, site=again, variant=1)
        if b is not None:
            built.append(b)
            rows.append({**rows[0], "shot_id": b.shot.site_id, "video_id": "v-reupload",
                         "channel": "ch-reuploader"})
            infos.append(splits.ShotInfo(b.shot.site_id, "v-reupload", "ch-reuploader",
                                         orig.shot.kind, splits.signature(b.prep.feats)))
    site_of = splits.sites(infos)
    split_of = splits.assign(infos, site_of, seed=seed)
    for r in rows:
        r["site_id"] = site_of[r["shot_id"]]
        r["split"] = split_of[r["site_id"]]
    by_id = {b.shot.site_id: b for b in built}
    dataset.write(out, rows, {k: v.prep for k, v in by_id.items()},
                  {k: v.pairs for k, v in by_id.items()},
                  stages={k: v.shot.stage for k, v in by_id.items()},
                  title="Synthetic construction progress pairs (T146 trial)")
    return {"built": built, "infos": infos, "site_of": site_of, "split_of": split_of,
            "rows": rows, "leaks": splits.leaks(infos, site_of, split_of)}
