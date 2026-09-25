# DRISHTI — Full Working Prototype Plan

*A hosted, tested prototype built one milestone at a time. The product design is the SIH deck (`Downloads/SIH 2026 PPT.pdf`), unchanged.*

---

## 0. In plain words

**What you'll have:** one password-protected web link where you can:
- see about 2.1 lakh real MPLADS works on a dashboard and map, with the ones that need checking ranked at the top
- act as a **field officer**: take or upload site photos, type in your own words what changed since the last visit, and watch the four agents check it live
- act as a **district officer**: open a flagged work, see the evidence behind each alert (photos side by side, a map, a price comparison) and record a decision
- see how each agent scored on test data. The numbers are honest and include what it missed.

**How hosting works:**
- The link goes live at the first milestone (by 30 Sept) and only ever gets better.
- Each time an agent is fully built and tested, it's added to the live link.
- Unfinished work goes on separate preview links, so the main link always works when you need to show someone.

**Cost: ₹0.** Everything runs on free tiers:
- Vercel hosts the website.
- Supabase holds the database and photos.
- Google Gemini is the AI that reads the photos.

The free Gemini allowance covers roughly 100+ photo reports a day. If that ever limits you, one setting switches to a paid key.

**What you'll need to do (small, one-time; I'll prompt you at the right moment):**
1. Create a free Supabase project (about 2 minutes).
2. Create a free Gemini key at aistudio.google.com (about 1 minute).
3. Click "approve" if Vercel asks for access to the new private GitHub repo.

Later on: send me real site photos to replace the web ones.

| Milestone | Target | What goes live |
|---|---|---|
| **M0** | by 30 Sept | Live site, real data, dashboard, and the **Statistical agent** (price check) |
| **M1** | ~7 Oct | **Duplicate Project agent** (DIGIPIN "already funded here?") |
| **M2** | ~17 Oct | **Image Reuse agent** (reused photos and edits, including the GPS in photo data) |
| **M3** | ~31 Oct | **Site Progress agent** (the officer's own words checked against photos, plus GPS location check) |
| **M4** | ~15 Nov | **Full loop**: risk fusion, review queue, officer decisions, audit trail. This is the complete prototype. |
| **M5** | Nov–Dec | Finale polish: your real photos, Hindi screens, offline field capture, demo script |

---

## 1. Context

- **The goal:** a hosted, working prototype that does exactly what the deck promises, tested on real and web data, ready for anyone at any time.

- **Why not the current build?** `~/saakshya` is a research platform built with care, but it has a different shape from the deck:
  - five "layers" and about 28 detectors
  - a satellite layer
  - DuckDB
  - a static site export
  - photo-checking that has never been run with a real model

  Its best parts are proven and get **ported**, not rewritten:
  - DIGIPIN spatial index
  - duplicate checks
  - 256-bit photo fingerprints
  - the "a 'no' must repeat before it counts" controls
  - reliability-weighted fusion
  - the verified guideline clauses
  - the measured cost design (AD-106/107)
  - the hash-chained audit log

- **Guardrails from you (do not break):**
  - exactly the deck's pipeline and **four agents**
  - no added agents
  - **no satellite anything**
  - agents may gain facets
  - GPS/location validation lives **inside Site Progress and Image Reuse**
  - different technology from the deck is allowed

- **Decisions you've made:**
  - host at every milestone and keep building until December
  - free tiers now, with a paid-AI switch kept open
  - web photos now, your real photos later
  - a private GitHub repo

---

## 2. Product design, fixed by the deck

```
1 WORK ENTERS  ->  2 DATA VALIDATION  ->  3 FOUR PARALLEL AGENTS  ->  4 RISK FUSION  ->  5 RISK REVIEW  ->  6 OFFICER VERIFICATION
 (records,          (clean + check)        01 Site Progress           (combine by         (ranked queue,     (evidence -> decision,
  claims, photos)                          02 Image Reuse              confidence +        Low/Med/High)      audit, feedback)
                                           03 Duplicate Project        evidence)
                                           04 Statistical                                        -> DASHBOARD (results & insights)
```

**Where each anomaly class on the deck's second slide is handled:**

| Deck anomaly (slide 2) | Handled by |
|---|---|
| Financial: unusual costs, spending, cost–progress mismatch | 04 Statistical |
| Timeline & progress: delays, reported-vs-observed gaps | 01 Site Progress (observed) + 04 Statistical (delays, money ahead of site) |
| Geographic: location mismatch, boundaries | 2 Data Validation (pin inside district/constituency) + 01 Site Progress (photo GPS vs site) + 02 Image Reuse (photo-data GPS/time anomalies) |
| Record inconsistencies | 2 Data Validation (impossible dates, prohibited works, missing fields) |
| Pattern & evidence: repeated projects, reused images | 03 Duplicate Project + 02 Image Reuse |

**Principles carried over:**
- **Never accuse.** Outputs say "needs verification", backed by a banned-word test.
- **Every alert links to its evidence.**
- **"Can't tell" / NOT_ASSESSABLE is never a clean chit.**
- **AI never decides alone.** The model judges individual photos and claims; fixed code applies the controls and does the scoring.
- **Score works and agencies, never MPs.**
- **Every decision is logged.**
- **Real data, planted scenarios and live submissions are always labelled.** They are never mixed silently.

---

## 3. Architecture and stack

```
Browser / phone (PWA)
   │  same origin: drishti-*.vercel.app
   ▼
Vercel project "drishti" (Services)
 ├─ web    : Next.js 16 (App Router, TS, Tailwind v4, shadcn/ui, MapLibre GL, Recharts)
 └─ engine : FastAPI (Python 3.12) at /api/v1/*
      prepare → validate → [4 agents in parallel, asyncio] → fuse → persist
   │                                   │
   ▼                                   ▼
Supabase (Mumbai, ap-south-1)       Google Gemini API (free tier; model auto-discovered)
 Postgres + pgvector (bit(256) photo fingerprints, Hamming search)
 Storage (private "photos" bucket, signed upload/read URLs)
 Auth (email+password, roles in `profiles`)
```

| Deck tech | Prototype | Why |
|---|---|---|
| Next.js, React, MapLibre | same | — |
| Python, FastAPI | same (Vercel Python service) | — |
| eSAKSHI APIs | eSAKSHI **public export** adapter (210k works) | The API needs ministry access. The adapter is the drop-in point. |
| PostgreSQL, pgvector | Supabase Postgres + pgvector (photo-hash similarity search) | Free and managed |
| PostGIS | DIGIPIN cell index in Postgres + Shapely boundary checks in the engine | Testable locally without Docker; PostGIS can be switched on later |
| Pandas, scikit-learn, PyOD | Pandas offline (cohorts, sweeps); PyOD optional, offline (M5) | Keeps the hosted engine small |
| OpenCV, pHash | OpenCV (DCT, ORB feature matching), 256-bit pHash + dHash | Proven in the old repo |
| PyTorch | not needed at runtime | Gemini + OpenCV cover vision |
| Gemini API / Qwen3-VL | Gemini behind a pluggable provider; Qwen3-VL as a later self-hosted option (M5, optional) | Free tier now |
| DIGIPIN, GeoPandas | DIGIPIN (ported, checked against India Post's published code); GeoPandas offline for boundaries | — |
| Sentinel-2 | **removed** | Your decision: no satellite |
| Redis, Celery | Postgres `runs` table + agents run in parallel inside the request | Serverless-friendly, fewer moving parts |
| MinIO | Supabase Storage (S3-compatible, same role) | Free and managed |

### Repo layout: new private repo `github.com/Phoenix-techstuf/drishti`, local at `~/drishti`

```
apps/web/                 Next.js app (pages below)
apps/engine/drishti/
  main.py                 FastAPI app, /api/v1 routes
  pipeline/               orchestrator, run records, timeouts
  prepare/                EXIF, derivatives, fingerprints, DIGIPIN, district lookup
  validation/             record checks, guideline eligibility, boundary checks
  agents/contract.py      AgentResult / Finding / Evidence types (shared by all 4)
  agents/site_progress/   claims.py, verify.py, location.py, address.py, prompts/
  agents/image_reuse/     fingerprint.py, search.py, verify_orb.py, metadata.py
  agents/duplicate_project/ digipin.py, footprint.py, text.py, agent.py, sweep.py
  agents/statistical/     cohort.py, band.py, bulk.py, unit_rate.py, ceilings.py, timeline.py
  fusion/                 fuse.py (weights, caps, conflicts, bands), reliability.py
  vision/                 provider.py (Gemini, fallback chain, quota ledger, cache/replay)
  geo/                    boundaries (Shapely STRtree), haversine
  storage/, db/ (psycopg3 + SQL migrations), audit/ (hash chain), reference/ (YAML taxonomies)
apps/engine/tests/        pytest (unit + integration on pgserver = real Postgres+pgvector, no Docker)
data/                     offline pipelines: ingest, boundaries, gazetteer, cohorts, photo harvest, scenarios, seed
eval/                     labelled test sets + runners → JSON → Evidence page
docs/                     specs/, plans/, STATUS.md (RESUME HERE), DEMO.md, evaluation/
vercel.json               services: web "/" ; engine "/api/v1/(.*)" ; daily keep-alive cron
```

### Hosting and free-tier limits

| Limit | Mitigation |
|---|---|
| Vercel Hobby: 300 s per request | Pipeline target under 60 s. Each agent has a 240 s timeout; on timeout the agent returns ERROR/CANT_TELL. |
| Vercel request bodies capped at 4.5 MB | Photos go **directly to Supabase Storage** via signed upload URLs from the engine |
| Supabase free: 500 MB database | Lean schema. Full evidence is stored only for flagged works; unflagged real works keep a compact summary and are recomputed on demand (under 1 s). Size is measured after each load. |
| Supabase free: 1 GB storage | Stored photos are about 300 KB derivatives (1600 px long side, EXIF preserved). Originals are discarded after extraction. |
| Supabase free: pauses after 7 idle days | Daily Vercel cron hits `/api/v1/health/keepalive`, which touches the database |
| Gemini free quota | See §7.5 (quota guard, model fallback chain, cache, "pending" state) |

If Vercel Services isn't available on Hobby, the fallback is the documented `api/index.py` + Next.js rewrites pattern, using the same code.

**Security:**
- Keys live only in Vercel/Supabase environment variables, never in git.
- Every table has RLS enabled with no public policies; only the engine reads the database.
- Supabase JWT is verified by the engine (JWKS).
- Access is scoped by role: field officer = own works; district officer = own district; ministry = all.
- Per-user daily caps apply on AI-consuming endpoints.
- Uploads are limited by file type and size.
- Signed URLs expire in 10 minutes.

---

## 4. The pipeline in detail

**Intake types:**

| Type | Trigger | What runs |
|---|---|---|
| RECORD | A new work is recommended (form with a map pin or DIGIPIN) | 03 and 04 run; 01 and 02 show "waiting for first site report" |
| REPORT | Progress report: photos + "what changed" + optional stage/% and expenditure | All 4 agents |
| BATCH | Offline sweep over the real corpus | Validation, 03 (text axis), 04 |

**Prepare** (the deck's "Data Processing") covers:
- downloading uploaded photos
- EXIF extraction: time, GPS, make/model, software
- derivatives
- SHA-256 + pHash-256 + dHash + five crop-variant hashes
- work pin → DIGIPIN
- pin → district/constituency (Shapely)

**Data Validation:** each issue is marked BLOCK, WARN or INFO. WARNs feed fusion as a small, capped input (at most 0.30).
- required fields and valid values
- impossible dates, e.g. completed before recommended. This reuses the old quarter-cohort weighting from `core/rules/lifecycle.py` and the era gate from `core/era.py`.
- prohibited works with clause citation (`contracts/prohibited_works.yaml` and its exceptions)
- pin inside the declared district and constituency (Rajya Sabha MPs: the state)
- outside-constituency ceiling of ₹25 lakh (para 2.9, verified clause)
- photo count, types and size

**Agent contract** (`agents/contract.py`), returned by every agent:
- `status`: ASSESSED / NOT_APPLICABLE / NOT_ASSESSABLE / ERROR
- `verdict` (an agent-specific enum)
- `risk` 0–1 and `confidence` 0–1
- `hard` (a direct contradiction or fact) vs soft (statistical unusualness)
- `headline` (plain English, no banned words)
- `findings[]`, each with `evidence[]` (photo pair, map points, cost band, claim table)
- `limitations[]`, `model_id`/`origin`, `duration_ms`, `version`

**Orchestration:**
1. `POST /reports` (or `/works`) creates a `run` (QUEUED).
2. The UI calls `POST /runs/{id}/execute`. This long request runs prepare → validate → `asyncio.gather` of the 4 agents (CPU work in threads) → fuse.
3. Each stage is written to the database as it finishes.
4. Meanwhile the UI polls `GET /runs/{id}` every second, so the agent cards light up live (deck-style).
5. A run stuck for more than 5 minutes can be re-run. Agents are idempotent.

---

## 5. The four agents

Each agent's UI card mirrors its panel on the deck's Technical Approach slide, using the deck's colours:
- 01 green `#70C6AB`
- 02 purple `#9469E5`
- 03 pink `#EF558A`
- 04 orange `#F48137`
- fusion teal `#2FB0AE`

### 01 Site Progress Agent: "Does the site evidence match the claimed progress?" (M3)

**Facets:**

1. **Claim check (core; your framing, never a checklist).**
   - The report asks: *"What changed since the last report? Name what was built, in your own words."* Any Indian language is accepted.
   - Gemini call A (text only) splits the answer into atomic claims, each tagged exterior-visible / interior / quantity / non-visual.
   - The reported stage or % also becomes a claim. For example "2nd floor complete" reproduces the deck's "Claim: 2nd floor / Actual: 1st floor".
   - Gemini call B looks at all photos and judges each claim: **SHOWN / NOT_SHOWN / CANT_TELL**, with the photo numbers, a ≤25-word observation of what it sees instead, and a confidence.
   - Output is structured JSON via `response_schema`, at temperature 0.
2. **What changed vs the last visit.** When a previous report exists, up to 4 of its photos go in as the "BEFORE" set. The model judges whether each claimed change is visible between before and after.
3. **Controls, ported from `core/field/verify.py`.** This asymmetry matters because a wrong "no" is an accusation.
   - A NOT_SHOWN must hold on **both repeats** (the second repeat uses a shuffled photo order) **and on each half** of the photo set (only asked if a NOT_SHOWN exists). Otherwise it becomes CANT_TELL.
   - Interior claims can never be NOT_SHOWN from exterior photos.
   - A provider failure produces CANT_TELL plus a limitation, never a finding.
   - Photo text is scene content, never instructions (prompt-injection guard).
   - Normal cost is 3 calls (up to 5).
4. **Location check (GPS).**
   - The best fix per photo is chosen from:
     - the **device GPS at capture** (live in-app camera, with accuracy radius)
     - EXIF GPS (camera or desktop uploads, and web photos)
     - mobile browsers often strip EXIF GPS, which is why live capture is the primary source
   - Checks:
     - distance to the work's footprint (pin, or corridor for roads)
     - inside the district polygon
     - photo time within the reporting window (not before sanction, not before the last report, not in the future)
     - spread of the photos (all at one site?)
     - consistency with previous visits' centroid
     - device GPS vs EXIF disagreement
   - Verdict: **AT_SITE / NEAR_SITE / ELSEWHERE / OUTSIDE_DISTRICT / NO_LOCATION**, shown on a map.
   - If a work has no pin, the first live report with high accuracy can propose a **site anchor**, which the district officer confirms.
5. **Address check.** The photo location is reverse-geocoded to the nearest place name (precomputed OSM gazetteer where available, otherwise cached Nominatim) and compared with the villages or landmarks named in the work description.
6. **Photo relevance and quality.** Does each photo show this type of work at all? Is it too dark, blurry or blocked? Poor quality leads to "request better photos", never a finding.

**Risk (initial values, tuned on the dev split):**

| Finding | Type | Risk |
|---|---|---|
| Stable contradicted claim | hard | 0.60, then +0.12 each, capped at 0.85 (one stable contradiction can reach HIGH on its own: the deck's "2nd floor claimed / 1st floor seen" case) |
| ELSEWHERE | hard | 0.60 |
| OUTSIDE_DISTRICT | hard | 0.75 |
| Photos don't show this work type | stable | 0.50 |
| Mostly CANT_TELL | soft | 0.15 |
| NEAR_SITE | soft | 0.20 |
| Address mismatch | soft | 0.20 |
| NO_LOCATION | soft | 0.10, and lowers confidence |

**Output:** Site Risk Score, a claim table with photo thumbnails, the location map, and the what-changed summary.

### 02 Image Reuse Agent: "Has the same image appeared elsewhere?" (M2)

**Facets:**

1. **Exact:** SHA-256 of the pixels.
2. **Near-duplicate:** 256-bit pHash + dHash (`core/vision/hashing.py`, which measured 64-bit hashes as failing at national scale). Stored as pgvector `bit(256)` with an HNSW Hamming index, so the deck's "Similarity Search" is literally a pgvector query. The fallback is `bit_count(a # b)`.
3. **Crops and partial reuse:** five crop-variant hashes per photo (centre 60% + four quadrants) are matched both ways. The top candidates are then confirmed with **OpenCV ORB + RANSAC** (inlier count; matched points are drawn for the officer).
4. **Photo data (EXIF) checks** (the deck's "mismatches and edits", GPS integrated):
   - capture time before sanction or before the previous report → stale photo
   - editing software tag (Photoshop, Snapseed and others)
   - the same capture time + camera across different works → one photo shoot reused
   - EXIF GPS in another district
   - metadata stripped (info only; common with WhatsApp)
   - the same photo twice within one report
5. The search covers **all photos nationally**. That's the point: cross-district reuse is invisible to reviewers who each see only their own district.

**Wording:** officers see a **"difference score"** (lower means more alike; your wording), plus "N matching points".
- Starting threshold: 48 on the 256-bit hash, dHash 22 (from `docs/visual/photo_reuse.json`: a copy scored 10, different houses scored 118–150).
- The threshold is recalibrated on the new test set.

**Verdicts:**

| Verdict | Type | Risk |
|---|---|---|
| REUSED_FROM_OTHER_WORK | hard | 0.80 |
| RESUBMITTED_FROM_EARLIER_REPORT (no new photo) | hard | 0.50 |
| STALE_PHOTO | hard | 0.50 |
| EDITED | soft | 0.20 |
| DUPLICATE_WITHIN_REPORT | soft | 0.10 |
| NO_MATCH | — | — |
| NOT_APPLICABLE | — | — |

**Output:** a Reuse Alert, shown side by side with "Uploaded: <date> / Found in previous work <id>: <date>" as on the deck.

### 03 Duplicate Project Agent: "Is a similar work already recorded nearby?" (M1)

This ports `core/duplicates/*` from DuckDB to Postgres, keeping every measured gate:
- compatible work types only
- the earlier work must be SANCTIONED / IN_PROGRESS / COMPLETED
- amount ratio ≥ 0.6
- completed more than 5 years ago counts as renewal
- delivery points (ambulances, computers) never overlap

**Facets:**

1. **DIGIPIN → spatial matching.** Level-8 cells (about 60 m) are held as indexed text prefixes. Footprints are only as large as the reported size.
2. **Nearby works within 2 km**, for context and the deck's map ("Previous work, 1.2 km away").
3. **Text axis for the real corpus**, which has no coordinates: works whose descriptions name rare places, the same district, compatible type, concept-set overlap ≥ 0.55. This is capped at 0.45: it shows resemblance, not proof.
4. **Batch sweep** over the real corpus (port of `RepeatedRecommendation`, measured at 429 clusters / 899 works). Bulk orders are excluded by cluster size.
5. **Pilot-district approximate pins.** A gazetteer (OSM places ± LGD names) is matched to village names in descriptions. The pins are "village precision": they can only ever produce PRIOR_WORKS_NEARBY, never an overlap finding.
   - Pilots are 2–3 districts, chosen for the most works and the highest share of descriptions naming a village (both measured).
   - Your home district is added in M5 when your real photos arrive.
   - Coverage (% pinned) and a hand-checked 50-work precision sample are reported.

**Verdicts** (unchanged, the fourth is the design): **OVERLAPPING_PRIOR_SANCTION** (hard when the work is declared NEW) / PRIOR_WORKS_NEARBY / NO_PRIOR_FOUND / **NOT_ASSESSABLE**.

A declared REPAIR / EXTENSION of the matched prior is not a contradiction.

**Output:** a Duplicate Alert, a map with current, previous and potential-duplicate markers plus distances, and the records compared side by side.

### 04 Statistical Agent: "Is the project cost unusual for similar works?" (M0)

This builds the already-measured design in `docs/specs/2026-09-09-cost-reasonableness-design.md` (AD-106/107). Constants are not re-derived.

**Facets:**

1. **Cost vs peers:**
   - Log-cost band per `work_type × district`, backing off to state, then national (n ≥ 20).
   - Uses the p10–p90 spread (MAD collapses on round amounts), shrunk toward the type's spread: K=12, floor 0.10.
   - Flags z ≥ 3. The measured flag rate is 1.20% above peers.
2. **Bundle reading:** a description naming a count or a list gives **BUNDLED_SANCTION**. This is a governance note, not a mispricing.
3. **Unit rate** when a quantity is known (from the form, or parsed from the description, about 7% of the corpus):
   - fitted scale curves, e.g. ROAD_CC cost ≈ ₹34,522·len^0.631 (n = 4,065)
   - published rate anchors, e.g. rural CC road at ₹4,000–6,500/m
   - this gives the deck's "₹/km vs typical range, +56%" table
4. **Ceilings** (the only hard statistical signals, with verified clauses): outside-constituency above ₹25 lakh (para 2.9); an MP's yearly total above the ₹5 crore entitlement (para 2.1).
5. **Timeline:** in progress beyond the 98th percentile of duration for its work type (the median is 392 days on real data).
6. **Money ahead of site:** reported expenditure % minus the last *verified* progress (from a previous Site Progress run) is more than 40 points. This returns NOT_APPLICABLE until Site Progress exists (M3), and the card says so.

**Verdicts:** COST_TYPICAL / COST_ABOVE_PEERS / COST_BELOW_PEERS / BUNDLED_SANCTION / CEILING_BREACH / DELAYED / MONEY_AHEAD_OF_SITE / NOT_ASSESSABLE.

Everything cohort-derived is **soft and capped at 0.45**: *it can say an amount is unusual, not that it is wrong*.

**Output:** a Cost Risk Score, the deck's comparison table (metric / this work / typical range / deviation) and a band chart.

### Location ownership: every geo check counts exactly once in fusion

| Check | Owner |
|---|---|
| Work pin inside district/constituency, ₹25 lakh ceiling | Data Validation |
| Photo GPS vs the site, in-district, address, time window, cross-visit | 01 Site Progress |
| Photo data anomalies: stale timestamp, editing software, same shoot reused, EXIF GPS in another district | 02 Image Reuse. EXIF-GPS distance is used only when Site Progress had no location. |
| Nearby and overlapping prior works | 03 Duplicate Project |

---

## 6. Risk fusion, review, officer verification, dashboard

**Fusion** (ported from `core/fusion/case_builder.py` and `calibration.py`):

1. Per agent: `w = risk × confidence × reliability(agent)`, with soft findings capped at 0.45.
2. **Score = the strongest `w` + 0.45 × the sum of the others' `w`** (the old measured corroboration uplift), capped at 1.
3. The parts **add up exactly to the score**, and the UI shows them as bars.
4. Reliability is a Beta posterior:
   - The prior comes from each agent's measured evaluation precision (strength 20).
   - It is updated from officer decisions (confirmed vs dismissed), so **the queue improves with use** (deck slide 5, "Continuous Model Improvement").

**Conflict rules** (deck challenge: "Conflicting Signals"; each one tested):

| Rule | What happens |
|---|---|
| R1 | Photos reused, taken ELSEWHERE, or stale → Site Progress confirmations are **voided** ("verified on photos that can't be trusted"). The photo finding carries the weight, and it isn't double-counted. |
| R2 | Location counts once (ownership table above) |
| R3 | A bulk sanction flagged by both the text sweep and the cost check is one finding |
| R4 | A declared repair/extension of the matched prior downgrades the duplicate |
| R5 | Agents that disagree are shown as "conflict: both sides". The officer decides. |

**Bands** (deck: Low/Medium/High):
- HIGH at 0.60 or above, or any single **hard** finding whose own risk is ≥ 0.60 at confidence ≥ 0.70. Those are: reused photo, photos taken ELSEWHERE / OUTSIDE_DISTRICT, a stable contradicted claim, an overlapping prior sanction, a ceiling breach. A stale photo (0.50) alone stays MEDIUM.
- MEDIUM at 0.30 or above
- LOW otherwise
- "LOW (limited evidence)" when two or more agents couldn't assess

**Priority** = score × money weight (log ₹).

**Risk Review (step 5):** the queue shows MEDIUM and HIGH, filterable by district, band and agent. Statuses: NEW → IN_REVIEW → EVIDENCE_REQUESTED / FIELD_VISIT → CLOSED. Cases can be assigned to officers.

**Officer Verification (step 6):**
- The case page shows every agent's evidence.
- The officer's decision is one of: **Confirm issue** (action: stop payment / field inspection / notice to agency), **Dismiss (false alarm, reason)**, or **Request fresh evidence**. The last one creates a task for the field officer.
- The officer gives per-agent "was this alert right?" feedback, which feeds reliability.
- Everything goes into the **hash-chained audit log** (port of `core/db.py`), with a "verify chain" button.

**Pages:**

| Page | Contents |
|---|---|
| Login | Three demo roles |
| **Dashboard** | KPIs, India map (district choropleth + pinned works), band distribution, 4 agent cards with alert counts, top-priority list, "Found in real eSAKSHI data" vs "Demo scenarios" panels |
| Works | Search and list |
| **Work / case page** | Record, timeline, 4 agent cards, fusion bars, photos with location/time/reuse badges, map, decision panel, audit |
| **Field report** | Mobile-first: works near my GPS, live camera with location lock or upload, "what changed" box, live agent view |
| **New work check** | Map pin or DIGIPIN; runs 03 and 04 before sanction |
| Queue | The review queue |
| **Evidence** | Measured accuracy per agent, generated from eval JSON, never hand-typed |
| How it works | The deck's pipeline, animated |
| Audit | The audit log |

**Maps:**
- National and state views draw **India's official boundaries from LGD 2024** on a plain background, with no third-party borders.
- Zoomed views use OpenFreeMap (OSM) street tiles with country-border layers hidden.

---

## 7. Data

1. **Real corpus.**
   - Source: `~/saakshya/data/raw/inrolls/works_{ls17,ls18,rs}.csv` (the eSAKSHI export, 209,993 works). Ingested via the ported `ingest/adapters/esakshi.py`, `lgd.py` and `lgd_aliases.py`.
   - It has: type, description, amounts, dates, status, district, MP and agency.
   - It has **no** coordinates, quantities or photos. The UI says so ("the fix is an export, not a model").
   - Each work's source badge is `REAL`.
2. **Reference data:**
   - taxonomy (`contracts/work_types.yaml` / `work_categories.yaml`, satellite fields removed)
   - prohibited works + verified guideline clauses
   - LGD 2024 district/state and 543 constituency polygons (India Geodata / DataMeet), simplified, bundled in the engine and served as TopoJSON to the web
   - pilot-district gazetteer (OSM Overpass, cached)
3. **Web photo library (M2).**
   - About 300 CC-licensed Wikimedia Commons photos of MPLADS-type works in India: roads, halls, school rooms, street lights, handpumps, tanks, toilets, drains, bus shelters.
   - The originals are downloaded **with EXIF/GPS**.
   - Author, licence and URL are stored and shown on every photo.
   - Photo series (same site on different dates) are found automatically: clustered by author and location.
   - I label what each photo shows, independently of Gemini, so the test isn't the AI grading itself.
4. **Scenario works (M2–M3).**
   - About 40–60 records placed **at the real GPS locations of those photo series**, with amounts drawn from the real cohort of that district.
   - Planted issues: reused photo, photos taken 30 km away, false claim, stale photo, duplicate sanction, inflated cost, bulk order, and clean controls.
   - Badge `DEMO SCENARIO — planted: <issue>`. The answer key is in `scenario_truth`, used only by evaluation.
   - Real works never get fake photos.
5. **Gemini on the free tier:**
   - The default is the best available **Flash-Lite** model, auto-discovered (roughly 500 requests a day per model as of Sept 2026; the real limits are shown in AI Studio).
   - A **fallback chain** across free models kicks in on quota exhaustion.
   - A per-day **ledger** tracks usage.
   - An **identical-input cache** means seeded demos cost nothing and tests replay recorded responses.
   - When quota runs out, reports show "Site check pending, runs when the daily AI allowance resets", never a fake answer.
   - `DRISHTI_VISION_TIER=paid` switches to Flash with 3 repeats later.
   - Every result records the model that produced it.
   - Caveat: free-tier inputs may be used by Google. That's fine for web photos; production would use a paid tier or self-hosted Qwen3-VL (stated on the capture page, wording ported from `contracts/declaration.yaml`).

---

## 8. Testing and evaluation

- **TDD for every module** (superpowers:test-driven-development).
- Engine tests run on **pgserver**: real Postgres + pgvector, pip-installed, no Docker. The same SQL runs as on Supabase.
- Ported regression tests:
  - DIGIPIN, including the India Post published-code check
  - footprint, text specificity
  - the six duplicate scenarios
  - hashing
  - verify asymmetry
  - the banned-word scan
- Web: typecheck, lint, build, plus key component tests.
- CI: GitHub Actions.

**Per-agent evaluation sets:**
- Tuned only on a **dev split**.
- Reported only on a **held-out split** (the old project's leakage lesson).
- Targets aren't promises; misses are published.

| Agent | Test set | Target |
|---|---|---|
| 04 Statistical | 500 held-out real works with amounts inflated ×1.5/×2/×3/×5; untouched corpus for flag rate | ×3 caught in ≥80%, flag rate ≤1.5% |
| 03 Duplicate | Six geometric scenarios; 100 planted reworded duplicates of real works; 500 random real works | Planted duplicates found ≥80%, random works flagged ≤2% |
| 02 Image Reuse | About 200 originals × 9 edits (resize, recompress q50, crop 70/50%, brightness, rotate 5°, flip, screenshot border, text overlay); all distinct pairs; same-site-different-visit pairs | Resize/recompress ≥95%, 70% crop ≥80%, distinct pairs ≤1% false alarm, same-site visits not called reuse |
| 01 Site Progress | About 60 photo sets / 150+ claims (true, false, vague, interior, out-of-scope, Hindi) from labelled web photos; about 40 location cases (at site, 300 m, 5 km, 50 km, no GPS, stale, EXIF vs device) | False claims caught ≥70%, **true claims wrongly contradicted ≤5%**, location cases 100% |

**End-to-end:**
- A **scenario pack of about 20 works**, one per agent issue, combinations, conflicts and clean controls, each with an expected band.
- It runs in CI with recorded model responses, and live once per milestone.
- A **Playwright smoke test** against the hosted URL: login → submit report → agents finish → decision → audit entry.
- **The Evidence page** is generated from `eval/results/*.json`.

---

## 9. Milestones: each one ends deployed to production and verified

**M0: Foundations + Statistical agent (by 30 Sept)**

Build:
- Snapshot-commit `~/saakshya`'s uncommitted work locally, so two weeks of work is safe. No push.
- Create `~/drishti` and the private GitHub repo.
- Save this plan as `docs/specs/2026-09-25-drishti-prototype-design.md` + `docs/STATUS.md` (RESUME HERE), and commit.
- Set up Vercel project + Services, Supabase project (Mumbai), migrations, Auth + 3 demo users, and CI.
- Ingest the real corpus.
- Taxonomy/LGD mapping.
- Cohort, duration and unit-rate tables.
- Pipeline skeleton with 4 agent slots (unbuilt agents show "in development").
- Data Validation v1.
- **Statistical agent complete.**
- Fusion v1.
- Batch run over the real works.
- Dashboard, works search, work page with the Statistical card, queue, How-it-works.
- Keep-alive cron.

*Show:* the live link with 2.1 lakh real works ranked by price checks and record issues.

**M1: Duplicate Project agent (~7 Oct)**

Build:
- DIGIPIN/footprint/text/agent ported to Postgres.
- Batch text sweep on real data.
- New-work check page with map pin and DIGIPIN.
- Pilot gazetteer pins with a hand-checked precision sample.
- Duplicate map card.
- Evaluation.
- **A Gemini spike:** 10 labelled photo cases on the free models, to pick the model and de-risk M3 early.

*Show:* "this recommendation overlaps work X, already sanctioned".

**M2: Image Reuse agent (~17 Oct)**

Build:
- The photo pipeline: signed uploads, EXIF, derivatives, fingerprints in pgvector.
- ORB verification and EXIF checks.
- Commons library harvest with attribution.
- Field report page (upload mode).
- First scenario works.
- Reuse evaluation.

*Show:* upload a resized or cropped old photo and get caught, with both dates.

**M3: Site Progress agent with GPS (~31 Oct)**

Build:
- Claims → verification with the controls.
- Before/after judgment.
- Location and address facets, live camera + device GPS capture.
- Provider fallback chain, ledger and cache.
- Remaining scenario works and series.
- Claim and location evaluations.

*Show:* type "roof slab cast" on photos with no roof, get NOT_SHOWN with the photo evidence; photos taken 38 km away get flagged.

**M4: Full loop, the complete prototype (~15 Nov)**

Build:
- Fusion conflict rules and reliability from decisions.
- Review workflow, decisions, audit chain, role scoping.
- Dashboard insights and agent-performance panel.
- Evidence page.
- Scenario pack + Playwright smoke.
- `docs/DEMO.md`, a 5-minute judge walkthrough.

*Show:* the whole deck, end to end.

**M5: Finale polish (Nov–Dec)**

Build:
- Your real photos: evaluation + demo pilot district.
- Hindi UI toggle.
- Offline-capable field PWA (queue and sync).
- Performance and security review (`/security-review`).
- Backup demo video.

Optional:
- paid-model mode
- Qwen3-VL provider
- PyOD/ECOD portfolio sweep
- face blurring

**An agent counts as "fully built" when:**
- all its facets are working in the hosted pipeline
- its UI card matches the deck
- its evaluation has run, with results on the Evidence page
- tests are green
- it's deployed to production
- STATUS and memory are updated
- you've had a plain-words update with the link and what to try

---

## 10. How I'll execute

**For each milestone:**
1. Write its task-level plan (superpowers:writing-plans) to `docs/plans/Mx-*.md` and commit it, so an effort switch loses nothing.
2. Build it inline, TDD (your preference, no subagents).
3. Verify (superpowers:verification-before-completion).
4. Merge the feature branch to `main` → production deploy.
5. Run the smoke test on the live URL (Playwright MCP).
6. Update the `docs/STATUS.md` RESUME HERE block and the DRISHTI memory (old research build = `~/saakshya`; new prototype = `~/drishti`).
7. Give you a plain-words update.

**Branches:** `main` is always the demoable live link. Feature branches get Vercel preview links.

**Your actions** (I'll ask exactly when needed):
- Supabase project (or the Vercel-Marketplace Supabase integration, which injects keys automatically)
- Gemini key, added in the Vercel dashboard (never pasted into chat or git)
- approving Vercel's GitHub access
- later: real photos

---

## 11. Reuse map: old → new (`~/saakshya` → `~/drishti/apps/engine/drishti`)

| Old | New |
|---|---|
| `core/duplicates/digipin.py` + `tests/test_digipin.py` | `agents/duplicate_project/digipin.py` (also used by `prepare/`) |
| `core/duplicates/footprint.py`, `core/geo/router.py` (`_box_aoi`, `_corridor_aoi`, `load_taxonomy`, `work_type_index`) | `agents/duplicate_project/footprint.py`, `reference/` |
| `core/duplicates/text.py`, `core/similarity/normalise.py` | `agents/duplicate_project/text.py` |
| `core/duplicates/agent.py`, `store.py`, `detectors.py::RepeatedRecommendation`, `scripts/demo_duplicates.py` | `agent.py`, `sweep.py`, tests |
| `core/vision/hashing.py`, `docs/visual/photo_reuse.json` (thresholds) | `agents/image_reuse/fingerprint.py` |
| `core/vision/provider.py` (model discovery, 429 retry, provenance) | `vision/provider.py` |
| `core/field/verify.py` (repeats + halves asymmetry) | `agents/site_progress/verify.py` |
| `contracts/declaration.yaml` (form and privacy wording) | field report page copy |
| `core/fusion/case_builder.py`, `calibration.py` | `fusion/` |
| `contracts/prohibited_works.yaml`, `guidelines_clauses.yaml`, `core/guidelines.py`, `core/era.py`, `core/rules/lifecycle.py` | `validation/` |
| `docs/specs/2026-09-09-cost-reasonableness-design.md`, `docs/visual/analyse_costs.py` | `agents/statistical/` |
| `ingest/adapters/esakshi.py`, `lgd.py`, `lgd_aliases.py` | `data/ingest/` |
| `core/db.py` audit chain | `audit/` |

---

## 12. Verification: how we'll know it works

- **Engine:** `pytest` is green, including pgserver integration and the ported regression tests.
- **Evaluation:** `python -m eval.run --agent <name>` meets or reports against the targets in §8, on held-out data.
- **Scenario pack:** each of the ~20 works lands in its expected band. Conflict rules R1–R5 each have a passing test.
- **Hosted:**
  - The Playwright smoke run passes on the production URL after every deploy.
  - A manual walkthrough of `docs/DEMO.md` works on a phone (live camera + GPS) and on a laptop.
- **Free-tier health:**
  - database size under 400 MB, measured after each load
  - storage under 800 MB
  - keep-alive cron logs a daily hit
  - the quota ledger shows headroom

---

## 13. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Free Gemini quota is tight or changes without notice | Flash-Lite default, fallback chain, cache/replay, honest "pending" state, paid switch ready |
| Phones strip EXIF GPS from uploads | Live in-app capture records device GPS + accuracy at the shutter; EXIF is a bonus |
| Vercel Services not on Hobby | Documented `api/index.py` + rewrites fallback, same code |
| Supabase free limits or pausing | Lean schema, derivatives only, keep-alive cron, size checks; Pro is a one-click upgrade if you choose |
| Showing "risk" beside real named works | Login-only, "needs verification" wording, banned-word test, no MP scoring, source badges |
| India map-boundary sensitivity | Official LGD outline at national zoom; no third-party borders |
| The model misreads photos and wrongly contradicts a claim | Repeats + halves control, interior exemption, ≤5% target measured on held-out data, officer always decides |
| Web-photo licensing | Commons CC licences only, attribution stored and shown |
