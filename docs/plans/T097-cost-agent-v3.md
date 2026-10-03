# T097 · Cost v3: a cost checker that knows the size of the work

**Owner's pivot, 3 Oct 2026.** The Cost agent must be simple, certain in its own field, and nearly free of false alarms.
It gets a full **cost estimate form** filled by the implementing agency
([`docs/specs/2026-10-03-cost-estimate-form.md`](../specs/2026-10-03-cost-estimate-form.md)). It checks whether the
estimate is right **for the size of the work in that place**, then compares it with the **MP's recommended amount**. It
raises a question when the agency makes the work out to cost too much.

This file is the plan for the whole Cost v3 programme (tasks **T093–T098** in `docs/team/TASKS.md`). Any agent, yours
or a teammate's, can pick a task from here.

---

## 1. Goal

For every work that comes through the form, answer one question, with almost no false alarms:

> **Is the implementing agency's estimate more than this size of work costs here, and more than the MP recommended?**

Two kinds of answer:
- **Yes, with the reason in plain words:** which size, which comparison, which line drives the gap.
- **"Could not check"**, when there is no reliable reference. This is a status, never a low score and never a flag.

## 2. Why the old agent cannot do it (measured)

The old agent (`agents/statistical/`) sees only an amount and one sentence of text, so it has to guess the size.

| Measure | Result | Source |
|---|---|---|
| Its main flag ("above the comfort limit"), read by eye | **54 of 128** real price questions | `reference/reliability.json`, FINDINGS T053 |
| "Several sites in one amount" flags | **0 of 48** real | FINDINGS T053 |
| A planted 3× price on a normal work | caught **6%** of the time (it looks like a 3× bigger job) | FINDINGS T080 |

Uttar Pradesh in the eSAKSHI dashboard tables (`data/trial/results/cost_v3_reference_uttar_pradesh.json`) shows the
same problem from the other side:

| Work | Priced by | Works with a stated size | Median | Middle 80% around the median |
|---|---|---|---|---|
| Solar / LED street light | per light | 369 | Rs 20,944 | −0.3% / **+4.6%** |
| CC road | per metre | 493 | Rs 7,698 | −41.7% / **+58.5%** |
| Paver / interlocking path | per metre | 206 | Rs 5,789 | −22.2% / **+94.9%** |
| High mast | per mast | 232 | Rs 1,72,675 | −9.1% / **+60.9%** |

A standard item (one solar light) has a tight band. Anything whose size and specification eSAKSHI does not record
(how wide, how thick, how tall) spreads widely. The middle 80% of CC roads runs from 42% below to 59% above the
median, so a 50% mark-up hides inside it.

Place matters too. The median CC road per metre goes from Rs 4,000 (Ghazipur, 17 works) to Rs 12,259 (Mahrajganj, 27
works) across the 18 UP districts with 10+ roads.

Time barely matters inside the window: 2024 Rs 8,345, 2025 Rs 7,676, 2026 Rs 7,154 per metre. So 2024–2026 prices can
be pooled for the prototype.

**So the fix is not a better formula.** It is giving the agent the size and specification as numbers (the form), a
reference for **the same kind, size and specification in the same district**, and the MP's amount as a second check.

## 3. The flow

```
1. MP recommends (eSAKSHI)          work type, description, place, MP's amount
2. Agency fills the form (T094)     size + specification, site conditions, every expense line, charges
3. Checks while filling (T093)      fix / confirm, on the agency's screen; never a flag
4. Cost agent (T097)                a. price per unit of size  vs  the reference for this kind, size, district
                                    b. the total  vs  the MP's amount
                                    c. (with rates data) each confirmed material line  vs  its rate and quantity
5. Officer sees                     a question only when (a) says "too much for its size"; strongest when (b) agrees
```

## 4. The accuracy rules (what makes it certain)

1. **The form catches normal mistakes, not the agent.** Missing fields, typos, extra zeros and wrong units are `fix` or
   `confirm` on the form (`drishti/cost_form/validate.py`). The agent only runs on a form that is `ready`.
2. **No flag from guesswork.** The agent never flags from:
   - free text (the description, written-in work types, typed materials that are not confirmed);
   - "not known" answers;
   - site conditions (they can only widen what is allowed);
   - the typing guards (`guard` in the YAML is not a price judgment).
3. **No flag without a reference.** A comparison needs at least **30** real works of the same kind (and specification,
   when the reference has it) in the district, or else the state. Below that, "could not check".
4. **Allow the normal spread, then some.** "A certain percent above or below average" is measured, not chosen: the
   question starts above the **98th percentile** of price per unit in the reference group. That is the line only 2 in
   100 real works of that kind and place lie above, so at most about 2% of ordinary works can ever be asked about. T098
   tunes the percentile on read flags.
5. **The MP's amount is a second check, not a judge.** An estimate above the MP's amount but normal for its size gets no
   question: the MP's figure was simply low (the user's example: the MP thinks 3.2 lakh, it really costs 2.5–2.8).
   Above the MP's amount **and** above the size reference is the strongest case.
6. **Compare like with like.** Same pricing unit (m² for roads and buildings, per light, per kWp, …), same
   specification bucket when the reference has it (solar vs grid light, CC vs BT, M20 vs M25), same district (or state).
7. **Never score MPs** (project rule 5). The MP's amount is used only on this work; no MP-level counts or rankings, ever.
8. **Shown, not counted, until proved** (project rule 4). The new engine enters the score only after T098 measures it.

## 5. What the agent uses

| Input | From | Status |
|---|---|---|
| The form, `ready` | `cost_forms` table (T094), attached to the work as `work["cost_form"]` | form contract done (T093); storage T094 |
| MP's amount | the recommendation (`works.amount`) | exists |
| District, state | the work | exists |
| **Reference A: real works** (price per unit by type, district / state, percentiles) | eSAKSHI tables for UP (`data/trial/cost_v3_reference.py`) | **built for UP** (T095) |
| **Reference B: Schedule of Rates** (state SoR item rates, area premiums, carriage charges; CPWD DSR + cost index as fallback) | official PDFs, digitised | needs data (T096) |
| **Reference C: rates for goods** (GeM prices by specification) | GeM | needs data (T096) |
| Engineering norms (cement per m³ of concrete by grade, bricks per m³ of brickwork, …) | CPWD analysis of rates | needs data (T096) |
| Statutory tables (minimum wages, GST rates, cess, royalty) | state notifications | needs data (T096) |
| Forms with actual costs at completion | the form's completion step | later; makes Reference A tight (T098) |

**On data access:** this cloud environment's network policy blocks the government sites (cpwd.gov.in, data.gov.in,
gem.gov.in, pmgsy.nic.in, the state PWD sites; tested 3 Oct 2026). T096 is therefore a `human-task`. Either:
- someone downloads the files on an Indian connection into the team data pack; or
- the owner allows those hosts in the environment's network settings ("Network access" → Custom → Allowed domains).

## 6. How it works, step by step

1. **Not applicable:** no form on the work → `NOT_APPLICABLE` (the old agent keeps running for works without forms).
2. **Price per unit:** `catalog.pricing_size(type, size)` (e.g. 250 m × 3.75 m → 937.5 m²); the estimate's price per
   unit = grand total ÷ that size. Goods: each goods line's unit price. Work type `OTHER`: no unit reference, so
   step 4 only.
3. **Reference band:** pick the best layer that has 30+ works for this type and specification:
   1. completed forms (C, later);
   2. Schedule-of-Rates bottom-up (B, after T096);
   3. eSAKSHI real works (A, now; per metre or per unit, since eSAKSHI has no width).

   Use the district's group if it has 30+ works, else the state's. The band gives median, p90 and p98.
4. **Compare:**
   - **Size check:** price per unit > p98 of the group → "too much for its size".
   - **MP check:** total > MP's amount × (1 + 10%). The 10% matches the form's rule asking for a reason above 10%;
     T098 tunes it.
   - **Line checks** (needs T096):
     - each confirmed material's rate, restated per its own unit, > SoR basic rate × (1 + the measured spread);
     - each confirmed material's quantity > what the size needs by the norms × (1 + the measured spread). For example,
       cement bags for 140.6 m³ of M20 concrete.
5. **Findings** (wording: "needs checking", never accusing):

| Code | When | Risk (until T098 measures it) |
|---|---|---|
| `ESTIMATE_ABOVE_SIZE_AND_MP` | size check **and** MP check | the strongest |
| `ESTIMATE_ABOVE_SIZE` | size check only (the MP's amount was high too) | lower |
| `MATERIAL_RATE_ABOVE` | a confirmed material's rate above its SoR rate band | per line (T096) |
| `MATERIAL_QUANTITY_ABOVE_SIZE` | a confirmed material's quantity above what the size needs | per line (T096) |
| note: above the MP's amount but normal for the size | MP check only | none: "the MP's figure was low for this size" |
| note: below the size band | price per unit < p10 | none: "may run short of money; check nothing is left out" |
| note: lines not compared | typed items with no confirmed material | none |
| note: duration | `duration_months` beyond p90 of sanction-to-completion for the type | none |

   Example of the main sentence (made-up figures, to show the wording only):
   > "Rs 31.2 lakh for 937.5 m² of M20 CC road in Jaunpur is Rs 3,328 per m²; 98 in 100 similar roads in Jaunpur cost
   > under Rs 2,450. It is also 42% above the MP's recommended Rs 22.0 lakh (agency's reason: '…'). Please check the
   > estimate."

6. **Evidence on the card** (for the officer, never for the agency while filling): the size, the price per unit, the
   group's median, p90 and p98 with its n, the MP's amount, the gap, the agency's reason, and the line that drives it.

## 7. Where the code goes

| Piece | Path | Task |
|---|---|---|
| Field list (one source) | `apps/engine/drishti/reference/cost_form.yaml` | T093 ✅ |
| Catalog, materials, form checks | `apps/engine/drishti/cost_form/` (`catalog.py`, `materials.py`, `validate.py`) | T093 ✅ |
| Routes | `GET /api/v1/cost-form/catalog`, `POST /api/v1/cost-form/validate` | T093 ✅ |
| Storage | migration `NNN_cost_forms.sql` (next free number), `POST /api/v1/cost-forms`, `GET /api/v1/cost-forms/{work_id}` | T094 |
| Form screens | `apps/web/src/app/(app)/cost-form/` | T094 |
| Reference A (UP) | `data/trial/cost_v3_reference.py` → `data/trial/results/cost_v3_reference_uttar_pradesh.json` | T095 ✅ |
| Reference build for the engine | `data/build_cost_reference.py` → `apps/engine/drishti/reference/cost/<state>.json` | T097 |
| Reference B / C, norms, statutory tables | `data/build_sor.py`, `data/build_gem.py` → `reference/cost/` | T096 |
| The engine | `apps/engine/drishti/agents/cost_estimate/` (`engine.py` registry spec, `reference.py`, `agent.py`) | T097 |
| Hand-off | the old `statistical` agent returns `NOT_APPLICABLE` for a work that has a form (no double counting) | T097 |
| Fusion | weight 0 ("shown, not counted") until T098; then `reliability.json` entries from read flags | T098 |

## 8. How we prove it (T098, project rule 4)

**Planted tests**, on the test country (`evaluation/synthetic.py`, extended with forms), each with a pass condition:

| Planted change | Must |
|---|---|
| Same work at ½×, 2×, 5× size, price scaled to match | **not** be asked about |
| Same size at 1.25×, 1.5×, 2×, 3× price | be caught at a measured rate (report it) |
| MP's amount 30% low, price normal for the size | **not** be asked about (note only) |
| A normal price in a costly district | **not** be asked about |
| The same price in a cheap district | be asked about |
| Typos (extra zero, wrong unit) | be stopped by the form checks, never reach the agent |
| A typed material nobody confirmed | **not** be asked about |
| Work type `OTHER` | "could not check" on size; MP check only |

**On real data:**
- **Hold-out:** build Reference A from UP works recommended before 2026, run the agent on 2026 works (sized from their
  descriptions), and report the share flagged. Then read 30 fresh flags by eye.
- **Pilot:** 20–50 real estimates filled by an implementing agency (human task), read by an engineer.

**Targets** (for the owner to confirm):
- at least 9 of 10 flags are real price questions (today: 54 of 128);
- at most 2% of ordinary works asked about;
- 0 flags caused by a typo or a missing field (they cannot reach the agent).

## 9. Build order

1. **T093** form contract: field list, checks, routes, tests. **Done in this PR.**
2. **T095** UP reference from eSAKSHI, price per unit and time. **Done in this PR.**
3. **T094** form screens and saving (web, teammate). Starts now, from the spec.
4. **T097** the engine on Reference A (UP), then B and C as T096 lands.
5. **T096** official rates data (human task), in parallel.
6. **T098** proof, then switch on.

## 10. Decisions for the owner

1. The MP check margin (proposed 10%, the same as the form's "give a reason" rule) and the size threshold (proposed
   the 98th percentile). Both are tuned in T098 on read flags.
2. For a work that has a form, the old cost card is replaced by the new one (proposed: yes).
3. Data: allow the government hosts in the environment, or download the T096 files on an Indian connection.
4. A pilot implementing agency for 20–50 real estimates.

## 11. Built (3 Oct 2026): what changed from the plan, and why

Building the engine on the Uttar Pradesh records showed two ways a plain "price above the 98th percentile" rule would
still mistake size for price. Both are now rules in `agents/cost_estimate/reference.py` and `agent.py`:

1. **The group's unit must be the form's whole unit of size.**
   - UP's records never state a road's width (0 of 1,129 CC roads). So a group of roads per metre can look tight
     (Deoria: p90 +25%) while a 5 m road would still be asked about against 3 m ones.
   - Roads and paths are priced per m² on the form, so they are never compared with roads per metre.
   - Standard items are compared per unit: solar street lights per light, high masts per mast.
2. **A price question needs two signals.** The records hold no wattage or mast height, so a bigger item could explain a
   high price by itself. A price question (`ESTIMATE_ABOVE_STANDARD_AND_MP`) needs both:
   - the price per unit more than **25%** above the group's 98th percentile; **and**
   - the estimate more than **10%** above the MP's amount.

   Either signal alone is a note on the card.
3. **A group is used only when tight:** its own p90 within +25% of its median. A loose group is missing a size or
   specification, and comparing with it would be guessing.

**Added: quantities against the size** (`cost_form/norms.py`, exact by construction):
- more light fittings, batteries, panels or poles than solar lights (no poles at all on existing poles);
- more lamps than the masts carry;
- paver blocks beyond the path's area plus 5%;
- cement beyond an M10–M20 slab's volume by the IS 456 nominal mixes, plus 5%, only when nothing else on the road
  uses cement.

The form asks the agency to confirm anything above what the size needs. The engine asks the officer only about a
**confirmed** quantity more than 25% above it (`MATERIAL_QUANTITY_ABOVE_SIZE`).

**Moved to T098:** the old Cost Anomaly handing over for works with a form. The new engine is shown, not counted, so
until it is switched on both cards appear and nothing is counted twice.

**Measured** (`data/trial/cost_v3_holdout.py`, FINDINGS "T097"): the reference was built from UP works before 2026 and
tested on 68 unseen 2026 works.
- 0 of the 42 it could compare were above the question line.
- Planted price ×1.5, ×2 and ×3 were asked about 42 of 42 times; ×1.25 9 of 42; ×1.1 0 of 42.
- Half, double and five times the size at the same unit price changed 0 of 204 answers.
- 26 of 68 could not be compared (high masts outside the three districts with a tight group).
