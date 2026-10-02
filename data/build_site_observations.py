r"""Read every pilot site photo once for Site Progress v2 (T510): what it shows, and its plaque.

For each photo in data/evidence/manifest.jsonl:
  - the local zero-shot reader (agents/site_progress/readers.py ZeroShotReader: an open CLIP
    model on the CPU, free) scores it against reference/site_concepts.yaml
  - the local OCR (RapidOCR, as data/trial/ocr_pages.py) reads the WHOLE photo, and
    agents/site_progress/plaque.py keeps only whether an MPLADS plaque is named and its dates
  - optional, --vlm: with GEMINI_API_KEY set (the owner's free-tier key, T501), each work's
    claims are judged against up to 4 of its photos: shown / not shown / can't tell, within a
    daily cap (--cap) and a ledger (data/build/vision_ledger.json)

Every reading is cached by the photo's SHA-256 under data/build/site_cache/ (gitignored), so a
re-run reads only new photos and a photo on two works is read once. Only readings are kept: no
picture, no OCR text, no names.

Updates data/build/evidence_facts.parquet (written first by data/build_evidence.py): each photo
gets "site", each work with judgements "site_judgements". Then load it: data/load_db.py.

One-time setup, in the trial venv (Windows PowerShell):
  .venv-trial\Scripts\python.exe -m pip install open_clip_torch torch rapidocr_onnxruntime
Run:
  .venv-trial\Scripts\python.exe data\build_site_observations.py            (all photos)
  .venv-trial\Scripts\python.exe data\build_site_observations.py --limit 20 (a quick try)
  $env:GEMINI_API_KEY="..."; .venv-trial\Scripts\python.exe data\build_site_observations.py --vlm
"""

from __future__ import annotations

import argparse
import io
import json
import math
import sys
import time
from collections import Counter
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "engine"))
from drishti.agents.photo_evidence.index import PHOTO_EXT  # noqa: E402
from drishti.agents.site_progress import observe, plaque  # noqa: E402
from drishti.agents.site_progress.claims import claims_of  # noqa: E402
from drishti.agents.site_progress.readers import (  # noqa: E402
    GeminiReader,
    QuotaReached,
    ZeroShotReader,
)

EVID = ROOT / "data" / "evidence"
BUILD = ROOT / "data" / "build"
CACHE = BUILD / "site_cache"
MAX_SIDE = 1024
VLM_PHOTOS = 4


def clean(rec: dict) -> dict:
    """NaN / NaT from pandas -> None (as data/common.py, without its database imports: this
    job runs in the trial venv)."""
    return {k: None if v is None or v is pd.NaT or (isinstance(v, float) and math.isnan(v))
            else v for k, v in rec.items()}


def _image(path: Path):
    from PIL import Image, ImageOps
    img = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
    if max(img.size) > MAX_SIDE:
        img.thumbnail((MAX_SIDE, MAX_SIDE))
    return img


def _ocr_text(img, ocr) -> str:
    import numpy as np
    res, _ = ocr(np.asarray(img))
    return " ".join(text for _box, text, _conf in (res or []))


def read_photo(path: Path, sha: str, reader, ocr) -> dict | None:
    """The cached reading of one photo, made if missing."""
    cached = CACHE / f"{sha}.json"
    if cached.exists():
        site = json.loads(cached.read_text(encoding="utf-8"))
        if site.get("version") == observe.VERSION:
            return site
    try:
        img = _image(path)
    except Exception:                    # unreadable or damaged image: counted, not fatal
        return None
    site = reader.read(img)
    if ocr is not None:
        site["plaque"] = plaque.read(_ocr_text(img, ocr))
    cached.write_text(json.dumps(site), encoding="utf-8")
    return site


def _jpeg(path: Path) -> bytes:
    buf = io.BytesIO()
    _image(path).save(buf, format="JPEG", quality=85)
    return buf.getvalue()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="read at most this many new photos")
    ap.add_argument("--model", default="ViT-B-32")
    ap.add_argument("--pretrained", default="laion2b_s34b_b79k")
    ap.add_argument("--no-ocr", action="store_true", help="skip the plaque reading")
    ap.add_argument("--vlm", action="store_true", help="also judge claims with GEMINI_API_KEY")
    ap.add_argument("--cap", type=int, default=200, help="most model calls per day (--vlm)")
    args = ap.parse_args()

    CACHE.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    reader = ZeroShotReader(args.model, args.pretrained)
    ocr = None
    if not args.no_ocr:
        from rapidocr_onnxruntime import RapidOCR
        ocr = RapidOCR()

    ev = pd.read_parquet(BUILD / "evidence_facts.parquet")
    facts = {r.work_id: json.loads(r.data) for r in ev.itertuples()}
    paths = {}
    for line in (EVID / "manifest.jsonl").read_text(encoding="utf-8").splitlines():
        rec = json.loads(line)
        for f in rec["files"]:
            paths[(rec["work_id"], f["attach_id"])] = ROOT / f["path"].replace("\\", "/")

    counts: Counter = Counter()
    fresh = 0
    for wid, data in facts.items():
        for f in data.get("files") or ():
            if f.get("ext") not in PHOTO_EXT:
                continue
            path = paths.get((wid, f["id"]))
            if path is None or not path.exists():
                counts["photo file missing"] += 1
                continue
            new = not (CACHE / f"{f['sha256']}.json").exists()
            if new and args.limit and fresh >= args.limit:
                counts["left for a later run"] += 1
                continue
            site = read_photo(path, f["sha256"], reader, ocr)
            fresh += new
            if site is None:
                counts["unreadable"] += 1
                continue
            f["site"] = site
            counts["read"] += 1
            counts["plaque named"] += bool((site.get("plaque") or {}).get("scheme"))

    if args.vlm:
        g = GeminiReader(daily_cap=args.cap, ledger=BUILD / "vision_ledger.json")
        works = pd.read_parquet(BUILD / "works.parquet")
        works = {r["work_id"]: clean(r) for r in works[works.work_id.isin(facts)]
                 .to_dict("records")}
        try:
            for wid, data in facts.items():
                cs = [c.text for c in claims_of(works.get(wid, {}) | {"evidence": data})]
                shots = [(f["sha256"], _jpeg(paths[(wid, f["id"])]))
                         for f in data.get("files") or ()
                         if f.get("ext") in PHOTO_EXT and (wid, f["id"]) in paths
                         and paths[(wid, f["id"])].exists()][:VLM_PHOTOS]
                if cs and shots:
                    data["site_judgements"] = g.judge(cs, shots)
                    counts["works judged by the VLM"] += 1
        except QuotaReached as exc:
            print(f"stopped: {exc} (re-run tomorrow; judged works are cached)")

    ev["data"] = [json.dumps(facts[w]) for w in ev.work_id]
    ev["version"] = [f"{v}+{observe.VERSION}" if observe.VERSION not in v else v
                     for v in ev.version]
    ev.to_parquet(BUILD / "evidence_facts.parquet", index=False)
    print(f"{dict(counts)} in {time.time() - t0:.0f}s -> {BUILD / 'evidence_facts.parquet'}")


if __name__ == "__main__":
    main()
