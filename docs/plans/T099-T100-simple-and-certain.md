# T099 + T100 · Simple and certain: one Cost check, one repeat check

**The owner, 3 Oct 2026:**
- "Work on the cost anomaly agent so that it works."
- "Pivot the duplication agent to only do the tasks which have a high chance of being very accurate. It should compare
  works in the given area to works that have already been sanctioned, and understand if this is a repeated work."
- "Account for continuations of works; you can include this in the form if needed. Simple and very accurate."
- "Remove all the bloat: only the very highly effective stuff that works and is simple."

This plan covers two tasks in `docs/team/TASKS.md`: **T099** (Cost) and **T100** (Duplicate). Every number below comes
from `data/trial/simple_certain_trial.py` → `data/trial/results/simple_certain_trial.json`, with the by-eye labels in
`data/trial/simple_certain_labels.py`.

---

## 1. What the records can and cannot say (measured)

### Cost: no price question is certain from a record

The old Cost Anomaly compares an amount with "similar works", because it cannot know the size. Its main flag read right
**54 of 128** times, and it caught a planted 3× price **6%** of the time (FINDINGS T053, T080).

The most precise thing a record can support is a standard item with a stated count, such as "10 solar street lights" or
"one high mast". The Cost Estimate engine's reference groups (`agents/cost_estimate/reference.py`) were built for
every state. They can price **1,032 of 40,935** works (11 tight groups in 7 states).

A real work was questioned when its price per unit was more than 25% above the group's 98th percentile:

| | Works questioned | Read by eye |
|---|---|---|
| In-sample (every year) | 5 | 3 misreads, 1 bigger item, 1 grey |
| Hold-out (reference before 2026, works of 2026) | 10 of 211 | 2 misreads, 8 bigger items |
| **Together** | **15** | **0 real price questions**, 1 grey |

The misreads are the record's count being wrong for the money:
- two lights listed as "1 nag" each;
- six sites in one record.

The bigger items are things the record does not price as one: a 16 m mast, "4 way" lights, solar mini-masts. Only the
size and specification typed on a form can tell these apart. The two-signal rule of T097 exists for this reason.

Nothing else in the record is a certain cost fact either: on every one of the 36,430 works with a disbursed amount, the
money paid is at or under the sanctioned amount.

### Repeats: text alone is right about 2 times in 3, at best

On the team's 289 repeat pairs read by eye (108 one asset funded twice), here is what the stricter text rules get:

| Rule | Right | Recall |
|---|---|---|
| every pair the engine flags now | 108 / 289 (37%) | 100% |
| identical wording | 24 / 37 (65%) | 22% |
| 90%+ alike, every place word shared, nothing apart, no continuation word, not many sites | 38 / 59 (64%) | 35% |
| ... and two or more place words | 25 / 35 (71%) | 23% |
| identical wording, two or more place words, nothing apart | 13 / 16 (81%) | 12% |

On the dashboard's own works, the strictest rule's 25 pairs dated more than 60 days apart read **8 same, 6 grey, 11
different**. The misses are always the same few things:
- a village or landmark is not a site: one village has many roads, lights and borewells;
- an SC colony and a BC colony;
- a ground floor and a first floor;
- a resubmission, or a "completion of" work;
- no place at all ("Construction of returning wall").

The record's finest place is the district, so no text rule can be very accurate.

**So both checks take their certainty from the cost estimate form.** It carries the size and specification, a map pin
per site (both ends for a road), the nature of the work, and the earlier work it continues.

## 2. T099 · Cost: one engine, on the form

1. **The Cost Estimate engine becomes the Cost check**, in the core slot: blueprint weight 0.20, order 2, name "Cost".
   Its questions are unchanged from T097:
   - `MATERIAL_QUANTITY_ABOVE_SIZE`: a quantity the agency confirmed, more than 25% above what the size needs;
   - `ESTIMATE_ABOVE_STANDARD_AND_MP`: the price per unit more than 25% above the 98th percentile of the same standard
     item **and** the estimate more than 10% above the MP's amount. These margins are the owner's, decided 3 Oct 2026.

   A new kind of finding counts at the 1-in-4 prior in fusion v3 until officers' verdicts are read, so it cannot queue
   a work on its own (proof before launch).
2. **A work with no form is NOT_APPLICABLE:** "No cost estimate form for this work yet." This is a status, never a low
   score.
3. **The old Cost Anomaly is retired.**
   - `agents/statistical/engine.py` is removed, so it no longer runs, shows or counts.
   - The package stays as the shared readers (`scope.py`, `text.py`) and the cohort statistics that Guideline
     Compliance's R12 uses.
   - Its old agent code stays only so the trials behind FINDINGS can be re-run.
4. **References for every state** with a usable group: `data/build_cost_reference.py --all` writes
   `reference/cost/<state>.json`. These hold aggregates only.
5. **Forms are saved and reach the engines.** This is the storage half of T094; the screens stay with T094.
   - Migration `013_cost_forms.sql`.
   - `POST /api/v1/cost-forms`: a draft or a submitted form. A form is submitted only when it is `ready`, and the work
     is re-assessed at once.
   - `GET /api/v1/cost-forms/{work_id}`.
   - The batch, the work page and the API read a submitted form as `work["cost_form"]`.

## 3. T100 · Duplicate: is this work already sanctioned at this site?

The engine keeps its stored id `dup_split`. It is renamed **Duplicate Work** and answers one question.

**Questions** (counted; each one certain by how it is built):

| Code | When |
|---|---|
| `SANCTIONED_WORK_AT_THIS_SITE` | The form's map pin is within **50 m** of the map pin of a sanctioned work of the same kind of asset, and the agency did not name that work as the one this work continues. Roads, drains and other linear works compare both ends. |
| `REBUILT_SOON_AFTER_COMPLETION` | The agency itself declares that this work rebuilds sanctioned work X (nature "reconstruction", earlier work X), and X was completed less than **3 years** before this work was recommended. |

**Notes** (shown, never counted):
- `CONTINUES_SANCTIONED_WORK`: the agency names the earlier work this one continues, extends, upgrades or rebuilds. The
  note says whether that work is on record in the district.
- `LOOKS_LIKE_SANCTIONED_WORK`: an earlier sanctioned work of the same kind whose description names the same place in
  the same words (the strictest text rule above, right about 2 times in 3). With a form, the note shows the agency's own
  answer about it.

**Removed:** split works, numbered stretches, bulk orders, the under-a-limit bonus, and text-only repeat flags. Each read
right about half the time (`reliability.json`: splits 18 of 32, repeats 6 of 12 and 33 of 74). The bunching of amounts
under Rs 5 lakh stays visible as an office's habit in Office Patterns.

**On the form (continuations):**
- The nature of the work gains **`continuation`** (finishing, or the next phase of, an earlier work). For a
  continuation the earlier work's ID is required.
- The form lists the sanctioned works the engine found that look like this one. The agency answers each:
  - **"the same work"** blocks the form: it is already sanctioned;
  - **"this work continues it"** must match the nature and the earlier work ID;
  - **"a different work"** needs a sentence saying what differs (another site, another landmark).
- These answers turn the 2-in-3 text match into a declaration on record. The map pins make the site check certain.

**Where earlier works' pins come from:**
- submitted forms (every new work from now on);
- for older completed works, later, the GPS stamps on their eSAKSHI completion photos (Photo Evidence already reads
  them).

## 4. Proof before launch (rule 4)

- **Unit tests** cover every question and note, the 50 m line and its edges (49 m asks, 51 m does not), a linear work by
  both ends, a declared continuation never asked about, a different kind of asset at the same pin, and every
  NOT_APPLICABLE / NOT_ASSESSABLE case. They also check plain wording on damaged forms.
- **The test country** (`evaluation/synthetic.py`) carries the same truth: kinds that are no longer checked are marked
  "not checked by design", so the quality gate measures what the product does.
- **The dashboard's 40,935 works:** what leaves the queue is measured and listed in FINDINGS.
- **Real forms:** T098 reads the first officer verdicts and sets the measured rates in `reliability.json`.
