# NidhiNetra blueprint: the main architecture (from 27 Sept 2026)

**This is now the design every task follows.** Source: the team's *NidhiNetra Solution Blueprint &
Implementation Guide* v1.0 (PDF, shared by the owner; not in this public repo). This page carries everything an
agent needs to build from it. The earlier 12-checker v2 design (`2026-09-25-drishti-v2-full-agents-design.md`)
is now a **side track**: its real-evidence checkers are built only after the core below, and feed into it.

**Name:** the blueprint calls the product **NidhiNetra** ("the eye on the fund"). Code and repo still say DRISHTI
until task T091 renames the user-facing text.
**Stack:** stays as built (Next.js + FastAPI + Supabase Postgres on Vercel). The blueprint suggests React/Vite,
SQLite and Docker; those are equivalents, not requirements.

## The loop: detect → explain → act → learn

| Layer | What | Tasks |
|---|---|---|
| 1 Ingest | eSAKSHI works (have 2,09,993), Guidelines 2023 rule library, location lookup (village/block/district → lat/lon), field inputs | T001, T061 |
| 2 Prepare | clean/validate (never drop rows, flag them), work-type tagging, quantity extraction ("300 m", "10 nos"), **mask PII** (phones, "S/o", "W/o", "Shri …"), features | mostly built; T011 |
| 3 Detect | **four engines**, each returns per work a `signal` 0–1 + `evidence` dict; engines never talk to each other | T010, T011, T020, T030, T040 |
| 4 Explain | one 0–100 risk score, top-3 reasons in English + Hindi | T050 |
| 5 Act | alerts + lifecycle, 4 role dashboards, **Inspection Planner (headline)**, field app, pre-sanction check | T060–T065 |
| 6 Learn | field verdicts → engine reliability → re-tuned weights; later a re-ranker | T070 |
| Prove | planted-anomaly test (50 fake problems), measured numbers | T080 |

## The four engines

**Contract:** `run(works, features) -> rows of (work_id, signal 0..1, evidence dict)`. Our existing per-work
`AgentResult` contract can carry this (`risk` = signal); T010 decides and documents the exact shape.

1. **Guideline Compliance** (rules as code). `rules.json`: id, title, guideline_ref (para of Guidelines 2023),
   condition, severity, message_en, message_hi. Severity → signal: High 1.0, Medium 0.6, Low 0.3; the work's
   signal = highest severity broken. Starter rules:
   R01 sanction late (`sanction_days > 45`, Medium) · R02 completion overdue (not completed, `age_days > 365`,
   High) · R03 spend above sanction (High) · R04 completed, nothing spent (High) · R05 ≥90% spent, not started
   (High) · R06 impossible timeline (High) · R07 possibly inadmissible work, wording "verify" (Medium; use our
   Eligibility v2 patterns, 56% precision measured) · R08 outside allowed area (Medium) · R09 stalled >180 days
   (Medium) · R10 SC/ST share below 15%/7.5% (Low, MP-year, only if area tag exists) · R11 missing key data (Low).
2. **Cost Anomaly.** Version A: peers = work type + state + ±2 years (fallback type + national if <20),
   leave-one-out p10/p50/p90 (per unit when quantity known); `signal = clip((cost/peer_median - 1.3)/1.7, 0, 1)`.
   Version B: LightGBM quantile models (q 0.1/0.5/0.9) on log cost, out-of-fold; plus an Isolation Forest
   "odd overall" signal (`s_outlier`). *Our live cost agent (district peer bands) is the starting point; its
   measured 63% catch of 5× mark-ups at 1.5% false alarms stays the benchmark.*
3. **Duplicate & Split-Work.** Duplicates: multilingual embeddings
   (`paraphrase-multilingual-MiniLM-L12-v2`), block by district, cosine ≥ 0.85, confirm place (fuzzy ≥ 85),
   time (≤ 24 months), amount (±25%); `pair = 0.50 text + 0.20 place + 0.15 time + 0.15 amount`, signal if ≥ 0.75.
   Splits: same district + type (+ agency) within 30 days, text ≥ 0.80 + shared place token, groups of ≥3 with
   amount CV < 0.15, amounts just under a limit raise it. Every split flag says "verify". *Our trial already found
   136 bulk-order groups and same-day splits under ₹5 lakh (`data/trial/split_trial.py`).*
4. **Delay Prediction.** Label = completed >365 days after sanction or still open after 365. XGBoost on work type,
   log cost, state/district, agency past delay rate (out-of-fold), sanction month, MP-year load (+ months elapsed,
   spend ratio for snapshots); SHAP top reasons. Target AUC ≥ 0.80 on held-out districts. *Honest baseline: our
   trial model scored 0.71 vs 0.68 for the office's own record; report the real number.*

## Risk score and reasons

```
risk = 100 * (0.30*s_rule + 0.20*s_cost + 0.20*s_dup_split + 0.20*s_delay + 0.10*s_outlier)
if high_severity_rules >= 1: risk = max(risk, 70)
if high_severity_rules >= 2: risk = max(risk, 85)
band = Low <40 · Medium <70 · High <85 · Critical ≥85
```
Tune cut-offs so High + Critical ≈ 5–10% of works. Contribution = weight × signal × 100; top three become the
reasons, from per-engine sentence templates (EN + HI) filled from evidence. Never a bare number.

## Action layer

- **Alerts** for High/Critical; lifecycle New → Triaged → In plan → Inspected → Issue confirmed / Cleared →
  Closed; every write in a hash-chained `audit_log`. Daily digest (console/email in demo).
- **Dashboards:** Ministry (national map, trends, engine performance) · State Nodal (district league table,
  escalations) · District (ranked queue, alert card, today's plan, pre-sanction) · Field officer (route,
  checklist, capture) · MP (own works, view-only, neutral wording "delayed — under review"). Row-level scoping.
- **Inspection Planner (headline):** candidates = open alerts risk ≥ 40 + 10% random lower-risk; locate (village
  → block → district centroid, "approximate"); travel = haversine × 1.3 ÷ 30 km/h, 40 min per stop; value =
  risk × (1 + log10(amount in lakh)); greedy by value ÷ extra minutes within an 8-hour budget; order with
  OR-Tools TSP; output map, stops, per-stop checklist from the reasons; report km saved vs list order.
- **Field app** (mobile web): route, site card, checklist, photo + GPS + time, verdict OK / Issue / Not found /
  Can't verify; GPS > 2 km from site = "location mismatch"; perceptual-hash photo reuse check.
- **Pre-sanction check:** compliance (category, location), duplicate/split search, expected cost → Green /
  Amber / Red with reasons, inside the decision window; never blocks.

## Learning loop and proof

- Verdict labels: Issue / Not found = 1, OK = 0, Can't verify = ignored. Engine reliability = (1 + a)/(2 + a + b)
  over alerts where it was a top-3 reason; weight ← start weight × reliability, renormalised (per state
  optional). 200+ labels → logistic re-ranker. 10% exploration visits. Demo uses **simulated verdicts, labelled
  "mechanism demo, not field accuracy"**.
- **Planted-anomaly test:** copy works, insert 50 fakes (inflated cost 2–3×, reworded/translated duplicates,
  3–5-way splits, rule breaches, impossible timelines), run blind, report share in the top 5% (target ≥ 75%).
  Also: delay AUC, review load 5–10%, top-50 manual precision, full scoring < 5 min, planner km saved.

## Honest notes carried over from our measurements (don't lose these)

- The blueprint quotes "₹9.16 cr on 518 works" from CAG; we could not find it in CAG Report 31 of 2010-11.
  Use the annexure TOTAL figures in `docs/STATUS.md` until someone finds the source.
- 45 vs 75 days: the 2016 text says 75; the blueprint says 45 (2023). T001 settles it from the 2023 PDF.
- The public export has district-level location only (no GPS); the planner's distances are approximate.
- Our project rules still apply: "needs verification", never "fraud"; never score MPs (the MP dashboard is a
  neutral status view); only measured numbers; no private data in this public repo.
