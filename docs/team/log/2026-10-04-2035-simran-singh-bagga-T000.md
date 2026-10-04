# T000: Work intelligence form: a signed-in tab below Pre-sanction check

- **Who:** @Simran Singh Bagga (agent: Claude Code)
- **When:** 2026-10-04 20:35 IST
- **Task / issue:** T000 (no issue: `gh` is not logged in on this machine)
- **Branch / PR:** main, pushed directly at the user's request (no branch, no PR); from 0006a28
- **State:** merged

## What I did
Web only; no engine, API, database or agent change.

- Added the team's **Pre-Sanction Work Intelligence Form** (PSWIF v1.0, sections A–K) to the app as a new sidebar
  tab, **Work intelligence form**, directly below Pre-sanction check, at `/work-form`.
- **Signed-in only.** The tab is hidden from the public view (role `PUBLIC`, T130) in the sidebar and in the
  Ctrl+K search. A public visitor who opens `/work-form` directly gets a "Sign in to fill the work intelligence form"
  panel, not the form.
- **The form is unchanged.** The original file is `apps/web/forms/pre-sanction-work-intelligence-form.html`, byte for
  byte as given. `scripts/embed-forms.mjs` (run by `predev`/`prebuild`) turns it into
  `src/lib/forms/pre-sanction-work-intelligence-form.ts`, and the page shows it in a frame (`srcDoc`), so the site's
  styles never touch it and there is no public URL for the bare file. Its own toolbar works as before: drafts in
  this browser's localStorage, required-data check, JSON export, print. "Open in a new tab" opens the same form.
- **Fix:** the smooth-scroll CSS from the redesign disabled clicks on every iframe
  (`.lenis.lenis-smooth iframe { pointer-events: none }`); it now applies only while a scroll is running
  (`.lenis-scrolling`), as Lenis intends. Without this the form could not be filled.

## How I checked it (commands run and what they printed)
- `cmp` of the Downloads file and `forms/…html` → identical; the generated module round-trips to the same string
  (`round-trip identical: true`, 67,691 characters)
- `cd apps/web && npx tsc --noEmit` → clean · `npm run lint` → exit 0 · `npm run build` → 13 routes, `/work-form` included
- Browser, local engine on main's code (test database migrated to 014):
  - signed in (dev role MINISTRY): the tab shows below Pre-sanction check; the form renders; its "Validate Required
    Data" button answers inside the app ("add at least one valid BOQ line…")
  - public view (no dev role; `/me` answers `PUBLIC`): the sidebar lists `/presanction` but no `/work-form`;
    `/work-form` shows the sign-in panel

## Numbers measured (only from saved script output)
- None.

## Decisions made (and why)
- **A frame, not a port to React:** the owner asked that the form's look stay exactly as designed; a frame keeps its
  CSS, scripts and sticky toolbar intact and isolated.
- **Bundled, not in `public/`:** a file in `public/` would be reachable by URL without signing in.
- **The generated module is committed:** CI runs `tsc` before `build`, so it must exist without `prebuild`.

## Problems, traps, surprises
- The form's section J says "Completeness only; this is not a fraud score". Rule 1 keeps accusing words out of
  officer-facing text; this one is a disclaimer, and the form was to stay unchanged, so it is left as written.
  The owner may want it reworded (e.g. "this is not a risk score").
- The form saves drafts only in the browser (localStorage) and exports JSON; nothing reaches the engine yet.

## Files touched
- `apps/web/forms/pre-sanction-work-intelligence-form.html` (new), `apps/web/scripts/embed-forms.mjs` (new),
  `apps/web/src/lib/forms/pre-sanction-work-intelligence-form.ts` (generated), `apps/web/src/app/(app)/work-form/page.tsx` (new)
- `apps/web/src/components/shell/{nav.ts,AppSidebar.tsx,Topbar.tsx}`, `apps/web/src/app/globals.css`, `apps/web/package.json`

## Next step (exact, so another agent can pick it up cold)
1. After the deploy, sign in on https://drishti-lyart.vercel.app and open Work intelligence form. This went to main
   without a PR, so CI did not run on it first: the same checks were run locally (above).
2. If the form should be saved to the database for the agents (Cost reads the cost estimate form, T093/T094), wire its
   "Export Structured JSON" shape to the engine's cost-form routes in a separate task.

## Needs a human / the owner?
- Optional: the wording "this is not a fraud score" in the form's section J (see Problems).
