"""Small helpers shared by the team scripts. Standard library only, so they run on any machine."""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOG_DIR = ROOT / "docs" / "team" / "log"
IST = timezone(timedelta(hours=5, minutes=30))  # fixed offset: zoneinfo needs tzdata on Windows

if hasattr(sys.stdout, "reconfigure"):  # Windows consoles default to cp1252 and choke on "₹"
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def run(*cmd: str) -> str | None:
    """Run a command in the repo; return its output, or None if it is missing or fails."""
    if shutil.which(cmd[0]) is None:
        return None
    try:
        out = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
                             errors="replace", timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return out.stdout.strip() if out.returncode == 0 else None


def gh_ok() -> bool:
    return run("gh", "auth", "status") is not None


def github_user() -> str:
    """The GitHub login if gh is logged in, else the git user name."""
    name = run("gh", "api", "user", "--jq", ".login") or run("git", "config", "user.name") or "someone"
    return name


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "x"


def now_ist() -> datetime:
    return datetime.now(IST)


def log_entries() -> list[Path]:
    """Every log entry, oldest first (file names start with the date and time)."""
    return sorted(p for p in LOG_DIR.glob("*.md") if p.name[:1].isdigit())
