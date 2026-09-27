# Run DRISHTI yourself

The live prototype is at **https://drishti-lyart.vercel.app**. This page is for running it on your own
machine, running the tests, and deploying.

## The quick way (teammates)

```powershell
python scripts/team/setup.py         # installs engine + web, unpacks the data pack from Downloads, runs tests
python scripts/team/setup.py --db    # builds the local database with the real corpus (~10 min, once)
python scripts/dev/start.py          # database + engine + web together: http://localhost:3000
```
The sections below are the same steps by hand.

## Prerequisites

- Python **3.12+**
- Node.js **24** (CI uses 24; 20+ should work)
- Git
- For real data: a PostgreSQL database (Supabase, or a local one)

## 1. Engine (Python API)

```bash
cd apps/engine
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
pip install -e . -r requirements-dev.txt

ruff check drishti tests        # lint
pytest -q                       # 141 tests
```

Run the API against a database with the data loaded:

```bash
# PowerShell
$env:DATABASE_URL = "postgresql://..."
$env:DRISHTI_AUTH = "dev"                         # lets the web app name its role locally
python -m uvicorn drishti.main:app --port 8000 --app-dir apps/engine
```

Interactive API docs: http://localhost:8000/api/v1/docs

## 2. Web (Next.js)

```bash
cd apps/web
npm ci
# PowerShell: $env:NEXT_PUBLIC_DEV_ROLE = "MINISTRY"   (or DISTRICT with NEXT_PUBLIC_DEV_DISTRICT)
npm run dev
```

Open **http://localhost:3000** (not 127.0.0.1 — Next.js dev blocks it). In dev mode the app skips login and
calls the engine with the role you set.

## 3. Load data into a database

**Teammates, the quick way:** install the private data pack ([`team/DATA-PACK.md`](team/DATA-PACK.md)), then
`apps\engine\.venv\Scripts\python.exe scripts\dev\local_db.py --load` starts a local Postgres, loads the
built data and assesses every work; it prints the `DATABASE_URL` for the engine. Later runs: drop `--load`.

The full pipeline, from the raw export:

```bash
python data/build_corpus.py      # needs the raw export (DRISHTI_OLD_REPO, see docs/DATA.md)
python data/build_stats.py       # asserts it reproduces the measured statistics
python data/load_db.py           # uses DATABASE_URL; session pooler (port 5432) for Supabase
python data/batch_assess.py
python data/seed_users.py --district <district code>   # hosted only: creates demo accounts
```

Against the hosted database, wrap each script so no secret is printed:
`python data/with_env.py load_db.py` (reads `.env.local`, uses the session pooler).

## 4. Environment variables

Names only — **never commit values**. See [`.env.example`](../.env.example).

| Variable | Used by | Meaning |
|---|---|---|
| `DATABASE_URL` | engine, data scripts | Postgres connection (falls back to `POSTGRES_URL`) |
| `POSTGRES_URL` / `POSTGRES_URL_NON_POOLING` | engine / `with_env.py` | set by the Vercel–Supabase integration: transaction pooler / session pooler |
| `SUPABASE_URL` | engine | where the engine fetches the token-signing keys |
| `SUPABASE_SERVICE_ROLE_KEY` | `seed_users.py` only | admin key for creating demo accounts — server-side only |
| `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY` | web | public login configuration |
| `DRISHTI_AUTH=dev` | engine | local dev mode (refused on Vercel) |
| `NEXT_PUBLIC_DEV_ROLE`, `NEXT_PUBLIC_DEV_DISTRICT` | web | the role/district used in dev mode |
| `DRISHTI_SNAPSHOT_DATE` | engine | "today" for real works (default `2026-05-26`, the export date) |
| `DRISHTI_OLD_REPO` | `build_corpus.py` | path to the research build holding the raw export |

## 5. The real-data trial

```bash
python -m venv .venv-trial      # trial needs extra libraries: opencv, rapidocr, pymupdf, lightgbm, shapely, scipy
python data/harvest/esakshi_evidence.py --district "PRATAPGARH" --state "Uttar Pradesh" --national 400
python data/trial/ocr_pages.py
python data/trial/cost_trial.py           # …and the other *_trial.py scripts
python data/trial/sanitize_results.py     # ALWAYS before committing results
```

The harvester is deliberately slow (1 request / 1.5 s). Please keep it that way.

## 6. Deploy

- Push to `main` → Vercel builds both services (`vercel.json`) and deploys production.
- Or manually: `npx vercel deploy --prod`.
- After a deploy, check: login → dashboard loads with the map → open a flagged work → agent cards show.

## 7. Troubleshooting

| Symptom | Fix |
|---|---|
| Map paints works on the wrong district | re-run `data/boundaries.py` **then** `data/district_crosswalk.py` |
| `invalid connection option "supa"` | use `config.database_url()` — it strips pooler hints libpq rejects |
| Map is blank in dev | `npm run dev` copies the MapLibre worker to `public/maplibre` (`scripts/copy-maplibre.mjs`) |
| `local_db.py`: "Timeout starting server", log says "sharing violation" | the database was not shut down cleanly (window closed instead of Ctrl+C). Stop leftovers with `pg_ctl stop -D data/cache/pg -m fast` (pg_ctl is under `apps/engine/.venv/Lib/site-packages/pgserver/pginstall/bin/`); if it still fails, delete `data/cache/pg` and re-run with `--load` |
| First load after deploy is slow | expected: cold start + aggregation over 2.1 lakh rows |
| Windows: "WinError 6 handle is invalid" in OCR | run OCR as single-process shards (`--shard i/n`) |
