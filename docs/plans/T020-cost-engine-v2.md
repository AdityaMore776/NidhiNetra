# T020 — Cost Anomaly engine v2: plan

**Why (owner, 30 Sept 2026):** the live cost agent gives odd answers. A library *building* is compared with
book purchases ("typical ₹10,000") and reads as hundreds of times the typical cost; many works show the
identical "5.0x"; every queued work gets the same "Medium risk".

## What is wrong today (measured on the real corpus, `data/dry_run.py` + a diagnostic)

1. **Peers mix different jobs.** A work type is coarse: `LIBRARY` holds book purchases (median ₹1 lakh) and
   library buildings (median ₹7 lakh); `COMPUTER` holds laptops and ₹3–5 crore incubation labs;
   `HEALTH_BUILDING` holds MRI machines; `COMMUNITY_HALL` holds skill hubs and guest houses. In a district
   where most library works are book orders the "typical" is ₹10,000, so a ₹1 crore building reads 1,000×.
2. **Undescribed and many-site sanctions are scored as mark-ups.** "Letter as per attached", "List as per
   attached", "Solar light in Allahabad Lok Sabha kshetra", "works recommended in letter no 216 for Jamalpur
   block": the amount covers an unknown number of sites.
3. **The spread collapses on round amounts.** 36.9% of sanctions are exact lakhs; in many districts most
   roads are filed at one value, so p10–p90 is narrow and a ₹5 lakh road next to ₹1 lakh peers reads "5.0x"
   (179 of 2,582 flags are exactly 5.0×, 138 exactly 2.0×). Works flagged at only 2× are noise.
4. **Every flag scores the same.** Soft findings are capped at 0.45 and weighted by confidence and
   reliability, so all 276 queued works land at 0.30–0.31: one band, one colour, no ranking signal.
5. **Scale is ignored where it is known.** A 1.2 km road is compared by total cost with 200 m roads; the
   per-metre check exists but found 1 work; counted items ("100 high mast lights") are not priced per unit.

## Plan

**Version A (rules, in the engine):**
- `scope.py`: read from the description what the money buys: GOODS (purchase/supply of books, equipment,
  furniture, vehicles), NEW (construction), REPAIR (repair/renovation/upgradation); UNDESCRIBED (no usable
  description → NOT_ASSESSABLE, "cannot compare a cost without knowing what it buys"); MANY_SITES (whole
  constituency / block / "various villages" / ward lists → bundle, not a mark-up).
- Peers = work type × scope (GOODS vs works) when both have 20+ works, leave-one-out, district → state →
  national back-off as today.
- Flag against the **top of the usual range** (p90), not the median: the finding says "₹X; similar works
  usually cost ₹a–b (9 in 10 under ₹b)". A floor stops round-amount districts flagging 2×.
- Roads with a stated length and counted items with a stated count are judged per metre / per unit instead of
  by total cost.
- Very far above every similar work (e.g. >25× the median) is worded as a **scope question** ("far larger than
  any usual community hall: check what the work covers and that its type is right"), not a mark-up.

**Version B (model, offline):** LightGBM quantile regression (q 0.1 / 0.5 / 0.9) of log cost on the
description's words (numbers stripped so the amount cannot leak), work type, state and year; out-of-fold by
constituency so an MP's copy-pasted works never teach the model their own price. A data job writes each
work's expected range; the engine compares against it.

**Outlier signal (`s_outlier`):** Isolation Forest over the whole record, kept only if it adds catch at the
same false-alarm rate (the trial measured 3% at 5× on amount + type + state).

## How it is judged (`data/trial/cost_trial_v2.py`)

1. Planted mark-ups, as trial 1: 1,000 held-out real works × 1.5/2/3/5/10, false alarms on 20,000 untouched
   works; plus a second test pool drawn at random (trial 1's pool favoured today's agent).
2. **Precision by eye:** 60 flags per version (top 30 + 30 random), each read and labelled "like-for-like
   price question" or "explained" (different job, many sites, undescribed, mis-typed). Labels saved with the
   result.
3. Keep whichever is better on both, and say so in FINDINGS. The old 63% / 1.5% stays the benchmark.

**Done when:** trial re-run and saved · tests (NOT_ASSESSABLE, NOT_APPLICABLE, each rule) · `s_outlier`
exposed or documented as off · CATALOG + FINDINGS updated · queue size before/after in the log.
