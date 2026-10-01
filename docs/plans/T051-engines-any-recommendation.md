# T051: every engine must work on any MPLADS recommendation, not just the works it was built on

**Asked by the owner, 1 Oct 2026.** Review the four live engines as a system design. Each engine's "brain"
must give a correct, specific answer for a recommendation it has never seen (new district, new office, new
year, new wording, Hindi script). It must not pass on the 2,09,993 works it was built from and fail
everywhere else. Then build the rest of the planned checkers, merged from 12 to about 8.

## 1. What the review found (measured on 1 Oct 2026)

Script: every real work through `assess_work` (147 s), plus eight made-up recommendations the engines
had never seen. Saved in the T051 log entry.

| Engine | Problem on unseen works | Problem in its output |
|---|---|---|
| Guideline Compliance | a Hindi-script description ("ग्राम रामपुर में मंदिर का निर्माण") is never read, though the same text in English is flagged · the election pause in the sanction clock is hard-coded to 2024 only | **3 risk values for 2,09,993 works** (0, 0.3, 0.6): 80 days waiting = 718 days waiting · "98% of completed street light works finished within 881 days" repeated word for word on hundreds of queued works |
| Cost Anomaly | the "described like this" check (version B) exists only for works in the training file, so a new work is judged by peers alone, a looser rule than the one that was measured | fine: 208 distinct risk values |
| Duplicate & Split | **an exact copy of a completed work, filed under a new id, gets "Compared with every work in its district: no repeat found"**. Nothing was compared: the matches were computed once, offline, for the old file only | 6 risk values; 16,372 works all at 0.15 |
| Delay | **cannot score any new work** (scores were computed once, offline); in unseen districts its accuracy falls to 0.59 (0.5 = chance) | 2 sentence templates; "the implementing office's past record" is the main reason in 5,173 of 5,450 warnings |
| Risk score | | 802 of the 1,524 queued works share one score (0.30 = guideline 0.18 + duplicate 0.12); 55 distinct scores in the whole queue |

## 2. The design rule this task adds

**One brain per engine, and it runs on any work.** The engine's reasoning is a pure function of (the work,
reference data, statistics tables). Offline jobs may *learn* tables and models from the corpus, but they must
be stored as data the engine reads (statistics, coefficients, word lists), never as per-work answers. A work
the engine has never seen goes through exactly the same code path as a corpus work. "Compared and found
nothing" may only be said after a comparison actually ran.

And: **a signal grows with the evidence.** A rule broken by a little and a rule broken by a lot must not score
the same; every sentence names this work's own numbers against its own comparison group.

## 3. Changes per engine

**Guideline Compliance 1.1**
- Graded signal per rule (`overrun_risk`): R01 from 0.30 just past the clock to 0.60 at four times it; R02
  from 0.15 at one year to 0.30 at the type's 98th percentile, then up to 0.60 at twice that. Never above a
  rule's severity, so one delay alone still can't make a work High.
- Sentences say how far past the limit *this* work is.
- Election pauses (model code of conduct) move to `reference/rules.json`, with a limitation naming the last
  date the calendar covers.
- R07 reads Devanagari: Hindi words for places of worship and their verbs ("निर्माण", "जीर्णोद्धार"), with
  the same landmark guard ("के पास", "के सामने", "तक"). A description in a script it cannot read says so
  in the limitations instead of passing silently.

**Cost Anomaly 2.1**
- Version B's "what works described like this cost" becomes a linear price model over words used in at
  least 20 constituencies (so it learns what words mean everywhere, not one MP's habits or village
  names), stored as coefficients in `engine_models`. The engine computes the range for any description,
  so seen and unseen works meet the same rule. Measured against the LightGBM version on held-out
  constituencies and the planted mark-up test; it replaces LightGBM only if it does as well.

**Duplicate & Split 2.0**
- The matching rules move into the engine (`agents/dup_split/match.py`, standard library only) and run
  for every work: corpus works in the batch, a new work from the API. Text similarity is lexical with a
  Hindi/English word map (sadak = road, nirman = construction). It must agree with the old meaning-vector
  matches on the corpus and pass a fresh by-eye sample.
- Place words = words not in a generic-word list (words found in at least 25% of districts, stored in
  `reference/generic_words.txt`), so a new village's name is a place word with no corpus count needed.
- Signals grade with the evidence: pair score, gap, amount closeness, group size, how tight under the limit.
- The ₹5 lakh and ₹10 lakh limits come from reference data, not a constant.

**Delay 2.0**
- LightGBM per-work scores are replaced by a backed-off late rate (office → district × type → state × type
  → type, each shrunk toward the level above) stored as a table: any work scores, a new office borrows
  its district's record and says so. Same strict backtest and held-out-district test as before; kept only
  if it is at least as good. Stays "shown, not counted" unless it reaches 0.80.
- Reasons are this work's facts (the office's open backlog today, its record with this work type), and a
  warning needs the office record to rest on at least 30 works.

**Risk score**: band cut-offs re-tuned on the new distribution; a fresh 30-work queue sample read by eye.

## 4. Twelve checkers merged into eight

| # | Engine | Merges (old ids) | Data it needs | State after this plan |
|---|---|---|---|---|
| 1 | Guideline Compliance | Eligibility A1 + rules R01-R11 | the export | live, counted 0.30 |
| 2 | Cost Anomaly | A3 | the export | live, counted 0.20 |
| 3 | Duplicate & Split | A2 | the export | live, counted 0.20 |
| 4 | **Delay & Fund Flow** | C1 Delay + C2 Fund Flow | the export, term dates | shown, not counted |
| 5 | **Paperwork** | B4 Document + C3 Contractor Network | certificates (local OCR) | built on the pilot evidence |
| 6 | **Photo Evidence** | B2 Photo Forensics + B3 Geo-Location + D1 Citizen photos | photos, GPS stamps | built on the pilot evidence |
| 7 | **Site Progress** | B1 Site Progress + plaque + B5 Satellite | an AI vision key; big works only for satellite | frame + tests, off until the owner adds a key (rule 10) |
| 8 | Odd Overall | the blueprint's outlier slot | the export | built; counted only if it passes the planted test |

Why these merges: Delay and Fund Flow both ask "is money or time stuck?" and use the same dates. Document
and Contractor read the same certificates (the vendor code comes from the certificate). Photo Forensics,
Geo-Location and citizen photos all judge the same photos (is this photo new, from this place, from this
time?). Site Progress and Satellite both ask "was it physically built?", and both need inputs we don't
have yet. Eligibility already lives inside Guideline Compliance as R07.

Engines 5 and 6 only have evidence for the 837 pilot works. Everywhere else they say "no evidence
attached" (NOT_APPLICABLE), which is not a clean chit. They are shown, not counted, until each meets its
accuracy target on real evidence.

## 5. Order and pull requests

1. T051 (this plan): engines 1-4 fixed, measured, bands re-tuned. One PR.
2. T110 Paperwork (closes T101-T104), T310 Photo Evidence (closes T301-T304, T505), T410 Delay & Fund
   Flow (closes T402), #63 Odd Overall, T510 Site Progress frame (T503, T604 stay open for the key and the
   go/no-go). One PR each, every one based on main after the previous merges. Lesson from 30 Sept:
   stacked PRs are retargeted to main before any branch is deleted.
