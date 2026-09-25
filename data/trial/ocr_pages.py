r"""Read the text on every downloaded evidence file with local OCR (no AI service, no key).

  - PDF pages (first 6 of each file) at 150 dpi - certificates, bills, photo sheets
  - photos: the bottom 35% only, where GPS-camera apps stamp location and time

Cached one JSON per page under data/trial/cache/ocr/ (gitignored), so re-runs only read new
files. Runs 4 workers in parallel.

Run:  .venv-trial\Scripts\python.exe data\trial\ocr_pages.py
"""

from __future__ import annotations

import io
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EVID = ROOT / "data" / "evidence"
CACHE = ROOT / "data" / "trial" / "cache" / "ocr"
MAX_PAGES = 6
PHOTO_BAND = 0.35

_ocr = None


def _engine():
    global _ocr
    if _ocr is None:
        os.environ.setdefault("OMP_NUM_THREADS", "4")
        from rapidocr_onnxruntime import RapidOCR
        _ocr = RapidOCR()
    return _ocr


def _lines(img) -> list[list]:
    import numpy as np
    res, _ = _engine()(np.asarray(img.convert("RGB")))
    return [[[[round(float(v), 1) for v in pt] for pt in box], text, round(float(conf), 3)]
            for box, text, conf in (res or [])]


def read_file(path: str) -> list[str]:
    """OCR one evidence file; returns the cache files written."""
    import pymupdf
    from PIL import Image, ImageOps
    p = Path(path)
    written = []
    if p.suffix.lower() == ".pdf":
        doc = pymupdf.open(p)
        for i in range(min(MAX_PAGES, doc.page_count)):
            out = CACHE / f"{p.stem}_p{i + 1}.json"
            if out.exists():
                continue
            pix = doc[i].get_pixmap(dpi=150)
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            data = {"file": p.name, "page": i + 1, "kind": "pdf_page", "size": img.size,
                    "text_layer": len(doc[i].get_text().strip()), "lines": _lines(img)}
            out.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            written.append(out.name)
    else:
        out = CACHE / f"{p.stem}_photo.json"
        if not out.exists():
            img = ImageOps.exif_transpose(Image.open(p))
            w, h = img.size
            band = img.crop((0, int(h * (1 - PHOTO_BAND)), w, h))
            if band.width > 1600:
                band = band.resize((1600, int(band.height * 1600 / band.width)))
            data = {"file": p.name, "page": 0, "kind": "photo_band", "size": [w, h], "lines": _lines(band)}
            out.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            written.append(out.name)
    return written


def main() -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
    start = int(sys.argv[sys.argv.index("--from-line") + 1]) if "--from-line" in sys.argv else 1
    lines = (EVID / "manifest.jsonl").read_text(encoding="utf-8").splitlines()[start - 1:]
    files = sorted({f["path"].replace("\\", "/") for line in lines for f in json.loads(line)["files"]})
    files = [str(ROOT / f) for f in files]
    if "--shard" in sys.argv:  # "--shard 0/3": this process takes every 3rd file, no worker pool
        i, n = map(int, sys.argv[sys.argv.index("--shard") + 1].split("/"))
        files = files[i::n]
        print(f"{len(files)} files (shard {i}/{n})", flush=True)
        t0 = time.time()
        for k, f in enumerate(files, 1):
            try:
                read_file(f)
            except Exception as exc:  # unreadable file: note it and continue
                print("failed", Path(f).name, str(exc)[:100], flush=True)
            if k % 25 == 0 or k == len(files):
                print(f"{k}/{len(files)} files, {(time.time() - t0) / 60:.1f} min", flush=True)
        return
    print(f"{len(files)} files", flush=True)
    t0, done, pages = time.time(), 0, 0
    with ProcessPoolExecutor(max_workers=4) as pool:
        futs = {pool.submit(read_file, f): f for f in files}
        for fut in as_completed(futs):
            done += 1
            try:
                pages += len(fut.result())
            except Exception as exc:  # unreadable file: note it and continue
                print("failed", Path(futs[fut]).name, str(exc)[:100], flush=True)
            if done % 25 == 0 or done == len(files):
                print(f"{done}/{len(files)} files, {pages} new pages, {(time.time() - t0) / 60:.1f} min",
                      flush=True)
    sys.exit(0)


if __name__ == "__main__":
    main()
