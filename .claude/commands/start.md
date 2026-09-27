---
description: Start a DRISHTI team session (sync, read the log, pick or resume a task)
---
Start a DRISHTI session exactly as AGENTS.md sections 2 and 3 describe:

1. If `apps/engine/.venv` does not exist, this machine is new: run `python scripts/team/setup.py` first and report anything it says is missing.
2. `git checkout main && git pull`, then `python scripts/team/sync.py`.
3. Read the newest log entries it lists.
4. If my GitHub user already has a task in progress, resume it from its branch and newest log entry. Otherwise propose the task to claim (T010 first while open; core T0xx before side-track tasks, else the lowest claimable), and claim it only after I say yes.
5. Tell me in 2–3 plain sentences what you'll do. $ARGUMENTS
