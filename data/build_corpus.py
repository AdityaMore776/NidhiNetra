r"""Build data/build/works.parquet and districts.parquet from the old research build.

Source of truth for the 209,993 real works is ~/saakshya's cleaned DuckDB
(its eSAKSHI adapter already pivoted the three stage rows into one work and
resolved districts to LGD codes). What that table lacks - house, term,
constituency, MP name, agency name, category - is joined back from the raw
eSAKSHI CSVs on the ACTIVITY_NAME reference, which is the old work_id minus
its "ESK-" prefix.

Run: apps\engine\.venv\Scripts\python.exe data\build_corpus.py
"""

from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path

import duckdb
import pandas as pd

OLD = Path(os.environ.get("DRISHTI_OLD_REPO", Path.home() / "saakshya"))
DB = OLD / "data" / "db" / "drishti_real.duckdb"
RAW = OLD / "data" / "raw" / "inrolls"
OUT = Path(__file__).resolve().parent / "build"

REF = re.compile(r"^(WS/[^/]+/\d{4}-\d{4}/\d+)-")
IDA = re.compile(r"^([^(]+)\((.*)\)\s*$")

EXPECTED_WORKS = 209_993
EXPECTED_STATUS = {"RECOMMENDED": 28_433, "SANCTIONED": 94_662, "COMPLETED": 86_898}
EXPECTED_NO_TYPE = 6_658


def raw_attributes() -> pd.DataFrame:
    cols = ["tenure_label", "house", "state_name", "CONSTITUENCY", "mp_name",
            "ACTIVITY_NAME", "IDA_NAME", "WORK_CATEGORY",
            # the four fields the old adapter hashed into a NOREF id
            "mp_id", "WORK_DESCRIPTION", "RECOMMENDED_AMOUNT"]
    frames = []
    for name in ("works_ls17.csv", "works_ls18.csv", "works_rs.csv"):
        df = pd.read_csv(RAW / name, usecols=cols, dtype=str, low_memory=False)
        frames.append(df)
    raw = pd.concat(frames, ignore_index=True)
    raw["ref"] = raw["ACTIVITY_NAME"].str.extract(REF, expand=False)
    # Works eSAKSHI gave no reference were keyed by the old adapter on a hash of
    # four fields (ingest/adapters/esakshi.py, pivot_stages). Rebuild the same key.
    blank = raw[["mp_id", "WORK_DESCRIPTION", "IDA_NAME", "RECOMMENDED_AMOUNT"]].fillna("")
    noref = blank.agg("|".join, axis=1).map(
        lambda t: "NOREF-" + hashlib.sha1(t.encode()).hexdigest()[:14])
    raw["ref"] = raw["ref"].fillna(noref)
    agency = raw["IDA_NAME"].fillna("").str.strip()
    raw["agency_name"] = agency.where(agency != "", None)
    first = raw.groupby("ref", sort=False).first()
    return first.rename(columns={
        "tenure_label": "term", "CONSTITUENCY": "constituency",
        "WORK_CATEGORY": "category", "state_name": "raw_state_name"})[
        ["term", "house", "raw_state_name", "constituency", "mp_name", "agency_name",
         "category"]]


def main() -> None:
    con = duckdb.connect(str(DB), read_only=True)
    works = con.execute("""
        SELECT w.work_id AS old_id, w.fy, w.district_lgd_code AS district_lgd,
               d.name AS district_name, d.state_lgd_code AS state_lgd, d.state_name,
               w.work_type_code, w.description_raw AS description,
               w.estimated_cost AS amount, w.recommended_date, w.completed_date,
               w.status, w.quantity, w.quantity_unit, w.is_outside_constituency
        FROM work w LEFT JOIN district d ON d.district_lgd_code = w.district_lgd_code
    """).df()
    districts = con.execute("""
        SELECT district_lgd_code AS district_lgd, name, state_lgd_code AS state_lgd,
               state_name FROM district
    """).df()
    con.close()

    assert len(works) == EXPECTED_WORKS, len(works)
    assert works.status.value_counts().to_dict() == EXPECTED_STATUS
    assert int(works.work_type_code.isna().sum()) == EXPECTED_NO_TYPE

    works["ref"] = works["old_id"].str.removeprefix("ESK-")
    attrs = raw_attributes()
    works = works.join(attrs, on="ref")
    joined = works["constituency"].notna().mean()
    print(f"constituency joined for {joined:.1%} of works")
    assert joined > 0.95, joined

    works["state_name"] = works["state_name"].fillna(works["raw_state_name"])
    works["work_id"] = works["ref"]
    works["source"] = "REAL"
    for c in ("recommended_date", "completed_date"):
        works[c] = pd.to_datetime(works[c]).dt.date
    keep = ["work_id", "source", "house", "term", "state_lgd", "state_name",
            "district_lgd", "district_name", "constituency", "mp_name", "agency_name", "fy",
            "work_type_code", "category", "description", "amount", "recommended_date",
            "completed_date", "status", "quantity", "quantity_unit",
            "is_outside_constituency"]
    works = works[keep]
    assert works.work_id.is_unique

    OUT.mkdir(parents=True, exist_ok=True)
    works.to_parquet(OUT / "works.parquet", index=False)
    districts.to_parquet(OUT / "districts.parquet", index=False)
    print(f"wrote {len(works):,} works and {len(districts):,} districts to {OUT}")
    print(works.house.value_counts(dropna=False).to_string())


if __name__ == "__main__":
    main()
