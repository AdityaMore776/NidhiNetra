r"""Load the built parquet files into Postgres (local pgserver or Supabase).

Idempotent: tables are emptied and refilled in one transaction, so a failed
load leaves the previous data in place. The works are replaced in place instead
(drishti/reload.py, T169): saved cost forms and site visits point at them and
must survive every reload.

Run:
  $env:DATABASE_URL = "postgresql://..."      # Supabase session pooler (port 5432) for bulk loads
  apps\engine\.venv\Scripts\python.exe data\load_db.py
"""

from __future__ import annotations

import json
import os
import time

import pandas as pd
import psycopg

from common import BUILD, clean, model_rows, signal_rows
from drishti import migrate, reload

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
    "evidence_facts": ["work_id", "data", "version"],
}
# Built by a later data job (T051); an older data pack may not have them yet.
OPTIONAL = {"evidence_facts": "data/build_evidence.py (needs the evidence + OCR cache)"}
MAX_DB_MB_NOTE = "free tier is 500 MB"
MAX_DB_MB = 400


def load_signals(con: psycopg.Connection) -> None:
    """Offline engine facts (common.SIGNALS) into work_signals; a signal not built is skipped."""
    t0 = time.time()
    n = 0
    with con.cursor().copy("COPY work_signals (work_id, engine, data, version) FROM STDIN") as cp:
        for work_id, engine, data, version in signal_rows():
            cp.write_row([work_id, engine, json.dumps(data), version])
            n += 1
    print(f"work_signals: {n:,} rows in {time.time() - t0:.0f}s")


def load(url: str) -> None:
    print("migrations applied:", migrate.apply(url) or "none pending")
    with psycopg.connect(url, prepare_threshold=None) as con:
        # never `works` here: cost_forms and site_visits reference it (reload.replace_works)
        con.execute("TRUNCATE assessments, work_signals, districts, cohort_stats, "
                    "duration_stats, unit_rate_models, timeline_quarters, timeline_agencies, "
                    "evidence_facts")
        for table, cols in TABLES.items():
            t0 = time.time()
            if table in OPTIONAL and not (BUILD / f"{table}.parquet").exists():
                print(f"{table}: no data/build/{table}.parquet - run {OPTIONAL[table]}; the "
                      "engine will report NOT_ASSESSABLE where it needs it")
                continue
            df = pd.read_parquet(BUILD / f"{table}.parquet")
            rows = ([r[c] for c in cols] for r in map(clean, df[cols].to_dict("records")))
            if table == "works":
                out = reload.replace_works(con, cols, rows)
                print(f"works: {len(df):,} rows ({out['written']:,} new or changed) in "
                      f"{time.time() - t0:.0f}s; {out['removed']:,} gone from the source "
                      f"removed, {out['kept_for_saved_input']:,} kept for their saved form or "
                      f"site visit")
                continue
            with con.cursor().copy(f"COPY {table} ({', '.join(cols)}) FROM STDIN") as cp:
                for r in rows:
                    cp.write_row(r)
            print(f"{table}: {len(df):,} rows in {time.time() - t0:.0f}s")
        load_signals(con)
        con.execute("TRUNCATE engine_models")
        for m in model_rows():
            con.execute("INSERT INTO engine_models (name, version, data) VALUES (%s, %s, %s)",
                        (m["name"], m["version"], json.dumps(m["data"])))
            print(f"engine_models: {m['name']} {m['version']}")
        con.commit()
        con.execute("ANALYZE")
        mb = con.execute("SELECT pg_database_size(current_database()) / 1e6").fetchone()[0]
    print(f"database size: {mb:.0f} MB")
    if mb > MAX_DB_MB:
        raise SystemExit(f"over the {MAX_DB_MB} MB budget for the free tier - stop and slim")


if __name__ == "__main__":
    load(os.environ["DATABASE_URL"])
