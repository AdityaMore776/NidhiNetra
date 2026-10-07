"""From raw shot frames to the tuned dataset (plan §3).

    prepare()   quality filter -> overlays -> align -> even out light -> mask what moves ->
                temporal median -> patch features -> usable patches
    label()     the hindsight teacher on a prepared shot (plus stage marks, if any)
    write()     the dataset folder:

        card.md                 what is in it: counts by split, material and label; thresholds;
                                licences
        shots.jsonl             one line a shot: ids, split, material, frames, thresholds, pairs
        pairs.jsonl             one line a pair: shot, a, b, label, kind, split
        shots/<shot>.npz        frames (T, H, W, 3) uint8, valid (T, gh, gw), overlay (H, W),
                                activity (T, gh, gw) share of each patch masked as moving,
                                stage (T,)
        labels/<shot>.npz       a, b, label, kind (K,), patches (K, gh, gw) int8; on synthetic
                                shots also truth (K, gh, gw) and truth_label (K,)

Frames and labels stay out of git (the folder is in .gitignore); only the code and the card's
numbers are shared.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from drishti_vision.features import Extractor, patch_share
from drishti_vision.frames import daylight_normalise, motion_mask, quality, temporal_median
from drishti_vision.hindsight import Hindsight
from drishti_vision.masks import Masker
from drishti_vision.overlays import overlay_mask
from drishti_vision.pairs import PAIR_KINDS, Pair
from drishti_vision.register import align_shot

MASK_SHARE = 0.3            # a patch more than this share masked is not used
MIN_KEPT = 12               # a shot with fewer usable, aligned frames is dropped


@dataclass
class Prepared:
    shot_id: str
    frames: np.ndarray          # (T, H, W, 3) aligned, light evened
    index: np.ndarray           # (T,) frame index in the raw shot
    valid: np.ndarray           # (T, gh, gw) usable patches
    overlay: np.ndarray         # (H, W)
    activity: np.ndarray        # (T, gh, gw) share of each patch masked as moving (metadata only)
    feats: np.ndarray           # (T, gh, gw, D)
    patch: int
    report: dict = field(default_factory=dict)


def prepare(shot_id: str, raw: np.ndarray, extractor: Extractor, masker: Masker | None = None,
            median_radius: int = 1, mask_share: float = MASK_SHARE) -> Prepared | None:
    """None when too few frames survive (the report says why in the caller's log)."""
    keep = np.array([quality(f).usable for f in raw])
    raw_kept, index = raw[keep], np.nonzero(keep)[0]
    report = {"frames": len(raw), "usable": int(keep.sum())}
    if len(raw_kept) < MIN_KEPT:
        report["dropped"] = "too few usable frames"
        return None
    ov = overlay_mask(raw_kept)
    aligned, valid_px, align_rep = align_shot(raw_kept, mask=~ov)
    ok = np.array([a.ok for a in align_rep])
    report["aligned"] = int(ok.sum())
    if ok.sum() < MIN_KEPT:
        report["dropped"] = "too few frames align"
        return None
    aligned, valid_px, index = aligned[ok], valid_px[ok], index[ok]
    aligned = daylight_normalise(aligned)
    moving = masker.masks(aligned) if masker is not None else motion_mask(aligned, median_radius)
    clean = temporal_median(aligned, median_radius)
    feats = extractor.extract(clean)
    p = extractor.patch
    activity = patch_share(moving, p)
    blocked = patch_share(moving | ~valid_px | ov[None], p) > mask_share
    report["usable_patch_share"] = round(float((~blocked).mean()), 4)
    report["overlay_share"] = round(float(ov.mean()), 4)
    return Prepared(shot_id, aligned, index, ~blocked, ov, activity.astype(np.float16), feats, p,
                    report)


def label(prep: Prepared, stages: np.ndarray | None = None, **kw) -> Hindsight:
    if stages is not None:
        stages = stages[prep.index]
    return Hindsight(prep.feats, prep.valid, stages=stages, **kw)


def write(out: str | Path, shots: list[dict], prepared: dict[str, Prepared],
          pairs: dict[str, list[Pair]], stages: dict[str, np.ndarray] | None = None,
          title: str = "DRISHTI construction progress pairs",
          raw: dict[str, np.ndarray] | None = None) -> Path:
    """shots: one dict a shot with shot_id, video_id, site_id, split, material, work_type,
    licence, lo, hi (the teacher's thresholds)."""
    out = Path(out)
    (out / "shots").mkdir(parents=True, exist_ok=True)
    (out / "labels").mkdir(parents=True, exist_ok=True)
    stages = stages or {}
    with open(out / "shots.jsonl", "w", encoding="utf-8") as fs, \
            open(out / "pairs.jsonl", "w", encoding="utf-8") as fp:
        for s in shots:
            sid = s["shot_id"]
            prep, ps = prepared[sid], pairs.get(sid, [])
            st = stages.get(sid)
            extra_raw = {"raw": raw[sid]} if raw and sid in raw else {}
            np.savez_compressed(
                out / "shots" / f"{sid}.npz", frames=prep.frames, valid=prep.valid,
                overlay=prep.overlay, activity=prep.activity, index=prep.index,
                stage=(st[prep.index] if st is not None
                       else np.full(len(prep.index), -1, np.int16)), **extra_raw)
            if ps:
                extra = {}
                if all(p.truth is not None for p in ps):
                    extra = {"truth": np.stack([p.truth for p in ps]),
                             "truth_label": np.array([p.truth_label for p in ps], np.int8)}
                np.savez_compressed(
                    out / "labels" / f"{sid}.npz", a=np.array([p.a for p in ps]),
                    b=np.array([p.b for p in ps]), label=np.array([p.label for p in ps], np.int8),
                    kind=np.array([PAIR_KINDS.index(p.kind) for p in ps], np.int8),
                    patches=np.stack([p.patches for p in ps]), **extra)
            row = {**s, "frames": int(len(prep.index)), "patch": prep.patch,
                   "pairs": len(ps), "progress_pairs": sum(p.label == 1 for p in ps),
                   **{f"prep_{k}": v for k, v in prep.report.items()}}
            fs.write(json.dumps(row) + "\n")
            for p in ps:
                fp.write(json.dumps({"shot_id": sid, "a": p.a, "b": p.b, "label": p.label,
                                     "kind": p.kind, "split": s["split"]}) + "\n")
    (out / "card.md").write_text(card(title, shots, pairs), encoding="utf-8")
    return out


def card(title: str, shots: list[dict], pairs: dict[str, list[Pair]]) -> str:
    by = Counter()
    for s in shots:
        for p in pairs.get(s["shot_id"], []):
            by[(s["split"], s["material"], p.label, p.kind)] += 1
    splits = sorted({s["split"] for s in shots})
    mats = sorted({s["material"] for s in shots})
    lines = [f"# {title}", "", f"{len(shots)} shots, {len({s['site_id'] for s in shots})} sites.",
             "", "## Pairs by split and material (progress / none / swapped)", "",
             "| split | " + " | ".join(mats) + " |", "|---|" + "---|" * len(mats)]
    for sp in splits:
        cells = []
        for m in mats:
            pos = sum(v for (a, b, lab, k), v in by.items() if (a, b, lab) == (sp, m, 1))
            neg = sum(v for (a, b, lab, k), v in by.items()
                      if (a, b, lab) == (sp, m, 0) and k != "swapped")
            sw = sum(v for (a, b, lab, k), v in by.items() if (a, b, k) == (sp, m, "swapped"))
            cells.append(f"{pos} / {neg} / {sw}")
        lines.append(f"| {sp} | " + " | ".join(cells) + " |")
    lines += ["", "## Licences", ""]
    for lic, n in sorted(Counter(s.get("licence", "?") for s in shots).items()):
        lines.append(f"- {lic}: {n} shots")
    lines += ["", "## Teacher thresholds (per shot, from its own noise)", ""]
    los = [s["lo"] for s in shots if "lo" in s]
    if los:
        lines.append(f"- lo: {min(los):.3f} to {max(los):.3f}; hi is twice lo")
    return "\n".join(lines) + "\n"
