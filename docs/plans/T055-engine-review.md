# T055 · Engine review: a test country, a new engine, and a score built from measured hit rates (2 Oct 2026)

**Asked (owner, 2 Oct 2026):** check the whole architecture and every agent; refine each one or find an
architecture that is more accurate for the goal (finding MPLADS works an officer should check); add agents
that help; test them hard on data they have never seen and in a random environment. Then: use the real
eSAKSHI dashboard tables (four CSVs, 40,935 works) to test.

Numbers in this file come from saved script output; the full tables are in
[`trial/FINDINGS.md`](../trial/FINDINGS.md) "T055".

**Result in one table** (test country: 3 seeds, 60,951 works, 810 planted problems; real: the dashboard's 40,935
works):

| | Main | This branch |
|---|---|---|
| planted problems caught by the engine meant for them | 31% | **74%** |
| planted problems in the review queue | 4% | **16%** |
| planted problems in the top 5% of the score | 34% | **74%** |
| queue precision on the test country | 62% | **68%** |
| ordinary works queued (false alarms) | 0.03% | 0.11% |
| real works in the review queue | 47 | **427** |
| 40 random real queue works read by eye: worth checking / grey / misread | 38 / 1 / 1 | **39 / 1 / 0** |
| team's 159 labelled repeat pairs: false / true repeats flagged | 56 / 44 | **50 / 43** |

## 1. What the review found

| Where | What was wrong | How we know |
|---|---|---|
| **Measuring** | The only recall measurement was the planted test (T080: 50 fakes, needs the private data pack). By-eye samples measure precision only. Nothing in CI stopped a change that blinded an engine or made it flag look-alikes. | the repo |
| **Risk score (v2)** | A fixed weight times each engine's signal. No single engine could reach High (Guideline Compliance at its strongest gave 0.18 of the 0.22 needed), so a temple work found with certainty, a split or a repeat stayed Medium unless a second engine happened to fire. The weights were the blueprint's, never measured. | 4% of planted problems reached the queue on the test country; T080 4 of 50 |
| **The queue** | One purchase entered as many works filled the queue: 11 of 40 random queue works on the dashboard data were one ₹1.53 crore street-light purchase. | `dashboard_labels.py` QUEUE_BASELINE |
| **Guideline Compliance** | R07 missed real wordings ("hall in Mandir", "wall for temple", a church toilet, kitchen tables for a private school, "PRIVETE ITI") and misread a few ("Pulic Distribution shop" is a ration shop). The dashboard carries real sanction dates, but no rule looked at a building recorded complete days after its sanction. | dashboard flags read by eye |
| **Cost** | "Far bigger than usual" excused a high price even when the description states a single unit ("1 high mast light" at 10× its peers). | test country: 28% of these caught |
| **Duplicate & Split** | One road cut into numbered stretches ("part-1 / part-2", "phase", "chainage 0-500") was not read as one site, and the numbered pieces were paired as repeats; a repair of an asset the scheme had just built was never looked at; one village spelt two ways ("Chakwa" / "Chakva") read as two places; spec-sheet and typo words read as place names; the repeat clock ran from the first recommendation, not from completion. | test country: stretches 33%, repairs 0%; labelled pairs |
| **A missing view** | Nothing looked at offices. A habit (most works priced just under ₹5 lakh; buildings recorded complete within days of sanction) shows only across an office's works. | dashboard data |

## 2. What was built

```
  works ──► engines (one brain each, any recommendation) ──► calibrated fusion (v3) ──► queue, one row per case
            Guideline Compliance  R01-R14  (R14 new: built right after sanction)          ▲
            Cost                  + a stated single unit is never "a bigger project"      │ hit rates read by eye
            Duplicate & Split     + stretches, repairs, sound keys, completion clock      │ reference/reliability.json
            Office Patterns  NEW  office habits: priced at the limit, built at sanction   │ (+ officer verdicts, T070)
            Fund Flow, Paperwork, Photo Evidence   shown, not counted (unchanged)
  proof:   evaluation/ test country (planted problems + look-alikes) ── CI quality gate + random-environment tests
           data/trial/dashboard_trial.py (40,935 unseen real works) ── by-eye labels
```

1. **A test country** (`apps/engine/drishti/evaluation/`). A seeded generator builds a made-up eSAKSHI (states,
   districts, villages, offices, MPs; ~19,000 works per seed, shaped like the real export: amounts bunch under
   ₹5 lakh as often as on the portal, villages by a long-tail law, Hindi/English/typo wording) and plants
   labelled problems plus look-alikes the engines must leave alone (a temple as a landmark, "Saraswati Shishu
   Mandir" schools, batches for different villages, opposite sides of one road, bulk entry when the portal
   opened, big projects that state their size, a repair of a different asset). Statistics and the price
   model are rebuilt from each country, so nothing is tuned to one draw. **This is the only recall
   measurement that needs no private data.** `data/trial/synthetic_eval.py` runs three countries;
   `tests/evaluation/test_quality_gate.py` runs two small ones in CI with floors per planted kind and per
   look-alike; `test_random_environment.py` throws 400 malformed records at every engine and checks that
   load order, run order and capitals change nothing.
2. **Risk fusion v3** (`fusion/calibrated.py`, ARCHITECTURE §4). The score is the chance a work is worth a
   look: each finding counts its measured hit rate (worth + 1) / (read + 4); engines combine as independent
   evidence. A kind never read by eye counts 1 in 4 and cannot queue a work alone. Reasons say how often
   flags like it were right. `Reliability.with_verdicts()` is the hook for the learning loop (T070).
   `DRISHTI_FUSION=v2` rolls back.
3. **One case, one queue row.** A Duplicate & Split group is stored with `case_id` / `case_size`
   (migration 012) and shown once.
4. **Office Patterns** (new engine, `agents/office_patterns/`). Counted live from all works of an office:
   the share of its works priced just under a limit, and the share of its constructions recorded complete
   within 7 days of sanction, against the national share. "Routine" only when the Wilson lower bound is at
   least 3× the national share on 30+ (15+) works. A work just under a limit from such an office gets
   `PRICED_AT_LIMIT` (weight 0.10: it backs up a work's own findings, never queues it alone); the
   after-sanction habit is told as a fact, because R14 already counts the work. The dashboard lists the
   offices once (`GET /dashboard/office-habits`).
5. **Guideline Compliance.** R14 (new): a construction of ₹3 lakh or more recorded complete within 7 days of
   its sanction (needs a sanction date; migration 011). R07 reader: objects of worship after "in / for /
   on" ("hall in Mandir", "wall for temple"), private institutions before the route word, typo spellings of
   public distribution shops, "institution / institute / academy".
6. **Duplicate & Split.** Numbered pieces ("part / phase / bit / chainage") of one site are a
   `SPLIT_INTO_STRETCHES` group and never a repeat pair; `REPAIR_SOON_AFTER_BUILT` (a repair of the same
   asset within 3 years of the scheme completing it, judged on the asset words, not the amount); a sound key
   (w = v, long vowels short, aspirates plain) so one village spelt two ways agrees; Hindi/English synonyms;
   segment numbers are not plot numbers; a repeat's clock starts at completion; ~490 vetted generic words
   (spec-sheet and typo words) so they are not read as places.
7. **Cost.** A description that states one unit ("1 no. high mast light", "one borewell") is never excused as
   a bigger project.
8. **The dashboard tables as a test set** (`data/esakshi_dashboard.py`, `data/trial/dashboard_trial.py`):
   eSAKSHI categories mapped to work types (`reference/esakshi_categories.yaml`), real sanction dates, all
   engines run blind with statistics rebuilt from those works.
9. **Web.** Dashboard section "Offices with an unusual habit"; queue rows show "One case: N alike works";
   the score panel shows each reason's measured hit rate; How-it-works describes the seven checkers and v3.

## 3. Tried and not kept

- An amount-gap rule for repeat pairs and live "words spread across many districts are generic": neither
  improved the team's 159 labelled pairs, so neither was kept.
- "motar" / "moter" as generic words: they made a village spelt "Motari" read as a typo of them and lost
  a planted split; they appear in none of the labelled pairs, so they were removed.
- A finding for the office after-sanction habit: it double-counted R14 on the same works; it is a fact in
  the headline instead.

## 4. Ideas not built (and why)

- **Translated repeats** (a Hindi copy of an English work): the biggest known blind spot. Needs an offline
  translator or multilingual embeddings that run on the free tier; measure on the T080 planted test first.
- **End-of-year rush** (sanctions bunched in March by one office): a natural third Office Patterns habit;
  needs sanction dates for more than the dashboard's 15,662 works to measure a base rate per month.
- **Contractor concentration at national scale:** needs vendor codes from certificates beyond the pilot
  (Paperwork, T110) and a harvest (T003).
- **Price drift by year:** peers are pooled across years; an inflation-adjusted band needs a few years of
  sanctioned amounts per type.
- **Never built, by rule:** anything that scores an MP (utilisation by MP, an MP's "risk").

## 5. Open for the owner

- **v3 is the default.** On the dashboard's 40,935 works the queue grows from 47 to 427 (1.04%), and 40 random
  queue works read 39 worth checking, 1 grey, 0 misread (main's queue: 38 / 1 / 1). On the test country planted
  problems in the queue go from 4% to 16% while ordinary works queued go from 0.03% to 0.11%.
  `DRISHTI_FUSION=v2` rolls back without a code change.
- **Hosted database:** apply migrations 011 (sanction date column) and 012 (case id), then re-run
  `batch_assess.py`. The research export carries no sanction dates, so R14 and the after-sanction habit say
  "cannot be assessed" there until a dashboard load fills the column.
- **Planted test (T080) on the full 2,09,993 works with v3:** run `data/trial/planted_test.py` where the data
  pack is installed (it was not available in this session).
- **The 2023 guideline PDF (45 vs 75 days, T001):** still not reachable: this session's network policy blocks
  mplads.mospi.gov.in, mplads.gov.in and data.gov.in.
