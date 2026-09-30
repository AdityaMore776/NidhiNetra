# T030 · Duplicate & Split-Work engine: plan

**Question for the officer:** is this work repeated, or one job cut into pieces?

## How it works
1. **Offline data job** `data/build_dup_split.py` (heavy libraries stay out of the web engine):
   every description becomes a meaning vector (free local model
   `paraphrase-multilingual-MiniLM-L12-v2`, so English and Hinglish wordings match). Works are
   compared only inside their own district (the finest location the record has).
2. **Duplicate pairs:** text alike (cosine ≥ 0.85), within 24 months, and the rare place-like words
   of both descriptions agree (fuzzy ≥ 85). A pair naming no place cannot confirm a site and is
   dropped. Score = 0.50 text + 0.20 place + 0.15 time + 0.15 amount; flagged at ≥ 0.75.
   Same MP within 60 days = a batch (left to the split rule); repair/phase/balance words = staged,
   not flagged.
3. **Split groups:** same district, type and MP; each piece within 30 days of the last; text ≥ 0.80
   alike; 3+ pieces with near-equal amounts. Shared place word = `same_site_split`, else
   `bulk_order`. Every piece Rs 4–5 lakh while the total passes Rs 5 lakh = extra signal.
4. Results go to `work_signals["dup_split"]` (migration 006); the engine
   `apps/engine/drishti/agents/dup_split/` only reads them.

## Signal
| case | signal |
|---|---|
| repeated after the first was completed | 0.85 |
| repeated while the first was open | 0.60 |
| split at one site | 0.60 (+0.20 under the limit) |
| bulk order | 0.35 (+0.20 under the limit) |

The strongest case wins; each group member carries the group id so fusion counts a group once.
Not run, or no description/date/amount → NOT_ASSESSABLE (never a clean chit).

## Proof (done-when)
- Read the top 50 pairs by eye; report the share that look like real repeats in FINDINGS.
- The Nanded "Sapti" 3 × Rs 4,96,000 split is found.
- Unit tests (`tests/agents/dup_split/`).

## Result (30 Sept 2026)
Found by reading the output and fixed: groups cut by place, numbers separate sites, 3+ identical
copies = a series, whole place lists must match. Fresh random samples: pairs 15/40 real, same-site
splits 10/15, bulk orders 15/15 read correctly; Nanded Sapti found. Details: FINDINGS A2.
