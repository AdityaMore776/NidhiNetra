# DRISHTI — the task plan

**Every remaining piece of work, split into tasks one person's AI can finish.** Each task has a GitHub
issue with the same ID (`T101` etc.); **the issue says who is doing it, this file says how**. Claim through
the issue (see [`AGENTS.md`](../../AGENTS.md) §3), never by editing this file.

- Where the build stands: [`docs/STATUS.md`](../STATUS.md) · what's been done lately: [`log/`](log/)
- The checkers and their measured results: [`docs/AGENT-CATALOG.md`](../AGENT-CATALOG.md),
  [`docs/trial/FINDINGS.md`](../trial/FINDINGS.md)
- The design behind all of this: [`docs/specs/2026-09-25-drishti-v2-full-agents-design.md`](../specs/2026-09-25-drishti-v2-full-agents-design.md)

**How to read a task:** **Size** S = one session, M = 2–3 sessions, L = a week (write a plan in
`docs/plans/` first). **Depends on** = tasks whose issues must be closed before you start (`scripts/team/sync.py`
reads these, so write them as task IDs on the heading line). **Data** = what you need
from the private team pack ([`DATA-PACK.md`](DATA-PACK.md)). **Done when** = every box must be true, with
command output to show it, before the PR is marked ready.

**Architecture:** the NidhiNetra blueprint ([`docs/specs/2026-09-27-nidhinetra-blueprint.md`](../specs/2026-09-27-nidhinetra-blueprint.md))
is the main plan: four engines → risk score → alerts, dashboards, Inspection Planner, field app → learning loop.
**Order:** T010 first (it unblocks the four engines). Core tasks (T0xx) come before side-track tasks (M9). After
T010, the four engines can be built side by side. Target dates are aims, not
deadlines. Editing this file (adding a task, fixing a spec) is fine in any PR: say so in your log entry.

### Rules every checker task shares

A **checker** (the design calls them "agents"; not to be confused with your AI) lives in
`apps/engine/drishti/agents/<id>/` and returns an `AgentResult` (`agents/contract.py`). Every checker task's
"Done when" silently includes:
- unit tests under `apps/engine/tests/agents/<id>/`, including a `NOT_ASSESSABLE` and a `NOT_APPLICABLE` case
- officer-facing text in plain words, no accusing words (the contract enforces it)
- the measurement on real data re-run through a script in `data/trial/` with its output saved in
  `data/trial/results/` (sanitised), matching or beating the number in FINDINGS, or FINDINGS updated with
  the honest new number
- `docs/AGENT-CATALOG.md` row + section updated (🧪 → ✅ once it's in the live engine)
- no real names, phone or account numbers in test fixtures: write synthetic OCR text that has the same layout

---

## M1c — Four agents only (owner's pivot, 3 Oct 2026): Cost, Duplicate Work, Time & Rules, Site Progress

The owner's decision: four agents, each flagging only what is likely fraud, never minor mistakes. The plan, in plain
words and ready for the deck: [`docs/plans/T120-four-agents.md`](../plans/T120-four-agents.md). Every new check stays
off (shown, not counted) until it meets the plan's §14 target.

### T120 · Four-agent architecture plan  ·  S  ·  docs
**What:** the prototype architecture of the four agents, the review of the owner's Site Progress design, the timing
facts measured on the dashboard (`data/trial/four_agents_timing.py`).
**Done when:** [x] plan written · [x] timing facts in `results/four_agents_timing.txt` and FINDINGS · [ ] owner's go-ahead

### T121 · Cost: every line against the district's rates, then the whole estimate  ·  L  ·  engine + data  ·  Depends on: T099
**What:** plan §6. Each confirmed line priced against its SoR code, the district's recent rates (5+ forms from 3+
agencies, never the agency's own) or the standard item; quantities against the size norms; charges and site
conditions against the map; then the fair estimate and the gap. Asks only when 60%+ of the money is compared and the
gap is 15%+ and Rs 50,000+ (starting values). SoR lines switch on once T096 lands; the rest can be built and tested
on planted forms first.
**Done when:** [ ] planted forms of plan §14 (9 in 10 padded by 20%+ caught, at most 2 in 100 honest asked) · [ ]
CAN'T CHECK and NOT_APPLICABLE cases · [ ] the officer's sentence names the top three lines · [ ] FINDINGS + CATALOG

### T122 · Time & Rules agent: the 75-day clock and the comfort window  ·  M  ·  engine  ·  Depends on: T099
**What:** plan §8. One agent from R01 (the clock, less election days), R06 (impossible dates), R13 and R14 (finished in
days), plus the comfort window: the form's "Expected duration" field renamed "Estimated time to completion", the
estimate checked against the band for its kind and size (an engineers' minimum table with a source per row, and
eSAKSHI's measured 90th percentile), the early and late lines, `FINISHED_TOO_FAST`, `BUILT_BEFORE_SANCTION`,
`PAST_PROMISED_TIME`, `SANCTIONED_LATE` (a fact, never queues alone).
**Done when:** [ ] tests at both lines' edges, padded and too-short estimates, declared lost months · [ ] dashboard
re-run: 20+ `FINISHED_TOO_FAST` read by eye, 9 in 10 worth checking · [ ] no work queued on lateness alone

### T123 · Site capture app: viewpoints, the walk, the site map, the seal  ·  L  ·  web + engine  ·  Depends on: T099
**What:** plan §9.3 and §9.8. Mobile web first (camera, GPS, motion sensors): the site opened from the form's map pins,
the first visit's viewpoints and zones, the monthly guided return with last month's view shown faintly, the at-site
checks that refuse a bad video, offline filming, the sealed upload; faces blurred before storage. A small Android app
for the mock-location and phone-integrity checks comes after.
**Done when:** [ ] a first visit and a monthly visit filmed end to end on a phone · [ ] a gallery upload and an edited
file refused · [ ] screenshots on a phone in the PR

### T124 · Site Progress v3: the six checks on video  ·  L  ·  engine  ·  Depends on: T123
**What:** plan §9.4 and §9.5: live and sealed, at this site (GPS and views both), new footage (fingerprints across
works and months), zones shown, change since last month at the same viewpoint, the agency's claim judged shown / not
shown / can't tell (the vision model on its free tier, capped). Findings only as in §9.5; notes never counted.
**Done when:** [ ] unit tests for each check and each finding, NOT_APPLICABLE (no videos) and NOT_ASSESSABLE · [ ] the
photo reuse numbers of FINDINGS B2 reproduced on kept frames

### T125 · Four agents only: registry, scoring, web; retire the rest  ·  M  ·  engine + web  ·  Depends on: T122
**What:** plan §12. The registry holds Cost, Duplicate Work, Time & Rules and Site Progress; Guideline Compliance,
Fund Flow, Office Patterns, Photo Evidence and Paperwork go to `RETIRED` (old results still read by name); fusion
weights for four; the web's agent list, how-it-works and explain pages.
**Done when:** [ ] engine and web checks pass · [ ] dashboard queue before / after in FINDINGS

### T126 · Site Progress field trial: honest visits and planted tricks  ·  M  ·  data + eval  ·  **human-task**  ·  Depends on: T124
**What:** plan §14: 3–5 real public works near teammates (with permission), three monthly visits each, and each trick
of §9.6 planted. Only readings and blurred frames are kept; no video enters the repo.
**Done when:** [ ] each trick caught 9 in 10 · [ ] a finding on at most 1 in 30 honest visits · [ ] FINDINGS

---

## M0 — Foundations

### T001 · Verify the 2023 guideline limits (45 vs 75 days; Annexure-II)  ·  S  ·  research  ·  human task
**Why:** mplads.gov.in refuses connections from outside India, so the 2023 guidelines PDF was never read.
The sanction clock (75 days in 2016 text, possibly 45 in 2023) and the prohibited-works list both depend on it.
**What:** a teammate in India downloads the MPLADS Guidelines 2023 PDF in a browser, commits it to
`docs/reference/` (it's a public document), and records the exact clauses: sanction/rejection days, the
prohibited-works annexure, inspection share (para 6.4 in 2016).
**Done when:**
- [ ] PDF in `docs/reference/`, with the page numbers of each clause in a log entry
- [ ] `apps/engine/drishti/reference/guidelines_clauses.yaml` and `prohibited_works.yaml` updated with 2023
      wording where it differs (clause ids cited); tests still pass
- [ ] FINDINGS and CATALOG say which clock the checks use

## M1 — Core: detect (four engines)  ·  target Oct wk 1–2

### T010 · Engine contract + registry for the four engines  ·  M  ·  engine  ·  **do first**
**What:** one place that lists the blueprint's four engines (compliance, cost, dup_split, delay) plus the
outlier signal, each returning per work `signal` 0–1 + `evidence`, so four people can build four engines in
separate folders without editing the same lines. Keep the existing `AgentResult` contract if it fits (`risk` =
signal) and the stored id `statistical` for cost; map old ids when reading stored assessments. Discovery by
folder (`apps/engine/drishti/agents/<engine>/`), a missing engine reports `NOT_BUILT`. The web work page shows
the engines that exist.
**Done when:** [ ] tests: discovery, NOT_BUILT, an engine raising → ERROR, a dummy engine added in a test
without editing central files · [ ] `data/dry_run.py` runs · [ ] `CONTRIBUTING.md` "Adding" recipe updated

### T011 · Guideline Compliance engine (rules.json, R01–R11)  ·  M  ·  engine  ·  Depends on: T010
**What:** `reference/rules.json` with the 11 starter rules from the blueprint spec (id, title, guideline_ref,
condition, severity, message_en, message_hi) and a vectorised evaluator. Severity → signal (1.0/0.6/0.3), highest
wins; evidence lists each broken rule with value vs limit. R07 reuses the Eligibility v2 patterns from
`data/trial/eligibility_trial.py` (worded "verify"). R06 reuses `validation/timeline.py` (impossible dates judged
by quarter). Add PII masking (phones, "S/o", "W/o", "Shri …") to the prepare step if not already masked.
**Done when:** [ ] one test per rule · [ ] counts per rule on the real corpus in the log · [ ] guideline_ref filled
(para numbers from T001; "TBC" until then) · [ ] no rule text uses accusing words

### T020 · Cost Anomaly engine (version A, then B + outlier)  ·  M–L  ·  engine + data  ·  Depends on: T010
**What:** start from the live cost agent (`agents/statistical/`); add the blueprint's signal
`clip((ratio-1.3)/1.7, 0, 1)` against leave-one-out peers (type + state + ±2 yrs, fallback national). Then
version B: LightGBM quantile models (out-of-fold) + Isolation Forest `s_outlier` as a separate signal.
**Done when:** [ ] `data/trial/cost_trial.py` re-run: catch rate at 2×/3×/5× and false alarms vs today's 63% /
1.5%; keep whichever is better and say so · [ ] tests · [ ] `s_outlier` exposed for T050

### T030 · Duplicate & Split-Work engine  ·  L  ·  engine + data  ·  Depends on: T010
**What:** multilingual embeddings (`paraphrase-multilingual-MiniLM-L12-v2`, free, local), district blocking,
pair score and split groups exactly as in the spec; embeddings precomputed by a data job (pgvector available).
Start from `data/trial/split_trial.py` and `dup_trial.py` (136 bulk groups / 744 works; 48 repeat pairs). A group
counts once in the score. Every flag says "verify".
**Done when:** [ ] plan in `docs/plans/` · [ ] hand-read top 50 pairs: share that look real, in FINDINGS · [ ]
the Nanded 3 × ₹4,96,000 split found · [ ] tests

### T040 · Delay Prediction engine (XGBoost + SHAP)  ·  M  ·  engine + data  ·  Depends on: T010
**What:** label and features per the spec; strict time-based backtest (train only on outcomes known then, as
`data/trial/delay_trial.py` does) and held-out districts; SHAP top reasons as evidence. Report the real AUC even
if under 0.80, and compare with the office's own record (0.68).
**Done when:** [ ] AUC + "late among riskiest 10%" in FINDINGS · [ ] wording never says "will be late" ·
[ ] model file loading tested; training script in `data/`

## M1b — Cost v3: a cost checker that knows the size (owner's pivot, 3 Oct 2026)

The implementing agency fills a full cost estimate form; the Cost agent checks it against the same kind and size of
work in the same district, then against the MP's amount. Plan: [`docs/plans/T097-cost-agent-v3.md`](../plans/T097-cost-agent-v3.md);
the form: [`docs/specs/2026-10-03-cost-estimate-form.md`](../specs/2026-10-03-cost-estimate-form.md). Strong accuracy:
normal mistakes are caught on the form, never flagged.

### T093 · Cost form contract: field list, checks, routes  ·  M  ·  engine
**What:** `reference/cost_form.yaml` (every field, one source), `drishti/cost_form/` (catalog, material matcher, the
fix / confirm checks), `GET /api/v1/cost-form/catalog`, `POST /api/v1/cost-form/validate`.
**Done when:** [x] every work type has its size fields · [x] checks tested (typos, units, arithmetic, totals, GPS
length, goods, OTHER, junk input never breaks them) · [x] routes tested · [x] the spec lists every field (test)

### T094 · Cost form screens and saving  ·  M  ·  web + engine  ·  Depends on: T093
**What:** the nine-step form of the spec §4, rendered from the catalog route, with the expense table, several sites,
live totals, fix / confirm at each field, drafts. Storage: migration `NNN_cost_forms.sql` (next free number),
`POST /api/v1/cost-forms` (draft or submitted; submitted only when `ready`), `GET /api/v1/cost-forms/{work_id}`;
district scoping like every route.
**Done when:** [ ] spec §10 checklist · [ ] API tests (save, read back, scoping, a not-ready form refused) · [ ] web
`tsc`, `lint`, `build` · [ ] screenshots on a phone and a laptop in the PR

### T095 · Cost v3 reference for one state (Uttar Pradesh) from real works  ·  S  ·  data
**What:** `data/trial/cost_v3_reference.py`: per work type, amounts, price per metre or per unit (size read by the Cost
engine's own readers), percentiles (p10–p98), by year, by district, and days from recommendation to sanction to
completion. Aggregates only.
**Done when:** [x] `results/cost_v3_reference_uttar_pradesh.json` + `.txt` · [x] numbers in FINDINGS "T095"

### T096 · Official rates data for Uttar Pradesh  ·  M  ·  data  ·  **human-task**
**What:** the UP PWD Schedule of Rates (current edition: item rates, area premiums, carriage charges); CPWD DSR 2023 +
the CPWD cost index for UP centres (fallback); CPWD analysis-of-rates consumption norms (cement per m³ by grade, bricks
per m³, …); UP minimum wages, GST rates, labour cess, royalty; GeM prices for the goods types. Digitised into
`reference/cost/` with a build script and a source note per number. The cloud environment cannot reach .gov.in
(tested 3 Oct 2026): download on an Indian connection into the data pack, or allow the hosts in the environment.
**Done when:** [ ] files in the data pack, listed in `docs/team/DATA-PACK.md` · [ ] build script + tests · [ ] a
sample of 20 digitised rates checked against the PDFs by eye

### T097 · Cost Estimate engine (v3)  ·  L  ·  engine  ·  Depends on: T093, T095
**What:** `agents/cost_estimate/` per the plan §6: price per unit of size vs the 98th percentile of the same kind
(and specification) in the district or state (30+ works, else "could not check"); then the MP check; line checks once
T096 lands; findings and notes of plan §6.5; the old `statistical` agent hands over (NOT_APPLICABLE) for works with a
form; batch and API attach the work's submitted form. Weight 0 until T098.
**Done when:** [x] planted tests of plan §8 pass · [x] NOT_APPLICABLE / NOT_ASSESSABLE cases · [x] the hold-out run on
UP 2026 works in FINDINGS · [x] AGENT-CATALOG row. (Built 3 Oct 2026, plan §11: price questions need two signals; the
hand-off from the old agent moved to T098.)

### T098 · Cost v3: prove it, then switch it on  ·  M  ·  engine + data  ·  Depends on: T094, T097
**What:** plan §8: planted tests on the test country with forms, the UP hold-out, 30 fresh flags read by eye, a pilot of
20–50 real estimates from an implementing agency; check the two margins the owner kept (+25% beyond the 98th
percentile, +10% over the MP's amount) on read flags, changing them only with the owner's go-ahead; then `reliability.json`
entries and a fusion weight; the old `statistical` agent hands over (NOT_APPLICABLE) for works with a form.
**Done when:** [ ] targets of plan §8 met (or FINDINGS says honestly where they are not) · [ ] owner's go-ahead

### T099 · Cost: one engine on the form, old Cost Anomaly retired, forms saved and attached  ·  M  ·  engine  ·  Depends on: T097
**What:** the owner's pivot (3 Oct 2026, plan [`docs/plans/T099-T100-simple-and-certain.md`](../plans/T099-T100-simple-and-certain.md)):
- measure whether any price question is certain from a record;
- the Cost Estimate engine takes the Cost core slot; `statistical` is unregistered;
- every state's reference is built;
- the storage half of T094: migration `013_cost_forms.sql`, `POST /api/v1/cost-forms` and
  `GET /api/v1/cost-forms/{work_id}`, and the batch, the work page and the API attach a submitted form.

**Done when:** [x] record-only check measured (0 of 15 real) · [x] a work with no form is NOT_APPLICABLE · [x] the old
Cost Anomaly retired · [x] migration + routes + API tests · [x] references for 7 states · [x] dashboard queue
before/after in FINDINGS

### T100 · Duplicate: is this work already sanctioned here, or one job cut to stay under a limit?  ·  M  ·  engine  ·  Depends on: T093
**What:** same plan, §3. Questions only when certain:
- a map pin within 50 m of a sanctioned work of the same kind;
- a declared rebuild of a work completed under 3 years ago;
- the strictest split (every piece 96–100% of a limit).

Look-alikes by words become notes, and the form asks the agency about them. Continuations are declared on the form
(nature `continuation`, earlier work ID, answers per look-alike).

**Done when:** [x] text rules measured on the 289 labelled pairs · [x] every strict split group on the dashboard read by
eye · [x] unit tests at the 50 m edge, linear works, declarations, damaged forms · [x] test country plants pin repeats and
rebuilds (caught 100%, look-alikes 0) · [ ] first officer verdicts on real forms (T098)

## M2 — Core: explain + act  ·  target Oct wk 3 – Nov wk 1

### T050 · Risk score 0–100, bands, top-3 reasons (EN + HI)  ·  M  ·  engine  ·  Depends on: T011, T020
**What:** replace fusion v1 with the blueprint formula (weights 0.30/0.20/0.20/0.20/0.10, safety floors 70/85,
bands Low/Medium/High/Critical); contributions add up to the score; per-engine sentence templates in English and
Hindi. Tune cut-offs so High + Critical ≈ 5–10%. Engines not built yet count 0 and are shown as "not built".
**Done when:** [ ] tests for formula, floors, bands, reasons · [ ] band shares on the real corpus in the log ·
[ ] `batch_assess.py` + API + work page show score, band and 3 reasons

### T060 · Alerts, lifecycle, audit log  ·  M  ·  engine + web  ·  Depends on: T050
**What:** tables `alerts` (New → Triaged → In plan → Inspected → Issue confirmed / Cleared → Closed) and
hash-chained `audit_log`; `GET /alerts`, `PATCH /alerts/{id}`; district queue UI with triage actions; daily digest
to console.
**Done when:** [ ] every state change audited, chain verified by a test · [ ] role scoping tested

### T061 · Location lookup  ·  S–M  ·  data  ·  Data: LGD / PIN files
**What:** work → approximate lat/lon: village or place token → block → district centroid, with a precision flag
("approximate"). Our LGD outlines + PIN file + district crosswalk are the starting point.
**Done when:** [ ] share of works at each precision level in the log · [ ] never joins census and LGD codes by number

### T062 · Inspection Planner (headline)  ·  L  ·  engine + web  ·  Depends on: T050, T061
**What:** exactly the spec's algorithm (candidates risk ≥ 40 + 10% random, value = risk × money weight, greedy
by value per extra minute within 8 h, OR-Tools TSP, per-stop checklist from the reasons). `POST /plans/generate`,
`GET /plans/{id}`; map + stop list on the district dashboard.
**Done when:** [ ] plan in `docs/plans/` · [ ] km saved vs visiting the top sites in list order, measured on real
districts · [ ] tests for the greedy step and the budget

### T063 · Field verification app (mobile web)  ·  M  ·  web + engine  ·  Depends on: T062
**What:** today's route, site card, checklist, photo + GPS + time, verdict (OK / Issue / Not found / Can't verify);
GPS > 2 km from site → "location mismatch"; perceptual-hash reuse check (port from `data/trial/photo_trial.py`).
Submissions labelled `source = LIVE`, written to the audit log.
**Done when:** [ ] works on a phone browser · [ ] verdict reaches the alert and the audit chain

### T064 · Pre-sanction check  ·  M  ·  engine + web  ·  Depends on: T011, T020, T030
**What:** one screen / API: run compliance (category, location), dup/split search and expected cost on a new
recommendation → Green / Amber / Red with reasons. Never blocks.
**Done when:** [ ] one test per colour · [ ] demo case from real data in the log

### T065 · Role dashboards: Ministry, State, District, MP, Field  ·  L  ·  web + engine  ·  Depends on: T050
**What:** the spec's screens per role, row-level scoping (a district officer's API answers "not found" outside
their district). MP view is a neutral status view of their own works: no reviewer tools, no risk wording, and
MPs are never scored. Includes the dashboard-speed summary tables (was T002).
**Done when:** [ ] plan in `docs/plans/` · [ ] each role checked with demo logins · [ ] screenshots in the PR

## M3 — Core: learn + prove  ·  target Nov wk 2–3

### T070 · Learning loop (simulated verdicts)  ·  M  ·  engine  ·  Depends on: T060, T063
**What:** reliability = (1 + a)/(2 + a + b) per engine over alerts where it was a top-3 reason; weights re-tuned
and renormalised; "what changed" note; 10% exploration visits in the planner. Demo with simulated verdicts on
planted cases, labelled "mechanism demo, not field accuracy".
**Done when:** [ ] tests for the reliability maths · [ ] before/after weights shown on the Ministry dashboard

### T080 · Planted-anomaly test (50 fakes)  ·  M  ·  data + eval  ·  Depends on: T050
**What:** script that copies the works, plants 50 labelled fakes (inflated cost, reworded/translated duplicates,
splits, rule breaches, impossible timelines, `source = SCENARIO`), runs the pipeline blind, reports the share in
the top 5% of each engine and overall. Never mixes planted rows into the live database silently.
**Done when:** [ ] result JSON in `data/trial/results/` · [ ] numbers in FINDINGS and the deck, reported honestly

### T090 · Five-minute demo script + judge Q&A  ·  S  ·  docs  ·  Depends on: T062, T080
**Done when:** [ ] script walks the loop by role on the live site · [ ] every number from FINDINGS

### T092 · DRISHTI Visualization Engine: what happens to a work, step by step  ·  L  ·  engine + web  ·  Depends on: T050, T064
**Owner's request, 2 Oct 2026.** Plan: `docs/plans/T092-visualization-engine.md`. A public page (`/explain`) that shows
judges, with animations, what DRISHTI does to a work at each step (input, privacy, reading, the seven checks, the
score's arithmetic, the officer's result), each step replayable, with built-in examples and the judge's own example.
Every number is real engine output (`drishti/explain.py`); built-in examples run on the dashboard's 40,935 works.
**Done when:** [x] `explain()` + route + tests · [x] examples built on the dashboard data · [x] page animated and
replayable, own example via the API · [x] web checks pass, checked in a browser · [x] docs, log

### T091 · Rename user-facing text to NidhiNetra  ·  S  ·  web + docs  ·  **needs-owner** (confirm the name)
**What:** app title, logo text, README, docs headers. Repo/folder names and env vars stay (they carry deploy ids).

---

### T051 · Every engine works on any recommendation (generalisation review)  ·  L  ·  engine + data  ·  Depends on: T050
**Owner's request, 1 Oct 2026.** Plan: `docs/plans/T051-engines-any-recommendation.md`. One brain per engine: no
engine reads a per-work answer stored by an offline job; signals grow with the evidence; band cut-offs re-tuned.
**Done when:** [x] made-up unseen recommendations get the same rules as corpus works · [x] every engine measured
before/after (FINDINGS "T051") · [x] fresh by-eye samples with rules frozen · [x] queue re-read by eye

### T055 · Engine review: test country, Office Patterns, calibrated score (v3), dashboard data  ·  L  ·  engine + data + eval  ·  Depends on: T051, T080
**Owner's request, 2 Oct 2026:** "make the product way better at finding problems on MPLADS: refine each agent,
find a more accurate architecture, add agents, test them aggressively on unseen data". Write-up:
`docs/plans/T055-engine-review.md`; numbers in FINDINGS "T055".
**Done when:** [x] a seeded made-up country with planted problems measures recall (`drishti/evaluation/`), with a
CI quality gate · [x] every engine measured before/after on it and on the dashboard's 40,935 unseen works · [x]
queue read by eye · [ ] hosted DB: migrations 011 + 012 applied and works re-assessed (**needs-owner**) · [ ]
planted test (T080) re-run on the full 2,09,993 works with v3 (needs the data pack)

### T056 · Foolproof and accuracy pass: evidence engines, Fund Flow, Paperwork reader, Cost  ·  M  ·  engine + eval  ·  Depends on: T055
**Owner's request, 2 Oct 2026:** "work on the next few agents to make them foolproof and accurate". Malformed or
oddly written records must never crash an engine or the batch, and the same facts written another way must give
the same answer; accuracy changes only where real flags read by eye show a fix. Numbers in FINDINGS "T056".
**Done when:** [x] fuzz + invariant tests for every evidence engine and index · [x] Fund Flow reads any case,
text dates, impossible dates · [x] certificate reader survives OCR noise (tests) · [x] Cost: misses diagnosed,
real flags read by eye, fix measured on real and test works · [x] Duplicate & Split: split flags read by eye, fixes
measured, a fresh sample read · [x] the work record itself: damaged rows in the corpus cannot stop the indexes or
the statistics, loosely typed records give the same answer (`records.py`) · [x] owner re-runs `build_evidence.py` +
`paperwork_trial.py` to measure the reader change on real certificates (sanction date 69.4% → 69.4%, vendor code
97.7% → 97.9%; `results/paperwork_trial_t056.txt`)

## M9 — Side track: real-evidence checkers (after the core; they feed its engines)

**Merged 12 → 8 (T051).** The owner asked for about eight checkers. The merged tasks below replace the old ones
(which stay in this file as the detailed specs): **T110 Paperwork** = T101 + T102 + T103 + T104 (Document +
Contractor read the same certificates) · **T310 Photo Evidence** = T301 + T302 + T303 + T304 + T505 (one photo:
new? from this place? from this time?) · **T410 Delay & Fund Flow** = T402 folded into the Delay engine ·
**T510 Site Progress** = T503 + T604 (v2, 2 Oct 2026: free local readers, built and off until its go/no-go on the
pilot photos passes; the owner's key only adds judging free-text claims; satellite only after its go/no-go; plan
`docs/plans/T510-site-progress-v2.md`). Every merged checker follows T051's rule: its reasoning runs in the engine on any work's evidence;
offline jobs only extract facts with the engine's own reader.

These come from the earlier 12-checker design and our real-evidence trial. Build them only when the core task you
could take is blocked or done. Where they fit the core: Document feeds R03/R04/R05 with real payment dates;
Photo Forensics and Geo feed the field app; Contractor Network and Fund Flow are extra dashboard facts.
In each spec below, read "checker" as an engine plugged in through T010's registry: where a spec says `Depends
on: T100`, it now means T010.

### T003 · Harvest more evidence (one person at a time)  ·  M  ·  data  ·  **needs-owner** (picks the districts)
**Why:** the pilot is 837 works (Pratapgarh + 400 random). Photo, geo and document checkers need more
districts, and satellite needs large works with coordinates.
**What:** run `data/harvest/esakshi_evidence.py` for districts the owner picks, at the built-in polite rate
(never faster), then `data/trial/ocr_pages.py`. Add the new files to the team pack (tell the owner).
**Done when:** [ ] manifest lines added, no request faster than 1.5 s · [ ] OCR run · [ ] log entry lists
districts, works, files, MB and minutes · [ ] pack updated
**Label:** `needs-owner` until the owner names the districts.

---

### T101 · Evidence tables + loader  ·  M  ·  engine + data  ·  Depends on: T010  ·  Data: evidence + OCR cache
**What:** migration for the evidence-derived tables (design §7: `evidence_files`, `doc_fields`,
`photo_hashes`, `overlay_geo`, `contractors`, `contractor_links`; create only what M1 needs, leave the rest
for their tasks) and `data/load_evidence.py` that fills them from `data/evidence/manifest.jsonl` + the OCR
cache. **Only derived facts go in the database** (dates, amounts, vendor code, file kind); never file bytes,
names or account numbers. The engine loads a work's evidence facts into the checker context.
**Done when:** [ ] migration + RLS tested with pgserver · [ ] loader is idempotent (run twice → same rows) ·
[ ] loads all 837 pilot works locally; counts in the log · [ ] a masking test proves account numbers never
reach a table

### T102 · Certificate reader in the engine  ·  M  ·  engine  ·  Depends on: T010
**What:** port the UP Utilisation Certificate parser from `data/trial/document_trial.py` (`parse_uc`,
`parse_uc_p2`, `page_kind`, `after_colon`, `ordered_lines`, `to_date`) into
`apps/engine/drishti/agents/document/reader.py` as pure functions over OCR output. Keep both form versions
(the older one has no sanction-date line; fall back to the certification paragraph).
**Done when:** [ ] tests on synthetic OCR pages for both form versions, missing fields, OCR-dropped spaces ·
[ ] re-running the trial through the ported reader reproduces FINDINGS' field coverage (≥99% amounts,
98% vendor, 91% agency, 69% sanction date on 431 certificates) · [ ] 10 certificates checked by eye, noted in the log (work IDs only)

### T103 · B4 Document checker  ·  M  ·  engine  ·  Depends on: T101, T102
**What:** checks, each a finding with its evidence and clause:
1. sanctioned more than 75 days after recommendation (clock from `guidelines_clauses.yaml`; T001 may change it)
2. sanction dated before the recommendation (hard: impossible order)
3. certificate payments don't add up to the portal amount (portal amount = what was paid)
4. portal says complete, every attached paper says "in progress" (a note, not a finding: 282 of 285 do this)
5. the officer's certification boxes blank (note)
6. another work's certificate attached (needs checking)
`NOT_APPLICABLE` = no evidence; `NOT_ASSESSABLE` = papers the local reader can't read (Hindi, handwritten).
**Done when:** [ ] reproduces FINDINGS: 16% of 211 late, 1 sanction-before-recommendation · [ ] every check
has a test · [ ] runs in `batch_assess.py`; queue size before/after in the log (it must not flood the queue)

### T104 · C3 Contractor Network checker  ·  M  ·  engine + data  ·  Depends on: T101
**What:** vendor code (e.g. `V9174…`) = exact contractor identity. Precompute per district and per agency:
works per vendor, top-1 and top-3 share. Per work: show the vendor's share as a fact; a finding only when
combined with another checker's finding (low weight on its own). Never name a person on screen; show the
vendor code.
**Done when:** [ ] reproduces Pratapgarh: 261 works, 7 vendors, top 39%, top three 84% · [ ] tests ·
[ ] catalog explains "concentration is a fact, not a finding"

### T105 · Web: evidence panel + Document/Contractor cards  ·  M  ·  web  ·  Depends on: T103 (start the Contractor card once T104 is merged)
**What:** on the work page, list the evidence files (kind, date, pages; no personal data) and the facts read
from them; cards for Document and Contractor. Read `apps/web/AGENTS.md` first (Next.js 16).
**Done when:** [ ] `tsc`, lint, build clean · [ ] screenshots of a work with a late sanction and a work
with no evidence in the PR · [ ] no account number or phone number rendered (grep the page)

### T106 · Load M1 into the hosted database and deploy  ·  S  ·  **needs-owner**  ·  Depends on: T103, T104, T105
**What:** the owner (hosted DB secrets) runs `data/with_env.py load_evidence.py` then `batch_assess.py`,
checks the live site, updates STATUS.
**Done when:** [ ] live work page shows the Document card for a Pratapgarh work · [ ] STATUS "At a glance" updated

---

### T301 · Photo fingerprints data job  ·  M  ·  data + engine  ·  Depends on: T101  ·  Data: evidence
**What:** from `data/trial/photo_trial.py` (`phash256`, `orb_features`, `orb_inliers`): compute for every
evidence **photo** (not PDFs/certificates: fingerprints don't work on forms) a SHA-256, a 256-bit
fingerprint and ORB features; store in `photo_hashes` (bit(256)). OpenCV stays in the offline job; the engine
only compares stored values.
**Done when:** [ ] 319 pilot photos processed · [ ] the edit-robustness test reproduces 99.9% (either method)
with 0 confusions between different photos at the chosen thresholds

### T302 · B2 Photo Forensics checker  ·  M  ·  engine  ·  Depends on: T301
**What:** exact copy on another work → finding, **except** combined files (an invoice or certificate naming
several works/villages is normal; an exact copy matters only when the file names one work or person);
near-copy via fingerprint or ORB → finding.
**Done when:** [ ] the 5 byte-identical groups found; the 2 "needs checking" ones flagged and the 3 combined
files not · [ ] tests for each rule

### T303 · GPS-stamp reader in the engine  ·  M  ·  engine  ·  Depends on: T101
**What:** port `read_stamp()` + `LATLON`/`DATES` from `data/trial/geo_trial.py` into
`agents/geo_location/stamp.py` with all three date fixes (US-style dates from one app; misread year corrected
by the printed weekday; only a date followed by a time counts as the stamp, so painted plaque dates are
ignored). Store results in `overlay_geo`.
**Done when:** [ ] tests for each stamp app format and each date fix (synthetic text) · [ ] 190 stamps on
170 works reproduced · [ ] 12 checked by eye still correct

### T304 · B3 Geo-Location checker  ·  M  ·  engine  ·  Depends on: T303  ·  Data: PIN file, LGD outlines
**What:** inside the work's own district (LGD outline via the crosswalk; within 5 km of the border =
"at the border", not a finding); PIN code agrees with the district (the PIN file predates new districts:
note, not finding); photo dated before the recommendation (finding, needs checking); same spot, same day,
two works (weak note).
**Done when:** [ ] reproduces: 187 points inside their district, 0 far away, the 3 "finished before
recommended" works (Sabar Kantha 7171, Chittaurgarh 124508 and 124252) · [ ] tests

### T305 · Web: photo evidence with stamp facts  ·  M  ·  web  ·  Depends on: T302, T304
**What:** no photo thumbnails: they are real government evidence and stay off the site unless the owner
decides otherwise. Show the facts (stamp date/place, distance to district, reuse matches
by work ID) and cards for B2/B3.
**Done when:** [ ] cards render for a work with a stamp and one without · [ ] screenshots in the PR

---

### T402 · C2 Fund Flow: sanction backlog + term-end leftovers  ·  M  ·  engine + data  ·  Depends on: T010  ·  Data: fund files
**What:** from `data/trial/fund_flow_trial.py` (`sanction_backlog`, `funnel`, `timing`): works waiting for
sanction past the clock (21,323 works, ₹1,361 cr, median 239 days); those recommended under a Lok Sabha term
that has ended (3,331, ₹169 cr). MP-level money is summed by term and **never scored per MP**. Compare
offices only with the same period nationally (the "March rush" was a portal cycle).
**Done when:** [ ] reproduces the figures above · [ ] tests · [ ] no MP name in any finding

### T501 · Gemini provider with a quota ledger  ·  M  ·  engine  ·  **needs-owner** (key)
**What:** one provider class behind a switch: free tier by default, a hard daily cap, every call logged to a
ledger table, cached by file hash so nothing is read twice. Key only in env (`GEMINI_API_KEY`), never in code.
**Done when:** [ ] tests with a fake provider · [ ] cap enforced in a test · [ ] works with no key (checkers
report NOT_ASSESSABLE, never crash)

### T502 · Hindi and handwritten papers  ·  M  ·  engine + data  ·  Depends on: T501, T103
**What:** send the 51% of papers local OCR can't read to Gemini; extract the same fields as T102.
Low-confidence fields become "can't tell", never findings.
**Done when:** [ ] field accuracy measured by eye on 20 papers, in FINDINGS · [ ] cost per paper in the log

### T503 · B1 Site Progress + plaque check  ·  L  ·  engine + web  ·  Depends on: T501
**What:** the site officer writes in their own words what changed; the AI judges each claim against the
photos: **shown / not shown / can't tell**. Never a fixed yes/no checklist. Plaque check: is the MPLADS
plaque visible (CAG found 4,918 works without one). A reused photo (B2) voids progress confirmations.
**Done when:** [ ] plan in `docs/plans/` · [ ] the decisive test: photos of a half-built thing + a claim the
photos plainly don't show ("roof slab cast", no roof) → "not shown" · [ ] measured on real evidence


### T505 · D1 Citizen Verification demo  ·  S–M  ·  web  ·  Depends on: T302, T304
**What:** QR/link → simple form (photo + GPS) checked by B2/B3. eSAKSHI ratings are unused (21,789 of 21,793
are zero), so this is shown only as a **clearly labelled demo**.

---

### T604 · B5 Satellite go/no-go (big works only)  ·  L  ·  research  ·  Depends on: T003
Only ponds, roads over 1 km, large buildings, and only with coordinates. Go/no-go test first: if built vs not
built can't be told apart on real sites, it stays off and the docs say so.

---

## Adding a task

New work found? Add it here under the right milestone with the next free ID (`T206`, …), then create its
issue: `gh issue create --title "T206: <title>" --label ready --milestone "<milestone>" --body "Spec:
docs/team/TASKS.md, section T206"`. Mention it in your log entry.
