"""T062 API: POST /plans/generate and GET /plans/{id} on a small real-district database."""

from __future__ import annotations

import psycopg
import pytest
from fastapi.testclient import TestClient
from psycopg.types.json import Jsonb

from drishti.agents.contract import BANNED_WORDS
from drishti.planner import service

KARUR = "613"            # census code works carry; Karur, Tamil Nadu


def _reason(text):
    return {"reasons": [{"code": "BUILT_IN_DAYS", "source": "time_rules", "text_en": text,
                         "text_hi": "तिथियों की जाँच करें।"}]}


# work_id, description, status, band, score, priority, case_id
WORKS = [
    ("K-1", "Two Class Room Building on GHSS Rachandar Thirumalai Village", "COMPLETED",
     "HIGH", 0.82, 2.2, None),
    ("K-2", "CC road, phone 9876543210, Letter as per attached", "SANCTIONED", "HIGH", 0.6,
     1.5, None),
    ("K-3a", "Street lights piece 1", "COMPLETED", "HIGH", 0.7, 1.0, "case-1"),
    ("K-3b", "Street lights piece 2", "COMPLETED", "HIGH", 0.7, 0.9, "case-1"),
    ("K-L1", "Hand pump", "COMPLETED", "LOW", 0.0, 0.0, None),
    ("K-L2", "Library books", "SANCTIONED", "MEDIUM", 0.3, 0.4, None),
    ("K-L3", "Not yet sanctioned hall", "RECOMMENDED", "LOW", 0.0, 0.0, None),
]


@pytest.fixture()
def client(migrated_url, monkeypatch):
    with psycopg.connect(migrated_url) as con:
        for wid, desc, status, band, score, prio, case in WORKS:
            con.execute(
                "INSERT INTO works (work_id, source, state_name, district_lgd, district_name, "
                "description, amount, status) VALUES (%s,'REAL','Tamil Nadu',%s,'Karur',%s,"
                "500000,%s)", (wid, KARUR, desc, status))
            con.execute(
                "INSERT INTO assessments (work_id, score, band, priority, parts, validation, "
                "agents, versions, headline, case_id) VALUES (%s,%s,%s,%s,%s,'{}','[]','{}',"
                "%s,%s)",
                (wid, score, band, prio, Jsonb(_reason(f"Check the dates of {wid}.")),
                 f"Check {wid}.", case))
        con.execute("INSERT INTO works (work_id, source, district_lgd, district_name, status) "
                    "VALUES ('OTHER-1','REAL','640','Elsewhere','COMPLETED')")
        # eSAKSHI's district left unresolved (2 live queue cases, 11 Oct 2026): nowhere to plan from
        con.execute("INSERT INTO works (work_id, source, district_lgd, status) "
                    "VALUES ('NOWHERE-1','REAL','UNRESOLVED','COMPLETED')")
        con.execute("INSERT INTO assessments (work_id, score, band, priority, parts, validation, "
                    "agents, versions) VALUES ('NOWHERE-1',0.6,'HIGH',1,'{}','{}','[]','{}')")
        con.commit()
    monkeypatch.setenv("DATABASE_URL", migrated_url)
    monkeypatch.setenv("DRISHTI_AUTH", "dev")
    monkeypatch.delenv("VERCEL", raising=False)
    from drishti.main import app

    return TestClient(app)


MINISTRY = {"X-Dev-Role": "MINISTRY"}


def gen(client, **body):
    return client.post("/api/v1/plans/generate", json={"district": KARUR, "day": "2026-10-11",
                                                       **body}, headers=MINISTRY)


def test_a_plan_visits_each_queue_case_once_and_adds_a_spot_check(client):
    r = gen(client)
    assert r.status_code == 200, r.text
    p = r.json()
    assert p["id"] == "613_2026-10-11_8"
    assert p["district"]["name"] == "Karur"
    assert p["totals"]["flagged_in_queue"] == 3          # K-3a and K-3b are one case
    assert p["totals"]["spot_checks_drawn"] == 1         # 10% of 3, at least 1
    ids = [s["work_id"] for s in p["stops"]]
    assert "K-3b" not in ids and {"K-1", "K-2", "K-3a"} <= set(ids)
    spot = [s for s in p["stops"] if s["kind"] == "spot"]
    assert len(spot) == 1 and spot[0]["work_id"] in {"K-L1", "K-L2"}   # never unsanctioned
    assert p["totals"]["minutes"] <= 8 * 60


def test_stops_carry_their_place_checklist_and_times(client):
    p = gen(client).json()
    by = {s["work_id"]: s for s in p["stops"]}
    assert by["K-1"]["location"]["precision"] == "village"
    assert by["K-1"]["location"]["place"] == "Rachandarthirumalai"
    assert by["K-2"]["location"]["precision"] == "district"
    assert by["K-1"]["checklist"][0]["en"] == "Check the dates of K-1."
    assert by["K-1"]["checklist"][-1]["en"].startswith("Record what you found")
    assert "9876543210" not in by["K-2"]["description"]
    assert p["stops"][0]["arrive"] >= "09:00"
    assert [s["order"] for s in p["stops"]] == list(range(1, len(p["stops"]) + 1))


def test_the_same_id_gives_the_same_plan(client):
    first = gen(client).json()
    again = client.get(f"/api/v1/plans/{first['id']}", headers=MINISTRY)
    assert again.status_code == 200
    assert again.json() == first


def test_a_short_day_sends_the_rest_to_the_next_trip(client):
    p = gen(client, hours=2).json()
    assert p["totals"]["minutes"] <= 120
    flagged_seen = {s["work_id"] for s in p["stops"] if s["kind"] == "flagged"}
    flagged_seen |= {w["work_id"] for w in p["next_trip"]}
    assert flagged_seen == {"K-1", "K-2", "K-3a"}


def test_no_plan_text_accuses_anyone(client):
    text = gen(client).text.lower()
    assert not [w for w in BANNED_WORDS if w in text]


def test_bad_ids_hours_and_districts_are_refused(client):
    assert client.get("/api/v1/plans/613_2026-13-01_8", headers=MINISTRY).status_code == 404
    assert client.get("/api/v1/plans/613_2026-10-11_30", headers=MINISTRY).status_code == 404
    assert client.get("/api/v1/plans/nonsense", headers=MINISTRY).status_code == 404
    assert gen(client, hours=1).status_code == 422
    r = client.post("/api/v1/plans/generate", json={"district": "999"}, headers=MINISTRY)
    assert r.status_code == 404


def test_a_district_officer_plans_only_their_own_district(client):
    own = {"X-Dev-Role": "DISTRICT", "X-Dev-District": KARUR}
    other = {"X-Dev-Role": "DISTRICT", "X-Dev-District": "640"}
    body = {"district": KARUR, "day": "2026-10-11"}
    assert client.post("/api/v1/plans/generate", json=body, headers=own).status_code == 200
    assert client.post("/api/v1/plans/generate", json=body, headers=other).status_code == 404


def test_a_district_with_nothing_in_the_queue_gives_an_empty_day(client):
    r = client.post("/api/v1/plans/generate", json={"district": "640", "day": "2026-10-11"},
                    headers=MINISTRY)
    assert r.status_code == 200
    p = r.json()
    assert p["stops"] == [] and p["totals"]["flagged_in_queue"] == 0
    assert p["totals"]["back_by"] is None


def test_the_district_list_holds_districts_with_queue_cases(client):
    r = client.get("/api/v1/plans/districts", headers=MINISTRY)
    assert r.status_code == 200
    assert r.json() == [{"district_lgd": KARUR, "name": "Karur", "state": "Tamil Nadu",
                         "cases": 3}]


def test_plan_ids_round_trip():
    from datetime import date

    pid = service.plan_id("613", date(2026, 10, 11), 8)
    assert service.parse_id(pid) == ("613", date(2026, 10, 11), 8)
    assert service.parse_id("613_2026-10-11_1") is None
