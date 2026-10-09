# Working on NidhiNetra

How the code is organised is in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md), and how to run it in
[`docs/SETUP.md`](docs/SETUP.md). Where the build stands: [`docs/STATUS.md`](docs/STATUS.md).

## Rules of the project

1. **Never accuse.** Officer-facing text says "needs verification" or "needs checking", never fraud, corrupt,
   scam or guilty. The engine rejects those words (`agents/contract.py`).
2. **"Couldn't check" is a status, not a low score.** `NOT_ASSESSABLE` / `NOT_APPLICABLE` carry no weight.
3. **Only measured numbers.** Every figure in the docs, the app or the deck comes from a script whose output
   is saved in `data/trial/results/`. Examples quoted as findings were checked by eye.
4. **Proof before launch.** A new check ships only with tests, a measurement on real data and an accuracy
   target it meets. If it misses, it stays off and the docs say so.
5. **Never score MPs.** Works, offices and agencies only.
6. **Privacy.** Never commit keys or passwords (`.env*`), real evidence files (`data/evidence/`), OCR text
   (`data/trial/cache/`), phone numbers, bank account numbers, or people's names from certificates. Run
   `python data/trial/sanitize_results.py` before committing trial results. Works are named by their work ID.
7. **Be polite to eSAKSHI.** The harvester keeps 1 request per 1.5 s, and only one harvester runs at a time.
8. **No competitor talk.** Nothing says NidhiNetra is better than another product or team. Benchmarks of
   our own models against general-purpose models (NidhiLens against Gemini) are measurements, published with
   their method and data.
9. **Satellite only for big works** (ponds, roads over 1 km, large buildings), and only after its go/no-go
   test passes.
10. **Free tiers first.** Anything that costs money is the project lead's decision.
11. **`main` is always the working live site.** Changes arrive through a pull request with green CI.

## Decisions already made

- **Four agents**, a quarter of the weight each ([`docs/plans/T120-four-agents.md`](docs/plans/T120-four-agents.md)):
  Cost (every line against the district's rates, then the whole estimate), Duplicate Work, Time & Rules (the
  75-day sanction clock and a comfort window from the form's estimated time to completion), Site Progress (a
  monthly site video from fixed spots, with GPS). Each flags only what is likely wrong, never a minor mistake.
- **Site Progress judges the agency's own claims** against the site's pictures and videos (shown / not shown /
  can't tell). It is never a fixed yes/no checklist.
- **Pre-2023 and post-2023 works are different populations** (eSAKSHI went digital around 2023) and are never
  pooled. The boundary keys on `recommended_date`, never on `fy`.
- **Simple and certain.** Cost asks only from the implementing agency's cost estimate form. Duplicate Work asks
  only by map pins (the form's, and where the site videos were filmed), the agency's own declarations, or the
  strictest split (every piece 96–100% of a limit); look-alikes by words are notes.
- **Cost margins.** A price question needs the price per unit more than 25% above the same standard item's
  98th percentile and the estimate more than 10% above the MP's amount.

## Adding a check to an agent

1. Write the failing test first, under `apps/engine/tests/agents/<agent>/`, including the honest cases the
   check must leave alone and a `NOT_ASSESSABLE` case.
2. Implement it in `apps/engine/drishti/agents/<agent>/`; findings are `Finding(code, text, risk=…,
   evidence=…)` inside an `AgentResult` (`agents/contract.py`).
3. Give the new finding its prior in `drishti/reference/reliability.json`; it counts 1 in 4 until officers
   have read real cases.
4. Measure it with a script in `data/trial/`, save the output in `data/trial/results/`, and record the numbers
   in [`docs/trial/FINDINGS.md`](docs/trial/FINDINGS.md) and [`docs/AGENT-CATALOG.md`](docs/AGENT-CATALOG.md).

## Checks every pull request must pass (CI)

```bash
# engine (from apps/engine)
ruff check drishti tests && pytest -q
# vision (from apps/vision)
ruff check drishti_vision tests && pytest -q
# web (from apps/web)
npx tsc --noEmit && npm run lint && npm run build
```

and a gitleaks scan for keys.
