# T135: the four agents' self-improvement loop

The owner (5 Oct 2026): take each agent through samples, find every way it can give a wrong answer,
be bypassed or stop working (random variability, missing or bad data), fix it, and keep iterating
until the agents are robust. Where the data is too thin to trust (a price), switch that one check
off rather than guess, and learn from the gap.

## The loop

1. **Attack**: `data/trial/agent_robustness_loop.py` runs the four agents exactly as production does
   (`assess_work`, the district's index rebuilt with the changed filing in it) on the work form's
   example filings in Jaunpur (made-up agencies, on top of the district's 1,038 real eSAKSHI works).
   Each probe changes a filing, or the data around it:
   - **damage**: random junk in any field of the website form, the engine's own form, the site
     videos' readings and the record. No agent may crash, break the contract or answer differently
     twice.
   - **noise**: what an honest form varies in (rates a few % apart, lines reordered or split, other
     words, units or a language for the same item, GPS jitter, rounded pins, GST in "other
     charges", one bad GPS fix). No answer may flip.
   - **evasion**: what a dishonest agency would try. The agent must still ask, or say plainly what it
     could not check.
   - **scarce**: too little or untrustworthy data. The agent must switch that check off for that
     item (never a wrong question) and record the gap.
   - **scale**: a district with 3,000 filed roads; one check must stay under 2 s.
2. **Read**: each probe ends PASS, FAIL or LIMIT. A LIMIT is a known edge of a measured rule (for
   example, padding just under the 15% line), written down with its reason so nobody mistakes it
   for coverage.
3. **Fix**: every FAIL is fixed in the agent, with a regression test in the engine suite (CI keeps
   it fixed). A probe that was wrong (testing the wrong thing) is fixed instead, and said so.
4. **Guard**: after each round, re-run the measurements the fixes could move: the full engine suite,
   the planted-form trial (`cost_whole_trial.py`), the dashboard's 40,935 real works
   (`dashboard_trial.py`, compared work by work), the example filings and the page in a browser.
5. **Repeat** with new probes for anything the fixes touched, until no FAIL remains.

Run: `apps\engine\.venv\Scripts\python.exe data\trial\agent_robustness_loop.py [--damage N] [--seed S] [--only text]`.
To add a probe: a function decorated `@probe(agent, kind, name)` returning `(verdict, detail)`.

## Data that cannot be trusted: off for that price, then learned

The Cost agent never guesses a price.

- **Off for that price.** A material's fair rate comes from the state's Schedule of Rates (T096,
  not loaded yet), else other agencies' recent forms in the district: 5+ forms from 3+ agencies,
  one vote per agency, rates that agree (interquartile spread at most 30%). Failing that, from the
  state's forms (8+ forms from 4+ agencies) with 10% more leniency. Failing that, the line is not
  priced.
- **Recorded as a gap.** Every unpriced material is recorded with its reason: no form, too few,
  too old, or the agencies disagree. The officer's result names it.
- **Learned.** `GET /api/v1/cost/data-gaps?district=` lists, for each material, where its price
  comes from or what would close the gap: the team's list of price data to collect. Every form an
  agency files joins the index, so a gap closes by itself once enough forms agree.

## What is still a limit (and why)

| Edge | Why it stays |
|---|---|
| Padding just under 15% | below it a gap is an honest spread (planted forms, T121) |
| Split pieces at 95% of a limit | looser splits read right 18 of 32 times (T100) |
| GPS faked inside the site, views elsewhere | one proof is a note by design (GPS error and changed views are common) |
| 22% padding priced only from the state's forms | a state-wide rate carries 10% for local prices: asked from about 27% |
| Every agency in a district padding together | only the state's Schedule of Rates (T096) can cap a district's own rate |
| A bigger size claimed consistently (field and scope) | the size is the agency's word: the site videos and the officer's visit check it |

## Next

- Load the Schedule of Rates (T096): it closes the two price LIMITs.
- Read the new findings on real forms (T098) to replace their 1-in-4 prior with measured rates.
- Site Progress could measure the built length and area from the videos' zones, closing the size
  LIMIT.
