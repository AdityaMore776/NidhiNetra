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
| A2 | Duplicate & Split | Before sanction | ✅ **in the engine** (T030, matching by meaning) | random pairs 15/40 real repeats, same-site splits 10/15, Nanded split found |
| A3 | Cost | Before sanction | ✅ **live** (v2 ready, T020) | v2: top 30 flags 10/30 real price questions (v1 0/30); 55% of 5× mark-ups caught at 1.3% false alarms |
| B1 | Site Progress (+ plaque) | During construction | 📝 planned | Not tested — needs an AI vision key |
| B2 | Photo Forensics | During construction | 🧪 trial | **Works** — 99.9% of edited copies recognised |
| B3 | Geo-Location | During construction | 🧪 trial | **Works** — stamps read on 170 works; 3 real timing findings |
| B4 | Document | During construction | 🧪 trial | **Works on typed certificates, free**; Hindi/handwritten needs AI |
| B5 | Satellite (big works only) | During construction | ⛔ no-go for now | Pilot has no large works with coordinates |
| C1 | Delay | Money & time | ✅ **in the engine, shown, not counted** (T040) | **Weak** as a prediction (AUC 0.71 vs 0.68 office record; target 0.80) |
| C2 | Fund Flow | Money & time | 🧪 trial | **Facts work**; forecasts can't be tested on a single snapshot |
| C3 | Contractor Network | Money & time | 🧪 trial | **Works where certificates exist** (vendor code = exact identity) |
| D1 | Citizen Verification | After completion | 📝 planned | Can't be tested — 21,789 of 21,793 eSAKSHI ratings are zero |
| — | Guideline Compliance | every work | ✅ **in the engine** (T011) | rules R01–R11 in English + Hindi; 5 of 11 not checkable from the export |
| — | Data Validation | every work | ✅ live | impossible dates judged by quarter and office; shown, not counted in the v2 score |
| — | Risk score | every work | ✅ v2 ready (T050) | blueprint weights, 4 bands, top-3 reasons EN + HI; queue 1,524 (0.73%), 24/30 random queue works worth checking |
| — | Inspection Planner | every work | 📝 planned | — |
| — | Ask DRISHTI | every work | 📝 planned | — |

✅ built into the engine (the T011–T050 ones go live when their stacked PRs are merged and the hosted database is reloaded) · 🧪 method proven on real data, not yet in the engine · 📝 planned · ⛔ gated off

## The four core engines (NidhiNetra blueprint, built 30 Sept 2026)

| Engine | Folder | Weight in the score | How it was checked on real works |
|---|---|---|---|
| Guideline Compliance | `agents/compliance/` | 0.30 | all 2,09,993 works: R01 21,323 · R02 61,920 · R06 1,114 · R07 458 · R11 7,576; no HIGH-severity rule fires |
| Cost Anomaly | `agents/statistical/` | 0.20 | planted mark-ups + a frozen fresh sample read by eye (FINDINGS A3, "Cost engine v2") |
| Duplicate & Split Work | `agents/dup_split/` | 0.20 | fresh random samples read by eye after each rule change (FINDINGS A2, "matching by meaning") |
| Delay Prediction | `agents/delay/` | **0** (shown, not counted) | strict time-based backtest AUC 0.71, held-out districts 0.59; target 0.80 |
| Odd Overall (outlier) | — | 0.10 | not built yet |

Heavy steps run offline in `data/` (`build_cost_model.py`, `build_dup_split.py`, `build_delay_model.py`) and
are stored per work in `work_signals`; the engines only read them. The risk score that combines them is in
[ARCHITECTURE.md §4](ARCHITECTURE.md#4-risk-score-fusion-v2-t050).

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
- **Next:** port v2 into the engine and raise it from a note to a finding.

### A2 Duplicate & Split — *Already funded, or one work cut into pieces?*

- **Catches:** the same asset funded twice; one work split into pieces under the ₹5 lakh / ₹10 lakh limits; bulk purchases cut under the tender limit.
- **Method:** bunching test at the limits; same-site splits (same text, district, type, recommended close together, each piece just under the limit, total over it); same named site recommended again while the first is still open. Planned: DIGIPIN location grid + multilingual meaning match (ported from the research build) for reworded repeats.
- **Measured:**
  - **12.1× more works just under ₹5 lakh than just over** (11.5× at ₹10 lakh; other round sums 1.9–5.4×). Kolar 58.8%, Darbhanga 54.4% of works at ₹4.8–5 lakh vs 4.6% nationally.
  - **136 bulk-order groups (744 works)** kept under the limit — e.g. Sitamarhi, 48 high-mast lights, ₹2.39 cr within 7 days.
  - **Same-site split:** Nanded, 3 × ₹4,96,000 for one road, same day.
  - **Funded twice:** 48 pairs re-recommended while the first was open; read one by one, ~19 look like one asset funded twice (e.g. Malappuram: a school bus for one school, completed, then sanctioned again).
- **Limits:** exact wording finds nothing once the first work is complete — real repeats are reworded, so matching by meaning is the next step.

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

## B · While the work is built

### B1 Site Progress — *Do the photos show what was claimed?* 📝

- **Catches:** "roof done" with no roof; photo of the wrong kind of work; **missing plaque** (CAG: 4,918 works).
- **Method:** a vision model checks each claim against the photos, with repeat and half-set controls (ported from the research build); plaque present and readable.
- **Precedent:** PMAY-G pays only on geotagged stage photos (3.84 crore houses).
- **State:** not tested — nothing free and local can judge "does this photo show a finished road". Needs the paid AI key (the team's decision).

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
| **Risk score** | combines the engines into the 0–100 score by the blueprint weights, with an exact breakdown and the top three reasons in English and Hindi — see [ARCHITECTURE.md §4](ARCHITECTURE.md#4-risk-score-fusion-v2-t050). Planned: conflict rules (a reused photo voids progress confirmations; a bulk order counts once; satellite may only withdraw a finding, never create one). | ✅ v2 |
| **Inspection Planner** | picks the District Authority's mandatory 10% of inspections (para 6.4): mostly by risk × money, ~20% at random to keep base rates honest and deter gaming, grouped into day trips. | 📝 |
| **Ask DRISHTI** | plain-language questions answered from checked database queries; guideline answers quote the clause verbatim; drafts inspection notes in English/Hindi. | 📝 |
