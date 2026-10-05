# T137: other agent architectures, tested against the current ones

Asked for by the owner on 5 Oct 2026:

> test different agent architectures (remember the current ones, you are just testing right now)
> ... see which one runs the best and is the most accurate, and also doesn't have any problems or
> loopholes ... Test aggressively, then if it's better write it down in a log and only when it's
> proven to be better then you switch it.

## The rule for a switch
A candidate replaces the current design only when, on the same benchmark and at the same
false-alarm budget:
1. it asks no more honest cases, in every scenario;
2. it catches at least as much, and more somewhere;
3. it passes the robustness loop (`data/trial/agent_robustness_loop.py`) with no FAIL, and the
   loopholes closed in T135–T136 stay closed;
4. the examples and the dashboard's 40,935 works answer as before, except where the switch is
   meant to change them.

Where a benchmark rests on an assumption (honest spreads, the reader's error rate), the result
must also hold when the assumption moves (Site Progress: half to 1.5 times the error rates).

## What was tested (`data/trial/architecture_bakeoff.py`)

| Agent | Candidates | Outcome |
|---|---|---|
| Cost: the whole-estimate decision | current money gap; a calibrated gap; z-tests (independent lines, precision-weighted); z against the peers' own scatter; peer-adaptive money lines (stricter-only, banded); current OR a peer line; isolation forest | **kept**: the statistical tests read a remote site as padding, and ML catches half as much. "Current OR peer line" is better only on assumed tight districts: ready, not switched |
| Site Progress: decisions over the readings | current (T136); a 300 m rule for "elsewhere"; a sliding window; "4 of the last 5" unusable; "3 of the last 5" claims; a CUSUM running score | **switched** to 4 of the last 5 (or every video so far from the third) and the 300 m rule; claims kept ("twice in a row", owner's design; the reader's real error rate decides) |
| Duplicate Work: finding nearby works | full scan; a map grid of 550 m cells looked up within 200 m | **switched**: same answers, 8–10x faster |
| The score (fusion) | not re-tested | its labelled benchmark needs the research build, which is not on the build machine |

Two loopholes found on the way are closed: three bad videos and then no more filming, and a work
recorded complete with no final video (`COMPLETE_NOT_FILMED`).

Numbers: FINDINGS "T137".

## Next
- T098 (real forms): measure the honest spread of rates by district; if tight districts exist,
  re-run `architecture_bakeoff.py cost` with the measured spreads and adopt "current OR peer
  line" if it still wins.
- T126 (field trial): measure the reader's error rates; re-run `architecture_bakeoff.py site`
  with them, and settle the claim rule (twice in a row, or 3 of the last 5).
