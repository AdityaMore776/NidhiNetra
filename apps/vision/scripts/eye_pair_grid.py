"""Eye-check helper (T153): the not-yet-checked items of a split as a compact grid, two pairs a
row, 16 pairs an image (A | B each), with an index of eyecheck keys to record the verdicts.

    python scripts/eye_pair_grid.py <items.jsonl> <out_dir> [--split test] [--source timelapse]

After looking: append one line to eye_checks.jsonl, {"checked_keys": [...], "wrong_keys": [...]},
using index.json (n -> key). Photos are read from NN_DATA (default D:\\nidhinetra-data).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from drishti_vision import eyecheck  # noqa: E402
from drishti_vision.vlmdata import read_items  # noqa: E402

ROOT = Path(os.environ.get("NN_DATA", r"D:\nidhinetra-data"))
W, H = 300, 260


def fit(rel: str) -> np.ndarray:
    im = cv2.imread(str(ROOT / rel))
    s = min(W / im.shape[1], H / im.shape[0])
    im = cv2.resize(im, (int(im.shape[1] * s), int(im.shape[0] * s)))
    out = np.full((H, W, 3), 255, np.uint8)
    out[:im.shape[0], :im.shape[1]] = im
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("items")
    ap.add_argument("out")
    ap.add_argument("--split", default="test")
    ap.add_argument("--source", default="")
    a = ap.parse_args()
    sel = [i for i in read_items(a.items) if i.split == a.split and i.label_check != "eye"
           and (not a.source or i.source == a.source)]
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    cells = []
    for n, it in enumerate(sel):
        band = np.full((20, 2 * W + 10, 3), 235, np.uint8)
        cv2.putText(band, f"{n} {it.trick} {it.target['verdict']} {it.site}", (3, 14),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 0, 160), 1)
        gap = np.full((H, 10, 3), 255, np.uint8)
        cells.append(np.vstack([band, np.hstack([fit(it.image_a), gap, fit(it.image_b)])]))
    k = 0
    for g in range(0, len(cells), 16):
        rows = []
        for r in range(g, min(g + 16, len(cells)), 2):
            pair = cells[r:r + 2] + ([np.full_like(cells[r], 255)] if r + 1 >= len(cells) else [])
            rows.append(np.hstack([pair[0], np.full((pair[0].shape[0], 20, 3), 120, np.uint8),
                                   pair[1]]))
        cv2.imwrite(str(out / f"grid_{k:02d}.jpg"), np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 80])
        k += 1
    (out / "index.json").write_text(json.dumps([{"n": n, "key": eyecheck.key(i)}
                                                for n, i in enumerate(sel)]))
    print(len(sel), "items,", k, "images")


if __name__ == "__main__":
    main()
