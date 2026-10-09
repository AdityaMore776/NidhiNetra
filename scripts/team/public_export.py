r"""Build the public copy of the repository: the product, its docs and its results, without the
team's working files (session logs, task plan, agent manuals, editor settings).

The private repository stays the team's working copy. This script writes a clean snapshot of one
commit into a separate folder that is its own git repository, so the public one never shares
history (or pull requests, issues, branches) with the private one. Re-run it to refresh the public
copy: files are added, changed and removed to match, then you commit and push from that folder.

    python scripts/team/public_export.py --ref origin/main --out D:\nidhinetra-public ^
        --repo AdityaMore776/NidhiNetra-SIH

It stops with a list of lines if anything that should not be public is still there.
"""

from __future__ import annotations

import argparse
import io
import re
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PRIVATE_REPO = "AdityaMore776/NidhiNetra"
REPORT = "NidhiLens (Fine-Tuned Qwen for site progress monitoring)"

# whole files and folders that stay private
DROP = [
    "AGENTS.md", "CLAUDE.md", "GEMINI.md", "apps/web/AGENTS.md", "apps/web/CLAUDE.md",
    ".claude", ".github/copilot-instructions.md", ".github/ISSUE_TEMPLATE",
    ".github/pull_request_template.md",
    "docs/team", "scripts/team", "docs/superpowers", "docs/deck",
    # plans written as step lists for a coding assistant
    "docs/plans/T147-run-on-your-pc.md", "docs/plans/M0-foundations-statistical.md",
    # the first two designs, written as a conversation (the blueprint of 27 Sept replaced them)
    "docs/specs/2026-09-25-drishti-prototype-design.md",
    "docs/specs/2026-09-25-drishti-v2-full-agents-design.md",
    # local tools that need the team's private data pack
    "scripts/dev/start.py", "scripts/dev/local_db.py",
    "r06.txt",
]
# ... except these, put back after the drops
KEEP = ["docs/deck/DRISHTI_SIH26102_v2.pdf"]

# (file, line pattern): lines removed
DROP_LINES = [
    ("README.md", r"^\| \*\*Joining the team\?\*\*"),
    ("README.md", r"^\| \*\*The task plan\*\*"),
    ("README.md", r"^\| Earlier design documents"),
    ("README.md", r"^│   └── team/ "),
    ("README.md", r"^├── AGENTS\.md "),
    ("apps/web/README.md", r"AGENTS\.md` / `CLAUDE\.md`"),
    (".gitignore", r"\.claude"),
    ("docs/STATUS.md", r"^\*\*Working as a team"),
    ("docs/SETUP.md", r"^\*\*Teammates, the quick way:\*\*"),
    ("docs/SETUP.md", r"^`apps\\engine\\\.venv\\Scripts\\python\.exe scripts\\dev\\local_db\.py --load`"),
    ("docs/SETUP.md", r"^built data and assesses every work; it prints the `DATABASE_URL`"),
    ("docs/plans/T150-vlm-progress-dataset.md", r"^\*\*RESUME HERE:\*\*"),
    ("docs/plans/T150-vlm-progress-dataset.md", r"^commands, where the data is, traps\)\.$"),
]

# (file or "*", old, new): text replaced
REPLACE = [
    ("README.md", "| **Team rules** for working on the repo |", "| **Project rules** |"),
    ("README.md", "├── scripts/             team tools (sync, new_log, check_pr) and local development",
     "├── scripts/             local development"),
    ("README.md", "├── .github/             CI (tests, team checks, secret scan), issue and PR templates",
     "├── .github/             CI: tests and a secret scan"),
    ("docs/SETUP.md", ("## The quick way (teammates)\n\n```powershell\n"
                       "python scripts/team/setup.py         # installs engine + web, unpacks the data "
                       "pack from Downloads, runs tests\n"
                       "python scripts/team/setup.py --db    # builds the local database with the real "
                       "corpus (~10 min, once)\n"
                       "python scripts/dev/start.py          # database + engine + web together: "
                       "http://localhost:3000\n```\nThe sections below are the same steps by hand.\n\n"),
     ""),
    ("data/requirements.txt", "Installed into the engine's venv by scripts/team/setup.py:",
     "Installed into the engine's venv:"),
    ("data/trial/results/hosted_assess_v3.txt", "(T054 handoff, 1 Oct 2026", "(T054, 1 Oct 2026"),
    ("data/trial/dashboard_labels.py", "Read by the agent (Claude Code) working for @AdityaMore776,",
     "Read by an AI model,"),
    ("docs/plans/T120-four-agents.md", "(AGENTS.md §8)", "(CONTRIBUTING.md, decisions)"),
    ("docs/STATUS.md", (" The roadmap and v2 notes below are history / side track; the live task "
                        "order is [`team/TASKS.md`](team/TASKS.md)."), ""),
    ("docs/AGENT-CATALOG.md", "specs/2026-09-25-drishti-v2-full-agents-design.md",
     "specs/2026-09-27-nidhinetra-blueprint.md"),
    ("docs/plans/T097-cost-agent-v3.md", ("(tasks **T093–T098** in `docs/team/TASKS.md`). Any "
                                          "agent, yours\nor a teammate's, can pick a task from here."),
     "(tasks **T093–T098**)."),
    ("docs/plans/T099-T100-simple-and-certain.md",
     "This plan covers two tasks in `docs/team/TASKS.md`: ", "This plan covers two tasks: "),
    ("docs/plans/T150-vlm-progress-dataset.md",
     ' "You" means a person; "AI" means Claude Code doing it.',
     ' "You" means a person; "AI" means it is automated.'),
    # the report's links: the test data and the code, in this repository
    (f"{REPORT}/README.md", f"github.com/{PRIVATE_REPO}/releases/", "github.com/{repo}/releases/"),
    (f"{REPORT}/README.md", f"--repo {PRIVATE_REPO}`", "--repo {repo}`"),
    ("*", "AGENTS.md section 8", "CONTRIBUTING.md, decisions"),
    ("*", "AGENTS.md", "CONTRIBUTING.md"),
]

# nothing public may say these (a hit stops the export) ...
DENY = re.compile(r"claude[ -]?code|CLAUDE\.md|(?<![\w-])AGENTS\.md|GEMINI\.md|\.claude/|copilot|codex|"
                  r"windsurf|superpowers|docs/team|team/log|scripts/team|new_log|check_pr|"
                  r"Co-Authored-By|Generated with|cloud session|session log|handoff|"
                  r"! npx|your AI\b|AI agents? on the team|claude/[a-z0-9-]+", re.IGNORECASE)
# ... except where the name is the subject: the Claude API as a benchmark baseline (code and
# its results), and npm's lock file (package names)
ALLOW_FILES = re.compile(r"^(apps/vision/drishti_vision/(flagship_claude|cli|vlmeval)\.py|"
                         r"apps/web/package-lock\.json)$")
# ... and lines that cite other work by name (a field study of general-purpose assistants)
ALLOW_LINES = re.compile(r"Smart Cities field study")
TEXT = {".md", ".py", ".ts", ".tsx", ".js", ".mjs", ".json", ".yml", ".yaml", ".toml", ".txt",
        ".sql", ".html", ".css", ".csv", ".jsonl", ".cfg", ".ini", ""}
# the public copy's own files that are never touched (its git folder)
OWN = {".git"}
# files written over the snapshot: the public CONTRIBUTING.md (the private one is the team manual)
OVERLAY = ROOT / "scripts" / "team" / "public"


def snapshot(ref: str, dest: Path) -> None:
    tar = subprocess.run(["git", "-C", str(ROOT), "archive", "--format=tar", ref],
                         check=True, capture_output=True).stdout
    with tarfile.open(fileobj=io.BytesIO(tar)) as t:
        t.extractall(dest, filter="data")


def text_files(base: Path):
    for p in sorted(base.rglob("*")):
        if p.is_file() and (p.suffix.lower() in TEXT or p.name.startswith(".")):
            try:
                yield p, p.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue


def clean(tmp: Path, repo: str) -> list[str]:
    kept = {k: (tmp / k).read_bytes() for k in KEEP if (tmp / k).exists()}
    for d in DROP:
        p = tmp / d
        if p.is_dir():
            shutil.rmtree(p)
        elif p.exists():
            p.unlink()
    for k, b in kept.items():
        (tmp / k).parent.mkdir(parents=True, exist_ok=True)
        (tmp / k).write_bytes(b)
    for src in OVERLAY.rglob("*"):
        if src.is_file():
            dst = tmp / src.relative_to(OVERLAY)
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(src.read_bytes())
    problems = []
    for f, pat in DROP_LINES:
        p = tmp / f
        s = p.read_text(encoding="utf-8")
        lines = s.splitlines(keepends=True)
        out = [x for x in lines if not re.search(pat, x)]
        if len(out) == len(lines):
            problems.append(f"line rule found nothing: {f}: {pat}")
        p.write_text("".join(out), encoding="utf-8")
    for f, old, new in REPLACE:
        new = new.replace("{repo}", repo)
        targets = [tmp / f] if f != "*" else [p for p, _ in text_files(tmp)]
        hit = 0
        for p in targets:
            s = p.read_text(encoding="utf-8")
            if old in s:
                hit += s.count(old)
                p.write_text(s.replace(old, new), encoding="utf-8")
        if not hit and f != "*":
            problems.append(f"replace found nothing: {f}: {old[:60]!r}")
    # STATUS.md: the "At a glance" table only (the rest is the team's history)
    st = tmp / "docs" / "STATUS.md"
    s = st.read_text(encoding="utf-8")
    cut = s.find("*The table below is the 26 Sept roadmap")
    if cut > 0:
        st.write_text(s[:cut].rstrip() + "\n", encoding="utf-8")
    else:
        problems.append("STATUS.md: the roadmap line to cut at was not found")
    return problems


def ci(tmp: Path) -> None:
    """The CI without the team job (it checked for a session log)."""
    p = tmp / ".github" / "workflows" / "ci.yml"
    s = p.read_text(encoding="utf-8")
    a = s.find("  # AGENTS.md rules that a machine can check")
    if a < 0:
        a = s.find("  # CONTRIBUTING.md rules that a machine can check")
    b = s.find("  # keys and passwords must never reach")
    if a < 0 or b < a:
        raise SystemExit("ci.yml: the team job was not found; update public_export.py")
    p.write_text(s[:a] + s[b:], encoding="utf-8")


def scan(tmp: Path) -> list[str]:
    hits = []
    for p in sorted(tmp.rglob("*")):
        rel = p.relative_to(tmp).as_posix()
        if DENY.search(rel) and not ALLOW_FILES.match(rel):
            hits.append(f"{rel}: (file name)")
    for p, s in text_files(tmp):
        rel = p.relative_to(tmp).as_posix()
        if ALLOW_FILES.match(rel):
            continue
        for i, line in enumerate(s.splitlines(), 1):
            if DENY.search(line) and not ALLOW_LINES.search(line):
                hits.append(f"{rel}:{i}: {line.strip()[:160]}")
    # links to files that are not in the copy
    for p, s in text_files(tmp):
        if p.suffix != ".md":
            continue
        for m in re.finditer(r"\]\((?!https?:|#|mailto:)((?:[^()\s]|\([^()\s]*\))+)\)", s):
            target = m.group(1).split("#")[0].replace("%20", " ")
            if target and not (p.parent / target).exists():
                hits.append(f"{p.relative_to(tmp).as_posix()}: broken link -> {m.group(1)}")
    return hits


def sync(tmp: Path, out: Path) -> tuple[int, int, int]:
    out.mkdir(parents=True, exist_ok=True)
    added = changed = removed = 0
    want = {p.relative_to(tmp) for p in tmp.rglob("*") if p.is_file()}
    for p in sorted(out.rglob("*"), reverse=True):
        rel = p.relative_to(out)
        if rel.parts and rel.parts[0] in OWN:
            continue
        if p.is_file() and rel not in want:
            p.unlink()
            removed += 1
        elif p.is_dir() and not any(p.iterdir()):
            p.rmdir()
    for rel in sorted(want):
        src, dst = tmp / rel, out / rel
        b = src.read_bytes()
        if not dst.exists():
            added += 1
        elif dst.read_bytes() != b:
            changed += 1
        else:
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(b)
    return added, changed, removed


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--ref", default="origin/main")
    ap.add_argument("--out", required=True, help="the public copy's folder (its own git repo)")
    ap.add_argument("--repo", required=True, help="the public GitHub repository, owner/name")
    a = ap.parse_args()
    out = Path(a.out).resolve()
    if out == ROOT or ROOT in out.parents:
        raise SystemExit("--out must be outside this repository")
    tmp = out.parent / (out.name + ".building")
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir(parents=True)
    try:
        snapshot(a.ref, tmp)
        problems = clean(tmp, a.repo)
        ci(tmp)
        hits = scan(tmp)
        if problems or hits:
            print("Not exported. Fix these first (or the rules in scripts/team/public_export.py):")
            for x in problems + hits:
                print("  " + x)
            sys.exit(1)
        n = sum(1 for p in tmp.rglob("*") if p.is_file())
        added, changed, removed = sync(tmp, out)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    sha = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--short", a.ref], check=True,
                         capture_output=True, text=True).stdout.strip()
    print(f"Public copy of {a.ref} ({sha}) in {out}: {n} files; "
          f"{added} added, {changed} changed, {removed} removed. Nothing private found.")


if __name__ == "__main__":
    main()
