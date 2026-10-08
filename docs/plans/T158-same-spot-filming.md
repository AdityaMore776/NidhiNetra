# T158: film from the same spot every month, and more spots for big works

> **Status (8 Oct 2026): built, PR #124.** Engine, API, phone page and work page done; 1,019 engine
> tests, web build green; the replay (`data/trial/t158_replay.py`) and the real-browser run with a
> compass (`data/trial/capture_e2e.py`) behave as below. **Next: the owner's walk test on a real phone.**
> Changes from the first draft, each found while building (all below are the built version):
> - §D combining: a spot that does not face the part a claim names answers "not shown" too, so only a
>   claim about the WHOLE work is "not shown" on one spot's contradiction; a one-part claim needs every
>   filmed spot to agree and half the needed spots filmed (`spots.combine`).
> - §A spot: GPS fixes during the viewpoint ±0.5 s (not ±2 s: the walk up to it is not the spot); with
>   none, the last good fix up to 60 s before stands (a phone standing still sends no new fix; found by
>   the browser run).
> - §B the facing is kept even when the GPS is unusable (it no longer hangs on the box; browser run).
> - No compass gives "can't tell", never "0% panned" (found by the replay).
> - `MAX_JUDGED_SPOTS` is 12, not 8: a long road asks 8 stretches, plus the viewpoints.

Owner's request (8 Oct 2026): mark where the person stood to film the work; next time, tell them to
stand in that box and show the same areas again; when the work is too big to show from one spot (by
the size the form gives), ask for more spots, and judge by what was actually shown. Design agreed
with the owner on 8 Oct 2026. Issue #123.

## What exists today (T123, T136)

- The capture page (`apps/web/src/app/(app)/capture/page.tsx`): the first visit marks at least 2
  viewpoints while filming; later visits show last month's picture faintly, to line up each one.
- After upload, `video/visit.py` re-finds each viewpoint by picture matching
  (`views_match_site`).
  - GPS only says whether the phone was inside the site (a circle round the form's pin, ±20 m).
  - The claim is judged once, from all the pictures together.
- What's missing:
  - no standing spot or facing is saved for a viewpoint, so nothing guides the person back to it;
  - the number of viewpoints doesn't depend on the work's size;
  - the verdict doesn't say how much of a big work was shown.

## Design

### A. What a visit saves for each viewpoint

The phone logs the compass, beside the GPS and motion it already logs:

```
"heading": [{"t": 4.2, "h": 131.0, "p": -8.0}, ...]   # compass degrees (0 = north), tilt
```

- **Android Chrome:** `deviceorientationabsolute`, with heading = (360 − alpha) mod 360.
- **iPhone Safari:** `webkitCompassHeading`, after `DeviceOrientationEvent.requestPermission()`
  from the Start tap, like motion today.
- **No compass:** the log has no headings, and everything below that needs them says "can't
  tell".

`video/visit.py` adds these to each viewpoint in `kept["viewpoints"][id]`:

| Field | What it is |
|---|---|
| `spot` | `{lat, lon, acc}`: the median of the GPS fixes from 2 s before to 2 s after the viewpoint, using only fixes better than `GPS_POOR_M`; `acc` is their median accuracy. None when there are no such fixes. |
| `facing` | `{mid, from, to}`: the smallest arc (on the circle, wrapping past north) that holds the viewpoint's headings, and its middle. None without headings. |
| `pans` | Three pictures: the usable frames nearest the moments the phone faced `from`, `mid` and `to`, or at 1/6, 1/2 and 5/6 of the viewpoint without a compass. Faces are blurred, like the key frame. |

Nothing new is a column: `kept` and `log` are JSON already, so **no migration**.

### B. The anchor, and what the next visit is told

`api/site_visits._viewpoints` returns, for each viewpoint:
- `frame_url` (as today);
- `anchor {lat, lon, acc, box_m}`;
- `facing {mid, from, to}`;
- `pan_urls` (3).

- **Anchor = the first trusted visit's spot with `acc ≤ GOOD_FIX_M` (15 m).** "Trusted" means the
  views matched, the GPS was not outside the site, and there was no mock location. Until such a
  visit exists, the anchor is the trusted spot with the best accuracy.
  - So the anchor can move only while every earlier fix was poor, and once a good fix exists it
    never moves.
  - This stops the box creeping a little each month.
- **`facing` comes from the same visit as the anchor**, so the arc to cover is the one first set.
  It can't shrink month by month.
- **`pan_urls` are the newest trusted visit's**: what it looked like last time.
- **`box_m` = `max(BOX_M, anchor acc)`** with `BOX_M` = 6 m: a box about 12 m across, since phone
  GPS is about 5 m in the open.

The phone (`capture.ts` + page) shows, per viewpoint still to film:
- **The radar** (SVG, no map tiles, so it works offline):
  - your dot in the middle and the box at its bearing and distance;
  - "Spot v2: 23 m, ahead-left";
  - it turns green when `distance − current accuracy ≤ box_m`.
  - With a compass, "up" on the radar is the way the phone faces; without one, up is north.
- **Facing:** while at a viewpoint, a compass arrow ("turn right 40°") until the heading is within
  `FACING_TOL_DEG` (20°) of the anchor's `mid`.
- **The arc:** last time's arc drawn as a grey band, which fills as the phone pans across it,
  with last time's 3 pictures as thumbnails under the video.
- **Warnings only, never a block** (owner's choice): "v2 marked 18 m from its box" or "v2: 40% of
  last time's view panned".
  - They are noted in the log's `tips`.
  - The engine recomputes everything from the raw log.

### C. How many spots a work needs (`sitemap.spots_needed`)

**Compact works** (building, toilet, shelter, pond, ground, check dam, tank, and others with one
pin):

```
side   = the form's length_m when given (shelter, check dam), else
         sqrt(2 × footprint)     # a 2:1 rectangle, the usual shape of a school block or a hall
footprint = built_up_area_m2 / floors_nos | area_m2 | water_area_m2
spots  = clamp(2 × ceil(side / VIEW_REACH_M), 2, MAX_SPOTS)
```

- `VIEW_REACH_M` = 40: the distance at which a phone video still shows building detail (brick
  courses, plaster, a slab edge).
- **Spots come in pairs at opposite corners**, because a building's back can't be seen from its
  front. Hence two spots for every 40 m of side.
- **No size on the form:** 2 spots (today's minimum).
- **`MAX_SPOTS` = 8**, so a very large pond or ground isn't asked for dozens.

| Example | Footprint | Side | Spots |
|---|---|---|---|
| 10×10 m room | 100 m² | 14 m | 2 |
| 30×15 m school block | 450 m² | 30 m | 2 |
| 60×40 m hall | 2,400 m² | 69 m | 4 |
| 100×60 m ground | 6,000 m² | 110 m | 6 |

**A fix found while reading `site_of`:** the site circle ignores `water_area_m2`, and it uses
all floors' area. It will use the same footprint, so a pond gets its real size and a 3-floor
building isn't treated as three times wider.

**Linear works** (road, path, drain, wall, embankment, pipeline, power line; the form gives both
ends):
- every `STRETCH_M` (50 m) stretch up to `LONG_LINEAR_M` (1 km);
- longer works: `SAMPLE_STRETCHES` (6) stretches drawn at random, plus the first and last
  stretches.
  - The draw is seeded by `HMAC(capture secret, visit_id)`, so nobody outside the server can
    know it before filming starts, and the engine can recompute it.
  - `/site-visits/start` returns them as `stretches_asked`.
- **A stretch counts as a spot.** The visit keeps the sharpest frame filmed while the GPS was in
  that stretch, as viewpoint `s<n>`, so it can be compared next time like any spot.

### D. Judging by what was shown

- **Each matched spot is judged on its own:** `judge([claim], [before-<id>, now-<id>])`, up to
  `MAX_JUDGED_SPOTS` (8). Same reader, same question, one spot at a time. This is exactly the
  pair NidhiLens was trained on, so T159 plugs it in here.
- **New readings:**
  - `spots_needed`, `spots_filmed`;
  - `spot_verdicts {id: shown | not_shown | cant_tell}`;
  - `spot_offsets_m {id: metres from the anchor}`;
  - `spot_coverage {id: share of the anchor arc panned}`.
- **They combine into `claim_verdict`:**
  - **`not_shown`** when any spot says not_shown and the video quality is OK.
    `claim_spots_not_shown` lists those spots.
  - **`shown`** when at least one spot says shown, none contradicts, and `spots_filmed ≥
    ceil(spots_needed / 2)`.
  - **`cant_tell`** otherwise.
- **Agent (`agent.py`):**
  - The existing rule stays: CLAIM_NOT_SHOWN needs two visits in a row. Its text now names the
    spots, for example "not shown at spot v2 on both visits".
  - Fewer spots filmed than needed is a note ("2 of 4 spots filmed: part of the work was not
    judged"), never a finding: couldn't check isn't a low score.
  - Being far from the box, or a short pan, is a room-for-error note. A visit's place is decided
    by the picture match, as today.
- **The officer's work page** gets one line per visit: "Spots: v1 ✓ shown · v2 ✗ not shown · v3
  not filmed".

### E. Constants (one place each, engine and web mirrored like `outsideBy`)

| Constant | Value |
|---|---|
| `VIEW_REACH_M` | 40 |
| `MAX_SPOTS` | 8 |
| `BOX_M` | 6 |
| `GOOD_FIX_M` | 15 |
| `FACING_TOL_DEG` | 20 |
| `COVER_GOOD` | 0.7 |
| `LONG_LINEAR_M` | 1000 |
| `SAMPLE_STRETCHES` | 6 |
| `MAX_JUDGED_SPOTS` | 8 |

## Build steps (tests first for every engine step)

1. **`sitemap.py`:**
   - `footprint_m2(form)` and `spots_needed(site, form)`;
   - the radius uses the footprint;
   - `stretches_asked(site, visit_id)`.

   Tests: the table above; no size gives 2; the cap; a 3-floor building; a pond by water area; a
   road under and over 1 km; the draw is stable for one visit and different for the next.
2. **`video/visit.py`:**
   - `_spot`, `_facing` (circular arc, wraparound at north), `_pans`;
   - stretch keyframes for linear works;
   - per-spot judging and the combination.

   Tests:
   - spot = median of the good fixes;
   - an arc across north (350°→20°);
   - no compass gives facing None and pans by time;
   - each verdict rule (a contradiction wins, half the spots needed for shown, too few gives
     can't tell);
   - a dark video never says not_shown.
3. **`api/site_visits.py`:**
   - the anchor rule (the first good fix; it moves only while every fix was poor), `box_m`,
     `facing`, `pan_urls`;
   - `spots_needed` and `stretches_asked` in GET and in `/start`.

   Tests on the existing fake connection.
4. **`agent.py`:** spot names in CLAIM_NOT_SHOWN, the spots-filmed note, the off-box and short-pan
   notes. Tests, including a NOT_ASSESSABLE case (no visits).
5. **Web:**
   - **`capture.ts`:** compass logging in `Recording`, plus `bearing`, `boxDistance`, `turnBy` and
     `arcCovered`, mirrored from the engine with small tests where the repo has them;
   - **the page:** the radar component, the facing arrow, the arc and thumbnails, spots needed
     on the first visit, the warnings;
   - **`api.ts`:** the types.
   - **The work page's spot line.** Then `npx tsc --noEmit`, `npm run lint`, `npm run build`.
6. **Replay check:** a script feeds recorded logs (GPS, compass, viewpoints) through the engine
   readings: someone standing in the box, someone 25 m off, someone who pans half the arc, and a
   phone without a compass. Its output is saved to `data/trial/results/t158_replay.txt`.
7. **Docs:** HOW-IT-WORKS and AGENT-CATALOG (Site Progress), STATUS, a log entry.

## Proof before it counts (rule 4)

- **Automatic:** the engine tests, the web checks and the replay check, all green.
- **Real:** the owner walks round any building once as a first visit and once as a monthly visit,
  then reads the readings back. Until then the guidance is live (it only helps), and the per-spot
  verdicts show on the work page as "new". The existing two-visits rule for CLAIM_NOT_SHOWN is
  unchanged, so no new flag can appear from this work alone.

## Out of scope

- Live picture matching on the phone (OpenCV.js): only if the walk test shows people can't line
  up.
- A native AR app.
- Street lights and other works spread over many points of a village (they need one spot per
  point: a later task).
- Serving NidhiLens (T159).
