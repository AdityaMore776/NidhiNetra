r"""Download the evidence eSAKSHI publishes for completed works (pilot sample).

Public endpoints of the MPLADS eSAKSHI dashboard - the dataset MoSPI names in SIH26102:

  POST /rest/PreLoginDashboardData/getAttachIdsbyFlag        {"json": {"FLAG": "3", "WORK_ID": id}}
       -> [{"FILE_NAME": [...], "ATTACH_ID": [...]}]
  POST /rest/PreLoginCitizenWorkRcmdRest/getAttachmentById   {"id": attach_id}
       -> [{"FILE_NAME": ..., "URL": <base64 file>}]

Polite by design: one request every 1.5 s, each file fetched once (cached on disk, so a
re-run resumes), and it stops by itself after 10 consecutive failures. Files stay on this PC
under data/evidence/ (gitignored); data/evidence/manifest.jsonl records what came from where.

Run:
  apps\engine\.venv\Scripts\python.exe data\harvest\esakshi_evidence.py ^
      --district "PRATAPGARH" --state "Uttar Pradesh" --national 400
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import random
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW = Path.home() / "saakshya" / "data" / "raw" / "inrolls"
OUT = ROOT / "data" / "evidence"
FILES = OUT / "files"
MANIFEST = OUT / "manifest.jsonl"

BASE = "https://mplads.mospi.gov.in"
LIST_URL = BASE + "/rest/PreLoginDashboardData/getAttachIdsbyFlag"
FILE_URL = BASE + "/rest/PreLoginCitizenWorkRcmdRest/getAttachmentById"
HEADERS = {
    "Content-Type": "application/json; charset=utf-8",
    "User-Agent": "DRISHTI-SIH2026-prototype/0.1 (research pilot; 1 request per 1.5 s)",
    "Referer": BASE + "/digigov/dashboard.html",
}
GAP_S = 1.5
MAX_CONSECUTIVE_FAILURES = 10
REF = re.compile(r"^(WS/[^/]+/\d{4}-\d{4}/\d+)-")

_last = 0.0


def post(url: str, body: dict, timeout: float = 90.0) -> list:
    global _last
    wait = GAP_S - (time.time() - _last)
    if wait > 0:
        time.sleep(wait)
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST",
                                 headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8", errors="replace"))
    finally:
        _last = time.time()


def candidates() -> pd.DataFrame:
    cols = ["tile_label", "ATTACH_ID", "WORK_ID", "FLAG", "ACTIVITY_NAME", "IDA_NAME", "STATE_NAME"]
    frames = [pd.read_csv(RAW / f, usecols=cols, dtype=str, low_memory=False)
              for f in ("works_ls17.csv", "works_ls18.csv", "works_rs.csv")]
    d = pd.concat(frames, ignore_index=True)
    d = d[(d.tile_label == "Works Completed") & d.ATTACH_ID.notna() & d.WORK_ID.notna()].copy()
    d["work_id"] = d.ACTIVITY_NAME.str.extract(REF, expand=False)
    d["district"] = d.IDA_NAME.str.extract(r"^([^(]+)", expand=False).str.strip().str.upper()
    return d.dropna(subset=["work_id"]).drop_duplicates("work_id")


def select(d: pd.DataFrame, district: str | None, state: str | None, national: int,
           seed: int) -> pd.DataFrame:
    parts = []
    if district:
        m = d.district == district.upper()
        if state:
            m &= d.STATE_NAME.str.lower() == state.lower()
        parts.append(d[m].assign(sample="district"))
    rest = d.drop(parts[0].index) if parts else d
    if national:
        parts.append(rest.sample(n=min(national, len(rest)), random_state=seed).assign(sample="national"))
    return pd.concat(parts, ignore_index=True)


def done_works() -> set[str]:
    if not MANIFEST.exists():
        return set()
    return {json.loads(line)["work_id"] for line in MANIFEST.read_text(encoding="utf-8").splitlines()
            if line.strip()}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--district")
    ap.add_argument("--state")
    ap.add_argument("--national", type=int, default=0)
    ap.add_argument("--seed", type=int, default=26)
    args = ap.parse_args()

    FILES.mkdir(parents=True, exist_ok=True)
    todo = select(candidates(), args.district, args.state, args.national, args.seed)
    seen = done_works()
    todo = todo[~todo.work_id.isin(seen)]
    print(f"{len(todo)} works to fetch ({len(seen)} already in the manifest)", flush=True)

    failures, t0, n_files, n_bytes = 0, time.time(), 0, 0
    with MANIFEST.open("a", encoding="utf-8") as man:
        for i, row in enumerate(todo.itertuples(index=False), 1):
            rec = {"work_id": row.work_id, "esakshi_work_id": row.WORK_ID, "flag": row.FLAG,
                   "sample": row.sample, "district": row.district, "state": row.STATE_NAME,
                   "files": [], "errors": []}
            try:
                listing = post(LIST_URL, {"json": {"FLAG": row.FLAG, "WORK_ID": row.WORK_ID}})
                names = listing[0].get("FILE_NAME") if listing else None
                ids = listing[0].get("ATTACH_ID") if listing else None
                if not isinstance(names, list) or not isinstance(ids, list):
                    names, ids = [], []
                for name, aid in zip(names, ids):
                    if not aid or name == "File not available.":
                        continue
                    ext = (name.rsplit(".", 1)[-1] if "." in name else "bin").lower()[:5]
                    path = FILES / f"{aid}.{ext}"
                    if not path.exists():
                        got = post(FILE_URL, {"id": aid})
                        blob = base64.b64decode(got[0]["URL"])
                        path.write_bytes(blob)
                    blob = path.read_bytes()
                    n_files += 1
                    n_bytes += len(blob)
                    rec["files"].append({"name": name, "attach_id": aid, "path": str(path.relative_to(ROOT)),
                                         "bytes": len(blob), "sha256": hashlib.sha256(blob).hexdigest()})
                failures = 0
            except (urllib.error.URLError, TimeoutError, ValueError, KeyError, IndexError) as exc:
                failures += 1
                rec["errors"].append(f"{type(exc).__name__}: {str(exc)[:120]}")
            rec["fetched_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
            man.write(json.dumps(rec, ensure_ascii=False) + "\n")
            man.flush()
            if i % 25 == 0 or i == len(todo):
                print(f"{i}/{len(todo)} works, {n_files} files, {n_bytes / 1e6:.0f} MB, "
                      f"{(time.time() - t0) / 60:.1f} min", flush=True)
            if failures >= MAX_CONSECUTIVE_FAILURES:
                print("stopping: 10 consecutive failures - the site may be refusing requests", flush=True)
                sys.exit(2)


if __name__ == "__main__":
    random.seed(26)
    main()
