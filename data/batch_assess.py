r"""Assess every work in the database and store the results.

Run after load_db.py:
  apps\engine\.venv\Scripts\python.exe data\batch_assess.py
"""

from __future__ import annotations

import os
import time

import psycopg

from common import config  # noqa: F401  (puts the engine on the path)
from drishti.agents.statistical.cohort import StatsStore
from drishti.batch import assess_all
from drishti.pipeline.orchestrator import Context


def main() -> None:
    url = os.environ["DATABASE_URL"]
    ctx = Context(stats=StatsStore.load(url), as_of=config.snapshot_date())
    t0 = time.time()
    bands = assess_all(url, ctx)
    print(f"assessed {sum(bands.values()):,} works in {time.time() - t0:.0f}s: {bands}")
    with psycopg.connect(url, prepare_threshold=None) as con:
        mb = con.execute("SELECT pg_database_size(current_database()) / 1e6").fetchone()[0]
    print(f"database size after assessment: {mb:.0f} MB")


if __name__ == "__main__":
    main()
