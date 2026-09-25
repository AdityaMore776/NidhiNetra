"""Database connections.

prepare_threshold=None because production goes through Supabase's
transaction pooler, which cannot hold prepared statements across requests.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

import psycopg
from psycopg.rows import dict_row

from drishti import config


@contextmanager
def connect(url: str | None = None) -> Iterator[psycopg.Connection]:
    con = psycopg.connect(url or config.database_url(), prepare_threshold=None,
                          row_factory=dict_row)
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()
