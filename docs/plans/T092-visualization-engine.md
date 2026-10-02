# T092 · DRISHTI Visualization Engine: a step-by-step picture of what happens to a work

**Owner's request, 2 Oct 2026:** "a website whose whole purpose is to visually show what data is going in (it lets
you input your own example as well), and shows with pictures, animations and visualization what exactly is
happening at each step, simple to understand ... similar to how visualization websites work for a convolutional
network ... each step can be played again ... for judges that hardly know the technical stuff."

## What the judge sees (one public page, `/explain` on the live site)

Six steps on a track, each with Play / Replay, and Play all:

1. **The work goes in.** The record card fills in field by field (what, where, how much, dates, office).
2. **Private details are hidden.** A scan line sweeps the description; names and phone numbers flip to [name] /
   [phone]. Nothing personal goes further.
3. **Reading the description.** Words light up one by one by what they are: a place, a quantity (length, count),
   goods or a construction, a word from the not-allowed list, a hidden detail. The facts read appear beside it.
4. **Seven checks look at it at once** (like a network's channels): each engine lights up with its own small
   picture. Rules ticking through a checklist; the price dot landing on the band of similar works; the district's
   other works drawn as dots, the closest ones joined by lines with their likeness; the dates on a timeline against
   the guideline clocks; the office's habit against the national share; papers and photos (not attached here).
5. **Adding up the score.** Each question becomes a chance (how often that kind was right when read × how strong
   it is); the chances combine into one score that rises past the MEDIUM / HIGH / CRITICAL lines.
6. **What the officer gets.** The band, the queue or not, the top three reasons in plain words; DRISHTI never
   decides, the officer does.

## Where the numbers come from (only real engine output)

- One function in the engine, `drishti/explain.py`, runs a work through the same pipeline as the batch and
  returns a **trace**: the masked input, what the readers extracted, every engine's result with the data its
  picture needs, and the score's arithmetic step by step. Nothing in the page computes a score.
- **Built-in examples** (no sign-in, always fast): made-up recommendations placed in real districts and run
  through the real engines on the eSAKSHI dashboard's 40,935 works (`data/trial/explain_examples.py`, saved to
  `apps/web/public/explain/examples.json`, descriptions masked). Labelled as such on the page.
- **Your own example:** `POST /api/v1/explain` on the live engine, behind the same sign-in as the pre-sanction check
  (no new public access to the hosted database). Signed out, the page says to sign in with the demo account.

## Done when

- [x] `explain()` + route, tests: the trace's score equals the pipeline's; nothing private or accusing in it;
  odd input never fails
- [x] examples script run on the dashboard data; the page works with them signed out
- [x] page: six steps animated, each replayable, Play all; own example via the API; works on a phone
- [x] web `tsc`, `lint`, `build` pass; checked in a real browser (screenshots)
- [x] FINDINGS / ARCHITECTURE / TASKS, log entry

## Built (2 Oct 2026)

- Engine: `drishti/explain.py`, `POST /api/v1/explain`; tests `tests/test_explain.py` and the API test.
- Examples: seven (an "ordinary" one, five single questions, and "two checks agree", the only CRITICAL), built by
  `data/trial/explain_examples.py`; numbers in FINDINGS "T092".
- Page: `apps/web/src/app/explain/` (`page.tsx`, `Explainer.tsx`, `steps.tsx`, `explain.css`), types in
  `src/lib/explain.ts`; linked from the login page and the app's menu ("Step by step").
- Animations are CSS only (no new library); a step replays by being mounted again; `prefers-reduced-motion` turns them
  off. Play all moves on when each step's animation has played; the arrow keys step through.
