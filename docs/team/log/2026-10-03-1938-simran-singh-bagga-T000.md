# T000: NidhiNetra frontend redesign: new brand, type, shell, 3D dashboard, globe, sign-in

- **Who:** @Simran Singh Bagga (agent: Claude Code)
- **When:** 2026-10-03 19:38 IST
- **Task / issue:** T000 (no issue: `gh` was not logged in on this machine). Covers the web half of T091 (rename to NidhiNetra).
- **Branch / PR:** simran/T000-nidhinetra-ui (from main at 3888f7b; no PR yet)
- **State:** ready for review

## What I did
Frontend only. No engine, API, database or agent code was touched (`git status` shows nothing under `apps/engine`, `data/`).

- **Brand:** the team's NidhiNetra emblem cut out of its white background (the eye's white kept opaque) as
  `public/brand/nidhinetra-emblem*.webp`, plus `src/app/{favicon.ico,icon.png,apple-icon.png}`. Every user-facing
  "DRISHTI" in the web app now says NidhiNetra (`Logo.tsx`, titles, Explainer copy).
- **Design system** (`src/app/globals.css`): white surface, brand ramp sampled from the emblem (navy / royal blue /
  cyan / teal), eight engine colours as a validated categorical palette, band colours as reserved status colours.
  Legacy token names (`--navy`, `--inputs`, …) kept as aliases so the Explainer's animations still work.
- **Type** (`src/app/layout.tsx`): Geist for the interface and all numbers (tabular figures), Instrument Serif
  italic for one accent word per headline, Geist Mono for ids and labels, Noto Sans Devanagari for the Hindi reasons.
- **Libraries:** shadcn/ui initialised (`components.json`, Radix, "nova"), Kokonut UI registry added
  (`@kokonutui`); six Kokonut components adapted to the brand. Added three, @react-three/fiber, @react-three/drei,
  motion, gsap, @gsap/react, lenis, recharts (via shadcn chart).
- **App shell:** shadcn inset sidebar (collapsible to icons, a sheet on phones), sticky glass top bar, Ctrl+K search
  palette (pages, risk bands, work types, full-text search), entry transitions between pages, Lenis smooth scroll.
- **Dashboard:** count-up figures; a 3D "review funnel" (R3F: every band as a ring of particles around the eye,
  exact counts in the legend); the district map is now a **3D globe** (MapLibre globe projection, districts extruded
  by share / count / money, fly-in from the whole Earth, 3D/flat toggle) with the same hover card and the same click to
  `/works?district=`; "districts to look at first" list that steers the globe; charts: engine findings, risk mix,
  works needing review by state, district size vs share (click opens the district), money by state treemap; offices
  tables restyled.
- **Sign-in:** a scroll-told landing page; the sign-in logic is unchanged (same Supabase call, same dev mode). The 3D
  emblem was modelled in Blender (dome, colonnade, eye, sweep, circuits, flag), exported as meshopt glTF
  (`public/models/nidhinetra-emblem.glb`, 571 KB; source `apps/web/design/nidhinetra-emblem.blend`); GSAP plays its
  arrival, its iris follows the pointer, it turns as the page scrolls.
- **Other pages:** queue (filters in the address bar, rank continues across pages), works (filters in the address
  bar, removable chips; fixes the old "search box ignores back button" problem by keying the box on `?q=`), work page
  (score gauge, animated parts bar, reasons EN/HI, engine overview strip, engine cards, cost evidence strip, dates
  timeline from stored dates only), pre-sanction (traffic-light verdict), how it works (scroll-drawn pipeline, engine
  cards), Explainer (new shell and controls; the six steps unchanged).
- 3D scenes stop rendering when scrolled off screen; reduced-motion is respected everywhere.

## How I checked it (commands run and what they printed)
- `cd apps/web && npx tsc --noEmit` → no output (clean)
- `cd apps/web && npm run lint` → exit 0, no problems
- `cd apps/web && npm run build` → compiled; 11 routes prerendered (`/`, `/explain`, `/how-it-works`, `/login`,
  `/presanction`, `/queue`, `/work`, `/works`, icons, not-found)
- `python scripts/team/setup.py` (first run on this machine) → engine tests `599 passed`
- Dataviz palette check: `validate_palette.js "#2563eb,#ea6a2a,#c026d3,#0d9488,#7c3aed,#a16207,#0891b2,#db2777" --mode light`
  → all checks pass (worst adjacent CVD ΔE 10.3, normal-vision ΔE 23.3, every slot ≥ 3:1 on white)
- Clicked through every page in the browser against a local engine (see "Problems"): dashboard, globe hover and click,
  queue band tabs, works filters, a work page, a pre-sanction check (Amber), how it works, the Explainer playing,
  the sign-in page on desktop and at 375 px (no horizontal scroll).

## Numbers measured (only from saved script output)
- None about MPLADS. Every figure seen while building came from a made-up local database (below) and is not a finding.

## Decisions made (and why)
- **Worked from latest main, not from @iamjaydatt2006's `T000-operational-ui-redesign` branch** (the user's choice):
  that branch also rewrites the shell, dashboard, queue, works and work pages and carries engine migrations 013–015.
  Whichever of the two merges second will have to merge the page files by hand; their Alerts and Inspections pages
  will need the new look afterwards.
- **No radar chart of engine risks on the work page:** it would draw "could not assess" as a zero, against rule 2.
  An engine strip says each engine's status in words instead.
- **Globe shows only India's LGD outlines** on a plain sphere with a graticule: no third-party world borders, as the
  old map already insisted.
- **Bands are never colour alone:** every badge carries its word; engine colours never reuse the band reds/amber/green.
- **Removed** `components/ui.tsx` (replaced by `components/nn/*`, since `components/ui/` is now shadcn's folder) and
  the flat `IndiaMap.tsx` (replaced by `map/IndiaGlobe.tsx`).

## Problems, traps, surprises
- **No data pack on this machine**, so the real corpus could not be loaded. For looking at the screens only, a local
  pgserver was filled with the engine's own made-up corpus (`drishti.evaluation.synthetic`, 34,320 works mapped onto
  real outlines) and assessed by the real engine. That script stayed out of the repo; nothing from it is committed.
- **shadcn's `--muted` is a background colour; the old code used `--muted` for grey text.** The Explainer was moved
  to `muted-foreground`; any new code should use `text-muted-foreground` for grey text.
- **React-Compiler lint rules:** don't mutate values returned from hooks in R3F (`useThree`, `useMemo`); read
  `camera`/`pointer` from the `useFrame` callback and reach scene nodes through a ref. shadcn's generated
  `use-mobile.ts` was rewritten on `useSyncExternalStore` for the same reason.
- **SVG gradient on a straight line:** `objectBoundingBox` gradients do not render on a zero-height line; use
  `gradientUnits="userSpaceOnUse"`.
- **Hydration:** Node and the browser disagree in the last digits of `Math.sin`; generated SVG paths are rounded.
- `next/font` variable `--font-devanagari` clashed with the Tailwind theme key; the font variable is `--font-noto-deva`.
- Two engine strings still say "DRISHTI" (the cost engine's comfort-zone sentence, and three headlines inside
  `public/explain/examples.json`, which a script generates). Left alone: backend text, out of this task's scope.

## Files touched
- `apps/web/`: `package.json`, `package-lock.json`, `components.json` (new), `README.md`, `design/` (new),
  `public/brand/` (new), `public/models/` (new)
- `apps/web/src/app/`: `globals.css`, `layout.tsx`, `favicon.ico`, `icon.png`, `apple-icon.png`, `login/page.tsx`,
  `(app)/{layout,page}.tsx`, `(app)/{queue,works,work,presanction,how-it-works}/page.tsx`, `explain/{Explainer,steps,page}.tsx`, `explain/explain.css`
- `apps/web/src/components/`: `Logo.tsx`, `AgentCard.tsx`, `FusionPanel.tsx`, `StatisticalEvidence.tsx`; new folders
  `charts/`, `kokonutui/`, `map/`, `motion/`, `nn/`, `shell/`, `three/`, `ui/`; removed `ui.tsx`, `IndiaMap.tsx`
- `apps/web/src/lib/`: `format.ts` (engine/band colours), `cache.ts` (new), `utils.ts` (new); `src/hooks/` (new)

## Next step (exact, so another agent can pick it up cold)
1. The owner (or anyone with the data pack) runs it on the real corpus: `python scripts/team/setup.py --db`, then
   `python scripts/dev/start.py`, and checks the dashboard globe and charts with all ~750 districts.
2. `gh auth login`, push, open the PR: `gh pr create --title "T000: NidhiNetra frontend redesign" --body "..."`.
3. Coordinate with @iamjaydatt2006 on merge order (see Decisions); after both land, restyle `/alerts` and
   `/inspections` with `components/nn/*`.
4. T091 rest (owner): README and docs headers; the two engine strings that still say DRISHTI.

## Needs a human / the owner?
- Yes: confirm the NidhiNetra name for T091 (the user says the team has switched), and agree merge order with
  @iamjaydatt2006's UI branch.
