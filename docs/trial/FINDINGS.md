# DRISHTI agents on real works: what works, what doesn't

**Trial run 25–26 September 2026.** All figures come from the scripts in `data/trial/`, and
their outputs are in `data/trial/results/`. Every example quoted here was checked by eye
before it was written down. "Needs checking" never means wrongdoing. It means an officer
should look.

---

## The short version

| Agent | Verdict | One line |
|---|---|---|
| A3 Cost *(built)* | **Works, for big mark-ups** | Catches 63% of works inflated 5× and 84% at 10×, while flagging 1.5% of normal works. The Isolation Forest rivals use catches 3% and 5% at the same false-alarm rate (18% and 47% in its best version). Mark-ups under 2× need a second signal. |
| A2 Split works | **Works** | Real pattern: 12× more works just under ₹5 lakh than just over. Found same-day splits and bulk orders kept under the limit. |
| A2 Duplicates | **Partly** | 48 cases of one named site recommended again while the first was still open; about 19 of them look like one asset funded twice. Exact wording finds nothing once the first work is complete, so real repeats are reworded. Matching by meaning is not built yet. |
| A1 Eligibility | **Works after a rewrite** | On a fresh sample, 56% of what it flags plainly reads as prohibited, and 80% is worth an officer's look. The keyword search rivals use: 5% and 18%, while flagging 46× more works. |
| C1 Delay prediction | **Weak** | Scores 0.71 on a 0.5–1.0 scale, against 0.68 for simply using the office's past record. Better sold as office track records. 7 in 10 works miss the one-year target anyway. |
| C2 Fund flow | **Facts work; forecasts can't be tested** | 21,323 works (₹1,361 cr) are still waiting for sanction past 75 days. A "year-end rush" signal turned out to be a portal cycle and was dropped. |
| B4 Document | **Works on typed certificates, free** | Local text reading (no AI service) reads the sanction date, payments and contractor off 431 Uttar Pradesh certificates. It shows 16% of works were sanctioned after the 75-day limit, and that the paper for 282 of 285 "completed" works still says "in progress". About half of other states' papers (Hindi, handwritten) need AI reading. |
| C3 Contractor | **Works where certificates exist** | The vendor code is an exact identity. In Pratapgarh, 3 vendors hold 84% of the 261 works we could read. |
| B2 Photo reuse | **Works** | Recognises 99.9% of edited copies (crops, stamps, screenshots); the rival fingerprint gets 56%. The pilot has no disguised copies, but 5 exact files sit on different works, and 2 of those need checking. |
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
- Run Isolation Forest (the method several rival projects use) at **the same false-alarm rate**.

| Mark-up | DRISHTI cost agent | Isolation Forest (type + state + amount) | Isolation Forest (amount only) |
|---|---|---|---|
| 1.5× | 0.4% | 1.4% | 1.8% |
| 2× | 18% | 1.9% | 2.0% |
| 3× | 39% | 2.0% | 5.9% |
| 5× | **63%** | 2.8% | 18% |
| 10× | **84%** | 5.1% | 47% |
| False alarms | 1.5% | 1.5% | 1.5% |

**On its own**, the price finding puts only 0.11% of normal works in the review queue, and
it catches 18% of 5× mark-ups and 36% of 10×. That is deliberate: price alone should rarely
queue a work.

**Meaning:** comparing a work with its peers beats a generic outlier model by a wide margin.
Mark-ups under 2× hide inside normal price variation, so they need a second signal, such as
the document agent reading quantities.

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

### A1 Eligibility (prohibited works): works after a rewrite

| Reader | Works flagged | Plainly prohibited | Worth an officer's look |
|---|---|---|---|
| Keyword anywhere (rival method) | 21,010 | 5% (2 of 40) | 18% |
| v1: word must be the object of the work *(built)* | 642 | 12% (7 of 60) | 25% |
| **v2: v1 + fixes from reading its mistakes** | **458** | **56% (28 of 50)** | **80%** |

**Honest scoring:**
- The v2 fixes were found on one sample of 50. The figure above comes from a **fresh** sample
  of 50, read after the rules were frozen.
- Of the 20,553 works that only the keyword search flags, 0 of 60 read as plainly prohibited
  and 2 as worth a look. So v2 misses little while flagging 46× fewer works.

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
- **Setting:** each method runs at the loosest setting that confuses no two *different*
  photos.
- **Check by eye:** the 25 closest pairs were all different pictures sharing a layout —
  photographed forms of one template, handwritten photo sheets, numbered handpump prints.
- **Result:** each edited copy of each photo was tested:

| Edit | 64-bit fingerprint (rival) | 256-bit fingerprint | Feature matching (ORB) | **DRISHTI (either)** |
|---|---|---|---|---|
| Re-save, half size | 100% | 100% | 99–100% | **100%** |
| Brighten 25% | 88% | 100% | 99.7% | **100%** |
| Stamp band added | 45% | 93% | 97% | **99.4%** |
| 2° turn | 43% | 87% | 100% | **100%** |
| 8% crop | 19% | 10% | 99.7% | **100%** |
| Screenshot frame | 0.3% | 0.9% | 100% | **100%** |
| **All edits** | **56%** | **70%** | **99.4%** | **99.9%** |

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

### B3 Geo-location
*(Filled in after the text reading finishes.)*

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
