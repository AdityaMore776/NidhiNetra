"""The four agents together, on the three agents' held-out cases (T168)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
import world as W  # noqa: E402

_P = W.load(Path(__file__).with_name("cases.py"), "pipeline_cases")


def cases():
    return _P._from("holdout")
