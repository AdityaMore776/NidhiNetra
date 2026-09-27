# The private team data pack

The code is public on GitHub; **the data is not**. Real eSAKSHI records and the certificates behind them carry
names, signatures, phone numbers and bank details, so they travel as one zip in the team's **private Google
Drive folder**, shared by the owner with teammates only.

## Install (teammates)

1. Download `DRISHTI-team-pack.zip` from the team Drive folder (link from the owner).
2. From the repo root:
   ```powershell
   python scripts/team/install_pack.py "$HOME\Downloads\DRISHTI-team-pack.zip"
   ```
   It never overwrites files you already have (add `--force` to refresh from a newer pack).
3. Optional, to run the app locally with the real corpus (after the engine setup in [`docs/SETUP.md`](../SETUP.md)):
   ```powershell
   apps\engine\.venv\Scripts\python.exe scripts\dev\local_db.py --load
   ```

## What's inside, and which tasks need it

| In the pack | Lands in | Needed for |
|---|---|---|
| `data/build/*.parquet`: the 2,09,993 works, peer cost bands, durations, district crosswalk | repo `data/build/` | running the app locally, every checker task, the trial scripts |
| `data/evidence/`: 905 real certificates and photos for 837 works + `manifest.jsonl` | repo `data/evidence/` | Document, Contractor, Photo, Geo tasks (T101–T104, T301–T304) |
| `data/trial/cache/`: local OCR text of that evidence | repo `data/trial/cache/` | same; saves an hour of OCR |
| `data/raw/MPLADS_real.csv`, `inrolls/` (MP fund files, raw work lists) | `~/saakshya/data/raw/` | rebuilding the corpus, Fund Flow (T402), the harvester |
| `data/raw/lgd/` (PIN ↔ district file, LGD lists) | `~/saakshya/data/raw/lgd/` | Geo PIN check (T304) |
| `data/raw/guidelines/`, `data/raw/cag/` | `~/saakshya/data/raw/` | clause checks, CAG figures for the deck |
| the old research build's **code** (snapshot `abf2da4`) | `~/saakshya/` | tasks that port code from it (duplicates, hashing, geo, fusion calibration) |

`~/saakshya` is the old research version of DRISHTI (it was called SAAKSHYA before). Several scripts look
for raw data there. Put it elsewhere with `$env:DRISHTI_OLD_REPO = "D:\somewhere"`.

## Rules

- **Never commit** anything from the pack. All its folders are in `.gitignore`, and CI rejects them anyway.
- **Never upload** it anywhere else (no public links, no other clouds, no pasting into chat tools).
- **Never quote** a person's name, phone or account number from it in code, tests, logs or screenshots.
  Refer to works by work ID. Test fixtures use made-up text with the same layout.
- Delete it from your machine when the project ends.

## For the owner: building and updating the pack

```powershell
python scripts/team/make_pack.py "$HOME\Documents\DRISHTI-team-pack.zip"            # full, ~1 GB
python scripts/team/make_pack.py "$HOME\Documents\DRISHTI-team-pack-small.zip" --no-evidence   # ~300 MB
```

Upload to the private Drive folder, share it with each teammate's email (Viewer), and post "pack updated,
re-run install_pack.py --force" on the relevant issue. Rebuild the pack after new harvests (T003) or a
corpus rebuild.
