# DRISHTI deck: the answers to every question on the slides (four-agent design)

**How to use this file.** The older deck (`DRISHTI_SIH26102_Final.pptx`) is used here **only as the list of questions**
the slides must answer: its headings and boxes. Its answers are **not** our design; many are outdated or wrong (§9 lists
what to drop). Every answer below comes from the four-agent design decided on 3 Oct 2026
([`docs/plans/T120-four-agents.md`](../plans/T120-four-agents.md)), and every number from a saved measurement
(sources in §10).

- **Rules for the deck itself:**
  - "needs checking", never "fraud" about a work or a person;
  - only measured numbers; a target is called a target;
  - MPs are never scored;
  - no "better than X" anywhere except one comparison on the final References slide (AGENTS.md §7).
- **Built / to build:** each section marks what exists today (✅) and what is designed but not yet built (🛠).
  Judges ask; never present 🛠 as working.

---

## Slide 1 · Title

| Field | Answer |
|---|---|
| Problem Statement ID | SIH26102 |
| Title | Development of an AI-powered system to detect anomalies, fraud, and inefficiencies in MPLAD Scheme implementation |
| Theme / Category | Smart Automation / Software |
| Team | NeuralNexus, Team ID 121911 |
| Our tagline | **DRISHTI: four agents that each flag only what is likely fraud, and prove it** (suggested) |

---

## Slide 2 · Idea

### Problem (one or two lines)

Every MPLADS work is a claim on paper: a recommendation, an estimate, dates, and a "completed" tick. Today nothing
checks those claims against the ground, the official rates or each other, and the record itself is too thin to judge
from. Measured on eSAKSHI's own data:
- **60%** of works are sanctioned after the 75-day limit (median wait: 90 days).
- **832** works were recorded **complete within 7 days of sanction**, 195 of them constructions of ₹5 lakh or more. One
  community hall in ten was "finished" within about a day.
- **A quarter** of completed works carry **no picture at all** (9,300 of 36,508).
- The record has no size: **0 of 1,129** Uttar Pradesh CC-road records state a width. A price question from the record
  alone was right **0 times in 15**.

### Proposed solution (two or three lines)

DRISHTI adds two things the portal does not have:
- a **cost estimate form** the implementing agency fills before sanction (every line, the size, map pins, the time it
  will take);
- a **monthly site video** filmed in our app at fixed spots on the site.

Four agents then check each work. **Cost**, **Duplicate Work**, **Time & Rules** and **Site Progress** each flag only
what is likely fraud. Their findings become a 0–100 score with the top three reasons in plain words, and an inspection
list for the district.

### Detailed explanation (the four agents)

| Agent | The question | It flags | Certain because |
|---|---|---|---|
| **Cost** | Is every line fairly priced for this district, and is the whole estimate fair? | The whole estimate clearly above its fair price (starting line: 15% and ₹50,000), naming the lines that make the gap | Lines are priced against the state's official Schedule of Rates and the district's own recent rates. Quantities are checked against the size. |
| **Duplicate Work** | Is this work already sanctioned here, or one job cut into pieces to stay under a limit? | A sanctioned work of the same kind within 50 m; a declared rebuild of a work finished under 3 years ago; every piece of a group 96–100% of a limit | A map pin is a place, not a description. The agency answers about look-alike works on record. |
| **Time & Rules** | Sanctioned on time? Finished in a believable time? | Finished faster than the work can be built, when the videos do not show it being built; unfinished well past its own promised time | Physics (concrete curing, slab props) and the agency's own promised time, checked against the size |
| **Site Progress** | Do the monthly videos show real, new work, at this site, for this work only? | Footage used before; not filmed at this site; a claimed stage not shown two visits running; "complete" not shown | The same fixed viewpoints every month; GPS **and** the picture must both match |

### How it addresses the problem

| The problem | What DRISHTI does |
|---|---|
| Thousands of works, few officers | Every work is screened on each run. Only works with a well-founded finding reach the list (dashboard test: 439 of 40,935 works). |
| Prices hide in averages | The estimate is priced line by line, then judged as a whole: "one costly line can be honest; every line a little costly is a pattern" |
| The same asset funded twice | Map pins within 50 m, plus the agency's own answer about each look-alike sanctioned work |
| Jobs split to stay under a limit | Only the strictest split: 12 of 14 such groups on the dashboard read as one job cut up, and none was wrong |
| Paper completions | "Finished too fast" checked against physics and the videos (its record version read right 25 of 25 times) |
| Photos that prove nothing | Monthly video at fixed viewpoints. Progress is counted only where the same spot was seen last month. |
| Problems found after the money is spent | The form and three agents run **before sanction**; the video starts **before work** |
| Flags nobody can act on | Every flag says what was found, the numbers, and what would clear it |

### Innovation & uniqueness

1. **Certainty from new evidence, not guesses from thin records.** The form gives size, rates and map pins; the video
   gives the ground. We measured that records alone cannot support price or repeat questions (0 of 15; 13 of 16 at
   best).
2. **Judging the whole estimate.** Quiet padding of 15–20% spread over every line is invisible line by line but
   obvious in the total.
3. **A time window from the work's own promise.** The agency's estimated time is checked for believability, then
   becomes the comfort window. Fast but real work is protected by its own videos.
4. **Site Progress with fixed viewpoints and a site map in zones.** You cannot pass off a new corner as progress, film
   another site, or reuse old footage.
5. **Hit rates, not hunches.** Each finding carries how often it was right when checked. A new finding cannot list a
   work alone; officers' verdicts move the rates (the learning loop).
6. **Simple and explainable.** Arithmetic and maps for three agents; AI only where nothing simpler works (judging a
   claimed stage on a video frame).

### What DRISHTI detects, mapped to the problem statement

| Problem statement asks for | DRISHTI's answer | Agent |
|---|---|---|
| Cost irregularities / overruns | Lines above official and district rates; quantities above what the size needs; a padded total; the built size smaller than the estimate's | Cost (+ Site Progress for built size) |
| Duplicate projects | The same place and kind as a sanctioned work; a rebuild too soon; the same footage or site on two works | Duplicate Work (+ Site Progress) |
| Split works | Every piece just under a limit, at one place, by one MP, within 30 days | Duplicate Work |
| Delays | Past its own promised time; sanction past 75 days (an office fact on the report card) | Time & Rules |
| Fraud / funds misuse | Paper completions, built-before-sanction, claimed progress not shown, reused footage | Time & Rules, Site Progress |
| Early warning | The pre-sanction check: the form's answers before the money is committed | Cost, Duplicate Work, Time & Rules |

---

## Slide 3 · Technical approach

### System architecture & workflow (a work's life)

| # | When | Who | What happens | Agents |
|---|---|---|---|---|
| 1 | Day 0 | MP | Recommends the work on eSAKSHI | none |
| 2 | Before sanction | Implementing agency | Fills the cost estimate form: lines, size, map pins, nature (new / continuation), answers about look-alikes, estimated time | Cost, Duplicate Work, Time & Rules |
| 3 | Sanction | District | Sanctions, with the agents' answers in front of it | Time & Rules (75-day clock) |
| 4 | Before work starts | Agency | First site video: the empty site, fixed viewpoints, the site map | Site Progress, Duplicate Work |
| 5 | Monthly | Agency | Video from the same viewpoints, plus a one-line claim | Site Progress, Time & Rules |
| 6 | At random | Officer, or someone other than the agency | A check video within 48 hours | Site Progress |
| 7 | Completion | Agency | Final video; completion on eSAKSHI | Site Progress, Time & Rules |
| 8 | After | Officer | Visits the listed sites; records a verdict | Learning loop: hit rates update |

**Pipeline in five boxes (for the diagram):**
1. **Inputs:** eSAKSHI record, the cost estimate form, monthly videos.
2. **Checks on entry:** typos and impossible values are fixed on the form, never flagged; PII is masked.
3. **Four agents.**
4. **Score:** 0–100, top three reasons, LOW / MEDIUM / HIGH / CRITICAL. CRITICAL needs two agents agreeing.
5. **Action:** review queue, pre-sanction answer, district dashboards; officers' verdicts feed back.

### The detection engines (one box each)

| Agent | How it works | Catches | State |
|---|---|---|---|
| **Cost** | Each line against the SoR item rate, the district's recent rates (5+ forms from 3+ agencies, never the agency's own) or the standard item; quantities against size norms; charges and site conditions against the map; then the fair estimate and the gap | A padded estimate, inflated quantities, a fake hard site, a bigger size than the map holds | ✅ form, quantity norms, standard-item price, MP gap · 🛠 line-by-line and whole-estimate verdict (T121; the SoR data is T096) |
| **Duplicate Work** | Haversine distance between map pins (both ends for roads); the agency's declared links; the strictest split | Repeat at the same site; rebuild too soon; split job | ✅ built (T100) |
| **Time & Rules** | Date arithmetic; a band per kind and size (engineers' minimum + eSAKSHI's measured longest usual time); the comfort window | Paper completion; built before sanction; past promised time; late sanction (fact) | ✅ the record versions (R01, R06, R13, R14) · 🛠 one agent with the window (T122) |
| **Site Progress** | Sealed in-app video; GPS + matching each viewpoint to its earlier views; image fingerprints across all works; zone coverage; change at the same viewpoint; an AI vision model judges the claim (shown / not shown / can't tell) | Reused footage; wrong site; same place as another work; claim or completion not shown; already built at start | ✅ photo fingerprints (99.9% of edited copies), claim-judging frame for photos · 🛠 capture app and video checks (T123, T124) |

### Technology stack (what is actually used)

| Layer | Used today | Added for the four agents (🛠) |
|---|---|---|
| Web | Next.js 16, React, TypeScript, MapLibre (India map on LGD outlines) | Mobile web capture page (camera, GPS, motion sensors); later a small Android app for mock-location and phone-integrity checks |
| Engine / API | Python 3.12, FastAPI | Video checks run offline as jobs |
| Database & login | Supabase PostgreSQL (row-level security), Supabase Auth with roles and district scoping | Tables for videos' readings, fingerprints and zones (no full videos kept) |
| Hosting | Vercel: web and engine on one domain; deploys on merge to `main` | n/a |
| Matching & vision | Image fingerprints (256-bit) | OpenCV feature matching (free); one AI vision model on a free tier with a daily cap, for claim judging only |
| Text | Local OCR (RapidOCR) for plaques; rule-based readers | n/a |
| Phone checks | n/a | Android `Location.isMock()`, Google Play Integrity (free up to 10,000 checks a day) |

Everything is open source or on a free tier (project rule: free tiers only).

---

## Slide 4 · Feasibility and viability

### Feasibility analysis

| Kind | Answer |
|---|---|
| **Technical** | <ul><li>Three of the four agents are arithmetic, maps and dates, built and tested in Python (628 automated tests pass).</li><li>Video checks use free, CPU-only image matching; only one step uses an AI model.</li><li>The live prototype already screens all 2,09,993 eSAKSHI works.</li></ul> |
| **Data** | <ul><li>eSAKSHI's public data supplies the dates, amounts and types (2,09,993 works; 40,935 with sanction dates).</li><li>What it lacks (size, rates, location, the ground) is exactly what the form and video add.</li><li>Official rates (Schedules of Rates) are public PDFs; digitising them is task T096.</li></ul> |
| **Operational** | <ul><li>It fits the existing flow (MP → district → implementing agency). The agency already prepares a detailed estimate before sanction; the form puts it in a structured shape.</li><li>Engineers already visit sites; the video replaces a photo.</li><li>DRISHTI never blocks or approves anything; officers decide.</li></ul> |
| **Economic** | <ul><li>Free and open-source tools on free tiers.</li><li>Videos are reduced to kept frames and readings, so storage stays small.</li><li>AI calls are capped per day.</li></ul> |

### Challenges & risks → strategies

| Challenge | Strategy |
|---|---|
| No labelled fraud cases | <ul><li>Every check is proven on planted cases first (the planted test put 78% of fakes in the top 5%), then read by eye on real works.</li><li>Officers' verdicts become hit rates.</li></ul> |
| Genuine cost differences (terrain, remoteness, specification) | <ul><li>Site conditions widen the fair band only when the map confirms them.</li><li>The specification fields compare like with like.</li><li>Judging the whole estimate ignores one odd line.</li></ul> |
| False alarms | <ul><li>Mistakes are fixed on the form, never flagged.</li><li>A new finding cannot list a work alone.</li><li>CRITICAL needs two agents.</li><li>A late sanction is a fact, not a flag (it would have hit 60% of works).</li></ul> |
| GPS and phone tracking are imprecise (GPS ±5 m; phone AR drifts by metres) | Position on site comes from fixed viewpoints matched by the camera; GPS only says "this site" |
| No real forms or videos yet | <ul><li>Pilots: 20–50 real estimates (T098) and a 3–5-site field trial (T126).</li><li>Each check stays off until it meets its target.</li></ul> |
| Sensitive data and public code | <ul><li>Role and district scoping, row-level security, PII masking.</li><li>Faces blurred.</li><li>No videos or names in the repository.</li></ul> |

### Loopholes: how someone could try to cheat, and how it is closed

> This is the box judges probe hardest. ✅ = closed by a check that exists today; 🛠 = closed by the design, being
> built.

**Cost**

| Loophole | How it is closed |
|---|---|
| Raise every rate a little, so no single line looks wrong | Whole-estimate gap: the extras add up in the total 🛠 |
| Inflate quantities instead of rates | Quantity norms for the size (cement per m³, bricks per m³, pavers per m²) ✅ |
| Claim a bigger size | Road length must fit between its two map pins ✅; the site video measures what was built 🛠 |
| Name items the system does not recognise | Below 60% of the money compared, the officer sees "can't check" and the share unrecognised 🛠 |
| Claim a hilly, far or carry-by-hand site to justify extra cost | Terrain and access come from the map pin; a contradicted claim widens nothing 🛠 |
| Quote a Schedule of Rates code but a higher rate | The form shows that code's official rate; a different rate needs a reason 🛠 |
| All agencies in a district raise rates together | The official rates cap the district band; an agency never counts in its own baseline 🛠 |
| Pay for a standard item (lights, masts) at an inflated unit price | Unit price against the district's real works: above the 98th percentile + 25% and above the MP's amount + 10% ✅ |

**Duplicate Work**

| Loophole | How it is closed |
|---|---|
| Re-describe an existing asset in new words | Map pins within 50 m of a sanctioned work of the same kind; words don't matter ✅ |
| Call a repeat a "continuation" | A continuation must name the earlier work's ID; the claim is on record ✅ |
| Answer "different work" falsely about a look-alike | The answer is signed on record; the first site video shows the place 🛠 |
| Rebuild something finished recently | A declared rebuild of a work completed under 3 years ago is asked ✅ |
| Cut one job into pieces just under ₹5 / 10 lakh | Every piece 96–100% of a limit, one place, one MP, within 30 days ✅ |
| Film one site for two works | The place match across works' viewpoints 🛠 |

**Time & Rules**

| Loophole | How it is closed |
|---|---|
| Record completion the day after sanction (paper completion) | "Finished too fast" (record version: 25 of 25 right) ✅; with videos 🛠 |
| Build before sanction, file afterwards | The first video (or a photo's date stamp) shows it already standing ✅ (photo dates: 3 found) / 🛠 (video) |
| Promise a very long time so the work is never late | The window caps at the usual longest time for that kind and size 🛠 |
| Promise a very short time to make a fake fast finish look planned | "Too fast" is judged against physics and the videos, not only the promise 🛠 |
| Invent lost months after the fact | Lost months are declared on the form before sanction 🛠 |
| An office records every completion on sanction day | The office's habit is named once, and its works score low, so one office cannot flood the list ✅ |

**Site Progress**

| Loophole | How it is closed |
|---|---|
| Upload an old or downloaded video | Filming only in the app; fingerprints against all earlier footage 🛠 (photo version ✅ 99.9%) |
| Film a different, finished site | GPS **and** the views must both match this site's earlier views 🛠 |
| Fake the GPS with a mock-location app | Mock-location flag, phone integrity check, and the views must still match 🛠 |
| Film a screen playing a video | The phone's own motion does not match the motion in the picture 🛠 |
| Show a new corner each month as "progress" | Progress is counted only zone by zone against the same zone last month 🛠 |
| Film only the finished part | The app won't finish until every viewpoint is matched 🛠 |
| Dress up the site for the filming day | Random check videos within 48 hours, by someone else 🛠 |
| Edit the video | The seal (signature over video, GPS, motion and time) breaks 🛠 |

**The system itself**

| Loophole | How it is closed |
|---|---|
| An officer sees other districts' data | District scoping in every query, row-level security ✅ |
| A user forges a login | The engine verifies every access token itself; the local test login is refused on the hosted site ✅ |
| Someone games the score by knowing the weights | A finding moves the score only by its measured hit rate; CRITICAL needs two independent agents ✅ |

### Viability

| Point | Answer |
|---|---|
| Human control | DRISHTI asks; officers decide. Every flag reads "needs checking" with its facts; nothing is blocked automatically. |
| Existing workflow | Same MP → district → agency flow. The estimate and the site visit already exist; DRISHTI gives them a structured form and a guided video. |
| Priority-based action | Only well-founded findings reach the list: 439 of 40,935 dashboard works (about 1%), so officers' time goes where evidence is strongest |
| Modular | Each agent is a folder with one contract. Agents can be added or retired without touching the others (the old Cost Anomaly was retired this way). |
| Adapts to rule changes | The limits are settings: 75 vs 45 days, margins, the window's grace. The 2023 guideline text is being confirmed (T001). |
| Gets better with use | Each officer verdict updates that finding's hit rate (the learning loop) |

---

## Slide 5 · Impact and benefits

### Impact on stakeholders

| Stakeholder | What they get |
|---|---|
| **Ministry (MoSPI)** | <ul><li>A national view of where works are listed for checking, by state and district.</li><li>Office report cards: share of late sanctions, median wait.</li><li>Evidence-backed facts for Parliament: "60% sanctioned past 75 days" is measured, not estimated.</li></ul> |
| **State nodal authorities** | <ul><li>Compare districts on sanction speed and on works listed.</li><li>Follow up works past their own promised time.</li></ul> |
| **District authorities** | <ul><li>A pre-sanction answer on every estimate.</li><li>A short, ranked review list with reasons.</li><li>Monthly progress they can see without travelling.</li></ul> |
| **Implementing agencies** | <ul><li>Honest work is protected: a fast real finish is shown on video, and an odd but honest line does not trigger a question.</li><li>Mistakes are fixed on the form, not held against them.</li></ul> |
| **MPs** | <ul><li>See the status of their recommended works.</li><li>DRISHTI never scores MPs.</li></ul> |
| **Citizens** | Assets that really exist, at the place and size paid for |

### Benefits

| Social | Economic | Environmental |
|---|---|---|
| Trust that a "completed" asset exists; faster completion when stalls are seen monthly | Padding caught before sanction, when money can still be saved; officers visit the right sites | Fewer wasted site trips (video first, visit when needed); paperless estimates and monitoring |

### Expected outcomes (measured vs target, labelled honestly)

| Measure | Value | Kind |
|---|---|---|
| Works screened | All 2,09,993 eSAKSHI works on each run | ✅ done |
| Planted fakes in the top 5% of the score | 78% (50 fakes); 74.3% on the 810-problem test country | ✅ measured |
| Works reaching the review list | 439 of 40,935 dashboard works (about 1%) | ✅ measured |
| Cost: padded estimates caught (20%+) | 9 in 10, with at most 2 in 100 honest estimates asked | 🎯 target (T121) |
| Time & Rules: "finished too fast" worth checking | 9 in 10 (its record version: 25 of 25) | 🎯 target (T122) |
| Site Progress: each cheating trick caught | 9 in 10, with a finding on at most 1 in 30 honest visits | 🎯 target (T126 field trial) |
| Every estimate checked before sanction | Yes, once agencies file the form | 🛠 |

---

## Slide 6 · Research & references

### Comparison (the only slide where a comparison is allowed)

Compare **capabilities**, not claims about others' quality. Mark only what DRISHTI really has.

| Capability | DRISHTI | eSAKSHI portal today | Manual inspection |
|---|---|---|---|
| Estimate priced line by line against official and district rates | 🛠 | ✗ | Partial (an engineer checks some) |
| Repeat detection by map pin, with declared continuations | ✅ | ✗ | Partial |
| Split-work detection (strictest rule) | ✅ | ✗ | ✗ |
| Paper-completion detection (finished too fast) | ✅ (records) | ✗ | Partial |
| Monthly progress at fixed viewpoints, with reuse and location checks | 🛠 | ✗ (photos, often none) | Partial (occasional visits) |
| Explainable 0–100 score with top three reasons | ✅ | ✗ | ✗ |
| Pre-sanction check | ✅ | ✗ | ✗ |
| Learns from officers' verdicts (hit rates) | ✅ mechanism, awaiting real verdicts | ✗ | ✗ |

### References

**Government and policy**
- MPLADS Guidelines (2016 text in hand; 2023 text being confirmed, T001)
- eSAKSHI portal and its public dashboard tables (downloaded 2 Oct 2026)
- State PWD Schedules of Rates; CPWD Delhi Schedule of Rates and cost index (T096)
- GeM (Government e-Marketplace) prices
- IS 456:2000, *Plain and Reinforced Concrete* (curing cl. 13.5.1; formwork cl. 11.3)

**Technical sources**
- GPS.gov, "GPS Accuracy": smartphones about 4.9 m under open sky
- *Sensors* 2022, 22(24):9873, "A Benchmark Comparison of Four Off-the-Shelf Proprietary Visual–Inertial Odometry
  Systems" (phone AR drift)
- Android developer reference: `Location.isMock()`; Google Play Integrity API
- OpenCV (feature matching); RapidOCR

**Our own measurements**
- `docs/trial/FINDINGS.md`
- `data/trial/results/`
- the plan `docs/plans/T120-four-agents.md`

**Prototype:** the GitHub link (the repo is public) and the demo video link.

---

## 7. Questions judges are likely to ask, with short answers

| Question | Answer |
|---|---|
| Is this AI or just rules? | Both, used where each is right. Cost, Duplicate and Time are arithmetic, maps and dates, because those can be certain. AI judges what a video frame shows against the agency's own claim. We measured that "AI on the record alone" could not be certain (0 of 15 price questions right). |
| What if the agency doesn't fill the form? | The work shows "no form: not checked", never a low score. Filing the form is part of getting sanction in the proposed flow. |
| Can't the agency just lie on the form? | Its answers become checkable promises: map pins are checked against videos, sizes against what is built, rates against official ones, "continuation" against the earlier work's ID. A lie on the form is a signed fact on record. |
| How do you avoid flagging honest work? | <ul><li>Mistakes are fixed on the form.</li><li>One odd line doesn't count; the whole estimate does.</li><li>A fast finish shown on video is fine.</li><li>One bad month never counts.</li><li>New findings start at a 1-in-4 hit rate and cannot list a work alone.</li></ul> |
| What is your accuracy? | Measured so far: 25 of 25 (paper completion, records), 12 of 14 (strict split), 78% of planted fakes in the top 5%. The new checks have targets, not results yet, and stay off until they meet them. |
| Why is late sanction not a red flag? | 60% of works break the 75-day limit. Flagging it would list most works and hide the real cases, so it goes on the office's report card. |
| GPS can be faked. | Yes, so GPS is never enough alone: the camera's view must match the site's own earlier views, and Android reports mock locations. |
| What does it cost? | Free and open-source tools on free tiers; videos are reduced to frames and readings; AI calls are capped. |
| Privacy? | Faces blurred; no names kept; district-scoped access; nothing personal in the public code. |
| What about old works with no form or video? | The record checks still run (split, paper completion, impossible dates). Repeat checks gain pins as new videos arrive. |

---

## 8. One-line answers per box (for the slide text itself)

| Box | Text |
|---|---|
| Problem | MPLADS works are paper claims; 60% are sanctioned late, some are "finished" in a day, and a quarter of completed works have no picture. |
| Proposed solution | A structured estimate before sanction, a guided monthly site video, and four agents that flag only likely fraud, with reasons. |
| How it addresses | Priced line by line, pinned on the map, timed against its own promise, filmed at fixed spots. |
| Innovation | Certainty from new evidence; judging the whole estimate; a time window from the work's own promise; progress counted only where the same spot was seen before. |
| Feasibility | Three agents are arithmetic and maps (built); video checks are free image matching plus one capped AI step. |
| Viability | Officers decide; the existing flow is unchanged; the list is about 1% of works. |
| Impact | Padding caught before money moves; paper completions caught; honest work protected. |

---

## 9. What to drop or correct from the old deck

| Old deck said | Why it goes | Say instead |
|---|---|---|
| "Pre-sanction check inside the 45-day window" | The 2016 guidelines say 75 days for sanction; 45 is unconfirmed for 2023 (T001). The team uses 75. | "before sanction (75-day limit)" |
| Guideline-as-Code engine checking all rules, each citing the para | Retired: the four agents keep only the timing rules | Time & Rules: the sanction clock and believable timing |
| Expected-cost model per type and state; Isolation Forest + LightGBM; "₹18 L road vs ₹6–9 L usual" | Record-only price questions were right 0 of 15; the old model caught a doubled price 18% of the time | Cost on the agency's form, line by line, then the whole |
| Hindi–English duplicate finder, multilingual text match | Never built; words alone are right about 2 in 3 at best | Map pins and the agency's declared answers |
| Delay prediction (XGBoost) | 0.71, against 0.68 for simply using the office's record; retired | The comfort window from the agency's own estimate |
| SHAP top-5 reasons | Not used; the reasons are the findings themselves | Top three reasons, in plain words |
| "Spend > sanction" | On all 36,430 works with a disbursed amount, spend ≤ sanction; it catches nothing | Remove |
| SMS / email alerts, PDF brief, shortest-route inspection plan | Not built | Mark as planned, or remove |
| Celery, Redis, PostGIS, XGBoost, LightGBM, PyOD, FAISS, Sentence Transformers, OR-Tools, Docker, Nginx | Not in the product | The real stack (Slide 3 table) |
| "≥ 75% planted anomalies caught in top-5% (target)" | Now measured | "78% of 50 planted fakes in the top 5% (measured)" |
| "Learns from the field: geo-tagged officer verdicts become labels" | The mechanism exists, but no real verdicts are collected yet | "Each finding's hit rate updates with officers' verdicts" |
| "100% of works screened every day" | Screened on each batch run, not on a daily schedule | "All 2,09,993 works screened" |
| Comparison table marking us ✓ on everything | Must show only what is real; comparison only on the References slide | The table in Slide 6 above |

---

## 10. Sources for the numbers

| Number | Source |
|---|---|
| 60% past 75 days; median 90 days; 832 complete within 7 days; 195 ₹5 lakh+ constructions; halls p10 1.3 days; 9,300 of 36,508 with no picture | `data/trial/results/four_agents_timing.txt` |
| 0 of 1,129 road widths | FINDINGS T095 |
| 0 of 15 record price questions; words 13 of 16; strict split 12 of 14; dashboard list 439 of 40,935 | FINDINGS "T099 + T100" (PR #106) |
| R14 25 of 25 | FINDINGS T055 (reliability table) |
| 78% of planted fakes in the top 5% | FINDINGS T080 |
| 74.3% on the test country | FINDINGS T055 |
| Old cost model, doubled price 18% | FINDINGS A3 |
| Delay model 0.71 against 0.68 | FINDINGS C1 |
| Photo fingerprints 99.9%; 3 works dated before recommendation | FINDINGS B2, B3 |
| Spend ≤ sanction on 36,430 works | Plan T099–T100 §1 |
| 628 tests | `pytest -q` on PR #106 |
| GPS 4.9 m; phone AR drift; Play Integrity 10,000 a day | Plan T120 §17 |
