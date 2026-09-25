from pathlib import Path

import psycopg

from drishti import migrate

TABLES = {"districts", "works", "cohort_stats", "duration_stats", "unit_rate_models",
          "assessments", "profiles", "schema_migrations"}


def _tables(url):
    with psycopg.connect(url) as con:
        rows = con.execute(
            "SELECT tablename FROM pg_tables WHERE schemaname = 'public'").fetchall()
    return {r[0] for r in rows}


def test_apply_creates_every_table(db_url):
    applied = migrate.apply(db_url)
    assert TABLES <= _tables(db_url)
    files = sorted(Path(migrate.MIGRATIONS).glob("*.sql"))
    assert applied == [f.name for f in files]


def test_apply_twice_is_a_no_op(db_url):
    migrate.apply(db_url)
    assert migrate.apply(db_url) == []
    with psycopg.connect(db_url) as con:
        n = con.execute("SELECT count(*) FROM schema_migrations").fetchone()[0]
    assert n == len(list(Path(migrate.MIGRATIONS).glob("*.sql")))


def test_row_level_security_is_on_everywhere(migrated_url):
    with psycopg.connect(migrated_url) as con:
        rows = con.execute(
            "SELECT relname FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
            "WHERE n.nspname = 'public' AND c.relkind = 'r' AND NOT c.relrowsecurity"
        ).fetchall()
    assert rows == []
