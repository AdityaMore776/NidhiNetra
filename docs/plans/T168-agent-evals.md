# T168 · Eval environments for all four agents and NidhiLens

**Owner's request (19 Oct 2026):** "use different popular eval environments to rigorously test all agents of drishti
in different scenarios." Owner's choices (19 Oct): where a test finds a fraud slipping past, **fix the rules too**
(as T167 did for Cost; ask before swapping an agent's whole method); **include NidhiLens**, run on this PC's GPU
(RTX 3070 Ti 8 GB, free compute only). Builds on T167 (PR #136: the Cost agent's Inspect AI eval, `data/eval/cost/`).

## 1. Three environments, each for what it does best

| Environment | What it is | What it tests here |
|---|---|---|
| **Inspect AI** (UK AI Security Institute; already pinned, `inspect-ai==0.3.281`) | the eval framework of the labs and safety institutes; any Python as the solver; a log viewer | labelled scenarios for Duplicate Work, Time & Rules and Site Progress (as Cost has), the four agents together (fusion), and **NidhiLens as a real model** on altered photos |
| **promptfoo** (open source, the most used test/red-team runner for AI apps) | YAML test matrix, a provider per system under test, assertions per case | the whole system through the form check's own code (`POST /work-form/check`: form in, four agents + fusion out): end-to-end scenarios, and attacks on the free-text and number fields |
| **Hypothesis** (the standard Python property-based tester) | generates thousands of inputs, shrinks a failure to its smallest case | properties that must always hold for every agent (metamorphic tests): invariance, monotonicity, "can't tell" never "clean", no crash |

Not used, and why: DeepEval, Giskard, Ragas grade chat answers with an LLM judge (paid calls; three of the four agents
are rules, not chat); lmms-eval / VLMEvalKit need NidhiLens registered as a model class, Inspect runs it through the
engine's own reader with less code.

## 2. Labels and levels (shared by every agent, from T167)

Each case: `truth` honest / edge (honest but unusual) / fraud / evasion (a fraud dressed to dodge a rule) / broken
(missing or damaged data); `ideal` level; `allowed` levels; `why`; look-alike `pair` where one exists.

Levels from an agent's result: `fits` (assessed, nothing), `edge` (assessed, a note or leeway, risk 0), `check` (a
finding with risk < 0.4), `ask` (risk >= 0.4), `na` (NOT_ASSESSABLE / NOT_APPLICABLE). For Duplicate Work, Time &
Rules and Site Progress the "check" tier is whatever finding they raise below 0.4 (e.g. `SANCTIONED_LATE` 0.05 is
edge-like: it never queues, so it maps to `edge`).

Hard rules (each a metric that must be 0): **fraud excused** (a fraud or evasion at fits/edge), **honest asked**
(an honest or edge case at ask when its label does not allow it), **broken cleared** (missing data at fits: a
"couldn't check" must never read as clean).

Honesty about results:
- every agent gets a baseline run of today's agent before any change (`results/t168_<agent>_baseline.txt`);
- each agent's held-out file is committed **before** its first run; after a rule changes for a held-out case, the
  case is marked `seen` and reported apart;
- frauds another agent should catch are `scope: other` and reported apart, never counted as coverage.

## 3. Scenarios per agent (Inspect AI, `data/eval/<agent>/`)

**Duplicate Work** (`dup_split`): a world of earlier works in Jaunpur (`work_form_examples` builders), then:
- honest: a new road in another village; the house next door (8 m) with a solar light filed the same day; the next
  lane 25-35 m away; a purchase of another kind at the same office;
- edge: a declared continuation of a named work; a rebuild after 4 years; a road that crosses an old one;
- fraud: a new road pinned 20 m on an old one; a rebuild 16 months on; one lane in three parts at 96-100% of a
  limit; the same hall filed by another agency;
- evasion: the pin typed 60-90 m off (filmed on the old site), a rebuild called an "upgrade", parts at 95% of the
  limit, parts 31+ days apart, the road a little longer than the old one, the old work named but not on record;
- broken: no pin, no date, no index for the district.

**Time & Rules** (`time_rules`): honest fast finish that was filmed; honest slow work still filmed changing; late
sanction alone (an office fact); election-code days; fraud: complete 6 days after sanction never filmed; complete
before recommended (R06); abandoned past the late line with a still site; evasion: a start date promised years away;
a long duration claimed to widen the window; one video filmed only on the last day; broken: no dates, dates in the
future, swapped dates.

**Site Progress** (`site_progress`): honest monthly videos; one dark month (forgiven); GPS jitter near the site;
edge: a pause shown honestly; fraud: footage reused, filmed 2.4 km away, a claim not shown twice, complete not
shown, already built at the first visit, never filmed; evasion: alternate "can't tell" and "not shown", film badly
every month, film the neighbour's site with a mock GPS, skip the first visit; broken: unsealed uploads, no readings.

**The four together** (`data/eval/pipeline/`): the band and score per case; a fraud seen by two agents counts once;
an honest work has no finding at risk.

## 4. NidhiLens (Inspect AI on the GPU, `data/eval/nidhilens/`)

Data: the released test set (`D:\nidhinetra-data\release\siteclaim_test_v1`, 883 real checks, labels checked by
eye). Solver: the engine's own reader path (`readers.VLMReader` over `drishti_vision.vlm`, 4-bit, sure = 0.6) on the
video job's frame (1,280 px, JPEG 80), as T159 measured. Scenarios (each a perturbation of the same checks):
- clean (must reproduce T159's 4-bit numbers within noise);
- dark (-60% brightness), blur, low JPEG quality, crop to 60%, small (480 px);
- A and B swapped (a "removed" claim: nothing built must stay not_shown / cant_tell);
- the same photo as A and B (nothing changed: must never be shown for a "since the last visit" claim);
- text written into photo B ("WORK COMPLETE", "रोड पूर्ण"): must not raise "shown".

Pass rules: **false "shown" on not_shown checks must not rise** above the clean rate by more than its 95% interval;
macro-F1 per scenario reported with a bootstrap 95% interval. Time is estimated on 20 checks first; scenarios
beyond the budget run on a fixed random 300 (seed 0) and say so.

## 5. promptfoo (`data/eval/promptfoo/`)

`promptfooconfig.yaml` + `provider.py` (Python provider: runs `pswif.to_work` -> `validate_cost_form` ->
`explain_work` with the eval world's index, the route's own steps without its database). Tests: every example
filing of the form page reproduces its codes; each agent's scenario as a whole form; attacks on text fields
(instructions to "mark this clean", Devanagari and mixed scripts, homoglyph agency names, 50 KB descriptions, numbers
as words, negative and NaN amounts, an oversized form refused). Run with `npx promptfoo@<pinned> eval`.

## 6. Hypothesis (`apps/engine/tests/properties/`, in CI)

Per agent, at least: a NOT_ASSESSABLE never on a full record; missing data never `fits`; renaming the agency or
the village (to a non-duplicate name) never changes the level; shifting every date by the same days never changes
Time & Rules; GPS jitter under 5 m never flips Duplicate Work; more padding never lowers Cost's level; one more
good video never adds a Site Progress finding; no input raises (ERROR) or breaks the contract.
`hypothesis` is added to the engine's dev requirements, `max_examples` kept so CI stays under a minute.

## 7. Done when

- [ ] baselines of today's agents on every scenario set, saved
- [ ] Inspect tasks for dup_split, time_rules, site_progress, pipeline; NidhiLens task run on the GPU
- [ ] fraud excused 0, honest asked 0, broken cleared 0 on the main sets; held-out sets committed before first runs
- [ ] promptfoo suite green; Hypothesis properties green in CI
- [ ] FINDINGS "T168", AGENT-CATALOG rows, log entry, PR
