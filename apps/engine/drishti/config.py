"""Settings from the environment. Nothing secret is ever given a default."""

from __future__ import annotations

import os
from datetime import date
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

# The eSAKSHI export was scraped in late May 2026 (latest recommendation date
# 2026-05-26). That date is the "today" for real works, so a work is not called late merely
# because the data is old. Overridable for live data.
DEFAULT_SNAPSHOT = "2026-05-26"

# Vercel's Supabase integration appends pooler hints that libpq rejects as unknown
# connection options ("supa=base-pooler.x", "pgbouncer=true").
_NOT_LIBPQ = {"supa", "pgbouncer"}


def clean_url(url: str) -> str:
    parts = urlsplit(url)
    query = [(k, v) for k, v in parse_qsl(parts.query) if k not in _NOT_LIBPQ]
    return urlunsplit(parts._replace(query=urlencode(query)))


def database_url() -> str:
    """DATABASE_URL if set, else POSTGRES_URL from the Vercel Supabase integration.

    On Vercel POSTGRES_URL is the transaction pooler (port 6543), which is what a
    serverless function should use; db.py already disables prepared statements for it.
    """
    url = os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL")
    if not url:
        raise RuntimeError("DATABASE_URL (or POSTGRES_URL) is not set")
    return clean_url(url)


def snapshot_date() -> date:
    return date.fromisoformat(os.environ.get("DRISHTI_SNAPSHOT_DATE", DEFAULT_SNAPSHOT))


def supabase_url() -> str | None:
    return os.environ.get("SUPABASE_URL")
