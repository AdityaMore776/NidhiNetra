# T141: a labour schedule, judged trade by trade, only for blatant irregularities

**Owner (6 Oct 2026):** "Labour isn't paired fairly, depends on what the workers are and what they
are doing, so it would be better to have a whole different field to put in detailed worker rates,
what workers you are using, etc, and then judge that ... we just need to detect blatant
irregularities, none of the 'can still be made with lower amount of workers' or 'doesn't need
this many', some projects might need that amount of workers to get the project done."

## What is wrong today

| Problem | Where |
|---|---|
| No labour section: labour is an ordinary estimate line, recognised by a word ("mason", "labourer") | website form section F, `pswif._lines` |
| Two kinds only: "skilled" lumps mason, carpenter, plumber, electrician, welder together; machine operators, drivers and supervisors have no home | `cost_form.yaml` materials `labour_skilled`, `labour_unskilled` |
| A welder or an operator is priced against the district's "skilled" rate, which is mostly masons | `rates.price_line`, `whole.judge` |
| Nothing stops calling a helper "skilled" to get the skilled rate | the item's words decide the kind |
| A worker on site longer than the whole work lasts is never noticed | nothing reads days |
| Labour can be paid twice: inside a composite schedule-of-rates item (which includes labour) and again as a labour line, or with a machine hired with its operator | nothing links them |

Real rates show the kinds differ (UP PWD Schedule of Rates 2025-26, Jaunpur-Ghazipur, typed on the
T096 branch, not merged). In Rs a day:

| Trade | Rs a day |
|---|---|
| beldar | 423 |
| semi-skilled | 465 |
| mason grade-II | 465 |
| mason grade-I | 525 |
| carpenter | 525 |
| mate | 525 |
| supervisor | 529 |
| chowkidar | 423 |

Market wages run above these floors.

## The design

**1. A labour schedule on the form.** One row per trade:
- **trade:** from a list, or "other" with its name;
- **grade:** unskilled, semi-skilled, skilled or highly skilled. It is filled from the trade, and
  required for "other";
- **numbers:** how many workers, the days each is on site, and the day rate;
- **why:** what they do, and which estimate lines they work on;
- **rate source:** where the rate comes from.

The amount is workers × days × rate. Each estimate line says whether its rate already includes the
workers who do it (a composite schedule item, or a machine hired with its operator).

In the engine form, a row is a line in group `labour`. Its fields are `workers`, `days`,
`activity`, `for_lines` and `grade`, with quantity = workers × days in unit `day`. So the rate
index, the whole-estimate check and validation all read labour like any line.

**2. Trades in the catalogue**, each with its own grade:

| Grade | Trades |
|---|---|
| unskilled | beldar / mazdoor, helper, chowkidar |
| semi-skilled | mate |
| skilled | mason, carpenter, bar bender, painter, plumber, electrician, welder, driver |
| highly skilled | machine operator, supervisor |

The four grade words stay as generic entries, used only when no trade name fits. A typed "skilled
mason" is a mason. Hindi names are included (mistri, badhai, beldar, mazdoor, chowkidar, chalak ...).

**3. Judged against its own trade, never its declared grade.** The fair rate of a row is what other
agencies in the district pay the same trade (the rate index, as for materials).
- If there are too few forms, the state's agencies are used.
- If the trade itself has too few forms anywhere, the grade's pool of trades is used, and only for
  the blatant check below.

A declared grade above the trade's own grade changes nothing. It is a note, and the form asks the
agency to confirm it.

**4. Only blatant irregularities are questions:**

| Code | When | Why it is blatant |
|---|---|---|
| `LABOUR_RATE_FAR_ABOVE` | a trade's day rate is at least 2× what other agencies pay that trade here (2.5× its grade's pool when the trade has too few forms), and the extra comes to at least Rs 10,000 over the work | within one district a trade's honest wages differ by tens of percent, not double |
| `LABOUR_DAYS_BEYOND_WORK` | a worker's days on site exceed the work's own time to completion by more than 10%, and the agency confirmed it | no one works more days on a work than the work lasts |

The whole estimate still prices every labour row at its trade's fair rate × the person-days
stated (`ESTIMATE_ABOVE_FAIR_PRICE`), so a padded rate counts there too.

**5. Mistakes the form refuses** (an honest slip is fixed on the agency's screen, never an officer's
question; T093):
- workers × days ≠ the person-days;
- workers not a whole number of at least one, or days not more than zero;
- an "other" trade with no grade;
- a labour row working on a line whose rate already includes labour (paid twice);
- on the new form, a labour line among the estimate lines instead of in the labour section.

**6. Not judged, on purpose (the owner):**
- how many workers;
- how many days within the work's time;
- labour's share of the estimate.

A work may need many operators, or many hands.

## Loopholes to try (the robustness loop, T135)

| Try | Expected |
|---|---|
| helper called "highly skilled", paid a mason's rate | judged as a helper: asked if 2× a helper's rate |
| an unknown trade name, or a Hindi name | Hindi trades are recognised; an unknown one is judged at its declared grade's pool |
| one trade split in two rows, one at 3× | each row judged |
| labour moved back among the estimate lines | the new form refuses it |
| labour paid inside a composite line and again | the form refuses it |
| days on site beyond the work's time | asked when confirmed |
| person-days inflated within the work's time | not asked (the owner's choice): a LIMIT |
| a composite line declared "no labour" | a LIMIT until the schedule of rates' item codes are loaded (T096) |
| operators paid more than helpers, many workers, a high-wage district | not asked |
| junk in every labour field | no error |

## As built (6 Oct 2026), after the robustness loop

- **Fallback when a trade has too few forms:** its grade's pool at 2.5×; when the grade has none,
  the nearest grade with forms (a higher one first), with 1.25× more room for each grade below
  (`labour.GRADE_STEP`; at 1.5× a step, masons at 2.4× went unasked where only labourers had
  forms).
- **The whole estimate:** a labour row within twice its trade's rate is settled. It adds nothing to
  the gap and stays out of the share's base, so neither an honest wage premium nor a large honest
  crew moves the verdict. A row citing a schedule item is held to that item's rate like any line.
- **A labour line among the BOQ lines** is asked to move (a confirm, not a refusal: "JCB with
  operator" is a machine) and is still judged as its trade. A machine hired "with operator" by the
  hour is read as a machine.
- **A row with no trade chosen** is refused (a trade is the row's identity); "Other" needs its
  grade; the lines a row works on are needed when any line's rate includes its workers.
- Results: FINDINGS "T141".

## Measure (planted forms, `data/trial/labour_trial.py`)
- **Honest districts:** each trade's market wage, every agency within an honest spread.
- **Honest forms:** honest asked must be at most 1%.
- **Padded forms:** the share caught at 1.5×, 2× and 3× a trade's rate, by grade inflation, and by
  days beyond the work.
- **Margins:** the 2× / 2.5× are starting values. Real forms (T098) set the final ones, with the
  owner's go-ahead.
