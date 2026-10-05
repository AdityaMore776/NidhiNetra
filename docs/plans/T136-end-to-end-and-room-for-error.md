# T136: five filings end to end, Site Progress with room for error, one real region

Asked for by the owner on 5 Oct 2026 (after T135):

> create an end to end loop example (set of 5), of everything from form filling, all the way to
> agent risk on the form, then create a placeholder for the site progress agent which will be
> created and tested later. Put some legit values, then also put some things in other examples that
> will be flagged by the agents ... Site progress agent needs to be finished, easy to use, give you
> room for error and still do its job, the other agents should understand and flag relevant, be
> hard to find loopholes in and not crash ... try to find valid data, you can choose a single
> specific region or state.

## 1. Five filings, form to risk score (`/end-to-end`)

Four steps for each filing, played one after another or all at once:

1. **The agency fills the form**: the answers that matter by section, the estimate lines and their
   total, and the price per unit of size beside real works in Uttar Pradesh.
2. **The form checks itself** (`cost_form/validate.py`): ready to file, what it asked to fix or
   confirm, the estimate against the MP's amount.
3. **The agents read it**: Cost, Duplicate Work, and Time & Rules each say "asks" or "clear", with
   one line. Before sanction, Time & Rules also shows the window it will watch. **Site Progress is
   a placeholder**: it starts after sanction with the first site video, and joins once its field
   trial (T126) is done.
4. **The risk score**: each agent's chance and the running total, the band, and the officer's next
   step. A last line: the loop goes on after sanction.

The five filings (made-up agencies in Jaunpur; the record is the district's 1,038 real works):

- an honest road and honest solar lights, priced inside UP's real ranges;
- the road with money hidden in a line nobody prices;
- a lane split into pieces laid end to end (one described in other words);
- a "new" hall on a finished hall's site, overpriced and waiting past the 75-day clock.

`data/trial/end_to_end_examples.py` builds them through the live check's path and refuses any
filing that no longer raises exactly its questions.

## 2. Site Progress: room for error, still doing its job

| A person at a site... | Before | Now |
|---|---|---|
| films in poor light, or too briefly | the views "did not match": half of "filmed elsewhere" | "can't tell"; one such video is a note |
| stands under trees (GPS ±90 m) | GPS "outside the site" | each fix counts with its own accuracy; all poor: "can't tell" |
| misses a viewpoint one month | that viewpoint was lost from then on | every viewpoint the site ever had is compared, from its last 3 good frames |
| cannot reach a viewpoint (a truck, a flood) | the page would not upload | "Can't reach" on the page; not counted against the visit |
| is 150 m from a wrongly placed pin | the page would not upload | a tip; the views decide |
| films badly every month (the dodge) | never asked | two unusable videos in a row: `SITE_VIDEOS_UNUSABLE` |
| films elsewhere with the GPS faked inside, every month | a LIMIT | asked once repeated (views never match) |
| records the work complete with no video at all | asked 60 days after the start | asked at once |

A visit whose views did not match never becomes the site's reference. A dark video can no longer
prove that a claim is missing.

## 3. The other agents, round 6

What a dishonest agency would try next, and how it is closed (FINDINGS "T136"):
- sand doubled: an IS 456 sand norm, with bulking;
- money in a line nobody prices: unread items beyond 15% of a construction estimate;
- "Rs 464/-": read;
- lines with no rate: not ready;
- a split piece renamed: splits by map pin;
- a gravel road: keeps both ends;
- a hall 60 m off: a note.

Limits stay written down with their reasons.

## 4. One real region: Uttar Pradesh

The government sites cannot be reached from the build machine, so the region's real data is the
eSAKSHI dashboard tables: 8,702 UP works.
- **Test:** every agent on every UP work.
- **Train or not:** the Time caps against UP's own finished works. They hold within ±2.2%, so
  there are no per-state bands; a state with fast fake closures would make its own cap too strict.
- **Yardstick:** UP's real prices per unit of size for the honest filings.

When the PWD Schedule of Rates for UP (T096) or the first real forms (T098) arrive, the same
scripts take them.
