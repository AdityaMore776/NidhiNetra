# The Cost Estimate Form: what to build

**Status:** spec, 3 Oct 2026 · **For:** whoever builds the form screens (task **T094**) and the Cost agent
(task **T097**) · **Plan:** [`docs/plans/T097-cost-agent-v3.md`](../plans/T097-cost-agent-v3.md)

**Source of truth:** every field below is defined once, in
[`apps/engine/drishti/reference/cost_form.yaml`](../../apps/engine/drishti/reference/cost_form.yaml). The web form gets
them from the API (`GET /api/v1/cost-form/catalog`), and the checks run on the server
(`POST /api/v1/cost-form/validate`). A test fails if this document misses a field, so the two stay in step.
Field limits (the allowed and the usual range of each number) live only in the YAML, never copied here.

---

## 1. What this form is for, in plain words

The MP recommends a work with an estimate of its cost. The **implementing agency** (the engineer who will build it) then
fills this form: exactly what will be built, how big, where, and what every part costs. DRISHTI's Cost agent checks the
estimate against what works of the same kind **and the same size** cost in the same place, and compares it with the MP's
amount. A question is raised only when the agency's estimate is too much for this size of work, and above what the MP
recommended.

Why a form: the old Cost agent saw only an amount and one sentence, so it had to guess the size. When we read its flags,
only **54 of 128** were real price questions, and works covering several sites were **0 of 48**
(`docs/trial/FINDINGS.md`, T053). With the size given as numbers, the guessing goes away.

**The one rule that matters most: a normal mistake must never become a flag.** A missing field, a typo, an extra zero,
the wrong unit: the form catches these on the agency's own screen and asks to fix or confirm them before it can be
submitted. The Cost agent only ever sees a complete, checked form.

## 2. Who fills it, and when

```
MP recommends a work, with an amount  ──►  Implementing agency fills THIS form  ──►  checks while filling
   (eSAKSHI; read-only here)                (size, site, every expense line)         (fix / confirm, never a flag)
                                                                                              │
                                    Officer sees the result  ◄──  Cost agent  ◄──────────────┘ submitted
                                    (only if it is too much       (same size, same place;
                                     for its size, and above       then compared with the
                                     the MP's amount)              MP's amount)
```

## 3. Rules for whoever builds the screens

1. **Render from the catalog.** Ask `GET /api/v1/cost-form/catalog?work_type=<code>` and draw what it returns. Do not
   hard-code fields; a new field in the YAML must appear without a web change.
2. **Show only what applies.** A field with `types` shows only for those work types; with `when`, only when the other
   field holds that value; `construction_only` fields are hidden for purchases; `linear_only` (the end point) only for
   roads, paths, drains, walls, embankments, pipelines and power lines; `goods_only` line fields only on goods lines.
3. **Units are fixed.** A number's unit comes with the field (`m`, `mm`, `m2`, …) and is printed next to the box. The
   person never picks the unit of a size field. (Expense lines are different: there the person picks the unit.)
4. **No guessed fields.** Sizes are measured (from the survey and drawings). Where a fact may truly be unknown, the
   choice list has `not_known`, and an unknown never causes a flag.
5. **"Other" always has a box.** Any choice that includes `other` shows a text box `<field>_other` when chosen. The work
   type can be `OTHER` with its own name and size; any material can be typed.
6. **Totals are worked out, never typed.** Line amounts are quantity × rate; subtotals, contingency, the grand total
   and the gap from the MP's amount are calculated live. The one typed total is the estimate document's own figure, to
   compare.
7. **Check as they type.** Call `POST /api/v1/cost-form/validate` with the whole form (debounced, and on each step's
   Next). Show each issue next to its field:
   - `fix` (red): must be corrected; Submit stays disabled.
   - `confirm` (amber): "looks like a typing mistake". Two buttons: correct it, or **"Yes, this is right"**, which adds
     the issue's `key` to the form's `confirmed` list.
   Submit is enabled only when the answer says `ready: true`.
8. **Never show a reference price.** The form shows the agency's own numbers and totals only: nothing about what other
   works cost.
9. **Save drafts.** An estimate takes time; keep the draft and let them come back.
10. **Works on a phone**, and every label can later carry Hindi (keep labels in one place).

## 4. Screens

A step-by-step form, a running total pinned at the side (at the bottom on a phone):

| Step | Screen | Sections |
|---|---|---|
| 1 | The recommendation | 5.0 (read-only) |
| 2 | Where | 5.1 (per site), constituency and land (5.2) |
| 3 | The work | 5.2 |
| 4 | Size and specification | 5.3 (per site) |
| 5 | Site conditions | 5.4 (per site) |
| 6 | Expenses | 5.5 (per site), 5.6 |
| 7 | Timing and totals | 5.7, 5.8 |
| 8 | Who prepared it, attachments | 5.9 |
| 9 | Declarations and submit | 5.10 |

A work with several sites (one recommendation, three villages) repeats steps 2, 4, 5 and 6 for each site, each with
its own size and lines.

An expense line, as one row:

```
Group      Item (type anything)        Recognised as    Qty    Unit  Rate (Rs)  Amount (Rs)  Rate from     SoR code
Materials  Cement OPC 43 grade         Cement ✓ change  1,125  bag   400        4,50,000     Market rate
Materials  Geotextile fabric           — none —         900    m2    60         54,000       Quotation
Labour     Unskilled labour            Unskilled labour 900    day   450        4,05,000     SoR           UP-LAB-1
```

"Recognised as" is suggested from what was typed. The person confirms it, picks another, or picks "none". Only a
confirmed material is compared material by material; a line marked "none" still counts in the total.

## 5. Every field

`id` is the stored name (also the JSON key). Everything is required unless it says otherwise.

### 5.0 The MP's recommendation (read-only, filled from eSAKSHI by work ID)

| id | What | Notes |
|---|---|---|
| `work_id` | eSAKSHI work ID | the form starts from a recommendation |
| `mp_amount` | MP's recommended amount (Rs) | what the agency's total is compared with |
| `recommended_type` | work type in the recommendation | |
| `recommended_description` | description in the recommendation | |
| `recommended_date` | recommended on | |

### 5.1 Where (per site)

| id | What | Notes |
|---|---|---|
| `district_lgd` | district | from the recommendation; a district officer sees only theirs |
| `block` | block / urban local body | |
| `gp_or_ward` | gram panchayat / ward | |
| `village` | village / locality | |
| `pin` | PIN code | 6 digits |
| `area_type` | rural / urban / peri-urban | |
| `lat`, `lon` | map pin | drop the pin on a map; must be inside India |
| `end_lat`, `end_lon` | end point | linear works only: the length is checked against the distance between the two ends |

### 5.2 The work (asked once)

| id | What | Notes |
|---|---|---|
| `inside_constituency` | inside the MP's constituency? | yes / no |
| `outside_reason` | why outside | when not inside |
| `land_owner` | who owns the land | construction only |
| `land_free` | the land costs nothing | must be yes: MPLADS cannot pay for land |
| `work_type` | type of work | the 33 types, **or `OTHER`** |
| `other_type_name` | type of work, written in | when `OTHER` |
| `nature` | new / continuation / extension / upgrade / reconstruction / purchase / installation | maintenance is not allowed under MPLADS, so it is not offered; **continuation** (T100) = finishing, or the next phase of, an earlier work |
| `existing_description` | what exists there now | for continuation, extension, upgrade, reconstruction |
| `existing_age_years` | its age | same |
| `existing_condition` | good / damaged / collapsed | same |
| `earlier_scheme` | last built or repaired under (MPLADS, MGNREGA, state scheme, …, not known) | for continuation, extension, upgrade, reconstruction |
| `earlier_work_id` | earlier work ID | **required for a continuation**; optional otherwise. The Duplicate check trusts a named link and never asks about it |
| `design_standard` | state type design / PMGSY / IRC / CPWD / own design / none | construction only |
| `description` | the work in your own words: what, exactly where (from X to Y), why this size, anything unusual | at least 25 words; for people to read: the agent never takes size from it |

### 5.3 Size and specification (per site; the fields of the chosen work type)

All measured, never guessed. The **priced by** column is the size the agent compares cost with.

| Family (work types) | Fields | Priced by |
|---|---|---|
| **road** (`ROAD_CC`, `ROAD_BT`) | `length_m`, `width_m`; for CC `concrete_grade`, `cc_thickness_mm`; for BT `bt_layer`, `bt_thickness_mm`; `base_type`, `base_thickness_mm` (unless no base); `existing_surface`; `raising_m`; `shoulder_width_m`; `side_drain_m`; `cross_drains_nos`; `kerb_m`; `signs_markings` | m² (length × width) |
| **path** (`FOOTPATH`, paver / interlocking) | `length_m`, `width_m`, `paver_thickness_mm`, `base_type`, `base_thickness_mm`, `edging_m` | m² |
| **drain** (`DRAIN`) | `length_m`, `drain_cover`, `drain_material`, `inner_width_m`, `inner_depth_m`, `wall_thickness_mm`, `cover_slabs_nos` (covered only), `outfall` | m |
| **wall** (`BOUNDARY_WALL`) | `length_m`, `height_m`, `foundation_depth_m`, `wall_thickness_mm`, `wall_material`, `gates_nos`, `gate_width_m` (if gates), `grill_m` | m² of wall face |
| **embankment** (`EMBANKMENT`) | `length_m`, `top_width_m`, `height_m`, `side_slope`, `pitching_m2` | m |
| **building** (`COMMUNITY_HALL`, `SCHOOL_BUILDING`, `HEALTH_BUILDING`, `LIBRARY`, `CREMATORIUM`) | `built_up_area_m2` (all floors), `floors_nos`, `structure`, `floor_height_m`, `roof`, `foundation`, `foundation_depth_m`, `rooms_nos`, `doors_nos`, `windows_nos`, `flooring`, `electrical_points_nos`, `water_sanitary`, `toilet_seats_nos`, `ramp`, `rainwater_harvesting`, `rooftop_solar_kw`; crematorium also `platforms_nos`, `chimney`, `fuel` | m² built-up |
| **toilet** (`TOILET_BLOCK`) | `seats_men_nos`, `seats_women_nos`, `seats_accessible_nos`, `built_up_area_m2`, `water_tank_l`, `disposal` | seats |
| **shelter** (`BUS_SHELTER`) | `length_m`, `depth_m`, `roof`, `structure`, `seats_nos` | m² |
| **crossing** (`CULVERT`, `BRIDGE`) | `structure_type`, `spans_nos`, `span_m`, `deck_width_m`, `pipe_dia_mm` and `pipe_rows_nos` (pipe only), `barrel_length_m`, `foundation`, `approach_m` | pipe: m of barrel × rows; others: m² of deck |
| **pond** (`POND`) | `water_area_m2`, `avg_depth_m`, `pond_nature`, `lining_m2`, `steps_nos`, `inlet_outlet_nos`, `fencing_m`, `soil_lead_m` | m³ dug |
| **check dam** (`CHECK_DAM`) | `length_m`, `height_m`, `dam_material` | m² |
| **borewell** (`BOREWELL`, hand pumps too) | `wells_nos`, `depth_m`, `bore_dia_mm`, `casing`, `casing_length_m`, `pump`, `pump_hp` (submersible), `rising_main_m`, `water_level_m`, `strata`, `platform` | per well |
| **tank** (`WATER_TANK`) | `tanks_nos`, `capacity_l`, `staging_m`, `tank_material`, `connecting_pipe_m` | kl |
| **pipeline** (`WATER_SUPPLY`) | `length_m`, `pipe_material`, `pipe_dia_mm`, `pressure_class`, `trench_depth_m`, `road_restoration_m`, `house_connections_nos`, `valves_nos`, `pump_hp` | m |
| **lights** (`STREET_LIGHT`) | `lights_nos`, `light_power`, `led_w`, `pole_height_m`, `pole_material`; solar: `panel_wp`, `battery_wh`, `battery_type`; grid: `cable_m`; `warranty_years` | per light |
| **mast** (`HIGH_MAST`) | `masts_nos`, `mast_height_m`, `lamps_per_mast`, `lamp_w`, `mast_power`, `cable_m` | per mast |
| **solar** (`SOLAR_PLANT`) | `capacity_kwp`, `mounting`, `grid_type`, `battery_kwh`, `inverter_kva` | kWp |
| **power line** (`ELECTRICITY`) | `length_m`, `voltage`, `poles_nos`, `transformers_nos`, `transformer_kva` (if transformers), `conductor` | m |
| **cctv** (`CCTV`) | `cameras_fixed_nos`, `cameras_ptz_nos`, `resolution_mp`, `recorder_channels`, `storage_tb`, `poles_nos`, `cable_m`, `control_room` | per camera |
| **ground** (`PLAYGROUND`) | `area_m2`, `levelling_m3`, `surface`, `fencing_m`, `flood_lights_nos` | m² |
| **goods** (`COMPUTER`, `FURNITURE`, `SPORTS_EQUIPMENT`, `MEDICAL_EQUIPMENT`, `VEHICLE`, `AMBULANCE`) | `receiving_institution`; the items themselves are goods lines (5.5) | per item |
| **other** (`OTHER`, a type not in the list) | `size_measure` (what you measured, e.g. "floor area"), `size_value`, `size_unit`, `specification` (10+ words) | the unit given; the agent has no reference for it, so it only compares the total with the MP's amount |

### 5.4 Site conditions (per site, construction only)

These can only **explain** a cost or **widen** what is allowed. They never cause a flag. Distances to material sources
are optional.

| id | What |
|---|---|
| `terrain` | plain / rolling / hilly / steep hilly / desert / coastal / floodplain / island |
| `soil` | normal / black cotton / sandy / rocky / waterlogged / not known |
| `groundwater_shallow` | water close below ground: yes / no / not known |
| `access` | truck / tractor only / head load only |
| `road_distance_m` | distance from the nearest motorable road |
| `sand_source_km`, `aggregate_source_km`, `brick_source_km`, `cement_depot_km` | distances to material sources (optional) |
| `site_water`, `site_power` | water / electricity on site for the work |
| `lost_months` | months when work cannot happen (optional) |
| `urban_constraints` | night work only / traffic diversion / narrow lane / heritage zone (optional) |
| `demolition_m3`, `utility_shifting_nos`, `trees_nos` | old structure to demolish, poles or pipes to shift, trees to cut (0 if none) |

Filled automatically from the map pin later (T096), never typed: altitude, hill / North-East / island / Left-Wing
Extremism / border area, seismic zone.

### 5.5 Expense lines (per site)

**Groups** (each line belongs to one): `preparatory` (survey, design, soil test, clearing, demolition, utility
shifting, temporary works, permits) · `materials` · `labour` · `machinery` · `carriage` · `goods` · `finishing` (MPLADS
plaque, safety signs, ramps, connections) · `quality` (testing) · `supervision` (only where the state allows it) ·
`other` (each named and explained).

**Every line:**

| id | What | Notes |
|---|---|---|
| `item` | the item, typed freely | e.g. "Cement OPC 43 grade", "sariya 12 mm", "Geotextile fabric" |
| `material_id` | recognised as | suggested from the item; the person confirms, changes or sets "none" |
| `quantity` | quantity | |
| `unit` | unit | any unit of the catalog (bag, kg, t, m3, cft, brass, nos, m, m2, day, hour, …); `ls` for a lump sum |
| `rate` | rate (Rs per unit) | |
| `amount` | amount (Rs) | worked out as quantity × rate; typed only for a lump sum |
| `basis` | where the rate comes from | Schedule of Rates / GeM / quotation / market rate / earlier work / other |
| `sor_code` | Schedule of Rates item code | when the basis is the Schedule of Rates |
| `spec` | specification | goods lines only, required |
| `gem_id` | GeM product ID | goods lines; otherwise attach 3 quotations |
| `quotations_nos` | quotations attached | goods lines |

**Materials the form suggests** (anything else can be typed). A typed item is matched by whole words, in English and
the Hindi words used on estimates (सीमेंट, सरिया, बालू, गिट्टी, ईंट, …):
`cement`, `steel_rebar`, `structural_steel`, `sand`, `aggregate`, `brick`, `paver_block`, `rmc` (ready-mix concrete),
`bitumen`, `granular_base` (GSB / WBM / moorum), `earth_fill`, `pipe`, `cable`, `led_luminaire`, `solar_panel`,
`battery`, `pole`, `tiles`, `paint`, `door_window`, `labour_skilled`, `labour_unskilled`.

### 5.6 Charges

| id | What | Notes |
|---|---|---|
| `contingency_percent` | contingency (safety margin), % of the lines | 0 if none; the amount is worked out |
| `escalation_percent` | price rise reserve, % | only for works longer than 12 months (optional) |
| `gst_percent` | GST rate | |
| `gst_amount` | GST amount (Rs) | checked against the rate (confirm, since some estimates charge it on part only) |
| `labour_cess_amount` | building workers' welfare cess (Rs) | 0 if none |
| `royalty_amount` | royalty on sand / stone, mineral fund (Rs) | 0 if none |
| `other_fees_amount` | permission and other statutory fees (Rs) | 0 if none |

### 5.7 Timing

| id | What | Notes |
|---|---|---|
| `estimate_month` | prices are as of (YYYY-MM) | not in the future; older than 18 months asks to confirm |
| `sor_edition` | Schedule of Rates used (state, year) | when any line uses it |
| `start_month` | expected start (YYYY-MM) | |
| `duration_months` | expected duration (months) | |

### 5.8 Totals and the MP's amount

| id | What | Notes |
|---|---|---|
| `total_as_per_document` | grand total in the estimate document (Rs) | must match the lines and charges (within 0.5%) |
| `reason_differs_from_mp` | why the total differs from the MP's amount | required when they differ by more than 10%; the officer sees it |

### 5.9 Who prepared it, and attachments

| id | What | Notes |
|---|---|---|
| `prepared_by_role` | agency engineer / consultant / other | |
| `prepared_by_designation`, `checked_by_designation` | designations | **kept private**, never shown publicly (no names) |
| `estimate_pdf` | the detailed estimate | |
| `drawings` | drawings or layout sketch | construction only |
| `site_photo_before` | photo of the site before work, with location | construction only |
| `land_noc` | land NOC / ownership paper | construction only |

### 5.9b Earlier works at this site (T100; answered once per work listed)

`GET /api/v1/cost-forms/{work_id}` lists, as `earlier_candidates`, the sanctioned works of the district that the
Duplicate check finds **at this site** (another form's map pin within 50 m, same kind of asset) or **in the same words**
(the same place named, descriptions 90%+ alike). Show each one (work ID, description, amount, status) and ask:

| id | What | Notes |
|---|---|---|
| `earlier_work` | the sanctioned work's ID | filled in from the list, read-only |
| `answer` | this work is: **the same work** / **continues it** / **a different work** | "the same work" blocks Submit: it is already sanctioned. "Continues it" needs the nature (continuation, extension, upgrade, reconstruction) and `earlier_work_id` set to it |
| `difference` | what differs: another site, landmark, floor or side | when "a different work"; at least 4 words |

Each answer is one row of `earlier_works`. Why this is asked: from the words of two records alone, a repeat is right
only about 2 times in 3 (`docs/plans/T099-T100-simple-and-certain.md`). The agency knows. Its answer, and the map
pins, make the Duplicate check certain.

### 5.10 Declarations (all must be ticked)

| id | What |
|---|---|
| `decl_no_land_cost` | no line pays for land or compensation |
| `decl_no_maintenance` | no line pays for maintenance or running costs (salaries, fuel, consumables) beyond the warranty |
| `decl_not_funded_elsewhere` | not already funded by another scheme (or the joint funding is stated) |
| `decl_actuals` | actual costs will be reported against these same lines at completion |

### 5.11 At completion (later)

The same lines, filled with the actual quantity and amount, and a reason for any line that went over. This catches
overruns and gives the measured data the agent's allowed ranges are set from (T098).

## 6. Checks while filling (never flags)

`fix` blocks Submit; `confirm` asks "correct it, or confirm it is right". Each issue has a `code`, a `field` path and a
`key` (`<code>:<field>`); a confirmed key goes into the form's `confirmed` list.

| code | Level | When |
|---|---|---|
| `required` | fix | a required field is empty |
| `not_a_number`, `not_a_choice`, `not_yes_no`, `not_text`, `bad_month`, `bad_date`, `bad_pin`, `no_file` | fix | the wrong kind of answer |
| `impossible` | fix | a number outside its possible range (a road 37 m wide) |
| `unusual` | confirm | a number outside its usual range (a road 14 m wide) |
| `other_unnamed` | fix | "other" chosen with nothing written |
| `too_short` | fix | a description below its word count |
| `gps_outside_india` | fix | a map point outside India |
| `shorter_than_ends` | fix | a linear work shorter than the straight distance between its two ends |
| `much_longer_than_ends` | confirm | more than 5 times that distance |
| `line_arithmetic` | fix | amount is not quantity × rate (an extra zero) |
| `line_incomplete` | fix | an amount without quantity and rate, and not a lump sum |
| `unit_for_material` | confirm | a unit unusual for the recognised material (cement in metres) |
| `rate_typo` | confirm | a rate far outside any real price for that material: a typing guard only, never a price judgment |
| `maybe_not_payable` | confirm | the item reads like land, maintenance or running costs |
| `goods_price_basis` | fix | a goods line with neither a GeM product ID nor 3 quotations |
| `duplicate_line` | confirm | the same item twice |
| `no_lines`, `no_goods_lines`, `no_site`, `no_group` | fix | lines or sites missing |
| `lump_sums` | confirm | more than 20% of the lines are lump sums |
| `other_share` | confirm | more than 10% is under "anything else" |
| `gst_rate`, `gst_amount` | confirm | an unusual GST rate, or an amount that does not match it |
| `escalation_short_work` | fix | a price rise reserve on a work of 12 months or less |
| `future_estimate` | fix | prices from a future month |
| `old_prices`, `start_before_estimate` | confirm | prices over 18 months old; a start before the price month |
| `total_mismatch` | fix | the lines and charges do not add up to the estimate document's total |
| `land_not_free`, `declaration` | fix | land not free; a declaration not ticked |
| `continuation_needs_id` | fix | a continuation with no earlier work ID |
| `earlier_unanswered` | fix | a sanctioned work in `earlier_candidates` not answered |
| `same_as_sanctioned` | fix | the agency says it is the same as a sanctioned work: it cannot be estimated again |
| `continues_mismatch` | fix | "continues it" while the nature or the earlier work ID says otherwise |

## 7. The JSON the form sends

```json
{
  "recommendation": {"work_id": "WS/MP.../2026-2027/...", "mp_amount": 2200000, "recommended_type": "ROAD_CC",
                     "recommended_description": "...", "recommended_date": "2026-08-01"},
  "work": {"work_type": "ROAD_CC", "nature": "new", "inside_constituency": true, "land_owner": "panchayat",
           "land_free": true, "design_standard": "pmgsy", "description": "..."},
  "sites": [{
    "location": {"district_lgd": "...", "block": "...", "gp_or_ward": "...", "village": "...", "pin": "222001",
                 "area_type": "rural", "lat": 25.75, "lon": 82.69, "end_lat": 25.752, "end_lon": 82.69},
    "size": {"length_m": 250, "width_m": 3.75, "concrete_grade": "M20", "cc_thickness_mm": 150, "...": "..."},
    "site_conditions": {"terrain": "plain", "soil": "normal", "...": "..."},
    "lines": [{"group": "materials", "item": "Cement OPC 43 grade", "material_id": "cement", "quantity": 1125,
               "unit": "bag", "rate": 400, "basis": "market_rate"},
              {"group": "finishing", "item": "MPLADS plaque", "unit": "ls", "amount": 15000, "basis": "market_rate"}]
  }],
  "charges": {"contingency_percent": 3, "gst_percent": 18, "gst_amount": 347810.4, "labour_cess_amount": 19323,
              "royalty_amount": 0, "other_fees_amount": 0},
  "timing": {"estimate_month": "2026-09", "sor_edition": "UP PWD SoR 2025-26", "start_month": "2026-11",
             "duration_months": 6},
  "totals": {"total_as_per_document": 2299413},
  "prepared": {"prepared_by_role": "ia_engineer", "prepared_by_designation": "...", "checked_by_designation": "...",
               "estimate_pdf": "<file id>", "drawings": "<file id>", "site_photo_before": "<file id>", "land_noc": "<file id>"},
  "declarations": {"decl_no_land_cost": true, "decl_no_maintenance": true, "decl_not_funded_elsewhere": true,
                   "decl_actuals": true},
  "confirmed": ["unusual:sites[0].size.width_m"],
  "earlier_works": [{"earlier_work": "WS/MP.../2024-2025/...", "answer": "different",
                     "difference": "the other road is in the SC colony, this one near the school"}]
}
```

A complete worked example is `road_form()` in `apps/engine/tests/cost_form/test_cost_form.py`.

## 8. API

| Route | Does | Built in |
|---|---|---|
| `GET /api/v1/cost-form/catalog?work_type=ROAD_CC` | every section, the size fields of that type, line groups, suggested materials, units | T093 (done) |
| `POST /api/v1/cost-form/validate` | body: the form JSON → `{ready, issues[], computed{lines_total, contingency_amount, escalation_amount, charges_total, grand_total, mp_gap, sites[{pricing, lines_total, lines[]}]}}`; any body gets an answer, never an error | T093 (done) |
| `POST /api/v1/cost-forms` | body `{work_id, form, submit}`: saves a draft, or submits when `ready` (else 422 with the issues). The recommendation section is filled from the work's record, never from the body. A submitted form is read-only (409), and submitting re-assesses the work at once | T099 (done) |
| `GET /api/v1/cost-forms/{work_id}` | the saved form (or none), its status, and `earlier_candidates`: the sanctioned works the agency must answer about (§5.9b) | T099 (done) |

All need a signed-in user; a district officer only reaches their district's works.

## 9. What the Cost agent does with it (short)

It compares the agency's estimate with what works **of the same kind and size** cost **in the same district**,
allowing the normal percentage above or below the average that real works show, then compares it with the MP's
amount. It raises a question only when the estimate is too much for its size **and** above the MP's amount. It stays
silent when it has no reference to compare with. It never shows the reference while the form is filled. Full detail:
[`docs/plans/T097-cost-agent-v3.md`](../plans/T097-cost-agent-v3.md).

## 10. Checklist for building the screens (T094)

- [ ] steps 1–9 render from `GET /cost-form/catalog`; conditional fields appear and disappear correctly
- [ ] several sites: add / remove a site; each has its own location, size, conditions and lines
- [ ] expense table: add / remove lines, type any item, "Recognised as" suggestion with change / none, lump sums
- [ ] live totals and the gap from the MP's amount; never a reference price
- [ ] `fix` and `confirm` shown at their fields; "Yes, this is right" stores the key; Submit only when `ready`
- [ ] drafts saved; a submitted form is read-only
- [ ] the earlier works listed by `GET /cost-forms/{work_id}` shown with their three answers (§5.9b)
- [ ] works on a phone; `tsc`, `lint`, `build` pass; screenshots in the PR
