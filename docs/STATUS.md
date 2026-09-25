# DRISHTI prototype — STATUS

**Read this first. It is the single source of truth for where the build is.**

- Design (approved 2026-09-25): `docs/specs/2026-09-25-drishti-prototype-design.md`
- Milestone task plans: `docs/plans/`
- Old research build (read-only source for ported code and raw data): `~/saakshya`
  (snapshot commit `abf2da4`)
- GitHub (private): https://github.com/AdityaMore776/drishti (the gh login is
  `AdityaMore776`; "Phoenix-techstuf" no longer resolves)

## >>> RESUME HERE <<<

**Current milestone: M0 — Foundations + Statistical agent (target 30 Sept 2026).**

**Built and tested locally (2026-09-25):** engine (123 tests, ruff clean), web
(typecheck, lint, build clean), full real corpus assessed on a local Postgres.
**Blocked on two user logins** before hosting:

1. `! npx vercel login` — the Vercel CLI on this machine is logged out.
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
