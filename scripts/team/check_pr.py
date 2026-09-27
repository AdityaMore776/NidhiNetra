r"""Team checks for a pull request. CI runs this on every PR; run it yourself before marking a PR ready:

    python scripts/team/check_pr.py                  # compares your branch with origin/main
    python scripts/team/check_pr.py --base origin/main

Fails (exit 1) when the branch:
  1. adds no progress-log entry under docs/team/log/
  2. touches private or local-only paths (real evidence, OCR text, raw data, secrets)
  3. adds a file over 5 MB outside the allowed places (deck files, map outlines)
  4. has a backspace byte (0x08) in code: the Windows heredoc trap that turned \b into it twice
  5. puts something that looks like a phone number, account number or key into a log entry
"""

from __future__ import annotations

import argparse
import re
import sys

from _common import ROOT, run

FORBIDDEN = ("data/evidence/", "data/trial/cache/", "data/raw/", "data/build/", "data/cache/",
             ".vercel/", ".demo-logins.txt")
BIG_OK = ("docs/deck/", "apps/web/public/geo/", "docs/reference/")
MAX_MB = 5
CODE = (".py", ".ts", ".tsx", ".js", ".mjs", ".sql", ".yaml", ".yml", ".json")
PRIVATE = [
    # (?<![\w/]) skips work ids ("/124508") and vendor codes ("V9174...")
    (re.compile(r"(?<![\w/])[6-9]\d{9}(?!\d)"), "a 10-digit mobile number"),
    (re.compile(r"(?<![\w/])\d{11,18}(?!\d)"), "a long number (bank account?)"),
    (re.compile(r"(?i)(api[_-]?key|secret|password|service_role)\s*[:=]\s*\S{8,}"), "a key or password"),
    (re.compile(r"\beyJ[\w-]{20,}\.[\w-]{20,}"), "a token"),
    (re.compile(r"postgres(?:ql)?://[^\s:]+:[^\s@]+@"), "a database URL with a password"),
]


def is_env(path: str) -> bool:
    name = path.rsplit("/", 1)[-1]
    return name.startswith(".env") and name != ".env.example"


def main() -> int:
    ap = argparse.ArgumentParser(description="team checks for a pull request")
    ap.add_argument("--base", default="origin/main")
    args = ap.parse_args()

    diff = run("git", "diff", "--name-status", "--no-renames", f"{args.base}...HEAD")
    if diff is None:
        print(f"could not diff against {args.base}: run `git fetch origin` first")
        return 1
    changes = [line.split("\t", 1) for line in diff.splitlines() if line.strip()]
    present = [path for status, path in changes if status != "D"]
    added = [path for status, path in changes if status == "A"]
    problems: list[str] = []

    logs = [p for p in added if p.startswith("docs/team/log/") and p.endswith(".md")
            and p.rsplit("/", 1)[-1][:1].isdigit()]
    if not logs:
        problems.append("no progress-log entry: run `python scripts/team/new_log.py T<id> \"summary\"`, "
                        "fill it in, commit it (AGENTS.md section 5)")

    for path in present:
        if path.startswith(FORBIDDEN) or is_env(path):
            problems.append(f"{path}: private or local-only file, must not be in git (see .gitignore)")
            continue
        file = ROOT / path
        if not file.is_file():
            continue
        size_mb = file.stat().st_size / 1e6
        if size_mb > MAX_MB and not path.startswith(BIG_OK):
            problems.append(f"{path}: {size_mb:.1f} MB (limit {MAX_MB} MB); large data belongs in the team pack")
        if path.endswith(CODE) and b"\x08" in file.read_bytes():
            problems.append(f"{path}: contains a backspace byte (0x08); a heredoc mangled a \\b. "
                            "Rewrite the line with your editor")

    for path in logs:
        text = (ROOT / path).read_text(encoding="utf-8", errors="replace")
        for pattern, what in PRIVATE:
            if pattern.search(text):
                problems.append(f"{path}: looks like it contains {what}; this repo is public, remove it")

    if problems:
        print("Team checks FAILED:")
        for p in problems:
            print(f"  - {p}")
        return 1
    print(f"Team checks passed ({len(present)} changed file(s), {len(logs)} log entr{'y' if len(logs) == 1 else 'ies'}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
