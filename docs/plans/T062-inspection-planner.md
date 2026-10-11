# T061 + T062: Location lookup and the Inspection Planner

**Owner's choices (11 Oct 2026):** build the planner on the real works, with a village lookup (T061) rather than
made-up pinned filings; compute each plan on request (no new table, no database reload); route order by exact
search instead of OR-Tools. Blueprint section: `docs/specs/2026-09-27-nidhinetra-blueprint.md` ("Inspection Planner").

## What an officer gets

Pick a district (and, if wanted, the hours in the day). The planner returns one day's visits:
- a map with numbered stops, each marked **village** (found by name, approximate) or **district centre** (rough);
- the stops in driving order with arrival times;
- for each stop, a short checklist taken from the work's top reasons ("check the completion certificate and dates");
- the flagged works that did not fit, as the **next trip**;
- the km saved against visiting the same works in list order.

Words follow the project rules: "needs checking", never an accusation. Spot checks are labelled as random, so a
visit to them says nothing about the work.

## 1. Location lookup (T061): `drishti/planner/locate.py`

- **Reference file** `reference/post_offices.json.gz`, built by `data/build_post_offices.py` from India Post's
  office directory with map positions (the `indiapins` package, MIT; data from India Post's public pincode
  directory). Each office is placed in a district by its **position**, inside the official LGD outlines
  (`reference/district_outlines.json`, keyed by the census code works carry; never joined by number). Offices
  whose India Post district name disagrees with the outline they fall in are counted in the build log; the build
  decides from that count whether to drop them.
- **Matching** a work: its description's words against the office names of **its own district only** (office
  suffixes such as B.O / S.O / H.O removed). Whole-word matches only; names on a generic-words list (market,
  road, school, ...) and names under 4 letters never match. A name held by several offices more than 5 km apart is
  ambiguous and does not match. Of several matched names, the one after a place cue (village, vill, gram, at, in,
  near, panchayat) wins, else the longest.
- **Fallback**: the district's head office position, else the outline's centre: precision `district`.
- Output `Location(lat, lon, precision: "village" | "district", place: str | None)`.

## 2. The plan (T062): `drishti/planner/plan.py`, pure functions

- **Candidates**: the district's review-queue cases (band CRITICAL or HIGH, one stop per case, the same rule as
  the queue page; the blueprint's "risk >= 40" predates the calibrated bands, where HIGH starts at 50) plus
  **spot checks**: 10% as many random lower-risk works from the same district (at least 1), drawn with a seed
  from the plan's inputs, so the same request gives the same plan.
- **Value** = the stored priority = risk x (1 + log10(amount in lakh)), capped as the queue caps it. Spot checks
  get a small fixed value so they fill spare time but never push out a flagged work.
- **Travel**: straight-line km x 1.3, at 30 km/h; 40 minutes at each stop; the day starts and ends at the
  district's head office; default budget 8 hours.
- **Greedy**: repeatedly add the candidate with the highest value per extra minute (the cheapest insertion into
  the current route) while the day still fits.
- **Route order**: exact (Held-Karp) up to 12 stops; above that, nearest neighbour + 2-opt.
- **Km saved**: the same chosen stops visited in queue order (highest priority first) against the planned order.

## 3. API and page

- `POST /api/v1/plans/generate {district, hours?, date?}` -> the plan, with an `id` that encodes its inputs.
- `GET /api/v1/plans/{id}` -> the same plan again (recomputed from the id; nothing stored).
- Web page `/planner`: district picker, MapLibre map with numbered stops, stop list with checklists, next trip.

## 4. Proof (done when)

- Tests: place matcher (cue word wins, ambiguous name, generic word, other district's office never used), greedy
  step and budget (never over the hours; higher value per minute first), route search (exact = brute force on
  small cases), the id round trip, the API on the test database, `NOT_ASSESSABLE`-style case: a district with no
  queue works gives an empty plan with a reason.
- `data/trial/t062_planner.py`: on every district with queue works, the share of stops found at village level,
  and km saved against list order; 30 random village matches read by eye. Results in `data/trial/results/`.
