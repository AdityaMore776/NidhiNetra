"""Create the GitHub labels, milestones and task issues that docs/team/TASKS.md describes but GitHub lacks.

    python scripts/team/sync_issues.py --dry-run     # show what would be created
    python scripts/team/sync_issues.py               # create it

Safe to re-run: it only adds what is missing and never edits or closes existing issues. Run it after adding
a task to TASKS.md. Needs the GitHub CLI (gh) logged in with write access to the repo.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess

from _common import ROOT, run

TASKS = ROOT / "docs" / "team" / "TASKS.md"
SPEC_URL = "https://github.com/AdityaMore776/drishti/blob/main/docs/team/TASKS.md"
LABELS = {
    "ready": ("0E8A16", "Not claimed yet: free to take once its dependencies are closed"),
    "in-progress": ("FBCA04", "Claimed: someone's agent is working on it"),
    "blocked": ("B60205", "Waiting on something; see the latest comment"),
    "needs-owner": ("5319E7", "Needs the owner (@AdityaMore776): a decision, an account, a key or the hosted database"),
    "human-task": ("1D76DB", "Needs a person, not just an AI (e.g. downloading from an Indian connection)"),
}


def parse_tasks() -> list[dict]:
    tasks, milestone = [], None
    for line in TASKS.read_text(encoding="utf-8").splitlines():
        m = re.match(r"##\s+(M[\d.]+\s+—\s+[^·]+)", line)
        if m and not line.startswith("###"):
            milestone = m.group(1).strip()
            continue
        m = re.match(r"###\s+(T\d{3})\s+·\s+(.+)", line)
        if m and milestone:
            parts = [p.strip().replace("**", "") for p in m.group(2).split("·")]
            deps = next((p.split(":", 1)[1].strip() for p in parts if p.startswith("Depends on")), "none")
            tasks.append({
                "id": m.group(1), "title": parts[0], "milestone": milestone,
                "size": parts[1] if len(parts) > 1 else "", "area": parts[2] if len(parts) > 2 else "",
                "deps": deps, "deps_ids": re.findall(r"T\d{3}", deps),
                "owner": "needs-owner" in line, "human": "human task" in line,
            })
    return tasks


def gh_json(*args: str) -> list[dict]:
    out = run("gh", *args)
    return json.loads(out) if out else []


def gh(*args: str, dry: bool) -> str:
    print("  gh " + " ".join(a if " " not in a else repr(a) for a in args[:6]) + (" ..." if len(args) > 6 else ""))
    if dry:
        return ""
    res = subprocess.run(["gh", *args], cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
    if res.returncode != 0:
        raise SystemExit(res.stderr.strip())
    return res.stdout.strip()


def main() -> None:
    ap = argparse.ArgumentParser(description="create missing labels, milestones and task issues")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    dry = args.dry_run

    tasks = parse_tasks()
    print(f"{len(tasks)} tasks in TASKS.md")

    have_labels = {lb["name"] for lb in gh_json("label", "list", "--limit", "200", "--json", "name")}
    for name, (color, desc) in LABELS.items():
        if name not in have_labels:
            gh("label", "create", name, "--color", color, "--description", desc, dry=dry)

    have_ms = {m["title"] for m in gh_json("api", "repos/{owner}/{repo}/milestones?state=all&per_page=100")}
    for ms in dict.fromkeys(t["milestone"] for t in tasks):
        if ms not in have_ms:
            gh("api", "repos/{owner}/{repo}/milestones", "-f", f"title={ms}", dry=dry)

    issues = gh_json("issue", "list", "--state", "all", "--limit", "500", "--json", "number,title")
    number = {m.group(1): i["number"] for i in issues if (m := re.match(r"(T\d{3})\b", i["title"]))}
    created = 0
    for t in tasks:
        if t["id"] in number:
            continue
        dep_text = ", ".join(f"{d} (#{number[d]})" if d in number else d for d in t["deps_ids"]) or t["deps"]
        body = (f"**Spec:** [docs/team/TASKS.md, section {t['id']}]({SPEC_URL}) — read it before starting.\n\n"
                f"**Size:** {t['size']} · **Area:** {t['area']}\n"
                f"**Depends on:** {dep_text}\n\n"
                "**To claim:** assign yourself, swap label `ready` → `in-progress`, comment your plan "
                "([AGENTS.md §3](https://github.com/AdityaMore776/drishti/blob/main/AGENTS.md)). "
                "Link your PR with `Closes #<this issue>`.")
        labels = ["needs-owner" if t["owner"] else "ready"] + (["human-task"] if t["human"] else [])
        cmd = ["issue", "create", "--title", f"{t['id']}: {t['title']}", "--body", body,
               "--milestone", t["milestone"]]
        for lb in labels:
            cmd += ["--label", lb]
        url = gh(*cmd, dry=dry)
        if url:
            number[t["id"]] = int(url.rstrip("/").rsplit("/", 1)[-1])
        created += 1
    print(f"{'would create' if dry else 'created'} {created} issue(s)")


if __name__ == "__main__":
    main()
