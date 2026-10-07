"""The manifest: one row a video, the only part of the data that enters git (plan §4.2).

Videos and frames never enter git (the repo is public; AGENTS.md rule 6). A row records where a
video came from, under what licence, who made it, and what it shows. A row whose licence is not on
the allow-list is refused: no-derivatives and non-commercial licences, and YouTube downloads, wait
for the owner's decision (plan §4.1).
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path

LICENCES = {
    "cc0": "CC0 (public domain dedication)",
    "pd": "Public domain",
    "cc-by": "Creative Commons Attribution",
    "cc-by-sa": "Creative Commons Attribution-ShareAlike",
    "own": "Filmed by the team, with the site's permission",
    "permission": "Used with the maker's written permission (see permission_ref)",
}
# refused until the owner decides: training may count as a derivative, and use as non-commercial
WAITING = {"cc-by-nd", "cc-by-nc", "cc-by-nc-sa", "cc-by-nc-nd", "youtube-standard"}
SOURCES = ("youtube", "wikimedia", "university", "webcam", "own", "dataset", "other")
WORK_TYPES = ("building", "road", "drain", "boundary_wall", "bridge", "other")
MATERIALS = ("masonry", "concrete_frame", "wood", "steel", "road", "mixed", "other")
CAMERAS = ("fixed", "handheld", "drone", "mixed")


@dataclass
class Video:
    id: str                         # short, unique: "yt-<video id>", "wm-<file>", "own-<site>-<n>"
    url: str
    source: str
    licence: str
    attribution: str                # the maker's name as the licence asks it to be credited
    channel: str                    # the uploader: one channel's videos stay in one split
    work_type: str
    material: str
    country: str
    camera: str
    site_id: str = ""               # filled by splits.py after duplicates are joined
    sha256: str = ""                # of the downloaded file
    permission_ref: str = ""        # where the written permission is kept (licence "permission")
    stage_marks: bool = False       # a person has marked where each stage begins
    notes: str = ""
    extra: dict = field(default_factory=dict)


def problems(v: Video) -> list[str]:
    out = []
    if not v.id or any(c in v.id for c in "/\\ "):
        out.append("id must be non-empty with no spaces or slashes")
    if v.licence in WAITING:
        out.append(f"licence {v.licence!r} waits for the owner's decision (plan §4.1)")
    elif v.licence not in LICENCES:
        out.append(f"unknown licence {v.licence!r}")
    if v.licence == "permission" and not v.permission_ref:
        out.append("licence 'permission' needs permission_ref")
    if v.licence.startswith("cc-by") and not v.attribution:
        out.append("a CC BY licence needs the attribution")
    for name, allowed in (("source", SOURCES), ("work_type", WORK_TYPES),
                          ("material", MATERIALS), ("camera", CAMERAS)):
        if getattr(v, name) not in allowed:
            out.append(f"{name} {getattr(v, name)!r} is not one of {allowed}")
    if not v.channel:
        out.append("channel is needed: one uploader's videos must stay in one split")
    return out


def load(path: str | Path) -> list[Video]:
    names = {f.name for f in fields(Video)}
    rows = []
    for n, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        raw = json.loads(line)
        unknown = set(raw) - names
        if unknown:
            raise ValueError(f"line {n}: unknown fields {sorted(unknown)}")
        rows.append(Video(**raw))
    ids = [v.id for v in rows]
    dup = {i for i in ids if ids.count(i) > 1}
    if dup:
        raise ValueError(f"duplicate ids: {sorted(dup)}")
    return rows


def save(path: str | Path, rows: list[Video]) -> None:
    Path(path).write_text("".join(json.dumps(asdict(v), ensure_ascii=False) + "\n" for v in rows),
                          encoding="utf-8")


def check(rows: list[Video]) -> dict[str, list[str]]:
    """{video id: its problems} for every row with a problem."""
    return {v.id: p for v in rows if (p := problems(v))}
