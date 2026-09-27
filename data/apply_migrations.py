"""Apply pending engine migrations to the database in DATABASE_URL (hosted: run via data/with_env.py).

    apps\\engine\\.venv\\Scripts\\python.exe data\\with_env.py apply_migrations.py

Run this BEFORE merging code that needs a new migration, or the live API will miss the table.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "engine"))
from drishti import migrate  # noqa: E402

print("migrations applied:", migrate.apply(os.environ["DATABASE_URL"]) or "none pending")
