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

## 3. The agents, one line each

Grouped by the step of a work's life they watch. ✅ = built into the live app ·
🧪 = tested on real data in our trial, being built · 📝 = planned.

**Before the money moves**
- ✅ **Cost** — *Is the agency's cost estimate right for this size of work here?* It reads the implementing agency's
  cost estimate form (size, specification, every expense line) and asks only when a confirmed quantity is far above
  what the size needs, or the price is far above the same standard item here **and** above the MP's amount. A work
  with no form is not judged: an amount alone does not say what is built (3 Oct 2026: of 15 works a record-only check
  would have questioned, none was a real price question).
- ✅ **Guideline Compliance** (includes Eligibility) — *Does the work follow the MPLADS rules?* (e.g. waiting for sanction past 75 days, works inside a temple campus)
- ✅ **Duplicate Work** — *Is this work already sanctioned here, or one job cut to stay under a limit?* It asks when the
  cost form's map pin is within 50 m of a sanctioned work of the same kind, when the agency itself says it rebuilds a
  work completed under three years ago, or when every piece of one job sits within 4% under the ₹5 or 10 lakh limit
  (12 of 14 such groups read as one job). Works that only *read* alike are notes for the agency to answer: from words
  alone that is right about 2 times in 3.
- ✅ **Office Patterns** — *Does this office price most of its works just under a limit, or record buildings complete days after sanction?* (an office's habit backs up a work's own findings; it never puts a work on the list by itself)

**While the work is built**
- 🧪 **Site Progress** — *Do the photos show what the record says was built? Is the plaque there, and do its dates fit?* (built with free local photo readers; switched on only after it is measured on real photos)
- 🧪 **Photo Forensics** — *Has this photo been used on another work, or edited?*
- 🧪 **Geo-Location** — *Was the photo taken at the site, and at the right time?*
- 🧪 **Document** — *Do the certificates and bills match the portal?*
- 📝 **Satellite** — *Did a large pond or long road actually change the ground?* (big works only)

**Money and time**
- ✅ **Delay** — *Which open works are most likely to run late?* (shown on each work, not counted in the score until it meets its accuracy target)
- 🧪 **Fund Flow** — *Where is money waiting for sanction too long?*
- 🧪 **Contractor Network** — *Is a small circle of contractors getting most of the works?*

**After completion**
- 📝 **Citizen Verification** — *Do local people confirm the asset exists and is used?* (scan a QR code at the site)

**For every work:** Data Validation ✅ · Risk Fusion (the score) ✅ · Inspection Planner 📝 · Ask DRISHTI (questions in plain Hindi/English) 📝

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
