"""Eye-check helper (T153): asset cards for checking GeoMGNREGA labels by eye, one row an asset.

Every label of an asset's items follows from its stage photos (vlmdata.mgnrega_items), so one look
at the six photos (1a 1b before, 2a 2b during, 3a 3b after) plus the other-place photo checks them
all. What to look for:
  - a BEFORE photo that already shows the finished work  -> flag "<photo>:built"
  - an AFTER photo that does not show the finished work  -> flag "<photo>:unfinished"
  - a DURING photo used as "work under way" showing nothing new -> flag "<photo>:nothing"

    SPLIT=test python scripts/eye_asset_cards.py render <items.jsonl> <eye_checks.jsonl> <out_dir>
    SPLIT=test python scripts/eye_asset_cards.py resolve <items.jsonl> <out_dir> <flags.json>
        -> one eye_checks.jsonl line on stdout
flags.json: {"<asset id>": ["s1_p2:built", ...], ...}; assets not listed were all right.
Photos are read from NN_DATA (default D:/nidhinetra-data).
"""

from __future__ import annotations

import json
import os
import sys
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from drishti_vision import eyecheck  # noqa: E402
from drishti_vision.vlmdata import read_items  # noqa: E402

SPLIT = os.environ.get("SPLIT", "test")
ROOT = Path(os.environ.get("NN_DATA", "D:/nidhinetra-data"))
W, H = 196, 200
SLOTS = ("s1_p1", "s1_p2", "s2_p1", "s2_p2", "s3_p1", "s3_p2")


def unchecked_by_asset(items_path, checks):
    its = [i for i in read_items(items_path) if i.split == SPLIT and i.source == "geomgnrega"]
    done = set()
    if checks and Path(checks).exists():
        for line in Path(checks).read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                done |= {eyecheck._norm(k) for k in r.get("checked_keys", [])}
                done |= {eyecheck._norm(k) for k in r.get("wrong_keys", [])}
    by = defaultdict(list)
    for i in its:
        if eyecheck.key(i) not in done:
            by[i.site].append(i)
    return dict(sorted(by.items()))


def tile(path, label):
    img = cv2.imread(str(ROOT / path)) if path else None
    out = np.full((H + 16, W, 3), 255, np.uint8)
    if img is not None:
        s = min(H / img.shape[0], W / img.shape[1])
        im = cv2.resize(img, (max(1, int(img.shape[1] * s)), max(1, int(img.shape[0] * s))))
        y, x = 16 + (H - im.shape[0]) // 2, (W - im.shape[1]) // 2
        out[y:y + im.shape[0], x:x + im.shape[1]] = im
    cv2.putText(out, label, (3, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 0, 160), 1)
    return out


def render(items_path, checks, out_dir):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    by = unchecked_by_asset(items_path, checks)
    rows, index, n_img = [], [], 0
    for k, (site, its) in enumerate(by.items()):
        folder = f"gov/mgnrega/photos/{site}"
        used = {Path(p).stem for i in its for p in (i.image_a, i.image_b) if folder in p}
        other = [i.image_b for i in its if i.trick == "other_site"]
        tiles = [tile(f"{folder}/{s}.jpg" if (ROOT / folder / f"{s}.jpg").exists() else None,
                      s + (" *" if s in used else "")) for s in SLOTS]
        tiles.append(tile(other[0] if other else None, "other place"))
        gap = np.full((H + 16, 6, 3), 255, np.uint8)
        body = np.hstack([x for t in tiles for x in (t, gap)])
        band = np.full((22, body.shape[1], 3), 235, np.uint8)
        kinds = ", ".join(sorted({f"{i.trick}:{i.target['verdict']}" for i in its}))
        txt = f"[{k}] {site} {its[0].work_type} | {kinds}"
        cv2.putText(band, txt.encode("ascii", "replace").decode()[:150], (4, 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1)
        rows.append(np.vstack([band, body]))
        index.append({"n": k, "site": site, "items": len(its)})
        if len(rows) == 8:
            cv2.imwrite(str(out_dir / f"cards_{n_img:03d}.jpg"), np.vstack(rows),
                        [cv2.IMWRITE_JPEG_QUALITY, 82])
            rows, n_img = [], n_img + 1
    if rows:
        cv2.imwrite(str(out_dir / f"cards_{n_img:03d}.jpg"), np.vstack(rows),
                    [cv2.IMWRITE_JPEG_QUALITY, 82])
        n_img += 1
    (out_dir / "index.json").write_text(json.dumps(index))
    print(len(by), "assets,", sum(len(v) for v in by.values()), "items,", n_img, "images")


def wrong(it, flags):
    """Whether a flag on one of the asset's photos makes this item's label wrong."""
    a, b = Path(it.image_a).stem, Path(it.image_b).stem
    v, t = it.target["verdict"], it.trick
    for f in flags:
        photo, what = f.split(":")
        if what == "built":           # a before photo already shows the finished work
            if v == "shown" and a == photo:
                return True
            if t in ("view", "swapped") and b == photo and it.claim_kind == "reached":
                return True
            if t == "swapped" and b == photo:
                return True
        if what == "unfinished" and v == "shown" and b == photo:
            return True
        if what == "nothing" and v == "shown" and b == photo:
            return True
        if what == "bad":             # the photo cannot be judged at all (sign, blur, other place)
            if photo in (a, b) and t not in ("other_site", "busy", "double_claim"):
                return True
    return False


def resolve(items_path, out_dir, flags_path):
    by = unchecked_by_asset(items_path, None)
    index = json.loads((Path(out_dir) / "index.json").read_text())
    shown_sites = {r["site"] for r in index}
    flags = json.loads(Path(flags_path).read_text())
    checked, bad = [], []
    for site, its in by.items():
        if site not in shown_sites:
            continue
        for i in its:
            checked.append(eyecheck.key(i))
            if wrong(i, flags.get(site, [])):
                bad.append(eyecheck.key(i))
    print(json.dumps({"note": f"v5 test, GeoMGNREGA, one asset card a row ({out_dir}); flags "
                              f"{json.dumps(flags)} (agent, 8 Oct 2026)",
                      "checked_keys": checked, "wrong_keys": bad}))
    print(f"{len(checked)} checked, {len(bad)} wrong", file=sys.stderr)


if __name__ == "__main__":
    if sys.argv[1] == "render":
        render(*sys.argv[2:5])
    else:
        resolve(*sys.argv[2:5])
