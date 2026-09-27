"""Start-of-session briefing: where your copy stands, what the team did lately, what's free to claim.

Run from the repo root at the start of every session (after `git pull`):
    python scripts/team/sync.py            # newest 8 log entries
    python scripts/team/sync.py --log 15   # more

It changes nothing. Needs git; uses the GitHub CLI (gh) for the task board if it is logged in.
"""

from __future__ import annotations

import argparse
import json
import re

from _common import ROOT, gh_ok, github_user, log_entries, run

TASKS = ROOT / "docs" / "team" / "TASKS.md"


def section(title: str) -> None:
    print(f"\n=== {title} " + "=" * max(0, 70 - len(title)))


def where_am_i() -> None:
    section("Your copy")
    run("git", "fetch", "--quiet", "origin")
    branch = run("git", "branch", "--show-current") or "?"
    print(f"branch: {branch}")
    counts = run("git", "rev-list", "--left-right", "--count", "origin/main...HEAD")
    if counts:
        behind, ahead = counts.split()
        print(f"vs main: {behind} commit(s) behind, {ahead} ahead")
        if branch == "main" and behind != "0":
            print("  -> run: git pull")
        elif branch != "main" and behind != "0":
            print("  -> bring your branch up to date: git merge origin/main")
    dirty = run("git", "status", "--short")
    if dirty:
        print(f"uncommitted changes: {len(dirty.splitlines())} file(s)")


def recent_log(n: int) -> None:
    section(f"Newest {n} log entries (read these)")
    entries = log_entries()[-n:]
    if not entries:
        print("(none yet)")
    for p in entries:
        first = p.read_text(encoding="utf-8", errors="replace").splitlines()[:1]
        title = first[0].lstrip("# ").strip() if first else ""
        print(f"- docs/team/log/{p.name}\n    {title}")


def task_id(title: str) -> str:
    m = re.match(r"\s*(T\d{3})\b", title)
    return m.group(1) if m else ""


def task_dependencies() -> dict[str, list[str]]:
    """T-ids each task depends on, read from the '### T101 · ... Depends on: T100' headings."""
    deps: dict[str, list[str]] = {}
    for line in TASKS.read_text(encoding="utf-8").splitlines():
        m = re.match(r"###\s+(T\d{3})\b(.*)", line)
        if m:
            after = m.group(2).split("Depends on:", 1)
            deps[m.group(1)] = re.findall(r"T\d{3}", after[1]) if len(after) > 1 else []
    return deps


def closed_tasks() -> set[str]:
    out = run("gh", "issue", "list", "--state", "closed", "--limit", "300", "--json", "title")
    return {task_id(i["title"]) for i in (json.loads(out) if out else [])} - {""}


def board(me: str) -> None:
    if not gh_ok():
        section("Task board")
        print("gh is not logged in: run `gh auth login`, or see "
              "https://github.com/AdityaMore776/drishti/issues")
        return

    def issues(label: str, limit: int = 30) -> list[dict]:
        out = run("gh", "issue", "list", "--state", "open", "--label", label, "--limit", str(limit),
                  "--json", "number,title,assignees,updatedAt,labels")
        return json.loads(out) if out else []

    def show(items: list[dict], with_who: bool) -> None:
        if not items:
            print("(none)")
        for i in sorted(items, key=lambda i: i["title"]):
            who = ", ".join("@" + a["login"] for a in i["assignees"]) or "nobody"
            extra = f"  [{who}, updated {i['updatedAt'][:10]}]" if with_who else ""
            if any(lb["name"] == "human-task" for lb in i.get("labels", [])):
                extra += "  (human task: needs your person, not just the AI)"
            print(f"#{i['number']:<4} {i['title']}{extra}")

    mine = [i for i in issues("in-progress") if any(a["login"] == me for a in i["assignees"])]
    section(f"Your task in progress (@{me})")
    show(mine, with_who=False)
    section("In progress (don't start these)")
    show(issues("in-progress"), with_who=True)
    section("Blocked")
    show(issues("blocked"), with_who=True)

    ready = issues("ready", 100)
    done = closed_tasks()
    deps = task_dependencies()
    free, waiting = [], []
    for i in ready:
        need = [d for d in deps.get(task_id(i["title"]), []) if d not in done]
        (waiting if need else free).append((i, need))
    section("Claimable now (dependencies done; T100 first, else the lowest ID)")
    show([i for i, _ in free], with_who=False)
    section("Waiting on other tasks")
    for i, need in sorted(waiting, key=lambda x: x[0]["title"]):
        print(f"#{i['number']:<4} {i['title']}  [needs {', '.join(need)}]")
    if not waiting:
        print("(none)")
    prs = run("gh", "pr", "list", "--state", "open", "--json", "number,title,author,isDraft")
    section("Open pull requests")
    for p in json.loads(prs) if prs else []:
        tag = "draft" if p["isDraft"] else "READY for review"
        print(f"#{p['number']:<4} {p['title']}  [@{p['author']['login']}, {tag}]")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--log", type=int, default=8, help="how many log entries to list")
    args = ap.parse_args()
    me = github_user()
    where_am_i()
    recent_log(args.log)
    board(me)
    print("\nNext: read the newest log entries, then AGENTS.md section 2 or 3.")


if __name__ == "__main__":
    main()
