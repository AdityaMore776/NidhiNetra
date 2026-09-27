"""OWNER ONLY: bundle the private data teammates need into one zip for the team's private Google Drive.

    python scripts/team/make_pack.py "%USERPROFILE%\\Documents\\DRISHTI-team-pack.zip"
    python scripts/team/make_pack.py out.zip --no-evidence      # small pack (~300 MB), no evidence files

The pack holds real government records (names, signatures, bank details on certificates). It goes to the
team's PRIVATE Drive folder only: never GitHub, never a public link. Teammates unpack it with
scripts/team/install_pack.py. Contents and rules: docs/team/DATA-PACK.md.
"""

from __future__ import annotations

import argparse
import io
import os
import subprocess
import tarfile
import zipfile
from pathlib import Path

from _common import ROOT, now_ist

OLD = Path(os.environ.get("DRISHTI_OLD_REPO", Path.home() / "saakshya"))
OLD_COMMIT = "abf2da4"   # the approved snapshot of the research build
REPO_DIRS = ["data/build", "data/trial/cache"]
EVIDENCE = "data/evidence"
OLD_RAW = ["data/raw/MPLADS_real.csv", "data/raw/lgd", "data/raw/inrolls", "data/raw/guidelines",
           "data/raw/cag"]
STORED = {".jpg", ".jpeg", ".png", ".pdf", ".parquet", ".zip", ".webp"}   # already compressed


def add_tree(z: zipfile.ZipFile, src: Path, prefix: str) -> int:
    n = 0
    files = [src] if src.is_file() else sorted(p for p in src.rglob("*") if p.is_file())
    for p in files:
        rel = p.name if src.is_file() else p.relative_to(src).as_posix()
        mode = zipfile.ZIP_STORED if p.suffix.lower() in STORED else zipfile.ZIP_DEFLATED
        z.write(p, f"{prefix}/{rel}", compress_type=mode)
        n += 1
    return n


def main() -> None:
    ap = argparse.ArgumentParser(description="build the private team data pack")
    ap.add_argument("out", type=Path)
    ap.add_argument("--no-evidence", action="store_true", help="leave out data/evidence (760 MB)")
    args = ap.parse_args()

    missing = [d for d in REPO_DIRS if not (ROOT / d).exists()] + \
              [d for d in OLD_RAW if not (OLD / d).exists()]
    if missing:
        raise SystemExit(f"missing on this machine: {missing}")

    counts: dict[str, int] = {}
    with zipfile.ZipFile(args.out, "w", compresslevel=6) as z:
        for d in REPO_DIRS + ([] if args.no_evidence else [EVIDENCE]):
            counts[d] = add_tree(z, ROOT / d, f"repo/{d}")
        for d in OLD_RAW:
            counts[f"saakshya/{d}"] = add_tree(z, OLD / d, f"saakshya/{d}")
        # the research build's code (tracked files only, at the approved snapshot)
        tar = subprocess.run(["git", "-C", str(OLD), "archive", OLD_COMMIT], check=True,
                             capture_output=True).stdout
        n = 0
        with tarfile.open(fileobj=io.BytesIO(tar)) as t:
            for m in t.getmembers():
                if m.isfile():
                    z.writestr(f"saakshya/{m.name}", t.extractfile(m).read(), zipfile.ZIP_DEFLATED)
                    n += 1
        counts[f"saakshya code @ {OLD_COMMIT}"] = n
        z.writestr("PACK-INFO.txt",
                   f"DRISHTI team data pack, built {now_ist():%Y-%m-%d %H:%M} IST\n"
                   "PRIVATE: real government records. Team Drive only. Never commit, never share publicly.\n"
                   "Install: python scripts/team/install_pack.py <this zip>\n\n"
                   + "".join(f"{k}: {v} files\n" for k, v in counts.items()))

    for k, v in counts.items():
        print(f"{v:>6} files  {k}")
    print(f"\n{args.out}  {args.out.stat().st_size / 1e6:.0f} MB")
    print("Upload it to the team's PRIVATE Google Drive folder and share with teammates only.")


if __name__ == "__main__":
    main()
