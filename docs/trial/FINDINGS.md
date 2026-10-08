# DRISHTI agents on real works: what works, what doesn't

**Trial run 25–26 September 2026.** All figures come from the scripts in `data/trial/`, and
their outputs are in `data/trial/results/`. Every example quoted here was checked by eye
before it was written down. "Needs checking" never means wrongdoing. It means an officer
should look.

---

## The short version

| Agent | Verdict | One line |
|---|---|---|
| **Four agents** *(T121–T125, 4 Oct 2026)* | **Built; two wait on real evidence** | Cost judges every line, then the whole estimate (synthetic forms: target met at a 10% honest spread with district rates). Time & Rules: the 75-day clock as an office fact, the comfort window. Site Progress reads monthly videos (end-to-end trial on made-up scenes). Dashboard queue 439 → 217. |
| A3 Cost *(T099: on the form)* | **Certain only with the form** | A record alone supports no certain price question (0 of 15 real, T099). The Cost check reads the agency's cost estimate form; the old Cost Anomaly (54/128) is retired. |
| A2 Split works *(T100: strictest only)* | **Works** | Real pattern: 12× more works just under ₹5 lakh than just over. Kept only the strictest split: every piece 96–100% of a limit, 12 of 14 dashboard groups read as one job (2 grey). |
| A2 Duplicates *(T100: by map pin)* | **Partly, by words; certain by map pin** | Words alone are right about 2 times in 3 at best (T099 + T100); repeats are now asked by the form's map pin and the agency's declarations. |
| A2 Duplicates *(before T100)* | **Partly** | 48 cases of one named site recommended again while the first was still open; about 19 of them look like one asset funded twice. Exact wording finds nothing once the first work is complete, so real repeats are reworded. Matching by meaning is not built yet. |
| A1 Eligibility | **Works after a rewrite** | On a fresh sample, 56% of what it flags plainly reads as prohibited, and 80% is worth an officer's look. |
| C1 Delay prediction | **Weak** | Scores 0.71 on a 0.5–1.0 scale, against 0.68 for simply using the office's past record. Better sold as office track records. 7 in 10 works miss the one-year target anyway. |
| C2 Fund flow | **Facts work; forecasts can't be tested** | 21,323 works (₹1,361 cr) are still waiting for sanction past 75 days. A "year-end rush" signal turned out to be a portal cycle and was dropped. |
| B4 Document | **Works on typed certificates, free** | Local text reading (no AI service) reads the sanction date, payments and contractor off 431 Uttar Pradesh certificates. It shows 16% of works were sanctioned after the 75-day limit, and that the paper for 282 of 285 "completed" works still says "in progress". About half of other states' papers (Hindi, handwritten) need AI reading. |
| C3 Contractor | **Works where certificates exist** | The vendor code is an exact identity. In Pratapgarh, 3 vendors hold 84% of the 261 works we could read. |
| B2 Photo reuse | **Works** | Recognises 99.9% of edited copies (crops, stamps, screenshots). The pilot has no disguised copies, but 5 exact files sit on different works, and 2 of those need checking. |
| B3 Geo-location | **Works** | GPS stamps were read on 170 works, and all fall inside their own district. The date check caught 3 works whose own photos show them finished *before* the MP recommended them. |
| B1 Site progress | **Not tested** | Needs an AI vision key. |
| B5 Satellite | **No-go for now** | The pilot has no large works that also have GPS coordinates. |
| D1 Citizen | **Can't be tested** | 21,789 of the 21,793 citizen ratings on eSAKSHI are zero. |

---

## What we tested on

- **2,09,993 real works** from the eSAKSHI export (snapshot 26 May 2026).
- **Real evidence for 837 completed works:**
  - every completed work with evidence in Pratapgarh, Uttar Pradesh (437)
  - 400 completed works picked at random from across India
- **905 files, 791 MB**, downloaded from eSAKSHI's public endpoints.
  - One request every 1.5 s, 64 minutes.
  - One work's listing failed to download.
  - Files stay on this PC (gitignored).
- **1,925 pages and photos read by open-source text reading (OCR) on this PC** (1,604 PDF pages
  and 321 photos). No AI service, no key, no cost.

---

## Agent by agent

### A3 Cost *(built)*: works for big mark-ups

**Method:**
- Take 1,000 real works that read as typical.
- Rebuild the price bands without them.
- Inflate each by 1.5×, 2×, 3×, 5× and 10×.
- Count how many the agent catches. Count false alarms on 20,000 untouched works.

| Mark-up | DRISHTI cost agent |
|---|---|
| 1.5× | 0.4% |
| 2× | 18% |
| 3× | 39% |
| 5× | **63%** |
| 10× | **84%** |
| False alarms | 1.5% |

**On its own**, the price finding puts only 0.11% of normal works in the review queue, and
it catches 18% of 5× mark-ups and 36% of 10×. That is deliberate: price alone should rarely
queue a work.

**Meaning:** comparing a work with similar works in its own district catches large mark-ups reliably.
Mark-ups under 2× hide inside normal price variation, so they need a second signal, such as
the document agent reading quantities.

#### Cost engine v2 (T020, 30 Sept 2026): fixing the odd prices

The live version's strangest flags were not price questions at all. A library building was judged
against book orders ("hundreds of times typical"), many works showed the same "5.0x", and every
queued work was "Medium". Version 2 compares like with like: a library building is judged against
other library buildings, not book orders. Works with no real description are marked "can't tell".
Lists of sites are read as several jobs, not one inflated price. A work is flagged only above 2× the
top of its district peers and above the state/national top. A second check, a price model learned
from description words, must agree (inside its 10–90% range for 80.2% of works, tested
constituency by constituency).
Script `data/trial/cost_trial_v2.py`, results `results/cost_trial_v2.json`, labels `cost_v2_labels.py`.

| | live v1 | v2 (rules + model) |
|---|---|---|
| 5× mark-ups caught | 63% | 55% |
| 10× mark-ups caught | 82% | 82% |
| False alarms on 20,000 untouched works | 1.7% | **1.3%** |
| Real price questions among the 30 highest-ranked flags (fresh sample, rules frozen) | **0 / 30** | **10 / 30** |
| Real price questions among 30 random flags (same sample) | 10 / 30 | 5 / 30 |

"Real price question" = read by eye: one described job at one site, compared with the same kind of
work, and the amount looks high. **Meaning:** v2 fixes the top of the list, which is what an officer
reads first. It is not yet better on a random flag: half of its random flags are "several sites
bundled" or "check what it covers" notes, which by design make no price claim (0/12 and 3/11). Among
flags that do claim a price is high, both versions score about a third (v2 11/32, v1 10/32). v2 also
catches fewer 5× mark-ups because the model must agree. Two earlier samples were used to fix the
rules and are not counted here.

### A2 Split works and duplicates: a real pattern

**Bunching at the limits:**
- 12.1× more works sit just under ₹5 lakh than just over it, and 11.5× at ₹10 lakh. Other
  round sums show 1.9–5.4×.
- The round sum itself is counted separately. 20,533 works are exactly ₹5 lakh.
- Districts where 4.6% (the national share) would be normal:

| District | Share of works at ₹4.8–5 lakh |
|---|---|
| Kolar | 58.8% |
| Darbhanga | 54.4% |
| Sitamarhi | 44.3% |
| Mahabubabad | 38.3% |

**Same-site splits:** Nanded, "Construction of Cement Concrete Road At Sapti Tq Hadgaon".
- 3 works at ₹4,96,000 each, recommended the same day (13 May 2025), all sanctioned.
- ₹14.88 lakh together, in pieces just under ₹5 lakh.
- *(An earlier chat message said four pieces. The data shows three.)*

**Bulk orders kept under the limit:**
- The rule: identical text, same district and work type, each work recommended within 60 days
  of the last, every piece ₹4–5 lakh, total over ₹5 lakh.
- It finds **136 groups (744 works)**.
- *(An earlier chat message said 108 groups and 602 works, from a one-off query. These figures
  come from the saved script.)*

| District | Works | Total | What and when |
|---|---|---|---|
| Sitamarhi | 48 | ₹2.39 cr | High-mast lights, within 7 days |
| Gumla | 58 | ₹2.32 cr | Book purchases, one day |
| Eluru | 50 | ₹2.00 cr | Lab equipment, one day |

**Read the description before judging.** A description that names a place points to a
same-site split. Generic text points to a bulk purchase cut under the tender limit.

**The same named asset funded twice:**
- Of 1,34,326 works whose text names a specific site, 1,828 share that exact text with
  another work in the same district.
- Most were recommended within 60 days of each other: batches or splits.
- 48 pairs were recommended again **more than 60 days later, while the first was still
  open**. Reading them one by one: 19 look like the same asset funded twice, 20 look like a
  staged or top-up payment or a resubmission, and 9 name no real site. Examples:
  - Prakasam: 3 RO plants (named villages), sanctioned under the 17th Lok Sabha and sanctioned
    again under the 18th, same text.
  - Kancheepuram: smart-class equipment for one school, both works marked complete.
  - Malappuram: a school bus for one school, completed, then sanctioned again.
- **What didn't work:** the same exact text recommended again *after* the first was
  completed: 0 cases. Real repeats are reworded, so the next step is matching by meaning.

#### Duplicate & Split engine (T030, 30 Sept 2026): matching by meaning

Every description (207,881 with readable text) is turned into a meaning vector by a free
multilingual model, so "CC road at X" and "X me CC sadak" match. Works are compared only within
their district. Script `data/build_dup_split.py`, results `results/dup_split.json`, by-eye
labels `data/trial/dup_split_labels.py` → `results/dup_split_eye.json`.

| What it finds | Count |
|---|---|
| Pairs that read as the same work twice | 953 (121 after the first was completed, 740 while it was open, 92 staged and not flagged) |
| Same-site splits (2+ near-equal pieces naming one place) | 1,993 groups |
| Bulk orders (3+ near-equal pieces naming no place) | 1,114 groups |
| Groups with every piece ₹4–5 lakh and a total over ₹5 lakh | 456 |
| Works carrying any flag | 23,236 (11%) |

The Nanded Sapti split (3 × ₹4,96,000, same day) is found and marked "every piece just under
₹5 lakh".

**Read by eye (fresh samples, rules frozen):**

| Sample | Real repeats / splits |
|---|---|
| 40 random duplicate pairs | **15 / 40 (38%)** |
| 15 random same-site splits | **10 / 15 (67%)** |
| 15 random bulk orders | 15 / 15 correctly read as a series of identical purchases |
| Top 50 pairs by score (development sample) | 29 / 50 |

**What reading the output fixed** (each fix was followed by a fresh sample):
1. The first version put 31% of all works in "groups". It chained an MP's batch of alike works for
   *different* villages ("CC road at Sapti", "at Walki", ...) and then threw the whole chain away
   because the amounts differed, losing the Sapti split with it. Groups are now cut by place.
2. Different survey numbers, property numbers or road stretches ("0–300 m" vs "301–600 m") had
   matched, because place words ignored numbers. Different numbers now mean different sites.
3. Wording one MP filed 3+ times (7 identical water coolers) is a series, not a duplicate: a real
   duplicate is a pair.
4. A shared panchayat name made two villages "the same place". The first random test read only
   7/40 real; after requiring the whole place list to match, a new random test read 15/40.

**Still wrong, known:** generic text with an unusual word taken as a place ("Yatri pratikshalaya",
"Disposal of sullage water"); "Construction of..." followed by "Completion of..." (a staged
payment); "East side" and "West side" of one street (direction words are too common to count as
place words). Every flag says "check", never more: the district is the finest location in the
record, so only the files or a visit can confirm two works are one.

### A1 Eligibility (prohibited works): works after a rewrite

| Reader | Works flagged | Plainly prohibited | Worth an officer's look |
|---|---|---|---|
| v1: word must be the object of the work *(built)* | 642 | 12% (7 of 60) | 25% |
| **v2: v1 + fixes from reading its mistakes** | **458** | **56% (28 of 50)** | **80%** |

**Honest scoring:**
- The v2 fixes were found on one sample of 50. The figure above comes from a **fresh** sample
  of 50, read after the rules were frozen.
- Checking what v2 leaves out: of 20,553 works that merely mention a prohibited word, 0 of 60 read as plainly prohibited
  and 2 as worth a look. So v2 misses little.

**What v2 fixed:**
- **Ration, fair-price and PDS shops** are government outlets, not commercial ones.
- **Landmarks written after the name** show the temple is only a landmark: "mandir ke pas",
  "temple to …", "masjid road".
- **"Shishu Mandir", "Vidya Mandir", "Ranga Mandir"** are schools and halls.
- **New:** works *inside* temple premises ("mandir prangan", "temple campus").

**What it finds:**
- solar lights inside temple campuses, including a series in Rae Bareli "on request of" named
  individuals
- community halls built on temple premises
- "construction of a community temple"
- welcome gates

**Caveats:**
- The verdicts are our reading, not an official ruling.
- The prohibited list is the 2016 Annexure-II. The 2023 text is still not verified, because
  mplads.gov.in refuses connections from outside India.
- Maintenance and statue items stay "worth a look", not "prohibited".

### C1 Delay prediction: weak, so ship it as a track record

**Strict backtest:** pretend today is 1 Jan 2025. Train only on outcomes known then (works
recommended in 2023), and test on works recommended from January to May 2025.

| Measure | Model | Office's past record | Work type's past record |
|---|---|---|---|
| Ranking score (0.5 = chance) | **0.71** | 0.68 | 0.63 |
| Late among the riskiest 10% | 81% | 78% | 90% |
| Late among the safest 10% | **19%** | 29% | 69% |

- District-level forecasts are weak (rank correlation 0.43).
- **The real finding:** 71–77% of works miss the one-year target. Delay is system-wide, not a
  few bad works.
- **Stuck works (a plain count, no model):** of 97,808 works recommended between April 2023
  and May 2024, **40,489 (41%, ₹2,178 cr) are still not complete two years later**:
  - 37,658 were sanctioned but never finished
  - 2,831 were never even sanctioned
  - 7,590 of them are street lights, which normally take weeks
- **Use:** show each office's track record, and the stuck works, plainly. Present the model as
  a ranking aid, never as an accurate prediction.

### C2 Fund flow: facts yes, forecasts no

**Money** (MP-level files, summed by term; DRISHTI never scores MPs):

| Term | Allocated | Spent | Completed works |
|---|---|---|---|
| 17th Lok Sabha (ended June 2024) | ₹4,768 cr | ₹3,783 cr (79%) | 53% of recommended value |
| 18th Lok Sabha so far | — | 27% of allocation | — |

**Sanction backlog:**
- 21,323 works (₹1,361 cr) are still shown as waiting for sanction more than 75 days after
  recommendation. The median wait is 239 days.
- 3,331 of them (₹169 cr) were recommended under the 17th Lok Sabha, whose term has ended.
- Districts with the most of their works waiting:

| District | Share waiting |
|---|---|
| North Goa | 69% |
| Rayagada | 63% |
| Shrawasti | 58% |
| Mumbai | 53% |
| Nanded | 52% |
| Sangareddy | 52% |

**Pre-election rush:**
- 45,167 recommendations in January–March 2024, the most of any quarter, then 115 in
  April–June.
- Only 17% of the rush works finished within a year, against 29% for July–September 2023.

**Trap avoided:**
- A "March rush" looked strong: 47–61% of completions fell in January–March in two of three
  years.
- But it vanished in 2024-25, and April–May show almost no completions. That points to a
  portal cycle, not office behaviour.
- **Rule:** compare an office to the same period nationally, never to a flat average.

**Not testable:** forecasting whether funds will lapse. The public files are a single
snapshot with no payment dates. The certificates below do carry payment dates, so the
Document agent can fill this gap.

#### Delay & Fund Flow engine (T410, 1 Oct 2026): Fund Flow inside the Delay engine

`data/trial/delay_fund_flow_trial.py` → `results/delay_fund_flow.json`, all 2,09,993 works: **3,331 works (₹168.9
crore) recommended under the ended 17th Lok Sabha are still not sanctioned**, exactly the trial's figure; the term's
end date is reference data (`rules.json` "terms"; Rajya Sabha terms are per member and not modelled). 131 works of
3 offices hold at least twice their district's share of old recommendations still waiting (e.g. 59 of 125, 47%,
against 268 of 1,841, 15%, in its district); read by eye, each sentence carries that office's own counts. The
first cut for "likely late" (estimate ≥ 0.90) warned on 23,476 open works (43%): most offices finish few works
within a year. The cut is now the riskiest tenth of open works, stored with the counts (5,475 works).

### B4 Document: works on typed certificates, with free local text reading

**What the certificates contain.** Uttar Pradesh uploads the portal's own Utilisation
Certificate (Annexure-VI), printed, signed and scanned. It carries:
- implementing agency
- work name and location
- **sanction date**
- sanctioned amount
- **vendor name and vendor code**
- work status
- each payment's date, amount and bank reference

**Reading accuracy:**
- Six certificates were compared field by field against the page image. All values were
  right; the OCR sometimes drops spaces.
- The OCR sometimes skips the long sanction-date line. The date is then taken from the
  certification paragraph, which repeats it.
- Fields found on 431 certificates:

| Field | Found on |
|---|---|
| Amounts, payment dates, status | ≥ 99% |
| Vendor | 98% |
| Implementing agency | 91% |
| Sanction date (not printed on the older version of the form) | 69% |

**Checks against the portal:**
- **Right document:**
  - 284 of 286 files carry only their own work's certificate. None lacks one.
  - 2 also carry another work's final certificate.
  - Useful fact: the portal's "amount" is what was **paid**, and it equals the sum of the
    certificate payments.
- **Sanction delay (real dates, 211 works):**
  - Median 68 days.
  - **16% sanctioned after the 75-day limit.** If the 2023 rule is 45 days, 97% are late.
  - 1 certificate shows sanction 13 days *before* the portal's recommendation date.
- **Completion evidence:** on 282 of 285 works the portal marks complete, every attached
  certificate still says "in progress". The papers prove payment, not completion.
- **Blank certification:**
  - On 427 of 429 certification pages, the reader found every box empty.
  - All the pages viewed by eye were unticked, with place and date blank.
  - The officer's certification is signed but never filled in.

**Other states' papers:**
- Papers include Hindi bills, measurement books, handwritten notes, completion certificates
  and photo sheets.
- **158 of 308 PDFs (51%) from the national sample have nothing the local reader can use**
  (Devanagari, handwriting, poor scans). These need the AI reader (Gemini).
- Where an English paper shows rupee amounts (95 files), 64 (67%) carry the portal's amount
  within 1%. The rest need structured reading to tell a mismatch from a partial payment or an
  estimate.
- Some scans are upside down or sideways.

#### Paperwork engine (T110, 1 Oct 2026): Document + Contractor in the engine

The certificate reader now lives in the engine (`agents/paperwork/reader.py`); `data/build_evidence.py` runs it
over the pilot's OCR pages and stores only derived facts (dates, amounts, status, vendor CODE, the location line).
`data/trial/paperwork_trial.py` → `results/paperwork_trial.json` reproduces this section: 431 certificates; fields
read 99.8% amounts / status, 97.7% vendor code, 69.4% sanction date; 33 works sanctioned past 75 days on the raw
calendar (**32** once the 2024 election pause is left out, as para 3.12 says), 1 sanctioned before it was
recommended; 282 of 285 completed works with every own certificate "in progress"; 2 of 429 certification pages
marked; Pratapgarh 261 works, 7 vendors, top 39.1%, top three 83.9%.
Read by eye while building it: 12 of 12 first "payments differ" cases were one certificate per instalment (a
₹9,000 instalment of ₹1.86 lakh) or the same certificate twice in one file, so less-paid-on-paper is a note
(0.05) and only more-paid-on-paper is a finding; one file carried two works' certificates (Malakpur, Sherpur,
₹1.07 lakh each) with a description naming neither, so such files say so (9 works) instead of adding the
payments. Shown, not counted: papers exist for the 837 pilot works only.

### C3 Contractor network: works where certificates exist

- The **vendor unique code** (e.g. V9174…) identifies a contractor exactly, so no name
  matching is needed.
- **Pratapgarh:** 261 works, 7 vendors. The top vendor holds 39% of works; the top three hold
  84%. (Across the whole pilot: 19 vendors on 278 works.)
- Most of these works went through one state agency, UP Small Industries Corporation, Kanpur.
- **Caveat:** this is one district, and mostly street lights through one agency. Concentration
  is a fact to show, not a finding on its own.

### B2 Photo forensics: works; the exact-copy check found real cases

**Robustness.**
- **Setup:** 319 distinct real photos, compared across 50,678 pairs from different works.
- **Setting:** each part runs at the loosest setting that confuses no two *different*
  photos.
- **Check by eye:** the 25 closest pairs were all different pictures sharing a layout —
  photographed forms of one template, handwritten photo sheets, numbered handpump prints.
- **Result:** each edited copy of each photo was tested:

| Edit | 256-bit fingerprint | Feature matching (ORB) | **DRISHTI (either)** |
|---|---|---|---|
| Re-save, half size | 100% | 99–100% | **100%** |
| Brighten 25% | 100% | 99.7% | **100%** |
| Stamp band added | 93% | 97% | **99.4%** |
| 2° turn | 87% | 100% | **100%** |
| 8% crop | 10% | 99.7% | **100%** |
| Screenshot frame | 0.9% | 100% | **100%** |
| **All edits** | **70%** | **99.4%** | **99.9%** |

**Real reuse in the pilot:** no disguised (edited) copies turned up. 5 groups of works carry
the **byte-identical file**:

| Where | What | Reading |
|---|---|---|
| Pratapgarh | One road photo on two different interlocking roads (WS/MP807/2023-2024/32921 and /32924), both completed 24 Aug 2025 | The photo's file name, "shivgarh jamtali", names the *first* work's village. The second work shows another road's photo. **Needs checking.** |
| Narmadapuram | One "work complete certificate" file on two works for two different named beneficiaries (₹95,000 each) | Hindi, so the local reader can't tell whose it is. **Needs checking.** |
| Neemuch | One invoice on 3 water-tanker works | The invoice lists 18 villages: a combined bulk order |
| Betul | One utilisation certificate on 2 works | It lists 48 items: a combined certificate |
| Anantnag | One contractor file on 2 solar-light works | Likely a combined file |

**Lesson:**
- **Image fingerprints are useless on certificates.** Portal forms and photographed templates
  look alike, which gave 59,054 false "matches" in a first run. Documents must be compared by
  their text.
- **Combined files are normal.** An exact copy only matters when the file names a single work
  or person.

#### Photo Evidence engine (T310, 1 Oct 2026): B2 + B3 + citizen photos in the engine

The stamp reader, the district check (pure Python, `agents/photo_evidence/geo.py`) and the reuse checks now live in
the engine; `data/build_evidence.py` stores each file's stamp facts and 256-bit fingerprint.
`data/trial/photo_evidence_trial.py` → `results/photo_evidence_trial.json` reproduces B2 and B3: 190 stamps on 170
works; 187 inside the work's district, 2 within 5 km of its border, 0 further; PIN agrees 66, differs 3; the 3
works whose own photos predate the recommendation (WS/MP070/2023-2024/7171, WS/MP720/2024-2025/124252 and 124508);
the one shared spot and day; the 2 byte-identical files that need checking flagged (the road photo on two
Pratapgarh works, the completion certificate on two Narmadapuram works) and 0 of the 3 combined files. Two traps
found: works with papers but no photo were skipped by the first version (now checked for reuse), and the PIN file
carries Census-2011 district codes like the works do. The combined-file rule (3+ pages or 50+ text lines) rests on
these 5 cases only. Edited copies are matched by fingerprint alone in the engine (70% of edited copies in the
trial; ORB, 99.4%, needs OpenCV and stays out). The trial's stamp-year window ended in 2026; it is now relative.

### B3 Geo-location

- **Phone GPS data is gone.** 0 of 321 photos carry it (Pratapgarh and national alike); upload
  strips it. The only location is the text that GPS-camera apps (NoteCam, GPS Map Camera,
  AngleCam) stamp into the picture.
- **The stamp is readable locally.**
  - Found on 190 photos and pages, covering 170 works (20% of the pilot).
  - Checked by eye on 12: the coordinates were right on all 12.
- **Date-reading fixes, found by checking:**
  - Dates were right on 10 of 12 until two fixes.
  - US-style dates from one app (07-19-2024) are now read correctly.
  - A misread year ("2026" for "2025") is corrected using the printed weekday.
  - A third fix: a painted plaque's "date of commencement" had been taken for the photo's
    date. Only a date followed by a time counts as the stamp now.
- **Place:**
  - All 187 readable points inside India fall in the work's own district.
  - 2 fall within 1 km over the border, which the simplified outlines can't resolve.
  - 0 are far away.
  - In the pilot, photos are taken where the work is.
- **Time: 3 works whose own evidence shows them finished before the MP recommended them.**
  All three were checked by eye:
  - **Sabar Kantha (Gujarat), WS/MP070/2023-2024/7171.** The portal says recommended
    31 Jul 2023 and completed 3 Jul 2023, which is impossible. The photo stamp says
    29 Jun 2023, which fits the work being done first and entered later.
  - **Chittaurgarh (Rajasthan), WS/MP720/2024-2025/124508**, a boundary wall at a bus stand.
    The two completion photos are stamped 30 Jul and 2 Aug 2023, and show the finished, painted
    wall. The portal says the MP recommended it on **11 Mar 2024**.
  - **Chittaurgarh, WS/MP720/2024-2025/124252**, a cremation-ground wall. The photo is stamped
    12 Feb 2024. The wall's own painted plaque says work started 1 Oct 2023 and finished
    31 Dec 2023. The portal says recommended **11 Mar 2024**.
  - The two Chittaurgarh works were recommended on the same day, in the pre-election rush.
    **Needs checking:** was the portal entry simply late, or were finished works put forward
    as new recommendations?
- **Same spot, same day, two works:** two ₹19,926 solar-light works in Bara Banki carry photos
  stamped at identical coordinates on the same day. The photos differ, so this is a weak
  signal only.
- **PIN check:** 66 PIN codes agree with the district. The 3 that don't are border or
  new-district cases (the PIN file predates them), not findings.
- **Bonus:** one work with no district in the export is placed by its stamp (Sanchor,
  Rajasthan).

### B1 Site progress
Not tested. It needs an AI vision key, and nothing in the free local toolset judges "does this
photo show a finished road".

**T510 (1 Oct 2026):** the engine frame exists (`agents/site_progress/`, merged with the plaque check and the
satellite gate): each claim in the officer's own words judged shown / not shown / can't tell, a reused photo voids
every confirmation, a complete work without a visible plaque is a note. Tested with a stand-in provider only, so
it reports "cannot be assessed yet" on every work with photos and carries no weight. The satellite gate (ponds and
check dams, roads over 1 km, buildings over ₹50 lakh) finds 2,822 qualifying works in the export (2,167 ponds), of
which only 1 has a GPS-stamped photo in the pilot: the go/no-go test needs more harvested evidence (T003).

**T510 v2 (2 Oct 2026): free local readers, built and switched off until measured.** The first sentence of this
section is no longer true: open CLIP models name what a photo shows on a CPU, and the local OCR reads a plaque.
Design: [`plans/T510-site-progress-v2.md`](../plans/T510-site-progress-v2.md). Checked so far: 34 unit tests and an
end-to-end smoke test (real RapidOCR on a drawn plaque, a stand-in for the photo model; it found and fixed a bug
with OCR that glues words together, "MPLADS2023-24"). **No real photo has been read yet**: the pilot photos are in
the data pack and this session could not fetch the model. The go/no-go numbers will go here from
`data/trial/site_progress_trial.py`.

### B5 Satellite
No-go for now.
- Of the 170 works with GPS points, the median cost is ₹2.8 lakh and only one exceeds
  ₹25 lakh (a ₹33 lakh town road).
- They are handpumps, lights, 100 m lanes and one bathing ghat: all too small for 10 m
  satellite pixels.
- Revisit only when large works (long roads, ponds, big buildings) with coordinates are
  collected on purpose.

### D1 Citizen verification
Can't be tested on real data. 21,789 of the 21,793 eSAKSHI citizen ratings are zero. It can
only be shown as a labelled demo.

---

### The risk score (T050, 30 Sept 2026): all four engines together

Every real work was run through the four engines and the blueprint's weighted score
(`data/dry_run.py` → `results/risk_score_bands.json`; by-eye labels `data/trial/risk_score_labels.py`
→ `results/risk_score_eye.json`).

**What the first run showed:** with the old scoring, the four engines would have put **43,646 works (21%)**
in the review queue. Two causes: the old scoring counted every flag as strong evidence (21,323 works are
simply "waiting for sanction too long", a system-wide delay), and it ignored "shown, not counted", so the
Delay engine, below its accuracy target, still added weight (it was on 16,529 of the queued works). A second double count was found: 13,158 of the cost engine's
16,010 flags were only its old "overdue" note, the same fact Guideline Compliance reports; it was removed
from the cost engine.

**With the blueprint score:**

| Band | Works | Meaning |
|---|---|---|
| Critical (≥ 33) | 128 | a guideline issue plus a split under ₹5 lakh or a repeat after completion, or three engines |
| High (≥ 22) | 1,396 | two engines each with a meaningful signal |
| Medium (≥ 15) | 35,085 | one strong signal (mostly a long wait for sanction) |
| Low | 173,384 | |

- **Review queue (High + Critical): 1,524 works (0.73%).** Read by eye, **24 of 30 random queue works are
  worth checking**. The misses: village-level "solar light in village X" entries (two lights in one village
  is normal), a list of 47 Wi-Fi locations read as one price, "GP and other villages".
- **The blueprint's cut-offs (40/70/85) cannot be used as written:** the highest real score is 37 (Delay counts 0,
  Outlier is not built). Its target of 5–10% High + Critical has no cut-off in the data either: the scores
  come in steps, and the next step below 2.3% is 17% (one guideline delay on its own).
- **What reading the queue fixed** (each followed by a fresh sample): at a High cut of 20, a weak second signal
  (a routine bulk order, a work flagged for being cheap) made High → cut at 22; 16, 23 and 50 identical works
  sharing a typo ("tenker", "publiic") read as "one site" → a same-place group of 6+ is a series; Critical at 30
  was reached by any delay plus any repeat, down to ₹20,000 lights → Critical at 33.

### T053 (1 Oct 2026): only agents that find real problems

**The owner:** the cost agent "always flags the money as high even on low-risk works"; Odd Overall must say what it
looks for; agents and notes that barely add anything go.

**Cost.** The engine flags 1.1% of works, but its card coloured anything above the top of the usual range red (1 in
10 works by definition). Every flag type was scored against all cost flags read by eye (`cost_v2_labels.py`):
several sites in one amount **0/48** real price questions, far above every similar work **3/18**, per unit above
**0/3**, above the comfort limit **54/128**; "well below similar works" was never measured. The first three are now
plain statements with no risk and "below" is gone. The comfort zone is explicit: from the top of the usual range up
to the comfort limit (the highest of twice the district's top, the state's top, twice the top for works described
like this), room for a bigger scope or a contingency margin. The card shows usual range, comfort zone and comfort
limit, and only beyond it a question. Widening the limit further did not raise precision (2-2.5× over 3/7, 3-4× 9/13,
6×+ 17/59).

**Removed.** The delay forecast (two methods, 0.71 and 0.70 AUC against 0.80; with 73% of works late it added little
to R02's real overdue count); Fund Flow stays (exact: 3,331 works, ₹168.9 cr). Site Progress (it could never run
without a key). The separate Data Validation step (it repeated Guideline Compliance with the 12%-precision matcher).
Notes on nearly every work: Paperwork's "in progress on paper" (282/285), blank certification boxes (427/429),
instalment-only certificates, vendor-share note; Photo Evidence's PIN, camera-clock, long-after-completion and
same-spot notes. Queue 502 → **442**: the 60 that left were carried by the removed cost notes; of the 30 queue works
read for T051, 22 stay and 19 of those have a reason beyond a delay.

**Odd Overall.** A fresh random 30 of the forest's 214 flags read **9/30** worth a look (9 of the 30 were one prefab
bus-stop series). The two kinds of real case became plain rules (`data/trial/odd_rules_trial.py`,
`odd_rules_labels.py`): **a big amount with no stated scope** (₹10 lakh+, above its type's national top, at most six
words, no number, no place: 618 works, **30/30** read as a question the record cannot answer: what and where?) and
**built in days** (a building, road or drain of ₹5 lakh+ recorded complete 0-14 days after recommendation, outside a
bulk-entry quarter, not a backfilled older work: 13 works, **13/13**). Both are checks on the record, so they would
fit inside Guideline Compliance rather than a separate engine. **The owner chose that:** the Odd Overall engine is
removed and the rules are Guideline Compliance **R12** (big sum that does not say what or where) and **R13** (built in
days). In the engine (like-for-like type tops, plain place words) R12 raises 697 works and R13 13; a fresh random 30 of
R12's engine flags read **28/30** (the misses: a size written as a word, now read; a common village name taken as a
generic word). Final queue **493** (50 CRITICAL, 443 HIGH); of the 52 queue works carrying R12/R13, 15 random read
**15/15** worth checking.

### MP history (1 Oct 2026): tested, not adopted

**The owner's question:** should DRISHTI look at an MP's history, e.g. a hidden MP risk score that sets how
thoroughly that MP's recommendations are checked? **What an MP's record holds** (eSAKSHI's public data, MP files in
the research build): per MP and term, money allocated / recommended / sanctioned / completed / spent and counts;
per work, the letter number, implementing office, dates, amount, description, a citizen rating (unused: 21,789 of
21,793 are zero). No audit, complaint or verified-problem history, so an MP "risk" could only be built from
DRISHTI's own flags.

**Does MP history predict problems?** `data/trial/mp_history_trial.py` → `results/mp_history_trial.json`. Past
(works recommended before 1 July 2024) predicting the future (after), each history shrunk toward the overall rate:

| Outcome in later works | MP history alone | District alone | Office alone | Adding MP history to district + office |
|---|---|---|---|---|
| finished more than a year late (a real outcome) | 0.56 | 0.71 | 0.71 | +0.004 |
| repeat or split found | 0.50 | 0.56 | 0.56 | −0.006 |
| price question | 0.57 | 0.62 | 0.62 | −0.065 |

(AUC: 0.5 = chance.) And **84,509 of 109,213 later works (77%) come from MPs with no history at all** (the June 2024
election changed most MPs; Rajya Sabha terms are individual).

**Decision: no MP score, no scrutiny that varies by MP.** It is not proven (it adds nothing to the district and the
office, which the engines already use), and it opens loopholes: a "low-risk" MP's works would get lighter checks,
which is where misuse would move; three in four new works would start with no history; more checks on high-score
MPs find more flags and raise the score further (a loop built on DRISHTI's own flags); and the project's rule 5 (never
score MPs) stays. Every check already runs on every work (they cost nothing); the only scarce depth is human
inspection and paid AI reads, and those follow the **work's own** risk × money plus a random share (Inspection
Planner, T062), which keeps a clean-looking record from buying less scrutiny.

**What MP history already does, where it is proven:** the Duplicate engine compares each recommendation with every
earlier work of its district, the MP's own included (fresh by-eye sample 20/40 real repeats). The same-MP "series"
rule (identical wording filed 3+ times = a series, not repeats) hides only 1 set of 4 works that name a place
(read: one water tanker per village), so it is not a loophole. **Letter numbers** (one MP letter, several works):
117,611 works sit on letters carrying several works, and a third of the real same-site splits span different
letters, so grouping by letter would miss splits and simplify nothing; not adopted.

**The one gap found and fixed:** 39,616 comparable works (19%) name no place ("Construction of Community Hall."), so a
repeat can be neither confirmed nor ruled out; the Duplicate engine said "no repeat found" for them. It now says
"names no place, so a repeat cannot be ruled out" (21,852 works; the rest sit in bulk-order groups).

### Odd Overall (#63, 1 Oct 2026): unusual in two ways at once

`data/build_outlier.py` → `results/outlier_trial.json`. Three fields judged within the work type: amount, days from
recommendation to completion, length of the description. Two methods at the same 1.5% of real works flagged:

| Planted on 1,000 ordinary works | Isolation Forest | Robust z (second-largest) |
|---|---|---|
| amount ×5 + completed in 2 days | **100%** | 51% |
| amount ×5 + description cut to one word | **75%** | 51% |
| completed in 2 days + one-word description | **100%** | 100% |
| amount ×5 alone (the cost engine's job) | 6% | 0% |
| false alarms on 20,000 untouched works | 1.6% | 1.7% |

The forest is kept, exported as numbers and scored in plain Python (equal to sklearn within 1e-16). Read by eye
(`outlier_labels.py`): the 30 oddest real works **22/30 worth a look** (a ₹49 lakh lab purchase "completed" 8 days
after recommendation; ₹1-1.35 crore roads with no description done in two months), but 30 random works at the 1.5%
cut only **3/30** (mostly light installations done in a fortnight, cheap jobs, backfilled 2022-23 works). So the
engine reports only the oddest 0.1% (214 works) and is shown, not counted.

## T051 (1 Oct 2026): do the engines work on recommendations they have never seen?

**The owner's question:** are the engines good only because they were built on these 2,09,993 works? A
system check, not a tuning pass: eight made-up recommendations the engines had never seen, plus every real
work, before and after. Plan and design rule: [`plans/T051-engines-any-recommendation.md`](../plans/T051-engines-any-recommendation.md).

**What was wrong (before):**
- **Duplicate & Split** read answers stored once, offline, for the 2026 export. An exact copy of a completed
  work under a new id was told "compared with every work in its district: no repeat found". Nothing had been compared.
- **Delay** could not score any new work (its scores were stored per work), and its model fell to 0.59 in
  districts it had not seen (0.5 = chance).
- **Cost** version B (the "described like this" range) existed only for works in its training file, so a new
  work met a looser rule than the measured one.
- **Guideline Compliance** gave 3 risk values to 2,09,993 works (80 days waiting = 718 days), repeated
  "98% of completed street light works finished within 881 days" word for word across the queue, never read
  Hindi script, and had the 2024 election pause written into code.
- **The queue:** 802 of 1,524 works shared one score (0.30).

**What changed, and what it measured (after):**

| Engine | Change | Measured (script → result) |
|---|---|---|
| Duplicate & Split | rules moved into the engine (`match.py`, stdlib only); any work is compared with its district live; place words = not in a generic-word list (5% of districts), minus each district's own boilerplate; opposite sides of a road = two works; a typo is not a place; a same-site split needs near-identical text | fresh pairs read by eye with rules frozen: **20/40 real repeats** (T030: 15/40); same-site groups **9/15** (T030: 10/15). Two development samples (1/40, then 19/40) led to the rules and are not counted. `dup_split_v2_trial.py` → `dup_split_v2.json`, labels `dup_split_v2_labels.py` |
| Delay | LightGBM per-work scores → a late-rate ladder (office → district × type → state × type → type) stored as counts | strict backtest **0.705** (LightGBM 0.710); **unseen districts 0.685 (LightGBM 0.588)**. Still below 0.80: shown, not counted. `build_delay_rates.py` → `delay_rates.json` |
| Cost | LightGBM ranges → a word-price model (words used in 20+ constituencies) the engine applies to any description | typical miss ×1.82 (LightGBM ×1.72), 80% of works inside the range (same). Planted test: 5× mark-ups caught **42-45%** (was 55%), 10× **80%** (82%), false alarms **1.2%** (1.3%). Top-30 flags read by eye **11/30** real price questions (was 10/30), random 3/30 (5/30). `build_price_model.py`, `cost_trial_v2.py --linear` → `cost_trial_v2_linear.json`, `cost_linear_eye.json` |
| Guideline Compliance | signals grow with how far past the limit (R01 0.30 → 0.60 at 4× the clock; R02 0.15 → 0.60); sentences give this work's overrun; Hindi-script R07; election pauses in `rules.json` | **447 distinct signals** (was 3) |
| Risk score | cut-offs re-tuned: CRITICAL 0.30, HIGH 0.22 | queue **502** (0.24%); largest share of one score **9%** (was 53%); 30 random queue works read by eye: **30/30** have a reason that survives reading, **27/30** a reason other than a delay. Of T050's 24 "worth checking" sample works, 7 stay queued; all 6 "explained" ones leave. `dry_run.py` → `risk_score_bands.json`, `risk_score_eye.json` |

**After, on the made-up works:** the exact copy is found ("descriptions 100% alike, the same place named");
80 and 718 days waiting score 0.31 and 0.60; the Hindi temple is caught like the English one; a new office
is scored from its district's record and says so; a new work with no match says how many works it was
compared with.

**Still true / open:** a duplicate found by the Duplicate engine alone stays LOW or MEDIUM, because no one
engine can reach HIGH in the blueprint's weights (owner's call whether an exact repeat should). The
sanitiser missed phone numbers before a full stop; fixed, and `identical_groups.json` on main carried 12
such numbers until this branch.

## T054 (1 Oct 2026): the timing rules, scored by how unusual the wait is

**Asked (owner):** "most works are past the 75-day limit or aren't removed, or they get too high a risk score for
just being a few days past". All three were true.

**Measured** (`data/trial/wait_curves_trial.py` → `results/wait_curves.json`; the export has no sanction date,
so the wait is read off the snapshot: of the works recommended N days before it, how many still wait):

| Days since recommendation | 75 | 120 | 180 | 365 | 540 | 730 |
|---|---|---|---|---|---|---|
| still waiting for sanction (R01, per 100) | 63 | 53 | 25 | 13 | 4 | 4 |
| still shown open, of sanctioned works (R02, per 100) | – | – | – | 69 | 39 | 43 (at 900) |

- **R01** fired on 21,323 of the 28,433 waiting works, and day 76 scored 0.30 (half the rule's maximum) although
  6 in 10 works that old still wait. 3,331 of the waiting works belong to the 17th Lok Sabha (ended 5 June
  2024); the public data has **no rejected status**, so a recommendation the district turned down stays
  "waiting" for ever. 9 in 10 recommendations are eventually sanctioned (by recommendation quarter, 2023-25).
- **R02** fired on 61,920 of 94,662 open works; 12,060 of them as MEDIUM "past the time by which 98% of finished
  works of its type had finished". That line is an artefact: the data starts in 2023, so no finished work can
  show a longer time, and 36-57 in 100 works recommended 2-3 years ago are still shown open.
- 364 of the 493 queue works were not yet sanctioned; 356 were led by R01, mostly R01 + a repeat/split signal
  (a refiling of an earlier recommendation, often after an unrecorded rejection).

**Cross-check against real sanction dates:** 226 portal certificates (almost all Pratapgarh, UP) give a median
sanction time of 71 days, 14.5% past 75. The snapshot method on Pratapgarh alone gives 12 in 100 works aged 60-90
days still waiting, so the two methods agree; districts differ widely (nationally 63 in 100 at that age).

**Changed:** R01's signal follows how few works that old still wait (0.05 when most do, 0.30 at 1 in 10,
0.60 at 1 in 25; `rules.json` `wait_curves` + `rarity_signal`), and its sentence says how common the wait is. An
ended term's leftover runs on the para 3.15 clock (75 days from the term's end), is LOW (0.15) and says the
record needs closing. R02 is always LOW (0.05-0.08) and says long-open works are common on the portal.

**After** (`dry_run.py` → `risk_score_bands.json`): CRITICAL 5, HIGH 126, MEDIUM 2,197 (was 50 / 443 / 14,581);
**queue 131** (0.06%). A fresh 30 from the new queue read by eye (`risk_score_queue_sample_t054.csv`, labels
`QUEUE_T054`): **28/30 worth checking**, 2/30 record clean-up (an unsanctioned work refiled later). Of the 57
works in the earlier eye samples, 5 stay queued; the rest had been lifted by a delay note and now sit in MEDIUM
on their repeat/split signal alone (one engine cannot reach HIGH: the owner's open question).

**Not settled:** the 2023 guidelines may set 45 days for sanction (para 3.2.4 as quoted in the press); the 2023
PDF still cannot be fetched from outside India (T001). With 45 days R01 would fire on more works but score
the same, since the signal now follows the wait curve, not the clock.

## T120 (3 Oct 2026): timing facts for the Time & Rules agent, on the dashboard's sanction dates

Measured for the four-agent plan ([`plans/T120-four-agents.md`](../plans/T120-four-agents.md) §8) by
`data/trial/four_agents_timing.py` → `results/four_agents_timing.txt` / `.json` (aggregates only). The dashboard
tables of 2 Oct 2026 carry real sanction dates, which the research export does not.

- **The 75-day clock is broken by most works.** Of 15,662 works with a recommendation and a sanction date (recommended
  8 Jul 2024 – 2 Oct 2025), the median wait is **90 days** (p10 21, p90 256); **9,401 (60.0%)** waited past 75 days
  and 11,928 (76.2%) past 45 (before any election-code days are taken off). A late sanction is an office fact, not a
  work's fraud: as a flag it would put most works in the queue.
- **Some works are "finished" impossibly fast.**
  - Of 11,577 works with both a sanction and a completion date, **832 (7.2%)** are recorded complete within 7 days of
    sanction.
  - Among 5,038 constructions, **195 of Rs 5 lakh or more** are complete within 7 days.
  - One community hall in ten is complete within 1.3 days of sanction, and 20.3% within 30 days.
  - CCTV is legitimately quick: a median of 7 days.
  - None is dated complete before its own sanction.
- **One window per type would be wrong.** Sanction to completion has a median of 209 days, but the spread inside a
  type is huge: the 90th percentile is 8 times the 10th for CC roads (56 to 462 days) and 367 times for community
  halls. The amount barely separates them: CC roads have a median of 167, 209 and 217 days under Rs 3 lakh, at
  Rs 3–10 lakh, and at Rs 10 lakh+. The window must come from each work's own size and estimated time (plan §8.2).
- **Completion evidence today:** 9,300 of 36,508 completed works (25.5%) carry no picture at all. The portal's own
  stages for sanctioned works include a "Time Estimation" step (Physical Inspection 3,506, Sanction 512, Vendor Identification 474, Work
  Completed 262, Work partially Completed 237, Time Estimation 9).
- **Caveat:** build times come from works finished by the snapshot, so slow works are under-counted; the fast end,
  which the "too fast" question uses, is not affected.

## T080 (1 Oct 2026): the planted-anomaly test, 50 known problems run blind

`data/trial/planted_test.py` → `results/planted_test.json`, `planted_test_rows.csv`. 50 fakes built from real
works (seed 80), 10 of each kind, run through the whole pipeline with all 2,09,993 works, in memory only
(nothing reaches a database). Measured after T054.

| Kind (10 each) | Meant to be caught by | Caught by that engine | In the top 5% of the risk score | In the review queue |
|---|---|---|---|---|
| Rule breaches (3 temple R07, 3 outside the area R08, 2 big vague sums R12, 2 built in days R13) | Guideline Compliance | **10/10** | 10/10 | 4/10 (the 3 R08 CRITICAL, 1 R12 HIGH) |
| Completed before recommended (R06) | Guideline Compliance | **10/10** | 10/10 | 0/10 (MEDIUM) |
| Split into 3-4 pieces just under Rs 5 lakh, same day | Duplicate & Split | **10/10** | 10/10 | 0/10 (LOW) |
| Filed again 60-300 days later, reworded | Duplicate & Split | **7/10** | 8/10 | 0/10 |
| Price raised 2-3× | Cost Anomaly | **0/10** | 1/10 | 0/10 |
| **All 50** | | **37/50** | **39/50 (78%; target 75%)** | **4/50** |

- **Top 5% met the blueprint's target (78%).** The top 5% of scores starts at 0.09, which is still the LOW band.
- **The review queue holds 4 of 50.** One engine alone cannot reach HIGH (0.22) by the blueprint's weights, and a
  planted fake usually breaks one thing. Same open owner question as T054.
- **Cost at 2-3× is not questioned by design**: the engine asks only beyond its comfort limit (about twice the
  usual top, T053). The same 10 fakes through the Cost engine alone: 2× 0/10, 3× 0/10, 5× 3/10, 10× 5/10. Of the 5
  missed at 10×, 3 read as "a far bigger project, not a price question" (a single semi-high-mast light at Rs 22
  lakh; a CC road at Rs 50 lakh), 1 sits inside a wide state comfort zone (library), 1 has no work type. "Far
  bigger" stopped counting in T053 because it read right 3/18 on real works; a planted mark-up that keeps a small
  stated scope ("one light") is exactly the case it now lets through.
- Reworded repeats missed (3/10): a transliterated Hindi description with no word to swap (order rotated), and two
  where "at/near/village" swaps plus the original's district boilerplate left too few shared place words.
- Not planted: translated repeats (no offline translator; the duplicate rules compare words).

## T064 (1 Oct 2026): the pre-sanction check on real recommendations

`data/trial/presanction_demo.py` → `results/presanction_demo.json`. Each real recommendation is checked as it stood
on the day it arrived (not yet sanctioned, compared only with its district's earlier works):

| Case | Work | Answer | Why |
|---|---|---|---|
| ordinary | WS/MP618/2024-2025/156175, Rs 4.98 lakh community hall | **Green** | nothing the checks can see |
| refiled | NOREF-b14cbede407a6e, Rs 10 lakh sabhamandap | **Amber** | reads like WS/MP18114/2025-2026/157479, recommended 225 days earlier, still open |
| temple | WS/MP476/2024-2025/72649, solar light at a temple campus | **Amber** | Annexure-II item 13 reading |
| vague big | NOREF-840ee6aa1b9fe3, Rs 25 lakh "Construction of Community Hall" | **Red** | no place or size (R12) and 2.5× the top of the state's usual range |

**Trap:** re-dating a real work to the data's "today" hid its earlier copy (gap 225 → 533 days; the repeat score
weighs time and fell from 0.80 to 0.74, under the 0.75 flag). A live check dates a new recommendation the day it
is typed, so this only matters for demos built from old works.

## T055 (2 Oct 2026): engine review, a test country, Office Patterns and risk fusion v3

Write-up and reasoning: [`plans/T055-engine-review.md`](../plans/T055-engine-review.md). Two new measurements,
because the old ones could not answer "does it find more, and does it stay right?":

- **A test country** (`data/trial/synthetic_eval.py` → `results/synthetic_eval_<tag>.json`): three seeded made-up
  countries (seeds 11, 12, 13; 60,951 works), 810 planted problems of 16 kinds and look-alikes the engines must
  leave alone. The only **recall** measurement that needs no private data. "Main" = the engines on main
  (a separate checkout), with the same test country and labels.
- **The eSAKSHI dashboard's own tables** (`data/trial/dashboard_trial.py` → `results/dashboard_<tag>.json`,
  `_queue.csv`, `_codes.csv`, `_flags.json`): 40,935 works downloaded 2 Oct 2026, never seen by any rule, with real
  sanction dates for 15,662. Statistics and the price model rebuilt from them. Read by eye:
  `data/trial/dashboard_labels.py`.

**Test country, all planted problems (810):**

| | Main | New engines, v2 score | **New engines, v3 score** |
|---|---|---|---|
| caught by the engine meant for them | 31.1% | 73.7% | **73.7%** |
| Medium or above | 16.4% | 21.7% | **39.5%** |
| in the review queue (High + Critical) | 4.0% | 4.6% | **16.4%** |
| in the top 5% of the score | 33.7% | 45.9% | **74.3%** |
| queue precision (planted problems / queue) | 61.5% | 58.7% | **68.2%** |
| ordinary works queued (false alarms, of 47,671) | 0.03% | 0.04% | **0.11%** |

`synthetic_eval_baseline.json`, `synthetic_eval_engines_v2fusion.json`, `synthetic_eval_v3.json`. The middle
column is the same new engines scored by the old formula: the engines find the problems, the v3 score is what
lets a well-measured finding reach the queue. Not counted in precision: 684 works the generator happened to
make with a big sum and no place (`UNSCORED_BIG_VAGUE`); R12 queues 48% of them, rightly.

**By planted kind** (caught by the meant engine → in the queue; main → v3):

| Kind (n) | Caught: main → v3 | Queued: main → v3 | Note |
|---|---|---|---|
| Temple work, R07 (36) | 39% → **100%** | 0% → **100%** | the R07 reader fixes |
| Big sum, no place, R12 (18) | 100% → 100% | 78% → 100% | |
| Built in days, R13 (18) | 100% → 100% | 0% → **100%** | v3: 13 of 13 read right |
| Outside the area, R08 (18) | 100% → 100% | 100% → 100% | |
| Completed before recommended, R06 (18) | 100% → 100% | 0% → 0% | never read by eye: the prior, Medium at most |
| Split at one site (60) | 77% → 77% | 0% → 7% | splits read right about half the time: Medium alone |
| Split into numbered stretches (60) | 33% → **93%** | 0% → 5% | new `SPLIT_INTO_STRETCHES` |
| Repair soon after built (36) | 0% → **78%** | 0% → 0% | new, never read on real works: the prior |
| Repeat after completion (36) | 33% → 44% | 0% → 0% | Medium (44%); a repeat reads right ~50% |
| Repeat while open (36) | 28% → 28% | 0% → 0% | Medium |
| Office prices at the limit (237) | 0% → **100%** | 0% → 0.8% | new engine; corroborates, never queues alone |
| Office closes works in days (93) | 37% → 37% | 0% → 37% | R13 counts each work; the habit is a fact |
| Price ×10 on "1 unit" (36) | 28% → **78%** | 0% → 0% | a stated single unit is not "a bigger project" |
| Price ×10 / ×5 / ×3 (36 each) | 47% / 42% / 6% (unchanged) | 0% | price alone reads right 54 of 128: Medium at most |

**Look-alikes left alone** (v3, Medium or above / queued): a temple as a landmark (5,694) 3.7% / 0.1%; a school
named "Shishu Mandir" (1,044) 3.5% / 0%; batches for different villages (1,343) 3% / 0.1%; opposite sides of one
road (300) 0.7% / 0%; a repair of a different asset (18) 0% / 0%; bulk entry when the portal opened (211) 1.9% /
1.9%; big projects that state their size (36) 5.6% / 0%.

**The dashboard's 40,935 real works:**

| | Main (`dashboard_baseline`) | **This branch, v3 (`dashboard_final`)** |
|---|---|---|
| Critical / High / Medium | 0 / 47 / 543 | **40 / 387 / 1,423** |
| review queue | 47 (0.11%) | **427 (1.04%)** |
| 40 random queue works read by eye | 38 yes, 1 grey, 1 no (25 distinct cases: 11 of the 40 are one ₹1.53 crore street-light purchase) | **39 yes, 1 grey, 0 no** |
| by finding, in that sample | | R12 20 of 21 (+1 grey) · R14 13 of 13 · R07 3 of 3 · splits/stretches 3 of 3 |

An earlier v3 run (`dashboard_v3`, before the last R07 fixes; queue 419) read 37 yes, 1 grey, 2 no, the 2 "no"
being R07 misreads fixed the same day. New findings on the real works: R14 "built right after sanction" fires on
**320** works, 12 random flags read **12 of 12** worth checking; `SPLIT_INTO_STRETCHES` 18; `PRICED_AT_LIMIT` 1,311
works from **36 offices** whose routine is pricing works just under a limit (median office: 55% of its works,
against 9.5% nationally); **6 offices** record constructions complete within 7 days of sanction as a routine
(median 69% of their constructions, against 7.1% nationally). Offices are counted, never named, in the results.

**R07 (eligibility), every changed answer read** (`dashboard_baseline_flags.json` vs `dashboard_final_flags.json`,
labels `R07_CHANGES`): main flags 54, this branch 63. All **15 gained are right** (a church toilet, a wall for a
temple, a hall in a temple, a temple's beautification, a solar plant in a private ITI, 10 works "table of kitchen,
private school"); of the **6 dropped, 5 were misreads** (two roads named after a temple or church, a ration shop,
a school, a shed "near" a temple courtyard) and 1 is grey (a platform "beside" a temple campus). On the team's
fresh T051 eligibility TEST sample (`eligibility_rescore.py` → `eligibility_rescore.json`) the reader keeps
all 40 right flags (28 clear, 12 grey) and drops 1 of the 10 misreads.

**Duplicate & Split, the team's 159 labelled repeat pairs** (`dup_split_rescore.py` → `dup_split_rescore.json`;
words and places only): false repeats flagged **56 → 50** of 102, true repeats **44 → 43** of 57.

**How v3 reads the measured hit rates** (`apps/engine/drishti/reference/reliability.json`, each entry names its
labels): R12 46 of 48 read right · R13 13 of 13 · R14 25 of 25 · R07 53 of 62 · cost above the comfort limit
54 of 128 · repeat after completion 6 of 12 · repeat while open 33 of 74 · same-site split 14 of 27. A kind never
read counts 1 in 4 and cannot queue a work alone.

**Robustness** (`tests/evaluation/`): 400 malformed records (empty fields, impossible dates, Tamil and Hindi script,
sums of 0 to ₹100 crore, SQL-looking text) never crash an engine; the same work twice gives the same answer;
the order works are loaded in and capitals change no finding. A CI gate runs two small test countries on every
pull request with a floor per planted kind and a ceiling per look-alike.

**Live, all 2,09,993 works** (the owner ran `data/batch_assess.py` on the hosted database after PR #86 merged;
output in `results/hosted_assess_v3.txt`): CRITICAL 83, HIGH 1,347, MEDIUM 5,112, LOW 203,451. The review queue is
**1,430 works (0.68%)**, up from 131 with fusion v2 (1 Oct). That is the same order as on the dashboard's works
(1.04%). The queue shows one row per Duplicate & Split case, so it lists fewer rows than 1,430.

**Planted test (T080) re-run with v3 on all 2,09,993 works** (the owner ran `data/trial/planted_test.py`, same 50
fakes, seed 80; `results/planted_test_v3.json`, added in PR #87): in the review queue **4 → 11 of 50**, MEDIUM or
above **25 → 38**, caught by the engine meant for them 37 → 39, in the top 5% 39 → 39 (78%, target 75%).

| Kind (10 each) | Caught by the meant engine | Top 5% | Review queue |
|---|---|---|---|
| Rule breaches (R07, R08, R12, R13) | 10/10 | 10/10 | **10/10** (was 4/10) |
| Completed before recommended (R06) | 10/10 | 10/10 | 0/10 |
| Split into pieces just under ₹5 lakh | 10/10 | 10/10 | 0/10 |
| Filed again, reworded | **8/10** (was 7/10) | 8/10 | 1/10 |
| Price raised 2-3× | 1/10 (was 0/10) | 1/10 | 0/10 |

The Cost engine on its own (cost sweep): 2× 0/10, 3× 1/10, 5× 3/10, **10× 6/10** (was 5/10: a stated single unit is
no longer excused as a bigger project). Most of the fakes that still stay out of the queue stay out on purpose: a split or a reworded repeat alone reads right about half
the time (the measured hit rates), so it stays MEDIUM until a second check agrees. Completed-before-recommended (R06)
has never been read by eye, so it counts at the 1-in-4 prior. Prices raised 2-3× are inside the comfort zone (T053).

**Not measured yet:** 30 random live queue works read by eye (needs the data pack or database access). The 2023 guideline PDF stays unreachable (network policy blocks mplads.mospi.gov.in).

## T056 (2 Oct 2026): foolproof and accuracy pass on the remaining agents

**Asked (owner):** "work on the next few agents to make them foolproof and accurate". Covered: the evidence engines
(Photo Evidence, Paperwork, Site Progress) and their indexes, Fund Flow, the certificate reader, and Cost Anomaly.
Foolproof means a malformed or oddly written record can never crash an engine or the batch, and the same facts
written another way give the same answer. Accuracy changes were made only where real flags read by eye showed a fix.

**Foolproof, found by fuzzing** (tests in `tests/evaluation/test_random_evidence.py`, `tests/agents/delay/`,
`tests/agents/paperwork/`):

| Found | Effect before | Fix |
|---|---|---|
| One evidence row whose file was not an object (or a stamp without numbers, a payment without an amount, a fingerprint that is not hex) | the photo and vendor indexes raised, so **the whole batch stopped**; a work page too | `agents/evidence.py`: every part checked once, malformed parts dropped, never guessed; every engine and index reads through it. 250 random malformed works and 5 fuzz seeds run clean; 8 of the 14 new tests fail on the old code |
| Fund Flow compared text exactly: status "recommended", a term "17th lok sabha", house "rajya sabha" | the work was skipped as "sanctioned", or an ended term missed | case and spacing ignored (`delay/backlog.norm`) |
| A recommendation date written as text ("2024-02-01") | Fund Flow raised; the office-backlog index (all works) raised, so **the batch stopped** | text dates read as dates (`backlog.day`) |
| A recommendation date after the data's own date | "Waiting -30 days" | NOT_ASSESSABLE, with both dates named |
| Certificate OCR with words glued together ("TESTVENDORV123456789012") | the vendor code was lost | the code is found inside glued text |
| Certificate dates with "-", "." or "\|" for "/" ("20-03-2024"); the letter O for a zero ("3,OO,OOO", "2O/O3/2O24") | the date or amount was lost | read, inside numbers only ("Block O", "CO-OP" untouched) |
| One work row in the corpus with a pandas NaN in a text column, a district code loaded as a number, a datetime where a date was expected, an amount written "1,00,000", or a negative amount on a CC road | the Duplicate & Split index and the cohort statistics raised, so **the whole batch stopped** (every fuzz seed) | `drishti/records.py`: every column checked once at the indexes, the statistics and the orchestrator (text as written, numbers from any number type, ISO and Indian day-first dates, a clear yes/no); malformed values dropped, never guessed; a clean row is not copied. 5 seeds × 300 damaged rows run clean; the 2 new corpus tests fail on the old code. A loosely typed twin of every work (dates as text or datetimes, amounts as Decimal or grouped text, codes as numbers) gets the same answer finding for finding. On clean records nothing changes: the dashboard's 40,935 works give byte-identical codes, flags and queue files (`dashboard_agents4.json` vs agents3) and the test country is identical (`synthetic_eval_agents4.json`) |

**The certificate reader on the pilot's 431 real certificates** (the owner re-ran `data/build_evidence.py` and
`data/trial/paperwork_trial.py` after #89 merged; output kept verbatim in `results/paperwork_trial_t056.txt`):
nothing lost and one small gain. Sanction date read on **69.4% → 69.4%**, vendor code **97.7% → 97.9%**,
sanctioned amount, status and payments 99.8% and location 99.3% unchanged. Every engine count is unchanged too
(ASSESSED 405, sanction late 32, sanctioned before recommended 1, no certificate read 120). The run shows
`PAPERS_AGREE` 252 where `results/paperwork_trial.json` (1 Oct, T110) shows 1: that file predates T053, which
removed five Paperwork notes (in progress on paper, blank certification, part-payment papers, papers of several
works, vendor concentration as a finding), so the 209 + 33 + 9 works that carried one now read "papers agree".
Not counted here: how many of the other 30.6% are on the older certificate form, which has no sanction-date line
(DATA.md), so no reader could find one.

**Cost Anomaly: where its misses come from** (test country, seeds 11-13, `synthetic_eval_agents2.json`). Planted 5×
mark-ups: 20 of 36 sit inside the comfort zone and 15 of 36 are flagged. Planted 10×: 15 of 36 are read as "a far
bigger project" and 17 flagged. Both are deliberate (T053: flags inside the comfort zone and "far bigger" flags
almost never read as real price questions, 3/18). One planted pattern, a "single room" at Rs 39-41 lakh judged
against whole school buildings, suggested a rule for single units; on the dashboard's real works it would have
changed **1 of 653** single-unit works, so it was not built (it would tune the engine to the test country).

**Cost Anomaly: its real flags read by eye.** 12 random Cost flags of the dashboard's 40,935 works
(`dashboard_labels.py` COST_SAMPLE): **3 real price questions, 5 grey, 4 not**. All 4 "not" were one amount for
several streets or parts ("2nd 3rd 4th 7th Cross", "…Street & Streets", a list of park components) or a wrong work
type. Fix: one amount for several streets or roads is a bundle for the price (`scope.several_ways`), and only for the
price. Duplicate & Split still reads "Internal CC Roads (Bit1)/(Bit2) in one village" as one place (a true split,
kept by a test). Measured (`dashboard_agents2.json` against `dashboard_final.json`; every change read, COST_CHANGES):

| | Before | After |
|---|---|---|
| Cost flags on the 40,935 works | 140 | **135** |
| dropped | | 7, all rightly (4 several streets, 3 vague sums that R12 still flags) |
| gained (narrower peer bands) | | 2: 1 grey, 1 not |
| review queue | 427 | 427 (4 works move from CRITICAL to HIGH: their second engine was the dropped Cost flag) |
| test country (all measures) | | unchanged |

Cost flags stay MEDIUM at most in fusion v3: price alone reads right less than half the time (54 of 128 in T053;
3 clear and 5 grey of 12 here).

**Duplicate & Split: its split flags read by eye** (12 random SPLIT_AT_ONE_SITE flags, `dashboard_labels.py`
SPLIT_SAMPLE_T056): **7 real questions, 2 grey, 3 not**. The 3 "not": a men's and a women's building read as one
job, twice ("Resting Barracks … for Men / for Women"; "Vishranthi Dhamam (Male block) / (Female block)"), and two
Rs 34,000 street lights near two different hamlets. Two rules, each measured:
- **Genders that differ make two works** (`match.genders`, like opposite sides of a road); two girls' toilets are
  still alike.
- **A split whose total stays under Rs 5 lakh avoids no limit**: said, not asked (`ALIKE_BELOW_LIMIT`, risk 0). 24
  of the 76 split flags were such; every one of them that had a label read grey or not (0 yes of 5).

Measured (`dashboard_agents3.json` against `dashboard_agents2.json`, every dropped flag read): split flags **76 →
48**, stretches 18 → 13, bulk orders 1,334 → 1,330; review queue 427 → 427; test country unchanged on every
measure (`synthetic_eval_agents3.json`). On the rules' own fresh sample, the groups not used to design them read
**4 real splits of 5** (SPLIT_FRESH_T056). Only those 5 fresh reads were added to the measured hit rate
(`reliability.json`: 14/27 → 18/32). With that rate a split of 5 or more pieces just under a limit reaches HIGH on its
own; none on the dashboard does yet.

**R06, recorded complete before it was recommended, read on the hosted data** (`data/trial/r06_rows.py`, run by
the owner; counts `results/r06_hosted.json`, labels `data/trial/r06_labels.py`). A first SQL count of the stored
findings returned 3: the batch stores full findings only for HIGH and CRITICAL works (migration 003), and R06 alone
was MEDIUM at most, so stored findings cannot count it. Counted from the works table: **1,105 of 85,773** works with
both dates are recorded complete 7+ days before their recommendation. R06's own check rates **21 MEDIUM** (they stand
out) and 1,084 LOW records notes (678 an office's habit, 285 a bulk-entry quarter, 121 less distinct).

| Read by eye (the first 10 MEDIUM cases in the script's fixed random order) | Result |
|---|---|
| Roads (7), a hall, a hospital toilet block, a high-mast light; Rs 2.99-37.87 lakh; complete 15-137 days before the MP's recommendation; no sanction date on the record | **10 of 10 worth checking** (the R13/R14 standard: the dates need checking) |
| Where | 8 of the 10 are Kerala district offices: a state-wide recording practice is possible and is the next thing to read |

Change: `compliance:IMPOSSIBLE_TIMELINE` worth 10 / read 10 (hit rate 0.25 → 0.79), so a case that stands out reaches
the queue alone; the records notes, which were not read as findings, carry risk 0.10 (`R06_NOTE_RISK`) and count
0.131, about the 0.125 they counted before. Measured: test country (`synthetic_eval_agents5.json` against agents4)
planted R06 queued **0 → 12 of 18**, queue 195 → 207 with every added work a planted R06, precision 0.682 → **0.700**,
ordinary works queued unchanged (0.11%); dashboard unchanged (R06 does not fire on its tables; `dashboard_agents5.json`).
Expected live: at most 21 more works in the queue.

**Live after T056** (`results/hosted_assess_t056.txt`, the owner's `batch_assess.py` after #89, #90 and #91, all T056
changes together): CRITICAL 83 → 82, HIGH 1,347 → 1,377, MEDIUM 5,112 → **4,321**, LOW 203,451 → 204,213; review queue
**1,430 → 1,459 (0.69%)**. The +29 cannot be split by change from band counts alone: R06 could add at most 21, and the
MEDIUM drop of 791 fits the split and Cost fixes, which turned flags into notes.

**Privacy: the masker on real descriptions** (`data/trial/pii_trial.py` on the dashboard's 57,508 descriptions; counts
`results/pii_trial.json`). Reading the R06 cases showed names the masker did not catch. Measured, the gap was large:
names before a home word with no possessive ("PCC road from <name> house to <name> house": "mahto house" 301 times,
"singh house" 219), the Hindi and Gujarati genitives "k ghar" (1,332) and "na ghar" (339), and the person named
*before* "S/O", whose father after it was masked. New rules in `validation/pii.py`: OWNER_HOME (up to three words before
house, land, ghar, shop, farm, field and the like, unless the word before is an ordinary one read by eye among the 450
commonest: "guest house", "panchayat land", "ration shop", "barat ghar", "old age home"), the genitives k / kai / na /
ni / nu, and BEFORE_RELATION.

| Measure (57,508 descriptions) | Before | After |
|---|---|---|
| Descriptions with something masked | 9,312 | **13,564** |
| Touched by the new home-word rule / the name before S/O | - | 4,820 / 2,612 |
| Fresh sample of 40 masked spans, read by eye (rules frozen) | - | **40 people's names** (4 also take a small word beside the name: "thi", "va", "nali") |
| Fresh sample of 40 "word + home word" spans left unmasked | 6 names (4 before "S/O") | **0 names** |

Two earlier samples were used to design the rules and are not counted: they found a double mask of "[name]'s
house", Hindi road words and association halls read as names, and "kothi" / "haveli" / "bungalow", which on real works
are mostly parts of place names (all fixed). `sanitize_results.py` now runs the same masker over every committed
results file (it masked numbers only): 270 lines changed across 43 files, numbers untouched, and a second run changes
nothing. Still not caught: a name in a phrase with no home word ("from <name> to the land").

*Then (T092, 2 Oct 2026):* the Visualization Engine's built-in examples showed real descriptions with "<name> ke avas"
(at <name>'s residence), which the Hindi rule did not know. The words after a genitive, counted on the 57,508
descriptions, gave the other spellings: "ka makaan" 177 times, "ke avas" 34, "ki dukaan" 32, "na ghare" 24, "ke gher" 19,
"ke awas" 8, "ke niwas" 3. HI_HOME now knows them; "<surname> Niwas" (a house's own name) and the Gujarati "<name> ghare"
joined the home words. "PM Awas" and "Indira Awas" (no genitive before them) and "<clan> ki dhani" (a hamlet's name) stay.

| Measure (57,508 descriptions) | Before | After |
|---|---|---|
| Descriptions with something masked | 13,564 | **13,776** |
| Fresh sample of the newly masked spans, read by eye | - | **46 of 47 people's names** (1 "ration dealer ki dukaan") |
| Every span of the new home words still unmasked (24), read by eye | - | **2 names**, each glued to a typo ("Krishnapal lke makaan"), 3 unclear ("Deepak Nagar ke makaan": a person or a place) |

`sanitize_results.py` re-run: 7 more lines masked in 7 files, a second run changes nothing.

**The API end to end** (`tests/api/test_api_at_scale.py`, in CI): the test country's 1,302 works across its districts,
seven made messy (Devanagari, Tamil, a made-up name and phone number, 2,000 characters, empty, none) plus a work id a
URL must escape, malformed evidence on 30, all assessed by the real batch; then every listing and dashboard endpoint
for the ministry, a district officer and a field officer; the work pages of every messy work, every work with
evidence, 20 stored in full and 40 at random; and 34 odd pre-sanction bodies. No 500; a
district officer gets 404 for another district's work; the queue total equals the stored HIGH/CRITICAL cases, in
priority order; no text returned holds an accusing word or anything the masker would hide. It found one leak: **every
work page sent the raw evidence facts, whose certificate place line is OCR text that can name a person** ("near <name>
house"). The web never reads that field, so the API no longer sends it (`api/routes.py`).

## T092 (2 Oct 2026): the Visualization Engine, one work step by step

A public page (`/explain`) shows judges what DRISHTI does to one work, in six animated steps, each replayable:
the work goes in; private details are hidden; the description is read (each word coloured by what it is, and the
facts found light up like a network's neurons); seven checks look at once, each with its own picture (the rule
checklist, the price dot on the band of similar works, the district's most alike works drawn closer the more alike
they are, the dates against the guideline clocks, the office's habit against the scheme); the score adds up
(how often that kind of question was worth a look, times how strong this one is, combined as "at least one is
right"); the officer's result. The page computes nothing: `drishti/explain.py` runs the work through the same
`assess_work()` as the batch, and `tests/test_explain.py` checks that the trace's score equals the pipeline's on 60
works and that nothing private or accusing is in it.

**Built-in examples** (`data/trial/explain_examples.py` → `apps/web/public/explain/examples.json`, summary in
`results/explain_examples.txt`): made-up works placed in Jaunpur (the dashboard district with the most dated
recommendations), checked by the real engines against the dashboard's 40,935 works.

| Example | Band | Score | Pre-sanction colour | What fires |
|---|---|---|---|---|
| An ordinary new road (length, ends and village named) | LOW | 0.000 | Green | nothing |
| A temple as the work itself | HIGH | 0.818 | Red | R07 not-allowed work |
| A large sum that says nothing ("As per recommendation letter attached", Rs 26 lakh) | HIGH | 0.904 | Red | R12 |
| One solar light for Rs 4.95 lakh | MEDIUM | 0.417 | Amber | Cost above peers |
| Completed 80 days before it was recommended | HIGH | 0.786 | - (completed) | R06 |
| Two checks agree (that light, inside a temple's campus) | **CRITICAL** | 0.894 | Red | R07 + Cost |
| A real work of the district typed in again | MEDIUM | 0.363 | Amber | Duplicate & Split, funded again after completion |

The vague example shows why one check alone stays HIGH even above the Critical line (0.904): Critical needs two
different checks to agree, as in the "two checks" example.

**Found while building it:** (1) the examples' real neighbour descriptions carried names in "<name> ke avas" and its
other spellings; the masker learned them (T056 masker table above, 13,564 → 13,776). (2) R06's sentence read "0.00%
of works ... (against 0.00% across the scheme)" when no other work in the data carries the defect (the dashboard tables:
none of 11,577 works with both dates); it now says so in words (`validation/timeline.py`, test added).

**Checked in a browser** (Chromium, the production build): all six steps of four examples at 1280 px and of one at
390 px (a phone), no console errors; "your own example" run end to end against a local engine on the test country
(a typed name and phone number come back hidden).

## T095 (3 Oct 2026): what works cost, and how long they take, in Uttar Pradesh (Cost v3 prototype)

The owner's pivot (plan `docs/plans/T097-cost-agent-v3.md`): the implementing agency fills a full cost estimate form,
and the Cost agent compares the estimate with the same kind and size of work in the same district, then with the MP's
amount. Its first reference is real works. `data/trial/cost_v3_reference.py` read the eSAKSHI dashboard tables for
Uttar Pradesh: **8,702 works**, the state with the most dated works and stated sizes (712 roads or drains with a length,
643 works with a count). Output `results/cost_v3_reference_uttar_pradesh.json` / `.txt`, aggregates only. Price per unit
is counted only for works whose description states the size of one job, read by the Cost engine's own readers.

| Work (UP) | Priced by | Works sized | Median | Middle 80% (below / above the median) | 98th percentile | Recommendation → sanction / sanction → completion (median days) |
|---|---|---|---|---|---|---|
| Solar / LED street light | per light | 369 | Rs 20,944 | −0.3% / +4.6% | Rs 82,609 | 82 / 295 |
| CC road | per metre | 493 | Rs 7,698 | −41.7% / +58.5% | Rs 15,711 | 56 / 286 |
| Paver / interlocking path | per metre | 206 | Rs 5,789 | −22.2% / +94.9% | Rs 14,460 | 68 / 278 |
| High mast | per mast | 232 | Rs 1,72,675 | −9.1% / +60.9% | Rs 4,08,965 | 31 / 354 |

What it shows:
- **A standard item has a tight band.** One solar light: 80% of works within −0.3% / +4.6% of the median.
- **What eSAKSHI cannot see spreads widely.** The middle 80% of CC roads runs from 42% below to 59% above the median,
  because no width or thickness is recorded. The street light's 98th percentile (Rs 82,609, 3.9× the median) mixes
  solar lamps with grid lights on new poles. The form's specification fields exist to separate these.
- **Place matters.** The median CC road per metre ranges from Rs 4,000 (Ghazipur, 17 works) to Rs 12,259 (Mahrajganj,
  27) across the 18 districts with 10+ sized roads. Bareilly's street lights (Rs 40,669, 26 works) cost twice Jaunpur's
  (Rs 20,896, 139). The reference must be per district.
- **Time barely matters inside 2024–2026.** CC road per metre: 2024 Rs 8,345, 2025 Rs 7,676, 2026 Rs 7,154. The prototype
  can pool these years; the Schedule of Rates (T096) will set a price date.
- **Times** (CC road): recommendation to sanction p10 / median / p90 = 18 / 56 / 169 days; sanction to completion 142 /
  286 / 471 days.

The official rate sources (CPWD, data.gov.in, GeM, PMGSY, state PWD sites) are blocked by this cloud environment's
network policy (tested 3 Oct 2026), so T096 is a human task.

## T097 (3 Oct 2026): the Cost Estimate engine on works it has never seen

The engine (`agents/cost_estimate/`, plan `docs/plans/T097-cost-agent-v3.md` §11) reads the agency's cost estimate form.
It asks the officer only when:
- a **confirmed** material quantity is more than 25% above what the size needs; or
- the price per unit is more than 25% above the 98th percentile of the same standard item in the district (or
  state) **and** the estimate is more than 10% above the MP's amount.

It is shown, not counted.

**Which real-works groups it can compare** (`data/build_cost_reference.py` → `results/cost_v3_reference_build_up.txt`):
a group is used only with 30+ works, a tight spread (p90 within +25% of the median), and the form's own unit of size.
- In Uttar Pradesh: solar street lights (334 works: median Rs 20,944, p98 Rs 23,588; Jaunpur and Varanasi have their
  own groups) and high masts in Bareilly, Kheri and Sitapur.
- Roads are never compared per metre: 0 of UP's 1,129 CC-road records state a width.

**Hold-out** (`data/trial/cost_v3_holdout.py` → `results/cost_v3_holdout_up.json`): the reference was built from UP works
dated before 2026 and tested on the **68** 2026 works of those kinds (54 high masts, 14 solar lights). Each became a
complete form at its real price, with the MP's amount equal to the estimate, as on eSAKSHI. One more work (215 masts
under one price, really several sites) was refused by the form itself.

| Measure | Result |
|---|---|
| Works it could compare | 42 of 68 (26 high masts in districts without a tight group: "could not check") |
| Real works above the price question line | **0 of 42** |
| Planted price ×1.1 / ×1.25 / ×1.5 / ×2 / ×3, MP's amount at the real figure | asked 0 / 9 / **42 / 42 / 42** of 42 |
| Same works at ½×, 2×, 5× the number of units, same unit price | **0 of 204** answers changed |

For comparison, the old engine caught a planted 3× price 6% of the time (T080), because without the size a 3× price
looks like a 3× bigger job.

The limit, honestly: with eSAKSHI's records, only standard items can be priced. Everything else answers "could not
check" until the state's Schedule of Rates (T096) or completed forms give a reference that knows the size. Line-by-line
rates wait for T096.

## T099 + T100 (3 Oct 2026): simple and certain: one Cost check, one Duplicate check

**The owner:** "remove all the bloat, only the very highly effective stuff that WORKS". The Cost agent must work; the
Duplicate agent should only do what has a high chance of being very accurate, compare a work with the sanctioned works
of its area, and account for continuations. Script `data/trial/simple_certain_trial.py` → `results/simple_certain_trial.json`
/ `.txt`; by-eye labels `data/trial/simple_certain_labels.py`; plan `docs/plans/T099-T100-simple-and-certain.md`.

**Cost from the record alone.** The most precise check a record supports is a stated count of a standard item.
The Cost Estimate engine's reference groups exist for every state; they can price **1,032 of 40,935** works (11 tight
groups, 7 states). Every real work the check would question, read by eye:

| | Questioned | Read by eye |
|---|---|---|
| In-sample (reference from every year) | 5 | 3 misread counts, 1 bigger item, 1 grey |
| Hold-out (reference before 2026, the 211 works of 2026) | 10 | 2 misread counts, 8 bigger items |
| **Together** | **15** | **0 real price questions**, 1 grey |

The misreads are the record's count being wrong for the money: "1 nag" twice for two people's lights, six sites in one
record. The bigger items are a 16 m mast, "4 way" lights and solar mini-masts. On every one of the 36,430 works with a
disbursed amount, the money paid is at or under the amount sanctioned, so no overpayment exists to ask about either.

**So the Cost check runs only on the agency's cost estimate form** (Cost slot, T099); a work with no form is
NOT_APPLICABLE. The old Cost Anomaly is retired.

**Repeats from words.** The team's 289 pairs read by eye for T030/T051 (108 one asset funded twice), re-read by stricter
and stricter rules:

| Rule | Right | Finds of the 108 |
|---|---|---|
| every pair the old engine flagged | 108 / 289 (37%) | 100% |
| identical wording | 24 / 37 (65%) | 22% |
| 90%+ alike, every place word shared, nothing apart, no continuation word, not many sites | 38 / 59 (64%) | 35% |
| ... and two or more place words | 25 / 35 (71%) | 23% |
| identical wording, two or more place words, nothing apart | 13 / 16 (81%) | 12% |

On the dashboard's own works, the strict rule's 25 pairs more than 60 days apart read **8 same, 6 grey, 11 different**.
The misses:
- a village or landmark is not a site;
- an SC and a BC colony;
- a ground and a first floor;
- a resubmission or a "completion of" work;
- no place at all.

**So a repeat is asked only with the form.** The questions are:
- `SANCTIONED_WORK_AT_THIS_SITE`: map pins within 50 m, same kind of asset, the link not declared;
- `REBUILT_SOON_AFTER_COMPLETION`: a declared rebuild of a work completed under 3 years ago.

Look-alikes by words are notes, and the form asks the agency about each: the same work (blocked), continues it, or a
different work (say what differs).

**The one split kept, the strictest:**
- 2–5 alike pieces at one place, or numbered parts of one job;
- one MP, filed within 30 days;
- every piece 96–100% of the Rs 5 or 10 lakh limit.

Every group on the dashboard was read by eye: **14 groups (34 works): 12 one job cut into pieces, 2 grey, 0 not.**
Examples:
- reach-1 / reach-2 of one road at Rs 4,99,942 and Rs 4,99,981;
- four rooms of one school at Rs 5,00,000 each;
- Sy.No 488 / 488-A / B / C of one hill road;
- "a project of 04 mineral water plants" filed as 4 works.

The grey ones are the left and right sides of one bridge approach, and "CC roads in various localities" of one ward,
filed twice. The 96% line was set while reading these groups; a fresh read on the hosted works is the next
measurement. `reliability.json`: 12 of 14.

**The dashboard's 40,935 works** (`dashboard_trial.py --tag t099_before` on main, `--tag t099_after` here):

| | Before (main) | After |
|---|---|---|
| CRITICAL / HIGH / MEDIUM | 36 / 391 / 1,392 | **8 / 431 / 1,231** |
| Review queue | 427 | **439** |
| Cost flags (counted) | 135 (`COST_ABOVE_PEERS`) | 0 (no forms yet) |
| Duplicate flags (counted) | 1,394 (1,330 bulk orders, 48 splits, 13 stretches, 3 repeats) | 34 (`SPLIT_JUST_UNDER_LIMIT`, 14 groups) |

**What moved:**
- **11 left the queue.** Each was a long wait for sanction plus one other flag: 7 a bulk order (read 15 of 15 as
  ordinary bulk purchases) and 4 the old cost flag (54 of 128). Alone, a wait stays MEDIUM by design.
- **23 entered:** the pieces of the strict split groups that were not already in the queue.
- **CRITICAL fell from 36 to 8**, because most had two engines agreeing through a bulk-order or old cost flag.

Works filed together (the same wording, MP and day) still show as one case in the queue, for display only.

**The test country** (CI gate, seeds 1–2):
- planted map-pin repeats and declared rebuilds are caught **100%**, and their look-alikes **0%** (another kind of
  asset at the pin, the same kind 80–300 m away, a declared continuation);
- planted splits at 92–100% of the limit are caught 43% / 50% (only those whose every piece is 96%+);
- queue precision is 0.946, and ordinary works queued 0.1%.

Record-only kinds (prices raised on a record, repeats and repairs by words) stay planted with no engine meant for them.

## T121–T125 (4 Oct 2026): the four agents, built and measured

The owner's four agents (plan [`plans/T120-four-agents.md`](../plans/T120-four-agents.md)): **Cost, Duplicate Work,
Time & Rules, Site Progress**, a quarter of the weight each. Guideline Compliance, Fund Flow, Office Patterns,
Paperwork and Photo Evidence are retired (their code stays as libraries; Time & Rules reuses the timing rules).

**Cost: every line, then the whole estimate (T121).** Each confirmed line of the agency's form gets a fair rate: the
state's Schedule of Rates item it cites, else what 3+ other agencies in the district paid on 5+ forms of the last six
months (never the agency's own; capped at the SoR rate + 15%), else the SoR rate of the material. Each quantity is held
to what the stated size needs + 10%. The whole estimate is asked about only when 60%+ of the money could be priced and
the gap is 15%+ **and** Rs 50,000+. Script `data/trial/cost_whole_trial.py` → `results/cost_whole_trial.txt`, 1,000
synthetic CC-road forms per cell (the honest spread around the fair rate is an assumption, not a measurement):

| Fair rate from | Honest spread | Honest forms asked | Every line +20% asked | Every line +10% asked | One line ×2 (cement) |
|---|---|---|---|---|---|
| the Schedule of Rates | 5% | 0.0% | 94.2% | 2.0% | 100% |
| the Schedule of Rates | 10% | 0.1% | **82.5%** | 16.8% | 96.6% |
| the Schedule of Rates | 15% | **2.4%** | 70.3% | 24.7% | 89.1% |
| the district's rates | 5% | 0.0% | 93.1% | 0.8% | 100% |
| the district's rates | 10% | 0.0% | **91.5%** | 29.0% | 98.8% |
| the district's rates | 15% | **3.3%** | 79.9% | 33.5% | 95.3% |

- The plan's target (§14: 9 in 10 padded by 20%+ caught, at most 2 in 100 honest asked) is **met at a 5% spread, and
  at 10% with district rates; missed at 10% with SoR rates (82.5%) and at a 15% spread (2.4–3.3% honest asked)**.
  The real spread is unknown until real forms come in; the margins stay starting values (T098).
- Padding the **quantity** (cement ×1.5) moves the whole estimate too little to be asked (5–39%), so the separate
  quantity question stays: whole or quantity together catch it **100%**, and honest forms get the quantity question
  **0%**.
- Every Schedule of Rates line waits on T096 (the SoR files are not loaded yet); until then a line is priced only from
  district rates, which need 5+ forms from 3+ other agencies. With no real forms yet, the whole estimate answers "not
  judged" on every real work today, and the per-unit price question (T099) still runs.

**Time & Rules (T122).** One agent from R01 (the 75-day clock, election-code days left out), R06 (impossible dates),
R13 and R14 (constructions complete within days), plus:
- `SANCTIONED_LATE`: a fact about the office, risk 0.05. On the dashboard it fires on **9,401** works (60% of the 15,662
  with both dates, T120) and never queues on its own (scores 0.05).
- **The comfort window** from the form's estimated time to completion. The estimate is first held between the
  shortest believable time for the kind of work (`reference/time_floors.json`: 7 days for roads, drains, walls, ponds
  and similar, the measured R14 line; 21 days for buildings, by design from concrete curing, IS 456) and the longest
  usual time (eSAKSHI's 90th percentile for the type, `reference/time_bands.json`, 453 days over all works). The early
  line is the larger of the floor and a quarter of the accepted estimate; the late line adds half the estimate (at least
  61 days), the declared monsoon months and any recorded extension.
- `FINISHED_TOO_FAST` (risk 0.6) only for a construction of Rs 3 lakh+ finished before the early line **with no site
  video showing the work**; `PAST_PROMISED_TIME` 0.2, or 0.4 when the last three site videos show no change. Both are
  at the 1-in-4 prior until read by eye. 26 unit tests, including both lines' edges, padded and too-short estimates,
  lost months, extensions and damaged forms.
- On the dashboard none of the window's findings can fire yet (no real work has a form), so R13/R14 still ask, as
  before.

**Site Progress v3 (T123 + T124).** Monthly site videos filmed in the capture page at the site's marked viewpoints,
sealed (SHA-256) when filming stops; read once by a job on a machine with OpenCV, which keeps blurred frames and readings
and deletes the video. Findings: footage seen before (3+ frames in order), the same place as another undeclared work
(40+ matching points), not filmed at this site (GPS **and** views both), the claim not shown twice in a row, complete
not shown, already built at the first visit. A dark, unsealed or not-in-app video is never a finding: the visit is not
accepted.
- The video readers on drawn scenes (`tests/video/`, 14 tests): an honest month with no building matches its
  viewpoints and reads "no change"; a wall built between visits reads "changed"; the same video uploaded again reads as
  reused footage, a new film of the same site does not; another site's video does not match; this site filmed for
  another work reads "same place"; a phone held still while the picture moves (a screen filmed) is not consistent; an
  edited file breaks the seal.
- **End to end** (`data/trial/capture_e2e.py` → `results/capture_e2e.txt`): headless Chromium films a made-up site
  through a fake camera, through the engine, a local storage stand-in and the video job. Hall H1's first and monthly
  visits match 5 of 5 viewpoints and read "changed"; H1's first video filed again for hall H2 reads **42 reused frames**
  and H1's place (875 matching points), and Site Progress asks about both; H1 raises nothing.
- Not yet measured on real sites: plan §14's field trial (T126, 3–5 real works, three months, planted tricks).

**The queue with four agents (T125).** The dashboard's 40,935 works (`dashboard_trial.py --tag t125_after`, against
`t099_after`):

| | Before (seven engines) | After (four agents) |
|---|---|---|
| CRITICAL / HIGH / MEDIUM | 8 / 431 / 1,231 | **2 / 215 / 342** |
| Review queue | 439 | **217** |

- **In the queue now:** 185 constructions recorded complete within a week of sanction (R14, read right 25 of 25) and 34
  pieces of the 14 strict split groups (12 of 14 read as one job); 2 carry both. The same 320 R14 works and the same
  34 split pieces fire as before (compared work by work in `_flags.json`).
- The other 135 R14 works are graded low (LOW), as before.
- **What left:** the queue's share from checks the four agents no longer make (in `t099_after`: R12 big sums that name
  nothing fired on 161 works, R07 possibly not allowed on 63, office price habits on 1,311).
- MEDIUM is now exactly the 342 works still waiting for sanction past 75 days (R01); never queued alone.

**The test countries** (`synthetic_eval.py --tag t125`, seeds 11–13, 61,077 made-up works, against `agents5`):

| | Before | After |
|---|---|---|
| Review queue | 207 | **101** |
| Queue precision (queued works that are planted problems) | 0.70 | **1.00** |
| Ordinary works queued | 0.11% | **0.0%** |
| Planted problems caught by the engine meant for them | 73.7% | 20.3% |

- The fall in "caught" is by design: the planted prohibited works, outside-area ceilings, vague big sums and office
  price habits are no longer checked (0%), and prices or repeats from the record's words alone were dropped in T099 +
  T100.
- What is still checked: R13 built in days **100%** caught and queued; R06 impossible dates 100% caught, 67% queued (an
  office's bulk entry looks the same and is never queued: 211 of 211 such works stay out); an office closing works in
  2–20 days 37% (only those within R13's line); map-pin repeats and declared rebuilds **100%** (MEDIUM: one finding at
  the 1-in-4 prior until read); splits 33% / 28% (only those whose every piece is 96%+ of the limit).
- Every look-alike stays out of the queue: 0 of 5,694 temple landmarks, 1,044 schools named "Mandir", 1,343 batches
  for different villages, 300 opposite sides of one road and the map-pin look-alikes.

## T134 (5 Oct 2026): the website's work intelligence form, read by the four agents, with example filings

The website's form (PSWIF v1.0, `/work-form`) now reaches the agents: `cost_form/pswif.py` turns a filled form into the
engine's cost form and work record, and `POST /api/v1/work-form/check` runs the four agents on it (nothing stored).
Twelve made-up filings in the real district of Jaunpur show each agent asking: made-up agencies and villages, honest
quantities from the size norms unless the example pads them, checked by the real engines against the dashboard's
40,935 works plus 11 made-up background filings (other agencies' roads, an earlier road and hall, a split's other
pieces). `data/trial/work_form_examples.py` refuses to write the file unless each example raises exactly its
questions (`results/work_form_examples.txt`):

| Example | Agent that asks | What it raises | Band (score) |
|---|---|---|---|
| An honest CC road | none | nothing; all four checks assessed | LOW (0) |
| Every line a little high | Cost | `ESTIMATE_ABOVE_FAIR_PRICE` | MEDIUM (0.25) |
| Twice the cement the road can use | Cost | `MATERIAL_QUANTITY_ABOVE_SIZE` + `ESTIMATE_ABOVE_FAIR_PRICE` | MEDIUM (0.44) |
| Solar lights at more than twice the usual price | Cost | `ESTIMATE_ABOVE_STANDARD_AND_MP` | MEDIUM (0.25) |
| A "new" road on top of one the scheme already paid for | Duplicate Work | `SANCTIONED_WORK_AT_THIS_SITE` | MEDIUM (0.25) |
| Rebuilding a hall finished 16 months earlier | Duplicate Work | `REBUILT_SOON_AFTER_COMPLETION` | MEDIUM (0.25) |
| One lane filed as three works, each just under Rs 5 lakh | Duplicate Work | `SPLIT_JUST_UNDER_LIMIT` | HIGH (0.72), queued |
| A 350 m road "complete" 6 days after sanction | Time & Rules | `FINISHED_TOO_FAST` | MEDIUM (0.25) |
| Eight months promised, sixteen months on, and stopped | Time & Rules | `PAST_PROMISED_TIME` | MEDIUM (0.25) |
| The first site video was filmed for another work | Site Progress | `FOOTAGE_USED_BEFORE` + `SAME_PLACE_AS_ANOTHER_WORK` | MEDIUM (0.44) |
| "Roof slab cast", twice, and the videos don't show it | Site Progress | `CLAIM_NOT_SHOWN` | MEDIUM (0.25) |
| A monthly video filmed 2.4 km away | Site Progress | `NOT_FILMED_AT_THIS_SITE` | MEDIUM (0.25) |

- One finding is MEDIUM (the 1-in-4 prior of fusion v3 until its findings are read by eye); only the split reaches
  the review queue on its own. The two halls whose filing predates the district's rates get Cost "could not check",
  shown as such, never as a pass.
- **In a real browser** (`data/trial/work_form_e2e.py`, `results/work_form_e2e.txt`): a local Postgres with Jaunpur's
  1,038 real works, the engine and the web app in the public view. The dashboard's card opens `/work-form`; every
  example fills the framed form (title, agency and BOQ rows read back) and the panel shows its verdict; a deep link
  `?example=time_fast` opens with its filing; a form without its district gets a plain message; 0 page errors.
- **The demo's live check uses the same example data** (`POST /work-form/check?demo=true`, `drishti/demo.py`, the
  file `reference/demo/work_form.json` written by the examples script): the other agencies' filings, the earlier
  works and each example's record after sanction, placed in the form's district; nothing stored, never used by any
  other route. In the browser, all 12 loaded examples raise **exactly** their worked flags live, and the script
  checks the same path without a browser before it writes the files.
- **The page shows what is flagged and why, simply**: each agent says Flagged, Clear, Not checked or After sanction,
  with one line built from the finding's own numbers (the trace now carries a whitelisted `facts` part: numbers,
  dates, work IDs, item names); the flagged fields are outlined in the form in the agent's colour (1 to 4 fields per
  example; the padded estimate marks its total and its three highest rates); "Show in form" scrolls to one.
- **Editing a field changes the answer**: "Twice the cement" with the cement set back to 1,307 bags clears both of
  Cost's flags (LOW). The **Data tab** shows, in plain words, the prices other agencies filed (10 items; cement Rs
  380 a bag on 22 forms), the standard solar-light price (Rs 20,896, 136 real eSAKSHI works in Jaunpur), the works
  on record, what happened after sanction (dates, site videos) and the rules the agents use.
- **Adapter rules** (`test_pswif.py`, 21 tests; `test_work_form_api.py`, 4): fill only what the agency wrote; fields
  PSWIF never asks are skipped by the required checks (`cost_form/versions.py`), never guessed; a BOQ line's
  justification confirms that line, the rate-deviation note the whole estimate; the work type from the title before
  the scope (a road "near the primary school" is a road); the rate index groups forms by the agency that filed them
  and dates them by the form's filing date (`rates.agency_of`, `filed_on`).
- Engine fixes found by the examples: a work recorded complete before its own planned start counts "too fast" from
  the sanction (it said "0 days after the work could start"); quantities read "2,614 bags", not "2,614 bag".

## T135 (5 Oct 2026): the agents' self-improvement loop

Each agent was run through samples and attacked until it stopped breaking
(`data/trial/agent_robustness_loop.py`, plan `docs/plans/T135-robustness-loop.md`). The samples are
the work form's example filings in Jaunpur on top of the district's 1,038 real works. The probes are
random damage, honest noise, deliberate evasions, scarce data and scale. The final run
(`results/agent_robustness.txt`):

| | |
|---|---|
| Probes | **65: 59 PASS, 0 FAIL, 6 LIMIT** |
| Random damage (seed 7) | **3,000 runs: 0 agent errors, 0 broken contracts, 0 different answers the second time** |
| Scale | 3,000 filed roads in one district: one work's four agents in 0.06 s |

**What the loop broke, and how it is fixed** (each with a regression test in the engine suite):

- **Crashes**: infinity as an estimated duration, NaN or infinity as a video's frame count, a list
  where a unit belongs. Every number reader now takes finite numbers only, every unit reader text
  only. `tests/evaluation/test_random_forms.py` keeps 300 damaged forms and videos in CI.
- **Cost**:
  - Padding hidden in a lump sum or "other charges" was invisible. Lump sums beyond 2% of a
    construction estimate, other charges beyond 5% (23% when the form names no GST) and
    contingency beyond 5% now count as not shown to be fair.
  - Items given names no reader knows: `ESTIMATE_NOT_ITEMISED` when over 40% of a construction
    estimate is lump sums or unrecognised items.
  - One unanswered warning switched the whole check off. Now only a line whose rate or unit looks
    like a typing mistake is held out; the rest is judged.
  - One agency filing many forms dragged the district's price. Now one vote per agency, and name
    variants are one agency.
  - Prices that disagree were trusted. Now they are switched off for that material and recorded as
    a gap (with the state's forms, 10% more leniently, when the district has too few).
  - A held or unpriced line watered the gap down. The gap is now measured against the fair price
    of what was priced.
  - A size the form's own scope contradicts: `SIZE_NOT_AS_DESCRIBED`.
  - Two adapter faults: a website filing with any lump sum could never be judged, and the trade
    words *kapchi*, *rodi*, *jelly* and "fine / coarse aggregate" were not recognised.
- **Duplicate Work**:
  - An old road filed again 100 m longer, or pinned 60 m off: a road lying 80% on another's line
    is the same ground.
  - A re-filed work declared a "continuation" or "repair", or named only among the nearby works:
    on a finished work's own ground it is a rebuild (`REBUILT_SOON_AFTER_COMPLETION`); on an
    unfinished one it is asked about.
  - Map pins outside India (0, 0; swapped) and roads with one end are set aside, and the result
    says so.
- **Time & Rules**:
  - An estimate over twice what 9 in 10 such works take falls back to the typical time.
  - A start promised more than 6 months after sanction counts from 6 months.
  - Lost months count as calendar months, at most 4.
  - A reused or elsewhere-filmed video no longer counts as showing the work built.
  - "completed" in lower case was read as not complete.
- **Site Progress**:
  - Never filming (or uploading only unsealed videos): `NO_SITE_VIDEO` 60 days past the start.
  - "can't tell" slipped between two "not shown" no longer resets the claim check.
  - Every video filmed consistently away from the form's pin: `SITE_NOT_AT_FORM_PIN`.
  - Videos dated after today are not counted.
  - Vague claims ("work in progress") are asked to be specific.

**Price data that cannot be trusted is switched off, then learned.** A material whose district
prices are too few, too old or disagree is not priced. The gap is recorded with its reason, and
`GET /api/v1/cost/data-gaps?district=` lists what to collect where. Every form filed joins the
index, so a gap closes by itself once enough agree. The live check now also reads the state's
other forms (`batch.state_forms`).

**The measurements the fixes could move:**

- **Planted forms** (`results/cost_whole_trial.txt`):
  - District rates, 10% honest spread: +20% padding asked **94.2%**, honest asked **0.1%** (target:
    at least 90%, at most 2%).
  - District rates, 5% spread: 95.9% and 0.0%. SoR rates, 10% spread: 86.5% and 0.2%.
  - At a 15% spread, honest forms are asked 3.6% (district) and 2.8% (SoR): over the 2% target, as
    before the loop.
- **The dashboard's 40,935 real works** (`results/dashboard_t135_after.json` against
  `t125_after`): the same bands, the same queue of 217, and every finding on the same works
  (compared work by work). The fixes touch forms and videos, which no real work has yet.
- **The example filings**: 12 of 12 raise what they are meant to. The 6-day road also gets
  `NO_SITE_VIDEO` (never filmed, 100 days after sanction). The page passes in a browser with 0
  page errors (`results/work_form_e2e.txt`).

**Still limits** (`results/agent_robustness.txt`, reasons in the plan):
- padding just under 15%;
- split pieces at 95% of a limit;
- GPS faked inside the site with the views elsewhere (one proof);
- 22% padding priced only from the state's forms;
- every agency in a district padding together (needs the SoR, T096);
- a bigger size claimed consistently everywhere (needs the site videos to measure it).

## T136 (5 Oct 2026): five filings end to end, Site Progress with room for error, and one real region

**One region's real works: Uttar Pradesh** (`data/trial/up_real_check.py`, `results/up_real_check.txt`).
The government sites (eSAKSHI, data.gov.in, the PWD Schedules of Rates) cannot be reached from
the build machine, so the real data is the eSAKSHI dashboard tables already in the team pack.
Uttar Pradesh is their largest state: 8,702 of 40,935 works, in 74 districts; Jaunpur has 1,038.

- **All four agents on every UP work**: 10.3 s (1.19 ms a work, slowest 458 ms), **0 agent
  errors**. Cost and Site Progress are not applicable (no form or video exists for these works).
  Duplicate Work assessed 8,641 and could not assess 61 (no description). Time & Rules assessed
  all 8,702. It asked `SANCTIONED_LATE` 2,292 times (an office fact, risk 0.05, never queues
  alone), `SANCTION_OVERDUE` 30, `BUILT_IN_DAYS` 2 and `BUILT_RIGHT_AFTER_SANCTION` 2. Bands:
  HIGH 2, MEDIUM 30, LOW 8,670.
- **The Time agent's caps hold for UP**:
  - The national "longest usual time" is within ±2.2% of UP's own 90th percentile for its five
    big types:
    - street lights: UP 460 days, India 450;
    - CC roads: 471 / 462;
    - borewells: 392 / 396;
    - paths: 463 / 470;
    - solar plants: 306 / 306.
  - 86.6–100% of UP's finished works fall within it. UP works are slower in the middle: median
    286–295 days against 199–203 nationally.
  - **Decision: keep the national bands; no per-state bands.** A state whose works close
    suspiciously fast would make its own cap stricter for honest works. In Bihar, 87 libraries
    were "completed" a median 6 days after sanction.
  - Recommendation to sanction: UP median 82 days, 53.9% past 75 days (India 90 days, 60.0%).
- **UP's real prices per unit of size**, the yardstick for the demo's honest values:
  - CC roads: Rs 4,491 to 12,201 a metre (middle 80% of 493 works, median 7,698);
  - paths: Rs 4,505 to 11,284 a metre (206 works);
  - high masts: median Rs 1,72,675 (232 works);
  - **solar street lights: median Rs 20,944 a light, tight** (334 works; Jaunpur 136 works,
    median Rs 20,896).

**Five filings, form to risk score** (`data/trial/end_to_end_examples.py`, `/end-to-end`,
`results/end_to_end_examples.txt`). Each filing goes through the same path as the live check: the
website form, the form's own check, the four agents and the fused score. Site Progress is shown
as a placeholder until its field trial (T126).

| Filing | Ready | Agents ask | Score | Band |
|---|---|---|---|---|
| An honest 300 m CC road (Rs 4,838 a metre: inside UP's real range) | yes | none | 0 | LOW |
| 20 solar lights at Rs 20,900 (Jaunpur's real median) | yes | none | 0 | LOW |
| The honest road with Rs 5.5 lakh in equipment hire | yes | Cost | 25 | MEDIUM |
| One lane as three pieces end to end, each just under Rs 5 lakh, one described in other words | yes | Duplicate | 72 | HIGH |
| A "new" hall 20 m from a finished one, rates +25%, waiting 100 days | yes | Cost, Duplicate, Time | 46 | MEDIUM |

The road with hidden hire costs Rs 6,672 a metre, which is inside UP's real range. A price check
on the record alone would pass it; the line-by-line check of the form asks.

The page passes in a real browser (`results/work_form_e2e.txt`):
- each filing's score is shown as computed;
- the placeholder and the decision are on the page;
- 0 page errors;
- the 12 work-form examples still match the live check.

**Robustness loop, round 6** (`results/agent_robustness.txt`): **81 probes, 74 PASS, 0 FAIL, 7
LIMIT**; 3,000 random damages (seed 7): 0 agent errors, 0 broken contracts, 0 different answers.
The round tried "just past a line", lines nobody prices, renamed pieces, and Site Progress's room
for error. What got past, and how it is fixed (each with a regression test):

- **Cost**:
  - Sand doubled went unasked. The only CC-road norm was cement. Sand now follows the same IS 456
    nominal mix (M20 = 1:1.5:3, 0.42 m³ of dry sand per m³). It allows 20% for moist sand's
    bulking, so honest estimates of 0.44–0.47 m³ are never asked. It applies only under bases
    that take no sand.
  - A line no reader prices (equipment hire, 30 days raised to 250) hid Rs 5.5 lakh. In a
    construction estimate, such items beyond 15% of the lines now count as not shown to be fair,
    like lump sums. Honest earthwork, shuttering and curing (about 10%) are not asked.
  - Rates typed "Rs 464/-" read as no rate. The adapter now reads Rs, ₹, INR, /- and Devanagari
    digits.
  - A form whose lines carried no readable rate passed as "ready". It now asks for the rate.
- **Duplicate Work**:
  - A split with one piece called a paver road, "Other" or "Gravel / WBM", or described in other
    words, escaped the wording rule. The forms' map pins now find the strictest split too: pieces
    of one lane laid end to end or at one pin, recommended within 30 days, every piece 96–100% of
    a limit.
  - A road subtype the engine has no code for kept only one end. It now keeps both.
  - A "new" hall pinned 60 m from a finished one (just past the 50 m line) is now named in a note
    (`NEAR_SANCTIONED_WORK`, within 150 m, never counted). Site Progress's first video
    (`ALREADY_BUILT_AT_START`) settles it.
- **Site Progress**:
  - A work recorded complete with not one accepted video is now asked at once. Before, it waited
    60 days past the start.
  - **Room for error.**
    - A dark, blurred or very short video says "can't tell", never "does not match". The
      agent's "filmed elsewhere" and "claim not shown" no longer count such a video.
    - A GPS fix counts with its own reported accuracy; when every fix is poorer than 50 m, the
      GPS says "can't tell".
    - A viewpoint missed one month is still compared the next. Every viewpoint the site ever had
      is compared, from its last 3 good frames; a visit that did not match never becomes the
      reference.
    - A viewpoint the person could not reach is skipped with a reason and not counted against
      the visit.
  - **Still does its job**: two unusable videos in a row (dark, short, viewpoints not filmed, or
    views not matching while the GPS says "at the site") ask `SITE_VIDEOS_UNUSABLE`. This also
    closes "GPS faked inside" when it is repeated. One poor month is never a finding.
  - **The capture page** no longer refuses an honest visit. Only a useless video stops the upload
    (under 20 s, a viewpoint half marked, a first visit with under 2 viewpoints). Everything else
    is a tip noted with the video: "Can't reach" a viewpoint, weak GPS, the phone placing you
    away from the pin, poor light, walking fast.
- **Proof in a real browser** (`results/capture_e2e.txt`, fake camera, local engine and storage):
  - The honest visit was uploaded with one tip: 3 of 5 viewpoints marked, 2 "can't reach",
    GPS ±90 m and 150 m off the pin.
  - The reader found all 5 views, saw the work changed, and said "can't tell" for the GPS.
    Site Progress asks nothing on H1.
  - The hall filmed at another hall's site is still asked (`FOOTAGE_USED_BEFORE`,
    `SAME_PLACE_AS_ANOTHER_WORK`).
- **Video reader**: 20 tests on drawn scenes (6 new; each new one fails on the old reader).

**Unchanged where it should be.**
- The dashboard's 40,935 real works (`results/dashboard_t136_after.json` against `t135_after`):
  the same bands, queue (217) and flags, work by work.
- The 12 work-form examples raise exactly what they did. Two outputs changed:
  - the 6-day road's `NO_SITE_VIDEO` now says it was recorded complete with no video;
  - two Cost limitations quote a higher priced share, because sand is now normed.

**Limits now 7.** The six of T135 (with "GPS faked inside" now caught when repeated), plus:
labour days multiplied 2.5 times are not asked, because labour per m³ is not normed yet (CPWD's
Analysis of Rates gives it, T096).

## T137 (5 Oct 2026): other agent architectures, tested against the current ones

The owner asked for other designs to be tested against the current agents. Two conditions:
- a switch only when the other design is proven better;
- it must stay immune to the loopholes the loop closed.

Every candidate ran on the same benchmarks. Where a design has a free line, the line is set so the
same share of honest cases is asked (`data/trial/architecture_bakeoff.py`; results
`results/architecture_bakeoff_{cost,site,dup}.txt`). Everything below is planted or simulated:
the honest spreads and the video reader's error rates are assumptions until real forms (T098) and
the field trial (T126).

### Cost: the whole-estimate decision. Not switched; the current rule holds up best

500 planted CC-road forms per cell, 12 scenarios. The scenarios cover:
- honest spreads of 5, 10 and 15% and a different spread per material;
- a per-site **carriage** factor on sand, aggregate and base, or one moving **every** line of a
  form (a remote site);
- a scarce district, 3 agencies filing scattered rates on purpose, and the SoR.

Paddings tried: every line +10 to +30%, one line ×2, two lines +40%.

| Candidate | Worst honest asked | +20% caught (mean) | All paddings caught | Cells meeting the target |
|---|---|---|---|---|
| **current: money gap 15% and Rs 50,000** | 3.0% | 79.8% | 63.1% | 1 of 12 |
| current OR peer-adaptive money line | 3.0% | 81.7% | 67.3% | 2 of 12 |
| z-test, precision-weighted (lines independent) | 2.8% | 76.4% | 54.2% | 4 of 12 |
| z-test against the peers' own scatter | 2.0% | 84.3% | 54.9% | 4 of 12 |
| isolation forest (machine learning) | 3.8% | 58.7% | 34.5% | 1 of 12 |

- **The statistical tests read an honest site as padding.**
  - They assume each line varies on its own. They ask no honest form when that is true (0.0% in
    the four independent scenarios).
  - When a remote site lifts every line together, they ask 2.2–2.8% of honest forms.
  - They also catch only about 40% of one doubled line, which the money gap catches 93–100% of
    the time.
- **The isolation forest catches half as much.** It has only the district's own forms to learn
  from.
- **"Current OR peer-adaptive line"**:
  - It asks the same honest forms as today in every scenario (0.2 → 0.4% in one, noise).
  - It catches more only where honest prices are tight: +15% padding in a 5%-spread district goes
    from 50.4% to 100%.
  - It can never ask less than today, so no loophole opens.
  - But the gain rests on the assumption that tight districts exist. **Not switched.** The
    reference code is in the bake-off script, ready to adopt when real forms (T098) show tight
    districts.

### Site Progress's decisions: switched

A simulated year of monthly visits for 2,000 honest works and 500 of each trick.
- The person and the reader err at assumed rates: 8% dark, 8% partial, 8% a month missed, 10%
  weak GPS, 3% GPS jitter, 2% views lost, and a real claim judged "not shown" 5% of the time.
- These rates are also tried at half and 1.5 times.
- Each design is checked at every month's end, as the daily batch does.

| Errors | **T136 design**: honest works asked in a year | **switched design** | tricks caught (switched) |
|---|---|---|---|
| half | 10.4% | 2.9% | 89–100% |
| assumed | **25.7%** | **5.0%** | 86–100% |
| 1.5× | 45.0% | 9.4% | 79–100% |

- "The last two videos unusable" asked 449 of 2,000 honest works a year (assumed rates). Two bad
  videos in a row turn up sometime in most honest years.
  - **Now:** 4 of the last 5 videos unusable, or every video so far from the third. That asks 33
    honest works.
  - On-purpose bad videos are still caught 95.4% of the time (99.6% before).
- A GPS jitter in the same video as lost views read as "filmed elsewhere" for 15 honest works.
  - **Now** that needs the GPS 300 m or more out, or a mock location. Nearer, the views count as
    unusable.
  - A video filmed 200 m away is still caught 100% of the time.
- Two loopholes found while doing this are closed:
  - three bad videos and then no more filming;
  - two honest months filmed, then the work recorded complete with no final video. Now
    `COMPLETE_NOT_FILMED`, 30 days after completion.
- Kept: the claim rule ("not shown twice in a row"). It is now most of the honest questions (54
  of 2,000 a year at a 5% reader error). "3 of the last 5" would ask 11 and catch 5–12 points
  fewer ghost claims. The reader's real error rate (T126) decides it.
- Rejected: a single running score (CUSUM). Set to 2% of honest works, it caught only 37–39% of
  on-purpose bad videos.

### Duplicate Work: a map grid. Switched; same answers, up to 10× faster

A check now looks only at works filed within 200 m of its own pins. That margin covers the
150 m note radius, the 50 m one-site rule and the 25 m road overlap.
- Measured on one district of n filed roads (`results/architecture_bakeoff_dup.txt`, same answers
  every time):

| Filed forms | One check, before → now | The district's batch, before → now |
|---|---|---|
| 1,000 | 8.4 → 1.1 ms | 8 → 1 s |
| 3,000 | 20.9 → 2.1 ms | 63 → 6 s |
| 10,000 | 72.6 → 9.1 ms | 726 → 91 s |

- Every at-site work, distance, overlap and nearby note is identical to the full scan on random
  dense districts of 700 works (`tests/agents/dup_split/test_dup_grid.py`).
- That covers roads and halls, roads with one end, and far ends typed hundreds of km away.

### The score (fusion): not re-tested

Its labelled benchmark (the planted test, T080) needs the 2,09,993-work build, which is not on the
build machine. The four agents' new questions also all sit at the 1-in-4 prior until read. So any
sensible combination ranks works the same, except for ties.

### Proof that nothing else moved

- The loop: **85 probes, 78 PASS, 0 FAIL, 7 LIMIT**; 3,000 random damages, 0 errors. Four new
  probes cover the switched rules and the two closed loopholes.
- The engine suite: 799 passed.
- The 12 work-form examples and the five end-to-end filings raise exactly what they did.
- The capture page end to end: the honest imperfect hall is asked nothing, and the hall filmed at
  another hall's site is still asked.
- The dashboard's 40,935 works: identical bands, queue (217) and flags (`dashboard_t137_after`).

## T139 (5 Oct 2026): the agents on real data from outside the project

The owner asked for relevant data "from anywhere", to test on temporarily and iterate from. What
this machine could reach:
- **Reachable:** Google's Open Buildings (satellite building footprints, CC BY 4.0); India Post's
  post-office directory with map positions (the `indiapins` package on PyPI); the team's
  eSAKSHI dashboard tables.
- **Blocked by the sandbox's network:** government sites (eSAKSHI, data.gov.in, the PWD rate
  schedules), Wikipedia and the web archive. So Cost could not be tested on published rates.

None of it is committed: buildings go to `data/raw/open_buildings/`, which git ignores.

### Duplicate Work: three rules changed, measured on real geography

`data/trial/real_geo_check.py` uses Jaunpur's 1,038 real works: their dates, amounts, MPs and
kinds. Only the map pins are simulated. Each honest work is pinned at a real building with a
phone's GPS error (5 m; 15 m for one pin in ten). The buildings are the 97,965 Open Buildings
within 600 m of the district's 106 post offices. Planted repeats file a sanctioned work again 6–18
months later at the same building. Results: `results/real_geo_check.txt`.

What real data showed:
- **Houses are close.** A house stands 8.3 m from the next (median). It has 23 others within
  50 m. 85% of buildings of 150 m² or more have another within 50 m.
- **Most real works are small items at houses.** 1,006 of Jaunpur's 1,038 works are solar street
  lights, each filed as its own work at one or a few named houses, in programmes of up to 240 a
  day. Nationally, lights are the largest group: 12,460 of 40,935.
- **One place, several purchases.** 673 real pairs of purchases name the same place but are of
  different kinds (computers and furniture for one school, for example).

| Honest filings | T137 rule: honest asked | Now: honest asked | Repeats asked (T137 → now) |
|---|---|---|---|
| lights, 5 a village, one hamlet | 78.9% | 1.7% | 100 → 98 of 100 |
| lights, 10 a village, one hamlet | 87.3% | 1.5% | 100 → 97 |
| lights, 10 a village, anywhere in the core | 36.9% | 5.3% | 100 → 93 |
| lights, 25 a village, anywhere in the core | 54.9% | 6.4% | 100 → 93 |
| purchases, 2 kinds per institution | 52.5% | 2.8% | 100 → 100 |
| buildings, 2 or 4 per village | 11.7%, 14.7% | unchanged | 100 → 100 |

The three changes (each measured on its own in the results):
1. **One programme's lights are not repeats of each other.** A street light filed on the same day
   as another is never "already sanctioned" before it: honest asks fall to 4–15%, with every
   repeat still asked.
   - A hall filed twice on one day is still asked. My first version applied the exception to
     every work, and the loop's new probe showed that opened a way past the check.
2. **A street light is one spot, 20 m, not 50 m.**
   - At 5–15 m, too many repeats were lost (19–97% caught), because two GPS fixes of one house
     differ.
   - At 20 m, 93–98% of repeats are kept, and honest asks fall to 1.5–6.4%.
   - A neighbour's light gets no note either.
3. **Purchases are compared by kind of purchase, not as "goods".** Computers and then furniture for
   one school are two purchases. Computers bought again are still asked.

**Buildings keep the 50 m line.** With 2–4 building works per village placed at random large
buildings, 12–15% of honest ones were asked. This is an upper bound: Open Buildings counts house
clusters as large buildings too. Real halls' and schools' positions will show the true figure.

**Moving the pin to the next building** (an agency dodging the rule) is still caught 89–97% of the
time for lights and 95–96% for buildings and purchases. The repeat's first video then shows the
light or hall already standing (Site Progress).

### Site Progress: one loophole closed (`FIRST_FILMED_FINISHED`)

On Jaunpur's real dates, 532 of the 1,025 completed works were closed within the month of their
sanction. An honest agency films a first video and a final one, perhaps on the same day.

All 1,025 real timelines were run with honest videos (first and final, final only, both on one
day). Site Progress asked nothing on any of them. That showed the gap: with no first video,
`ALREADY_BUILT_AT_START` can never be asked. An old light or hall filmed once, as the "final"
video, passed as new.

The new question asks when there is no first video, and the first accepted video is the final one
or already shows the work complete or standing, for a work the form calls new. It sits at the
1-in-4 prior until read. Progress filmed in between, or a declared upgrade, is not asked.

### Time & Rules on every real work

It asks about 9,830 of the 40,935 works. 9,401 of those are `SANCTIONED_LATE`, the 75-day sanction
clock (owner's rule). That is a fact about the office's pace at 0.05, and it never queues a work
alone, as designed (T122). Nothing to change.

### Round 4 (6 Oct): village lanes and hand pumps

The real descriptions say where these works sit:
- **Lanes run from house to house.** 39% of the dashboard's roads and 45% of its paths name houses
  ("from X's house to Y's house").
- **Lanes are short.** Of the 1,364 real lengths stated, the median is 121 m and 40% are 100 m or
  less.
- **Roads come in same-day programmes**, often 2 to 8 lanes by one MP in a day.
- **A third of borewells are hand pumps "near X's house"**, at about Rs 70,000 each, filed in
  batches.

`data/trial/real_geo_roads.py` (results `results/real_geo_roads.txt`) runs each lane between two
real houses at a real stated length. The two layouts are random lanes, and the next street over at
a set gap a year later. Repeats re-file a lane 6–18 months later: re-pinned, 30–60 m longer, or
its inner 70%.

**Roads.** A road was "the same road" when both ends lay within 50 m of another's, or 80% of it lay
within 25 m of the other's line. Real lanes are short, so the next street over, one row of houses
away, has both ends within 50 m. The rule is now: both ends within 30 m AND on its line (80%
within 20 m). A road filed longer or as a part, whose ends are not both near, is still matched by
its line within 25 m.

| Honest filings | T139 rule: honest asked | Now: honest asked |
|---|---|---|
| the next street over, 25 m away | 81% | 28% |
| the next street over, 35 m away | 64% | 3% |
| the next street over, 50 m away | 11% | 1% |
| programmes of random lanes | 12% | 10% |

Repeats caught (re-pinned, longer, a part):
- the T139 rule: 100%, 97%, 100%;
- now: 99%, 94%, 98%.

Other trials:
- The tighter "on its line within 15 m" catches only 84–90% of repeats.
- At 15 m apart, the GPS cannot tell two streets from one (76% are still asked). Phone pins wander
  about that much.

**Hand pumps** take the street lights' rules: one spot (20 m), and one programme's pumps are never
repeats of each other. Honest pumps asked fall from 86% to 1%, and 98 of 100 repeats are still
asked.

### Proof

- **The loop:** 97 probes, 90 PASS, 0 FAIL, 7 LIMIT, and 3,000 random damages with 0 errors.
  - The 8 probes of the first rounds: the neighbour's light, one programme's lights, the light
    filed again, furniture after computers, computers again, the hall filed twice on one day, the
    old asset filmed only as final, and the light installed in a day.
  - Round 4's 4 probes: the next street over, a lane filed again re-pinned, a neighbour's hand
    pump, and a pump filed again.
  - Every earlier road probe still passes: a road re-filed longer, ends swapped, a real extension
    beside the old road, and splits by pin.
- **The engine suite:** 814 passed.
- **The examples:** the 12 work-form examples and five end-to-end filings raise exactly what they
  did. The honest filings now read "within 20 m" (lights) and "within 30 m" (roads).
- **The dashboard:** the 40,935 works are identical (`dashboard_t139_after`).

## T140 (6 Oct 2026): the T139 rules in six more districts

T139 fitted Duplicate Work's one-site rules to Jaunpur's villages. Jaunpur is one kind of place:
large villages on the Gangetic plain. `data/trial/real_geo_districts.py` (results
`results/real_geo_districts.txt`) runs the same scenarios in six districts that look different.
Each uses its own real works, real post offices and real buildings (Open Buildings, fetched once,
never committed):

| District | Kind of place | Houses apart (median) | Real works tested |
|---|---|---|---|
| Kheri | Terai plains | 7.7 m | 412 lights |
| Bokaro | plateau hamlets | 8.8 m | 372 lights |
| Puri | coast | 9.3 m | 281 lights |
| Howrah | dense, peri-urban | 8.6 m | 118 lights |
| Palakkad | dispersed homesteads | 11.2 m | 131 lights |
| Kheda | compact villages | 8.1 m | roads only |

**Each district's own flat map.** The scripts now take a district (`real_geo_check.configure`).
Each district gets its own flat-map origin: Jaunpur's, used everywhere, would be 8% off in metres
in Kerala. Jaunpur's results are unchanged.

| Scenario (7 districts) | Before T139: honest asked | Now: honest asked | Repeats caught now |
|---|---|---|---|
| lights, 10 a village, one hamlet | 63–87% | 0–1.5% | 93–97% |
| lights, 10 a village, anywhere | 1–37% | 0–5.3% | 86–94% |
| hand pumps at houses | 63–87% | 0–1.1% | 94–98% |
| the next street over, 25 m | 81–87% | 22–31% | 94–98% |
| the next street over, 35 m | 64–74% | 3–7% | 93–98% |
| programmes of random lanes | 5–20% | 4–18% | 95–99% |

**No rule changes:** the T139 rules hold in every district.
- **Lights: what the misses are.** "Anywhere in the village" is the cleanest measure of the 20 m
  line. There, 86–94% of repeats are caught. The misses are the one phone fix in ten that wanders
  15 m or more. In a hamlet the rate looks higher only because the neighbour's light sometimes
  catches the repeat too.
- **Random lanes: what the questions are.** The lanes still asked are almost all (85 of 95 in
  Jaunpur) one lane lying along another's line, often a short lane on a much longer road. Random
  straight lines make that by chance. On real streets, a lane laid on an existing road's line is
  that road again or its upgrade, which is the question to ask. So this row overstates the honest
  cost.

## T141 (6 Oct 2026): labour, trade by trade, only blatant irregularities

The owner: labour "depends on what the workers are and what they are doing"; give it its own
detailed field, then detect only blatant irregularities, never "it could be done with fewer
workers". Plan: [`docs/plans/T141-labour-schedule.md`](../plans/T141-labour-schedule.md).

**What changed:**
- **A labour schedule on the website form (PSWIF v1.1):** one row per trade (from a list, or Other
  with its grade), workers, days each, day rate, what they do, which BOQ lines they work on, and
  where the rate comes from. Each BOQ line says whether its rate already includes its workers.
- **Trades, not two kinds:** 14 trades in 4 grades (beldar, helper, chowkidar; mate; mason,
  carpenter, bar bender, painter, plumber, electrician, welder, driver; machine operator,
  supervisor), with Hindi names. A row is judged as its trade, never the grade it declares.
- **Two questions only:**
  - `LABOUR_RATE_FAR_ABOVE`: a trade's day rate is at least 2× what other agencies pay that
    trade in the district (2.5× its grade's pool when the trade has too few forms; the nearest
    grade with forms, with 1.25× room a grade step, when its own grade has none), and Rs 10,000+
    extra over the work;
  - `LABOUR_DAYS_BEYOND_WORK`: workers on site more than 10% beyond the work's own time.
- **Refused on the form:** person-days that are not workers × days, a labour row on a line whose
  rate already pays its workers (paid twice), a trade not on the list with no grade, a row with no
  trade. Never judged: how many workers, days within the work's time, labour's share.
- **The whole estimate:** a labour row within twice its trade's rate is settled (the agency's
  call). It adds nothing to the gap and stays out of the share's base. A blatant one is priced
  like any line.

**Planted filings** (`data/trial/labour_trial.py`, `results/labour_trial.txt`): three districts at
three wage levels; 8 agencies × 6 roads each give the district's rates; 150 honest filings a
district by new agencies (agency factor log-normal, sd 10%; 1 in 20 at +30%), each then padded one
way:

| Filing | Low wages | Mid (+15%) | High (+60%) | All |
|---|---|---|---|---|
| honest: any question | 0/150 | 0/150 | 0/150 | 0/450 |
| ten times the workers, honest rates: any question | 0/150 | 0/150 | 0/150 | 0/450 |
| one trade ×1.5 asked | 9/150 | 0/150 | 0/150 | 9/450 (2%) |
| one trade ×2 asked | 64/150 | 43/150 | 54/150 | 161/450 (36%) |
| one trade ×2.5 asked | 130/150 | 129/150 | 136/150 | 395/450 (88%) |
| one trade ×3 asked | 149/150 | 145/150 | 146/150 | 440/450 (98%) |
| helper declared "highly skilled" at an operator's rate | 125/150 | 150/150 | 130/150 | 405/450 (90%) |
| … at 1.25× an operator's rate | 150/150 | 150/150 | 150/150 | 450/450 |
| Other trade, "highly skilled", 2.2× an operator | 0/150 | 0/150 | 0/150 | 0/450 (a limit) |
| Other trade, "highly skilled", 3× an operator | 150/150 | 150/150 | 150/150 | 450/450 |
| a watchman on site 1.6× the work's time | 150/150 | 150/150 | 150/150 | 450/450 |

The 9 at ×1.5 (low district) are the 1-in-20 agencies already 30% above the market: ×1.5 takes
them past twice the district's rate.

**Why labour is settled in the whole estimate** (`--wages-in-whole`, the whole estimate judging
every wage like any line; `results/labour_trial_wages_in_whole.txt`): honest filings drew the
whole-estimate question 9, 3 and 3 times in 150, and ten times the workers at honest rates 15, 8
and 10 times. That is the "doesn't need this many" the owner ruled out: a large crew turns an
honest wage premium into most of the estimate. Settled: 0 and 0.

**The effect on the whole-estimate rule** (`data/trial/cost_whole_trial.py`, its synthetic CC
roads carry an unskilled and a skilled labour line; before = main's saved results):

| Fair rate from, honest spread | Honest asked before → now | Every line +20% asked before → now | +30% before → now |
|---|---|---|---|
| SoR, 5% | 0.0% → 0.0% | 97.1% → 94.0% | 100% → 100% |
| SoR, 10% | 0.2% → 1.2% | 86.5% → 80.2% | 99.4% → 98.2% |
| SoR, 15% | 2.8% → 6.0% | 74.6% → 70.3% | 97.1% → 93.1% |
| district, 5% | 0.0% → 0.0% | 95.9% → 91.1% | 100% → 100% |
| district, 10% | 0.1% → 1.2% | 94.2% → 87.0% | 100% → 99.3% |
| district, 15% | 3.6% → 8.0% | 82.2% → 74.3% | 98.9% → 96.3% |

The share is now of the materials' fair price alone, so the honest spread of fewer lines shows
more: honest asked stays within the 2% target at a 5–10% spread and rises at 15% (already over
the target before). The other choice, keeping settled labour in the base, would let an agency
dilute padded materials by adding a large honest crew, which is never judged. A confirmed cement
quantity ×1.5 alone now moves the whole as well (9.0–44.9% → 57.0–72.9%; with its own quantity
question it was and is asked 100%). The margins are the owner's to set on real forms (T098).

**The robustness loop** (`results/agent_robustness.txt`): 112 probes, PASS 102, FAIL 0, LIMIT 10
(was 97: 90 / 0 / 7); 400 random damages, 0 errors. New labour probes: a crew of 34 at honest rates
(quiet), masons at 2.2× (asked), a helper called highly skilled (judged as a helper), an invented
trade at 4× a mason (asked at the nearest grade with forms), the masons split into two rows with
one at 3× (asked), masons at 2.2× moved back among the BOQ lines (still judged as masons), a
labour row on a line that already pays its workers (refused), a watchman on site twice the work's
time (asked), trades left blank (never a clean chit), a district where every agency pays 1.6×
(quiet), masons filed by only 2 other agencies (honest quiet, 2.4× asked), an old v1.0 export with
labour among its BOQ lines in Hindi (judged by trade).

**Loopholes the loop found, and what closed them:**
1. A labour row giving workers and days but no person-days never reached the rate index or the
   whole estimate (the examples showed it): person-days are now worked out everywhere.
2. An "Other" trade declared at a grade nobody in the district files escaped every comparison: the
   nearest grade with forms stands in.
3. At 1.5× room a grade step, masons at 2.4× went unasked where only labourers had forms: now
   1.25× a step (honest skilled pay is about 1.75× unskilled; the trial's honest filings stay
   quiet).
4. A padded material written in a unit that does not fit it ("cement in nos"), its warning left
   unanswered, took the estimate under the coverage it needs, so the padding on every other line
   went unjudged. A held line now counts toward the coverage (it is out of the price check by the
   agency's own warning, not for want of data) while staying at its own value. Counting it as
   unreadable money instead turned an honest typo (cement at Rs 3,800 a bag) into a question, so
   that was not kept.
5. Labour wages counted in the whole estimate: see above.

**Limits (stated, not hidden):**
- a trade's rate up to twice what others pay it, and how many workers and days, are never asked
  (the owner);
- a trade not on the list is judged at its declared grade's pool (2.5×): Other "highly skilled"
  at 2.2× an operator is not asked;
- a composite schedule item declared "no labour", and a recognised material written in another
  unit with a reason given, look like honest schedule items until the state's Schedule of Rates is
  loaded with its item codes (T096).

**The demo filings:** a new one, "Masons at more than twice the district's wage" (masons Rs 1,800
a day where 8 other agencies pay Rs 750; its 34 workers are not questioned), asks
`LABOUR_RATE_FAR_ABOVE` only. The padded road now pads its materials 25% (its crews at the
district's wages); the end-to-end hall pads its materials 40%. Every other example raises what it
did before, with the same score.

## T143 (6 Oct 2026): the website on a phone, and faster to load

The owner: "make the website usable on phones as well, and also make them faster to load if you
can while keeping all the functionality". Measured with `scripts/dev/phone_audit.mjs`: each page
in Chromium as a phone (390 px, touch) with Lighthouse's mobile throttling (150 ms round trip,
1.6 Mbps down, CPU 4× slower), the median of three loads, on a production build. Before = main
(`results/phone_audit_before.txt`), after = this branch (`results/phone_audit_after.txt`).

| Page | Downloaded, KB | Largest paint (LCP), s | Boxes scrolling sideways (in the form) |
|---|---|---|---|
| Dashboard `/` | 828 → 482 | 5.87 → 4.00 | 0 → 0 |
| Review queue | 767 → 506 | 4.81 → 3.73 | 1 → 0 |
| All works | 723 → 478 | 5.35 → 4.46 | 1 → 0 |
| An example's page | 878 → 719 | 5.09 → 4.17 | 3 → 0 |
| Work intelligence form | 843 → 566 | 5.24 → 4.20 | 0 (4, and 4 texts cut off) → 0 (0) |
| Step by step | 901 → 667 | 1.20 → 1.09 | 0 → 0 |
| How it works | 784 → 506 | 5.21 → 4.46 | 0 → 0 |
| Form to risk score | 864 → 586 | 5.37 → 4.35 | 2 → 0 |
| Sign-in / landing | 791 → 720 | 5.61 → 1.35 | 0 → 0 |
| **Median of the pages** | **843 → 582** | **5.33 → 4.20** | |

**What made it lighter** (the same features, loaded when used):
- the sign-in code (Supabase) loads only when a sign-in cookie exists, or on signing in; a
  visitor never downloads it;
- the Hindi font is no longer preloaded on every page; one-word Hindi labels use the device's
  own Devanagari font;
- the charts (recharts), the 3D scenes (three.js) and the staff map load when their panel nears
  the screen, the 3D after the page is idle (the landing page shows the emblem
  picture meanwhile);
- smooth scrolling (Lenis, GSAP) loads only for a mouse; a phone scrolls natively;
- "Staff sign in" no longer prefetches the sign-in page.

**What made it fit:** works lists as cards on a phone (agents named, no hover needed); the form
map's sections as a compact list; estimate and labour rows as cards; the form's own tables as
labelled cards below 560 px; a one-line top bar and banner; section headers that wrap; the form
frame at its full height below the wide layout (one page scrolls, "Show in form" still lands on
the field); a dropdown for the 13 example filings.

**Still slow, and why:** every app page is drawn in the browser (the server sends a loading
screen), so its text waits for the scripts. Rendering pages on the server is the next step, a
bigger change. The example and Step-by-step pages show 217 KB of fonts in this audit only because
the test machine has no Devanagari font of its own; a phone uses its own.

## T144 (6 Oct 2026): the agents, more concrete: quantities held to the size for more works

The owner: "work even more on the agents. I need the agents to be fully concrete, working and
good at it".

**The audit.** The robustness loop's 10 LIMITs (112 probes) are of three kinds, none closable from
here without changing the owner's rules or adding data:
- margins the owner set: padding 14% under the 15% line; masons at 1.8× under 2×; split pieces at
  95% under the 96% rule;
- the owner's labour ruling: crews' days ×2.5 within the work's time (how many workers is never
  judged);
- data still to come: the state's Schedule of Rates (T096) for district-wide padding, composite
  items and units; real filed forms (T098); real site videos (T126). The rate book on branch
  `adityamore776/T096-up-sor` waits on a check by eye, per-circle rates and GST.

What could be made concrete now: the Cost agent held quantities to the work's size for only four
kinds of work (CC roads' cement and sand, solar lights by count, high masts, footpaths).

**What changed** (`cost_form/norms.py`, `materials.py`, `validate.py`; whole estimate `whole.py`):
- **A CC road's stone** by its concrete mix (IS 456 nominal mix: 0.84 m³ of dry stone per m³ of
  M20), with 15% room for the analysis-of-rates figures (0.85–0.90) and wastage.
- **A water pipeline's pipes:** with the house connections' pipes on lines of their own (32 mm or
  less, or named for connections), the main alone is held to the pipeline's length + 10%; with
  every pipe on one line, the length + 20 m a connection + 10%. A tank's connecting pipe + 10%.
- **Solar lights bought by the watt or watt-hour:** panels at each light's Wp × the lights,
  batteries at each light's Wh, + 5%. Count lines are still held to the count.
- **Stone named for a base course is the base:** "40 mm aggregate for WBM", "Aggregate for GSB",
  "ballast for base course" were read as concrete's aggregate (and priced as it).
- **A road over a new stone base must itemise its stone:** with no base line and a stone line
  sized for neither the slab (6–20 mm, "concrete", "PCC") nor the base (40 mm and up), the form
  asks for the base on a line of its own before the estimate is judged. The loop found the reason:
  one unsized stone line hid twice the slab's stone.
- The whole estimate counts the same lines as the quantity check (one function, `norms.held`).

**Planted filings** (`data/trial/quantity_trial.py`, `results/quantity_trial.txt`): 200 a cell,
through the website form, the adapter, the form check and the Cost agent, the agency confirming
whatever the form asks (the worst case for a false question):

| Filing | Asked by the Cost agent |
|---|---|
| honest roads (base on a WBM line, as "aggregate for WBM", as "63 mm", none) | 0/800 |
| honest roads, all stone on one unsized line | 0/200 (the form asks to itemise: not judged) |
| road stone ×1.25 | 0/400 (the form asks the agency to confirm, 400/400) |
| road stone ×1.5, ×2 | 400/400, 400/400 |
| honest pipelines (itemised; one line) | 0/200, 0/200 |
| pipes ×1.5, ×2, itemised | 200/200, 200/200 |
| pipes ×1.5, ×2, all on one line | 69/200 (34.5%), 158/200 (79.0%) |
| honest solar lights by Wp, by Wh | 0/200, 0/200 |
| panels or batteries ×1.5, ×2 by capacity | 200/200 each |

The honest ranges are assumptions (0.84–0.92 m³ of stone per m³; 6–15 m a house connection);
real filings (T098) will show the real spread.

**Effects elsewhere:** two example filings (a road "complete" 6 days after sanction; a road filmed
2.4 km away) had their whole estimate "not judged" (43% of the money priced); their stone now has
a known need, so they are judged fair (62–63% priced). Labour and whole-estimate trials:
unchanged.

**The robustness loop** (`results/agent_robustness.txt`): 118 probes, PASS 108, FAIL 0, LIMIT 10;
400 random damages, 0 errors. New probes: the road's stone alone doubled (asked), the base's stone
written "Stone aggregate 63 mm for WBM" (quiet), all stone on one line (the form asks to
itemise), the slab's stone doubled inside one unsized line (the form refuses it until itemised),
solar panels by the watt at the lights' own Wp (quiet) and at twice (asked).

**A harness flaw, fixed:** when padding took the estimate more than 10% over the MP's amount, the
form refused the planted filing for its missing reason, so "padding 14%: just under the 15% line"
and "18% GST in other charges" never reached the price check. The planted agency now cites the
MP's consent, as a padder would. Both results stand, now for the right reason: 14% padding is
judged and quiet (under the 15% line); the GST line is judged and quiet.

## T145 (6 Oct 2026): what a quantity or a price should be is a range

The owner: the cost "size prediction" or "price prediction" "should give a range and not just
'should be quantity 1334'". Every figure the Cost agent gives for what a line should be is now a
range, from the same data as before (no rule or margin changed):
- **a quantity** (`norms.py`): from the standard amount for the size (the mix, the area, the
  count) to the same with the room honest estimates carry (wastage, the stone's analysis-of-rates
  room, a pipe's house connections at 6 to 20 m each);
- **a rate** (`rates.py`): from the lowest to the highest of the other agencies' own median rates
  here (the fair rate stays their median); a state-wide rate carries its 10% leeway on both ends;
  a schedule's rate is its own range;
- **the whole estimate's fair price** (`whole.py`): every priced line at those lowest and those
  highest rates;
- **a labour day rate** (`labour.py`): what other agencies pay that trade, lowest to highest;
- **a price per light or per metre**: the middle 8 in 10 of the similar works (10th to 90th
  percentile).

What the officer now reads, from the rebuilt examples (`apps/web/public/work-form/examples.json`,
`end-to-end/examples.json`): "Cement: 2,614 bags in the estimate, but the work's size takes
1,270–1,334 bags"; "a fair price for this work here: ₹15.13 L at the usual rates, ₹14.90 L–₹15.57 L
from the lowest to the highest rates other agencies charge"; "Mason at ₹1,800 a day: 2.4× the ₹750
others here pay this trade (₹735–₹780)". Jaunpur's 136 real solar lights cost ₹20,878–₹20,896 a
light (8 in 10): one price nearly everywhere, so that range is narrow by the data, not by the code.

**Unchanged:** every example raises the same findings; `quantity_trial.py`, `labour_trial.py`,
`cost_whole_trial.py` and the robustness loop (118 probes, PASS 108, FAIL 0, LIMIT 10) print the
same results. What is asked is still decided by the upper end and the owner's margins.

## T146 (7 Oct 2026): a vision model for real construction progress, measured on synthetic sites

The owner asked for a pipeline of construction site videos, a tuned dataset with augmentation, and an existing vision
model fine-tuned to see actual progress. The plan, with each of the owner's notes judged, is
`docs/plans/T146-site-progress-vision.md`; the code is `apps/vision/`. No real video could be fetched here: this
machine's network refuses YouTube, Wikimedia, Hugging Face and Kaggle, and it has no GPU. So everything was measured on
**synthetic timelapses whose truth is exact** (`data/trial/vision_synth_trial.py`,
`results/vision_synth_trial.txt`):
- 30 sites, 60 frames each, five kinds (masonry, concrete frame, wood, steel, road);
- people, trucks, scaffolding, stacks, machines, a sweeping shadow, changing light, camera shake, a date stamp;
- covered work (plaster over brick) and buried work (earth over footings).

These numbers check the pipeline and its measures. **They say nothing about accuracy on real sites** (T147, T148).

**The hindsight teacher against the truth** (progress = change that never goes back; 1,860 random pairs):

| | precision | recall | IoU | pairs labelled | pairs right |
|---|---|---|---|---|---|
| auto thresholds + stage marks | 0.913 | 0.957 | 0.877 | 96.1% | 97.5% |
| auto thresholds, no marks | 0.913 | 0.957 | 0.877 | 92.3% | 93.9% |
| fixed lo = 0.10 / 0.15 / 0.20 / 0.25 | 0.819 / 0.898 / 0.940 / 0.962 | 0.990 / 0.977 / 0.952 / 0.910 | 0.812 / 0.879 / 0.897 / 0.879 | 90.7–93.0% | 92.7–94.8% |

- By kind, pairs right: 96.2% (wood) to 98.3% (road); road's patch recall is the lowest (0.841).
- The thresholds from each shot's own noise (lo 0.127 to 0.282) come within 0.02 IoU of the best fixed value.
- **Buried work:** 16.9% of buried patches are called progress; the rest read "nothing changed", as no picture can
  show a footing under earth. With stage marks those pairs are labelled right; this is why the marks exist.

**Masks and splits:**
- date stamps and logos found with IoU 0.785 on average (lowest 0.633);
- 97.4% of patches with people or passing trucks masked, and 12.3% of other patches (around new work);
- 100% of frames aligned;
- a re-upload of a site (filmed at other moments) joined its original's site; no site or channel in two splits.

**The student** (frozen hand-made features + the trained head, on CPU; DINOv2 needs the GPU), against the truth, on
sites it never saw:

| Fold | AUROC | train − test | patch IoU | light | staged | both ways | build-up τ |
|---|---|---|---|---|---|---|---|
| in-type | 0.960 | +0.018 | 0.454 | 0.006 | 0.070 | 0.003 | 0.312 |
| in-type, no augmentation | 0.968 | +0.017 | 0.530 | 0.101 | 0.218 | 0.075 | 0.342 |
| held out: masonry | 0.976 | −0.007 | 0.532 | 0.007 | 0.019 | 0.005 | 0.160 |
| held out: concrete frame | 0.965 | +0.009 | 0.522 | 0.034 | 0.078 | 0.006 | 0.146 |
| held out: wood | 0.947 | +0.023 | 0.496 | 0.000 | 0.000 | 0.000 | 0.227 |
| held out: steel | 0.939 | +0.035 | 0.491 | 0.033 | 0.085 | 0.036 | 0.313 |
| held out: road | 0.918 | +0.062 | 0.222 | 0.012 | 0.098 | 0.015 | 0.020 |

Column meanings:
- **light:** pairs only minutes apart with no work, called progress;
- **staged:** no-work pairs with people, machines, scaffolds and stacks pasted in, called progress;
- **both ways:** progress pairs also called progress when the frames are swapped.

What this shows:
- **Augmentation buys robustness, not score.** Without it AUROC is about the same (0.968 against 0.960). But light is
  called progress 10.1% of the time (0.6% with it), a dressed-up site 21.8% (7.0%), and swapped pairs 7.5% (0.3%).
  The model without augmentation had learned "different", not "added".
- **The "wooden houses only" worry, measured.** Trained without a kind, the model still scores 0.92–0.98 on it. The
  most different kind, roads, is the hardest: AUROC 0.918, the largest train-test gap (+0.062), a weak map (IoU 0.222).
  Real data needs enough roads and drains of its own.
- **Not memorising:** the train-test gaps are −0.007 to +0.062.
- **Targets missed, said plainly:**
  - the build-up score orders frames poorly (τ 0.02–0.34, target 0.8);
  - the dressed-up audit is 7.0% in-type (target 2%).
  Both are for the GPU run on DINOv2 features to answer (T148), with more ordering epochs.

**Fixed along the way:**
- **Alignment:** keypoints bunched on the changing brickwork, so 20–60% of frames of some sites aligned. Spreading
  them over a grid and fitting a shift, rotation and zoom aligned 100%, with errors under 1 px.
- **Overlay mask:** it took the shadow's flicker at the foot of the building for a date stamp (twice the true area). A
  flickering box must now hug the frame's edge.
- **Moving-things mask:** it flagged a whole sweeping shadow (26% of pixels). It now compares fine detail and colour,
  which a shadow does not change, and drops huge blobs.
- **Training:** the hand-made features of all patches pointed almost the same way (differences about 1% of their
  length), so the head learned nothing (AUROC 0.48). The fixes:
  - centre each image's features;
  - give B's patches their difference from A's;
  - lean the yes / no on the map;
  - weigh rare progress patches up to 10 times.

## T151–T153 (8 Oct 2026): real Indian stage photos for the claim judge, and what the eye found

Plan: `docs/plans/T150-vlm-progress-dataset.md`. Code: `apps/vision/drishti_vision/` (`geomgnrega.py`, `change.py`,
`vlmdata.py`, `eyecheck.py`). Counts: `data/trial/vlm_trial.py` → `results/vlm_trial.txt`. Photos and records stay on
the owner's D: drive, never in git.

**The source (T151).**
- GeoMGNREGA photographs every MGNREGA asset at three stages: 1 before, 2 during, 3 after, two photos each. It is
  public on ISRO's Bhuvan map. Bulk export is off (WFS disabled; compressed photo copies answer 403), so only the
  requests a person's click makes are used, at one every 1.5 s: about 50 assets an hour.
- 130 assets read so far: all 130 have all three stages.
- The work types are MPLADS-like: interlocking, brick, CC and earth roads; Anganwadi and Panchayat buildings;
  sanitary complexes; school toilet blocks; compound walls; ponds and trenches.

**What looking at the photos changed (T153), each now a rule in code and a test:**

| Found by eye | Rule now |
|---|---|
| A grove's "after" photo differed from its "before" only by season (dry leaves vs green growth), yet passed a "the photos changed a lot" check | "Progress" items only for unmistakable built structures (an allowlist of sub-categories); no ponds, earth or gravel roads, bunds, trenches, playfields or repairs |
| One "before" photo already showed a (different, older) building | Progress also needs the before → after change to beat the asset's own same-moment noise, and to pass a floor (DINOv2 distance 0.25; the margins were set by eye on 12 pilot assets) |
| A pond's two "before" photos were taken from very different spots (a dry pit close-up vs a wide view with water): "nothing was added between them" could not be read from the photos | Same-moment pairs count only when the two photos show the same scene (distance ≤ 0.10; 78–85% of pairs) |
| "Is it finished?" on a grove's before photo cannot be decided from pixels (a finished trench may look the same) | Such claims only for structures that would be unmistakable once built |
| A green plot next to a green grove could pass for one place | The "different place" photo is always a finished structure of another work type |
| The portal writes "CmpOnd wall"; "pond" matched inside it | Word-start matching; a compound wall is a wall |

**The items (`vlm_trial.txt`):**
- 130 assets, of which 86 pass the progress certainty rule.
- **Train:** 1,063 items (633 real and unedited) from 5 districts.
- **Test:** 55 items, **all real and unedited**, from 1 district never used in training.
- Edited items (people pasted in, light, dark, blocked) are training-only. They are capped at 20% when training, and
  every edit also goes into a real progress pair labelled "shown".

**Every test label was looked at** (contact sheets, `eyecheck.py`; by the agent, a person to follow). The rules
above came from that look; after them, no label on the 6 test sheets was wrong.

**The untrained Qwen3-VL-4B (4-bit) on the 55 real test items:**

| | Result |
|---|---|
| Accuracy | 76% |
| Macro-F1 | 0.54 |
| Fooled | 2 of 38 no-progress pairs |
| Missed | 1 of 8 progress pairs |
| Time | 3.6 s a check, about ₹2 per 1,000 checks on the owner's PC |

Two things it shows:
- **It never says "can't tell" for a different place:** 0 of 9; it says "not shown".
- **It is fooled only when the two photos look clearly different:** 2 of 19 such pairs, against 0 of 19 nearly
  identical pairs.

The second is the shortcut the owner warned of: "different photos" standing in for "progress". It is why:
- training crops, turns and re-saves each photo on its own;
- the scores are split by how different the photos look;
- the timelapses' busy and light pairs (real photos, taken at different times, with nothing built between them) are
  being added.

These are early numbers on one test district; the final ones come with the full harvest (T152) and the trained
models (T154).

### T153–T154 (8 Oct 2026, later): the timelapse labels, checked by eye

The v3 build added 488 items from 180 CC BY timelapses. Every test label was looked at, larger than on the sheets
(two 640 px frames side by side). What the eye found:

| Found by eye | Count | Rule now (each with a test) |
|---|---|---|
| Every timelapse photo had red and blue swapped (orange skies): frames are kept RGB, OpenCV writes BGR | all 488 | Frames flipped before saving |
| **Wrong labels on the first look: 20 of 63 test pairs (32%)**: something permanent may have been added in a "nothing built" pair (paving stones, a bridge girder set in place, siding, a water tank, rooftop units) 7; two camera views, a dissolve or two rooms 6; title or advert cards 4; "work added" with no clear new structure 3 | 20 of 63 | The rows below, and the rest dropped by eye |
| The teacher could judge only about half the view (moving workers): "no lasting change found" meant little | the paving-stone pairs | A no-progress pair needs ≥ 80% of the view judged, and may not span a stretch where the same shot shows work |
| Hand-held clips, cuts and dissolves (frames 3–5 apart already differ, `lo` 0.5–1.3): the teacher calls almost everything unchanged and found **no** progress in any such test shot | 18 of 43 test shots | Shots with noise `lo` > 0.4 give no items. Below it, the wrong pairs left were title and advert cards and a few possible installs (the girder among them), all dropped by eye |
| The same pair twice | 2 | Each pair of frames used once |
| After the rules, a second look at the 31 test pairs they newly picked | 9 of 31 wrong | Dropped by eye: title or advert cards 4, possible installs 2, "work added" with no clear new structure 3 |

**The timelapse "work added" labels are mostly wrong.** Of 41 such items across all splits, **1** shows clear new
permanent structure (bridge girders placed across a river). The other 40 are season and snow changes on a webcam
(19), advert or end cards (3), a talking head, drone parallax, a load still hanging from a crane, timber formwork,
painting a fence, draining a pool, and webcam pairs with no visible new structure. The hindsight teacher
(`hindsight.py`) counts any change that never returns as progress, and snow, a new season or a caption never
returns within a shot. **This also bears on T146 (PR #120):** its DINOv2 student learnt from these same progress
labels. Only the eye-confirmed one is kept here. The swapped versions stay ("B is earlier": not shown either way).

**The government stage photos held up.** All 172 test items from GeoMGNREGA were right on the sheets. Two needed a
full-size look: a CC road whose slab and joints are clear at full size, and a road photographed from a new angle,
where the same teal house appears in both photos.

**The dataset trained on (v4, `items_eye.jsonl`):**
- **Train:** 2,642 items, 1,641 of them real and unedited.
- **Calibration:** 155 items, all real.
- **Test:** 205 items, **all real and every label checked by eye.**
  - 16 progress, 141 no progress, 48 different place;
  - government photos come from only 4 districts (Azamgarh, Sagar, Nagaur, Purulia), so the harvest now visits
    those first, then 11 new districts.

Counts: `data/trial/results/vlm_trial.txt`. Checks: `D:\nidhinetra-data\vlm\eye_checks.jsonl`, one line a review,
keyed by photo pair (`eyecheck.key`), so they survive rebuilds.

### T154 (8 Oct 2026): first fine-tuned judge, and the shortcut it learnt

Trained on Modal (A100-40GB, the owner's credit): LoRA rank 16, 2 passes, 2,051 training items (410 edited), about
32 minutes and about $1.2 a run. Scored on the 205 eye-checked real test items (v4):

| Judge | Macro-F1 [95% CI] | Fooled (no-progress called "shown") | Missed progress | Accuracy |
|---|---|---|---|---|
| Qwen3-VL-2B, untrained (owner's PC) | 0.39 | 19 of 141 (13.5%) | 3 of 16 | 64% |
| Qwen3-VL-4B, untrained | 0.44 [0.31, 0.51] | 2 of 141 (1.4%) | 5 of 16 | 37% |
| **4B fine-tuned** | **0.99** [0.93, 1.00] | **1 of 141 (0.7%)** | **0 of 16** | **99.5%** |
| 4B fine-tuned, real photos only (no edited items) | 0.98 | 1 of 141 | 1 of 16 | 99.0% |

The untrained 4B is rarely fooled because it rarely commits: it answered "can't tell" to 102 of the 141 no-progress
pairs. The tuned 4B's one miss is an honest hard case: a CC road's two before photos taken from two spots, one
showing an older paved stretch.

**The near-perfect score hid a shortcut.** In v4 the "different place" photo was always a finished work of
**another type** (the owner's rule, so that "different" was unmistakable). So a probe was built: photo B is a
finished work of the **same** type somewhere else in the same held-out district (another block), checked by eye
(44 of 58 pairs kept):

| Judge | Correct "can't tell" on 44 same-type other places |
|---|---|
| 4B untrained | **39 (89%)** |
| 4B fine-tuned | **2 (5%)**: it called another finished road "shown" 38 times |
| 4B fine-tuned on real photos only | 12 (27%) |

The tuning had taught "different place = different kind of work". An agency could pass the tuned judge by
photographing someone else's finished road. **Fix (now in `vlmdata.py`, with tests):** every training asset also
gets a same-type, other-block pair labelled "can't tell" (`other_site_same`). The probe stays as its own report.
The edited items made the shortcut worse (5% against 27%), which is the first hint for the owner's keep-or-drop
rule on edits.

**More test labels by eye (v5/v6).** The harvest reached 717 assets. The 193 new test assets were checked as **asset
cards** (all 6 stage photos and the other-place photo in one row), 967 labels in all:
- **82 wrong.** The worst group: 7 of 7 "Roof top rain water harvesting structure in gov/panchayat building"
  assets. "Panchayat" made them buildings, and their before photo always shows the building the pit sits beside.
  Now a rule (type "other", never progress), with a test.
- The rest were dropped by eye:
  - a before photo already showing an older paved road, or a toilet block standing;
  - after photos showing a field, a gate or a different spot;
  - 3 other-place pairs where the two could be one place.

**v6 (`items_eye.jsonl`), the set being trained now:**
- **Train:** 4,663 items, 563 assets, 53 districts (2,924 real).
- **Test:** 915 items from 203 assets in 15 held-out districts, **every label checked by eye**: 145 progress,
  580 no progress, 190 different place.
- **Probe:** 93 same-type other-place pairs, checked by eye.

### T154 (8 Oct 2026, later): v6 results (915 real test items, every label checked by eye)

LoRA rank 16, 2 passes, on Modal (A100 for training, L4 for scoring). Output: `data/trial/results/vlm_trial.txt`.

| Judge | Macro-F1 [95% CI] | Fooled (of 580 no-progress) | Missed progress (of 145) | Same-type probe right (of 93) |
|---|---|---|---|---|
| Qwen3-VL-2B untrained | 0.46 [0.43, 0.50] | 56 (9.7%) | 55 (38%) | not run |
| Qwen3-VL-4B untrained | 0.47 [0.43, 0.51] | 7 (1.2%), answers only 34% of the time | 84 (58%) | 62 (67%) |
| 2B tuned | 0.92 [0.90, 0.94] | 15 (2.6%) | 22 (15%) | 74 (80%) |
| 4B tuned (with edited photos) | 0.925 [0.91, 0.95] | 11 (1.9%) [0.8, 3.1] | 26 (18%) | 83 (89%) |
| **4B tuned, real photos only** | **0.92 [0.90, 0.94]** | **5 (0.9%) [0.2, 1.7]** | 32 (22%) | **86 (92%)** |

McNemar tests:
- every tuned model against its untrained base: p < 10⁻⁵⁰;
- with edits against real only: 13 against 11 items, p = 0.84 on the test, and p = 0.55 on the probe;
- 2B tuned against 4B tuned: p = 0.32.

What follows:
- **The edited photos are dropped (the owner's rule).** The real-only model is not worse: it ties overall, is fooled
  less, and passes the probe more often.
- **The same-type shortcut is mostly fixed** (89–92% on the probe, from 5% before). The pairs left are all "an empty
  plot, then a close-up of a finished building elsewhere". Real progress pairs for buildings look exactly like that, so
  photos alone cannot separate them: the photo's GPS tag, or a landmark seen in both, must.
- **Track B is in reach:** on the test, the tuned 2B is level with the tuned 4B. It is weaker on the probe (80%).
- **Weak spots left (the reinforcement stage's targets):**
  - real progress answered "can't tell" (17–23 of 145);
  - photos in reverse order (72–81% right).

### T155 (8 Oct 2026): against the flagship, at each model's best (owner's rules)

**The owner's rules for the comparison** (8 Oct 2026):
- **Real data only.** Every compared item is a real construction-site photo pair: GeoMGNREGA stage photos of
  MGNREGA works, plus real site timelapse frames. Nothing is edited or rendered, and every label was checked by eye
  (test 915, calibration 124 after the eye check).
- **The same question and the same photos for both models.** No model has seen the test before: 0 test districts,
  0 sites and 0 identical photo files are shared with training (checked by file hash over all 1,008 test and probe
  items).
- **Each model at its maximum, never weakened to match the other:**
  - Gemini gets full-resolution photos, its own thinking, temperature 0, and the choice of 4 worked examples (from
    training districts only);
  - ours may also run at 1,024 px.
  - Each model's setting is chosen on the calibration split, not the test.
- **Cost counts as much as accuracy:** a ton of checks will be run. Each judge's cost a check is measured:
  - Gemini: its billed tokens, thinking included, × Google's published price (ai.google.dev/gemini-api/docs/pricing,
    read 8 Oct 2026: 3.1 Pro $2 / $12 per million tokens in / out; 3.8 Flash $0.75 / $3.75), and the Batch API at
    half price for bulk;
  - ours: measured GPU seconds × Modal's published L4 price ($0.000222 a second).

**The key** is a Modal Secret, which the owner typed into Modal's website. Code reads it only inside Modal
containers; it never touches the PC or the repo.

**Calibration (92 items shared by all judges, labels checked by eye; only 11 progress pairs, so it only picks
settings):**

| Judge | Macro-F1 | Fooled (of 60) | Missed (of 11) | $ per 1,000 checks |
|---|---|---|---|---|
| Our 4B, 512 px | 0.84 | 1 | 4 | 0.18 |
| **Our 4B, 1,024 px** (chosen) | 0.86 | 1 | 4 | 0.39 |
| **Our 2B, 512 px** (chosen) | 0.87 | 1 | 3 | 0.12 |
| **Gemini 3.1 Pro** (chosen) | 0.73 | 0 | 8 | 9.56 |
| Gemini 3.1 Pro + 4 worked examples | 0.68 | 0 | 9 | 28.62 |
| Gemini 3.8 Flash | 0.66 | 0 | 10 | 2.80 |

Gemini is never fooled here, but it rarely confirms real work: it calls most real progress "not shown" or "can't
tell". The worked examples made it worse and cost 3× more.

**Daily cap:** Gemini 3.1 Pro stopped after 250 requests in a day on the owner's tier (Google: "You exceeded your
current quota"). The 915-item test therefore goes through the Batch API: the same requests, as one file, at half
price, with no daily request cap.

The eye check of calibration also found wrong labels:
- 6 sites (a before photo already showing the building; after photos showing only an earth track, grass or a wall);
- 14 of 33 timelapse pairs (a talking head, title cards, a theatre stage, garden fence work).

**THE RESULT: the 915 real test items, every label checked by eye** (`results/vlm_compare_test.txt`). Gemini 3.1 Pro is
Google's top model, at its best setting (full-resolution photos, its own thinking), sent through the Batch API:

| Judge | Macro-F1 [95% CI] | Fooled (of 580) | Missed progress (of 145) | $ per 1,000 checks |
|---|---|---|---|---|
| **Our 4B** (512 px) | **0.918** [0.896, 0.939] | 5 (0.9%) | 32 (22%) | **0.17** |
| Our 4B, 1,024 px | 0.917 [0.891, 0.941] | 6 | 33 | 0.38 |
| **Our 2B** | **0.912** [0.889, 0.934] | 15 (2.6%) | **23 (16%)** | **0.12** |
| Gemini 3.1 Pro | 0.689 [0.647, 0.735] | **2 (0.3%)** | 109 (75%) | 5.18 batch; about 10.4 live |
| Qwen3-VL-4B untrained | 0.471 [0.428, 0.512] | 7 | 84 | n/a |

Costs:
- ours: measured L4 seconds × Modal's price;
- Gemini: its billed tokens, thinking included, × Google's price (the Batch API is half the live price).

McNemar against Gemini, our 4B: our 4B is right on 117 items Gemini gets wrong, and wrong on 6 it gets right
(p = 8×10⁻²⁸). Our 2B: 122 against 19 (p = 1×10⁻¹⁹).

**Same-type probe** (`results/vlm_compare_probe.txt`): Gemini 3.1 Pro 93 of 93, our 4B 86 of 93 (p = 0.016 against
Gemini), our 2B 74 of 93.

**Against plan §7.4:**
- **Track B (same accuracy at a fraction of the cost): achieved, and passed.** Our models are more accurate than
  Google's top model:
  - macro-F1 +0.23;
  - it misses 75% of real progress, ours 16–22%;
  - one check costs 1/30 (4B) to 1/44 (2B) of Gemini's bulk price, and 1/60 to 1/88 of its live price. The plan's
    "1/100" is not quite reached against the bulk price.
- **Track A (fooled at most half as often as the best flagship): NOT claimed.**
  - Gemini is fooled less often (2 against 5 of 580) and passes the same-type probe (93 against 86 of 93).
  - It gets there by rarely confirming any work: it answers "can't tell" or "not shown" for 109 of 145 real,
    finished works. As a checker, that would send most honest agencies to an inspection.
  - The stop rule applies: this is reported as it is.
- **Where our model still loses:** an empty plot, then a close-up of a finished building elsewhere (the probe). The
  photo's GPS tag or a shared landmark is the remedy, not more of the same photos.

**Spend:**
- Google, about $11 (₹942 on the owner's cap): live calibration calls about $5.04 and the batches about $6. Then the
  account was blocked for billing (fixed by the owner with ₹800 of prepaid credit).
- After that, one test call for ₹0.0009, logged in `D:\nidhinetra-data` and on the volume
  (`/data/budget/gemini_inr.json`, ceiling ₹800, stop at ₹700; every paid call is priced at its worst case before it
  is sent).
- Of the Gemini 3.8 Flash test batch, 600 of 915 requests failed (unbilled) after the block. Flash is not re-run.

**Speed:** scoring answered one pair at a time with the adapter kept separate: 7.5 s a check on an L4, the GPU about 39%
busy. Folding the adapter into the weights and answering 8 pairs at once gives 0.84 s a check, with the same verdict
and the same confidence on all 48 items compared.

## Bugs and data problems found along the way

1. **The live map painted the wrong districts.**
   - Works carry Census-2011 district codes, even though the field is called `district_lgd`.
     The map outlines carry the real LGD codes.
   - Joined by number, Pratapgarh's works were drawn on Pilibhit, Kupwara's on Anantnag, and
     so on.
   - **Fixed and live (26 Sep 2026):** `data/district_crosswalk.py` matches all 752 districts
     by state and name, and the map joins on the new `code`. Checked on the live site:
     Pratapgarh (UP) now carries its own works.
2. **Personal data in public records.**
   - Some descriptions contain private phone numbers.
   - Certificates carry vendors' bank account numbers.
   - DRISHTI must mask both and never display them. The trial results store no account
     numbers.
3. **Portal cycles look like behaviour.** Completion months and impossible dates both follow
   the portal's calendar. Always compare with the same period nationally.
4. **The same form, several versions.** The older Utilisation Certificate has no sanction-date
   line, so the reader must use whichever version it finds.

---

## What to build next, in order

1. **Document + Contractor agents for portal-generated certificates.** Free, local and measured
   above. This gives real sanction dates (the 75-day check), payment dates (which fixes the
   fund-flow gap) and contractors.
2. **Port Eligibility v2 into the engine** with its tests, and raise its weight from note to
   finding.
3. **Split / bulk-order detector and "same asset funded twice" detector,** then matching by
   meaning for reworded repeats.
4. **Photo reuse:** exact copy + 256-bit fingerprint + feature matching.
5. **Geo:** stamp reader, district check, PIN check and time check.
6. **Delay:** office track records and stuck works. Present the model only as a ranking aid.
7. **Fund flow:** the sanction backlog, and recommendations left behind when a Lok Sabha term
   ends.
8. **AI key (paid, capped)** for Hindi and handwritten papers, site progress and plaques. This
   is the one switch that is the user's decision.
