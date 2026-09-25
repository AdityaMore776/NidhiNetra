"""One real Postgres (pgserver) for the whole run; a fresh database per test.

pgserver is Postgres 16 + pgvector installed by pip, so these tests run the
same SQL as Supabase with no Docker. Each test gets its own database so no
test can see another's rows.
"""

from __future__ import annotations

import itertools
import tempfile

import psycopg
import pytest

_counter = itertools.count()


@pytest.fixture(scope="session")
def pg_server():
    import pgserver

    srv = pgserver.get_server(tempfile.mkdtemp(prefix="drishti-pg-"), cleanup_mode="stop")
    yield srv


@pytest.fixture()
def db_url(pg_server) -> str:
    name = f"t{next(_counter)}"
    admin = pg_server.get_uri()
    with psycopg.connect(admin, autocommit=True) as con:
        con.execute(f"DROP DATABASE IF EXISTS {name}")
        con.execute(f"CREATE DATABASE {name}")
    return admin.rsplit("/", 1)[0] + f"/{name}"


@pytest.fixture()
def migrated_url(db_url) -> str:
    from drishti import migrate

    migrate.apply(db_url)
    return db_url
