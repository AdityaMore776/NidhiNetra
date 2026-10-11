# How DRISHTI works — in plain words

*For judges, officers and team members who don't read code. For the technical version see
[ARCHITECTURE.md](ARCHITECTURE.md).*

---

## 1. The scheme we are watching

The **MPLAD Scheme** gives every Member of Parliament **₹5 crore a year** to get small public works built
in their area. The whole scheme runs on a government portal called **eSAKSHI** (since April 2023).

A work goes through six steps:

```
 1 RECOMMEND        2 SANCTION          3 BUILD             4 PAY               5 COMPLETE          6 USE
 MP picks a    →    District        →   Implementing    →   District       →   Marked complete →   The public
 work on            Authority           Agency builds,      verifies each       on final            uses the
 eSAKSHI            approves it         uploads photos      stage, money        payment; should     asset
                    (75-day limit)      and bills           goes direct         take ≤ 1 year
```

At each step, things can go wrong — and government auditors (CAG) have found all of them:

| Step | What goes wrong | Example from CAG's audit |
|---|---|---|
| Recommend | work not allowed by the rules; same work funded twice; one work cut into pieces to dodge a limit | 7,230 works sanctioned without following the guidelines |
| Sanction | cost far above similar works; sanction delayed | — |
| Build | photos that don't show the work, reused from another work, or taken somewhere else; no plaque | **4,918 works without the mandatory plaque** |
| Pay | bills that don't add up; money paid ahead of progress | doubtful vouchers |
| Complete | works that never finish | **₹280 crore in 12,006 works left incomplete** |
| Use | asset missing or not used | assets not put to use |

**The real problem:** there are about 2.1 lakh works and a handful of officers per district. Nobody can
check every work by hand, so problems are found years later, by audit, if at all.

## 2. What DRISHTI does

DRISHTI is like a team of **specialist assistants** who read every work's file every day and put a sticky
note on the ones an officer should look at.

1. **It collects the data.** The work records from eSAKSHI, plus the certificates, bills and site photos
   that eSAKSHI already publishes for completed works.
2. **It cleans and checks the record.** Impossible dates (finished before it was recommended), missing
   fields, phone numbers that must be hidden.
3. **Specialist agents look at the work.** Each agent answers one question — *Is this cost unusual? Has this
   photo been used on another work? Was the photo taken in the right district?* (the full list is below).
4. **The answers are combined into one score from 0 to 100**, with the **top reasons** and the evidence.
   Low / Medium / High / Critical. The score is the chance the work is worth an officer's look, worked
   out from how often flags of each kind were right when the team read them one by one. One check that is
   nearly always right (a temple work, a ₹40 lakh sum that says nothing about what or where) is enough
   for High; a check that is right only half the time (a possible repeat) stays Medium until a second
   one agrees. Critical needs two different checks.
5. **The officer gets a short, ranked list**, not thousands of alerts. On the 40,935 works in eSAKSHI's
   public dashboard tables (2 Oct 2026, never used to build any rule), the list is **427 works (1%)**, and
   39 of 40 picked at random were worth checking. A purchase entered as many works shows once.
6. **The officer decides.** They open a work, see exactly why it was flagged, check it, and record their
   verdict. (Planned: those verdicts are added to the same counts the score is built from, so it learns which
   alerts were right.)

## 3. The four agents, one line each

Since 4 Oct 2026 DRISHTI runs four agents (the owner's decision). Each asks only about what is likely to be a real
problem, never a small mistake, and says "couldn't check" when it has nothing to look at.

- ✅ **Cost** — *Is every line of the estimate fairly priced for this district, and is the whole estimate fair?* It
  reads the implementing agency's cost estimate form, prices each line at a fair rate (the state's Schedule of Rates,
  or what other agencies in the district recently paid, never the agency's own) and holds each quantity to what the
  size needs. It asks only when the whole estimate is at least 15% **and** Rs 50,000 above the fair price, so one odd
  line or a rounding never counts. A work with no form is not judged.
- ✅ **Duplicate Work** — *Is this work already sanctioned here, or one job cut to stay under a limit?* It asks when the
  cost form's map pin is within 50 m of a sanctioned work of the same kind, when the agency itself says it rebuilds a
  work completed under three years ago, or when every piece of one job sits within 4% under the ₹5 or 10 lakh limit
  (12 of 14 such groups read as one job). Works that only *read* alike are notes for the agency to answer. A pin
  typed a little away from the real site does not hide it: once two site videos are filmed next to an earlier
  building of the same kind, it asks just the same.
- ✅ **Time & Rules** — *Was it sanctioned on time, and is it being finished in a believable time?* A sanction later
  than 75 days is told as a fact about the office (6 in 10 works pass it), never as a problem with the work. The
  agency's own estimated time to completion sets a "comfort window": finishing far too early is asked about only when
  no site video shows the work being built, so good, fast work is never punished; running past the window (after
  allowing monsoon months and approved extensions) is a follow-up. Dates that cannot be true, and buildings recorded
  complete within days of sanction, are asked about too.
- ✅ **Site Progress** — *Do the monthly site videos show real, new work, at this work's site, for this work only?* The
  agency films a short video each month in the app, at the same marked spots, with GPS. The video is sealed when
  filming stops, read once, then deleted (blurred frames are kept). It asks when footage was used before, when the
  site is another work's, when both the GPS and the views say it was not filmed here, or when the agency's claim is not
  shown two months in a row. A blurry or dark video is simply filmed again. (Built and tested on made-up scenes; the
  trial on real sites comes next.)
  **The same spot every month (T158):** the first visit saves where the person stood at each spot (GPS) and which
  way they faced and panned (the phone's compass). Next month the app shows a radar to each spot's box (about 12 m
  across), an arrow to turn the right way, and a band to pan across, with last month's three pictures. A work too
  big for one spot asks for more, from its size on the form: a pair of spots at opposite corners for every 40 m (a
  60×40 m hall needs 4); a road is filmed stretch by stretch, and over 1 km the app picks 6 stretches at random when
  filming starts. The claim is judged spot by spot, on last month's and this month's pictures of the same spot. A
  claim about the whole work must hold at every spot; a claim about one part needs one spot to show it, and "not
  shown" only when every filmed spot agrees and at least half the needed spots were filmed. The guidance never
  stops anyone filming: being off the box is only noted, and the pictures decide.

  Whether the footage *shows the agency's claim* ("walls up to lintel level") is read by **NidhiLens**, the team's
  own fine-tuned vision model. On 883 real site-photo checks it scored macro-F1 0.935, against 0.876 for Gemini 3.1
  Pro at its best, at 1/30 of the cost. Report: [`NidhiLens (Fine-Tuned Qwen for site progress monitoring)`](../NidhiLens%20(Fine-Tuned%20Qwen%20for%20site%20progress%20monitoring)/README.md).
  It is built into Site Progress behind a switch (it needs a GPU), and run that way it scores 0.933 on the same
  checks. Its answers stay notes for the officer until the field trial on real sites.

**For every work:** the risk score with its top three reasons ✅ · the pre-sanction check ✅ · Inspection Planner ✅ (`/planner`: one day's
visits for a district, each work placed at the village or block its description names, the most important visits
fitted into the day in the order that drives least, with random spot checks and a checklist per stop)

Retired on 4 Oct 2026: Guideline Compliance (its timing rules live on in Time & Rules), Fund Flow, Office Patterns,
Paperwork and Photo Evidence. Their trial results stay in [`trial/FINDINGS.md`](trial/FINDINGS.md).

## 4. One real example, start to finish

From our trial on real eSAKSHI evidence (Chittaurgarh, Rajasthan — a boundary wall at a bus stand):

1. **The record says:** the MP recommended this work on **11 March 2024**.
2. **Geo-Location reads the photo:** the completion photos carry a GPS stamp with the date —
   **30 July and 2 August 2023**. They show a finished, painted wall.
3. **Geo-Location checks the place:** the coordinates fall inside Chittaurgarh district. ✔
4. **So the finding is:** *the evidence shows this work finished seven months before it was recommended.*
   DRISHTI does **not** say why. Maybe the portal entry was simply late; maybe a finished work was put
   forward as a new one. **It says: needs checking**, shows both dates and the photo, and an officer decides.

Another: in Nanded, **three works of ₹4,96,000 each** for the *same road*, recommended the same day —
₹14.88 lakh in pieces each just under ₹5 lakh. Duplicate Work raises it; the officer checks whether the
split was allowed.

## 5. What DRISHTI brings

- **It reads the real evidence** — the certificates, bills and geo-stamped photos already on eSAKSHI, not just the spreadsheet.
- **It is tested on real government data** — the real evidence of 837 completed works, and all 2.1 lakh works.
- **One specialist per problem the auditors actually found** — cost, duplicates, splits, rules, photos, location, documents, delays, money, contractors.
- **Proof before launch** — every agent has a measured accuracy target and stays switched off until it meets it.
- **Every flag explains itself** — top reasons, the evidence and the guideline clause.
- **"Needs verification", never "fraud"** — the officer decides.

## 6. What DRISHTI will never do

- **Call anyone a fraud.** The software refuses accusing words; a test fails if an agent uses one.
- **Treat "couldn't check" as "clean".** If there is no photo, the photo agents say *could not assess*.
- **Score MPs.** It looks at works, offices and agencies — never at a Member of Parliament.
- **Show private data.** Phone numbers in descriptions and bank account numbers on certificates are masked.
- **Act on its own.** It suggests; officers decide.

## 7. Who sees what

| Role | What they get |
|---|---|
| **Ministry (MoSPI)** | national map, where risk concentrates, how accurate each agent is |
| **State Nodal Authority** *(planned)* | district and agency comparisons, stalled works |
| **District Authority** | the ranked review queue for their district, the evidence, an inspection plan |
| **Field officer** | the works to visit and a way to record what they found |
| **Member of Parliament** *(planned)* | progress and delays on their own recommended works |

The live prototype has the Ministry, District and Field views. A district officer only ever sees their own
district — this is enforced on the server, not just hidden on screen.
