# DRISHTI prototype — STATUS

**Read this first. It is the single source of truth for where the build is.**

- **Current design (approved 2026-09-25, v2): `docs/specs/2026-09-25-drishti-v2-full-agents-design.md`**
  - 12 agents in 4 stages + 4 decision tools; real eSAKSHI evidence; head-to-head vs rival methods.
  - Supersedes the 4-agent guardrail. Architecture/stack from the first design still apply:
    `docs/specs/2026-09-25-drishti-prototype-design.md`.
- Milestone task plans: `docs/plans/`
- Old research build (read-only source for ported code and raw data): `~/saakshya`
  (snapshot commit `abf2da4`)
- GitHub (private): https://github.com/AdityaMore776/drishti (the gh login is
  `AdityaMore776`; "Phoenix-techstuf" no longer resolves)

## >>> RESUME HERE <<<

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

| | Target | State |
|---|---|---|
| M0 Foundations + Statistical agent | 30 Sept | built locally; hosting blocked on logins |
| M1 Duplicate Project agent | ~7 Oct | not started |
| M2 Image Reuse agent | ~17 Oct | not started |
| M3 Site Progress agent (GPS) | ~31 Oct | not started |
| M4 Full loop (fusion, review, decisions) | ~15 Nov | not started |
| M5 Finale polish | Nov–Dec | not started |

## Guardrails (from the user — never break)

- Exactly the deck's pipeline and four agents. No new agents. No satellite anything.
- GPS/location validation lives inside Site Progress and Image Reuse.
- Free tiers only for now; paid Gemini is a switch, not a default.
- `main` is always the demoable live link; host at every milestone.
- The user is non-technical: report in plain words, outcome first.

## Traps already hit

- Shell heredocs / Python string edits turned `\b` into a backspace byte in a regex.
  Write regex files with the Write tool.
- pandas NaN reached the engine as a truthy float; clean records via `data/common.py`.
- MapLibre 6 needs its worker served from `public/maplibre` (`scripts/copy-maplibre.mjs`).
- Next.js 16: middleware is now `proxy.ts`; read `apps/web/node_modules/next/dist/docs/`.

## Live links

- Production: (not deployed yet)
