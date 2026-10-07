"""Cut-outs of people, vehicles and animals for planted "staged site" pairs (plan T150 block D5).

A COCO Mask R-CNN (torchvision, BSD licence; weights from download.pytorch.org) finds each person,
bicycle, motorcycle, car, truck, bus, cow and dog in real site photos; each confident, whole
instance
becomes an RGBA cut-out. Cut-outs come from TRAINING-split photos only, so no test photo leaks into
training through a pasted person (vlmdata.split_of).

Cut-outs stay on D: (they contain real people); they never enter git.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

KEEP = {1: "person", 2: "bicycle", 3: "car", 4: "motorcycle", 6: "bus", 8: "truck", 18: "dog",
        21: "cow"}


def model(device: str = "cuda"):
    import torch
    from torchvision.models.detection import (
        MaskRCNN_ResNet50_FPN_V2_Weights,
        maskrcnn_resnet50_fpn_v2,
    )
    m = maskrcnn_resnet50_fpn_v2(weights=MaskRCNN_ResNet50_FPN_V2_Weights.COCO_V1)
    return m.eval().to(device if torch.cuda.is_available() else "cpu")


def cut(img_bgr: np.ndarray, net, score: float = 0.85, min_h: int = 60,
        max_side: int = 1024) -> list[np.ndarray]:
    """RGBA (BGR + alpha) cut-outs of the kept classes in one photo."""
    import torch
    h, w = img_bgr.shape[:2]
    s = min(1.0, max_side / max(h, w))
    if s < 1:
        img_bgr = cv2.resize(img_bgr, (round(w * s), round(h * s)), interpolation=cv2.INTER_AREA)
    dev = next(net.parameters()).device
    x = torch.from_numpy(img_bgr[..., ::-1].copy()).permute(2, 0, 1).float().div(255).to(dev)
    with torch.no_grad():
        o = net([x])[0]
    out = []
    for lab, sc, box, mk in zip(o["labels"].tolist(), o["scores"].tolist(),
                                o["boxes"].round().int().tolist(), o["masks"], strict=True):
        if lab not in KEEP or sc < score:
            continue
        x0, y0, x1, y1 = box
        x0, y0 = max(0, x0), max(0, y0)
        x1, y1 = min(img_bgr.shape[1], x1), min(img_bgr.shape[0], y1)
        if y1 - y0 < min_h or x1 - x0 < 8:
            continue
        # a cut-out touching the frame edge is a partial object: skip it
        if x0 <= 1 or y0 <= 1 or x1 >= img_bgr.shape[1] - 1 or y1 >= img_bgr.shape[0] - 1:
            continue
        m = (mk[0].cpu().numpy() > 0.5)[y0:y1, x0:x1]
        if m.mean() < 0.2:
            continue
        rgba = np.dstack([img_bgr[y0:y1, x0:x1], (m * 255).astype(np.uint8)])
        out.append(rgba)
    return out


def build_library(photos: list[Path], out_dir: Path, device: str = "cuda",
                  limit: int = 600) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)
    net = model(device)
    n = 0
    for p in photos:
        img = cv2.imread(str(p))
        if img is None:
            continue
        for i, c in enumerate(cut(img, net)):
            cv2.imwrite(str(out_dir / f"{p.parent.name}_{p.stem}_{i}.png"), c)
            n += 1
            if n >= limit:
                return n
    return n


def load_library(dir_: Path) -> list[np.ndarray]:
    out = []
    for p in sorted(Path(dir_).glob("*.png")):
        c = cv2.imread(str(p), cv2.IMREAD_UNCHANGED)
        if c is not None and c.ndim == 3 and c.shape[2] == 4:
            out.append(c)
    return out
