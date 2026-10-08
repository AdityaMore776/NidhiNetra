# The DRISHTI agents

Every agent answers **one question** about a work, uses a method with a **real-world precedent**, and must
**meet its accuracy target on real data** before it goes live. This page is the single reference for all of
them: what each checks, how, what we measured, and where it stands.

- Full trial write-up with every number: [`trial/FINDINGS.md`](trial/FINDINGS.md)
- Trial scripts: [`../data/trial/`](../data/trial/) · saved outputs: [`../data/trial/results/`](../data/trial/results/)
- Design and the reasoning behind each choice: [`specs/2026-09-25-drishti-v2-full-agents-design.md`](specs/2026-09-25-drishti-v2-full-agents-design.md)

## The four agents (owner's decision, 3 Oct 2026; built 4 Oct 2026, T121–T125)

Only four agents run now, a quarter of the weight each. Each asks only about what is likely fraud, never a minor
mistake; "couldn't check" is a status, never a low score. Plan in plain words:
[`plans/T120-four-agents.md`](plans/T120-four-agents.md); numbers in FINDINGS "T121–T125".

| # | Agent | Folder | Asks when | Proof so far |
|---|---|---|---|---|
| 1 | **Cost** | `agents/cost_estimate/` | every confirmed line priced at a fair rate (its SoR item, else 3+ other agencies' recent district rates, never its own) and quantities held to the size; asked when 60%+ of the money is priced and the estimate is 15%+ and Rs 50,000+ above the fair price; a confirmed quantity far above the size; the per-unit price far above the standard item and the MP's amount (T099); labour by trade (T141): a trade's day rate 2×+ what others pay it, or workers on site beyond the work's time (never how many workers) | synthetic forms (T141): honest asked 0.0–1.2% and every line +20% caught 80.2–94.0% at a 5–10% honest spread; 6.0–8.0% honest asked at 15%. Labour: honest filings 0/450 asked, one trade ×2.5 caught 88%, ×3 98%. No real forms yet; SoR files wait on T096 |
| 2 | **Duplicate Work** | `agents/dup_split/` | the form's map pin within 50 m of a sanctioned work of the same kind; a declared rebuild under 3 years; the strictest split (every piece 96–100% of a limit) | splits 12 of 14 groups read as one job; map-pin cases 100% on the test country, look-alikes 0% |
| 3 | **Time & Rules** | `agents/time_rules/` | R01 still waiting past 75 days, R06 impossible dates, R13/R14 complete within days; with a form, the comfort window: finished before its early line with no site video showing the work, or past its late line (more when the site stands still) | R14 25 of 25 read worth checking; R06 read on the hosted data (T056); a late sanction (60% of works) is an office fact and never queues alone; the window's findings at the 1-in-4 prior until read |
| 4 | **Site Progress** | `agents/site_progress/` (+ `video/`) | footage seen before, the same place as another undeclared work, not filmed here (GPS and views both), the claim not shown twice in a row, complete not shown, already built at the first visit | 21 rule tests, 14 video tests on drawn scenes, an end-to-end trial in a real browser; the field trial on real sites is T126. The claim judge **NidhiLens** (fine-tuned Qwen3-VL-4B): macro-F1 0.935 on 883 real site-photo checks, against 0.876 for Gemini 3.1 Pro at 1/30 of the cost ([report](../NidhiLens%20(Fine-Tuned%20Qwen%20for%20site%20progress%20monitoring)/README.md)); benchmarked, not yet in the live engine |

Retired in T125 (results stored before still read by name until re-assessed; code kept as libraries): Guideline
Compliance (its timing rules live on in Time & Rules), Fund Flow, Office Patterns, Paperwork and Photo Evidence. On the
dashboard's 40,935 works the review queue went from 439 to 217 (185 R14, 34 split pieces, 2 both).

**Hardened by the robustness loop (T135, FINDINGS "T135")**: 65 probes of damage, honest noise,
evasions, scarce data and scale end 59 PASS, 0 FAIL, 6 LIMIT, and 3,000 random damages crash none.
New questions: Cost `ESTIMATE_NOT_ITEMISED` and `SIZE_NOT_AS_DESCRIBED`, Site Progress
`NO_SITE_VIDEO` and `SITE_NOT_AT_FORM_PIN` (each at the 1-in-4 prior until read). A price the data
cannot support is switched off for that material and recorded as a gap (`GET /cost/data-gaps`).

**Architectures tested (T137, FINDINGS "T137")**: other designs for each agent, on the same
benchmarks at the same false-alarm rate. Cost keeps its money-gap rule: z-tests read a remote site
as padding, and an isolation forest catches half as much. Site Progress switched to "4 of the last 5
videos unusable" and a 300 m rule for "filmed elsewhere": honest works asked in a simulated year
fall from 25.7% to 5.0%, and every trick is still caught. It also asks `COMPLETE_NOT_FILMED`.
Duplicate Work looks nearby works up on a map grid: the same answers, 8–10x faster.

**Real data from outside (T139, FINDINGS "T139")**: Jaunpur's real works pinned at real buildings
(Open Buildings, post-office positions). Houses stand 8 m apart, and 1,006 of the 1,038 works are
solar street lights at houses. The 50 m rule would have asked 37–87% of honest lights and half of
one institution's honest purchases. Duplicate Work changed three rules:
- a light filed the same day as another (one programme) is never a repeat of it;
- a light is one spot (20 m), not 50 m;
- purchases are compared by kind.

Honest lights asked now: 1.5–6.4%. Repeats asked: 93–100%. Round 4 (6 Oct):
- **Hand pumps** take the same light rules: honest asked fall from 86% to 1%.
- **Roads** are the same road only when both ends lie within 30 m and it lies on the other's line.
  Real lanes run house to house and are short (median 121 m), so the next street over, 25–35 m
  away, was asked 64–81% of the time; now 3–28%. 94–99% of repeats are still asked.

Site Progress asks
`FIRST_FILMED_FINISHED`: a new work whose first video already shows it finished, with no video
before work.

**Round 6 and room for error (T136, FINDINGS "T136")**: 81 probes end 74 PASS, 0 FAIL, 7 LIMIT;
3,000 random damages crash none. Cost norms sand by the IS 456 mix and counts unread items beyond
15% of a construction estimate; Duplicate Work finds the strictest split by map pins too and names a
same-kind building just past 50 m in a note (`NEAR_SANCTIONED_WORK`); Site Progress forgives one
poor video (dark, short, weak GPS, a viewpoint missed or skipped) and asks `SITE_VIDEOS_UNUSABLE`
only when the last two cannot show the work, and asks at once about a work recorded complete with no
video. Every agent ran on all 8,702 real UP works with 0 errors. `/end-to-end` follows five filings
from the form to the risk score, Site Progress as a placeholder until its field trial (T126).

The website's work intelligence form (`/work-form`, T134) is read by all four: twelve example filings in Jaunpur show
each agent flagging, with the flagged fields outlined in the form (made-up agencies; FINDINGS "T134"), and "Check this
form" runs them on any filled form against the same example data, shown on the page's Data tab.

## Status at a glance (history, before the four agents)

| # | Agent | Stage | State | Trial verdict on real data |
|---|---|---|---|---|
| A1 | Eligibility | Before sanction | ❌ retired with Guideline Compliance (T125): not one of the four agents | **Works** — 56% precision on a fresh sample |
| A2 | Duplicate Work (was Duplicate & Split) | Before sanction | ✅ **in the engine** (T100, 3 Oct 2026): asks only by map pin, a declared rebuild, or the strictest split | strictest split: 14 dashboard groups read 12 yes, 2 grey, 0 not; words alone right about 2 in 3 (289 labelled pairs), so look-alikes are notes |
| A3 | ~~Cost Anomaly~~ | Before sanction | ❌ **retired** (T099, 3 Oct 2026): a price question from the record alone is not certain | its main flag read 54/128; of 15 works a record-only per-unit check would have questioned, 0 were real |
| A3b | **Cost** (the cost estimate form, Cost v3) | Before sanction | ✅ **the Cost slot** (T099): runs on works with the agency's submitted form; no form, not judged | UP hold-out (2026 works, reference before 2026): 0 of 42 real works above the question line; planted price ×1.5 / ×2 / ×3 asked 42/42, ×1.25 9/42, ×1.1 0/42; size ×½ / ×2 / ×5 changed 0 of 204 answers; 26 of 68 works could not be compared (no tight group) |
| B1 | Site Progress (+ plaque) | During construction | ✅ **v3 in the engine** (T124, 4 Oct 2026): monthly site videos; v2 (photos) kept for the photo trial | 34 unit tests + an end-to-end smoke test; go/no-go on the pilot's real photos still to run (`site_progress_trial.py`) |
| B2 | Photo Forensics | During construction | ❌ retired with Photo Evidence (T125); the video job's fingerprints do this for site videos | exact copies + fingerprint; reproduces the 2 real reuse cases, 0 of 3 combined files flagged |
| B3 | Geo-Location | During construction | ❌ retired with Photo Evidence (T125); site videos carry their own GPS log | 190 stamps on 170 works; 187 inside, 2 at the border, 0 outside; the 3 photos older than the recommendation |
| B4 | Document | During construction | ❌ retired with Paperwork (T125) | reproduces the trial: 431 certificates, 32 sanctioned late, 1 before recommendation; Hindi/handwritten needs AI |
| B5 | Satellite (big works only) | During construction | ⛔ no-go for now; gate in Site Progress (T510) | 2,822 works qualify (2,167 ponds); only 1 has a GPS-stamped photo in the pilot |
| C1 | Delay | Money & time | ❌ retired (T053 forecast, T125 Fund Flow) | **Weak** as a prediction (AUC 0.705; unseen districts 0.685; target 0.80) |
| C2 | Fund Flow | Money & time | ❌ retired (T125); the 75-day clock lives on in Time & Rules | 3,331 works (₹168.9 cr) of the ended 17th Lok Sabha still unsanctioned (reproduced); office backlog vs its district |
| C3 | Contractor Network | Money & time | ❌ retired with Paperwork (T125) | Pratapgarh 261 works, 7 vendors, top 39%, top three 84% (reproduced) |
| D1 | Citizen Verification | After completion | 📝 merged into Photo Evidence: a citizen's photo meets the same checks (demo only) | Can't be tested — 21,789 of 21,793 eSAKSHI ratings are zero |
| — | Guideline Compliance | every work | ❌ retired (T125): R01, R06, R13, R14 run inside Time & Rules | rules R01–R14 in English + Hindi; T055: R14 built right after sanction (12/12 + 13/13 read worth a look), R07 reader fixes |
| — | Office Patterns | every office | ❌ retired (T125) | offices that price most works just under a limit or record buildings complete days after sanction; listed once on the dashboard |
| — | Data Validation | every work | ✅ live | impossible dates judged by quarter and office; shown, not counted in the v2 score |
| — | Risk score | every work | ✅ **v3** (T055; v2 = rollback) | the chance a work is worth a look, from hit rates read by eye; one case = one queue row; see FINDINGS "T055" |
| — | Pre-sanction check | before sanction | ✅ **in the engine + site** (T064) | every engine on a recommendation before sanction → Green / Amber / Red with reasons; never blocks, nothing stored. Real demo: ordinary hall Green, refiled hall Amber, temple-campus light Amber, Rs 25 lakh hall with no place Red |
| — | Inspection Planner | every work | 📝 planned | — |
| — | Ask DRISHTI | every work | 📝 planned | — |

✅ built into the engine (the T011–T050 ones go live when their stacked PRs are merged and the hosted database is reloaded) · 🧪 method proven on real data, not yet in the engine · 📝 planned · ⛔ gated off

## The four core engines (NidhiNetra blueprint, built 30 Sept 2026)

| Engine | Folder | Weight in the score | How it was checked on real works |
|---|---|---|---|
| Guideline Compliance | `agents/compliance/` | 0.30 | all 2,09,993 works: R01 21,323 · R02 61,920 · R06 1,114 · R07 458 · R11 7,576; no HIGH-severity rule fires. T051: timing rules graded (447 distinct signals, was 3), Hindi-script R07; T053: R12 big sum that does not say what or where (697 works, 28/30 by eye), R13 built in days (13, 13/13); T054: R01/R02 score by how unusual the wait is (at 75 days 63 in 100 works still wait), ended-term leftovers LOW on the para 3.15 clock, R02 always LOW; T056: R06 read on the hosted data (1,105 works, 21 stand out): the 21 count in full (10/10 by eye, they reach the queue alone), the 1,084 bulk-entry and office-habit records notes stay LOW (risk 0.10) |
| ~~Cost Anomaly~~ (retired 3 Oct 2026, T099) | `agents/statistical/` (shared readers only) | — | planted mark-ups + frozen fresh samples read by eye. T051: the word-price model judges any description: 5× mark-ups caught 42-45% (was 55%), false alarms 1.2%. T053: explicit comfort zone (asks only above the highest of 2× the district top, the state top, 2× the described-like-this top); flags that read almost never right removed (several sites 0/48, far bigger project 3/18, per unit 0/3, below peers unmeasured); kept: above the comfort limit (54/128) and road cost per metre |
| Cost | `agents/cost_estimate/` | 0.20 | T097 + T099: the agency's cost estimate form. UP hold-out: 0 of 42 real works above the question line; planted ×1.5 caught 42/42; findings count at the 1-in-4 prior until officers' verdicts |
| Duplicate Work | `agents/dup_split/` | 0.20 | T100: map pin within 50 m of a sanctioned work of the same kind; a declared rebuild under 3 years; the strictest split (12/14 yes, 2 grey). Look-alikes by words are notes (2 in 3 right) |
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
| 2 | Cost (T099: was Cost Anomaly) | A3b | the agency's cost estimate form | ✅ live, counted; no form, not judged |
| 3 | Duplicate Work (T100: was Duplicate & Split) | A2 | the export + the form's map pins and declarations | ✅ live, counted |
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

### A2 Duplicate Work — *Is this work already sanctioned here, or one job cut to stay under a limit?*

**T100 (3 Oct 2026), the owner's "simple and certain" pivot.** Words alone find a repeat right about 2 times in 3 at
best (the strictest text rule 13 of 16 on the team's 289 pairs read by eye, finding 12% of the real repeats), because
the record's finest place is the district. So the engine now asks only:
- **`SANCTIONED_WORK_AT_THIS_SITE`:** the cost form's map pin is within 50 m of a sanctioned work of the same kind
  (a linear work by both ends), and the form does not name it as the work this one continues;
- **`REBUILT_SOON_AFTER_COMPLETION`:** the agency declares this work rebuilds a work completed under 3 years ago;
- **`SPLIT_JUST_UNDER_LIMIT`:** 2–5 alike pieces at one place or numbered parts, one MP, within 30 days, **every**
  piece 96–100% of the Rs 5 or 10 lakh limit. All 14 groups on the dashboard read: 12 one job cut into pieces, 2 grey,
  0 not.

**Notes, never counted:**
- a continuation the agency declares;
- look-alikes by words, which the form asks the agency to answer: the same work (it cannot be estimated again),
  continues it, or a different work (say what differs).

**Removed:** looser splits, bulk orders, the under-a-limit bonus, and repeats judged on words. The history below is
how the old rules were measured. Numbers: FINDINGS "T099 + T100".

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
- **T056 (2 Oct 2026):** a men's and a women's building are two works; a split whose total stays under Rs 5 lakh
  avoids no limit and is said, not asked. 12 real split flags read by eye: 7 yes, 2 grey, 3 no (all 3 removed by
  these rules); on a fresh sample 4 of 5 groups are real splits. Split flags on the dashboard 76 → 48.

### A3 Cost Anomaly — *Is the cost unusual for similar works?* ❌ retired (T099, 3 Oct 2026)

Retired by the owner's "simple and certain" pivot: a price question from an amount and a sentence is not certain. Its
main flag read right 54 of 128 times. Of the 15 works the most precise record-only check (a stated count of a standard
item) would have questioned, none was a real price question. The Cost slot is now A3b, on the agency's form. The
history below is kept for the record.

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

### A3b Cost (Cost v3) — *Is the agency's estimate right for this size of work here?* ✅ the Cost slot (T099)

Since T099 this is the Cost check of the core slot. A work with no submitted form is NOT_APPLICABLE. Forms are saved
with `POST /api/v1/cost-forms` (migration 013), and the batch and the API attach them. References are built for 7
states (`data/build_cost_reference.py --all`).

The implementing agency fills a full cost estimate form (`docs/specs/2026-10-03-cost-estimate-form.md`); normal mistakes
are caught on the form, never flagged. The engine (`agents/cost_estimate/`) asks only when it is certain
(`docs/plans/T097-cost-agent-v3.md`):
- **`MATERIAL_QUANTITY_ABOVE_SIZE`**: a material the agency confirmed is more than 25% above what the size needs
  (`cost_form/norms.py`: more batteries, fittings or poles than solar lights; pavers beyond the path's area; cement
  beyond an M10–M20 slab's volume by the IS 456 nominal mixes).
- **`ESTIMATE_ABOVE_STANDARD_AND_MP`**: the price per unit is more than 25% above the 98th percentile of the same
  standard item in the district (or state), **and** the estimate is more than 10% above the MP's amount. It needs two
  signals because real works record no wattage or height.

A group of real works is compared only when it has 30+ works, is tight (p90 within +25% of the median), and is
priced in the form's own unit of size. Roads (priced per m²) are never compared with roads per metre.

In Uttar Pradesh today that means solar street lights, and high masts in Kheri, Sitapur and Bareilly; everything else
answers "could not check" until the Schedule of Rates (T096) or completed forms arrive. Line-by-line rates wait for
T096. Numbers: FINDINGS "T097".

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
