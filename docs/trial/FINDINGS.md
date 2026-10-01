# DRISHTI agents on real works: what works, what doesn't

**Trial run 25–26 September 2026.** All figures come from the scripts in `data/trial/`, and
their outputs are in `data/trial/results/`. Every example quoted here was checked by eye
before it was written down. "Needs checking" never means wrongdoing. It means an officer
should look.

---

## The short version

| Agent | Verdict | One line |
|---|---|---|
| A3 Cost *(built)* | **Works, for big mark-ups** | Catches 63% of works inflated 5× and 84% at 10×, while flagging 1.5% of normal works. Mark-ups under 2× need a second signal. |
| A2 Split works | **Works** | Real pattern: 12× more works just under ₹5 lakh than just over. Found same-day splits and bulk orders kept under the limit. |
| A2 Duplicates | **Partly** | 48 cases of one named site recommended again while the first was still open; about 19 of them look like one asset funded twice. Exact wording finds nothing once the first work is complete, so real repeats are reworded. Matching by meaning is not built yet. |
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
