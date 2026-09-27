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

**Order:** T100 first (it unblocks parallel work). After that, milestones are a priority order, not a queue:
M1–M4 tasks can run side by side because each checker lives in its own folder. Target dates are aims, not
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

## M0.5 — Team foundations

### T100 · Checker registry: 12 slots, one folder each  ·  M  ·  engine  ·  **do first**
**Why:** the pipeline still has the old 4 hard-coded slots (`site_progress`, `image_reuse`,
`duplicate_project`, `statistical`) in `pipeline/orchestrator.py` and `fusion/fuse.py`. If four people each
add a checker by editing those lists, every PR conflicts.
**What:** make adding a checker a one-folder change.
- Each `agents/<id>/__init__.py` declares `ID`, `LABEL`, `QUESTION`, `STAGE` (A/B/C/D), `PRIOR_RELIABILITY`
  and `run(work, ctx) -> AgentResult`. The orchestrator discovers the folders; a missing checker reports
  `NOT_BUILT`, exactly as today.
- The 12 v2 slots, in stage order: `eligibility`, `duplicate_split`, `statistical` (label "Cost"; keep the
  id, the stored assessments use it), `site_progress`, `photo_forensics`, `geo_location`, `document`,
  `satellite`, `delay`, `fund_flow`, `contractor_network`, `citizen_verification`.
- `Context` gets a way for a checker to receive precomputed lookups (e.g. split groups, vendor
  concentration) loaded once per batch, like `StatsStore` today.
- The web work page renders whatever checkers the engine returns, grouped by stage (read
  `apps/web/src/components/AgentCard.tsx`, `FusionPanel.tsx`).
- Old ids `image_reuse`/`duplicate_project` in stored assessments: map them to the new ids when reading.
**Done when:**
- [ ] all existing tests pass unchanged in meaning; new tests: discovery, NOT_BUILT for empty slots, an agent
      raising → ERROR, old-id mapping
- [ ] a throwaway dummy checker added in a test proves "one folder, no central edit"
- [ ] `data/dry_run.py` runs; the local web app shows 12 cards in 4 stage groups
- [ ] `CONTRIBUTING.md` "Adding an agent" updated to the new one-folder recipe

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

### T002 · Summary tables for a fast dashboard  ·  S–M  ·  engine + data
**Why:** the first load after a deploy takes seconds (cold start + aggregation over 2.1 lakh rows).
**What:** precompute the dashboard aggregates (`/summary`, `/districts`) in `batch_assess.py` into summary
tables (new migration), read those in `api/routes.py`.
**Done when:** [ ] API tests cover the summary tables · [ ] results identical to the live aggregates on a
local load · [ ] timing before/after written in the log entry

### T003 · Harvest more evidence (one person at a time)  ·  M  ·  data  ·  **needs-owner** (picks the districts)
**Why:** the pilot is 837 works (Pratapgarh + 400 random). Photo, geo and document checkers need more
districts, and satellite needs large works with coordinates.
**What:** run `data/harvest/esakshi_evidence.py` for districts the owner picks, at the built-in polite rate
(never faster), then `data/trial/ocr_pages.py`. Add the new files to the team pack (tell the owner).
**Done when:** [ ] manifest lines added, no request faster than 1.5 s · [ ] OCR run · [ ] log entry lists
districts, works, files, MB and minutes · [ ] pack updated
**Label:** `needs-owner` until the owner names the districts.

---

## M1 — Document + Contractor (free local reading of certificates)  ·  target Oct wk 1–2

### T101 · Evidence tables + loader  ·  M  ·  engine + data  ·  Depends on: T100  ·  Data: evidence + OCR cache
**What:** migration for the evidence-derived tables (design §7: `evidence_files`, `doc_fields`,
`photo_hashes`, `overlay_geo`, `contractors`, `contractor_links`; create only what M1 needs, leave the rest
for their tasks) and `data/load_evidence.py` that fills them from `data/evidence/manifest.jsonl` + the OCR
cache. **Only derived facts go in the database** (dates, amounts, vendor code, file kind); never file bytes,
names or account numbers. The engine loads a work's evidence facts into the checker context.
**Done when:** [ ] migration + RLS tested with pgserver · [ ] loader is idempotent (run twice → same rows) ·
[ ] loads all 837 pilot works locally; counts in the log · [ ] a masking test proves account numbers never
reach a table

### T102 · Certificate reader in the engine  ·  M  ·  engine  ·  Depends on: T100
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

## M2 — Eligibility v2, split works, funded-twice  ·  target Oct wk 2–3

### T201 · A1 Eligibility v2 as a checker  ·  M  ·  engine  ·  Depends on: T100
**What:** today eligibility is a validation note (`validation/prohibited.py`, v1, 12% precision). Port v2 from
`data/trial/eligibility_trial.py` (`v2()` and its patterns: PDS shops, landmark-after-name, institution
names like Shishu Mandir, temple premises) into `agents/eligibility/`, raise it from note to finding, cite
the Annexure-II item.
**Done when:** [ ] flags 458 works on the corpus (±2%, explain any change) · [ ] the 50-work fresh sample
still gives ≥ 56% plainly prohibited, 80% worth a look (labels are in the trial script) · [ ] one test per
pattern, including the false-positive cases v2 fixed

### T202 · A2 Split works + bulk orders under the limit  ·  M  ·  engine + data  ·  Depends on: T100
**What:** from `data/trial/split_trial.py` (`bunching`, `identical_groups`): a data job precomputes groups;
the checker reads them from the context.
- same-site split: same named-site text, same district, same day, each piece just under ₹5 lakh
  (e.g. Nanded, 3 × ₹4,96,000 on 13 May 2025)
- bulk order under the limit: identical text, same district + work type, each within 60 days of the last,
  every piece ₹4–5 lakh, total over ₹5 lakh
- a group counts **once** in fusion (don't let 48 works each score high for one pattern)
**Done when:** [ ] reproduces 136 groups / 744 works · [ ] the Nanded group found · [ ] queue impact in
the log · [ ] test that a group adds one signal, not N

### T203 · A2 Same named asset funded twice  ·  S–M  ·  engine + data  ·  Depends on: T202
**What:** from `data/trial/dup_trial.py`: exact named-site text in the same district, recommended again
more than 60 days later while the first is still open. Exclude repairs/extensions/phases (`REPAIR` pattern).
**Done when:** [ ] reproduces the 48 pairs · [ ] the 19 hand-read "same asset" pairs are all flagged and the
9 no-real-site pairs are not (or FINDINGS updated with why) · [ ] tests

### T204 · Matching by meaning for reworded repeats  ·  L  ·  research + engine  ·  Depends on: T203
**Why:** exact wording finds 0 repeats after completion; real repeats are reworded.
**What:** try a free, local multilingual text-embedding model (store vectors with pgvector, already in
Supabase and pgserver). Candidates: same district, same work type, rare shared place names. **Kill
criterion:** if a hand-read sample of 50 top candidates has fewer than 1 in 3 real repeats, it stays off.
**Done when:** [ ] plan in `docs/plans/` · [ ] measured on a hand-read sample, numbers in FINDINGS · [ ]
shipped behind the kill criterion or documented as off

### T205 · Web: linked works on split/duplicate cards  ·  S  ·  web  ·  Depends on: T202
**Done when:** [ ] the card lists the other works in the group with links · [ ] screenshots in the PR

---

## M3 — Photo Forensics + Geo-Location  ·  target Oct wk 3–4

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

## M4 — Delay, Fund Flow, role dashboards  ·  target Nov wk 1–2

### T401 · C1 Delay: office track records + stuck works  ·  M  ·  engine + data  ·  Depends on: T100
**What:** from `data/trial/delay_trial.py` (`stuck_now`, `office_load`): per office, share of works
finished within a year vs the same period nationally; per work, "stuck" (recommended Apr 2023–May 2024 and
still not complete; split sanctioned-never-finished vs never-sanctioned). The model is only a ranking aid
(0.71 vs 0.68 for the office's record): never present it as a prediction.
**Done when:** [ ] reproduces 40,489 stuck works (₹2,178 cr), 37,658 / 2,831 split · [ ] wording test: no
"will be late" · [ ] tests

### T402 · C2 Fund Flow: sanction backlog + term-end leftovers  ·  M  ·  engine + data  ·  Depends on: T100  ·  Data: fund files
**What:** from `data/trial/fund_flow_trial.py` (`sanction_backlog`, `funnel`, `timing`): works waiting for
sanction past the clock (21,323 works, ₹1,361 cr, median 239 days); those recommended under a Lok Sabha term
that has ended (3,331, ₹169 cr). MP-level money is summed by term and **never scored per MP**. Compare
offices only with the same period nationally (the "March rush" was a portal cycle).
**Done when:** [ ] reproduces the figures above · [ ] tests · [ ] no MP name in any finding

### T403 · Role dashboards v1  ·  L  ·  web + engine  ·  Depends on: T002
**What:** Ministry = national picture + worst districts; District officer = their queue, map zoomed to their
district, office track records; Field = their inspection list. Role scoping exists already; keep it.
**Done when:** [ ] plan in `docs/plans/` · [ ] each role checked with the demo logins (owner shares them
privately) · [ ] screenshots in the PR

---

## M5 — AI reading (needs the owner's paid-key decision)  ·  target Nov wk 3

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

### T504 · Field app page (camera + GPS)  ·  M  ·  web  ·  Depends on: T503
**Done when:** [ ] works on a phone browser · [ ] submissions labelled `source = LIVE`

### T505 · D1 Citizen Verification demo  ·  S–M  ·  web  ·  Depends on: T302, T304
**What:** QR/link → simple form (photo + GPS) checked by B2/B3. eSAKSHI ratings are unused (21,789 of 21,793
are zero), so this is shown only as a **clearly labelled demo**.

---

## M6 — Decisions, finale  ·  target Nov wk 4 – Dec

### T601 · Fusion v2: conflict rules  ·  M  ·  engine  ·  Depends on: T103, T104, T201, T202, T302, T304
Rules (design §3): a reused photo voids progress confirmations; a bulk order counts once; satellite may only
withdraw a finding, never create one; plus R4–R6 from the design. One test per rule; score parts still add
up exactly.

### T602 · Inspection Planner  ·  M  ·  engine + web  ·  Depends on: T601
The District Authority's mandatory 10% of inspections: ~80% by risk × money, ~20% at random (keeps base
rates honest, deters gaming), grouped into day trips.

### T603 · Ask DRISHTI  ·  L  ·  engine + web  ·  Depends on: T601
Plain-language questions answered only from checked database queries; guideline answers quote the clause
verbatim; drafts inspection notes in English/Hindi. Needs T501 for the language model.

### T604 · B5 Satellite go/no-go (big works only)  ·  L  ·  research  ·  Depends on: T003
Only ponds, roads over 1 km, large buildings, and only with coordinates. Go/no-go test first: if built vs not
built can't be told apart on real sites, it stays off and the docs say so.

### T605 · Evaluation report + demo script  ·  M  ·  docs  ·  Depends on: T106, T203, T302, T304, T401, T402
One page per checker: target, measured result, kill criterion, known limits. A 5-minute demo walk-through
of the live site by role.

### T606 · Final deck  ·  M  ·  deck  ·  Depends on: T605
Deck sources: `docs/deck/`. Rules: pictorial, plain words, no file paths or test counts on slides, no
competitor talk except the one chart on the final References slide. Numbers only from FINDINGS.

---

## Adding a task

New work found? Add it here under the right milestone with the next free ID (`T206`, …), then create its
issue: `gh issue create --title "T206: <title>" --label ready --milestone "<milestone>" --body "Spec:
docs/team/TASKS.md, section T206"`. Mention it in your log entry.
