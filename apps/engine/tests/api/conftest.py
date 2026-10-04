"""A small, fully assessed database behind the API, with dev sign-in switched on."""

from __future__ import annotations

from datetime import date

import psycopg
import pytest
from fastapi.testclient import TestClient

from drishti import batch
from drishti.agents.statistical.cohort import StatsStore
from drishti.pipeline.orchestrator import Context

WORKS = [
    # work_id, district, name, type, amount, description, status, recommended
    ("W-TYPICAL", "639", "Anand", "ROAD_CC", 160_000, "CC road in village Bijdih",
     "SANCTIONED", date(2026, 1, 10)),
    # overpriced AND waiting for sanction 20 months, when 1 in 25 works that old still wait
    # (R01, T054): two engines agree -> in the queue
    ("W-COSTLY", "639", "Anand", "ROAD_CC", 1_000_000, "CC road in village Vasad",
     "RECOMMENDED", date(2024, 9, 1)),
    # recorded complete two days after its sanction (Time & Rules, R14: 25 of 25 read right):
    # one well-measured finding -> in the queue (T125)
    ("W-OTHER-DISTRICT", "640", "Kheda", "ROAD_CC", 2_500_000, "CC road near Kheda market",
     "COMPLETED", date(2026, 1, 10)),
    ("W-NO-TYPE", "639", "Anand", None, 300_000, "Letter as per attached",
     "RECOMMENDED", date(2026, 2, 1)),
]


@pytest.fixture()
def api_db(migrated_url, monkeypatch):
    with psycopg.connect(migrated_url) as con:
        con.execute("INSERT INTO districts VALUES ('639','Anand','24','Gujarat'),"
                    "('640','Kheda','24','Gujarat')")
        for wid, dl, dn, wt, amt, desc, status, rec in WORKS:
            con.execute(
                "INSERT INTO works (work_id, source, state_lgd, state_name, district_lgd, "
                "district_name, work_type_code, description, amount, status, "
                "recommended_date) VALUES (%s,'REAL','24','Gujarat',%s,%s,%s,%s,%s,%s,%s)",
                (wid, dl, dn, wt, desc, amt, status, rec))
        con.execute("UPDATE works SET sanction_date = '2026-02-01', completed_date = '2026-02-03' "
                    "WHERE work_id = 'W-OTHER-DISTRICT'")
        con.execute("INSERT INTO cohort_stats VALUES "
                    "('type_district','ROAD_CC','639',709,4.9,5.204,5.5,0.2),"
                    "('type','ROAD_CC','',49000,4.9,5.2,5.5,0.2)")
        con.commit()
    ctx = Context(stats=StatsStore.load(migrated_url), as_of=date(2026, 5, 26))
    batch.assess_all(migrated_url, ctx)
    monkeypatch.setenv("DATABASE_URL", migrated_url)
    monkeypatch.setenv("DRISHTI_AUTH", "dev")
    monkeypatch.delenv("VERCEL", raising=False)
    return migrated_url


@pytest.fixture()
def client(api_db):
    from drishti.main import app

    return TestClient(app)


MINISTRY = {"X-Dev-Role": "MINISTRY"}
DISTRICT_ANAND = {"X-Dev-Role": "DISTRICT", "X-Dev-District": "639"}
