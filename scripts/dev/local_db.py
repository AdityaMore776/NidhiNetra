r"""Run a local Postgres with the real corpus: no Docker, no account, no internet after install.

Uses pgserver (Postgres 16 + pgvector from pip, already in the engine's dev requirements). Needs the
built data from the team pack (data/build/*.parquet, see docs/team/DATA-PACK.md).

    # PowerShell, from the repo root, with the engine venv:
    apps\engine\.venv\Scripts\python.exe scripts\dev\local_db.py --load    # first time: load + assess (~minutes)
    apps\engine\.venv\Scripts\python.exe scripts\dev\local_db.py           # later: just start it

It prints the DATABASE_URL to use in the engine terminal, then keeps the database running until Ctrl+C.
The data lives in data/cache/pg (gitignored).
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PGDATA = ROOT / "data" / "cache" / "pg"


def main() -> None:
    ap = argparse.ArgumentParser(description="local Postgres with the real corpus")
    ap.add_argument("--load", action="store_true", help="load data/build and assess every work")
    ap.add_argument("--dir", type=Path, default=PGDATA, help="where the database files live")
    args = ap.parse_args()

    try:
        import pgserver
    except ImportError:
        raise SystemExit("pgserver missing: use the engine venv (apps/engine/.venv) after "
                         "`pip install -e . -r requirements-dev.txt`") from None

    args.dir.mkdir(parents=True, exist_ok=True)
    srv = pgserver.get_server(str(args.dir), cleanup_mode="stop")
    url = srv.get_uri()
    env = {**os.environ, "DATABASE_URL": url}

    if args.load:
        if not (ROOT / "data" / "build" / "works.parquet").exists():
            raise SystemExit("data/build/works.parquet missing: install the team pack first "
                             "(docs/team/DATA-PACK.md)")
        for script in ("load_db.py", "batch_assess.py"):
            print(f"\n--- running data/{script}")
            subprocess.run([sys.executable, str(ROOT / "data" / script)], env=env, cwd=ROOT / "data",
                           check=True)

    print("\nLocal database is running. In another PowerShell window, start the engine with:")
    print(f'  $env:DATABASE_URL = "{url}"')
    print('  $env:DRISHTI_AUTH = "dev"')
    print("  apps\\engine\\.venv\\Scripts\\python.exe -m uvicorn drishti.main:app --port 8000 --app-dir apps/engine")
    print("Then the web app: see docs/SETUP.md section 2.  Ctrl+C here stops the database.")
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        print("stopping")


if __name__ == "__main__":
    main()
