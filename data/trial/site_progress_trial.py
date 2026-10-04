r"""Trial (T510): Site Progress v2 on the pilot's real photos, and its go / no-go.

Runs the engine (agents/site_progress) on every pilot work, with the photo readings stored by
data/build_site_observations.py. Then, for reading by eye:

  results/site_progress_sample.csv   photos to label: every photo of a work with a finding,
                                     and up to 20 random photos for each reading (shows /
                                     not_built / unclear), seed 510
  data/build/site_progress_sheet.html  the same photos on one page with their readings
                                     (gitignored: it shows the photos)

Label them in data/trial/site_progress_labels.py (PHOTO_LABELS: does the photo show the finished
asset? WORK_LABELS: is the finding worth a site check?) and run again: the trial then reports
how often each reading is right, a sweep of the cut-offs, and the go / no-go:

  GO     "not_built" right >= 80% on >= 20 labelled photos, "shows" right >= 80% on >= 20,
         and the engine's findings worth a site check >= 70% on >= 10 works
  NO-GO  anything else: the engine stays off (engine.py) and FINDINGS says why

Writes results/site_progress_trial.json.
Run (after build_site_observations.py), in the engine venv:
  apps\engine\.venv\Scripts\python.exe data\trial\site_progress_trial.py
"""

from __future__ import annotations

import csv
import html
import json
import random
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "data"))
sys.path.insert(0, str(ROOT / "data" / "trial"))
from common import BUILD, clean  # noqa: E402
from site_progress_labels import PHOTO_LABELS, WORK_LABELS  # noqa: E402

from drishti.agents.photo_evidence.index import PHOTO_EXT, PhotoIndex  # noqa: E402
from drishti.agents.site_progress import observe  # noqa: E402
from drishti.agents.site_progress import photos as agent  # noqa: E402
from drishti.validation import pii  # noqa: E402

OUT = ROOT / "data" / "trial" / "results"
AS_OF = date(2026, 9, 26)          # the evidence was downloaded 25-26 Sept 2026
SEED = 510
PER_READING = 20
GO = {"photo_precision": 0.80, "photo_min": 20, "work_precision": 0.70, "work_min": 10}


def _share(hit: int, n: int) -> float | None:
    return round(hit / n, 3) if n else None


def _paths() -> dict:
    out = {}
    for line in (ROOT / "data" / "evidence" / "manifest.jsonl").read_text(
            encoding="utf-8").splitlines():
        rec = json.loads(line)
        for f in rec["files"]:
            out[(rec["work_id"], f["attach_id"])] = f["path"].replace("\\", "/")
    return out


def sweep(rows: list[dict]) -> list[dict]:
    """How right a "not built" reading would be at other cut-offs, on the labelled photos."""
    out = []
    for cut in (0.5, 0.6, 0.7, 0.8, 0.9):
        picked = [r for r in rows if r["not_built"] >= cut and r["built"] <= observe.NOT_BUILT_MAX]
        right = sum(PHOTO_LABELS[r["file"]] == "not_built" for r in picked)
        out.append({"not_built_cut": cut, "read_not_built": len(picked),
                    "right": right, "precision": _share(right, len(picked))})
    return out


def main() -> None:
    ev = pd.read_parquet(BUILD / "evidence_facts.parquet")
    facts = {r.work_id: json.loads(r.data) for r in ev.itertuples()}
    w = pd.read_parquet(BUILD / "works.parquet")
    works = [clean(r) | {"evidence": facts[r["work_id"]]}
             for r in w[w.work_id.isin(facts)].to_dict("records")]
    photos = PhotoIndex.build(works)
    results = {x["work_id"]: agent.assess(x, AS_OF, photos) for x in works}
    paths = _paths()

    status = Counter(r.status.value for r in results.values())
    asset = Counter(r.evidence.get("claims", {}).get("asset", "no asset claim")
                    for r in results.values() if r.assessed)
    by_code: dict[str, list[str]] = defaultdict(list)
    for wid, r in results.items():
        for f in r.findings:
            by_code[f.code].append(wid)
    rows = []
    for x in works:
        group = observe.group_of(x.get("work_type_code"))
        for f in x["evidence"].get("files") or ():
            if f.get("ext") not in PHOTO_EXT or "site" not in f:
                continue
            g = (f["site"].get("groups") or {}).get(group or "", {})
            rows.append({
                "work_id": x["work_id"], "file": f["id"], "type": x.get("work_type_code"),
                "group": group, "status": x.get("status"),
                "reading": observe.read(f["site"], group) or "no group",
                "built": g.get("built", 0.0), "not_built": g.get("not_built", 0.0),
                "not_site": g.get("not_site", 0.0),
                "plaque": bool((f["site"].get("plaque") or {}).get("scheme")),
                "finding": ";".join(sorted({c.code for c in results[x["work_id"]].findings})),
                "description": (pii.mask(str(x.get("description") or "")) or "")[:200],
                "photo": paths.get((x["work_id"], f["id"]), "")})
    readings = Counter(r["reading"] for r in rows)

    rng = random.Random(SEED)
    sample = [r for r in rows if r["finding"]]
    for reading in ("shows", "not_built", "unclear"):
        pool = [r for r in rows if r["reading"] == reading and not r["finding"]]
        sample += rng.sample(pool, min(PER_READING, len(pool)))
    fields = list(rows[0]) if rows else []
    with (OUT / "site_progress_sample.csv").open("w", newline="", encoding="utf-8") as fh:
        wr = csv.DictWriter(fh, fieldnames=fields)
        wr.writeheader()
        wr.writerows(sample)
    cards = "".join(
        f"<figure><img src='../../{html.escape(r['photo'])}' loading='lazy'>"
        f"<figcaption><b>{html.escape(r['file'])}</b> {html.escape(str(r['type']))}: "
        f"{r['reading']} (built {r['built']:.2f}, not built {r['not_built']:.2f})"
        f"{' · plaque' if r['plaque'] else ''}<br>{html.escape(r['description'])}"
        "</figcaption></figure>" for r in sample)
    (BUILD / "site_progress_sheet.html").write_text(
        "<!doctype html><meta charset=utf-8><title>Site Progress sample</title><style>"
        "body{font:14px sans-serif;display:grid;grid-template-columns:repeat(auto-fill,"
        "minmax(320px,1fr));gap:12px;padding:12px}img{width:100%}</style>" + cards,
        encoding="utf-8")

    labelled = [r for r in rows if r["file"] in PHOTO_LABELS]
    photo_eval = {}
    for reading in ("shows", "not_built"):
        rs = [r for r in labelled if r["reading"] == reading]
        right = sum(PHOTO_LABELS[r["file"]] == reading for r in rs)
        photo_eval[reading] = {"labelled": len(rs), "right": right,
                               "precision": _share(right, len(rs))}
    work_rows = [w for w in WORK_LABELS if w in results and results[w].findings]
    work_right = sum(WORK_LABELS[w] == "yes" for w in work_rows)
    work_eval = {"labelled": len(work_rows), "worth_a_site_check": work_right,
                 "precision": _share(work_right, len(work_rows))}
    ok = (all(e["labelled"] >= GO["photo_min"] and (e["precision"] or 0) >= GO["photo_precision"]
              for e in photo_eval.values())
          and work_eval["labelled"] >= GO["work_min"]
          and (work_eval["precision"] or 0) >= GO["work_precision"])
    res = {"as_of": str(AS_OF), "works": len(works), "status": dict(status),
           "asset_claims": dict(asset), "photos_read": len(rows), "readings": dict(readings),
           "plaques_named": sum(r["plaque"] for r in rows),
           "findings": {c: {"works": len(ws), "ids": sorted(ws)} for c, ws in by_code.items()},
           "sample": len(sample), "labels": {"photos": len(labelled), "works": len(work_rows)},
           "photo_precision": photo_eval, "work_precision": work_eval,
           "sweep": sweep(labelled) if labelled else [],
           "go": "GO" if ok else "NO-GO (not measured enough yet, or below target)",
           "thresholds": {"SHOW_MIN": observe.SHOW_MIN, "NOT_BUILT_MIN": observe.NOT_BUILT_MIN,
                          "NOT_BUILT_MAX": observe.NOT_BUILT_MAX,
                          "NOT_SITE_MIN": observe.NOT_SITE_MIN}}
    (OUT / "site_progress_trial.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in res.items() if k != "findings"}, indent=2))
    print(f"label {len(sample)} photos: {OUT / 'site_progress_sample.csv'} "
          f"(see them in {BUILD / 'site_progress_sheet.html'})")


if __name__ == "__main__":
    main()
