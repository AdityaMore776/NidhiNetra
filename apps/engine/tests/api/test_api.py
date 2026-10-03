import pytest

from tests.api.conftest import DISTRICT_ANAND, MINISTRY


def test_health_needs_no_sign_in(client):
    assert client.get("/api/v1/health").json()["ok"] is True


@pytest.mark.parametrize("path", ["/api/v1/me", "/api/v1/dashboard/summary",
                                  "/api/v1/dashboard/districts", "/api/v1/works",
                                  "/api/v1/works/W-COSTLY", "/api/v1/queue"])
def test_everything_else_needs_sign_in(client, path):
    assert client.get(path).status_code == 401


def test_dev_sign_in_is_refused_on_vercel(client, monkeypatch):
    monkeypatch.setenv("VERCEL", "1")
    assert client.get("/api/v1/me", headers=MINISTRY).status_code == 401


def test_me(client):
    assert client.get("/api/v1/me", headers=MINISTRY).json()["role"] == "MINISTRY"


def test_summary_counts_real_works_and_money(client):
    s = client.get("/api/v1/dashboard/summary", headers=MINISTRY).json()
    assert s["works"] == 4
    assert s["amount"] == pytest.approx(160_000 + 1_000_000 + 2_500_000 + 300_000)
    assert sum(s["bands"].values()) == 4
    agents = {a["id"]: a for a in s["agents"]}
    assert agents["cost_estimate"]["built"] is True
    assert "outlier" not in agents                 # replaced by Compliance R12/R13 (T053)
    assert "statistical" not in agents             # the old Cost Anomaly is retired (T099)
    assert list(agents)[:4] == ["compliance", "cost_estimate", "dup_split", "delay"]


def test_district_officer_sees_only_their_district(client):
    s = client.get("/api/v1/dashboard/summary", headers=DISTRICT_ANAND).json()
    assert s["works"] == 3
    ids = {w["work_id"] for w in client.get("/api/v1/works", headers=DISTRICT_ANAND)
           .json()["items"]}
    assert "W-OTHER-DISTRICT" not in ids
    assert client.get("/api/v1/works/W-OTHER-DISTRICT",
                      headers=DISTRICT_ANAND).status_code == 404


def test_districts_aggregate(client):
    rows = {r["district_lgd"]: r for r in
            client.get("/api/v1/dashboard/districts", headers=MINISTRY).json()}
    assert rows["639"]["works"] == 3 and rows["640"]["works"] == 1


def test_works_search_and_filters(client):
    r = client.get("/api/v1/works", params={"q": "vasad"}, headers=MINISTRY).json()
    assert [w["work_id"] for w in r["items"]] == ["W-COSTLY"]
    r = client.get("/api/v1/works", params={"type": "ROAD_CC", "district": "639"},
                   headers=MINISTRY).json()
    assert {w["work_id"] for w in r["items"]} == {"W-TYPICAL", "W-COSTLY"}
    assert r["total"] == 2


def test_work_detail_carries_every_engine_and_the_parts(client):
    w = client.get("/api/v1/works/W-COSTLY", headers=MINISTRY).json()
    assert w["work"]["district_name"] == "Anand"
    a = w["assessment"]
    assert [r["agent"] for r in a["agents"]][:4] == ["compliance", "cost_estimate", "dup_split",
                                                   "delay"]
    cost = next(r for r in a["agents"] if r["agent"] == "cost_estimate")
    assert cost["name"] == "Cost" and cost["question"]
    # T099: no cost estimate form, so the amount alone is never judged
    assert cost["status"] == "NOT_APPLICABLE" and cost["risk"] == 0
    dup = next(r for r in a["agents"] if r["agent"] == "dup_split")
    assert dup["name"] == "Duplicate Work" and dup["status"] == "ASSESSED"
    assert sum(p["contribution"] for p in a["parts"]["parts"]) == pytest.approx(a["score"])


def test_unknown_work_is_404(client):
    assert client.get("/api/v1/works/NOPE", headers=MINISTRY).status_code == 404


def test_queue_holds_only_works_needing_review_in_priority_order(client):
    items = client.get("/api/v1/queue", headers=MINISTRY).json()["items"]
    assert items and all(i["band"] in ("CRITICAL", "HIGH") for i in items)
    assert [i["priority"] for i in items] == sorted((i["priority"] for i in items),
                                                    reverse=True)
    ids = {i["work_id"] for i in items}
    assert "W-TYPICAL" not in ids
    # a wait for sanction alone never reaches the queue (W-COSTLY: its price is no longer
    # judged from the amount alone, T099); a big sum that says nothing does (R12)
    assert "W-COSTLY" not in ids
    vague = next(i for i in items if i["work_id"] == "W-OTHER-DISTRICT")
    assert "Rs 25.00 lakh" in vague["headline"] and "sanction" not in vague["headline"]


def test_keepalive_touches_the_database(client):
    r = client.get("/api/v1/health/keepalive").json()
    assert r["ok"] is True and r["works"] == 4


def test_quiet_works_are_stored_compact_and_rebuilt_when_opened(client, api_db):
    import psycopg

    with psycopg.connect(api_db) as con:
        compact, agents = con.execute(
            "SELECT compact, agents FROM assessments WHERE work_id = 'W-TYPICAL'").fetchone()
        flagged = con.execute(
            "SELECT compact FROM assessments WHERE work_id = 'W-OTHER-DISTRICT'").fetchone()[0]
    assert compact is True and agents == []
    assert flagged is False
    w = client.get("/api/v1/works/W-TYPICAL", headers=MINISTRY).json()["assessment"]
    dup = next(r for r in w["agents"] if r["agent"] == "dup_split")
    assert dup["verdict"] == "NOT_SANCTIONED_BEFORE"


def test_stored_legacy_agent_ids_are_read_as_engine_ids():
    from drishti.api.routes import _described

    out = _described([{"agent": "duplicate_project", "status": "NOT_BUILT"},
                      {"agent": "statistical", "status": "ASSESSED"}])
    assert [r["agent"] for r in out] == ["dup_split", "statistical"]
    assert out[0]["name"] == "Duplicate Work"
    # a result stored before the old Cost Anomaly was retired still reads by name (T099)
    assert out[1]["name"] == "Cost Anomaly (retired)" and out[1]["question"]


def test_offices_with_unreliable_completion_dates(client, api_db):
    import psycopg

    with psycopg.connect(api_db) as con:
        con.execute("UPDATE works SET agency_name = 'Anand(DISTRICT COLLECTOR)' "
                    "WHERE district_lgd = '639'")
        con.execute("INSERT INTO timeline_quarters VALUES ('2024-Q3', 3719, 18)")
        con.execute("INSERT INTO timeline_agencies VALUES ('Anand(DISTRICT COLLECTOR)', 200, 40), "
                    "('Kheda(DISTRICT COLLECTOR)', 300, 1)")
        con.commit()
    from drishti.api import routes
    routes._stats.cache_clear()
    rows = client.get("/api/v1/dashboard/offices", headers=MINISTRY).json()
    assert [r["agency_name"] for r in rows] == ["Anand(DISTRICT COLLECTOR)"]
    assert rows[0]["district_name"] == "Anand" and rows[0]["bad"] == 40


def test_one_purchase_filed_as_several_works_is_one_case_in_the_queue(api_db, client):
    # three identical big sums that name no place, filed the same day: R12 queues each one,
    # and Duplicate Work files them as one case (display only, T100): one row of three
    from datetime import date

    import psycopg

    from drishti import batch
    from drishti.agents.statistical.cohort import StatsStore
    from drishti.pipeline.orchestrator import Context

    with psycopg.connect(api_db) as con:
        for i in range(3):
            con.execute(
                "INSERT INTO works (work_id, source, state_lgd, state_name, district_lgd, "
                "district_name, work_type_code, description, amount, status, "
                "recommended_date) VALUES (%s,'REAL','24','Gujarat','639','Anand','ROAD_CC',"
                "'Construction of PCC Road',1400000,'SANCTIONED',%s)",
                (f"W-PIECE-{i}", date(2026, 1, 5)))
        con.commit()
    batch.assess_all(api_db, Context(stats=StatsStore.load(api_db), as_of=date(2026, 5, 26)))
    body = client.get("/api/v1/queue", headers=MINISTRY).json()
    pieces = [i for i in body["items"] if i["work_id"].startswith("W-PIECE-")]
    assert len(pieces) == 1 and pieces[0]["case_size"] == 3 and pieces[0]["case_id"]
    assert body["total"] == len(body["items"])
    everything = client.get("/api/v1/works", headers=MINISTRY).json()["items"]
    assert sum(i["work_id"].startswith("W-PIECE-") for i in everything) == 3


def test_office_habits_are_listed_once_and_scoped(client):
    r = client.get("/api/v1/dashboard/office-habits", headers=MINISTRY)
    assert r.status_code == 200 and isinstance(r.json(), list)
    r = client.get("/api/v1/dashboard/office-habits", headers=DISTRICT_ANAND)
    assert r.status_code == 200
    assert all(o["district_lgd"] == "639" for o in r.json())
