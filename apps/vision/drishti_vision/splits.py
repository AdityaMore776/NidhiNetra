"""Splits by site, never by frame (plan §6).

1. Shots that show the same place, from different videos (a re-upload, a second camera on one
   project), are joined into one site: their pictures are matched by feature similarity.
2. A site, and every site of one uploader's channel, sit in one split only: a channel's camera,
   watermark and style would otherwise leak.
3. Folds about 70 / 15 / 15 of sites (train / calibration / test), balanced by material.
4. Leave-one-type-out: train on every material but one, test on that one.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass

import numpy as np

SAME_PLACE = 0.9            # two shots' signatures this similar (cosine): one place
SPLITS = ("train", "calib", "test")
SHARES = (0.7, 0.15, 0.15)


@dataclass
class ShotInfo:
    shot_id: str
    video_id: str
    channel: str
    material: str
    signature: np.ndarray   # (D,) unit vector: the shot's look (mean patch feature of its frames)


def signature(feats: np.ndarray) -> np.ndarray:
    """A shot's look from its patch features (T, gh, gw, D): the spatial layout of the mean
    feature, flattened. Two shots of one place from the same angle match; layouts do not."""
    s = feats.mean(axis=0).ravel()
    return s / max(float(np.linalg.norm(s)), 1e-9)


class _Union:
    def __init__(self, items):
        self.p = {i: i for i in items}

    def find(self, x):
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def join(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[max(ra, rb)] = min(ra, rb)


def sites(shots: list[ShotInfo], same_place: float = SAME_PLACE) -> dict[str, str]:
    """{shot id: site id}. Shots of one video are one site; shots of different videos whose
    signatures match are joined. Signatures of different sizes are never compared."""
    u = _Union([s.shot_id for s in shots])
    by_video = defaultdict(list)
    for s in shots:
        by_video[s.video_id].append(s.shot_id)
    for ids in by_video.values():
        for other in ids[1:]:
            u.join(ids[0], other)
    for i, a in enumerate(shots):
        for b in shots[i + 1:]:
            if a.video_id != b.video_id and a.signature.shape == b.signature.shape \
                    and float(a.signature @ b.signature) >= same_place:
                u.join(a.shot_id, b.shot_id)
    return {s.shot_id: f"site-{u.find(s.shot_id)}" for s in shots}


def _groups(shots: list[ShotInfo], site_of: dict[str, str]) -> list[set[str]]:
    """Sites joined through shared channels: each group must stay in one split."""
    u = _Union(sorted(set(site_of.values())))
    first_site = {}
    for s in shots:
        site = site_of[s.shot_id]
        if s.channel in first_site:
            u.join(first_site[s.channel], site)
        else:
            first_site[s.channel] = site
    groups = defaultdict(set)
    for site in set(site_of.values()):
        groups[u.find(site)].add(site)
    return sorted(groups.values(), key=lambda g: (-len(g), sorted(g)[0]))


def assign(shots: list[ShotInfo], site_of: dict[str, str], seed: int = 0,
           shares=SHARES) -> dict[str, str]:
    """{site id: split}. Groups (sites sharing a channel) are placed largest first, each in the
    split furthest below its share for the group's main material."""
    rng = np.random.default_rng(seed)
    mat_of_site = {}
    for s in shots:
        mat_of_site.setdefault(site_of[s.shot_id], s.material)
    groups = _groups(shots, site_of)
    # shuffle groups of equal size so the seed matters
    order = sorted(range(len(groups)), key=lambda i: (-len(groups[i]), rng.random()))
    total = Counter(mat_of_site.values())
    have = {sp: Counter() for sp in SPLITS}
    out = {}
    for i in order:
        g = groups[i]
        mats = Counter(mat_of_site[s] for s in g)
        main = mats.most_common(1)[0][0]
        need = [shares[k] * total[main] - have[sp][main] for k, sp in enumerate(SPLITS)]
        sp = SPLITS[int(np.argmax(need))]
        for s in g:
            out[s] = sp
        have[sp].update(mats)
    return out


def leave_one_type_out(shots: list[ShotInfo], site_of: dict[str, str]) -> dict[str, dict]:
    """{material: {"train": sites, "test": sites}}. A channel with any site of the held-out
    material is left out of training entirely (its style would leak)."""
    out = {}
    mats = sorted({s.material for s in shots})
    for m in mats:
        held_channels = {s.channel for s in shots if s.material == m}
        test = {site_of[s.shot_id] for s in shots if s.material == m}
        train = {site_of[s.shot_id] for s in shots
                 if s.material != m and s.channel not in held_channels}
        out[m] = {"train": sorted(train - test), "test": sorted(test)}
    return out


def leaks(shots: list[ShotInfo], site_of: dict[str, str], split_of: dict[str, str]) -> list[str]:
    """Every way a split leaks: a site or a channel in two splits. Empty means clean."""
    out = []
    by_channel = defaultdict(set)
    by_site = defaultdict(set)
    for s in shots:
        site = site_of[s.shot_id]
        by_channel[s.channel].add(split_of[site])
        by_site[site].add(split_of[site])
    out += [f"site {k} in {sorted(v)}" for k, v in by_site.items() if len(v) > 1]
    out += [f"channel {k} in {sorted(v)}" for k, v in by_channel.items() if len(v) > 1]
    return out
