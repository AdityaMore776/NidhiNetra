"""The student: two frames in, progress out (plan §7). PyTorch.

    backbone (frozen DINOv2, or a tiny CNN for CPU tests)
        -> patch features of A and of B
    head: both frames' patches, with positions and a "which frame" mark, through a few joint
          self-attention layers (so each patch of B can find its match in A when the phone moved)
        -> progress map (a logit a patch of B), progress yes / no (a logit), build-up score of each
           frame (from that frame alone), stage of each frame

The build-up score is computed from one frame on its own, so ordering frames (plan §7, step 1)
needs no pairs and no labels.
"""

from __future__ import annotations

import math

import numpy as np
import torch
import torch.nn.functional as F
from torch import nn

MEAN = (0.485, 0.456, 0.406)
STD = (0.229, 0.224, 0.225)


def normalise(x: torch.Tensor) -> torch.Tensor:
    """(B, 3, H, W) in [0, 1] -> ImageNet-normalised."""
    m = torch.tensor(MEAN, device=x.device).view(1, 3, 1, 1)
    s = torch.tensor(STD, device=x.device).view(1, 3, 1, 1)
    return (x - m) / s


class TinyBackbone(nn.Module):
    """A small CNN with stride 16, trained from scratch: for CPU tests and the synthetic trial."""

    patch = 16

    def __init__(self, dim: int = 96) -> None:
        super().__init__()
        chans = [3, 24, 48, 72, dim]
        layers = []
        for cin, cout in zip(chans[:-1], chans[1:], strict=True):
            layers += [nn.Conv2d(cin, cout, 3, stride=2, padding=1), nn.BatchNorm2d(cout),
                       nn.GELU(), nn.Conv2d(cout, cout, 3, padding=1), nn.BatchNorm2d(cout),
                       nn.GELU()]
        self.net = nn.Sequential(*layers)
        self.dim = dim
        self.frozen = False

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(normalise(x)).permute(0, 2, 3, 1)       # (B, gh, gw, D)


class HandcraftedBackbone(nn.Module):
    """features.Handcrafted as a frozen backbone (no download, CPU): the plan's design (a frozen
    feature extractor and a trained head) on a machine with no GPU and no model hub."""

    patch = 16

    def __init__(self) -> None:
        super().__init__()
        from drishti_vision.features import Handcrafted
        self.ex = Handcrafted(self.patch, center=False)
        self.dim = self.ex.dim
        self.frozen = True

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        imgs = (x.clamp(0, 1) * 255).byte().permute(0, 2, 3, 1).cpu().numpy()
        f = torch.from_numpy(self.ex.extract(imgs)).float().to(x.device)
        # every patch's raw vector points almost the same way (histograms are all positive): the
        # differences that matter are ~1% of its length. Centre and scale each image's patches so
        # the head sees them.
        f = f - f.mean(dim=(1, 2), keepdim=True)
        return f / f.std(dim=(1, 2, 3), keepdim=True).clamp_min(1e-6)


class LoRALinear(nn.Module):
    """A frozen linear layer plus a trainable low-rank update (LoRA)."""

    def __init__(self, base: nn.Linear, r: int = 8, alpha: float = 16.0) -> None:
        super().__init__()
        self.base = base
        for p in self.base.parameters():
            p.requires_grad_(False)
        self.a = nn.Parameter(torch.zeros(r, base.in_features))
        self.b = nn.Parameter(torch.zeros(base.out_features, r))
        nn.init.kaiming_uniform_(self.a, a=math.sqrt(5))
        self.scale = alpha / r

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.base(x) + (x @ self.a.t() @ self.b.t()) * self.scale


class Dinov2Backbone(nn.Module):
    """DINOv2 (Apache-2.0), frozen, from torch.hub. `lora_blocks` > 0 adds LoRA to the attention of
    the last blocks: the only backbone weights that train."""

    def __init__(self, name: str = "dinov2_vitb14_reg", lora_blocks: int = 0, r: int = 8) -> None:
        super().__init__()
        self.model = torch.hub.load("facebookresearch/dinov2", name)
        for p in self.model.parameters():
            p.requires_grad_(False)
        self.patch = self.model.patch_size
        self.dim = self.model.embed_dim
        self.frozen = lora_blocks == 0
        for blk in list(self.model.blocks)[-lora_blocks:] if lora_blocks else []:
            blk.attn.qkv = LoRALinear(blk.attn.qkv, r=r)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        b, _, h, w = x.shape
        out = self.model.forward_features(normalise(x))["x_norm_patchtokens"]
        return out.reshape(b, h // self.patch, w // self.patch, self.dim)


def sincos_2d(gh: int, gw: int, d: int, device) -> torch.Tensor:
    """(gh * gw, d) fixed 2-D sine-cosine positions."""
    q = d // 4
    freq = 1.0 / (10000 ** (torch.arange(q, device=device) / q))
    ys, xs = torch.meshgrid(torch.arange(gh, device=device), torch.arange(gw, device=device),
                            indexing="ij")
    ys, xs = ys.reshape(-1, 1).float() * freq, xs.reshape(-1, 1).float() * freq
    return torch.cat([ys.sin(), ys.cos(), xs.sin(), xs.cos()], dim=1)


class ProgressHead(nn.Module):
    def __init__(self, d_in: int, d: int = 256, layers: int = 2, heads: int = 8,
                 n_stages: int = 0, dropout: float = 0.1) -> None:
        super().__init__()
        self.d = d
        self.proj = nn.Sequential(nn.LayerNorm(d_in), nn.Linear(d_in, d))
        # B's patches also get their difference from A's patch at the same place: after alignment
        # the strongest cue; attention handles what alignment leaves
        self.diff = nn.Sequential(nn.LayerNorm(d), nn.Linear(d, d))
        self.frame = nn.Parameter(torch.zeros(2, d))
        self.cls = nn.Parameter(torch.zeros(1, 1, d))
        nn.init.normal_(self.frame, std=0.02)
        nn.init.normal_(self.cls, std=0.02)
        layer = nn.TransformerEncoderLayer(d, heads, 4 * d, dropout, batch_first=True,
                                           norm_first=True, activation="gelu")
        # layers=0: no attention between frames, a probe on the frozen features (plan §7, size a)
        self.joint = (nn.TransformerEncoder(layer, layers, enable_nested_tensor=False) if layers
                      else nn.Identity())
        self.norm = nn.LayerNorm(d)
        self.map = nn.Linear(d, 1)
        self.pair = nn.Linear(d, 1)
        self.score = nn.Sequential(nn.LayerNorm(d), nn.Linear(d, d), nn.GELU(), nn.Linear(d, 1))
        self.stage = nn.Linear(d, n_stages) if n_stages else None

    def frame_summary(self, f: torch.Tensor) -> torch.Tensor:
        """(B, gh, gw, D) -> (B, d): one frame on its own (for the build-up score and stage)."""
        return self.proj(f).mean(dim=(1, 2))

    def build_up(self, f: torch.Tensor) -> torch.Tensor:
        return self.score(self.frame_summary(f)).squeeze(-1)

    def forward(self, fa: torch.Tensor, fb: torch.Tensor) -> dict[str, torch.Tensor]:
        b, gh, gw, _ = fb.shape
        pos = sincos_2d(gh, gw, self.d, fb.device)
        pa = self.proj(fa).reshape(b, gh * gw, self.d)
        pb = self.proj(fb).reshape(b, gh * gw, self.d)
        ta = pa + pos + self.frame[0]
        tb = pb + self.diff(pb - pa) + pos + self.frame[1]
        x = torch.cat([self.cls.expand(b, -1, -1), ta, tb], dim=1)
        x = self.norm(self.joint(x))
        logits = self.map(x[:, 1 + gh * gw:]).squeeze(-1)
        # the pair's answer leans on its map (a soft maximum over patches): "progress, because
        # these patches show it", plus what the whole-pair token adds
        pooled = torch.logsumexp(logits, dim=1) - math.log(logits.shape[1])
        out = {"map": logits.reshape(b, gh, gw), "pair": self.pair(x[:, 0]).squeeze(-1) + pooled}
        sa, sb = self.frame_summary(fa), self.frame_summary(fb)
        out["score_a"], out["score_b"] = self.score(sa).squeeze(-1), self.score(sb).squeeze(-1)
        if self.stage is not None:
            out["stage_a"], out["stage_b"] = self.stage(sa), self.stage(sb)
        return out


class ProgressModel(nn.Module):
    def __init__(self, backbone: nn.Module, head: ProgressHead) -> None:
        super().__init__()
        self.backbone, self.head = backbone, head

    @property
    def patch(self) -> int:
        return self.backbone.patch

    def encode(self, x: torch.Tensor) -> torch.Tensor:
        if getattr(self.backbone, "frozen", False):
            with torch.no_grad():
                return self.backbone(x)
        return self.backbone(x)

    def forward(self, a: torch.Tensor, b: torch.Tensor) -> dict[str, torch.Tensor]:
        return self.head(self.encode(a), self.encode(b))

    def build_up(self, x: torch.Tensor) -> torch.Tensor:
        return self.head.build_up(self.encode(x))


def trainable(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


def build(backbone: str = "tiny", n_stages: int = 0, head_dim: int = 256, layers: int = 2,
          lora_blocks: int = 0) -> ProgressModel:
    """backbone: "tiny" (a CNN trained from scratch), "handcrafted" (frozen, CPU), or a DINOv2 hub
    name such as "dinov2_vits14_reg", "dinov2_vitb14_reg"."""
    if backbone == "handcrafted":
        bb = HandcraftedBackbone()
        return ProgressModel(bb, ProgressHead(bb.dim, d=min(head_dim, 128), layers=layers,
                                              heads=4, n_stages=n_stages))
    if backbone == "tiny":
        bb = TinyBackbone()
        return ProgressModel(bb, ProgressHead(bb.dim, d=min(head_dim, 128), layers=layers,
                                              heads=4, n_stages=n_stages))
    bb = Dinov2Backbone(backbone, lora_blocks=lora_blocks)
    return ProgressModel(bb, ProgressHead(bb.dim, d=head_dim, layers=layers, n_stages=n_stages))


class Dinov2Extractor:
    """DINOv2 patch features with the numpy interface of features.Extractor, for the hindsight
    teacher on real frames. Frames must be a multiple of the patch size (14) on each side."""

    def __init__(self, name: str = "dinov2_vitb14_reg", device: str = "cpu",
                 batch: int = 16) -> None:
        self.bb = Dinov2Backbone(name).to(device).eval()
        self.patch, self.device, self.batch = self.bb.patch, device, batch

    @torch.no_grad()
    def extract(self, frames: np.ndarray) -> np.ndarray:
        out = []
        for i in range(0, len(frames), self.batch):
            x = torch.from_numpy(np.ascontiguousarray(frames[i:i + self.batch]))
            x = x.permute(0, 3, 1, 2).float().div(255).to(self.device)
            f = F.normalize(self.bb(x), dim=-1)
            out.append(f.cpu().numpy())
        return np.concatenate(out)
