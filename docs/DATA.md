# Data

Where DRISHTI's data comes from, how it is processed, what we keep out of git, and the traps we hit.

---

## 1. Sources

| Source | What it gives | How we use it |
|---|---|---|
| **eSAKSHI public dashboard** (mplads.mospi.gov.in — the dataset named in SIH26102) | **2,09,993 works** (snapshot 26 May 2026): type, description, amount, place, MP, agency, recommendation/sanction/completion dates, status | the corpus every agent runs on |
| **eSAKSHI attachment endpoints** (public, no login) | the **certificates, bills and site photos** uploaded for completed works | the real-evidence agents (Document, Photo Forensics, Geo-Location, Contractor) |
| **MP-level fund files** (17th/18th Lok Sabha, Rajya Sabha) | allocated, recommended, sanctioned, spent per MP | Fund Flow (summed by term; MPs are never scored) |
| **Local Government Directory (LGD)** boundaries | official district and state outlines | maps; "is the photo inside the district" |
| **India Post PIN ↔ district file** | PIN code → district | PIN check on photo stamps |
| **MPLADS Guidelines 2016 / 2023** | clauses, limits, prohibited works (Annexure-II) | `apps/engine/drishti/reference/*.yaml`; every flag cites its clause |
| **CAG Report 31 of 2010-11** (MPLADS performance audit) | what auditors actually found, with scale | which problems the agents target; figures on the deck |

## 2. The real evidence

eSAKSHI's public dashboard serves the files behind each completed work through two endpoints:

```
POST /rest/PreLoginDashboardData/getAttachIdsbyFlag       {"json": {"FLAG": "3", "WORK_ID": <id>}}
     → file names + attachment ids
POST /rest/PreLoginCitizenWorkRcmdRest/getAttachmentById  {"id": "<attach id>"}
     → the file, base64
```

- **66% of completed works carry files.** In samples: most have one file; ~72% are PDFs (completion and
  utilisation certificates, bills, measurement books, handwritten Hindi notes), ~28% are photos.
- **Photos:** the phone's own GPS data is always stripped on upload, but GPS-camera apps (NoteCam, GPS Map
  Camera) **print the coordinates, date, time and PIN into the picture** — which DRISHTI reads.
- **Uttar Pradesh** uploads the portal's own typed Utilisation Certificate (sanction date, payments with dates
  and bank references, vendor name and vendor code) — readable for free by local OCR.

### The harvester — `data/harvest/esakshi_evidence.py`

Polite by design: **one request every 1.5 s**, each file fetched once and cached (a re-run resumes), a named
User-Agent, stops by itself after 10 consecutive failures. `data/evidence/manifest.jsonl` records the source
and fetch time of every file.

**Pilot sample used in the trial:** every completed work with evidence in Pratapgarh (UP) + 400 random
completed works nationally → **837 works, 905 files, 791 MB**, 64 minutes. Then **1,925 pages and photos**
read by local OCR (`data/trial/ocr_pages.py`, RapidOCR + PyMuPDF; photos: bottom 35% only, where stamps sit).

## 3. Processing pipeline

```
raw eSAKSHI export ─► build_corpus.py ─► build_stats.py ─► load_db.py ─► batch_assess.py ─► live app
(research build)      works.parquet      peer bands,        Postgres      every work
                      districts.parquet  durations,                       assessed
                                         road ₹/m curve
LGD outlines ─► boundaries.py ─► district_crosswalk.py ─► apps/web/public/geo/*.json (map)
```

| Script | Does |
|---|---|
| `data/build_corpus.py` | one row per work from the research build's cleaned table, joined back to the raw CSVs for house, term, constituency, MP, agency, category |
| `data/build_stats.py` | peer cost bands, completion-time percentiles, road price curve — **asserts** it reproduces the earlier measurements (e.g. 84.2% of works have a district peer group of 20+) before writing anything |
| `data/load_db.py` | loads everything in one transaction (a failed load leaves the old data in place) |
| `data/batch_assess.py` | assesses all works and stores the results (LOW works stored compact) |
| `data/seed_users.py` | creates the demo accounts; passwords printed once, stored nowhere |
| `data/boundaries.py` | simplified LGD outlines for the map |
| `data/district_crosswalk.py` | matches the two district-code systems (see traps) |
| `data/dry_run.py` | assesses without a database (quick checks) |
| `data/with_env.py` | runs any of the above against the hosted database without printing secrets |
| `data/trial/*.py` | the real-data trial of each agent; outputs in `data/trial/results/` |

**Rebuilding from scratch** needs the raw export held in the team's research build (`~/saakshya`, path set by
`DRISHTI_OLD_REPO`). It is not in this repo because of size and the personal data inside raw records. The
hosted database already holds the processed result.

## 4. Labels on every record

`works.source` is one of:
- **REAL** — from the eSAKSHI export or its attachments
- **SCENARIO** — a planted demo case, with its answer key
- **LIVE** — submitted on our site (field app, citizen form)

Real and planted data are never mixed silently.

## 5. What stays out of git

| Kept out | Why |
|---|---|
| `data/raw/`, `data/build/`, `data/cache/` | large; rebuilt by the scripts |
| `data/evidence/` | real government files with names, signatures, bank details |
| `data/trial/cache/` | OCR text of those files (names and account numbers) |
| `.env*`, `.demo-logins.txt`, `.vercel/` | secrets |

Committed trial results are passed through `data/trial/sanitize_results.py`: it masks phone and account numbers
and runs the site's own masker (`validation/pii.py`) over every text, so no results file shows a name the site
would hide (T056; `data/trial/pii_trial.py` measures the masker on the dashboard's 57,508 descriptions).

## 6. Traps we hit (so nobody hits them again)

1. **Two district-code systems.** The works' field called `district_lgd` actually holds the **Census-2011**
   district code; the map outlines carry the real **LGD** code. Joined by number, Pratapgarh's works were
   drawn on Pilibhit. Fixed: `district_crosswalk.py` matches all districts by state + name and the map joins
   on the works' code. **Never join the two by number.**
2. **Portal cycles look like behaviour.** Completion months and impossible dates follow the portal's calendar
   (bulk entry when eSAKSHI opened; a "March rush" that vanished next year). Always compare an office with
   the same period nationally, never with a flat average.
3. **eSAKSHI's "amount" is what was paid**, and equals the sum of the certificate's payments.
4. **The same form has several versions.** The older Utilisation Certificate has no sanction-date line.
5. **Combined files are normal.** One invoice for 18 villages attached to several works is not reuse; an
   exact copy matters only when the file names a single work or person.
6. **Image fingerprints don't work on certificates** — every form looks alike. Compare documents by text.
7. **Citizen ratings are empty:** 21,789 of 21,793 are zero.
8. **Private data in public records:** phone numbers in descriptions, bank account numbers on certificates —
   mask, never display. Names hide in road descriptions without any marker: "from <name> house to <name> house",
   "<NAME> K GHAR", "<name> na ghar", "<name> ke avas", "<name> ka makaan", "<name> S/O <name>" (T056, T092: 13,776 of
   57,508 descriptions carry something to mask).
