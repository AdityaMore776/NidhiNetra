"""One-command setup for a new teammate's machine. Safe to re-run: finished steps are skipped.

    python scripts/team/setup.py            # tools check, engine + web installs, tests
    python scripts/team/setup.py --db       # also build the local database with the real corpus (~10 min)

What it does:
  1. checks Python 3.12+, Node 20+, git, and the GitHub CLI login
  2. creates apps/engine/.venv and installs the engine, its test tools and the data-job libraries
  3. installs the web app's packages (npm ci)
  4. installs the private data pack if its zip is in Downloads/Documents/Desktop (docs/team/DATA-PACK.md)
  5. --db: starts a local Postgres, loads the corpus and assesses every work (scripts/dev/local_db.py)
  6. runs the engine tests to prove the setup works
Your AI runs this on its first session (AGENTS.md section 2).
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

from _common import ROOT, gh_ok, run

ENGINE = ROOT / "apps" / "engine"
WEB = ROOT / "apps" / "web"
WIN = os.name == "nt"
VENV_PY = ENGINE / ".venv" / ("Scripts/python.exe" if WIN else "bin/python")


def step(title: str) -> None:
    print(f"\n=== {title}")


def sh(cmd: list[str], cwd: Path = ROOT) -> None:
    print("  $ " + " ".join(cmd))
    exe = shutil.which(cmd[0]) or cmd[0]      # npm is npm.cmd on Windows
    subprocess.run([exe, *cmd[1:]], cwd=cwd, check=True)


def engine_python() -> list[str] | None:
    """A Python 3.12+ to build the engine venv with. 3.12 first: CI uses it and every wheel exists for it."""
    candidates = [["py", "-3.12"], ["python3.12"], ["py", "-3.13"], ["python3.13"]]
    if sys.version_info >= (3, 12):
        candidates.insert(1, [sys.executable])
    for cmd in candidates:
        out = run(*cmd, "-c", "import sys; print(sys.version_info >= (3, 12))")
        if out == "True":
            return cmd
    return None


def check_tools() -> list[str]:
    problems = []
    if VENV_PY.exists() or engine_python():
        pass
    else:
        problems.append(f"Python 3.12+ needed (found {sys.version.split()[0]}): "
                        "winget install --id Python.Python.3.12 -e")
    node = run("node", "--version")
    if not node or int(node.lstrip("v").split(".")[0]) < 20:
        problems.append("Node.js 20+ needed: winget install --id OpenJS.NodeJS.LTS -e")
    if not run("git", "--version"):
        problems.append("git needed: winget install --id Git.Git -e")
    if not run("gh", "--version"):
        problems.append("GitHub CLI needed: winget install --id GitHub.cli -e, then gh auth login")
    elif not gh_ok():
        problems.append("GitHub CLI not logged in: run  gh auth login  (browser login)")
    if not run("git", "config", "user.email"):
        problems.append('git doesn\'t know who you are: git config --global user.name "Your Name"; '
                        'git config --global user.email "you@example.com"')
    return problems


def engine() -> None:
    step("Engine (Python)")
    if not VENV_PY.exists():
        py = engine_python()
        sh([*py, "-m", "venv", str(ENGINE / ".venv")])
    sh([str(VENV_PY), "-m", "pip", "install", "--quiet", "--upgrade", "pip"])
    sh([str(VENV_PY), "-m", "pip", "install", "--quiet", "-e", ".", "-r", "requirements-dev.txt",
        "-r", str(ROOT / "data" / "requirements.txt")], cwd=ENGINE)


def web() -> None:
    step("Web (Next.js)")
    if (WEB / "node_modules" / "next").exists():
        print("  already installed (delete apps/web/node_modules to reinstall)")
        return
    sh(["npm", "ci"], cwd=WEB)


def data_pack() -> bool:
    step("Private data pack")
    if (ROOT / "data" / "build" / "works.parquet").exists():
        print("  already installed")
        return True
    home = Path.home()
    zips = sorted((p for d in (home / "Downloads", home / "Documents", home / "Desktop", ROOT)
                   if d.exists() for p in d.glob("DRISHTI-team-pack*.zip")),
                  key=lambda p: p.stat().st_mtime, reverse=True)
    if not zips:
        print("  not found. Ask the owner for DRISHTI-team-pack.zip (private Google Drive), put it in\n"
              "  Downloads and re-run. You can already work on tasks that need no data (e.g. T010).")
        return False
    try:
        sh([sys.executable, str(ROOT / "scripts" / "team" / "install_pack.py"), str(zips[0])])
    except subprocess.CalledProcessError:
        print("  could not install the pack (message above); carrying on without it")
        return False
    return True


def local_db() -> None:
    step("Local database (takes several minutes the first time)")
    print("  starts Postgres, loads 2,09,993 works and assesses them, then keeps running:")
    print("  press Ctrl+C when it says the database is running.")
    try:
        sh([str(VENV_PY), str(ROOT / "scripts" / "dev" / "local_db.py"), "--load"])
    except KeyboardInterrupt:
        print("  stopped. Later: python scripts/dev/start.py")


def tests() -> None:
    step("Engine tests")
    sh([str(VENV_PY), "-m", "pytest", "-q", "-p", "no:cacheprovider"], cwd=ENGINE)


def main() -> None:
    ap = argparse.ArgumentParser(description="set up this machine for DRISHTI")
    ap.add_argument("--db", action="store_true", help="also build the local database (needs the pack)")
    args = ap.parse_args()

    step("Tools")
    problems = check_tools()
    for p in problems:
        print(f"  MISSING: {p}")
    if any(p.startswith(("Python", "Node", "git needed")) for p in problems):
        raise SystemExit("\nInstall the missing tools, reopen the terminal, and run this again.")
    if not problems:
        print("  all present")

    engine()
    web()
    have_data = data_pack()
    tests()
    if args.db and have_data:
        local_db()

    step("Done")
    print("  Start the app locally:   python scripts/dev/start.py   (needs the data pack + --db once)")
    print("  Session briefing:        python scripts/team/sync.py")
    if problems:
        print("  Still to fix: " + "; ".join(problems))


if __name__ == "__main__":
    main()
