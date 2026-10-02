# The DRISHTI agents

Every agent answers **one question** about a work, uses a method with a **real-world precedent**, and must
**meet its accuracy target on real data** before it goes live. This page is the single reference for all of
them: what each checks, how, what we measured, and where it stands.

- Full trial write-up with every number: [`trial/FINDINGS.md`](trial/FINDINGS.md)
- Trial scripts: [`../data/trial/`](../data/trial/) · saved outputs: [`../data/trial/results/`](../data/trial/results/)
- Design and the reasoning behind each choice: [`specs/2026-09-25-drishti-v2-full-agents-design.md`](specs/2026-09-25-drishti-v2-full-agents-design.md)

## Status at a glance

| # | Agent | Stage | State | Trial verdict on real data |
|---|---|---|---|---|
| A1 | Eligibility | Before sanction | ✅ **in the engine** as Guideline Compliance rule R07 (v2 reader) | **Works** — 56% precision on a fresh sample |
| A2 | Duplicate & Split | Before sanction | ✅ **in the engine**, compares any work live (T051) | fresh pairs 20/40 real repeats, same-site splits 9/15 |
| A3 | Cost | Before sanction | ✅ **live** (v2 ready, T020) | v2: top 30 flags 10/30 real price questions (v1 0/30); 55% of 5× mark-ups caught at 1.3% false alarms |
| B1 | Site Progress (+ plaque) | During construction | 🔧 **v2 built, off** (T510, 2 Oct 2026): free local readers (CLIP + plaque OCR), optional Gemini key | 34 unit tests + an end-to-end smoke test; go/no-go on the pilot's real photos still to run (`site_progress_trial.py`) |
| B2 | Photo Forensics | During construction | ✅ **in the engine as Photo Evidence** (T310), shown, not counted | exact copies + fingerprint; reproduces the 2 real reuse cases, 0 of 3 combined files flagged |
| B3 | Geo-Location | During construction | ✅ **in the engine as Photo Evidence** (T310), shown, not counted | 190 stamps on 170 works; 187 inside, 2 at the border, 0 outside; the 3 photos older than the recommendation |
| B4 | Document | During construction | ✅ **in the engine as Paperwork** (T110), shown, not counted | reproduces the trial: 431 certificates, 32 sanctioned late, 1 before recommendation; Hindi/handwritten needs AI |
| B5 | Satellite (big works only) | During construction | ⛔ no-go for now; gate in Site Progress (T510) | 2,822 works qualify (2,167 ponds); only 1 has a GPS-stamped photo in the pilot |
| C1 | Delay | Money & time | ✅ **in the engine, shown, not counted** (T051 ladder) | **Weak** as a prediction (AUC 0.705; unseen districts 0.685; target 0.80) |
| C2 | Fund Flow | Money & time | ✅ **in the engine as Delay & Fund Flow** (T410), shown, not counted | 3,331 works (₹168.9 cr) of the ended 17th Lok Sabha still unsanctioned (reproduced); office backlog vs its district |
| C3 | Contractor Network | Money & time | ✅ **in the engine as Paperwork** (T110): a fact, not a finding | Pratapgarh 261 works, 7 vendors, top 39%, top three 84% (reproduced) |
| D1 | Citizen Verification | After completion | 📝 merged into Photo Evidence: a citizen's photo meets the same checks (demo only) | Can't be tested — 21,789 of 21,793 eSAKSHI ratings are zero |
| — | Guideline Compliance | every work | ✅ **in the engine** (T011) | rules R01–R14 in English + Hindi; T055: R14 built right after sanction (12/12 + 13/13 read worth a look), R07 reader fixes |
| — | Office Patterns | every office | ✅ **in the engine** (T055), weight 0.10: backs up a work's findings, never queues it alone | offices that price most works just under a limit or record buildings complete days after sanction; listed once on the dashboard |
| — | Data Validation | every work | ✅ live | impossible dates judged by quarter and office; shown, not counted in the v2 score |
| — | Risk score | every work | ✅ **v3** (T055; v2 = rollback) | the chance a work is worth a look, from hit rates read by eye; one case = one queue row; see FINDINGS "T055" |
| — | Pre-sanction check | before sanction | ✅ **in the engine + site** (T064) | every engine on a recommendation before sanction → Green / Amber / Red with reasons; never blocks, nothing stored. Real demo: ordinary hall Green, refiled hall Amber, temple-campus light Amber, Rs 25 lakh hall with no place Red |
| — | Inspection Planner | every work | 📝 planned | — |
| — | Ask DRISHTI | every work | 📝 planned | — |

✅ built into the engine (the T011–T050 ones go live when their stacked PRs are merged and the hosted database is reloaded) · 🧪 method proven on real data, not yet in the engine · 📝 planned · ⛔ gated off

## The four core engines (NidhiNetra blueprint, built 30 Sept 2026)

| Engine | Folder | Weight in the score | How it was checked on real works |
|---|---|---|---|
| Guideline Compliance | `agents/compliance/` | 0.30 | all 2,09,993 works: R01 21,323 · R02 61,920 · R06 1,114 · R07 458 · R11 7,576; no HIGH-severity rule fires. T051: timing rules graded (447 distinct signals, was 3), Hindi-script R07; T053: R12 big sum that does not say what or where (697 works, 28/30 by eye), R13 built in days (13, 13/13); T054: R01/R02 score by how unusual the wait is (at 75 days 63 in 100 works still wait), ended-term leftovers LOW on the para 3.15 clock, R02 always LOW |
| Cost Anomaly | `agents/statistical/` | 0.20 | planted mark-ups + frozen fresh samples read by eye. T051: the word-price model judges any description: 5× mark-ups caught 42-45% (was 55%), false alarms 1.2%. T053: explicit comfort zone (asks only above the highest of 2× the district top, the state top, 2× the described-like-this top); flags that read almost never right removed (several sites 0/48, far bigger project 3/18, per unit 0/3, below peers unmeasured); kept: above the comfort limit (54/128) and road cost per metre |
| Duplicate & Split Work | `agents/dup_split/` | 0.20 | T051: rules run live for any work. Fresh frozen samples read by eye: pairs 20/40 real repeats (T030: 15/40), same-site splits 9/15 (T030: 10/15) |
| Office Patterns (T055, new) | `agents/office_patterns/` | 0.10 (backs up a work's findings; never queues it alone) | dashboard's 40,935 works: 36 offices price most works just under a limit (median 55% of their works vs 9.5% nationally; 1,311 works flagged `PRICED_AT_LIMIT`), 6 record buildings complete within 7 days of sanction as a routine (median 69% vs 7.1%). Test country: 100% of planted limit-pricing offices' works found; fires on 0.02% of ordinary works |
| Fund Flow (was Delay Prediction) | `agents/delay/` | **0** (shown, not counted) | T053: the forecast was removed (LightGBM 0.710, ladder 0.705 AUC against 0.80; 73% of works run late anyway). Kept: 3,331 works (₹168.9 cr) of the ended 17th Lok Sabha still unsanctioned, office sanction backlog vs its district. T056: reads status, term and house in any case, text dates, and says "cannot be assessed" for a recommendation dated after the data |
| ~~Odd Overall~~ | — | — | removed in T053: Isolation Forest flags read 9/30 worth a look; replaced by Guideline Compliance R12 and R13 |

**One brain per engine (T051, 1 Oct 2026).** Each engine computes its answer for ANY recommendation from
stored tables, coefficients or reference files (`cohort_stats`, `engine_models`,
`reference/generic_words.txt`). No engine reads an answer stored per work, so a work recommended after the
data was built meets exactly the same rules. Learning jobs: `data/build_stats.py`, `build_price_model.py`,
`build_evidence.py`, `build_generic_words.py`. The risk score that combines them is in
[ARCHITECTURE.md §4](ARCHITECTURE.md#4-risk-score-fusion-v3-2-oct-2026-v2-kept-as-a-rollback); its cut-offs were re-tuned for T051
(CRITICAL 0.30, HIGH 0.22). After T053: queue 493. After T054 (timing rules by how unusual the wait is): queue 131, 28/30 read worth checking. Planted-anomaly test (T080): 39 of 50 fakes in the top 5% of the score (target 75%), 37/50 caught by the engine meant for them (rules, dates and splits 30/30, reworded repeats 7/10, prices 2-3× 0/10), 4/50 in the review queue.

**T055 (2 Oct 2026): engine review, test country, Office Patterns, risk fusion v3.** Write-up
[`plans/T055-engine-review.md`](plans/T055-engine-review.md), numbers in FINDINGS "T055". On three made-up
countries with 810 planted problems (`data/trial/synthetic_eval.py`): caught by the engine meant for them
**31% → 74%**, in the review queue **4% → 16%**, in the top 5% **34% → 74%**, queue precision 62% → 68%, ordinary
works queued 0.03% → 0.11%. On the eSAKSHI dashboard's 40,935 unseen works: queue 47 → **427 (1.04%)**, 40 random
queue works read **39 worth checking, 1 grey, 0 misread** (main: 38 / 1 / 1). The score is now the chance a work
is worth a look, from hit rates read by eye (`reference/reliability.json`); `DRISHTI_FUSION=v2` rolls back.

## Twelve checkers merged into six (T051, trimmed in T053, owner's requests 1 Oct 2026)

| # | Engine | Merges | Inputs | State |
|---|---|---|---|---|
| 1 | Guideline Compliance | A1 Eligibility + rules R01-R11 | the export | ✅ live, counted |
| 2 | Cost Anomaly | A3 | the export | ✅ live, counted |
| 3 | Duplicate & Split | A2 | the export | ✅ live, counted |
| 4 | Fund Flow | C2 Fund Flow (C1's delay forecast removed in T053: 0.70 < 0.80 and it added little to R02) | the export, Lok Sabha term dates | ✅ shown, not counted (the wait itself is R01's) |
| 5 | Paperwork | B4 Document + C3 Contractor Network | certificates read by local OCR | ✅ shown, not counted (pilot only); T053 kept only real findings (late or early sanction, another work's papers, more paid on paper) |
| 6 | Photo Evidence | B2 Photo Forensics + B3 Geo-Location + D1 Citizen photos | photos, GPS stamps | ✅ shown, not counted (pilot only); T053 kept only real findings (reuse, outside the district, photo before the recommendation) |
| — | ~~Site Progress~~ | B1 + plaque + B5 Satellite | an AI vision key | ❌ removed in T053: it could not run without a key, so it only ever said "cannot be assessed". Rebuild from git (T510) once a key exists and a test can be run |
| — | ~~Odd Overall~~ | the blueprint's outlier slot | the export | ❌ removed in T053 (the forest's flags read 9/30); replaced, by the owner's choice, by Guideline Compliance R12 (big sum that does not say what or where, 28/30) and R13 (built in days, 13/13) |

Why these merges: Delay and Fund Flow both ask "is time or money stuck?" from the same dates. Document and
Contractor read the same certificates (the vendor code comes from the certificate). Photo Forensics,
Geo-Location and citizen photos all judge the same photos (new? from this place? from this time?). Site
Progress and Satellite both ask "was it physically built?" and both need inputs we don't have yet.
Plan: [`plans/T051-engines-any-recommendation.md`](plans/T051-engines-any-recommendation.md).

---

## How every agent reports (the contract)

All agents return the same shape (`apps/engine/drishti/agents/contract.py`), so fusion and the screens need
no special cases:

| Field | Meaning |
|---|---|
| `status` | `ASSESSED`, `NOT_APPLICABLE` (question doesn't arise, e.g. no photos yet), `NOT_ASSESSABLE` (question arises but the data can't answer it), `NOT_BUILT`, `ERROR` |
| `risk` | 0–1, how concerning the finding is |
| `confidence` | 0–1, how sure the agent is of its own reading |
| `hard` | true only for findings that are arithmetic against a rule (e.g. over a ceiling) or an exact match |
| `headline` | one plain-language sentence for the officer |
| `findings` | each with a code, text, risk and the evidence behind it |
| `limitations` | what the agent could not check — shown, never hidden |

Two rules are enforced in code, not trusted to each agent:
- **No accusing words** (`fraud`, `corrupt`, `scam`, `guilty`, …). Text containing one raises an error, and tests cover every word.
- **"Could not assess" is a status, never a low score.** It carries no weight and is shown as such.

---

## A · Before the money moves

### A1 Eligibility — *Is this work allowed under MPLADS?*

- **Catches:** works the guidelines prohibit (Annexure-II): religious buildings, works inside temple premises, commercial outlets, private property, etc. CAG found 7,230 works sanctioned without following the guidelines.
- **Method:** the prohibited word must be the **object** of the work, not a landmark ("road *near* the mandir" is fine). v2 adds fixes learned from reading its own mistakes: ration/PDS shops are government outlets; "Shishu Mandir"/"Vidya Mandir" are schools; "mandir ke pas" is a landmark; new rule for works *inside* temple campuses. Every flag cites the guideline clause (`reference/prohibited_works.yaml`, `guidelines_clauses.yaml`).
- **Measured** (rules frozen on one sample, scored on a **fresh** sample of 50):

  | Reader | Works flagged | Plainly prohibited | Worth a look |
  |---|---|---|---|
  | v1 (in engine) | 642 | 12% | 25% |
  | **v2** | **458** | **56%** | **80%** |

- **Found:** solar lights inside temple campuses, community halls on temple premises, "construction of a community temple".
- **Limits:** verdicts are our reading, not an official ruling; the 2023 prohibited list is not yet verified (mplads.gov.in refuses connections from outside India).
- **Next:** port v2 into the engine and raise it from a note to a finding. *(Done: R07 in Guideline Compliance.)*
- **T055 (2 Oct 2026):** objects of worship after "in / for / on" ("hall in Mandir", "wall for temple"), private
  institutions before the route word, typo spellings of public distribution shops. Dashboard: 54 → 63 flags; all
  15 gained read right, 5 of 6 dropped were misreads. T051 TEST sample: keeps 40/40 right flags, drops 1 of 10 misreads.

### A2 Duplicate & Split — *Already funded, or one work cut into pieces?*

- **Catches:** the same asset funded twice; one work split into pieces under the ₹5 lakh / ₹10 lakh limits; bulk purchases cut under the tender limit.
- **Method:** bunching test at the limits; same-site splits (same text, district, type, recommended close together, each piece just under the limit, total over it); same named site recommended again while the first is still open. Planned: DIGIPIN location grid + multilingual meaning match (ported from the research build) for reworded repeats.
- **Measured:**
  - **12.1× more works just under ₹5 lakh than just over** (11.5× at ₹10 lakh; other round sums 1.9–5.4×). Kolar 58.8%, Darbhanga 54.4% of works at ₹4.8–5 lakh vs 4.6% nationally.
  - **136 bulk-order groups (744 works)** kept under the limit — e.g. Sitamarhi, 48 high-mast lights, ₹2.39 cr within 7 days.
  - **Same-site split:** Nanded, 3 × ₹4,96,000 for one road, same day.
  - **Funded twice:** 48 pairs re-recommended while the first was open; read one by one, ~19 look like one asset funded twice (e.g. Malappuram: a school bus for one school, completed, then sanctioned again).
- **Limits:** exact wording finds nothing once the first work is complete — real repeats are reworded, so matching by meaning is the next step.
- **T055 (2 Oct 2026):** one site in numbered stretches ("part / phase / bit / chainage / reach") is `SPLIT_INTO_STRETCHES`
  (test country 33% → 93%; 18 groups on the dashboard data), never a repeat pair; `REPAIR_SOON_AFTER_BUILT` (a repair of
  the same asset within 3 years of completion, 0% → 78%; not yet read on real works, so it counts at the prior);
  sound keys for one village spelt two ways; Hindi/English synonyms; ~490 vetted generic words; the repeat clock starts
  at completion. The team's 159 labelled pairs: false repeats 56 → 50, true 44 → 43 (`dup_split_rescore.py`).
  A purchase or split shows once in the queue (one case).

### A3 Cost — *Is the cost unusual for similar works?* ✅ live

- **Catches:** inflated estimates.
- **Method** (`apps/engine/drishti/agents/statistical/`):
  - **Peer cost bands:** log-cost distribution per work type × district (backing off to state, then country, when a group has fewer than 20 works). How far above peers a work sits sets the risk.
  - **Bundle reading:** "217 different places", counts and lists in the description explain a high amount (lights, borewells), so those are read at lower confidence.
  - **Road price per metre:** cement-concrete roads with a stated length, against a fitted price curve and published rural road rates.
  - **Outside-constituency ceiling:** works outside the MP's constituency over ₹25 lakh (para 2.9) — the only *hard* signal, because it is arithmetic against a clause.
  - **Delay:** open works past their type's 98th-percentile duration.
- **Measured** (1,000 typical works inflated, bands rebuilt without them, 20,000 untouched works for false alarms):

  | Mark-up | Caught by DRISHTI |
  |---|---|
  | 2× | 18% |
  | 3× | 39% |
  | 5× | **63%** |
  | 10× | **84%** |
  | false alarms | 1.5% |

- **By design,** price alone is soft (capped) so it rarely queues a work by itself — only 0.11% of normal works.
- **Limits:** mark-ups under 2× hide in normal price variation; they need a second signal (e.g. Document reading quantities).
- **T055 (2 Oct 2026):** a description that states a single unit ("1 no. high mast light") is never excused as "a far
  bigger project": planted ×10 mark-ups on one unit caught 28% → 78%. Price alone stays Medium at most in v3 (above the
  comfort limit read right 54 of 128).
- **T056 (2 Oct 2026):** one amount for several streets or roads ("2nd 3rd 4th 7th Cross", "CC Roads in Madhav Nagar")
  is a bundle for the price (it stays one place for Duplicate & Split). 12 random real Cost flags read by eye: 3 real
  price questions, 5 grey, 4 not; the fix drops 7 of the 140 dashboard flags, all rightly. The planted-test misses at
  5x/10x sit in the comfort zone or read as "a far bigger project", by design (FINDINGS "T056").

## B · While the work is built

### B1 Site Progress — *Do the photos show what was claimed?* 📝

- **Catches:** "roof done" with no roof; photo of the wrong kind of work; **missing plaque** (CAG: 4,918 works).
- **Method:** a vision model checks each claim against the photos, with repeat and half-set controls (ported from the research build); plaque present and readable.
- **Precedent:** PMAY-G pays only on geotagged stage photos (3.84 crore houses).
- **State (T510 v2, 2 Oct 2026): built, switched off until measured.** Free local readers, offline, once per photo:
  an open CLIP model names what each photo shows (a finished road vs a dirt track, a roofed building vs an empty plot),
  and the photo's text is read for the MPLADS plaque and its dates. The engine judges the record's own words against
  those readings: `ASSET_NOT_SHOWN` (recorded complete, 2+ usable photos read as an unbuilt site, none shows the asset),
  `PLAQUE_DATED_BEFORE_RECOMMENDATION`, and, with the owner's free Gemini key, `CLAIM_NOT_SHOWN` for an officer's
  notes. Reused, out-of-district and too-early photos (Photo Evidence's facts) confirm nothing. Design and go/no-go:
  [`plans/T510-site-progress-v2.md`](plans/T510-site-progress-v2.md). Not yet run on a real photo (the pilot photos
  are in the data pack): `data/build_site_observations.py`, then `data/trial/site_progress_trial.py`.

### B2 Photo Forensics — *Has this photo been used before, or edited?*

- **Method:** exact file hash + 256-bit perceptual fingerprint + ORB feature matching; documents compared **by their text**, not by image.
- **Measured** on 319 real photos, 50,678 cross-work pairs, at the loosest setting that confuses no two different photos:

  | Edit | **DRISHTI** |
  |---|---|
  | brighten 25% | **100%** |
  | stamp band added | **99.4%** |
  | 8% crop | **100%** |
  | screenshot frame | **100%** |
  | **all edits** | **99.9%** |

- **Found:** one road photo on two different roads in Pratapgarh (the file name names the first work's village); one Hindi "work complete certificate" on two works for two different beneficiaries in Narmadapuram. Both: needs checking.
- **Lessons:** image fingerprints are useless on certificates (same template → 59,054 false matches in a first run); combined files (one invoice for 18 villages) are normal — an exact copy only matters when the file names a single work or person.

### B3 Geo-Location — *Was the photo taken at the site, and when?*

- **Method:** eSAKSHI strips the phone's GPS data (0 of 321 photos keep it), so DRISHTI **reads the GPS stamp printed into the picture** by GPS-camera apps (coordinates, date, time, PIN). Checks: inside the work's district (official LGD outlines), PIN agrees with district, photo date inside the recommend → complete window.
- **Measured:** stamps found on 190 photos/pages covering 170 works (20% of the pilot); coordinates right 12/12 checked by eye; three date-reading fixes (US-style dates, misread year corrected by the printed weekday, plaque dates no longer mistaken for the photo date).
- **Found:** all 187 readable points fall in the work's own district; **3 works whose own photos show them finished before the MP recommended them** (Sabar Kantha; two in Chittaurgarh, both recommended the same day in the pre-election rush).
- **Bonus:** a work with no district in the export is placed by its stamp.

### B4 Document — *Do the certificates and bills add up?*

- **Method:** local OCR (no AI service, no cost) reads Uttar Pradesh's portal-generated Utilisation Certificates: agency, work, **sanction date**, amount, **vendor name and code**, status, each payment's date and amount. Checks against the portal: right document, amounts, sanction delay, completion evidence.
- **Measured** on 431 certificates: amounts/payment dates/status found on ≥99%, vendor 98%, sanction date 69% (older form has no such line). Six compared field by field: all right.
- **Found:** **16% sanctioned after the 75-day limit** (median 68 days; if the 2023 rule is 45 days, 97% are late); on **282 of 285 "completed" works the attached certificate still says "in progress"**; on 427 of 429 certification pages the officer's boxes are empty.
- **Limits:** 51% of other states' PDFs (Hindi, handwritten, poor scans) are unreadable locally and need the AI reader.

### B5 Satellite — *Did a large work change the ground?* ⛔

- **Only for big works** (ponds, roads over 1 km, large buildings), and only if a go/no-go test proves it can tell built from not built. Precedent: Mission Amrit Sarovar monitors 68,000+ ponds by remote sensing.
- **State:** no-go for now. Of the 170 works with coordinates, the median cost is ₹2.8 lakh — handpumps, lights, 100 m lanes — too small for 10 m satellite pixels.

## C · Money and time

### C1 Delay — *Which works are stuck, and which offices run late?*

- **Measured** (strict backtest: trained on outcomes known at 1 Jan 2025, tested on works recommended Jan–May 2025): model 0.71 vs office's past record 0.68 (0.5 = chance). Too close to sell as a prediction.
- **The real finding:** 71–77% of works miss the one-year target — delay is system-wide. Of 97,808 works recommended April 2023–May 2024, **40,489 (₹2,178 cr) are still not complete two years later**.
- **Ships as:** office track records and a plain list of stuck works; the model only as a ranking aid.

### C2 Fund Flow — *Is money waiting too long?*

- **Found:** **21,323 works (₹1,361 cr) waiting for sanction past 75 days** (median wait 239 days); 3,331 of them from the 17th Lok Sabha, whose term has ended. Pre-election rush: 45,167 recommendations in Jan–Mar 2024; only 17% finished within a year.
- **Trap avoided:** a "March rush" in completions was a portal cycle, not office behaviour — rule: always compare with the same period nationally.
- **Limits:** lapse forecasts can't be tested on a single snapshot; certificate payment dates (B4) fill that gap.

### C3 Contractor Network — *Is a small circle getting everything?*

- **Method:** the vendor code on certificates is an exact identity — no name matching needed. Contractor–agency–district links.
- **Found:** Pratapgarh, 261 works, 7 vendors; the top three hold 84%.
- **Limits:** one district, mostly street lights through one agency. Concentration is a fact to show, not a finding on its own.

## D · After completion

### D1 Citizen Verification — *Does the asset exist and get used?* 📝

- **Method:** a QR code / link at the completed work opens a simple web form (no app): photo + GPS, checked by B2/B3; requests aimed at high-risk works. Precedent: MGNREGA social audit.
- **State:** can't be tested on real data (eSAKSHI's citizen rating is unused). Will be shown only as a clearly labelled demo.

## Decision tools

| Tool | What it does | State |
|---|---|---|
| **Data Validation** | impossible dates judged against their own recommendation quarter and office (bulk entry when eSAKSHI opened explains most); missing fields; prohibited-work notes. Its total weight is capped so the record alone can never make a work HIGH. | ✅ |
| **Risk score** | combines the engines into the 0–100 score (v3, T055: the chance a work is worth a look, from hit rates read by eye; v2's blueprint weights kept as a rollback), with an exact breakdown and the top three reasons in English and Hindi — see [ARCHITECTURE.md §4](ARCHITECTURE.md#4-risk-score-fusion-v3-2-oct-2026-v2-kept-as-a-rollback). A bulk order or split counts once (one case, one queue row, T055). Planned: conflict rules (a reused photo voids progress confirmations; satellite may only withdraw a finding, never create one). | ✅ v3 |
| **Inspection Planner** | picks the District Authority's mandatory 10% of inspections (para 6.4): mostly by risk × money, ~20% at random to keep base rates honest and deter gaming, grouped into day trips. | 📝 |
| **Ask DRISHTI** | plain-language questions answered from checked database queries; guideline answers quote the clause verbatim; drafts inspection notes in English/Hindi. | 📝 |
