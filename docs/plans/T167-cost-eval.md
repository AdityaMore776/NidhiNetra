# T167 · An eval environment for the Cost agent: frauds vs honest edge cases

**Owner's request (19 Oct 2026):** use a current, popular AI evaluation environment for the price checks, with edge
cases; evaluate the Cost agent deeply; change its rules or structure where that makes a better agent (a higher score
on a test set is not always better: understand which cases are honest edge cases and which are frauds); keep some
leeway for honest edge cases; **a fraud must never be classed as an edge case: at the least it reaches "check this".**

## 1. The harness

**Inspect AI** (UK AI Security Institute, open source, MIT): the eval framework the large labs and government
safety institutes use. It runs any Python as the "solver", so it runs the real engine, not a model; every case and
every answer lands in a log (`inspect view` browses it). Model is `mockllm/model` (no AI call, no cost).

Files:
- `data/eval/cost/cases.py`: the world (Jaunpur, honest background filings by other agencies) and the labelled
  cases. Plain Python, no Inspect needed, so tests and scripts use the same cases.
- `data/eval/cost/levels.py`: the agent's answer as one level (below).
- `data/eval/cost/task.py`: the Inspect task (dataset, solver = the Cost agent, scorers, metrics).
- `data/eval/cost/run.py`: the same cases without Inspect, writing `data/trial/results/t167_cost_eval.{txt,json}`.
- `apps/engine/tests/eval/test_cost_eval.py`: CI gate, no fraud excused, no honest case asked.

## 2. Levels (what the officer sees)

| Level | Meaning | From the agent |
|---|---|---|
| `fits` | nothing unusual | ASSESSED, no finding, no leeway used |
| `edge` | unusual, but a leeway explains it; a note, no risk | ASSESSED, no finding, `evidence.leeway` non-empty |
| `check` | "check this": beyond the leeway, below certainty | a finding with risk < 0.4 |
| `ask` | a question before sanction | a finding with risk >= 0.4 |
| `na` | could not judge (a status, not a clean chit) | NOT_ASSESSABLE / NOT_APPLICABLE |

Fusion: every Cost finding stands at the prior hit rate (1 in 4) until officers' verdicts are read, so `check` and
`ask` both put the work in MEDIUM; the level is the Cost agent's own wording and risk.

## 3. Labels and scoring

Each case is `honest`, `edge` (honest but unusual) or `fraud`, with a short story and why. Many come as **look-alike
pairs**: the same surface numbers, one honest and one a fraud (a small road +12% vs a big road +12%; a hilly site
+18% vs a plains site claiming hills +18%; a bigger solar spec at 1.4x the usual price vs the MP agreeing to an
inflated one).

| Truth | Pass | Soft fail | Hard fail |
|---|---|---|---|
| fraud (in scope) | `check`, `ask` | `na` | **`fits`, `edge` = fraud excused** |
| edge | `fits`, `edge` | `check` | `ask` |
| honest | `fits`, `edge` | `check` | `ask` |

Frauds the estimate cannot show (a size inflated everywhere) are labelled `scope: other agent` (Site Progress / the
officer's visit) and reported apart, never counted as coverage.

Each case runs in two worlds: honest agencies' rates a tight +-4% apart, and a wide +-10%; a level must hold in both.

## 4. The leeway principle (the structure change)

- **Verified leeway can clear** (to `edge`): other agencies here charge as much (within their own range); the gap is
  within CPWD's band for justified rates (Works Manual para 20.4.3.2: up to 5% ignored, up to 10% with recorded
  reasons); the money is too small to matter (below the floors).
- **Claimed leeway can only soften** (`ask` -> `check`, never to `edge`): what the agency says and nobody has
  verified yet: a hilly or remote site, a bigger specification, the MP agreeing, a written justification. A fraud
  can claim all of these.
- So a fraud is never excused: at the least it is `check this`.

Starting thresholds (measured and reset by the eval): whole estimate `check` from 10% and Rs 25,000 above its fair
price AND above the highest rates other agencies here charge; `ask` stays 15% and Rs 50,000.

## 5. Order

1. Cases + runner + Inspect task on the current agent: the baseline (results saved).
2. Read every miss: is it the case's label or the agent? Fix labels by argument, the agent by rule.
3. Change the agent (levels, leeway, the check tier, the gaps found), re-run, compare per case.
4. Tests, docs (FINDINGS "T167", AGENT-CATALOG, reliability.json for new codes), log, PR.
