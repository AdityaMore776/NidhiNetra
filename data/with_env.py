r"""Run a data script against the hosted database without ever printing a secret.

Reads ~/drishti/.env.local (written by `vercel env pull` / `vercel integration add`,
gitignored), exports it to the environment, points DATABASE_URL at the Supabase
SESSION pooler (POSTGRES_URL_NON_POOLING, port 5432 - bulk COPY and long transactions
need a session, not the transaction pooler), then runs the named script.

Run:  apps\engine\.venv\Scripts\python.exe data\with_env.py load_db.py
"""

from __future__ import annotations

import os
import runpy
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ENV_FILE = HERE.parent / ".env.local"


def load_env() -> None:
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"'))
    sys.path.insert(0, str(HERE.parent / "apps" / "engine"))
    from drishti.config import clean_url

    os.environ["DATABASE_URL"] = clean_url(os.environ["POSTGRES_URL_NON_POOLING"])


if __name__ == "__main__":
    load_env()
    script = HERE / sys.argv[1]
    sys.argv = [str(script), *sys.argv[2:]]
    sys.path.insert(0, str(HERE))
    runpy.run_path(str(script), run_name="__main__")
