"""POST /api/v1/work-form/check: the website's work intelligence form through the four agents
(T134). Nothing is stored."""

from __future__ import annotations

import json

import psycopg
from psycopg.types.json import Jsonb

from tests.api.conftest import DISTRICT_ANAND, MINISTRY
from tests.cost_form.test_pswif import road

ANAND = {"district": "Anand", "state": "Gujarat"}
PIN = (22.5600, 72.9500)
METRE = 1 / 111_195


def _check(client, headers=None, **over):
    return client.post("/api/v1/work-form/check", json=road(**{**ANAND, **over}),
                       headers=headers or {})


def test_anyone_can_check_a_filled_form_and_nothing_is_stored(client, api_db):
    with psycopg.connect(api_db) as con:
        before = con.execute("SELECT count(*) FROM works").fetchone()[0]
    r = _check(client)                       # the public view: no sign-in
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["district"]["district_lgd"] == "639"
    assert body["form"]["ready"] is True and body["form"]["work_type"] == "ROAD_CC"
    assert body["form"]["grand_total"] == 868000
    checks = {c["id"]: c for c in body["trace"]["checks"]}
    assert list(checks) == ["cost_estimate", "dup_split", "time_rules", "site_progress"]
    assert checks["site_progress"]["status"] == "NOT_APPLICABLE"     # no site video yet
    with psycopg.connect(api_db) as con:
        assert con.execute("SELECT count(*) FROM works").fetchone()[0] == before


def test_what_the_form_lacks_for_the_agents_is_listed(client):
    body = _check(client, road_length_m="").json()
    assert body["form"]["ready"] is False
    assert any(i["field"] == "sites[0].size.length_m" for i in body["form"]["issues"])
    cost = next(c for c in body["trace"]["checks"] if c["id"] == "cost_estimate")
    assert cost["status"] == "NOT_ASSESSABLE"


def test_a_pin_at_a_sanctioned_road_is_asked_about(client, api_db):
    # W-TYPICAL (a sanctioned CC road in Anand) has its own submitted form, pinned here
    earlier = {"work": {"work_type": "ROAD_CC", "nature": "new"},
               "sites": [{"location": {"lat": PIN[0], "lon": PIN[1],
                                       "end_lat": PIN[0] + 300 * METRE, "end_lon": PIN[1]}}]}
    with psycopg.connect(api_db) as con:
        con.execute("INSERT INTO cost_forms (work_id, status, form, ready, submitted_at) "
                    "VALUES ('W-TYPICAL','submitted',%s,true,now())", (Jsonb(earlier),))
        con.commit()
    near = {"start_lat": str(PIN[0] + 20 * METRE), "start_lon": str(PIN[1]),
            "end_lat": str(PIN[0] + 320 * METRE), "end_lon": str(PIN[1]),
            "latitude": str(PIN[0] + 20 * METRE), "longitude": str(PIN[1])}
    body = _check(client, **near).json()
    dup = next(c for c in body["trace"]["checks"] if c["id"] == "dup_split")
    assert [f["code"] for f in dup["findings"]] == ["SANCTIONED_WORK_AT_THIS_SITE"]
    # the agency declares it continues that road: a note, never a question
    body = _check(client, **near, work_nature="Continuation / next phase",
                  prior_work_id="W-TYPICAL", known_nearby_work_ids="W-TYPICAL",
                  nearby_work_relationship="Same asset, separate phase").json()
    dup = next(c for c in body["trace"]["checks"] if c["id"] == "dup_split")
    assert not [f for f in dup["findings"] if f["risk"] > 0]


def test_bad_requests_are_refused_plainly(client):
    assert _check(client, district="").status_code == 422
    assert _check(client, district="Atlantis").status_code == 404
    other = {"X-Dev-Role": "DISTRICT", "X-Dev-District": "640"}
    assert _check(client, headers=other).status_code == 404
    assert _check(client, headers=DISTRICT_ANAND).status_code == 200
    assert _check(client, headers=MINISTRY).status_code == 200
    huge = client.post("/api/v1/work-form/check", json={**road(**ANAND), "x": "a" * 500_000})
    assert huge.status_code == 413


def _demo_file(monkeypatch, records, later):
    from drishti import demo
    monkeypatch.setattr(demo, "_text", lambda: json.dumps({"records": records, "later": later}))


def test_the_demo_compares_with_its_example_data_and_only_when_asked(client, monkeypatch):
    # an example road already sanctioned and completed, pinned where this form's road starts
    old = {"work_id": "WF-OLD", "source": "SCENARIO", "work_type_code": "ROAD_CC",
           "description": "CC road in village Sonbarsa", "amount": 1452000.0,
           "status": "COMPLETED", "recommended_date": "2025-01-10",
           "sanction_date": "2025-02-01", "completed_date": "2025-11-06",
           "cost_form": {"work": {"work_type": "ROAD_CC", "nature": "new"},
                         "sites": [{"location": {"lat": 25.7463, "lon": 82.6837,
                                                 "end_lat": 25.7463 + 300 * METRE,
                                                 "end_lon": 82.6837}}]}}
    _demo_file(monkeypatch, [old], {"WF-1": {"status": "COMPLETED",
                                             "completed_date": "2026-07-04"}})
    at_pin = {"district": "Anand", "state": "Gujarat", "start_lat": "25.7463",
               "start_lon": "82.6837", "end_lat": str(25.7463 + 300 * METRE),
               "end_lon": "82.6837"}
    plain = client.post("/api/v1/work-form/check", json=road(**at_pin)).json()
    assert plain["demo"] is False
    dup = next(c for c in plain["trace"]["checks"] if c["id"] == "dup_split")
    assert not [f for f in dup["findings"] if f["risk"] > 0]

    body = client.post("/api/v1/work-form/check?demo=true", json=road(**at_pin)).json()
    assert body["demo"] is True
    checks = {c["id"]: c for c in body["trace"]["checks"]}
    asked = [f for f in checks["dup_split"]["findings"] if f["risk"] > 0]
    assert [f["code"] for f in asked] == ["SANCTIONED_WORK_AT_THIS_SITE"]
    # the short facts a page shows beside the sentence
    assert asked[0]["facts"]["other"] == "WF-OLD" and asked[0]["facts"]["metres"] < 50
    # the example filing gets what its record shows after sanction: complete 3 days after it
    time_rules = checks["time_rules"]
    assert time_rules["picture"]["completed"] == "2026-07-04"
    assert "FINISHED_TOO_FAST" in [f["code"] for f in time_rules["findings"]]


def test_the_demo_never_gives_another_work_an_examples_record(client, monkeypatch):
    _demo_file(monkeypatch, [], {"WF-OTHER": {"status": "COMPLETED",
                                              "completed_date": "2026-07-04"}})
    body = client.post("/api/v1/work-form/check?demo=true", json=road(**ANAND)).json()
    time_rules = next(c for c in body["trace"]["checks"] if c["id"] == "time_rules")
    assert time_rules["picture"]["completed"] is None
