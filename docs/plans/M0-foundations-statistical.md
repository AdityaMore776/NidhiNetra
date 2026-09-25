# M0 — Foundations + Statistical Agent: Implementation Plan

> **For agentic workers:** execute inline with superpowers:executing-plans (the user prefers inline
> over subagents). TDD for every engine module. Steps use `- [ ]` checkboxes; tick them as you go.
>
> **Deviation from the writing-plans default, on purpose:** to save tokens (a standing user
> preference), steps name the exact files, the exact behaviour each test asserts, and the exact
> commands. Code is written once, during execution, rather than twice. Every constant a test
> asserts is given here.

**Goal:** a password-protected live site that holds all ~2.1 lakh real MPLADS works, runs them
through Data Validation, the Statistical agent (04) and Fusion v1, and shows the dashboard, works
search, the work page with the deck's cost card, the review queue and a How-it-works page. Agents
01–03 show as "in development".

**Architecture:** one Vercel project with two Services: `apps/web` (Next.js) at `/` and
`apps/engine` (FastAPI) at `/api/v1/*`. Supabase (Mumbai) provides Postgres and Auth. The heavy
statistics are computed offline in `data/` and loaded, and the engine reads precomputed cohort
tables at request time.

**Tech stack:** Python 3.12, FastAPI, psycopg 3, numpy, PyYAML, PyJWT; pandas and duckdb
(offline only); pgserver (tests); Next.js 16, TypeScript, Tailwind v4, shadcn/ui, MapLibre GL,
Recharts, @supabase/ssr.

**Sources in the old build (`~/saakshya`, commit abf2da4):**
- corpus: `data/db/drishti_real.duckdb` (table `work`, 209,993 rows; `district`, 752 rows)
- raw CSVs (house, constituency, MP name): `data/raw/inrolls/works_{ls17,ls18,rs}.csv`
- cost constants and regexes: `docs/visual/analyse_costs.py`
- prohibited list: `contracts/prohibited_works.yaml`; clauses: `contracts/guidelines_clauses.yaml`
- taxonomy: `contracts/work_types.yaml`, `contracts/work_categories.yaml`
- impossible-timeline weighting: `core/rules/lifecycle.py`; era: `core/era.py`

---

## File map

```
vercel.json                                  services + rewrites + cron
apps/engine/pyproject.toml                   runtime deps (fastapi, psycopg[binary], numpy, pyyaml, pyjwt[crypto], httpx)
apps/engine/requirements-dev.txt             pytest, pgserver, ruff
apps/engine/drishti/main.py                  FastAPI app, routers mounted at /api/v1
apps/engine/drishti/config.py                env settings (DATABASE_URL, SUPABASE_URL, SNAPSHOT_DATE)
apps/engine/drishti/db.py                    connection helper (autocommit off, prepare_threshold=None for pooler)
apps/engine/drishti/auth.py                  Supabase JWT verification (JWKS), role lookup from profiles
apps/engine/drishti/migrations/*.sql         schema; applied by drishti/migrate.py
apps/engine/drishti/migrate.py               apply migrations in order, record in schema_migrations
apps/engine/drishti/agents/contract.py       AgentResult, Finding, Status, banned-word check
apps/engine/drishti/agents/statistical/text.py      reads_as_bundle, stated_length (ported regexes)
apps/engine/drishti/agents/statistical/band.py      Band dataclass, z-score, verdict thresholds
apps/engine/drishti/agents/statistical/cohort.py    back-off lookup over cohort_stats
apps/engine/drishti/agents/statistical/unit_rate.py road length curve + published anchor
apps/engine/drishti/agents/statistical/timeline.py  delay vs p98 duration
apps/engine/drishti/agents/statistical/agent.py     assess(work, stats) -> AgentResult
apps/engine/drishti/validation/checks.py     validate(work) -> list[Issue]
apps/engine/drishti/validation/prohibited.py prohibited-works matcher (enforced items only)
apps/engine/drishti/reference/*.yaml         copied taxonomy / prohibited / clauses
apps/engine/drishti/fusion/fuse.py           fuse(results, validation) -> Fused (score, band, parts)
apps/engine/drishti/pipeline/orchestrator.py assess_work(): validation + 4 agent slots + fusion
apps/engine/drishti/api/{health,dashboard,works,queue}.py
apps/engine/tests/...                        mirrors the modules above; conftest starts pgserver
data/build_corpus.py                         duckdb + raw CSV -> data/build/works.parquet, districts.parquet
data/build_stats.py                          -> cohort_stats, duration_stats, unit_rate_models parquet
data/load_db.py                              parquet -> Postgres (COPY), then ANALYZE
data/batch_assess.py                         run orchestrator over every work, write summaries
data/boundaries.py                           LGD district polygons -> apps/web/public/geo/districts.json
apps/web/...                                 Next.js app (Tasks 12–16)
.github/workflows/ci.yml                     engine pytest + web typecheck/lint/build
```

---

### Task 1: Infrastructure spike (do this first; it decides the hosting shape)

- [ ] Create `apps/engine` venv with `py -3.12 -m venv .venv`, then install `pgserver`, and confirm
      `pgserver.get_server(tmpdir)` starts on Windows and `CREATE EXTENSION vector` works. If
      pgserver fails, fall back to `pixeltable-pgserver`. Record which one worked in STATUS.
- [ ] Minimal `apps/engine/drishti/main.py` (`GET /api/v1/health` → `{"ok": true}`) and minimal
      Next.js app (`npx create-next-app@latest apps/web --ts --tailwind --app --eslint
      --src-dir --no-turbopack --use-npm` or the current equivalent flags).
- [ ] `vercel.json` with `services` (web root `apps/web`; engine root `apps/engine`, entrypoint
      `drishti.main:app`) and rewrites `/api/v1/(.*)` → engine, `/(.*)` → web.
- [ ] Create the private GitHub repo (`gh repo create Phoenix-techstuf/drishti --private
      --source . --push`) and a Vercel project linked to it. Deploy a preview. Verify
      `/api/v1/health` and `/` both answer on the preview URL.
- [ ] **If Services is refused on Hobby:** use the fallback, which is FastAPI at
      `apps/web/api/index.py` with Next.js rewrites. Record the outcome in STATUS.
- [ ] Commit: "Hosting spike: web and engine answer on one Vercel URL".

### Task 2: Supabase project and schema

- [ ] **User action:** create a free Supabase project `drishti` in `ap-south-1` (or via the Vercel
      Marketplace integration). Put `DATABASE_URL` (transaction pooler, port 6543),
      `SUPABASE_URL` and `SUPABASE_ANON_KEY` in Vercel env and a local `.env`, never in git.
- [ ] Migration `001_core.sql`:
      - `works` (work_id PK text, source text check in ('REAL','SCENARIO','LIVE'), house,
        term, state_lgd, state_name, district_lgd, district_name, constituency, mp_name,
        agency_name, fy, work_type_code, category, description, amount numeric,
        recommended_date, completed_date, status, quantity, quantity_unit,
        is_outside_constituency bool)
      - `districts`
      - `cohort_stats` (level, work_type_code, key, n, p10, p50, p90, sd)
      - `duration_stats` (work_type_code, n, p50, p90, p98)
      - `unit_rate_models`
      - `assessments` (work_id PK, assessed_at, score, band, parts jsonb, validation jsonb,
        stat_result jsonb, versions jsonb)
      - `profiles` (user_id uuid PK, role, district_lgd)
      - `schema_migrations`
      - RLS enabled on every table, with no policies.
- [ ] Test `tests/test_migrate.py`: on a fresh pgserver DB, `migrate.apply()` creates every table
      and running it twice is a no-op. The row count in `schema_migrations` equals the number of
      files.
- [ ] Implement `drishti/migrate.py` and `drishti/db.py`. Run the tests, then commit.

### Task 3: Corpus build (offline)

- [ ] `data/build_corpus.py` reads `work` + `district` from the old DuckDB (read-only). It joins
      house / constituency / MP name / state from the raw CSVs on the ACTIVITY_NAME reference
      (`WS/<member>/<fy>/<serial>` = old `work_id` minus the `ESK-` prefix). It writes
      `data/build/works.parquet` with the `works` columns and `source='REAL'`. The amount is
      `estimated_cost` (99.5% populated; identical to sanctioned where both exist).
- [ ] Assertions inside the script (fail loudly): row count == 209,993; status counts
      RECOMMENDED 28,433 / SANCTIONED 94,662 / COMPLETED 86,898; work_type_code null == 6,658;
      and the share of works that got a constituency from the join is printed and asserted > 95%.
- [ ] Commit.

### Task 4: Statistics build (offline)

- [ ] `data/build_stats.py`, reusing the ported constants: MIN_COHORT = 20, SHRINK_K = 12,
      P10_P90_SD = 2.563, SD_FLOOR = 0.10.
      - cohort_stats over log10(amount>0) at three levels: `type_district`, `type_state`, `type`.
        `sd = (n*sd_raw + K*sd_type)/(n+K)`, floor 0.10.
      - duration_stats: days recommended→completed per work type, over COMPLETED works with both
        dates and a positive duration.
      - unit_rate_models: ROAD_CC log-log fit on the stated length (10–10,000 m), using the ported
        `LENGTH` regex. Expect n = 4,065, slope ≈ 0.631, intercept ≈ 4.538, resid_sd ≈ 0.277
        (assert within ±0.01 of the old measurement). Store the anchor 4,000–6,500 ₹/m.
- [ ] Assertion: the share of works with a `type_district` cohort n ≥ 20 is ≈ 84%, and the
      z ≥ 3 above-band share after the bundle gate is ≈ 1.2% (old AD-106 figures). If the numbers
      drift by more than 0.5 points, stop and investigate before loading.
- [ ] Commit.

### Task 5: Agent contract

- [ ] Tests `tests/agents/test_contract.py`:
      - `AgentResult` requires status ∈ {ASSESSED, NOT_APPLICABLE, NOT_ASSESSABLE, NOT_BUILT, ERROR}
      - risk and confidence are clamped to [0, 1]
      - `headline` containing any banned word (fraud, fraudulent, corrupt, corruption, guilty,
        criminal, embezzle, stolen, theft, bribe, scam, culprit, accused) raises ValueError
      - `to_json()` round-trips
- [ ] Implement `agents/contract.py` (dataclasses: `Finding(code, text, hard, risk, evidence:
      dict)`, `AgentResult(agent, status, verdict, risk, confidence, hard, headline, findings,
      limitations, version, duration_ms)`). Commit.

### Task 6: Statistical agent: pure parts

- [ ] `tests/agents/statistical/test_text.py`:
      - `reads_as_bundle`: "Installation of 60 Highmast lights" → True; "Supply and installation
        of 981 solar street lights" → True; "at different places" → True; "Construction of CC
        road in village Bijdih" → False; "Construction of 1 community hall" → False.
      - `stated_length`: "CC road 450 mtr" → 450; "road 5 mt width" → NaN (below 10);
        "20,000 mtr" → NaN.
- [ ] `tests/agents/statistical/test_band.py`:
      - A cohort with p10 = 5.0, p50 = 5.3, p90 = 5.6, n = 100, sd_type = 0.3 gives
        sd = (100*0.2341+12*0.3)/112 ≈ 0.2411.
      - Amount 10^6.1 → z ≈ 3.32 → COST_ABOVE_PEERS.
      - 10^4.5 → z ≈ -3.32 → COST_BELOW_PEERS.
      - 10^5.3 → COST_TYPICAL.
      - Outside the band + bundle → BUNDLED_SANCTION.
      - Risk mapping (soft, capped at 0.45): z 3 → 0.30, 4 → 0.40, ≥5 → 0.45.
- [ ] `tests/agents/statistical/test_unit_rate.py`: for the ROAD_CC model, 1,000 m at the fitted
      price → residual z 0. At 3× the fitted price → z ≈ log10(3)/0.2772 ≈ 1.72, which is not
      flagged. At 8× → z ≈ 3.26 → UNIT_RATE_ABOVE. The per-metre figure is reported against the
      4,000–6,500 anchor.
- [ ] `tests/agents/statistical/test_timeline.py`: SANCTIONED, 900 days since recommendation,
      type p98 = 800 → DELAYED (soft, 0.20). COMPLETED works are never DELAYED. A missing
      recommended_date → not assessed.
- [ ] Implement `text.py`, `band.py`, `unit_rate.py`, `timeline.py`. Run the tests, then commit.

### Task 7: Statistical agent: cohort back-off and `assess`

- [ ] `tests/agents/statistical/test_cohort.py` (pgserver, seeded rows):
      - Uses `type_district` when n ≥ 20; falls back to `type_state`, then `type`.
      - NOT_ASSESSABLE when no level reaches 20, or the amount is missing/zero, or the work type
        is missing.
      - The result names the level used ("works of the same type in this district").
- [ ] `tests/agents/statistical/test_agent.py`:
      - `assess()` returns an ASSESSED result with the deck's comparison-table evidence: metric,
        this work, typical range (10^p10–10^p90 in ₹), deviation % vs the median.
      - Headline in plain words, e.g. "Costs 6.9x the typical amount for CC roads in Anand".
      - The Money-ahead-of-site facet returns NOT_APPLICABLE with the text "starts once Site
        Progress is built".
- [ ] Implement `cohort.py`, `agent.py`. Commit.

### Task 8: Data Validation v1

- [ ] `tests/validation/test_checks.py`:
      - completed_date before recommended_date → WARN `IMPOSSIBLE_TIMELINE` with the gap in days.
        If recommended in 2023-Q3/Q4 (the eSAKSHI migration window, `core/era.py` boundary
        2023-04-01), the message adds "likely a data-migration entry".
      - completed_date after SNAPSHOT_DATE → WARN `FUTURE_DATE`.
      - amount missing/≤0 → WARN `MISSING_AMOUNT`.
      - work type missing → INFO `MISSING_WORK_TYPE`.
      - A prohibited keyword on an **enforced** item → WARN `PROHIBITED_CATEGORY` citing
        "MPLADS Guidelines (June 2016), Annexure-II item N".
      - Items with `superseded_likely: true` never fire.
- [ ] Implement `validation/checks.py`, `validation/prohibited.py`; copy the YAMLs into
      `drishti/reference/`. Commit.

### Task 9: Fusion v1 and orchestrator

- [ ] `tests/fusion/test_fuse.py`:
      - `w = risk*confidence*reliability`, soft capped at 0.45.
      - score = max w + 0.45 × sum(other w), capped at 1.
      - The parts sum exactly to the score (to 1e-9).
      - Band: HIGH ≥ 0.60 or a hard finding with risk ≥ 0.60 and confidence ≥ 0.70; MEDIUM ≥ 0.30;
        otherwise LOW.
      - "limited evidence" when ≥ 2 agents are not ASSESSED.
      - Validation WARNs contribute as one soft input capped at 0.30.
      - Initial reliability for the statistical agent is 0.6, until evaluation replaces it.
- [ ] `tests/pipeline/test_orchestrator.py`: `assess_work(work, ctx)` returns validation + four
      agent results (01–03 `NOT_BUILT`) + fused. It never raises: an agent exception becomes
      status ERROR with a limitation.
- [ ] Implement. Commit.

### Task 10: Load + batch assess (offline, against Supabase)

- [ ] `data/load_db.py`: apply migrations, then COPY the parquet files into
      works/districts/cohort_stats/duration_stats/unit_rate_models. Print the database size
      (`pg_database_size`). **Stop if > 400 MB.**
- [ ] `data/batch_assess.py`: run the orchestrator over every work (numpy-vectorised where it
      helps) and upsert `assessments`. Print band counts and the top-10 works by score. Read the
      top-10 by eye before trusting them (the AD-103/106 lesson: the first ranking shows filing
      conventions, not problems).
- [ ] Test `tests/test_batch_small.py` on pgserver with 300 synthetic works: every work gets
      exactly one assessment row, and re-running is idempotent.
- [ ] Commit.

### Task 11: Engine API

- [ ] Tests with FastAPI TestClient + pgserver:
      - `GET /api/v1/health` → 200 without auth.
      - Every other route → 401 without a valid token.
      - `GET /api/v1/dashboard/summary` → works, total ₹, band counts, per-agent status.
      - `GET /api/v1/dashboard/districts` → per-district counts and share HIGH+MEDIUM.
      - `GET /api/v1/works?q=&district=&type=&band=&page=` → paginated (25).
      - `GET /api/v1/works/{id}` → record + assessment (recomputed on demand if missing).
      - `GET /api/v1/queue?band=&district=` → MEDIUM/HIGH sorted by priority = score ×
        (1 + log10(amount/1e5) clipped 0..3).
      - `GET /api/v1/health/keepalive` → touches the DB.
      - Role scoping: a DISTRICT role only sees its district.
- [ ] Implement `auth.py` (JWKS from `SUPABASE_URL/auth/v1/.well-known/jwks.json`, cached; a
      test key pair is used in tests) and the routers. Commit.

### Task 12: Web foundation and auth

- [ ] shadcn/ui init; Inter font; deck palette as CSS tokens (site #70C6AB, reuse #9469E5,
      duplicate #EF558A, statistical #F48137, fusion #2FB0AE, inputs #2E9ADF).
- [ ] `@supabase/ssr` login page (email + password) and middleware that redirects to `/login`
      when signed out. An `apiFetch()` helper sends the access token to `/api/v1`.
- [ ] Seed three demo users via the Supabase admin API in `data/seed_users.py` (ministry, district
      officer of a chosen district, field officer). Passwords are generated and printed once, and
      stored only in the user's local `.env` notes, never in git.
- [ ] Commit.

### Task 13: Dashboard

- [ ] KPI tiles: works monitored, ₹ monitored, HIGH/MEDIUM/LOW counts.
- [ ] India district map (MapLibre, plain background, LGD 2024 district polygons simplified to
      `public/geo/districts.json` by `data/boundaries.py`), coloured by the share of works needing
      review.
- [ ] Four agent cards (04 live with its alert count; 01–03 "in development").
- [ ] Top-10 priority list.
- [ ] Panel "What the real eSAKSHI data can and cannot tell us" (no coordinates, quantities or
      photos in the export).
- [ ] Commit.

### Task 14: Works list + work page

- [ ] Works list: search box, district/type/band filters, paginated table with source badges.
- [ ] Work page: record header, band badge + score, fusion bars, validation issues, the four agent
      cards. The Statistical card mirrors the deck: comparison table (metric / this work / typical
      range / deviation), a cohort band strip chart (Recharts), plain-words headline, "compared
      with N works of the same type in <district>", and limitations.
- [ ] Commit.

### Task 15: Queue + How it works

- [ ] Queue: MEDIUM/HIGH, priority-sorted, band/district filters. Links to the work page.
- [ ] How it works: the deck's six-step pipeline with each agent's build status and one-line
      question.
- [ ] Commit.

### Task 16: CI, keep-alive, deploy, verify

- [ ] `.github/workflows/ci.yml`: engine ruff + pytest (pgserver on ubuntu), web lint + typecheck
      + build.
- [ ] Add the `crons` entry in vercel.json: daily `/api/v1/health/keepalive`.
- [ ] Merge to `main` → production. Playwright MCP smoke on the production URL: login → dashboard
      shows 209,993 works → open a HIGH work → the Statistical card renders the comparison table →
      the queue lists it.
- [ ] Update `docs/STATUS.md` (RESUME HERE → M1) and memory. Send the user a plain-words update
      with the link, the demo logins (told privately) and what to try.

## Done when

- The production URL is behind login and shows all real works, with a working dashboard, search,
  work page, queue and How-it-works.
- The Statistical agent's flag rate on real works matches the measured ≈1.2% (or the difference
  is explained in STATUS).
- Engine tests are green in CI, and the database size is < 400 MB.
