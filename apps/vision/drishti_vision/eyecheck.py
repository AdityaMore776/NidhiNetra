"""Contact sheets for checking items' labels by eye (T153; the owner's rule: every test label is
checked).

Each row: photo A | photo B, with the item number, the claim, the trick and the label written
above. A person (or an agent, first) looks at every sheet and records the numbers whose label is
wrong in eye_checks.jsonl; vlmdata items then carry label_check "eye" (checked) or are dropped
(wrong).
"""

from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np

from drishti_vision.vlmdata import Item

H = 260


def _fit(img: np.ndarray, h: int = H, w: int = 340) -> np.ndarray:
    s = min(h / img.shape[0], w / img.shape[1])
    img = cv2.resize(img, (max(1, int(img.shape[1] * s)), max(1, int(img.shape[0] * s))))
    out = np.full((h, w, 3), 30, np.uint8)
    y, x = (h - img.shape[0]) // 2, (w - img.shape[1]) // 2
    out[y:y + img.shape[0], x:x + img.shape[1]] = img
    return out


def _ascii(s: str) -> str:
    return s.encode("ascii", "replace").decode()


def sheets(items: list[Item], root: Path, out_dir: Path, per_sheet: int = 10) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for k in range(0, len(items), per_sheet):
        rows = []
        for n, it in enumerate(items[k:k + per_sheet], start=k):
            a = cv2.imread(str(root / it.image_a))
            b = cv2.imread(str(root / it.image_b))
            if a is None or b is None:
                continue
            band = np.full((34, 700, 3), 255, np.uint8)
            text = f"#{n} [{it.trick}] {it.target['verdict'].upper()} | {it.claim_kind}: "
            cv2.putText(band, _ascii(text + it.claim)[:95], (4, 14), cv2.FONT_HERSHEY_SIMPLEX,
                        0.42, (0, 0, 160), 1)
            cv2.putText(band, _ascii(f"{it.site} {it.work_type}  A | B"), (4, 29),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (60, 60, 60), 1)
            gap = np.full((H, 20, 3), 255, np.uint8)
            rows.append(np.vstack([band, np.hstack([_fit(a), gap, _fit(b)])]))
        if rows:
            p = out_dir / f"sheet_{k // per_sheet:03d}.jpg"
            cv2.imwrite(str(p), np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 80])
            paths.append(p)
    return paths


def apply(items: list[Item], checks_path: Path) -> tuple[list[Item], dict]:
    """Marks checked items `eye`; drops the ones recorded wrong. checks: one JSON line a sheet
    review, {"split": ..., "checked": [item numbers], "wrong": [item numbers], "note": ...}."""
    checked, wrong = set(), set()
    for line in checks_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            checked |= set(r.get("checked", []))
            wrong |= set(r.get("wrong", []))
    kept = []
    for n, it in enumerate(items):
        if n in wrong:
            continue
        if n in checked:
            it.label_check = "eye"
        kept.append(it)
    return kept, {"checked": len(checked), "wrong": len(wrong), "kept": len(kept)}
