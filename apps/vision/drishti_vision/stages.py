"""The stage lists: the words a labeller marks and the words of an agency's claims (plan §5.2).

A labeller marks only the frame where each stage BEGINS in a shot; every frame inherits the latest
stage begun. Stages only go up, so a later stage at t2 than at t1 makes (t1, t2) a progress pair,
whatever the pictures say (this is how buried work, a footing under backfill, keeps its label).
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

STAGES: dict[str, tuple[str, ...]] = {
    "building": ("cleared", "excavated", "footing", "plinth", "columns", "walls", "roof",
                 "plaster", "finishing"),
    "road": ("cleared", "earthwork", "sub_base", "base", "surface", "shoulders"),
    "drain": ("cleared", "excavated", "bed", "walls", "cover_slabs"),
    "boundary_wall": ("cleared", "foundation", "wall", "coping_plaster"),
}

# one line a stage, worded as an agency's claim would be (the text labels)
DESCRIBE: dict[tuple[str, str], str] = {
    ("building", "cleared"): "Site cleared and levelled; nothing built yet",
    ("building", "excavated"): "Foundation trenches dug",
    ("building", "footing"): "Footings cast in the trenches",
    ("building", "plinth"): "Plinth built: the raised base the walls stand on",
    ("building", "columns"): "Columns or frame standing",
    ("building", "walls"): "Walls rising between the columns, up to lintel level",
    ("building", "roof"): "Roof slab cast",
    ("building", "plaster"): "Walls plastered",
    ("building", "finishing"): "Doors, windows, paint and flooring done",
    ("road", "cleared"): "Alignment cleared",
    ("road", "earthwork"): "Earthwork: the road bed formed",
    ("road", "sub_base"): "Sub-base laid (granular layer)",
    ("road", "base"): "Base course laid (WBM or similar)",
    ("road", "surface"): "Surface laid (cement concrete or bitumen)",
    ("road", "shoulders"): "Shoulders and edges finished",
    ("drain", "cleared"): "Alignment cleared",
    ("drain", "excavated"): "Drain trench dug",
    ("drain", "bed"): "Bed concrete laid",
    ("drain", "walls"): "Side walls built",
    ("drain", "cover_slabs"): "Cover slabs placed",
    ("boundary_wall", "cleared"): "Line cleared",
    ("boundary_wall", "foundation"): "Foundation laid",
    ("boundary_wall", "wall"): "Wall built",
    ("boundary_wall", "coping_plaster"): "Coping and plaster done",
}


# one numbering over every work type's stages, for a single stage head in the model
OFFSETS: dict[str, int] = {}
_n = 0
for _wt, _st in STAGES.items():
    OFFSETS[_wt] = _n
    _n += len(_st)
N_ALL = _n


def global_index(work_type: str, k: int) -> int:
    """A work type's own stage index -> the shared numbering (-1 stays -1)."""
    return -1 if k < 0 else OFFSETS[work_type] + int(k)


def stage_index(work_type: str, stage: str) -> int:
    try:
        return STAGES[work_type].index(stage)
    except (KeyError, ValueError) as e:
        raise ValueError(f"unknown stage {stage!r} for work type {work_type!r}") from e


def describe(work_type: str, stage: str) -> str:
    return DESCRIBE[(work_type, stage)]


def check_marks(work_type: str, marks: list[tuple[int, str]]) -> list[str]:
    """Problems with one shot's marks: unknown stages, frames out of order, a stage going down."""
    problems = []
    last_frame, last_stage = -1, -1
    for frame, stage in marks:
        try:
            k = stage_index(work_type, stage)
        except ValueError as e:
            problems.append(str(e))
            continue
        if frame <= last_frame:
            problems.append(f"frame {frame} is not after frame {last_frame}")
        if k <= last_stage:
            problems.append(f"stage {stage!r} at frame {frame} does not come after the one before")
        last_frame, last_stage = frame, max(last_stage, k)
    return problems


def per_frame(n_frames: int, work_type: str, marks: list[tuple[int, str]]) -> np.ndarray:
    """Each frame's stage index (-1 before the first mark: unknown, never "cleared")."""
    problems = check_marks(work_type, marks)
    if problems:
        raise ValueError("; ".join(problems))
    out = np.full(n_frames, -1, np.int16)
    for frame, stage in marks:
        out[max(0, frame):] = stage_index(work_type, stage)
    return out


def load_marks(path: str | Path) -> dict[str, dict]:
    """marks.jsonl: one line a shot,
    {"shot": id, "work_type": ..., "marks": [[frame, stage], ...]}."""
    out = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            out[row["shot"]] = {"work_type": row["work_type"],
                                "marks": [(int(f), str(s)) for f, s in row["marks"]]}
    return out
