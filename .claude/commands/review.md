---
description: Review a teammate's pull request against its task's "Done when"
argument-hint: <PR number>
---
Review pull request #$ARGUMENTS as AGENTS.md section 6 "Reviewing someone's PR" describes:
read its task in docs/team/TASKS.md, `gh pr diff $ARGUMENTS`, `gh pr checkout $ARGUMENTS`, run the engine/web
checks, and check the project rules (no accusing words, no private data, only measured numbers, a log entry).
Then tell me in plain words whether it is ready, and approve or request changes only after I agree.
Switch back to my own branch afterwards.
