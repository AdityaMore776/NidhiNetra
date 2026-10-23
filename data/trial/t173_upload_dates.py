r"""T173 part 1: were the test photos online before the base model (Qwen3-VL) was trained?

Each GeoMGNREGA photo's address on Bhuvan holds its upload month (.../photos/<stage>/<YYYY-MM>/...).
Qwen3-VL-4B-Instruct was released in October 2025, so a photo uploaded after September 2025 cannot be
in its pretraining. This counts, for training, test, fresh and probe, the photos uploaded by month.

  D:\nidhinetra-data\venv\Scripts\python.exe data\trial\t173_upload_dates.py

Writes data/trial/results/t173_upload_dates.txt.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = Path(r"D:\nidhinetra-data")
REL = DATA / "release" / "siteclaim_test_v1"
ASSETS = DATA / "gov" / "mgnrega" / "assets.jsonl"
OUT = ROOT / "data" / "trial" / "results" / "t173_upload_dates.txt"
RELEASED = "2025-10"            # Qwen3-VL-4B-Instruct on Hugging Face
_MONTH = re.compile(r"/photos/\d/(\d{4}-\d{2})/")
_PHOTO = re.compile(r"photos/(mg-\d+)/s(\d)_p(\d)\.jpg$")


def _read(p: Path) -> list[dict]:
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]


def main() -> None:
    month = {}
    for a in _read(ASSETS):
        for ph in a.get("photos") or []:
            m = _MONTH.search(ph.get("url") or "")
            if m:
                month[(f"mg-{a['sid']}", int(ph["stage"]), int(ph["n"]))] = m.group(1)
    train = [r for r in _read(DATA / "vlm" / "v6" / "items_eye.jsonl")
             if r["split"] == "train" and r.get("real", True)]
    sets = {"training": train} | {n: _read(REL / f"items_{n}.jsonl") for n in ("test", "fresh", "probe")}
    lines = [f"T173: upload month of each GeoMGNREGA photo (base model released {RELEASED})", ""]
    for name, items in sets.items():
        photos = {(r[s]) for r in items for s in ("image_a", "image_b") if "mgnrega" in r[s]}
        months = []
        for p in photos:
            m = _PHOTO.search(p.replace("\\", "/"))
            months.append(month.get((m.group(1), int(m.group(2)), int(m.group(3)))) if m else None)
        known = [x for x in months if x]
        after = sum(x >= RELEASED for x in known)
        years = Counter(x[:4] for x in known)
        lines.append(f"{name:9} GeoMGNREGA photos {len(photos)}, month known {len(known)}, "
                     f"uploaded {RELEASED} or later {after}"
                     f" | by year {dict(sorted(years.items()))}"
                     + (f" | newest {max(known)}" if known else ""))
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
