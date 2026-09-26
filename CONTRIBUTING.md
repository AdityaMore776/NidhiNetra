# Working on DRISHTI — team rules

## The non-negotiables

1. **Never accuse.** Officer-facing text says "needs verification" / "needs checking" — never fraud, corrupt,
   scam, guilty, etc. The engine rejects those words (`agents/contract.py`); don't work around it.
2. **"Couldn't check" is a status, not a low score.** Use `NOT_ASSESSABLE` / `NOT_APPLICABLE`.
3. **No secrets in git.** Keys and passwords live in `.env.local` (gitignored) and Vercel's settings.
   `.env.example` lists the names.
4. **No real evidence in git.** Downloaded certificates/photos (`data/evidence/`) and OCR text
   (`data/trial/cache/`) stay local. Run `data/trial/sanitize_results.py` before committing trial results.
5. **Only measured numbers.** Any figure in the docs, the app or the deck must come from a script whose output
   is saved. Examples quoted as findings must have been checked by eye.
6. **Proof before launch.** A new agent ships only with (a) tests, (b) a measurement on real data, (c) a
   head-to-head against the simple/rival method, and (d) a kill criterion. If it loses, it stays off.
7. **Never score MPs.** Works, offices and agencies only.
8. **Be polite to eSAKSHI.** Keep the harvester at one request per 1.5 s.

## Adding an agent

1. Create `apps/engine/drishti/agents/<agent>/` returning an `AgentResult` (see `agents/statistical/agent.py`).
2. Register it in `pipeline/orchestrator.py` (`AGENT_ORDER`, `QUESTIONS`) and give it a label and reliability
   prior in `fusion/fuse.py`.
3. Tests under `apps/engine/tests/agents/<agent>/`, including a `NOT_ASSESSABLE` case.
4. A trial script in `data/trial/` with its saved result, and a section in `docs/AGENTS.md`.

## Workflow

- `main` is always the live, demoable site (every push deploys). Work on a branch; open a pull request.
- CI must pass: engine `ruff` + `pytest`; web `tsc` + `eslint` + `next build`.
- Keep `docs/STATUS.md` current when a milestone moves.
- Windows note: never patch regex-containing code through a shell heredoc (it turned `\b` into a backspace
  byte twice). Use an editor.

## Where to write things

| What | Where |
|---|---|
| Current state and next steps | `docs/STATUS.md` |
| A design decision | `docs/specs/` |
| A milestone's task plan | `docs/plans/` |
| Measured results | `data/trial/results/` + `docs/trial/FINDINGS.md` + `docs/AGENTS.md` |
