# Working on DRISHTI

**Team members and their AI agents: start with [`AGENTS.md`](AGENTS.md).** It is the one manual for
how we work together: session start, claiming a task on GitHub Issues, branches and pull requests, the
progress log, handoffs and the project rules. Humans new to GitHub: [`docs/team/README.md`](docs/team/README.md).

| | |
|---|---|
| The manual (every AI follows it) | [`AGENTS.md`](AGENTS.md) |
| The task plan: every task, how, done-when | [`docs/team/TASKS.md`](docs/team/TASKS.md) |
| Who is doing what | [GitHub Issues](https://github.com/AdityaMore776/NidhiNetra-team/issues) |
| What happened lately | [`docs/team/log/`](docs/team/log/) |
| Private data (not in git) | [`docs/team/DATA-PACK.md`](docs/team/DATA-PACK.md) |
| Where the build stands | [`docs/STATUS.md`](docs/STATUS.md) |

## The non-negotiables (full list: AGENTS.md §7)

1. **Never accuse.** "Needs verification", never fraud/corrupt/scam/guilty; the engine rejects those words.
2. **"Couldn't check" is a status, not a low score** (`NOT_ASSESSABLE` / `NOT_APPLICABLE`).
3. **This repo is public:** no secrets, no evidence files, no names, phone or account numbers.
4. **Only measured numbers**, from scripts whose output is saved.
5. **Proof before launch:** tests + a real-data measurement + an accuracy target it meets.
6. **Never score MPs.** Works, offices and agencies only.
7. **Be polite to eSAKSHI:** 1 request per 1.5 s, one harvester at a time.
8. **`main` is the live site:** changes arrive only through a pull request with green CI.

## Adding an engine or checker

1. Create `apps/engine/drishti/agents/<id>/` returning an `AgentResult` (see `agents/statistical/agent.py`
   and `agents/contract.py`). `risk` is the engine's per-work signal 0–1; `evidence` its evidence dict.
2. Add `agents/<id>/engine.py` defining `ENGINE = EngineSpec(id=..., name=..., question=..., assess=fn)`
   where `fn(work, ctx)` returns the `AgentResult` (`ctx` is `pipeline.orchestrator.Context`; put any
   store your engine loads once per process in `ctx.data["<id>"]`). That is all: `agents/registry.py`
   finds the folder. The five core slots (`compliance`, `statistical`, `dup_split`, `delay`, `outlier`)
   show as NOT_BUILT until their folder has an `engine.py`; don't edit the orchestrator or fusion to add one.
3. Tests under `apps/engine/tests/agents/<id>/`, including `NOT_ASSESSABLE` and `NOT_APPLICABLE` cases.
4. A trial script in `data/trial/` with its saved (sanitised) result, and its section in
   [`docs/AGENT-CATALOG.md`](docs/AGENT-CATALOG.md).

## Checks every pull request must pass (CI)

- **engine:** `ruff check drishti tests` + `pytest -q`
- **web:** `tsc --noEmit` + `eslint` + `next build`
- **team:** `python scripts/team/check_pr.py`: a progress-log entry is added; no private paths; no file
  over 5 MB; no backspace byte in code; nothing that looks like a phone/account number or key in log entries
- **secrets:** gitleaks scan

## Where to write things

| What | Where |
|---|---|
| What you did this session | a new file in `docs/team/log/` |
| A new task | `docs/team/TASKS.md` + a GitHub issue |
| Current state, milestone level | `docs/STATUS.md` |
| A design decision | `docs/specs/` (and a line in your log entry) |
| A large task's plan | `docs/plans/T<id>-<name>.md` |
| Measured results | `data/trial/results/` + `docs/trial/FINDINGS.md` + `docs/AGENT-CATALOG.md` |
