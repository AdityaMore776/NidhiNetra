"""Unpack the private team data pack into the right places. Safe to re-run; never overwrites your files.

    python scripts/team/install_pack.py "C:\\Users\\you\\Downloads\\DRISHTI-team-pack.zip"

Puts:
  repo/...      -> this repo (data/build, data/evidence, data/trial/cache; all gitignored)
  saakshya/...  -> %USERPROFILE%\\saakshya (the old research build: raw data + code to port from),
                   or wherever DRISHTI_OLD_REPO points
Details: docs/team/DATA-PACK.md.
"""

from __future__ import annotations

import argparse
import os
import zipfile
from pathlib import Path

from _common import ROOT


def main() -> None:
    ap = argparse.ArgumentParser(description="install the private team data pack")
    ap.add_argument("zip", type=Path)
    ap.add_argument("--force", action="store_true", help="overwrite files that already exist")
    args = ap.parse_args()

    old = Path(os.environ.get("DRISHTI_OLD_REPO", Path.home() / "saakshya"))
    if (old / ".git").exists() and not args.force:
        raise SystemExit(f"{old} is a git repository (the owner's research build?). Refusing to write "
                         "into it; set DRISHTI_OLD_REPO to another folder.")
    targets = {"repo/": ROOT, "saakshya/": old}
    written = skipped = 0
    with zipfile.ZipFile(args.zip) as z:
        for info in z.infolist():
            if info.is_dir():
                continue
            prefix = next((p for p in targets if info.filename.startswith(p)), None)
            if prefix is None:
                continue
            rel = info.filename[len(prefix):]
            dest = (targets[prefix] / rel).resolve()
            if targets[prefix].resolve() not in dest.parents:   # no "../" tricks
                continue
            if dest.exists() and not args.force:
                skipped += 1
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            with z.open(info) as src, open(dest, "wb") as out:
                out.write(src.read())
            written += 1
        info_txt = z.read("PACK-INFO.txt").decode("utf-8") if "PACK-INFO.txt" in z.namelist() else ""

    print(info_txt)
    print(f"written {written} file(s), kept {skipped} existing file(s)")
    print(f"repo data  -> {ROOT / 'data'}")
    print(f"old build  -> {old}")
    print("\nThese files are PRIVATE and gitignored. Never commit them, never upload them anywhere public.")


if __name__ == "__main__":
    main()
