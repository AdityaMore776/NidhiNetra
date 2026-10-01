"""Every work's attached files and photo stamps, to find reuse across works (T310).

Built from the evidence facts of the works given (the batch: all of them). Exact copies by
SHA-256, same picture by fingerprint (fingerprint.py), same spot same day by the stamp.
A linear scan over fingerprints is fine for the pilot (319 photos); at national scale it needs
a multi-index hash table.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from drishti.agents.photo_evidence.fingerprint import same_picture

PHOTO_EXT = {"jpg", "jpeg", "png", "tif", "tiff", "webp", "bmp", "heic"}


@dataclass
class PhotoIndex:
    by_sha: dict[str, set[str]] = field(default_factory=lambda: defaultdict(set))
    hashes: list[tuple[str, str]] = field(default_factory=list)          # (phash, work_id)
    spots: dict[tuple, set[str]] = field(default_factory=lambda: defaultdict(set))

    @classmethod
    def build(cls, works) -> PhotoIndex:
        idx = cls()
        for w in works:
            wid = w.get("work_id")
            for f in ((w.get("evidence") or {}).get("files")) or []:
                if f.get("sha256"):
                    idx.by_sha[f["sha256"]].add(wid)
                if f.get("ext") in PHOTO_EXT and f.get("phash"):
                    idx.hashes.append((f["phash"], wid))
                for s in f.get("stamps") or []:
                    if s.get("lat") is not None and s.get("date"):
                        idx.spots[(round(s["lat"], 4), round(s["lon"], 4), str(s["date"])[:10])
                                  ].add(wid)
        return idx

    def same_file(self, sha: str | None) -> set[str]:
        return set(self.by_sha.get(sha or "", ()))

    def same_picture(self, phash: str) -> set[str]:
        return {w for h, w in self.hashes if same_picture(h, phash)}

    def same_spot(self, lat: float, lon: float, when) -> set[str]:
        if when is None:
            return set()
        return set(self.spots.get((round(lat, 4), round(lon, 4), str(when)[:10]), ()))
