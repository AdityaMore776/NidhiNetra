"""Apply the SQL files in drishti/migrations, in name order, exactly once each.

The same runner serves the test database (pgserver) and Supabase, so the
schema the tests pass against is the schema production gets.
"""

from __future__ import annotations

from pathlib import Path

import psycopg

MIGRATIONS = Path(__file__).resolve().parent / "migrations"


def apply(url: str) -> list[str]:
    """Apply pending migrations. Returns the file names applied this call."""
    applied: list[str] = []
    with psycopg.connect(url, prepare_threshold=None) as con:
        con.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations ("
            " name text PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now())"
        )
        con.execute("ALTER TABLE schema_migrations ENABLE ROW LEVEL SECURITY")
        done = {r[0] for r in con.execute("SELECT name FROM schema_migrations").fetchall()}
        for path in sorted(MIGRATIONS.glob("*.sql")):
            if path.name in done:
                continue
            con.execute(path.read_text(encoding="utf-8"))
            con.execute("INSERT INTO schema_migrations (name) VALUES (%s)", (path.name,))
            applied.append(path.name)
        con.commit()
    return applied


if __name__ == "__main__":
    import os

    print(apply(os.environ["DATABASE_URL"]) or "nothing to apply")
