# Loopholes: every known way past the agents, and today's result

Every way found so far to get a fraud past NidhiNetra's agents, every bypass, and every situation where an agent cannot work, in one list, each run against the current agents. **When a new loophole is found, add it at once** (a labelled case in `data/eval/<agent>/`, a probe in `data/trial/agent_robustness_loop.py`, or an entry in `data/eval/loopholes/manual.py`) and run `data/eval/loopholes/check.py`, which rewrites this file (owner, 20 Oct 2026; T171).

**Last run:** 21 Oct 2026, on the research export (dashboard tables not on this PC). **242 entries.**

| Today's result | Entries |
|---|---|
| Caught: asked | 147 |
| Caught: "check this" | 40 |
| Couldn't check, and says so | 24 |
| Fixed (guarded by a test) | 7 |
| Made visible (not blocked) | 2 |
| Known limit | 16 |
| Measured: not fooled | 2 |
| OPEN: not caught | 4 |

**Caught or said so:** 220 of 242. **Known limits:** 16. **Made visible:** 2. **Being measured:** 0. **Open or missed:** 4.

How to read a result: *asked* = the agent raises a question (the work goes to the review queue); *check this* = a lighter follow-up; *another agent* = this agent cannot see it, but the four together still queue it; *couldn't check, and says so* = broken or missing data reads as "couldn't check", never as a clean chit; *known limit* = accepted by the owner's design or until data not on hand exists, listed so nobody mistakes it for coverage; *measured: not fooled* = tried on real checks, and the agent's answers did not change. A case counts as caught only when it is caught in every test district it runs in.

## Open and missed: not caught today (4)

### Duplicate Work

| Loophole | How it works | Found | Today | Detail |
|---|---|---|---|---|
| The same building filed again under another work type ("Other") | Duplicate Work compares a site with works of the same kind. A hall filed again as "Other", pinned 10 m from the finished hall, is compared with nothing. | T160, 9 Oct 2026, `M-DUP-1` | **OPEN: not caught** | Not asked before sanction. Site Progress's SAME_PLACE_AS_ANOTHER_WORK catches it once both works have site videos. Comparing "Other" with buildings at one pin could ask about honest pairs (a water tank beside a school): needs a measurement on real forms. Today: Duplicate Work: fits, fits (sparse, dense). |

### Site Progress

| Loophole | How it works | Found | Today | Detail |
|---|---|---|---|---|
| The before and after photos in the wrong order | A finished building filmed first and the bare site later, claimed as progress. | T168, 21 Oct 2026, `M-SITE-5` | **OPEN: not caught** | Wrongly says "shown" 8.8% [5.3, 12.7] (clean 1.9%). Measured on NidhiLens alone; the place and same-spot video checks were not part of this run. Guard: `data/trial/results/t168_nidhilens.txt`. |
| A "done" mark that is not writing (a big tick, a symbol) | The text finder greys only writing; a painted tick or a picture of a finished building held to the camera stays in the photo. | T172, 21 Oct 2026, `M-SITE-7` | **OPEN: not caught** | Not measured. No live score today (NidhiLens is behind a switch, M-SITE-1). |

### Inspection Planner

| Loophole | How it works | Found | Today | Detail |
|---|---|---|---|---|
| A work whose description names no place the planner can find | It is placed at the district's start point. Where no queue work names a village or block (Vijayapura, Belagavi), a day's plan is all at one point: 12 stops, 0 km. | T170 start-to-end check, 20 Oct 2026, `M-PLAN-1` | **OPEN: not caught** | Each stop is marked "District only"; owner to decide whether the planner opens on a district whose works can be placed. |

## Known limits (16)

### Time & Rules

| Loophole | How it works | Found | Today | Detail |
|---|---|---|---|---|
| A Rs 6 lakh road (no form) recorded complete 9 days after its sanction. | Two days past R14's 7-day line: as unbelievable for a road. LIMIT (after the first run): R14's line was measured on the dashboard's sanction dates (25 of 25 at 0-7 days); widening it needs the same measurement at 8-21 days, and no table with sanction dates is on this PC. With a form the comfort window catches it (T-F1). | T168 eval, `T-V6-nine-days-after-sanction` | **Known limit** | sparse: edge LOW -; dense: edge LOW - |
| Real works without a sanction date | The research export (what the live database holds) has no sanction dates; the rules that count from the sanction cannot run on those records. | T164, 9 Oct 2026, `M-TIME-1` | **Known limit** | Couldn't check for those rules; works with a form carry their own dates. Needs the eSAKSHI dashboard tables (sanction dates) loaded. |

### Site Progress

| Loophole | How it works | Found | Today | Detail |
|---|---|---|---|---|
| GPS faked inside the site, views elsewhere |  | T135-T164 loop, `GPS faked inside the site, views elsewhere` | **Known limit** | nothing: one video with one proof (the views) is a note by design; two such videos in a row are asked (SITE_VIDEOS_UNUSABLE, round 6) |
| A false claim on genuine site videos, on the live site | Reading the agency's claim against its videos needs NidhiLens (GPU); on the live site it is behind a switch, notes only until the field trial. | T159, 9 Oct 2026, `M-SITE-1` | **Known limit** | Video checks that need no model (reuse, place, GPS, dates, sealing) run; the claim reading does not, live. |

### Cost

| Loophole | How it works | Found | Today | Detail |
|---|---|---|---|---|
| a bigger size claimed everywhere (field and scope both 7 m) |  | T135-T164 loop, `a bigger size claimed everywhere (field and scope both 7 m)` | **Known limit** | nothing: a size claimed the same way everywhere is the agency's word; the site videos and the officer's visit check it, not the estimate |
| a composite line (labour inside) declared 'no labour' |  | T135-T164 loop, `a composite line (labour inside) declared 'no labour'` | **Known limit** | nothing: whether a schedule item's rate includes labour is the agency's own declaration until the state's Schedule of Rates is loaded with its item codes (T096) |
| every agency in the district pads 22% together |  | T135-T164 loop, `every agency in the district pads 22% together` | **Known limit** | nothing: when every agency raises its rates together, the rest of the state's forms tell it (T167, DISTRICT_RATES_ABOVE_STATE); this world has no forms from other districts, so only the state's Schedule of Rates (T096) could cap it |
| padded items in units that do not fit them, with a reason given |  | T135-T164 loop, `padded items in units that do not fit them, with a reason gi` | **Known limit** | nothing: a line the agency answered for in another unit looks like an honest schedule item (brick masonry per m3) until the state's Schedule of Rates is loaded with its item codes (T096); the coverage note says what was not priced |
| A work without the cost estimate form | Cost judges only the agency's form (owner, 3 Oct): an eSAKSHI record alone is never price-judged, so a work filed without the form is not priced. | T099, 3 Oct 2026, `M-COST-1` | **Known limit** | Cost says it could not check (no form); the form is required before sanction. |
| Padding where the district has too few recent forms | A material is priced only when enough recent forms from several agencies agree; otherwise Cost switches that price off and records the gap. A padded estimate in a district with too few forms of its kind goes unpriced. | T135, 5 Oct 2026, `M-COST-2` | **Known limit** | Not priced; the gap is listed (GET /cost/data-gaps) so the data can be collected; the state's forms stand in where there are enough (10% more leniently). Today: Cost: NOT_ASSESSABLE: Could not compare this estimate with anything yet: Price of the work: no reference for this kind of work yet. Not priced. |
| A trade's day rate below twice what others pay, and crew sizes | By the owner's rule (T141) wages within twice a trade's rate are the agency's call. Person-days far above other agencies' crews are checked since T167 (LABOUR_DAYS_ABOVE_PEERS). | T141, 6 Oct 2026, `M-COST-3` | **Known limit** | A rate under 2x is not asked; ghost person-days are checked. |
| A trade not on the list, declared at a high grade | Judged against its declared grade's pool (2.5x room): an "Other" trade declared highly skilled at 2.2x an operator's rate is not asked. | T141, 6 Oct 2026, `M-COST-4` | **Known limit** | Not asked. |
| A composite item declared "no labour", or a material in another unit with a reason | Without the state's Schedule of Rates (T096, not loaded) these read as honest schedule items. | T141, 6 Oct 2026, `M-COST-5` | **Known limit** | Not asked until the SoR is loaded. |
| The price of the whole work per metre | Real works of a kind vary too much in price per metre (UP CC roads: the middle 80% runs to +58%), so the whole-work price check cannot run. | T164, 9 Oct 2026, `M-COST-6` | **Known limit** | Said as a limitation on every road; the line-by-line check still runs. |

### Duplicate Work

| Loophole | How it works | Found | Today | Detail |
|---|---|---|---|---|
| A repeat found only by its words | A work with no form (no map pin) whose description matches an earlier work's: by the owner's rule (3 Oct) look-alikes by words are notes, never questions. | T099-T100, 3 Oct 2026, `M-DUP-2` | **Known limit** | A note on the work's page; the form's map pin is what asks. |
| Pieces of one job at 90-96% of a limit, without part numbers | Filed as different-sounding works just under a limit. Numbered parts are asked (SPLIT_NEAR_LIMIT); unnumbered ones are not: on the real works 1 of 14 such groups was one job. | T168, 20 Oct 2026, `M-DUP-3` | **Known limit** | Not asked (measured, results/t168_split_eye.json); the strict split (96-100%) still asks. Guard: `data/trial/t168_split_measure.py`. |

## Made visible, being measured (2)

### Case status

| Loophole | How it works | Found | Today | Detail |
|---|---|---|---|---|
| An office closes cases without a visit to bury them | "Read by the office" -> "Closed" needs no site visit. | T060, 20 Oct 2026, `M-SYS-1` | **Made visible (not blocked)** | A reason is required, the move is in the audit log, and the daily digest names every close without a visit. Guard: `tests/api/test_alerts.py::test_a_verdict_or_a_close_without_a_visit_needs_a_note`. |
| Someone with database access edits or deletes a past audit entry |  | T060, 20 Oct 2026, `M-SYS-2` | **Made visible (not blocked)** | The database refuses UPDATE, DELETE and TRUNCATE on the log; with the guard switched off, the hash chain check names the first broken entry. Guard: `tests/api/test_alerts.py::test_the_chain_check_finds_an_entry_changed_or_removed_behind_the_triggers`. |

## Caught, fixed or said so (220)

### Duplicate Work

| Loophole | How it works | Found | Today | Detail |
|---|---|---|---|---|
| A hall finished 16 months ago, filed as a 'new asset' 30 m from it. | The pin says one site, whatever the form calls it. | T168 eval, `DH-F4-rebuild-called-new` | **Caught: asked** | sparse: ask MEDIUM SANCTIONED_WORK_AT_THIS_SITE; dense: ask MEDIUM SANCTIONED_WORK_AT_THIS_SITE |
| Lights 15 m from last year's lights, filed by another agency. | Inside one spot (20 m), not one programme. | T168 eval, `DH-F5-light-15m-other-agency` | **Caught: asked** | sparse: ask MEDIUM SANCTIONED_WORK_AT_THIS_SITE; dense: ask MEDIUM SANCTIONED_WORK_AT_THIS_SITE |
| The old road filed again with its two ends swapped. | The same line, walked the other way. | T168 eval, `DH-F6-road-reversed` | **Caught: asked** | sparse: ask MEDIUM SANCTIONED_WORK_AT_THIS_SITE; dense: ask MEDIUM SANCTIONED_WORK_AT_THIS_SITE |
| A hall pinned 45 m from a hall still being built, with its videos filmed there. | Inside the one-site line. | T168 eval, `DH-F7-hall-45m-filmed` | **Caught: asked** | sparse: ask MEDIUM SANCTIONED_WORK_AT_THIS_SITE; dense: ask MEDIUM SANCTIONED_WORK_AT_THIS_SITE |
| A 'new' road pinned 20 m from a road finished last year; the form does not mention it. | The same road paid for twice. | T168 eval, `D-F1-road-on-old-road` | **Caught: asked** | sparse: ask MEDIUM SANCTIONED_WORK_AT_THIS_SITE; dense: ask MEDIUM SANCTIONED_WORK_AT_THIS_SITE |
| A hall declared rebuilt 16 months after the old one was finished. | A new hall does not need rebuilding this soon. | T168 eval, `D-F2-rebuild-16m` | **Caught: asked** | sparse: ask MEDIUM REBUILT_SOON_AFTER_COMPLETION; dense: ask MEDIUM REBUILT_SOON_AFTER_COMPLETION |
| One lane filed as three parts, each 98.6-99.6% of Rs 5 lakh. | The strictest split. | T168 eval, `D-F3-split-3-parts` | **Caught: asked** | sparse: ask HIGH SPLIT_JUST_UNDER_LIMIT; dense: ask HIGH SPLIT_JUST_UNDER_LIMIT |
| The same hall filed again by another agency, its pin 10 m from the sanctioned one. | One building, two works. | T168 eval, `D-F4-hall-refiled` | **Caught: asked** | sparse: ask MEDIUM SANCTIONED_WORK_AT_THIS_SITE; dense: ask MEDIUM SANCTIONED_WORK_AT_THIS_SITE |
| A new light 5 m from a light finished last year (not one programme). | One pole, two works. | T168 eval, `D-F5-light-on-light` | **Caught: asked** | sparse: ask MEDIUM SANCTIONED_WORK_AT_THIS_SITE; dense: ask MEDIUM SANCTIONED_WORK_AT_THIS_SITE |
| The pin typed 70 m off an old hall; two site videos filmed at the old hall. | T160: where the videos were filmed shows the real site. | T168 eval, `D-V1-pin-70m-filmed-old` | **Caught: asked** | sparse: ask MEDIUM SANCTIONED_WORK_WHERE_FILMED; dense: ask MEDIUM SANCTIONED_WORK_WHERE_FILMED |
| A hall finished 16 months ago, filed again as an 'upgrade' of itself, same size. | T135: a continuation on the old work's own ground with its size is a rebuild. | T168 eval, `D-V3-rebuild-called-upgrade` | **Caught: asked** | sparse: ask MEDIUM REBUILT_SOON_AFTER_COMPLETION; dense: ask MEDIUM REBUILT_SOON_AFTER_COMPLETION |
| The old 300 m road filed again as 330 m from the same start. | Mostly on the old road's line: the same ground. | T168 eval, `D-V6-road-longer` | **Caught: asked** | sparse: ask MEDIUM SANCTIONED_WORK_AT_THIS_SITE; dense: ask MEDIUM SANCTIONED_WORK_AT_THIS_SITE |
| Pinned on an old road, the form names another work ID that is not on record. | Naming a work that does not exist must not excuse the one at the pin. | T168 eval, `D-V7-names-fake-work` | **Caught: asked** | sparse: ask MEDIUM SANCTIONED_WORK_AT_THIS_SITE; dense: ask MEDIUM SANCTIONED_WORK_AT_THIS_SITE |
| Declared an extension of a road still being built, but lying on its ground. | T135: named, on the earlier work's own ground, not finished: still asked. | T168 eval, `D-V8-continues-unfinished` | **Caught: asked** | sparse: ask MEDIUM SANCTIONED_WORK_AT_THIS_SITE; dense: ask MEDIUM SANCTIONED_WORK_AT_THIS_SITE |
| a 'new' hall pinned 60 m from the old (just past the 50 m line) |  | T135-T164 loop, `a 'new' hall pinned 60 m from the old (just past the 50 m li` | **Caught: asked** | SAME_BUILDING_NEAR; a pin past 50 m is another site by rule; the same words and size make it 'check this' (T168), and the first site video (the hall already standing) settles it |
| a hall filed twice on the same day at one pin |  | T135-T164 loop, `a hall filed twice on the same day at one pin` | **Caught: asked** | the same-day exception is for a programme of lights only: SANCTIONED_WORK_AT_THIS_SITE (ASSESSED) |
| a hand pump filed again at the same spot |  | T135-T164 loop, `a hand pump filed again at the same spot` | **Caught: asked** | one spot, GPS 6 m apart: SANCTIONED_WORK_AT_THIS_SITE (ASSESSED) |
| a lane filed again, its ends re-pinned 8 m off |  | T135-T164 loop, `a lane filed again, its ends re-pinned 8 m off` | **Caught: asked** | the same lane, both ends near and on its line: SANCTIONED_WORK_AT_THIS_SITE (ASSESSED) |
| a map pin at (0, 0), or latitude and longitude swapped |  | T135-T164 loop, `a map pin at (0, 0), or latitude and longitude swapped` | **Caught: asked** | zero: nothing, says the pin is wrong: True; swapped: nothing, says the pin is wrong: True |
| a street light filed again at the same spot a year later |  | T135-T164 loop, `a street light filed again at the same spot a year later` | **Caught: asked** | one spot, GPS 6 m apart: SANCTIONED_WORK_AT_THIS_SITE (ASSESSED) |
| computers bought again for the same school |  | T135-T164 loop, `computers bought again for the same school` | **Caught: asked** | the same purchase again: SANCTIONED_WORK_AT_THIS_SITE (ASSESSED) |
| pins moved 60 m off the real site |  | T135-T164 loop, `pins moved 60 m off the real site` | **Caught: asked** | ['SANCTIONED_WORK_AT_THIS_SITE']: two pins 50 m apart are one site by rule; a pin off the real site is for Site Progress to see (the videos are filmed where the work is) |
| split into pieces each 95% of the limit (under the 96% rule) |  | T135-T164 loop, `split into pieces each 95% of the limit (under the 96% rule)` | **Caught: asked** | ['SPLIT_NEAR_LIMIT']: the 96-100% rule read 12 of 14 right; looser splits read 18 of 32 (T100), so they stay unasked |
| split with each piece described in other words |  | T135-T164 loop, `split with each piece described in other words` | **Caught: asked** | ['SPLIT_JUST_UNDER_LIMIT']: the pieces still meet end to end by their pins |
| split with the checked piece called a paver road / 'Other' |  | T135-T164 loop, `split with the checked piece called a paver road / 'Other'` | **Caught: asked** | missed: none (pieces end to end by pin) |
| the hall rebuild declared 'new' (no link) at the same pin |  | T135-T164 loop, `the hall rebuild declared 'new' (no link) at the same pin` | **Caught: asked** | a 'new' hall 10 m from the old: SANCTIONED_WORK_AT_THIS_SITE (ASSESSED) |
| the hall rebuild declared a 'repair / renovation' instead |  | T135-T164 loop, `the hall rebuild declared a 'repair / renovation' instead` | **Caught: asked** | renovation 16 months on: REBUILT_SOON_AFTER_COMPLETION (ASSESSED) |
| the old road re-filed 100 m longer and declared a 'continuation' |  | T135-T164 loop, `the old road re-filed 100 m longer and declared a 'continuat` | **Caught: asked** | ['REBUILT_SOON_AFTER_COMPLETION'] (the old 300 m inside the new 400 m) |
| the old road re-filed 100 m longer at one end |  | T135-T164 loop, `the old road re-filed 100 m longer at one end` | **Caught: asked** | 300 m of old road + 100 m: SANCTIONED_WORK_AT_THIS_SITE (ASSESSED) |
| the rebuild with no nature declared, the old hall only named nearby |  | T135-T164 loop, `the rebuild with no nature declared, the old hall only named` | **Caught: asked** | named nearby only: REBUILT_SOON_AFTER_COMPLETION (ASSESSED) |
| the road's far end left out of the form |  | T135-T164 loop, `the road's far end left out of the form` | **Caught: asked** | nothing (ASSESSED); says an end is missing: True |
| the same stretch declared a 'continuation' of the old road |  | T135-T164 loop, `the same stretch declared a 'continuation' of the old road` | **Caught: asked** | ['REBUILT_SOON_AFTER_COMPLETION'] (old road completed 11 months ago, same 300 m) |
| The old hall filed again, same words and size, its pin typed 120 m off. | Inside the 150 m near line: at least 'check this'. | T168 eval, `DH-F1-hall-120m-same` | **Caught: "check this"** | sparse: check MEDIUM SAME_BUILDING_NEAR; dense: check MEDIUM SAME_BUILDING_NEAR |
| One lane in four numbered parts at 91.6-92.4% of Rs 5 lakh, within 10 days. | Numbered parts just under a limit. | T168 eval, `DH-F2-four-parts-92pct` | **Caught: "check this"** | sparse: check HIGH SPLIT_NEAR_LIMIT; dense: check HIGH SPLIT_NEAR_LIMIT |
| Two pieces of one lane at 99% of Rs 5 lakh, 85 days apart. | The same job spread over months. | T168 eval, `DH-F3-split-85-days` | **Caught: "check this"** | sparse: check HIGH SPLIT_NEAR_LIMIT; dense: check HIGH SPLIT_NEAR_LIMIT |
| The same hall re-filed with its pin typed 70 m off, before sanction (no video yet). | Only the pin is known; a same-kind building 70 m away, same size, not named: at least 'check this' (the owner's rule: a fraud is never an edge case). | T168 eval, `D-V2-pin-70m-before-sanction` | **Caught: "check this"** | sparse: check MEDIUM SAME_BUILDING_NEAR; dense: check MEDIUM SAME_BUILDING_NEAR |
| Three parts of one lane at 94.6-95.4% of Rs 5 lakh: just below the strictest line. | Moved 1% to dodge the 96% line: at least 'check this'. | T168 eval, `D-V4-split-95pct` | **Caught: "check this"** | sparse: check HIGH SPLIT_NEAR_LIMIT; dense: check HIGH SPLIT_NEAR_LIMIT |
| Three parts at 98-99.6% of Rs 5 lakh, filed 35 days apart. | Spread past the 30-day window to dodge it: at least 'check this'. | T168 eval, `D-V5-split-35-days` | **Caught: "check this"** | sparse: check HIGH SPLIT_NEAR_LIMIT; dense: check HIGH SPLIT_NEAR_LIMIT |
| A form whose map pin is 0, 0, on an old road's site. | A pin that cannot be compared is not a clean chit. | T168 eval, `DH-B1-pin-zero` | **Couldn't check, and says so** | sparse: na LOW -; dense: na LOW - |
| A record with no district. | No district, nothing to compare with. | T168 eval, `D-B1-no-district` | **Couldn't check, and says so** | sparse: na LOW -; dense: na LOW - |
| A record with no dates and no description, no form. | Nothing to compare. | T168 eval, `D-B2-no-date-no-words` | **Couldn't check, and says so** | sparse: na LOW -; dense: na LOW - |
| A form with its map pin left blank, at the site of an old road. | Without the pin, words alone are right 2 in 3: a note at most, never 'nothing here'. | T168 eval, `D-B3-form-no-pin` | **Couldn't check, and says so** | sparse: na LOW -; dense: na LOW - |
| On an old road, the form's latitude and longitude swapped (a pin outside India). | A pin that cannot be compared must not read as 'nothing sanctioned here'. | T168 eval, `D-V9-pin-swapped` | **Couldn't check, and says so** | sparse: na LOW -; dense: na LOW - |

### Time & Rules

| Loophole | How it works | Found | Today | Detail |
|---|---|---|---|---|
| Complete 5 days after sanction; videos filmed only after the completion date. | Videos after the finish do not show it being built. | T168 eval, `TH-F1-filmed-after-done` | **Caught: asked** | sparse: ask MEDIUM FINISHED_TOO_FAST; dense: ask MEDIUM FINISHED_TOO_FAST |
| Complete 6 days after sanction; a reused video, then a final video. | Neither shows this work going on. | T168 eval, `TH-F2-reused-then-final` | **Caught: asked** | sparse: ask HIGH FINISHED_TOO_FAST; dense: ask HIGH FINISHED_TOO_FAST |
| A Rs 7 lakh drain (no form) recorded complete 10 days before its sanction. | R14's '7+ days before the sanction'. | T168 eval, `TH-F3-backdated-10-days` | **Caught: asked** | sparse: ask HIGH BUILT_RIGHT_AFTER_SANCTION; dense: ask HIGH BUILT_RIGHT_AFTER_SANCTION |
| A Rs 12 lakh road (no form) recorded complete the day it was recommended. | R13. | T168 eval, `TH-F4-built-same-day` | **Caught: asked** | sparse: ask HIGH BUILT_IN_DAYS,BUILT_RIGHT_AFTER_SANCTION; dense: ask HIGH BUILT_IN_DAYS,BUILT_RIGHT_AFTER_SANCTION |
| A hall months past its time; its last three videos: no change, can't tell, no change. | Past its own time: at least a follow-up. SEEN (band): the stall count was changed after the four-agent run's first pass (an unreadable video no longer resets it). | T168 eval, `TH-F5-almost-stalled` | **Caught: asked** | sparse: ask MEDIUM PAST_PROMISED_TIME; dense: ask MEDIUM PAST_PROMISED_TIME |
| A 350 m road recorded complete 6 days after sanction, never filmed. | A road this size is not built in 6 days (R14 line); nothing shows it. | T168 eval, `T-F1-done-in-6-days` | **Caught: asked** | sparse: ask MEDIUM FINISHED_TOO_FAST; dense: ask MEDIUM FINISHED_TOO_FAST |
| A record (no form) completed 60 days before it was recommended. | R06: dates in an impossible order, outside a bulk-entry quarter. | T168 eval, `T-F2-done-before-recommended` | **Caught: asked** | sparse: ask HIGH BUILT_RIGHT_AFTER_SANCTION,IMPOSSIBLE_TIMELINE; dense: ask HIGH BUILT_RIGHT_AFTER_SANCTION,IMPOSSIBLE_TIMELINE |
| A Rs 8 lakh hall (no form) recorded complete 5 days after recommendation. | R13: a construction this size cannot be finished that fast. | T168 eval, `T-F3-built-in-days` | **Caught: asked** | sparse: ask HIGH BUILT_IN_DAYS,BUILT_RIGHT_AFTER_SANCTION; dense: ask HIGH BUILT_IN_DAYS,BUILT_RIGHT_AFTER_SANCTION |
| A Rs 6 lakh road (no form) recorded complete 3 days after its sanction. | R14 (25 of 25 read). | T168 eval, `T-F4-right-after-sanction` | **Caught: asked** | sparse: ask HIGH BUILT_RIGHT_AFTER_SANCTION; dense: ask HIGH BUILT_RIGHT_AFTER_SANCTION |
| A hall 9 months past its promised time; the last three videos show no change. | Stopped: ask why. | T168 eval, `T-F5-abandoned` | **Caught: asked** | sparse: ask MEDIUM PAST_PROMISED_TIME; dense: ask MEDIUM PAST_PROMISED_TIME |
| Complete 6 days after sanction; one video, filmed on the completion day, 'changed'. | One video on the day it is called complete does not show the work going on. | T168 eval, `T-V1-filmed-on-the-last-day` | **Caught: asked** | sparse: ask MEDIUM FINISHED_TOO_FAST; dense: ask MEDIUM FINISHED_TOO_FAST |
| Complete 6 days after sanction; its video reuses another work's footage. | A reused video never shows this work going on. | T168 eval, `T-V5-reused-video` | **Caught: asked** | sparse: ask HIGH FINISHED_TOO_FAST; dense: ask HIGH FINISHED_TOO_FAST |
| A Rs 6 lakh road (no form) recorded complete 20 days BEFORE its sanction. | R14 includes 7+ days before the sanction. | T168 eval, `T-V7-backdated-complete` | **Caught: asked** | sparse: ask HIGH BUILT_RIGHT_AFTER_SANCTION; dense: ask HIGH BUILT_RIGHT_AFTER_SANCTION |
| 'complete' just past the 30-day floor, never filmed |  | T135-T164 loop, `'complete' just past the 30-day floor, never filmed` | **Caught: asked** | ['FINISHED_TOO_FAST', 'NO_SITE_VIDEO']: Time's floor is passed, but no site video was ever filmed |
| 'complete' past the early line, checked the next day, never filmed |  | T135-T164 loop, `'complete' past the early line, checked the next day, never ` | **Caught: asked** | ['NO_SITE_VIDEO']: complete with not one site video is asked at once |
| the 6-day road: one reused video 'shows' work going on |  | T135-T164 loop, `the 6-day road: one reused video 'shows' work going on` | **Caught: asked** | a reused video before completion: FINISHED_TOO_FAST (ASSESSED) |
| the late hall: 10 years promised |  | T135-T164 loop, `the late hall: 10 years promised` | **Caught: asked** | estimate 3,650 days: PAST_PROMISED_TIME (ASSESSED) |
| the late hall: 30 'lost months' declared on the native form |  | T135-T164 loop, `the late hall: 30 'lost months' declared on the native form` | **Caught: asked** | 30 lost months: PAST_PROMISED_TIME (ASSESSED) |
| the late hall: start month declared two years after sanction |  | T135-T164 loop, `the late hall: start month declared two years after sanction` | **Caught: asked** | start promised 2 years after sanction: PAST_PROMISED_TIME (ASSESSED) |
| Sanctioned 500 days ago, a 120-day estimate, the start declared two years after sanction. | A declared start counts at most 6 months after sanction (T135). | T168 eval, `T-V2-start-years-away` | **Caught: "check this"** | sparse: check MEDIUM PAST_PROMISED_TIME; dense: check MEDIUM PAST_PROMISED_TIME |
| A road with a 10-year estimate, sanctioned 2 years ago, nothing filmed for a year. | An estimate over twice the usual buys only the typical time. | T168 eval, `T-V3-ten-year-estimate` | **Caught: "check this"** | sparse: check MEDIUM PAST_PROMISED_TIME; dense: check MEDIUM PAST_PROMISED_TIME |
| A road with a 700-day estimate, sanctioned 900 days ago, not finished, never filmed. | An estimate past the usual buys only the usual time (9 in 10 finished works). | T168 eval, `T-V4-padded-estimate` | **Caught: "check this"** | sparse: check MEDIUM PAST_PROMISED_TIME; dense: check MEDIUM PAST_PROMISED_TIME |
| A record sanctioned 30 days before it was recommended. | Dates in an impossible order: at least a note, never a clean chit. SEEN: the note SANCTIONED_BEFORE_RECOMMENDED was added after this case's first run. | T168 eval, `TH-B1-sanction-before-recommendation` | **Couldn't check, and says so** | sparse: edge LOW -; dense: edge LOW - |
| A record with no status. | Its dates cannot be read against a status. | T168 eval, `T-B1-no-status` | **Couldn't check, and says so** | sparse: na LOW -; dense: na LOW - |
| A Rs 6 lakh road recorded complete with no completion date (no form). | How fast it was finished cannot be checked: not a clean chit. | T168 eval, `T-B2-complete-no-date` | **Couldn't check, and says so** | sparse: na LOW -; dense: na LOW - |
| A record completed on a date after the data was published. | R06's second half: a date that has not happened yet (LOW). | T168 eval, `T-B3-done-in-future` | **Couldn't check, and says so** | sparse: check LOW IMPOSSIBLE_TIMELINE; dense: check LOW IMPOSSIBLE_TIMELINE |
| an estimate of 0 days: no false question, says so |  | T135-T164 loop, `an estimate of 0 days: no false question, says so` | **Couldn't check, and says so** | nothing; says the estimate is missing: True |
| complete with no completion date: says so, asks nothing wrong |  | T135-T164 loop, `complete with no completion date: says so, asks nothing wron` | **Couldn't check, and says so** | nothing; says the completion date is missing: True |
| completion dated after today: no false question, says so |  | T135-T164 loop, `completion dated after today: no false question, says so` | **Couldn't check, and says so** | ['IMPOSSIBLE_TIMELINE']; says the date is after today: True |
| A final video moved a work's start to the completion day | The reason read "complete 0 days after the work could start" instead of counting from the sanction. | T170, 20 Oct 2026, `M-SYS-5` | **Fixed (guarded by a test)** | A final video never sets the start. Guard: `tests/agents/time_rules/test_time_rules_t168.py::test_a_final_video_never_moves_the_start_the_pace_is_counted_from`. |

### Site Progress

| Loophole | How it works | Found | Today | Detail |
|---|---|---|---|---|
| Last month's video uploaded again as this month's. | Frames already seen on an earlier visit of this same work. | T168 eval, `SH-F1-own-video-again` | **Caught: asked** | sparse: ask MEDIUM FOOTAGE_USED_BEFORE; dense: ask MEDIUM FOOTAGE_USED_BEFORE |
| Four of the last five monthly videos too dark, one good between them. | 4 of the last 5 (T137). | T168 eval, `SH-F2-four-of-five-unusable` | **Caught: asked** | sparse: ask MEDIUM SITE_VIDEOS_UNUSABLE; dense: ask MEDIUM SITE_VIDEOS_UNUSABLE |
| The false claim not shown, then a too-dark video, then not shown again. | A poor video between does not reset the count. | T168 eval, `SH-F3-dark-between-not-shown` | **Caught: asked** | sparse: ask MEDIUM CLAIM_NOT_SHOWN; dense: ask MEDIUM CLAIM_NOT_SHOWN |
| Complete; the final video shows the same place as another work's videos. | The finished building is another work's. | T168 eval, `SH-F4-final-at-another-work` | **Caught: asked** | sparse: ask MEDIUM SAME_PLACE_AS_ANOTHER_WORK; dense: ask MEDIUM SAME_PLACE_AS_ANOTHER_WORK |
| Every monthly video from a phone reporting a mock location, views not matching. | Faked GPS and other views: filmed elsewhere. | T168 eval, `SH-F6-mock-gps-every-month` | **Caught: asked** | sparse: ask MEDIUM LOCATION_NOT_RECORDED,NOT_FILMED_AT_THIS_SITE; dense: ask MEDIUM LOCATION_NOT_RECORDED,NOT_FILMED_AT_THIS_SITE |
| Two monthly videos recorded 300 m and 800 m from the form's site. | Twice: a question. | T168 eval, `SL-F2-filmed-far-twice` | **Caught: asked** | sparse: ask MEDIUM FILMED_AWAY_FROM_FORM_SITE; dense: ask MEDIUM FILMED_AWAY_FROM_FORM_SITE |
| The last three videos filmed with location off. | Never recording where it was filmed dodges every location check. | T168 eval, `SL-F3-gps-off-every-month` | **Caught: asked** | sparse: ask MEDIUM LOCATION_NOT_RECORDED; dense: ask MEDIUM LOCATION_NOT_RECORDED |
| The third video reuses 42 frames of another hall's video. | Not new filming. | T168 eval, `S-F1-footage-reused` | **Caught: asked** | sparse: ask MEDIUM FOOTAGE_USED_BEFORE; dense: ask MEDIUM FOOTAGE_USED_BEFORE |
| A monthly video filmed 2.4 km away; its views do not match the site. | GPS and views both say elsewhere. | T168 eval, `S-F2-filmed-elsewhere` | **Caught: asked** | sparse: ask MEDIUM NOT_FILMED_AT_THIS_SITE; dense: ask MEDIUM NOT_FILMED_AT_THIS_SITE |
| 'Roof slab cast' claimed twice; neither video shows a slab. | The claim failing twice in a row. | T168 eval, `S-F3-claim-not-shown-twice` | **Caught: asked** | sparse: ask MEDIUM CLAIM_NOT_SHOWN; dense: ask MEDIUM CLAIM_NOT_SHOWN |
| Recorded complete; the final video shows unfinished parts. | Complete, not shown complete. | T168 eval, `S-F4-complete-not-shown` | **Caught: asked** | sparse: ask MEDIUM COMPLETE_NOT_SHOWN; dense: ask MEDIUM COMPLETE_NOT_SHOWN |
| A 'new' hall whose first visit already shows a hall standing. | Built before sanction, or another scheme's hall. | T168 eval, `S-F5-already-built` | **Caught: asked** | sparse: ask MEDIUM ALREADY_BUILT_AT_START; dense: ask MEDIUM ALREADY_BUILT_AT_START |
| Sanctioned 200 days ago; not one site video. | Never filming dodges every other check. | T168 eval, `S-F6-never-filmed` | **Caught: asked** | sparse: ask MEDIUM NO_SITE_VIDEO; dense: ask MEDIUM NO_SITE_VIDEO |
| The site's viewpoints show the same place as another work's videos. | One site shown for two works. | T168 eval, `S-F7-same-place` | **Caught: asked** | sparse: ask MEDIUM SAME_PLACE_AS_ANOTHER_WORK; dense: ask MEDIUM SAME_PLACE_AS_ANOTHER_WORK |
| The false claim not shown, then a 'can't tell' month, then not shown again. | T135: a 'can't tell' between does not reset the count. | T168 eval, `S-V1-cant-tell-between` | **Caught: asked** | sparse: ask MEDIUM CLAIM_NOT_SHOWN; dense: ask MEDIUM CLAIM_NOT_SHOWN |
| Every monthly video too dark or too short to show anything. | Filming badly every month would dodge every check (T137). | T168 eval, `S-V2-film-badly-every-month` | **Caught: asked** | sparse: ask MEDIUM SITE_VIDEOS_UNUSABLE; dense: ask MEDIUM SITE_VIDEOS_UNUSABLE |
| A monthly video from a phone reporting a mock location; its views do not match. | A faked GPS and other views. | T168 eval, `S-V3-mock-location` | **Caught: asked** | sparse: ask MEDIUM NOT_FILMED_AT_THIS_SITE; dense: ask MEDIUM NOT_FILMED_AT_THIS_SITE |
| No first visit; the first video is the final one, showing a finished hall. | Nothing shows the asset is new (T139). | T168 eval, `S-V4-skip-first-visit` | **Caught: asked** | sparse: ask MEDIUM FIRST_FILMED_FINISHED; dense: ask MEDIUM FIRST_FILMED_FINISHED |
| Five uploads, none sealed or filmed in the app. | None accepted: as if never filmed. | T168 eval, `S-V5-unsealed-only` | **Caught: asked** | sparse: ask MEDIUM NO_SITE_VIDEO; dense: ask MEDIUM NO_SITE_VIDEO |
| Every video filmed about 150 m from the form's pin, views matching each other. | The work is not where the form says (T135). | T168 eval, `S-V6-pin-150m-off` | **Caught: asked** | sparse: ask MEDIUM SITE_NOT_AT_FORM_PIN; dense: ask MEDIUM SITE_NOT_AT_FORM_PIN |
| A monthly video re-encoded so that only 3 frames match another work's footage. | MIN_REUSED_FRAMES is 3: still the same footage. | T168 eval, `S-V7-few-reused-frames` | **Caught: asked** | sparse: ask MEDIUM FOOTAGE_USED_BEFORE; dense: ask MEDIUM FOOTAGE_USED_BEFORE |
| Recorded complete 90 days ago after two monthly videos; no final video ever. | T137: complete must be filmed complete. | T168 eval, `S-V8-complete-no-final` | **Caught: asked** | sparse: ask MEDIUM COMPLETE_NOT_FILMED; dense: ask MEDIUM COMPLETE_NOT_FILMED |
| 'can't tell' slipped between two 'not shown' claims |  | T135-T164 loop, `'can't tell' slipped between two 'not shown' claims` | **Caught: asked** | not shown, can't tell, not shown: CLAIM_NOT_SHOWN (ASSESSED) |
| 'not shown', a dark video, 'not shown': still twice in a row |  | T135-T164 loop, `'not shown', a dark video, 'not shown': still twice in a row` | **Caught: asked** | a dark video slipped between the two: CLAIM_NOT_SHOWN (ASSESSED) |
| 4 of the last 5 videos dark / viewpoints not filmed |  | T135-T164 loop, `4 of the last 5 videos dark / viewpoints not filmed` | **Caught: asked** | 4 of the last 5 unusable: SITE_VIDEOS_UNUSABLE (ASSESSED) |
| a video dated after today |  | T135-T164 loop, `a video dated after today` | **Caught: asked** | nothing; says the date is wrong: True |
| an old asset filmed once, as the final video (no first video) |  | T135-T164 loop, `an old asset filmed once, as the final video (no first video` | **Caught: asked** | first filmed finished (T139: ALREADY_BUILT_AT_START needs a first video): FIRST_FILMED_FINISHED (ASSESSED) |
| every claim vague ('work in progress') |  | T135-T164 loop, `every claim vague ('work in progress')` | **Caught: asked** | nothing; asks for a specific claim: True |
| every video uploaded unsealed (none accepted) |  | T135-T164 loop, `every video uploaded unsealed (none accepted)` | **Caught: asked** | ['NO_SITE_VIDEO'] (ASSESSED) |
| sanctioned months ago, never filmed |  | T135-T164 loop, `sanctioned months ago, never filmed` | **Caught: asked** | ['NO_SITE_VIDEO'] (ASSESSED); sanctioned 2026-04-15, no video |
| the form's pin is not where every video is filmed |  | T135-T164 loop, `the form's pin is not where every video is filmed` | **Caught: asked** | ['SITE_NOT_AT_FORM_PIN']: three videos all 320 m from the pin, views matching each other |
| three bad videos, then filming stops |  | T135-T164 loop, `three bad videos, then filming stops` | **Caught: asked** | every video so far unusable: SITE_VIDEOS_UNUSABLE (ASSESSED) |
| two honest months filmed, then 'complete' with no final video |  | T135-T164 loop, `two honest months filmed, then 'complete' with no final vide` | **Caught: asked** | complete 40 days ago, no final video: COMPLETE_NOT_FILMED (ASSESSED) |
| views never match while the GPS says 'at the site' |  | T135-T164 loop, `views never match while the GPS says 'at the site'` | **Caught: asked** | GPS faked inside, another place filmed: SITE_VIDEOS_UNUSABLE (ASSESSED) |
| No first visit; the first video is a monthly one, then the final one: complete. | Nothing filmed before work started shows the asset is new. SEEN: NO_FIRST_VISIT was added after this case's first run. | T168 eval, `SH-F5-no-first-visit-late-start` | **Caught: "check this"** | sparse: check MEDIUM NO_FIRST_VISIT; dense: check MEDIUM NO_FIRST_VISIT |
| One monthly video recorded 450 m from the form's site (its views still look like the site). | A lot more than a little: check this. | T168 eval, `SL-F1-one-month-elsewhere` | **Caught: "check this"** | sparse: check MEDIUM FILMED_AWAY_FROM_FORM_SITE; dense: check MEDIUM FILMED_AWAY_FROM_FORM_SITE |
| Two of the last three videos from a phone faking its location (views still matching). | A faked location is not a recorded location. | T168 eval, `SL-F4-mock-location-twice` | **Caught: "check this"** | sparse: check MEDIUM LOCATION_NOT_RECORDED; dense: check MEDIUM LOCATION_NOT_RECORDED |
| Two videos with every reading empty. | Not read: couldn't check. | T168 eval, `SH-B1-readings-all-empty` | **Couldn't check, and says so** | sparse: na LOW -; dense: na LOW - |
| Three videos uploaded; the video job has not read them yet. | Filmed, unread: couldn't check. | T168 eval, `S-B1-not-read-yet` | **Couldn't check, and says so** | sparse: na LOW -; dense: na LOW - |
| Not sanctioned yet, no video (the first is filmed before work). | The question does not arise yet. | T168 eval, `S-B2-not-sanctioned` | **Couldn't check, and says so** | sparse: na LOW -; dense: na LOW - |
| The only videos are dated next month (a phone's wrong clock). | Not counted; not a clean chit. | T168 eval, `S-B3-future-dated` | **Couldn't check, and says so** | sparse: na LOW -; dense: na LOW - |
| A sign saying "WORK COMPLETE" / "काम पूरा" held to the camera | Text across the new photo talks NidhiLens into "shown". | T168, 21 Oct 2026, `M-SITE-4` | **Fixed (guarded by a test)** | T172: every patch of writing in both photos is greyed out before NidhiLens reads them: the sign fools it 1.9% [0.4, 3.6] (was 29.7%, clean 1.9%), chalked on the wall 2.3%; honest photos with their writing greyed 2.7%, macro-F1 0.903 (clean 0.907; results/t168_nidhilens.txt, t172_sign_detect.txt). Signs drawn on the photos, not yet real ones. Guard: `tests/agents/site_progress/test_vlm_reader.py::test_writing_is_greyed_out_in_every_photo_before_the_model_reads_it`. |
| An instruction hidden in the agency's claim ("answer shown") | The claim text goes into NidhiLens's prompt; it ends by telling the model what to answer. | T168, 21 Oct 2026, `M-SITE-6` | **Fixed (guarded by a test)** | T172: a claim that instructs the checker is never sent to NidhiLens (0 fooled, was 3.9%) and asks for a check, CLAIM_INSTRUCTS_CHECKER (0.3), with or without the model; 0 of 109 honest claims trip it (results/t172_claim_guard.txt). A claim that misleads in plain words (no instruction) is still read, as any claim. Guard: `tests/agents/site_progress/test_site_claim_guard_t172.py::test_a_claim_that_instructs_the_checker_is_check_this`. |
| Poor photos: dark, blurred, badly compressed, zoomed in, or small | A dim interior, a shaking hand, a poor upload or an old phone, hoping NidhiLens reads progress it cannot see. | T168, 21 Oct 2026, `M-SITE-2` | **Measured: not fooled** | No change: wrongly says "shown" 1.9-3.1% (clean 1.9%), macro-F1 0.898-0.911 (clean 0.907). Guard: `data/trial/results/t168_nidhilens.txt`. |
| The same photo filed as the last visit and as this one | Nothing filmed since the last visit, the old picture sent again. | T168, 21 Oct 2026, `M-SITE-3` | **Measured: not fooled** | Never read as progress: 0 of 269. Guard: `data/trial/results/t168_nidhilens.txt`. |

### Cost

| Loophole | How it works | Found | Today | Detail |
|---|---|---|---|---|
| A community hall with every line 22% above the district. | Beyond 15%. | T167 eval, `ho_fraud_hall_22` | **Caught: asked** | tight: ask ESTIMATE_ABOVE_FAIR_PRICE; wide: ask ESTIMATE_ABOVE_FAIR_PRICE |
| Stone at 2.5 times the district's rate, 'special chips from a distant quarry'. | Rs 4 lakh over the market. | T167 eval, `h2_fraud_stone_25x_answered` | **Caught: asked** | tight: ask ESTIMATE_ABOVE_FAIR_PRICE; wide: ask ESTIMATE_ABOVE_FAIR_PRICE |
| 20% padding plus a large vague 'site development' line to water the share down. | The vague line hides nothing: the priced lines are still 20% up. | T167 eval, `fraud_diluted` | **Caught: asked** | tight: ask ESTIMATE_ABOVE_FAIR_PRICE; wide: ask ESTIMATE_ABOVE_FAIR_PRICE |
| The cement line entered twice under two names. | Twice the cement the size takes. | T167 eval, `fraud_duplicate_line` | **Caught: asked** | tight: ask ESTIMATE_ABOVE_FAIR_PRICE,MATERIAL_QUANTITY_ABOVE_SIZE; wide: ask ESTIMATE_ABOVE_FAIR_PRICE,MATERIAL_QUANTITY_ABOVE_SIZE |
| Three times the labourer-days the road needs (inflated muster roll), wages fair. | Ghost workers: the most common works fraud in India's rural schemes. | T167 eval, `fraud_ghost_labour` | **Caught: asked** | tight: ask LABOUR_DAYS_ABOVE_PEERS,LABOUR_DAYS_BEYOND_WORK; wide: ask LABOUR_DAYS_ABOVE_PEERS,LABOUR_DAYS_BEYOND_WORK |
| Masons at 2.4 times the district's day rate. | A blatant wage. | T167 eval, `fraud_labour_24x` | **Caught: asked** | tight: ask LABOUR_RATE_FAR_ABOVE; wide: ask LABOUR_RATE_FAR_ABOVE |
| Standard lights at Rs 48,000 each, twice the MP's amount. | The example filing. | T167 eval, `fraud_lights_2x` | **Caught: asked** | tight: ask ESTIMATE_ABOVE_STANDARD_AND_MP; wide: ask ESTIMATE_ABOVE_STANDARD_AND_MP |
| 18% of the estimate added as a lump sum. | Unitemised money in a construction estimate. | T167 eval, `fraud_lump_sum_18` | **Caught: asked** | tight: ask ESTIMATE_ABOVE_FAIR_PRICE; wide: ask ESTIMATE_ABOVE_FAIR_PRICE |
| Declared M25 so no nominal mix applies; cement 1.6 times what M20 takes. | IS 456 caps cement at 450 kg per m3 (9 bags): 1.6 x 8.06 bags is beyond it. | T167 eval, `fraud_m25_cement` | **Caught: asked** | tight: ask ESTIMATE_ABOVE_FAIR_RANGE,MATERIAL_QUANTITY_ABOVE_SIZE; wide: ask ESTIMATE_ABOVE_FAIR_RANGE,MATERIAL_QUANTITY_ABOVE_SIZE |
| 25% padding with sand in brass and cement in quintals. | Units chosen to avoid comparison. | T167 eval, `fraud_odd_units` | **Caught: asked** | tight: ask ESTIMATE_ABOVE_FAIR_PRICE; wide: ask ESTIMATE_ABOVE_FAIR_PRICE |
| Cement at twice the district's rate; everything else fair. | Rs 5 lakh in one line. | T167 eval, `fraud_one_line_2x` | **Caught: asked** | tight: ask ESTIMATE_ABOVE_FAIR_PRICE; wide: ask ESTIMATE_ABOVE_FAIR_PRICE |
| 20% 'other charges' while the rates already include tax. | Nothing to show for it. | T167 eval, `fraud_other_charges_20` | **Caught: asked** | tight: ask ESTIMATE_ABOVE_FAIR_PRICE; wide: ask ESTIMATE_ABOVE_FAIR_PRICE |
| Every material 20% above the district's rates. | Beyond CPWD's 10% limit; a whole-estimate pattern. | T167 eval, `fraud_pad_20` | **Caught: asked** | tight: ask ESTIMATE_ABOVE_FAIR_PRICE; wide: ask ESTIMATE_ABOVE_FAIR_PRICE |
| Every material 25% above the district's rates. | Beyond CPWD's 10% limit; a whole-estimate pattern. | T167 eval, `fraud_pad_25` | **Caught: asked** | tight: ask ESTIMATE_ABOVE_FAIR_PRICE; wide: ask ESTIMATE_ABOVE_FAIR_PRICE |
| Every material 40% above the district's rates. | Beyond CPWD's 10% limit; a whole-estimate pattern. | T167 eval, `fraud_pad_40` | **Caught: asked** | tight: ask ESTIMATE_ABOVE_FAIR_PRICE; wide: ask ESTIMATE_ABOVE_FAIR_PRICE |
| Every material 18% above the district's rates, no reason given. | Beyond 15%: a question. | T167 eval, `fraud_plain_18` | **Caught: asked** | tight: ask ESTIMATE_ABOVE_FAIR_PRICE; wide: ask ESTIMATE_ABOVE_FAIR_PRICE |
| 1.5 times the cement the road's size takes, 'justified'. | Material that is never used. | T167 eval, `fraud_qty_cement_150` | **Caught: asked** | tight: ask ESTIMATE_ABOVE_FAIR_PRICE,MATERIAL_QUANTITY_ABOVE_SIZE; wide: ask ESTIMATE_ABOVE_FAIR_PRICE,MATERIAL_QUANTITY_ABOVE_SIZE |
| Cement at Rs 1,200 a bag, the warning answered with a vague reason. | An answered warning puts the line back in the price check. | T167 eval, `fraud_rate_answered` | **Caught: asked** | tight: ask ESTIMATE_ABOVE_FAIR_PRICE; wide: ask ESTIMATE_ABOVE_FAIR_PRICE |
| The road is 300 m x 3.5 m on the ground; the form says 600 m x 7 m everywhere. | The estimate is consistent with its claimed size: only the site (videos, the officer's visit) can show it. Site Progress's job. | T167 eval, `fraud_size_everywhere` | **Caught: asked** | tight: ask LABOUR_DAYS_BEYOND_WORK; wide: ask LABOUR_DAYS_BEYOND_WORK |
| Cement at Rs 3,800 a bag, the 'typing mistake' warning never answered. | Rs 45 lakh more in the total; padding dressed as a typo. | T167 eval, `fraud_typo_cover` | **Caught: asked** | tight: ask RATE_TYPO_NOT_ANSWERED; wide: ask RATE_TYPO_NOT_ANSWERED |
| 25% padding, every item given a name no reader knows. | Nothing can be priced. | T167 eval, `fraud_unreadable_names` | **Caught: asked** | tight: ask ESTIMATE_NOT_ITEMISED; wide: ask ESTIMATE_NOT_ITEMISED |
| 22% padding where only the state's forms can price it |  | T135-T164 loop, `22% padding where only the state's forms can price it` | **Caught: asked** | ['ESTIMATE_ABOVE_FAIR_RANGE']: a state-wide rate carries 10% for local prices, so padding is asked from about 27% there; the district's own forms (or the SoR, T096) ask from 15% |
| a bigger size claimed (7 m wide road) to justify the cement |  | T135-T164 loop, `a bigger size claimed (7 m wide road) to justify the cement` | **Caught: asked** | ['SIZE_NOT_AS_DESCRIBED']: the form's own scope still says 3.5 m wide |
| a helper called 'highly skilled', paid more than an operator |  | T135-T164 loop, `a helper called 'highly skilled', paid more than an operator` | **Caught: asked** | judged as a helper: LABOUR_RATE_FAR_ABOVE (ASSESSED); compared with unskilled |
| a labour row on a BOQ line whose rate already pays its workers |  | T135-T164 loop, `a labour row on a BOQ line whose rate already pays its worke` | **Caught: asked** | the form refuses it (True); NOT_ASSESSABLE, never a clean chit |
| a typed extra zero (cement Rs 3,800 a bag), never answered |  | T135-T164 loop, `a typed extra zero (cement Rs 3,800 a bag), never answered` | **Caught: asked** | ['RATE_TYPO_NOT_ANSWERED'] (the rest of the road is honest: only the typo is asked) |
| a watchman on site twice the work's own time |  | T135-T164 loop, `a watchman on site twice the work's own time` | **Caught: asked** | 120-day work, 240 days on site: LABOUR_DAYS_BEYOND_WORK (ASSESSED) |
| an equipment-hire line raised from 30 days to 250 |  | T135-T164 loop, `an equipment-hire line raised from 30 days to 250` | **Caught: asked** | Rs 5.5 lakh more in a line no reader prices: ESTIMATE_ABOVE_FAIR_PRICE (ASSESSED) |
| an invented trade ('Other', highly skilled) at 4x a mason |  | T135-T164 loop, `an invented trade ('Other', highly skilled) at 4x a mason` | **Caught: asked** | an Other trade at its nearest grade with forms: LABOUR_RATE_FAR_ABOVE (ASSESSED) |
| every crew's days x2.5, still within the work's time |  | T135-T164 loop, `every crew's days x2.5, still within the work's time` | **Caught: asked** | ['LABOUR_DAYS_ABOVE_PEERS']: how many workers and days a work needs is never judged (the owner, T141); days beyond the work's own time are asked (below), and the site videos show the pace of work |
| labour rows with the trade left blank |  | T135-T164 loop, `labour rows with the trade left blank` | **Caught: asked** | nothing (NOT_ASSESSABLE): never a clean chit |
| masons at 1.8 times: under the 2x line |  | T135-T164 loop, `masons at 1.8 times: under the 2x line` | **Caught: asked** | ['LABOUR_RATE_ABOVE']: a trade's rate is a question only at twice what others pay it (the owner: blatant only); the whole estimate counts it with every other line |
| masons at 14 times (past the form's typo guard), never answered |  | T135-T164 loop, `masons at 14 times (past the form's typo guard), never answe` | **Caught: asked** | masons at Rs 10,500 a day: RATE_TYPO_NOT_ANSWERED (ASSESSED) |
| masons at 2.2 times what other agencies here pay masons |  | T135-T164 loop, `masons at 2.2 times what other agencies here pay masons` | **Caught: asked** | masons at 2.2x: LABOUR_RATE_FAR_ABOVE (ASSESSED) |
| masons at 2.2x moved back among the BOQ lines |  | T135-T164 loop, `masons at 2.2x moved back among the BOQ lines` | **Caught: asked** | still judged as masons: LABOUR_RATE_FAR_ABOVE (ASSESSED) |
| one agency files under name variants to lift the district price |  | T135-T164 loop, `one agency files under name variants to lift the district pr` | **Caught: asked** | 4 padded forms under name variants of the same agency: ESTIMATE_ABOVE_FAIR_PRICE (ASSESSED) |
| padded items given names no reader knows |  | T135-T164 loop, `padded items given names no reader knows` | **Caught: asked** | ['ESTIMATE_NOT_ITEMISED'] (ASSESSED); says what it could not price: True |
| padded items given units that do not fit them |  | T135-T164 loop, `padded items given units that do not fit them` | **Caught: asked** | cement in nos: ESTIMATE_ABOVE_FAIR_PRICE (ASSESSED) |
| padded items priced in units nobody converts (brass, quintal) |  | T135-T164 loop, `padded items priced in units nobody converts (brass, quintal` | **Caught: asked** | sand in brass, cement in quintal: ESTIMATE_ABOVE_FAIR_PRICE (ASSESSED) |
| padding 14%: just under the 15% line |  | T135-T164 loop, `padding 14%: just under the 15% line` | **Caught: asked** | ['ESTIMATE_ABOVE_FAIR_RANGE']: a question needs 15% and Rs 50,000; from 10% it is 'check this' (T167, CPWD Works Manual 20.4.3.2) |
| rates written as words ('see attached'): never a clean chit |  | T135-T164 loop, `rates written as words ('see attached'): never a clean chit` | **Caught: asked** | NOT_ASSESSABLE: Cannot be assessed: the cost estimate form is not complete (7 fields to fix). This is not  |
| sand and aggregate quantities doubled |  | T135-T164 loop, `sand and aggregate quantities doubled` | **Caught: asked** | twice the sand and the stone: ESTIMATE_ABOVE_FAIR_PRICE, MATERIAL_QUANTITY_ABOVE_SIZE, MATERIAL_QUANTITY_ABOVE_SIZE (ASSESSED) |
| solar panels bought by the watt, twice the lights' Wp |  | T135-T164 loop, `solar panels bought by the watt, twice the lights' Wp` | **Caught: asked** | 800 Wp for 10 lights of 40 Wp: ['solar_panel'] (ASSESSED) |
| the masons split into two rows, one at 3x |  | T135-T164 loop, `the masons split into two rows, one at 3x` | **Caught: asked** | each row judged: LABOUR_RATE_FAR_ABOVE (ASSESSED) |
| the padding moved into 'other charges' |  | T135-T164 loop, `the padding moved into 'other charges'` | **Caught: asked** | Rs 264,100 as other charges: ESTIMATE_ABOVE_FAIR_PRICE (ASSESSED) |
| the padding moved into a lump-sum line |  | T135-T164 loop, `the padding moved into a lump-sum line` | **Caught: asked** | Rs 264,100 as a lump sum: ESTIMATE_ABOVE_FAIR_PRICE (ASSESSED) |
| the road's stone alone doubled (the slab needs half) |  | T135-T164 loop, `the road's stone alone doubled (the slab needs half)` | **Caught: asked** | twice the stone: ['aggregate'] (ASSESSED) |
| the slab's stone doubled inside one unsized stone line |  | T135-T164 loop, `the slab's stone doubled inside one unsized stone line` | **Caught: asked** | nothing (NOT_ASSESSABLE): the form asks for the base's stone on a line of its own before the estimate is judged; itemised, twice the slab's stone is asked |
| Cement 16% high, written per kg. | The unit changes nothing. | T167 eval, `ho_fraud_cement_kg_16` | **Caught: "check this"** | tight: check RATE_ABOVE_ALL_OTHERS; wide: check RATE_ABOVE_ALL_OTHERS |
| A community hall with every line 13% above the district. | Beyond CPWD's 10% on a Rs 9 lakh building. | T167 eval, `ho_fraud_hall_13` | **Caught: "check this"** | tight: check ESTIMATE_ABOVE_FAIR_RANGE; wide: check ESTIMATE_ABOVE_FAIR_RANGE |
| A hall with three times the masons on the roll for the same days. | Ghost workers. | T167 eval, `ho_fraud_hall_ghost_masons` | **Caught: "check this"** | tight: check LABOUR_DAYS_ABOVE_PEERS; wide: check LABOUR_DAYS_ABOVE_PEERS |
| A hall's masons and labourers both at 1.6 times the district's wage. | Real money in wages no crew here earns. | T167 eval, `ho_fraud_hall_labour_16` | **Caught: "check this"** | tight: check LABOUR_RATE_ABOVE; wide: check LABOUR_RATE_ABOVE |
| Standard 12 W lights at 1.3 times the district's 98th percentile; the MP agrees. | Just beyond the price margin. | T167 eval, `ho_fraud_lights_130_mp` | **Caught: "check this"** | tight: check PRICE_ABOVE_STANDARD; wide: check PRICE_ABOVE_STANDARD |
| An 800 m road, every material 11% above the district. | Lakhs of rupees. | T167 eval, `ho_fraud_long_road_11` | **Caught: "check this"** | tight: check ESTIMATE_ABOVE_FAIR_RANGE; wide: check ESTIMATE_ABOVE_FAIR_RANGE |
| Sand and stone each 22% above what the slab takes, both 'justified'. | Each under the 25% question line; together real money. | T167 eval, `ho_fraud_qty_two_materials` | **Caught: "check this"** | tight: check MATERIAL_QUANTITY_ABOVE_PEERS,MATERIAL_QUANTITY_ABOVE_PEERS; wide: check MATERIAL_QUANTITY_ABOVE_PEERS,MATERIAL_QUANTITY_ABOVE_PEERS |
| Rates 8% high and 8% 'other charges' though tax is in the rates: 16% in all. | Each part looks like an edge case alone. | T167 eval, `ho_fraud_rates_plus_charges` | **Caught: "check this"** | tight: check ESTIMATE_ABOVE_FAIR_RANGE; wide: check ESTIMATE_ABOVE_FAIR_RANGE |
| Sand and stone 35% above the district; cement and base fair. | About a tenth of the estimate in two padded lines. | T167 eval, `ho_fraud_two_lines_35` | **Caught: "check this"** | tight: check ESTIMATE_ABOVE_FAIR_RANGE; wide: check ESTIMATE_ABOVE_FAIR_RANGE |
| Cement 30% high, split into three lots so no line looks big. | Rs 1.5 lakh over the market. | T167 eval, `h2_fraud_cement_split_30` | **Caught: "check this"** | tight: check ESTIMATE_ABOVE_FAIR_RANGE; wide: check ESTIMATE_ABOVE_FAIR_RANGE |
| A hall with 1.5 times the bricks other halls of its size use, justified. | Rs 1.5 lakh of bricks nobody lays. | T167 eval, `h2_fraud_hall_bricks_qty` | **Caught: "check this"** | tight: check MATERIAL_QUANTITY_ABOVE_PEERS; wide: check MATERIAL_QUANTITY_ABOVE_PEERS |
| A hall with 1.4 times the cement other halls of its size use, justified. | Rs 2 lakh of cement beyond the usual. | T167 eval, `h2_fraud_hall_cement_qty` | **Caught: "check this"** | tight: check MATERIAL_QUANTITY_ABOVE_PEERS; wide: check MATERIAL_QUANTITY_ABOVE_PEERS |
| A hall's labourers on the roll for 2.5 times the days other halls take. | Inflated muster roll. | T167 eval, `h2_fraud_hall_labour_days` | **Caught: "check this"** | tight: check LABOUR_DAYS_ABOVE_PEERS; wide: check LABOUR_DAYS_ABOVE_PEERS |
| A hall's steel at 1.5 times the district's rate; the rest fair. | About Rs 1 lakh in one line. | T167 eval, `h2_fraud_hall_steel_rate` | **Caught: "check this"** | tight: check ESTIMATE_ABOVE_FAIR_RANGE; wide: check ESTIMATE_ABOVE_FAIR_RANGE |
| Rates 6% high and a 6% lump sum: 12% in all, each part small. | A construction estimate carries 2% of lump sums at most. | T167 eval, `h2_fraud_lump_and_rates` | **Caught: "check this"** | tight: check ESTIMATE_ABOVE_FAIR_RANGE; wide: check ESTIMATE_ABOVE_FAIR_RANGE |
| A 600 m x 5.5 m road with every material 13% above the district. | Beyond CPWD's 10% on a Rs 40 lakh road. | T167 eval, `h2_fraud_pad_13_wide_road` | **Caught: "check this"** | tight: check ESTIMATE_ABOVE_FAIR_RANGE; wide: check ESTIMATE_ABOVE_FAIR_RANGE |
| Every agency in the district pads 22% together; this filing too. | The district's own rates are no fair rate when all of them are padded; the state's forms show it. | T167 eval, `fraud_cartel_22` | **Caught: "check this"** | tight: check DISTRICT_RATES_ABOVE_STATE; wide: check DISTRICT_RATES_ABOVE_STATE |
| Jaunpur is plains; the form claims a hilly head-load site to carry 18% padding. | The same form as the honest hilly site: a claim can soften a question, never clear it. | T167 eval, `fraud_claimed_hilly` | **Caught: "check this"** | tight: check ESTIMATE_ABOVE_FAIR_RANGE; wide: check ESTIMATE_ABOVE_FAIR_RANGE |
| Three times the labourers on the muster roll for the same days (ghost workers), wages fair. | Person-days three times what other agencies' roads of this size take. | T167 eval, `fraud_ghost_workers` | **Caught: "check this"** | tight: check LABOUR_DAYS_ABOVE_PEERS; wide: check LABOUR_DAYS_ABOVE_PEERS |
| Every trade paid 1.7 times the district's rate: Rs 2.3 lakh more in wages. | No crew earns 1.7 times the going wage on a village road. | T167 eval, `fraud_labour_17x_all` | **Caught: "check this"** | tight: check LABOUR_RATE_ABOVE; wide: check LABOUR_RATE_ABOVE |
| Standard 12 W solar lights at Rs 42,000 each (twice the district's), the MP's amount just as high. | The MP agreeing does not make a price fair: twice what 98 in 100 similar lights cost. | T167 eval, `fraud_lights_mp_agrees` | **Caught: "check this"** | tight: check PRICE_ABOVE_STANDARD; wide: check PRICE_ABOVE_STANDARD |
| Standard solar lights at Rs 32,000 each; the estimate 7% above the MP's amount (just under the 10% line). | 1.5 times the district's usual light. | T167 eval, `fraud_lights_mp_gap_7` | **Caught: "check this"** | tight: check PRICE_ABOVE_STANDARD; wide: check PRICE_ABOVE_STANDARD |
| 12% 'other charges' while the rates already include tax (CPWD contingency is 3%). | Above any honest contingency; over a lakh unexplained. | T167 eval, `fraud_other_charges_12` | **Caught: "check this"** | tight: check ESTIMATE_ABOVE_FAIR_RANGE; wide: check ESTIMATE_ABOVE_FAIR_RANGE |
| Every material 11% above the district's rates on a 300 m road: just under the 15% question line. | Above CPWD's 10% limit for justified rates; tens of thousands of rupees. | T167 eval, `fraud_pad_11` | **Caught: "check this"** | tight: check ESTIMATE_ABOVE_FAIR_RANGE; wide: check ESTIMATE_ABOVE_FAIR_RANGE |
| Every material 12% above the district's rates on a 300 m road: just under the 15% question line. | Above CPWD's 10% limit for justified rates; tens of thousands of rupees. | T167 eval, `fraud_pad_12` | **Caught: "check this"** | tight: check ESTIMATE_ABOVE_FAIR_RANGE; wide: check ESTIMATE_ABOVE_FAIR_RANGE |
| Every material 14% above the district's rates on a 300 m road: just under the 15% question line. | Above CPWD's 10% limit for justified rates; tens of thousands of rupees. | T167 eval, `fraud_pad_14` | **Caught: "check this"** | tight: check ESTIMATE_ABOVE_FAIR_RANGE; wide: check ESTIMATE_ABOVE_FAIR_RANGE |
| 1.2 times the cement the size takes, justified as kerbs and approaches. | About Rs 1 lakh of cement nobody needs; under the 25% quantity line. | T167 eval, `fraud_qty_cement_120` | **Caught: "check this"** | tight: check MATERIAL_QUANTITY_ABOVE_NEED; wide: check MATERIAL_QUANTITY_ABOVE_NEED |
| Only the state's forms can price this district; materials 22% above them. | 12% above even the state rate plus its 10% local allowance. | T167 eval, `fraud_state_22` | **Caught: "check this"** | tight: check ESTIMATE_ABOVE_FAIR_RANGE; wide: check ESTIMATE_ABOVE_FAIR_RANGE |
| a district with no forms: the state's forms stand in |  | T135-T164 loop, `a district with no forms: the state's forms stand in` | **Couldn't check, and says so** | honest: nothing; +50%: ['ESTIMATE_ABOVE_FAIR_PRICE']; priced from: 17 recent forms of 8 other agencies across the state, plus 10% for local prices 25 recent  |
| a typo'd price (Rs 38,000 a bag) among the filings: answers hold |  | T135-T164 loop, `a typo'd price (Rs 38,000 a bag) among the filings: answers ` | **Couldn't check, and says so** | changed: none |
| a work in a state with no reference prices: no question |  | T135-T164 loop, `a work in a state with no reference prices: no question` | **Couldn't check, and says so** | solar lights in a state without a reference: nothing (ASSESSED) |
| district prices all over the place: the honest road is not asked |  | T135-T164 loop, `district prices all over the place: the honest road is not a` | **Couldn't check, and says so** | no question (ASSESSED); unreliable prices recorded as gaps: 6 |
| every other filing older than 6 months: prices off, gap recorded |  | T135-T164 loop, `every other filing older than 6 months: prices off, gap reco` | **Couldn't check, and says so** | no question (ASSESSED); gaps recorded: 6 |
| masons filed by only 2 other agencies: honest not asked, 2.4x is |  | T135-T164 loop, `masons filed by only 2 other agencies: honest not asked, 2.4` | **Couldn't check, and says so** | honest nothing; at 2.4x ['LABOUR_RATE_FAR_ABOVE'] (compared with trade at 2.0x) |
| one agency files most forms, 30% under: the honest road not asked |  | T135-T164 loop, `one agency files most forms, 30% under: the honest road not ` | **Couldn't check, and says so** | 10 forms by one agency at 70% of the usual rates: nothing (ASSESSED) |
| only 4 other filings in the district: prices off, gap recorded |  | T135-T164 loop, `only 4 other filings in the district: prices off, gap record` | **Couldn't check, and says so** | no question (ASSESSED); data gaps recorded: 6 |

### All four together

| Loophole | How it works | Found | Today | Detail |
|---|---|---|---|---|
| HTML and script in the description: judged as text, no crash |  | T168 promptfoo, `HTML and script in the description: judged as text, no crash` | **Caught: asked** | the form check stayed right |
| NaN and Infinity as rates: the form is not ready, no crash |  | T168 promptfoo, `NaN and Infinity as rates: the form is not ready, no crash` | **Caught: asked** | the form check stayed right |
| a 50 KB description: judged, no crash |  | T168 promptfoo, `a 50 KB description: judged, no crash` | **Caught: asked** | the form check stayed right |
| a 500 KB form: refused as too large (413), as the route does |  | T168 promptfoo, `a 500 KB form: refused as too large (413), as the route does` | **Caught: asked** | the form check stayed right |
| a homoglyph agency name (Cyrillic a) on a repeat: still asked |  | T168 promptfoo, `a homoglyph agency name (Cyrillic a) on a repeat: still aske` | **Caught: asked** | the form check stayed right |
| a negative quantity: the form is not ready, no crash |  | T168 promptfoo, `a negative quantity: the form is not ready, no crash` | **Caught: asked** | the form check stayed right |
| a rate written in words: the form is not ready, Cost never clears it |  | T168 promptfoo, `a rate written in words: the form is not ready, Cost never c` | **Caught: asked** | the form check stayed right |
| inject (English) into a padded estimate: still asked |  | T168 promptfoo, `inject (English) into a padded estimate: still asked` | **Caught: asked** | the form check stayed right |
| inject (English) into an honest form: still clean, nothing new |  | T168 promptfoo, `inject (English) into an honest form: still clean, nothing n` | **Caught: asked** | the form check stayed right |
| inject (Hindi) into a repeat on an old road: still asked |  | T168 promptfoo, `inject (Hindi) into a repeat on an old road: still asked` | **Caught: asked** | the form check stayed right |
| inject into the rebuild reason: still asked |  | T168 promptfoo, `inject into the rebuild reason: still asked` | **Caught: asked** | the form check stayed right |
| the repeat with its pin swapped (lat, lon): never "nothing sanctioned here" |  | T168 promptfoo, `the repeat with its pin swapped (lat, lon): never "nothing s` | **Caught: asked** | the form check stayed right |
| the whole form in Devanagari: an honest work stays clean |  | T168 promptfoo, `the whole form in Devanagari: an honest work stays clean` | **Caught: asked** | the form check stayed right |
| zero-width characters in the title of a repeat: still asked |  | T168 promptfoo, `zero-width characters in the title of a repeat: still asked` | **Caught: asked** | the form check stayed right |

### Scoring

| Loophole | How it works | Found | Today | Detail |
|---|---|---|---|---|
| Scoring MPs by their history | Considered and rejected: lighter checks for "low-risk" MPs, a cold start for new ones, a loop feeding on its own flags. | T052, 1 Oct 2026, `M-SYS-3` | **Fixed (guarded by a test)** | Never scored (AGENTS.md rule 5): works, offices and agencies only; no MP's name ever reaches a work's record from the form. Guard: `tests/cost_form/test_pswif.py::test_the_work_record_carries_the_form_and_never_an_mp_name`. |

### Data loading

| Loophole | How it works | Found | Today | Detail |
|---|---|---|---|---|
| A data reload erasing what people saved | load_db emptied the works; saved cost forms and site visits point at them, so the reload failed, and CASCADE would have erased them. | T169, 20 Oct 2026, `M-SYS-4` | **Fixed (guarded by a test)** | Works are replaced in place; a work with a saved form or visit is never deleted. Guard: `tests/test_reload.py`. |

### Form page

| Loophole | How it works | Found | Today | Detail |
|---|---|---|---|---|
| The form page gave a wrong reason when Cost could not check | After a rate change Cost waits for a reason (the total differs from the MP's amount); the page said "No prices to compare with". | T170, 20 Oct 2026, `M-SYS-6` | **Fixed (guarded by a test)** | The page shows the agent's own reason and the missing answer. Guard: `start-to-end browser check (T170 log)`. |
| The live demo check judged examples on the wrong day | Examples were judged on the data's snapshot day, not their own (6 of 13 wrong live). | T164, 9 Oct 2026, `M-SYS-7` | **Fixed (guarded by a test)** | The demo check uses the examples' own day (demo.as_of). Guard: `data/trial/work_form_examples.py (stops when the demo path differs)`. |

