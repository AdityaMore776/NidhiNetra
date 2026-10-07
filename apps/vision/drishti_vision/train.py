"""Training and measuring the student (plan §7, §8). PyTorch.

Steps (plan §7):
  order      the build-up score learns to order 4 frames of a shot (no labels: time is the label)
  pairs      progress map + progress yes / no from the teacher's pairs, with augmentation;
             the build-up score keeps its order on the same pairs; stages where marked

Every epoch is measured on the calibration split; the best checkpoint is kept. `measure()` gives
every number of plan §8.1 for one split, including the shortcut audits:
  short     neighbouring frames the teacher calls "none": light and time of day are not progress
  staged    "none" pairs with people, machines, scaffolds and stacks pasted into B
  both_ways progress pairs also called progress when swapped (it saw "different", not "added")
"""

from __future__ import annotations

import json
import math
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

import cv2
import numpy as np
import torch
import torch.nn.functional as F
from torch.utils.data import DataLoader, Dataset

from drishti_vision import augment as aug
from drishti_vision import evaluate as ev
from drishti_vision.model import ProgressModel, build, trainable
from drishti_vision.pairs import PAIR_KINDS
from drishti_vision.stages import global_index

FORWARD, SHORT, SWAPPED = (PAIR_KINDS.index(k) for k in ("forward", "short", "swapped"))
MAX_POS_WEIGHT = 10.0


@dataclass
class TrainConfig:
    data: str
    out: str
    backbone: str = "tiny"
    size: tuple[int, int] = (192, 256)      # model input (H, W), multiples of the patch
    epochs: int = 8
    order_epochs: int = 2
    batch: int = 16
    lr: float = 3e-4
    weight_decay: float = 0.05
    map_weight: float = 1.0
    pair_weight: float = 1.0
    order_weight: float = 0.3
    stage_weight: float = 0.5
    n_stages: int = 0
    lora_blocks: int = 0
    head_dim: int = 256
    layers: int = 2
    train_sites: list[str] | None = None    # None: the "train" split
    eval_sites: list[str] | None = None     # None: the "calib" split
    augment: bool = True
    seed: int = 0
    device: str = "cpu"
    workers: int = 0
    log: list[dict] = field(default_factory=list)


# -- data ------------------------------------------------------------------------------------------

class Store:
    """The tuned dataset on disk (dataset.write), filtered to some sites or a split."""

    def __init__(self, root: str | Path, split: str | None = None,
                 sites: list[str] | None = None) -> None:
        self.root = Path(root)
        rows = [json.loads(x) for x in (self.root / "shots.jsonl").read_text().splitlines() if x]
        if sites is not None:
            keep = set(sites)
            rows = [r for r in rows if r["site_id"] in keep]
        elif split is not None:
            rows = [r for r in rows if r["split"] == split]
        self.shots = {r["shot_id"]: r for r in rows}
        self._frames: dict[str, dict] = {}
        self._labels: dict[str, dict] = {}
        self.items: list[tuple[str, int]] = []
        for sid in sorted(self.shots):
            lab = self.labels(sid)
            if lab is not None:
                self.items += [(sid, k) for k in range(len(lab["label"]))]

    def frames(self, sid: str) -> dict:
        if sid not in self._frames:
            with np.load(self.root / "shots" / f"{sid}.npz") as z:
                self._frames[sid] = {k: z[k] for k in z.files}
        return self._frames[sid]

    def labels(self, sid: str) -> dict | None:
        if sid not in self._labels:
            p = self.root / "labels" / f"{sid}.npz"
            if not p.exists():
                return None
            with np.load(p) as z:
                self._labels[sid] = {k: z[k] for k in z.files}
        return self._labels[sid]

    def patch(self, sid: str) -> int:
        return int(self.shots[sid]["patch"])


def resample(labels: np.ndarray, src_hw: tuple[int, int], src_patch: int,
             dst_grid: tuple[int, int]) -> np.ndarray:
    """Patch labels on the teacher's grid -> the student's grid over the same picture (nearest
    patch centre; -1 outside the teacher's grid)."""
    gh, gw = labels.shape
    H, W = src_hw
    oh, ow = dst_grid
    ys = ((np.arange(oh) + 0.5) / oh * H / src_patch).astype(int)
    xs = ((np.arange(ow) + 0.5) / ow * W / src_patch).astype(int)
    out = np.full((oh, ow), -1, np.int8)
    iy, ix = ys < gh, xs < gw
    out[np.ix_(iy, ix)] = labels[np.ix_(ys[iy], xs[ix])]
    return out


def _tensor(img: np.ndarray, size: tuple[int, int]) -> torch.Tensor:
    h, w = size
    if img.shape[:2] != (h, w):
        img = cv2.resize(img, (w, h), interpolation=cv2.INTER_AREA)
    return torch.from_numpy(np.ascontiguousarray(img)).permute(2, 0, 1).float().div(255)


class PairData(Dataset):
    def __init__(self, store: Store, size: tuple[int, int], patch: int, augment: bool, seed: int,
                 cfg: aug.Config | None = None, staged: bool | None = None,
                 swap: bool = False, use_truth: bool = False) -> None:
        self.store, self.size, self.patch = store, size, patch
        self.augment, self.seed, self.cfg = augment, seed, cfg or aug.Config()
        self.staged, self.swap, self.use_truth = staged, swap, use_truth
        self.epoch = 0

    def __len__(self) -> int:
        return len(self.store.items)

    def __getitem__(self, i: int) -> dict:
        sid, k = self.store.items[i]
        fr, lab = self.store.frames(sid), self.store.labels(sid)
        a_i, b_i = int(lab["a"][k]), int(lab["b"][k])
        label = int(lab["label"][k])
        kind = int(lab["kind"][k])
        patches = lab["patches"][k]
        if self.use_truth and "truth" in lab:
            patches, label = lab["truth"][k], int(lab["truth_label"][k])
        a, b = fr["frames"][a_i], fr["frames"][b_i]
        if self.swap:
            a, b = b, a
        tp = self.store.patch(sid)
        rng = np.random.default_rng((self.seed, self.epoch, i))
        if self.augment:
            a, b, patches = aug.augment_pair(a, b, patches, tp, rng, self.cfg, staged=self.staged)
        elif self.staged:
            b, patches, _ = aug.paste_transients(b, patches, tp, rng)
        grid = (self.size[0] // self.patch, self.size[1] // self.patch)
        target = resample(patches, fr["frames"].shape[1:3], tp, grid)
        order = 1 if (label == 1 and kind != SWAPPED) else (-1 if kind == SWAPPED else 0)
        st = fr["stage"]
        wt = self.store.shots[sid].get("work_type", "building")
        return {"a": _tensor(a, self.size), "b": _tensor(b, self.size),
                "map": torch.from_numpy(target.astype(np.int64)), "label": label, "kind": kind,
                "order": order, "stage_a": global_index(wt, int(st[a_i])),
                "stage_b": global_index(wt, int(st[b_i])),
                "shot": sid}


class OrderData(Dataset):
    """Four frames of a shot, in time order, each lightly augmented on its own (plan §7 step 1)."""

    def __init__(self, store: Store, size: tuple[int, int], seed: int, n: int = 4,
                 per_shot: int = 32) -> None:
        self.store, self.size, self.seed, self.n = store, size, seed, n
        self.shots = sorted(store.shots)
        self.per_shot = per_shot
        self.epoch = 0

    def __len__(self) -> int:
        return len(self.shots) * self.per_shot

    def __getitem__(self, i: int) -> dict:
        sid = self.shots[i % len(self.shots)]
        fr = self.store.frames(sid)["frames"]
        rng = np.random.default_rng((self.seed, self.epoch, i, 7))
        idx = np.sort(rng.choice(len(fr), self.n, replace=False))
        imgs = [aug.photometric(fr[j], rng) for j in idx]
        return {"x": torch.stack([_tensor(im, self.size) for im in imgs]),
                "t": torch.from_numpy(idx.astype(np.float32) / max(1, len(fr) - 1))}


# -- losses ----------------------------------------------------------------------------------------

def pair_losses(out: dict, batch: dict, cfg: TrainConfig) -> dict[str, torch.Tensor]:
    m = batch["map"]
    known = m >= 0
    zero = out["pair"].sum() * 0
    l_map = zero
    if known.any():
        y = m[known].float()
        # progress patches are rare (a few in a hundred): weigh them up to MAX_POS_WEIGHT times,
        # or the map learns that "nothing" is always nearly right
        pos = y.sum().clamp_min(1.0)
        w = ((y.numel() - pos) / pos).clamp(1.0, MAX_POS_WEIGHT)
        l_map = F.binary_cross_entropy_with_logits(out["map"][known], y, pos_weight=w)
    l_pair = F.binary_cross_entropy_with_logits(out["pair"], batch["label"].float())
    order = batch["order"].float()
    use = order != 0
    l_order = (F.softplus(-order[use] * (out["score_b"] - out["score_a"])[use]).mean()
               if use.any() else zero)
    l_stage = zero
    if "stage_a" in out:
        for side in ("a", "b"):
            y = batch[f"stage_{side}"]
            ok = y >= 0
            if ok.any():
                l_stage = l_stage + F.cross_entropy(out[f"stage_{side}"][ok], y[ok])
    total = (cfg.map_weight * l_map + cfg.pair_weight * l_pair + cfg.order_weight * l_order
             + cfg.stage_weight * l_stage)
    return {"total": total, "map": l_map, "pair": l_pair, "order": l_order, "stage": l_stage}


def order_loss(scores: torch.Tensor, t: torch.Tensor) -> torch.Tensor:
    """Every later frame must score above every earlier one, weighted by how far apart they are."""
    d = scores[:, None, :] - scores[:, :, None]          # (B, i, j): s_j - s_i
    gap = t[:, None, :] - t[:, :, None]
    later = gap > 0
    return (F.softplus(-d[later]) * gap[later]).sum() / gap[later].sum().clamp_min(1e-6)


# -- the loop --------------------------------------------------------------------------------------

def _loader(ds, cfg: TrainConfig, shuffle: bool) -> DataLoader:
    g = torch.Generator().manual_seed(cfg.seed)
    return DataLoader(ds, batch_size=cfg.batch, shuffle=shuffle, num_workers=cfg.workers,
                      generator=g, drop_last=False)


def _to(batch: dict, device: str) -> dict:
    return {k: (v.to(device) if torch.is_tensor(v) else v) for k, v in batch.items()}


def fit(cfg: TrainConfig) -> tuple[ProgressModel, dict]:
    torch.manual_seed(cfg.seed)
    out_dir = Path(cfg.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    model = build(cfg.backbone, cfg.n_stages, cfg.head_dim, cfg.layers, cfg.lora_blocks)
    model.to(cfg.device)
    train_store = Store(cfg.data, split=None if cfg.train_sites else "train",
                        sites=cfg.train_sites)
    eval_store = Store(cfg.data, split=None if cfg.eval_sites else "calib", sites=cfg.eval_sites)
    params = [p for p in model.parameters() if p.requires_grad]
    opt = torch.optim.AdamW(params, lr=cfg.lr, weight_decay=cfg.weight_decay)
    info = {"trainable": trainable(model), "train_pairs": len(train_store.items),
            "eval_pairs": len(eval_store.items), "train_shots": len(train_store.shots)}

    # step 1: ordering, no labels
    od = OrderData(train_store, cfg.size, cfg.seed)
    for e in range(cfg.order_epochs):
        od.epoch = e
        model.train()
        losses = []
        for batch in _loader(od, cfg, True):
            x, t = batch["x"].to(cfg.device), batch["t"].to(cfg.device)
            b, n = x.shape[:2]
            s = model.build_up(x.flatten(0, 1)).view(b, n)
            loss = order_loss(s, t)
            opt.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(params, 1.0)
            opt.step()
            losses.append(loss.item())
        cfg.log.append({"step": "order", "epoch": e, "loss": float(np.mean(losses))})

    # step 2: pairs
    ds = PairData(train_store, cfg.size, model.patch, cfg.augment, cfg.seed)
    steps = max(1, cfg.epochs * math.ceil(len(ds) / cfg.batch))
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=cfg.lr, total_steps=steps,
                                                pct_start=0.1)
    best, best_state = -1.0, None
    for e in range(cfg.epochs):
        ds.epoch = e
        model.train()
        t0, parts = time.time(), []
        for batch in _loader(ds, cfg, True):
            batch = _to(batch, cfg.device)
            out = model(batch["a"], batch["b"])
            ls = pair_losses(out, batch, cfg)
            opt.zero_grad()
            ls["total"].backward()
            torch.nn.utils.clip_grad_norm_(params, 1.0)
            opt.step()
            sched.step()
            parts.append({k: v.item() for k, v in ls.items()})
        m = measure(model, eval_store, cfg, audits=False)
        row = {"step": "pairs", "epoch": e, "seconds": round(time.time() - t0, 1),
               **{f"loss_{k}": round(float(np.mean([p[k] for p in parts])), 4) for k in parts[0]},
               **{f"calib_{k}": v for k, v in m.items()}}
        cfg.log.append(row)
        score = m.get("auroc", float("nan"))
        if not math.isnan(score) and score > best:
            best = score
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
    if best_state is not None:
        model.load_state_dict(best_state)
    info["best_calib_auroc"] = best
    torch.save({"state": model.state_dict(), "config": asdict(cfg)}, out_dir / "best.pt")
    (out_dir / "train_log.json").write_text(json.dumps({"info": info, "log": cfg.log}, indent=1))
    return model, info


@torch.no_grad()
def _predict(model: ProgressModel, ds: Dataset, cfg: TrainConfig) -> dict[str, np.ndarray]:
    model.eval()
    probs, labels, kinds, maps, targets = [], [], [], [], []
    for batch in _loader(ds, cfg, False):
        b = _to(batch, cfg.device)
        out = model(b["a"], b["b"])
        probs.append(torch.sigmoid(out["pair"]).cpu().numpy())
        maps.append(torch.sigmoid(out["map"]).cpu().numpy())
        labels.append(batch["label"].numpy())
        kinds.append(batch["kind"].numpy())
        targets.append(batch["map"].numpy())
    cat = np.concatenate
    return {"prob": cat(probs), "label": cat(labels), "kind": cat(kinds), "map": cat(maps),
            "target": cat(targets)}


@torch.no_grad()
def _build_up_tau(model: ProgressModel, store: Store, cfg: TrainConfig, n: int = 12) -> float:
    model.eval()
    taus = []
    for sid in sorted(store.shots):
        fr = store.frames(sid)["frames"]
        idx = np.linspace(0, len(fr) - 1, min(n, len(fr))).astype(int)
        x = torch.stack([_tensor(fr[i], cfg.size) for i in idx]).to(cfg.device)
        s = model.build_up(x).cpu().numpy()
        taus.append(ev.kendall_tau(s, idx))
    return float(np.nanmean(taus)) if taus else float("nan")


def measure(model: ProgressModel, store: Store, cfg: TrainConfig, audits: bool = True,
            use_truth: bool = False) -> dict[str, float]:
    """Plan §8.1 on one store. With `use_truth` (synthetic data) the labels are the true ones."""
    if not store.items:
        return {}
    p = _predict(model, PairData(store, cfg.size, model.patch, False, cfg.seed,
                                 use_truth=use_truth), cfg)
    keep = p["kind"] != SWAPPED
    y, pr = p["label"][keep], p["prob"][keep]
    acc, cover = ev.selective(pr, y)
    ps = ev.patch_scores(p["map"] > 0.5, p["target"])
    out = {"auroc": round(ev.auroc(pr, y), 4), "accuracy_answered": round(acc, 4),
           "answered": round(cover, 4), "ece": round(ev.ece(pr, y), 4),
           "patch_precision": round(ps["precision"], 4), "patch_recall": round(ps["recall"], 4),
           "patch_iou": round(ps["iou"], 4), "pairs": int(keep.sum())}
    if not audits:
        return out
    short_none = (p["kind"] == SHORT) & (p["label"] == 0)
    out["false_progress_short"] = round(ev.false_progress(p["prob"][short_none]), 4)
    none_fwd = (p["kind"] != SWAPPED) & (p["label"] == 0)
    staged = _predict(model, PairData(store, cfg.size, model.patch, False, cfg.seed + 1,
                                      staged=True, use_truth=use_truth), cfg)
    out["false_progress_staged"] = round(ev.false_progress(staged["prob"][none_fwd]), 4)
    prog = (p["kind"] != SWAPPED) & (p["label"] == 1)
    swapped = _predict(model, PairData(store, cfg.size, model.patch, False, cfg.seed, swap=True,
                                       use_truth=use_truth), cfg)
    out["both_ways"] = round(ev.both_ways(p["prob"][prog], swapped["prob"][prog]), 4)
    out["build_up_tau"] = round(_build_up_tau(model, store, cfg), 4)
    return out
