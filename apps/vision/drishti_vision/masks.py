"""People, vehicles and machines: masked, never repainted (plan §4.4).

Two maskers with one interface, `masks(frames) -> (N, H, W) bool`:

- `MotionMasker`: what moves between neighbouring frames (frames.motion_mask). No model.
- `DetectorMasker`: a pretrained instance-segmentation model's people, vehicles and machines, for
  what stands still (a worker posing, a parked truck). Torchvision's Mask R-CNN on COCO classes
  by default; a model trained on MOCS or SODA can be passed in the same way.

The masks are also kept as metadata: activity heatmaps check labels (plan §5.3), and are never
an input that says "progress".
"""

from __future__ import annotations

from typing import Protocol

import numpy as np

from drishti_vision.frames import motion_mask

# COCO category ids (torchvision numbering) of things that are never construction progress
COCO_TRANSIENT = {1: "person", 2: "bicycle", 3: "car", 4: "motorcycle", 6: "bus", 8: "truck"}
SCORE = 0.5


class Masker(Protocol):
    def masks(self, frames: np.ndarray) -> np.ndarray: ...


class MotionMasker:
    def __init__(self, radius: int = 1) -> None:
        self.radius = radius

    def masks(self, frames: np.ndarray) -> np.ndarray:
        return motion_mask(frames, self.radius)


def keep_transient(labels: np.ndarray, scores: np.ndarray, classes=COCO_TRANSIENT,
                   score: float = SCORE) -> np.ndarray:
    """Which detections to mask: a listed class, confident enough."""
    return np.isin(labels, list(classes)) & (scores >= score)


class DetectorMasker:
    """Torchvision Mask R-CNN (weights download once from the model hub; a GPU helps)."""

    def __init__(self, device: str = "cpu", model=None, classes=COCO_TRANSIENT,
                 score: float = SCORE, batch: int = 4) -> None:
        import torch  # the training environment only

        self.torch, self.device = torch, device
        if model is None:
            from torchvision.models.detection import (
                MaskRCNN_ResNet50_FPN_V2_Weights,
                maskrcnn_resnet50_fpn_v2,
            )
            model = maskrcnn_resnet50_fpn_v2(weights=MaskRCNN_ResNet50_FPN_V2_Weights.DEFAULT)
        self.model = model.eval().to(device)
        self.classes, self.score, self.batch = classes, score, batch

    def masks(self, frames: np.ndarray) -> np.ndarray:
        torch = self.torch
        out = np.zeros(frames.shape[:3], bool)
        with torch.no_grad():
            for i in range(0, len(frames), self.batch):
                x = [torch.from_numpy(f).permute(2, 0, 1).float().div(255).to(self.device)
                     for f in frames[i:i + self.batch]]
                for j, det in enumerate(self.model(x)):
                    keep = keep_transient(det["labels"].cpu().numpy(), det["scores"].cpu().numpy(),
                                          self.classes, self.score)
                    if keep.any():
                        m = det["masks"][keep, 0].cpu().numpy() > 0.5
                        out[i + j] = m.any(axis=0)
        return out


class Combined:
    def __init__(self, *maskers: Masker) -> None:
        self.maskers = maskers

    def masks(self, frames: np.ndarray) -> np.ndarray:
        out = np.zeros(frames.shape[:3], bool)
        for m in self.maskers:
            out |= m.masks(frames)
        return out
