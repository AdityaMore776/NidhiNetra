"""Start DRISHTI locally in one terminal: database + engine + web. Ctrl+C stops all three.

    python scripts/dev/start.py                                  # Ministry view
    python scripts/dev/start.py --role DISTRICT --district 173   # a district officer (census code)

Needs: scripts/team/setup.py done, and the local database built once (setup.py --db).
Then open http://localhost:3000 (not 127.0.0.1). No login in dev mode: the role above is used.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ENGINE = ROOT / "apps" / "engine"
VENV_PY = ENGINE / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
PGDATA = ROOT / "data" / "cache" / "pg"


def main() -> None:
    ap = argparse.ArgumentParser(description="start database + engine + web")
    ap.add_argument("--role", default="MINISTRY", choices=["MINISTRY", "DISTRICT", "FIELD"])
    ap.add_argument("--district", default="", help="census district code, for --role DISTRICT")
    ap.add_argument("--port", type=int, default=8000, help="engine port")
    args = ap.parse_args()

    try:
        import pgserver
    except ImportError:
        if not VENV_PY.exists():
            raise SystemExit("run python scripts/team/setup.py first") from None
        # re-run inside the engine venv (not os.execv: on Windows it detaches from the terminal)
        try:
            sys.exit(subprocess.run([str(VENV_PY), __file__, *sys.argv[1:]]).returncode)
        except KeyboardInterrupt:
            sys.exit(0)

    if not (PGDATA / "PG_VERSION").exists():
        raise SystemExit("no local database yet: python scripts/team/setup.py --db")
    srv = pgserver.get_server(str(PGDATA), cleanup_mode="stop")
    url = srv.get_uri()

    engine_env = {**os.environ, "DATABASE_URL": url, "DRISHTI_AUTH": "dev"}
    web_env = {**os.environ, "NEXT_PUBLIC_DEV_ROLE": args.role,
               "NEXT_PUBLIC_DEV_DISTRICT": args.district,
               "ENGINE_DEV_URL": f"http://127.0.0.1:{args.port}"}   # next.config.ts forwards /api/v1 here
    for k in ("NEXT_PUBLIC_SUPABASE_URL", "NEXT_PUBLIC_SUPABASE_ANON_KEY"):
        web_env.pop(k, None)   # dev mode = no Supabase login

    procs = [
        subprocess.Popen([str(VENV_PY), "-m", "uvicorn", "drishti.main:app", "--port", str(args.port),
                          "--app-dir", str(ENGINE)], cwd=ROOT, env=engine_env),
        subprocess.Popen([shutil.which("npm") or "npm", "run", "dev"], cwd=ROOT / "apps" / "web",
                         env=web_env),
    ]
    print(f"\nDRISHTI is starting as {args.role}. Open http://localhost:3000  "
          f"(engine API docs: http://localhost:{args.port}/api/v1/docs). Ctrl+C stops everything.\n")
    try:
        while all(p.poll() is None for p in procs):
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        for p in procs:
            if p.poll() is None:
                if os.name == "nt":   # npm starts node children; terminate() would leave them on port 3000
                    subprocess.run(["taskkill", "/T", "/F", "/PID", str(p.pid)], capture_output=True)
                else:
                    p.terminate()
        for p in procs:
            try:
                p.wait(timeout=15)
            except subprocess.TimeoutExpired:
                p.kill()
        print("stopped (the database stops cleanly on exit)")


if __name__ == "__main__":
    main()
