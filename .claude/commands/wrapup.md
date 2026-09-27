---
description: End a DRISHTI session (log entry, push, issue comment, plain summary)
---
Wrap up this session exactly as AGENTS.md section 5 describes:

1. Run the checks for what changed (engine: `ruff check drishti tests && pytest -q`; web: `npx tsc --noEmit && npm run lint`) and note the results.
2. `python scripts/team/new_log.py T<id> "<summary>" --agent "Claude Code"` and fill in every heading, including the exact next step.
3. Update AGENT-CATALOG / FINDINGS / STATUS only if a checker's state, a measured number or a milestone changed.
4. Commit, push the branch, comment on the issue with a link to the log entry. If the task is finished, follow AGENTS.md section 6 "Finished" (ask me before merging).
5. Tell me in plain words: what got done, what's left, anything I must decide. $ARGUMENTS
