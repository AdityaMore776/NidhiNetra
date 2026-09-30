# DRISHTI prototype — STATUS

**Read this first. It is the single source of truth for where the build is.**

**Plan changed 27 Sept 2026: the main architecture is now the NidhiNetra blueprint** ([`specs/2026-09-27-nidhinetra-blueprint.md`](specs/2026-09-27-nidhinetra-blueprint.md)): four engines → risk score → alerts, dashboards, Inspection Planner, field app → learning loop. The roadmap and v2 notes below are history / side track; the live task order is [`team/TASKS.md`](team/TASKS.md).

**Working as a team (from 27 Sept 2026):** tasks, claims and progress now live in the team system: [`AGENTS.md`](../AGENTS.md) (manual), [`team/TASKS.md`](team/TASKS.md) (plan), GitHub Issues (who), [`team/log/`](team/log/) (what happened). This file stays milestone-level: update it only when a milestone moves, and only the lines about your milestone.

## At a glance (26 Sept 2026)

| | |
|---|---|
| **Live** | https://drishti-lyart.vercel.app — all 2,09,993 real works assessed; review queue 276 (0.13%); Ministry / District / Field logins |
| **In the live engine** | Cost agent, Data Validation, Risk Fusion v1, role scoping, India map on LGD outlines |
| **Core engines, ready to go live (30 Sept)** | Guideline Compliance, Cost v2, Duplicate & Split, Delay (shown, not counted) + the 0–100 risk score with top-3 reasons in English and Hindi (T010–T050). Queue becomes 1,524 works (0.73%; 24 of 30 random ones worth checking). Stacked PRs #56 → #57 → #58 → #59 → #60 → T050; going live = merge in order **and** reload the hosted database (migrations 006 + 007, `load_db.py`, `batch_assess.py`). Checked on a full local copy: 313 MB. |
| **Proven on real data, being ported** | Eligibility v2, Split & Duplicate, Photo Forensics, Geo-Location, Document, Contractor Network, Delay (as track records), Fund Flow (facts) — see [AGENT-CATALOG.md](AGENT-CATALOG.md) |
| **Needs a decision** | paid AI key (capped) for Hindi/handwritten papers, Site Progress and plaque check |
| **Gated off** | Satellite (no large works with coordinates yet); Citizen Verification is demo-only (no real ratings) |

### Roadmap (v2 design §8, reordered by the trial)

| # | Build | State |
|---|---|---|
| M0 | Foundations + Cost agent, hosted | ✅ live 26 Sept |
| Trial | Every agent tried on real evidence for 837 works | ✅ done 26 Sept — [trial/FINDINGS.md](trial/FINDINGS.md) |
| M1 | Document + Contractor agents (free local reading of certificates) | next |
| M2 | Eligibility v2 in the engine; Split / bulk-order + funded-twice detector; matching by meaning | planned |
| M3 | Photo Forensics + Geo-Location (stamp reader, district, PIN, time) | planned |
| M4 | Delay track records + stuck works; Fund Flow sanction backlog; role dashboards | planned |
| M5 | Paid AI key → Hindi papers, Site Progress, plaques; field app; Citizen demo | needs decision |
| M6 | Fusion v2 (conflict rules), Inspection Planner, Ask DRISHTI, Satellite go/no-go, finale polish | planned |

The sections below are the working notes the team resumes from.

- **Current design (approved 2026-09-25, v2): `docs/specs/2026-09-25-drishti-v2-full-agents-design.md`**
  - 12 agents in 4 stages + 4 decision tools; real eSAKSHI evidence; every agent measured on real data.
  - Supersedes the 4-agent guardrail. Architecture/stack from the first design still apply:
    `docs/specs/2026-09-25-drishti-prototype-design.md`.
- Milestone task plans: `docs/plans/`
- Old research build (read-only source for ported code and raw data): `~/saakshya`
  (snapshot commit `abf2da4`)
- GitHub (private): https://github.com/AdityaMore776/drishti (the gh login is
  `AdityaMore776`; "Phoenix-techstuf" no longer resolves)

## >>> RESUME HERE <<<

**REAL-WORKS TRIAL DONE 2026-09-26: read `docs/trial/FINDINGS.md` first.** Every agent was
tested on the real export plus real eSAKSHI evidence for 837 completed works (all 435 in
Pratapgarh UP + 400 random; 905 files, 791 MB, in `data/evidence/`, gitignored; manifest
`data/evidence/manifest.jsonl`). Scripts `data/trial/*.py` (venv `.venv-trial`), results
`data/trial/results/` (run `sanitize_results.py` before committing - masks phone/account
numbers), local OCR cache `data/trial/cache/ocr/` (gitignored: holds names/accounts).
Headlines: Cost catches 63% of 5x mark-ups at 1.5% false alarms; Eligibility v2 56% precision (was 12%);
Document + Contractor agents work for FREE on UP's portal-generated certificates (real
sanction dates, payments, vendor codes); split/bulk patterns real; delay model weak
(AUC 0.71); GPS stamps readable (coords 10/10 by eye), phone EXIF GPS always stripped.
**Bug found + fixed + LIVE (commit a96b9ca):** works' `district_lgd` is really the CENSUS-2011 code; the map
outlines carry real LGD codes -> live map painted wrong districts. `data/district_crosswalk.py`
adds `code` to each outline; `IndiaMap.tsx` joins on it. Next build order: FINDINGS "What to
build next".

**M0 IS LIVE (2026-09-26): https://drishti-lyart.vercel.app** (Vercel project `drishti`,
team aditya-more-s-dreamscapeproject, auto-deploys on push to `main`; Vercel Services works on
Hobby). Database: Supabase via the Vercel marketplace (`drishti-db`, bom1 Mumbai, free plan);
env in `.env.local` (gitignored, pulled by the CLI). Bulk jobs: `data/with_env.py load_db.py`,
`data/with_env.py batch_assess.py` (session pooler; never prints secrets). Demo logins:
`.demo-logins.txt` (gitignored) - ministry@ / district@ (Pratapgarh UP, census code 173 =
LGD 174) / field@drishti.demo.
Verified live with Playwright: login, dashboard (2,09,993 works), district scoping (1,140 works).

Queue after porting T16/T18 (impossible dates judged by quarter; concentrated offices listed
once on the dashboard): **847 -> 276 works (0.13%)**, 253 on price; 22 offices listed.
Known follow-ups: first load after a deploy takes a few seconds (cold start + aggregation over
2.1 lakh rows - consider summary tables); district officers' map could zoom to their district.


**S1 SLIDES DONE 2026-09-25:** `docs/deck/DRISHTI_SIH26102_v2.pptx` (+ `.pdf`; copies in
`~/Downloads`). Six slides in the team's SIH template (title, proposed solution, technical
approach, feasibility, impact, research), rebuilt from measurements of their deck
(`docs/deck/spec/page*.json`) by `docs/deck/build.js`; render through real PowerPoint with
`docs/deck/render.ps1`. Facts learned doing it:
- CAG Report 31 of 2010-11 annexure TOTAL rows: Annex 7.2 plaques not erected = 4,918 works,
  31 DAs, Rs 100.20 cr; Annex 4.7 incomplete works = 12,006 works, 71 DAs, Rs 279.99 cr.
  **`~/saakshya/data/raw/cag/cag_findings.json` is unreliable** (column mix-ups, wrong totals) -
  read the TOTAL rows in `mplads_cag2010_annexures.txt` instead.
- The team's "Rs 9.16 Cr on 518 works" is not in that report; replaced, flagged to the user.
- 45 vs 75 days: the 2016 text says sanction in 75 days / reject in 45; secondary sources quote
  2023 wording "sanction/rejection ... within 45 days". The 2023 PDF could not be fetched
  (mplads.gov.in refused the connection) - ask the user to download it in a browser, then
  update `contracts`/validation clocks.
- Montserrat (title-slide labels) is not installed on this PC; the team's PowerPoint has it.

**2026-09-25: the user approved DRISHTI v2 (12 agents).** Order now (design §8):
1. **M0 hosting** - needs `! npx supabase login` (Vercel login DONE 2026-09-25).
2. **S1 slides** - the user will send "the other ppt we are working on" for the art style;
   build the slides from design §6 (pictorial, plain words, no file paths/test counts).
3. **M1** - Evidence Harvester (public eSAKSHI endpoints, see design §1/§4; pilot, 1.5 s
   between requests, free first test run of ~500 works) + Photo Forensics + Geo-Location.

**M0 detail - Foundations + Statistical agent (target 30 Sept 2026).**

**Built and tested locally (2026-09-25):** engine (123 tests, ruff clean), web
(typecheck, lint, build clean), full real corpus assessed on a local Postgres.
**Blocked on two user logins** before hosting:

1. ~~`! npx vercel login`~~ done 2026-09-25.
2. `! npx supabase login` — then create the project from the CLI
   (`supabase projects create drishti --region ap-south-1`), write the URL, anon key,
   service-role key and pooler URLs into `~/drishti/.env` (gitignored) WITHOUT printing
   them, then: `data/load_db.py` (session pooler 5432) → `data/batch_assess.py` →
   `data/seed_users.py --district <lgd>` → Vercel env vars → deploy → Playwright smoke.

Then Task 1's open question: does Vercel Services work on Hobby? Fallback is
`api/index.py` + Next rewrites (design §3).

### Run it locally

```
# terminal 1 - local Postgres with the real corpus (pgserver, no Docker)
apps\engine\.venv\Scripts\python.exe <script that calls pgserver.get_server("data/cache/pg")>
# terminal 2 - engine
$env:DATABASE_URL="<url>"; $env:DRISHTI_AUTH="dev"
apps\engine\.venv\Scripts\python.exe -m uvicorn drishti.main:app --port 8000 --app-dir apps/engine
# terminal 3 - web (use http://localhost:3000, NOT 127.0.0.1 - Next dev blocks it)
$env:NEXT_PUBLIC_DEV_ROLE="MINISTRY"; npm run dev --prefix apps/web
```

Rebuild data: `data/build_corpus.py` → `data/build_stats.py` (asserts AD-106 figures)
→ `data/load_db.py` → `data/batch_assess.py`. `data/dry_run.py` assesses without a DB.
`data/boundaries.py` rebuilds the LGD map outlines.

### Measured on real data (2026-09-25) — say these plainly

- 209,993 works; statistics reproduce AD-106 exactly (84.2% have a district cohort
  of 20+; 1.20% sit 3+ spreads above peers; ROAD_CC curve n=4065, slope 0.6309).
- **847 works (0.40%) need review, 0 HIGH.** Only one of four agents exists, so every
  work is "limited evidence".
- The first ranking was bulk light orders ("217 DIFFRENT PLACES"): bulk patterns
  widened; countable items (lights, borewells) now say a high amount may be many units
  and are read at confidence 0.6. The top of the list is now mis-categorised big
  projects (a skill hub filed as a community hall, a lift irrigation scheme as a pond)
  and undescribed sanctions ("Letter as per attached").
- Prohibited-works keywords: ~17,000 raw hits (temples/schools as landmarks), ~640 as
  the object of the work, mostly still legitimate → INFO note, weight 0.10.
- Database: 489 MB if every work keeps full detail → LOW works stored compact and
  rebuilt when opened → 193 MB.
- Not yet checked: MP annual total vs Rs 5 crore entitlement (needs carry-over rules).

## Milestones

See the roadmap under "At a glance" above (the original 4-agent milestone list was superseded by v2).

## Guardrails (from the user — never break)

- ~~Exactly four agents, no satellite~~ - superseded 2026-09-25 by the approved v2 design:
  12 agents, each only if proven; satellite only for big works and only after a go/no-go.
- Free tiers only for now; paid Gemini is a switch, not a default.
- `main` is always the demoable live link; host at every milestone.
- The user is non-technical: report in plain words, outcome first.

## Traps already hit

- Shell heredocs / Python string edits turned `\b` into a backspace byte in a regex.
  Write regex files with the Write tool. (Hit AGAIN 2026-09-26 via a Bash heredoc that ran
  Python to patch a file - never patch regex code through Bash; use Edit/Write only.)
- `district_lgd` in works/cohorts/PIN files is the Census-2011 code, NOT LGD. Never join it
  to the map outlines' `lgd` by number - use `data/build/district_crosswalk.parquet`.
- Windows: two ProcessPoolExecutors started from background shells died with
  "WinError 6 handle is invalid"; run extra OCR as single-process shards (`--shard i/n`).
- pandas NaN reached the engine as a truthy float; clean records via `data/common.py`.
- MapLibre 6 needs its worker served from `public/maplibre` (`scripts/copy-maplibre.mjs`).
- Next.js 16: middleware is now `proxy.ts`; read `apps/web/node_modules/next/dist/docs/`.

## Live links

- Production: https://drishti-lyart.vercel.app
