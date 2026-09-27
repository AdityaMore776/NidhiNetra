r"""Load the built parquet files into Postgres (local pgserver or Supabase).

Idempotent: tables are emptied and refilled in one transaction, so a failed
load leaves the previous data in place.

Run:
  $env:DATABASE_URL = "postgresql://..."      # Supabase session pooler (port 5432) for bulk loads
  apps\engine\.venv\Scripts\python.exe data\load_db.py
"""

from __future__ import annotations

import os
import time

import pandas as pd
import psycopg

from common import BUILD, clean
from drishti import migrate

TABLES = {
    "districts": ["district_lgd", "name", "state_lgd", "state_name"],
    "works": ["work_id", "source", "house", "term", "state_lgd", "state_name", "district_lgd",
              "district_name", "constituency", "mp_name", "agency_name", "fy",
              "work_type_code", "category", "description", "amount", "recommended_date",
              "completed_date", "status", "quantity", "quantity_unit",
              "is_outside_constituency"],
    "cohort_stats": ["level", "work_type_code", "key", "n", "p10", "p50", "p90", "sd"],
    "duration_stats": ["work_type_code", "n", "p50", "p90", "p98"],
    "unit_rate_models": ["work_type_code", "unit", "n", "slope", "intercept", "resid_sd",
                         "anchor_low", "anchor_high", "anchor_label"],
    "timeline_quarters": ["quarter", "n", "bad"],
    "timeline_agencies": ["agency_name", "completed", "bad"],
}
MAX_DB_MB = 400


def load(url: str) -> None:
    print("migrations applied:", migrate.apply(url) or "none pending")
    with psycopg.connect(url, prepare_threshold=None) as con:
        con.execute("TRUNCATE assessments, works, districts, cohort_stats, duration_stats, "
                    "unit_rate_models, timeline_quarters, timeline_agencies")
        for table, cols in TABLES.items():
            t0 = time.time()
            df = pd.read_parquet(BUILD / f"{table}.parquet")
            with con.cursor().copy(f"COPY {table} ({', '.join(cols)}) FROM STDIN") as cp:
                for rec in df[cols].to_dict("records"):
                    r = clean(rec)
                    cp.write_row([r[c] for c in cols])
            print(f"{table}: {len(df):,} rows in {time.time() - t0:.0f}s")
        con.commit()
        con.execute("ANALYZE")
        mb = con.execute("SELECT pg_database_size(current_database()) / 1e6").fetchone()[0]
    print(f"database size: {mb:.0f} MB")
    if mb > MAX_DB_MB:
        raise SystemExit(f"over the {MAX_DB_MB} MB budget for the free tier - stop and slim")


if __name__ == "__main__":
    load(os.environ["DATABASE_URL"])
