"""Settings from the environment. Nothing secret is ever given a default."""

from __future__ import annotations

import os
from datetime import date

# The published eSAKSHI export was scraped in 2025; its latest recommendation
# date is the "today" for real works, so a work is not called late merely
# because the data is old. Overridable for live data.
DEFAULT_SNAPSHOT = "2025-05-26"


def database_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is not set")
    return url


def snapshot_date() -> date:
    return date.fromisoformat(os.environ.get("DRISHTI_SNAPSHOT_DATE", DEFAULT_SNAPSHOT))


def supabase_url() -> str | None:
    return os.environ.get("SUPABASE_URL")
