# DRISHTI v2: the full-agent product

*Replaces the 4-agent design (the user lifted that limit on 2026-09-25). The architecture and the M0 build (`~/drishti`) carry over; the product scope does not.*

---

## 0. In plain words (for you)

**What changes:** DRISHTI goes from 4 agents to **12 agents in 4 stages of a work's life**, plus **4 decision tools**.
- Every agent checks a **different kind of problem** that auditors have actually found in MPLADS.
- Every agent uses a method **already proven in India or in industry**.
- Every agent must pass its own test before it goes live. An agent that fails stays switched off.

**The discovery that makes us different:** the public eSAKSHI dashboard (the dataset MoSPI names in the problem statement) serves the **real documents and photos** behind each work. I found:
- completion certificates showing the sanction order number and date, the real cost, the contractor's name and the handover date
- handwritten Hindi utilisation certificates
- site photos with the **GPS location and time stamped into the picture**

We test on the government's own evidence.

**What sets the approach:**
1. Real evidence from eSAKSHI itself.
2. A measured accuracy figure for every agent.
3. Every method measured on real data against an accuracy target.
4. Checks at every stage: before sanction, during work, on money and time, after completion.

**Next steps:**
1. Put the current version online (needs your `npx supabase login`).
2. You send the style deck, and I turn this plan into slides.
3. I build agent by agent, putting the site online at each milestone.

**Cost:** free for the first real-evidence test (about 500 works). After that, a small paid AI key (roughly ₹200–500 for 5,000 works) whenever you choose.

---

## 1. Context

### The problem statement (SIH26102, MoSPI, Data Informatics & Innovation Division)

**Analyse:** sanctions, expenditures, cost estimates, work progress, payments and asset creation.

**Detect:**
- unusual patterns
- cost overruns
- duplicate works
- delayed projects
- deviations from norms
- misuse of funds

**Provide:**
- risk-based alerts
- predictive insights
- early warnings
- trend analysis
- automated compliance monitoring
- dashboards for **MPs, State Nodal Authorities, District Authorities and the Ministry**

**Dataset named:** mplads.mospi.gov.in/digigov/dashboard.html

### How MPLADS really runs (2023 guidelines, eSAKSHI; PIB 2155040, 2235932, 2027330)

1. **₹5 crore authorised** per MP each April, in one go.
2. **The MP recommends** works on eSAKSHI (OTP or mobile app).
3. **The District Authority sanctions** within 75 days, or tells the MP of a rejection within 45 days (para 3.12). It then names an Implementing Agency.
4. **The Implementing Agency builds** and raises vendor payment requests stage by stage, uploading **photos and documents at every payment stage**.
5. **The District Authority verifies**, and payment goes direct.
6. **On final payment the work is marked "complete".** Works should finish **within one year** (para 3.13).

**Rules with numbers:**
- ₹25 lakh a year for works outside the constituency (para 2.9)
- trusts and societies ₹50 lakh per lifetime, or ₹75 lakh in tribal areas (paras 3.21.2 and 2.5.1)
- SC/ST earmarks of 15% and 7.5% (para 2.5)
- the District Authority inspects at least 10% of works each year (para 6.4)

**What auditors actually found** (CAG report 31 of 2010-11, already in `~/saakshya/data/raw/cag/cag_findings.json`, 21 categories):

| Finding | Scale |
|---|---|
| Delayed recommendations | 78,190 works |
| Sanctioned without following guidelines | 7,230 works |
| Incomplete works | ₹220.8 crore |
| Advances parked with agencies | ₹89.8 crore |
| **Plaques not erected** | **4,918 works** |
| Assets not put to use | — |
| Doubtful vouchers | — |
| Excess to trusts | ₹12.9 crore |
| SC/ST earmark shortfall | ₹498 crore |
| Convergence double-funding | — |

MoSPI itself added a way (March 2026) to replace **"incorrect images uploaded earlier"**, so wrong photos are an acknowledged problem.

### What the real data contains (measured today)

- **The export:** 209,993 works. It has type, description, amounts, dates and status, but no GPS, quantities or photos.
- **Attachments:** real attachments are served by the dashboard's public endpoints:
  - `getAttachIdsbyFlag` takes `{"json":{"FLAG":"3","WORK_ID":<id>}}`
  - `getAttachmentById` returns the file as base64
- **Coverage:** 66% of completed works carry attachments; about 58,000 nationally.
- **Sample of 40 works:** 85% have one file; 72% of files are PDFs, 28% photos.
  - The PDFs are completion certificates, utilisation certificates (handwritten Hindi), bills, and combined "WC+UC+QC+Bill" files.
  - The photos have their GPS/time/PIN code/address stamped into the image by "GPS Map Camera" or "NoteCam". The phone's own location data is usually stripped.
- **Citizen ratings exist on eSAKSHI but are unused:** 21,789 zeros and 4 real ratings.
- **MP-level money files:** allocated, recommended, sanctioned, completed and spent per MP (`mplads_{17ls,18ls,rs,aggregate}.csv`).

### Your decisions (2026-09-25)

- All feasible, proven agents.
- Satellite only where proven, and only for big works.
- A polite pilot sample of real eSAKSHI evidence.
- Free AI for the first test run, paid later.
- Plan first, then slides in the style of the deck you'll share, then build.

---

## 2. The rules every agent must pass (this is how we win)

1. **A distinct facet.** It catches something no other agent catches, tied to the problem statement or a CAG finding.
2. **Proven method.** It uses a technique with Indian-government or industry precedent. No research-grade gambles.
3. **Real data first.** It runs on real eSAKSHI data or evidence. Where it can't (citizen channel), the demo is labelled as a demo.
4. **Measured before it goes live.** Each agent has:
   - a labelled test set
   - a target
   - **an accuracy target on real data**
   - a **kill criterion**: missing the target keeps it switched off
5. **Honest output.** Results are SHOWN / NOT SHOWN / CAN'T TELL. "Needs verification", never an accusation. The officer always decides.

---

## 3. The line-up: 12 agents in 4 stages, plus 4 decision tools

| # | Agent | The question it answers (deck line) | Problem it fixes | Proven method | Precedent | Data | How we prove it |
|---|---|---|---|---|---|---|---|
| **A: before money moves** | | | | | | | |
| A1 | **Eligibility** | Is this work allowed under MPLADS? | Non-compliance (CAG 4.3: 7,230 works; 3.5; 7.3; outside-constituency) | Rule checks with verbatim clause citations + prohibited-work classifier (object-of-work matcher, built, + Gemini with the clause quoted) | The guidelines themselves; LLM text classification | Real | 300 hand-labelled real descriptions |
| A2 | **Duplicate & Split** | Is this already funded, or one work cut into pieces? | Duplicates (PS), convergence (CAG 3.6), split works | DIGIPIN spatial + rare-token + multilingual embeddings + status/amount/renewal gates (ported, measured) + split pattern (same MP/village/type, within 90 days, sum over threshold) | Record linkage; Open Contracting "split purchases" red flag | Real (429 repeat clusters measured) | 100 planted paraphrased duplicates + 500 random works |
| A3 | **Cost** *(built)* | Is the cost unusual for similar works? | Inflated estimates (PS "cost estimates") | Peer bands per type × district (AD-106), road ₹/m vs published rates, bulk-order reading | Estimate vetting against schedules of rates | Real (847 of 209,993 need review) | Planted inflation ×1.5 to ×5 |
| **B: while the work is built** | | | | | | | |
| B1 | **Site Progress** | Do the photos show what was claimed? | Progress misreporting, CAG 4.8 unfruitful works, **7.2 plaques missing (4,918 works)**, MoSPI's "incorrect images" | Gemini checks free-text claims with repeat + half-set controls (ported); **plaque present and readable**; "does the photo show this type of work?" | PMAY-G pays only on geotagged stage photos (3.84 crore sites) | Real completion photos (pilot) + labelled web photos | Claim set: false claims caught ≥70%, true claims wrongly contradicted ≤5%; plaque accuracy on labelled real photos |
| B2 | **Photo Forensics** | Has this photo, or this certificate, been used before or edited? | Reused or recycled evidence | 256-bit pHash + dHash, crop hashes, ORB feature matching; **also on rendered PDF pages** (same certificate on two works); editing/scan/screenshot signs | Perceptual hashing at scale (PhotoDNA-class) | Real pilot index | Edit suite (resize, crop, recompress…) + real matches checked by eye |
| B3 | **Geo-Location** | Was the photo taken at the site, and when? | Photos from elsewhere, backdated evidence | GPS from photo data **or read from the stamped overlay** (lat/long, PIN, address, time); inside the district/constituency (LGD polygons, built); near the named village (gazetteer); PIN→district (India Post–LGD file in repo); time inside the sanction→completion window; same coordinates + time on different works | PMAY-G AwaasApp, GeoMGNREGA, Amrit Sarovar all rely on geotagged photos | Real overlays seen in eSAKSHI photos | Overlay reading checked against 100 hand-read photos; boundary checks are exact |
| B4 | **Document** | Do the certificates and bills add up? | Doubtful vouchers (CAG 4.9), payment/document mismatch, sanction delays | Gemini reads certificates/UCs/bills (Hindi/English, handwritten) into fields. Checks: arithmetic; dates in order (sanction ≤ start ≤ completion ≤ handover, **real 75-day and 1-year checks**); document vs portal (amount, name, district); right document for the stage; required set present; GSTIN checksum/state code | Document AI is industry-standard; eSAKSHI requires documents at every payment stage | Real (pilot) | Field accuracy on 100 hand-transcribed documents, including handwritten Hindi UCs |
| B5 | **Satellite** *(big works only, gated)* | Did a large work change the ground? | Ghost large works (ponds, long new roads, big buildings) | Sentinel-2 before/after (free; Planetary Computer, no key): water index for ponds, built/bare-soil change for roads over 1 km and buildings over ~2,000 m², at coordinates from B3; otherwise NOT_APPLICABLE | **Mission Amrit Sarovar**: 68,000+ ponds monitored with remote sensing (BISAG-N) | Real works with B3 coordinates | **Go/no-go:** ≥20 real large works; if it can't separate built from not-built, it stays off |
| **C: money and time** | | | | | | | |
| C1 | **Delay Prediction** | Which works will be late, and which are stuck now? | Delays (PS), CAG 4.5/4.6/4.7 | Gradient-boosted model on **real completion histories** (late = not done within 12 months of recommendation), validated on a later period; stuck-now detector; sanction-delay monitor (dates from B4) | MoSPI's own PAIMANA problem (SIH26103) asks for exactly this | **Real labels** | Accuracy on a later cohort, and precision in the top 10% |
| C2 | **Fund Flow** | Will the money be used well and on time? | Unspent/idle funds, year-end rush, advances (CAG 6.7: ₹89.8 crore; 6.8), payment ahead of verified progress | Per-MP and per-district funnel (allocated→recommended→sanctioned→spent), March-rush share vs norm, lapse forecast, payment vs B1/B4 progress, calamity-consent checks | CAG findings; budget-execution monitoring | Real MP-level files + dates | Backtest the FY2024-25 forecast from mid-year data |
| C3 | **Contractor Network** | Is a small circle of contractors getting everything? | Collusion, concentration, cartels | Contractor names from B4, matched and cleaned → contractor–agency–district–MP graph; share per district/agency; contractors spread across many agencies; contractors behind flagged or duplicate works | Open Contracting red flags (supplier concentration) | Real names on certificates and photo sheets | Name-matching accuracy on hand-labelled pairs; concentration figures are facts |
| **D: after completion** | | | | | | | |
| D1 | **Citizen Verification** | Do local people confirm the asset exists and is used? | Assets not put to use or misused (CAG 5.1, 5.2), ghost works | QR / link web form (no app) at completed works; photo + GPS checked by B2/B3; asks aimed at high-risk works; independent confirmations weighted | MGNREGA social audit (statutory); eSAKSHI citizen rating exists but is unused (4 of 21,793) | Unused rating is real; the channel is a labelled demo | Scripted demo; validation pipeline tested |

### Decision tools

| Tool | What it does |
|---|---|
| **Data Validation** (built) | Impossible dates (1,193 real works, with portal-migration context), missing fields, guideline notes |
| **Risk Fusion** (v1 built) | Extended to 12 agents: weight = risk × confidence × reliability; a stronger bonus when *different stages* agree; parts add up exactly to the score; conflict rules (see below). High/Medium/Low bands. Reliability learns from officer decisions. |
| **Inspection Planner** | Picks the District Authority's 10% (para 6.4): mostly by risk × money, with about 20% at random (keeps honest base rates, deters gaming), grouped into day trips. Proof: expected catches per inspection vs random. |
| **Ask DRISHTI** | Plain-language questions for each role, answered by checked database tools (numbers verified before shown); guideline Q&A with verbatim clause quotes; drafts inspection notes and letters (English/Hindi) |

**Conflict rules (fusion):**

| Rule | What happens |
|---|---|
| R1 | Photos reused, taken elsewhere, or stale → progress confirmations are voided |
| R2 | Each location fact counts once |
| R3 | A bulk order counts once (Cost + Duplicate) |
| R4 | A declared repair or extension of the matched work downgrades a duplicate |
| R5 | A document disagreeing with the portal is shown with both sides |
| R6 | Satellite can only withdraw a finding where photos exist, never create one |

**Four role dashboards (as the problem statement asks):**

| Role | What they see |
|---|---|
| **MP** | My works' progress, delays, unused funds, citizen feedback |
| **State Nodal Authority** | District and agency bottlenecks, agency scorecards (institutions, never MPs) |
| **District Authority** | Review queue, inspection planner, evidence, decisions |
| **Ministry** | National map, trends, early warnings, agent accuracy |

---

## 4. The real-evidence pipeline (new)

**Evidence Harvester** (offline job, `data/harvest/`). It pulls attachments through the two public endpoints:
- one request every 1.5 s
- each file downloaded exactly once and cached
- a named User-Agent
- records its source URL and fetch time

**The pilot (your choice: pilot sample):**
- every completed work with attachments in **5–8 districts** (chosen for volume and variety), so that reuse *within* a district or agency can surface
- plus a **random national sample**
- about 5,000 works in total
- **The free first test run is about 500 works.**

**Storage:**
- Originals stay on this PC (`data/evidence/`, gitignored).
- Supabase holds only what's derived: hashes, extracted fields, overlay GPS, thumbnails of ~20 KB. This keeps inside the free 1 GB.

**AI reading:** one Gemini call per photo covers overlay text, scene, plaque and work-type match; one call per PDF page.
- **Free tier:** Flash-Lite with a fallback chain, a ledger and a cache.
- **Later:** a paid key with a hard cap. At roughly ₹200–500 per 5,000 works, this is the one switch you decide.
- Hashing (B2), boundaries/PIN (B3) and all statistics need no AI and run on everything.

**Labels:** every record shows where it came from:
- **REAL** (eSAKSHI export or attachment)
- **DEMO SCENARIO** (planted, with its answer key)
- **LIVE** (a submission on our site)

---

## 5. Proof plan: numbers, not claims

- **Per agent:** tuned on a development set, reported on a held-out set, misses published (see the table in §3).
- **A real-data findings report.** Each finding is checked by eye before it's quoted. Examples of what it would count: photos reused across works, certificates disagreeing with the portal, photos stamped outside the district, missing plaques, contractor concentration, predicted-late works.
- **The Evidence page** is generated from `eval/results/*.json`. No hand-typed numbers.

---

## 6. Deck blueprint (next step, once you send the style deck)

Keep it pictorial and plain-language, with no file paths or test counts on slides (your standing rule). One slide per point:

1. **Title.**
2. **Problem + how MPLADS works:** the lifecycle strip (recommend → sanction → build → pay → complete → use) with the CAG findings pinned to each stage.
3. **Proposed solution:** 12 agents in 4 stage columns, each with its one-line question and an icon, plus the 4 decision tools.
4. **What makes it real:** a real completion certificate, the real GPS-stamped photo and the real Hindi UC, each annotated with what the agent reads.
5. **Technical approach:** the pipeline plus the agent cards (method → output) and the stack.
6. **Proof:** measured accuracy for each agent (only measured numbers; unmeasured ones are shown as "target").
7. **What DRISHTI checks:** a capability grid of DRISHTI's checks and how each works.
8. **Feasibility:** proven precedents (PMAY-G, GeoMGNREGA, Amrit Sarovar, social audit, CAG), free/open tools, privacy.
9. **Impact:** 4 role dashboards, inspection planner, early warnings.

**Only measured facts go on slides:**
- 209,993 works
- 847 flagged, 0.40%
- the CAG figures
- the precedent figures
- 66% of completed works carry evidence
- 21,789 of 21,793 citizen ratings unused

Everything else is labelled as a target.

---

## 7. Architecture changes (from `docs/specs/2026-09-25-drishti-prototype-design.md`)

**What stays:**
- Next.js web + FastAPI engine as Vercel Services
- Supabase (Postgres/pgvector, Storage, Auth)
- Gemini behind a quota-aware provider
- pgserver for tests
- the agent contract and fusion

**What's new:**
- **Agent registry:** `drishti/agents/<id>/`, grouped by stage. The orchestrator runs any number of agents; unbuilt ones report NOT_BUILT.
- **Offline jobs:** `data/harvest/` (evidence), `data/read/` (Gemini extraction, cached), `data/models/` (delay model training), `data/satellite/` (Sentinel batch; heavy GDAL stays offline).
- **New tables:** `evidence_files`, `photo_hashes` (bit(256)), `doc_fields`, `overlay_geo`, `contractors`, `contractor_links`, `predictions`, `mp_funds`, `inspections`, `citizen_reports`.
- **Ported from `~/saakshya`:**
  - `core/vision/hashing.py`, `core/duplicates/*`
  - `core/field/verify.py`, `core/vision/provider.py`
  - `core/geo/{optical,timeseries,sources}.py` for the satellite work
  - `core/fusion/calibration.py`
  - `core/db.py` (the audit chain)
  - `ingest/adapters/lgd.py`
  - `data/raw/lgd/india-postal-lgd-mapping.csv` (PIN→district)

---

## 8. Milestones (each ends deployed and verified)

| # | When | Build | Show |
|---|---|---|---|
| **M0** | now | Put the built version online: needs your `! npx supabase login`, then load data, seed demo logins, deploy, smoke test | Live site: 2.1 lakh works, Cost agent |
| **S1** | when you send the style deck | New slides per §6 | Updated deck |
| **M1** | Oct wk 1–2 | Evidence Harvester + free 500-work test; B2 Photo Forensics; B3 Geo-Location | First real findings: reused photos, photos stamped outside the district |
| **M2** | Oct wk 2–3 | B4 Document + C3 Contractor Network (after the paid switch if you approve; else slower) | Certificates that disagree with the portal; contractor concentration |
| **M3** | Oct wk 3–4 | A1 Eligibility (classifier), A2 Duplicate & Split, C1 Delay Prediction, C2 Fund Flow; role dashboards v1 | Real accuracy of the delay model; MP/district funnels |
| **M4** | Nov wk 1–2 | B1 Site Progress + plaque check + field app (live camera + GPS); D1 Citizen Verification | Claims checked against photos; missing plaques on real works |
| **M5** | Nov wk 3 | Fusion v2 (12 agents, conflict rules), Inspection Planner, case workflow + audit chain, Ask DRISHTI | The complete loop, by role |
| **M6** | Nov wk 4 – Dec | B5 Satellite go/no-go (+ agent if it passes); your real photos; evaluation report; Hindi; demo script | The finale build |

**How I work each milestone:**
1. Write a task plan to `docs/plans/`.
2. Build inline with tests first.
3. Measure; push to `main` → live.
4. Update STATUS + memory.
5. Give you a plain-words update.

---

## 9. Verification

- **Engine tests:** each agent has unit tests plus pgserver integration tests. The fusion conflict rules R1–R6 each have a test.
- **Per-agent evaluation:** `python -m eval.run --agent <id>` writes held-out metrics.
- **Real findings:** every real finding quoted anywhere (site, slides) is checked by eye first and linked to its source file.
- **Live site:** a Playwright smoke run after every deploy (login → dashboard → a flagged work → agent cards → decision).
- **Free-tier health:** database under 400 MB, storage under 800 MB, the AI ledger within quota, the daily keep-alive cron running.

---

## 10. Risks

| Risk | Mitigation |
|---|---|
| eSAKSHI endpoints change or throttle | Cache everything once; slow, polite rate; the pilot is small; the adapter is isolated |
| The free AI allowance is too small for the evidence | First test ~500 works free; the paid switch is your call; hashing and geo checks need no AI |
| Handwritten Hindi documents read badly | Measure field accuracy first; low-confidence fields become CAN'T TELL, never findings |
| Satellite doesn't separate built from not-built | Go/no-go gate; stays off and says so |
| Too many agents to finish by December | Order puts the unique real-evidence agents first; each milestone is shippable alone |
| Naming real contractors or works | Login-only; "needs verification" wording; institutions scored, never MPs; banned-word test |
| Map-boundary sensitivity | Official LGD outlines only (built) |
