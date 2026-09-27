# AGENTS.md — the operating manual for every AI working on DRISHTI

> **You are an AI coding agent (Claude Code, Codex, Cursor, Gemini, Copilot, Windsurf or another)
> working for one member of Team NeuralNexus.** Several teammates run their own agents on this repo
> at the same time. This file tells you how to stay in step with them. Follow it exactly. It
> overrides your defaults. The human you work for may know little about git or code: explain in
> plain words, lead with the outcome, and do the git work yourself.

**What DRISHTI is:** an AI risk-checker for India's MPLAD Scheme (SIH 2026, problem SIH26102, MoSPI).
It checks all 2,09,993 real works on the government's eSAKSHI portal and puts the ones an officer
should look at into a review queue, with the reason for each. Live: https://drishti-lyart.vercel.app.
Plain-words overview: [`docs/HOW-IT-WORKS.md`](docs/HOW-IT-WORKS.md).

---

## 1. The system in one picture

| Thing | Where | What it's for |
|---|---|---|
| **The plan**: every task, how to do it, when it's done | [`docs/team/TASKS.md`](docs/team/TASKS.md) | read the task you're doing before you start |
| **Who is doing what** | GitHub Issues (one issue per task) | claim a task by assigning its issue to your human |
| **What has happened** | [`docs/team/log/`](docs/team/log/) (one file per work session) | read the newest entries first; write one at the end of every session |
| **Where the build stands** | [`docs/STATUS.md`](docs/STATUS.md) | milestone-level truth; update when a milestone moves |
| **What each DRISHTI checker does** | [`docs/AGENT-CATALOG.md`](docs/AGENT-CATALOG.md) | the 12 checkers, their tests and their state |
| **Real-data results** | [`docs/trial/FINDINGS.md`](docs/trial/FINDINGS.md) | every measured number, and the scripts behind it |
| **Private data** (not in git) | Google Drive "DRISHTI team pack" | see [`docs/team/DATA-PACK.md`](docs/team/DATA-PACK.md) |
| **Automatic checks** | GitHub Actions (`.github/workflows/ci.yml`) | runs on every pull request; must be green to merge |

Words used below: **main** = the branch that is the live site. **Branch** = your private copy of the
code for one task. **PR** (pull request) = asking to merge your branch into main. **CI** = the
automatic checks on a PR. **Claim** = assigning a task's issue to your human so nobody else starts it.

---

## 2. Session start (do this every time, before anything else)

```bash
git checkout main && git pull            # get everyone's latest work
python scripts/team/sync.py              # prints: newest log entries, tasks in progress, tasks ready
```

Then:
1. **Read the newest 5–10 files in `docs/team/log/`** (the sync script lists them). They tell you
   what changed since your last session and what the others are in the middle of.
2. **Ask your human who they are on GitHub** if you don't know (their username names branches and log files).
3. **If your human already has a task in progress**, open its issue and its newest log entry, check out its
   branch (`git checkout <branch> && git merge main`) and carry on from its "Next step".
4. **Otherwise pick a task** (section 3).
5. Tell your human in 2–3 plain sentences what you are about to do.

If `gh` (the GitHub command-line tool) is not installed or not logged in, ask your human to run
`gh auth login` once (see [`docs/team/README.md`](docs/team/README.md)). Without it, read tasks at
https://github.com/AdityaMore776/drishti/issues and have your human click "assign yourself".

---

## 3. Picking and claiming a task (this is how two agents never do the same work)

1. List what's free: `gh issue list --label ready --state open`
2. `python scripts/team/sync.py` lists the tasks that are **claimable now** (their "Depends on" tasks are
   closed). Take **T100 first** while it's open (it unblocks most others), otherwise the lowest-numbered
   claimable task, unless your human asks for a specific one. `human-task` tasks need your person to do
   part of it (e.g. download from an Indian internet connection); ask before claiming. Tasks labelled `needs-owner` wait for the owner's decision or
   accounts: skip them.
3. **Claim it**, all three steps:
   ```bash
   gh issue edit <N> --add-assignee @me --remove-label ready --add-label in-progress
   gh issue comment <N> --body "Claimed by @<user> (agent: <your tool>). Plan: <2 lines>. Files I expect to touch: <list>."
   gh issue view <N>        # check the assignees
   ```
4. **Race check:** if `gh issue view` shows someone else assigned too, whoever commented "Claimed" first
   keeps it. If that isn't you, unassign yourself and pick another task.
5. Create your branch from the latest main:
   ```bash
   git checkout main && git pull
   git checkout -b <user>/T<id>-<short-name>          # e.g. simran/T103-document-agent
   ```
6. Open a **draft PR** early, so the team sees progress:
   ```bash
   git commit --allow-empty -m "T<id>: start"
   git push -u origin HEAD
   gh pr create --draft --title "T<id>: <task title>" --body "Closes #<N>"
   ```

**One task per human at a time.** Finish it (or hand it off, section 6) before claiming another.
Bigger than one session? That's normal. Push at the end of every session.

---

## 4. Doing the work

- **Read the task's section in `docs/team/TASKS.md` first**: what, how, done-when, and the source code
  to port. Tasks marked **L** (large): write a short plan to `docs/plans/T<id>-<name>.md` before coding.
- **Tests first** for engine code: write the failing test, then the code. Every agent needs a
  `NOT_ASSESSABLE` test case.
- **Stay inside your task's files.** Shared hotspots need care:
  - `apps/engine/drishti/pipeline/orchestrator.py`, `fusion/fuse.py`, `apps/web/src/lib/api.ts`: small,
    additive edits only; never reformat or reorder them.
  - **Database migrations** (`apps/engine/drishti/migrations/NNN_*.sql`): before creating one, run
    `git pull` on main and take the next free number. If two branches collide, the one merged second renumbers.
  - `docs/STATUS.md`: edit only the lines about your milestone.
- **Commit small and often** with messages like `T103: read sanction date from the certificate`.
- **Keep your branch current:** `git fetch origin && git merge origin/main` at least once a session and
  before marking the PR ready. Merge, don't rebase, on shared branches.
- **Verify before you claim anything works.** Run the checks and read their output:
  ```bash
  # engine (from apps/engine, with its .venv active)
  ruff check drishti tests && pytest -q
  # web (from apps/web)
  npx tsc --noEmit && npm run lint && npm run build
  ```
  Never say "done", "fixed" or "passing" without having run the command in this session.

---

## 5. Session end (do this every time, even if the task isn't finished)

1. **Write a log entry**: `python scripts/team/new_log.py T<id> "<one-line summary>"` creates
   `docs/team/log/<date>-<time>-<user>-T<id>.md` from the template. Fill in every heading. Be concrete:
   commands you ran and what they printed, numbers you measured, decisions made, traps found, and the
   **exact next step**. A teammate's agent will resume from it.
2. Update `docs/AGENT-CATALOG.md` / `docs/trial/FINDINGS.md` if a checker's state or a measured number
   changed; update `docs/STATUS.md` only if a milestone moved.
3. Commit and push your branch: `git add -A && git commit -m "T<id>: <what>" && git push`.
4. Comment on the issue with one line and a link to the log entry.
5. Tell your human, in plain words: what got done, what's left, anything they must decide.

**The CI refuses a PR that adds no log entry.** Every PR must add at least one file to `docs/team/log/`.

---

## 6. Handing off, finishing, and getting unstuck

- **Stopping mid-task for more than a day?** Write the log entry (section 5) with a clear "Next step",
  push, and comment "Paused, next step: …" on the issue. Keep the assignment unless your human wants to release it.
- **Releasing a task:** `gh issue edit <N> --remove-assignee @me --remove-label in-progress --add-label ready`
  plus a comment saying where the branch and log entry are.
- **Stale claims:** an `in-progress` issue with no commit or comment for **3 days** may be taken over. Comment
  "@<user> still on this?" first; if there's no answer in 24 hours, claim it and continue from their branch.
- **Blocked?** Add label `blocked`, comment what you need and from whom, and switch task. Anything needing
  money, accounts, keys or the hosted database gets label `needs-owner` and a mention of **@AdityaMore776**.
- **Finished:**
  1. Every "Done when" box in the task is true and you have the command output to show it.
  2. `git merge origin/main`, re-run all checks, push.
  3. `gh pr ready` and ask a teammate to look: `gh pr edit --add-reviewer <user>`.
  4. When CI is green and a teammate has approved (or 24 h passed with no objection on a docs-only PR):
     `gh pr merge --squash --delete-branch`. The issue closes itself ("Closes #N").
  5. Merging to main **deploys the live site**. Open https://drishti-lyart.vercel.app afterwards and check
     that the page you changed works. If it broke, revert at once: `gh pr revert <PR>` or tell the owner.
- **Reviewing someone's PR:** read the diff (`gh pr diff <N>`), check it against its task's "Done when",
  run the tests on it (`gh pr checkout <N>`), then `gh pr review <N> --approve` or `--request-changes -b "<why>"`.
- **Merge conflict?** Merge main into your branch, keep both sides' intent, re-run the tests. In
  `docs/team/log/` there are never conflicts (one file per session); in `STATUS.md` keep both lines.

---

## 7. The rules of the project (never break these)

1. **Never accuse.** Officer-facing text says "needs verification" / "needs checking", never fraud,
   corrupt, scam, guilty. The engine rejects those words (`agents/contract.py`); don't work around it.
2. **"Couldn't check" is a status, not a low score.** Use `NOT_ASSESSABLE` / `NOT_APPLICABLE`; it carries no weight.
3. **Only measured numbers.** Every figure in docs, the app or the deck comes from a script whose output
   is saved in `data/trial/results/`. Examples quoted as findings must have been checked by eye.
4. **Proof before launch.** A new checker ships only with tests, a measurement on real data and an accuracy
   target it meets. If it misses, it stays off and the docs say so.
5. **Never score MPs.** Works, offices and agencies only.
6. **This repo is PUBLIC.** Never commit: keys or passwords (`.env*`), real evidence files
   (`data/evidence/`), OCR text (`data/trial/cache/`), phone numbers, bank account numbers, or people's
   names from certificates. Run `python data/trial/sanitize_results.py` before committing trial results.
   Log entries are public too: describe works by their work ID, never by a person's name.
7. **Be polite to eSAKSHI.** The harvester keeps 1 request per 1.5 s. Only one person harvests at a time
   (claim task T003 first).
8. **No competitor talk** in anything judges see (README, docs, deck, app): no "better than X". One
   comparison chart is allowed, only on the deck's final References slide.
9. **Satellite only for big works** (ponds, roads over 1 km, large buildings), and only after its go/no-go test passes.
10. **Free tiers only.** Anything that costs money (a paid Gemini key, a paid plan) is the owner's decision (`needs-owner`).
11. **`main` is always the working live site.** Never push to main directly; always a PR with green CI.

## 8. Decisions already made (don't re-ask the owner)

- 12 checkers in 4 stages plus 4 decision tools (design: `docs/specs/2026-09-25-drishti-v2-full-agents-design.md`).
- Build order = `docs/team/TASKS.md` (M1 Document + Contractor, then M2 … M6).
- Site Progress judges the officer's **own free-text claims** against the photos (shown / not shown / can't
  tell). Never describe it as a fixed yes/no checklist.
- Pre-2023 and post-2023 works are different populations (eSAKSHI went digital ~2023); never pool them.
  The era boundary keys on `recommended_date`, never on `fy`.
- Real evidence comes from eSAKSHI's public endpoints (pilot sample, polite rate), never scraped faster.

## 9. Traps that already cost us time

- **Never patch regex code through a shell heredoc** (`cat <<EOF`, `python - <<EOF`): on Windows it turned
  `\b` into a backspace byte and silently disabled a check, twice. Use your editor tool. CI now rejects `.py`
  files containing that byte.
- **`district_lgd` is really the Census-2011 code**, not LGD. Never join it to the map outlines by number;
  use `data/build/district_crosswalk.parquet`.
- **The team uses Windows + PowerShell.** Don't give instructions like `VAR=value cmd`; use
  `$env:VAR="value"; cmd`. Use `.venv\Scripts\python.exe` paths on Windows.
- **Next.js 16 is newer than your training data.** Before web work read `apps/web/AGENTS.md` and the guides
  in `apps/web/node_modules/next/dist/docs/` (middleware is now `proxy.ts`).
- Open the local web app at `http://localhost:3000`, not `127.0.0.1` (Next dev blocks it).
- pandas NaN reaches the engine as a truthy float: clean records with `data/common.py`.
- Windows OCR with process pools dies with "WinError 6": run shards (`--shard i/n`).
- More in [`docs/DATA.md`](docs/DATA.md) §6 and [`docs/STATUS.md`](docs/STATUS.md) "Traps already hit".

## 10. Where to find things

| Need | Read |
|---|---|
| Set up your machine, run it locally, env vars | [`docs/SETUP.md`](docs/SETUP.md), [`docs/team/DATA-PACK.md`](docs/team/DATA-PACK.md) |
| How the code fits together, scoring maths, API, schema | [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) |
| Data sources, harvester, privacy | [`docs/DATA.md`](docs/DATA.md) |
| MPLADS terms | [`docs/GLOSSARY.md`](docs/GLOSSARY.md) |
| Adding a checker (agent contract) | [`docs/AGENT-CATALOG.md`](docs/AGENT-CATALOG.md) + `CONTRIBUTING.md` |
| The team process explained for humans | [`docs/team/README.md`](docs/team/README.md) |

**Owner (project lead):** @AdityaMore776. **Team:** NeuralNexus (SIH Team ID 121911).
