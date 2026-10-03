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
