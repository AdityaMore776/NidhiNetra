# DRISHTI prototype — STATUS

**Read this first. It is the single source of truth for where the build is.**

**Plan changed 27 Sept 2026: the main architecture is now the NidhiNetra blueprint** ([`specs/2026-09-27-nidhinetra-blueprint.md`](specs/2026-09-27-nidhinetra-blueprint.md)): four engines → risk score → alerts, dashboards, Inspection Planner, field app → learning loop. The roadmap and v2 notes below are history / side track; the live task order is [`team/TASKS.md`](team/TASKS.md).

**Working as a team (from 27 Sept 2026):** tasks, claims and progress now live in the team system: [`AGENTS.md`](../AGENTS.md) (manual), [`team/TASKS.md`](team/TASKS.md) (plan), GitHub Issues (who), [`team/log/`](team/log/) (what happened). This file stays milestone-level: update it only when a milestone moves, and only the lines about your milestone.

## At a glance (26 Sept 2026)

| | |
|---|---|
| **Live** | https://drishti-lyart.vercel.app — all 2,09,993 real works assessed; review queue 276 (0.13%); Ministry / District / Field logins |
| **In the live engine** | Cost agent, Data Validation, Risk Fusion v1, role scoping, India map on LGD outlines |
| **Core engines, LIVE 30 Sept (merged, hosted DB reloaded; handoff: `team/log/2026-09-30-2322-*`)** | Guideline Compliance, Cost v2, Duplicate & Split, Delay (shown, not counted) + the 0–100 risk score with top-3 reasons in English and Hindi (T010–T050). Queue becomes 1,524 works (0.73%; 24 of 30 random ones worth checking). Stacked PRs #56 → #57 → #58 → #59 → #60 → T050; going live = merge in order **and** reload the hosted database (migrations 006 + 007, `load_db.py`, `batch_assess.py`). Checked on a full local copy: 313 MB. |
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

**5 Oct 2026: the website's work intelligence form reaches the four agents (T134).** `/work-form` shows twelve example
filings by made-up agencies in Jaunpur, each caught by one agent (one honest road passes all four): each agent says
flagged / clear / not checked with one line on why, and the flagged fields are outlined in the form. "Check this form"
runs the four agents on any filled form against the same example data (`POST /api/v1/work-form/check?demo=true`,
nothing stored), shown in plain words on the page's Data tab. Numbers in FINDINGS "T134". Going live needs nothing
new: the examples and the demo data ship with the web app and the engine.

**4 Oct 2026: the four agents are built (T121–T125, owner's pivot of 3 Oct; PR open).** Cost, Duplicate Work, Time &
Rules and Site Progress, a quarter of the weight each; Guideline Compliance, Fund Flow, Office Patterns, Paperwork and
Photo Evidence are retired (their code stays as libraries). Plan: `docs/plans/T120-four-agents.md`; numbers in
FINDINGS "T121–T125".
- **Cost** prices every confirmed line (SoR item, else 3+ other agencies' district rates), then judges the whole
  estimate: asked at 15%+ and Rs 50,000+ above the fair price. Synthetic forms: target met at a 10% honest spread with
  district rates (91.5% / 0.0%), missed with SoR rates (82.5%) and at a 15% spread (2.4–3.3% honest asked).
- **Time & Rules**: R01, R06, R13, R14, the late sanction as an office fact (never queues), and the comfort window from
  the form's estimated time to completion.
- **Site Progress v3**: monthly site videos filmed in the new capture page (`/capture`), sealed, read once by the video
  job (OpenCV, off the live engine), video deleted, blurred frames kept. End to end in a real browser on made-up scenes.
- **Dashboard's 40,935 works:** queue 439 → 217 (185 R14, 34 split pieces). Test countries: precision 0.70 → 1.00.
- **Going live:** merge, then apply migrations 013 + 014 (`data\with_env.py apply_migrations.py`), set
  `DRISHTI_CAPTURE_SECRET` and `SUPABASE_SERVICE_ROLE_KEY` on the engine, create a private `site-visits` bucket, and
  re-run `batch_assess.py`. The video job runs on a teammate's machine (`data/requirements-video.txt`).
- **Still to do:** the SoR files (T096), the field trial on real sites (T126, human-task), reading the new findings by
  eye once they fire, the Android app for mock-location checks.

**3 Oct 2026: simple and certain: one Cost check, one Duplicate check (T099 + T100, owner's pivot; PR open).**
- **Measured first** (`data/trial/simple_certain_trial.py`):
  - **Cost:** no price question is certain from a record. Of 15 works a record-only check would have questioned, 0
    were real (5 misread counts, 9 bigger items, 1 grey).
  - **Repeats:** words alone are right about 2 times in 3 at best.
- **Cost** is now the cost estimate form's check, in the core slot. A work with no form is not judged, and the old
  Cost Anomaly is retired. Forms are saved and attached (migration **013**, `POST/GET /api/v1/cost-forms`).
- **Duplicate Work** asks only:
  - by map pin (within 50 m of a sanctioned work of the same kind);
  - a declared rebuild of a work completed under 3 years ago;
  - one job cut into pieces each 96–100% of a limit (14 dashboard groups: 12 yes, 2 grey).

  Text look-alikes are notes for the agency to answer on the form.
- **The dashboard's 40,935 works:** queue 427 → 439. 11 left (a wait plus a bulk-order or old cost flag); 23 entered
  (strict split pieces). CRITICAL 36 → 8.
- **Going live:** merge, then apply migration 013 (`data\with_env.py apply_migrations.py`) and re-run
  `batch_assess.py`.
- Plan: `docs/plans/T099-T100-simple-and-certain.md`.

**3 Oct 2026: Cost Estimate engine built (T097; shown, not counted; PR open after #95).**
- **What it does:** it reads the agency's cost estimate form and asks only when certain: a confirmed quantity above
  what the size needs, or a price above the district's standard item **and** the MP's amount.
- **Measured** on 2026 UP works it never saw: 0 of 42 real works asked about; planted ×1.5 prices 42 of 42; size
  changes 0 of 204 answers.
- **Still needed:** the form screens (T094), the official rates (T096), then proof and switch-on (T098).

**3 Oct 2026: Cost v3 started (owner's pivot; PR open).** The implementing agency fills a full cost estimate form; the
Cost agent will compare it with the same kind and size of work in the same district, then with the MP's amount. Done:
the form's field list, checks and routes (T093), the UP reference from real works (T095). Next: the form screens (T094,
teammate), the engine (T097), the official rates (T096, human task: .gov.in is blocked in the cloud environment).
Plan: `docs/plans/T097-cost-agent-v3.md`; form: `docs/specs/2026-10-03-cost-estimate-form.md`.

**2 Oct 2026: T092 Visualization Engine built (PR open, after #92).** A public page, `/explain`, plays one work through
six animated, replayable steps (input, privacy, reading, seven checks, the score's arithmetic, the officer's result)
with seven built-in examples on the dashboard data and the judge's own example via `POST /api/v1/explain` (sign-in).
Every number is the real pipeline's (`drishti/explain.py`, tested equal). Numbers: FINDINGS "T092". Start from the
newest `docs/team/log/*-T092.md`.

**2 Oct 2026: T056 merged and LIVE (PR #89 `b1056b9`, PR #90 `f964f86`; no migration).** Foolproof and accuracy
pass: no malformed evidence or work row can stop the batch (`agents/evidence.py`, `records.py`); Fund Flow, the
certificate reader, Cost (several streets = a bundle) and Duplicate & Split (men's/women's twins, splits under
Rs 5 lakh said not asked) fixed from real flags read by eye. Certificate reader on the pilot: sanction date 69.4% →
69.4%, vendor code 97.7% → 97.9% (`results/paperwork_trial_t056.txt`). R06 read on the hosted data and counted
where it stands out (#91). **Hosted DB re-assessed after #89-#91: review queue 1,430 → 1,459 (0.69%)**, CRITICAL 82,
HIGH 1,377, MEDIUM 4,321 (`results/hosted_assess_t056.txt`). Masker: names before house/land/ghar and before S/O
now hidden, 9,312 → 13,776 of 57,508 descriptions, with the Hindi residence spellings "ke avas", "ka makaan" (`results/pii_trial.json`). Stored findings exist only for HIGH/CRITICAL works (migration 003), so count a finding from the
works table: R06 via `data/trial/r06_rows.py`. Start from `docs/team/log/2026-10-02-2220-adityamore776-T056.md`.

**2 Oct 2026: T055 + T510 merged and LIVE (PR #86, main `6efb61d`); migrations 011 + 012 applied in the Supabase SQL
editor; hosted DB re-assessed with fusion v3 (CRITICAL 83, HIGH 1,347, MEDIUM 5,112, LOW 203,451; review queue
1,430 = 0.68%, was 131; 430 s, 264 MB; `data/trial/results/hosted_assess_v3.txt`).** Planted test (T080) with v3:
fakes in the queue 4 → 11 of 50, MEDIUM+ 25 → 38, top 5% 39/50 (`data/trial/results/planted_test_v3.json`, PR #87). Not
yet measured on the full corpus: 30 random live queue works read by eye. Site Progress v2 is merged and
switched off. Start from `docs/team/log/2026-10-02-1352-adityamore776-T055.md` (handoff).

**2 Oct 2026, T055 (engine review, details).** A seeded test
country with planted problems measures recall (`apps/engine/drishti/evaluation/`, CI gate); new **Office Patterns**
engine; Guideline rule **R14** (built right after sanction) and R07 fixes; Duplicate & Split reads numbered
stretches and repairs; **risk fusion v3** (the chance a work is worth a look, from hit rates read by eye;
`DRISHTI_FUSION=v2` rolls back); one case = one queue row. Planted problems queued 4% → 16% on the test country;
eSAKSHI dashboard's 40,935 works: queue 47 → 427, 39/40 read worth checking. Write-up:
`docs/plans/T055-engine-review.md`.

**1 Oct 2026 night: T054 + T080 + T064 merged and LIVE; hosted DB re-assessed (CRITICAL 5, HIGH 126, MEDIUM
2,197; queue 131).** Start from `docs/team/log/2026-10-01-2352-adityamore776-T054.md` (handoff, three open owner
questions: HIGH cut-off, cost "far bigger", 45 vs 75 days). Guideline timing rules now score by how unusual the
wait is; planted-anomaly test 39/50 in the top 5%; new **Pre-sanction check** page.

**1 Oct 2026, T051 (PR #67): the four engines now work on ANY recommendation, not just the 2,09,993 they were
built on, and the 12 planned checkers are merged into 8** (`docs/AGENT-CATALOG.md`). Newest log entry in
`docs/team/log/` has the exact next step. Rebuild data after merging: `data/build_generic_words.py` (only if
the corpus changes), `.venv-trial` `data/build_price_model.py`, `data/build_evidence.py`,
then `load_db.py` → `batch_assess.py`.
**T053 (1 Oct 2026): only agents that find real problems.** Cost shows an explicit comfort zone and dropped the
flags that were almost never right; Delay's forecast, Site Progress and the separate Data Validation step were
removed; Paperwork and Photo Evidence keep only real findings; Odd Overall became Guideline rules R12/R13. Six
engines (`docs/AGENT-CATALOG.md`).

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
- A word added to `generic_words.txt` also hides every place name one letter away from it (the
  typo check): "motar" made the village "Motari" disappear and lost a planted split (2 Oct 2026). Add a
  word only when the labelled pairs (`data/trial/dup_split_rescore.py`) or the test country show a gain.
- Synthetic precision counts only planted problems as right: a made-up work that happens to be a real
  rule breach (a big sum with no place) is reported apart as `UNSCORED_*`, never as a false alarm.

## Live links

- Production: https://drishti-lyart.vercel.app
