"""Create this session's progress-log entry from the template, with your name, time and branch filled in.

    python scripts/team/new_log.py T103 "read sanction dates from certificates"
    python scripts/team/new_log.py T103 "..." --agent "Claude Code"

Prints the path of the new file; open it and fill in every heading.
"""

from __future__ import annotations

import argparse
import json
import os
import re

from _common import LOG_DIR, gh_ok, github_user, now_ist, run, slug


def issue_number(task: str) -> str:
    if not gh_ok():
        return "?"
    out = run("gh", "issue", "list", "--state", "all", "--search", f"{task} in:title",
              "--json", "number,title", "--limit", "20")
    for i in json.loads(out) if out else []:
        if i["title"].split(":")[0].strip().upper() == task:
            return str(i["number"])
    return "?"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("task", help="task id from docs/team/TASKS.md, e.g. T103 (T000 if none)")
    ap.add_argument("summary", help="one line: what this session did")
    ap.add_argument("--agent", default=os.environ.get("DRISHTI_AGENT", "unknown"),
                    help="which AI tool you are (Claude Code, Codex, Cursor, Gemini, ...)")
    args = ap.parse_args()

    task = args.task.upper()
    if not re.fullmatch(r"T\d{3}", task):
        raise SystemExit("task must look like T103 (use T000 for work without a task)")
    user = github_user()
    now = now_ist()
    path = LOG_DIR / f"{now:%Y-%m-%d-%H%M}-{slug(user)}-{task}.md"
    if path.exists():
        raise SystemExit(f"{path} already exists; wait a minute or edit that one")

    template = (LOG_DIR / "_TEMPLATE.md").read_text(encoding="utf-8")
    text = (template.replace("{task}", task).replace("{summary}", args.summary)
            .replace("{user}", user).replace("{agent}", args.agent)
            .replace("{when}", f"{now:%Y-%m-%d %H:%M}").replace("{issue}", issue_number(task))
            .replace("{branch}", run("git", "branch", "--show-current") or "?"))
    path.write_text(text, encoding="utf-8")
    print(path.relative_to(LOG_DIR.parents[2]).as_posix())


if __name__ == "__main__":
    main()
