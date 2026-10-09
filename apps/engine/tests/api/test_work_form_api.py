"""POST /api/v1/work-form/check: the website's work intelligence form through the four agents
(T134). Nothing is stored."""

from __future__ import annotations

import json
from pathlib import Path

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
    declared = dict(work_nature="Continuation / next phase", prior_work_id="W-TYPICAL",
                    known_nearby_work_ids="W-TYPICAL",
                    nearby_work_relationship="Same asset, separate phase")
    # the next phase, from where that road ends: a note, never a question
    beyond = {"start_lat": str(PIN[0] + 300 * METRE), "start_lon": str(PIN[1]),
              "end_lat": str(PIN[0] + 600 * METRE), "end_lon": str(PIN[1]),
              "latitude": str(PIN[0] + 300 * METRE), "longitude": str(PIN[1])}
    body = _check(client, **beyond, **declared).json()
    dup = next(c for c in body["trace"]["checks"] if c["id"] == "dup_split")
    assert not [f for f in dup["findings"] if f["risk"] > 0]
    # a "continuation" on that road's own ground, not finished yet, is asked (T135)
    body = _check(client, **near, **declared).json()
    dup = next(c for c in body["trace"]["checks"] if c["id"] == "dup_split")
    asked = [f for f in dup["findings"] if f["risk"] > 0]
    assert [f["code"] for f in asked] == ["SANCTIONED_WORK_AT_THIS_SITE"]
    assert "own ground" in asked[0]["text"]


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


def test_the_demo_is_judged_on_the_day_its_examples_were_written_for(client, monkeypatch):
    # T164: the hosted snapshot is 26 May 2026; the examples are written for 2 Oct 2026. Judged
    # on the snapshot's day, an example's later dates read as "in the future" (a false finding)
    # and its site videos and overdue dates as not happened yet
    from drishti import config, demo
    monkeypatch.setattr(demo, "_text", lambda: json.dumps({
        "as_of": "2026-10-02", "records": [],
        "later": {"WF-1": {"status": "COMPLETED", "completed_date": "2026-07-04"}}}))
    body = client.post("/api/v1/work-form/check?demo=true", json=road(**ANAND)).json()
    assert body["trace"]["as_of"] == "2026-10-02"
    time_rules = next(c for c in body["trace"]["checks"] if c["id"] == "time_rules")
    codes = [f["code"] for f in time_rules["findings"]]
    assert "FINISHED_TOO_FAST" in codes and "IMPOSSIBLE_TIMELINE" not in codes
    # without the demo, the snapshot's day as before
    plain = client.post("/api/v1/work-form/check", json=road(**ANAND)).json()
    assert plain["trace"]["as_of"] == config.snapshot_date().isoformat()
    # an example file older than the snapshot never moves the day back
    monkeypatch.setattr(demo, "_text", lambda: json.dumps({"as_of": "2020-01-01"}))
    body = client.post("/api/v1/work-form/check?demo=true", json=road(**ANAND)).json()
    assert body["trace"]["as_of"] == config.snapshot_date().isoformat()


EXAMPLES = Path(__file__).resolve().parents[4] / "apps" / "web" / "public" / "work-form" / \
    "examples.json"


def _asked(trace: dict) -> dict:
    return {c["id"]: sorted(f["code"] for f in c["findings"] if f["risk"] > 0)
            for c in trace["checks"]}


def test_every_example_filing_raises_on_the_live_route_what_its_page_shows(client, api_db):
    # T164: the page shows each example's stored verdict, and its "Check this form" button sends
    # the form to this route. They must agree (live, the time and site examples raised nothing).
    # The examples' own district, without its real works: the demo places its records there,
    # and the state's price reference (reference/cost/uttar_pradesh.json) prices the lights
    with psycopg.connect(api_db) as con:
        con.execute("INSERT INTO districts VALUES ('194','Jaunpur','09','Uttar Pradesh')")
        con.commit()
    examples = json.loads(EXAMPLES.read_text(encoding="utf-8"))["examples"]
    assert len(examples) >= 13
    for ex in examples:
        body = client.post("/api/v1/work-form/check?demo=true", json=ex["form"]).json()
        assert _asked(body["trace"]) == _asked(ex["trace"]), ex["id"]
        assert body["trace"]["result"]["band"] == ex["trace"]["result"]["band"], ex["id"]


def test_the_demo_never_gives_another_work_an_examples_record(client, monkeypatch):
    _demo_file(monkeypatch, [], {"WF-OTHER": {"status": "COMPLETED",
                                              "completed_date": "2026-07-04"}})
    body = client.post("/api/v1/work-form/check?demo=true", json=road(**ANAND)).json()
    time_rules = next(c for c in body["trace"]["checks"] if c["id"] == "time_rules")
    assert time_rules["picture"]["completed"] is None


def _kheda_forms(api_db, n=8, agencies=4):
    """n submitted road forms in Kheda (Anand's state), from `agencies` agencies, filed April."""
    from drishti.cost_form import pswif
    with psycopg.connect(api_db) as con:
        for i in range(n):
            wid = f"W-KHEDA-{i}"
            con.execute("INSERT INTO works (work_id, source, state_lgd, state_name, district_lgd, "
                        "district_name, work_type_code, description, amount, status, "
                        "recommended_date) VALUES (%s,'REAL','24','Gujarat','640','Kheda',"
                        "'ROAD_CC',%s,868000,'SANCTIONED','2026-04-01')",
                        (wid, f"CC road number {i} in Kheda"))
            form = pswif.to_cost_form(road(recommendation_ref=wid, district="Kheda",
                                           ida_received_date="2026-04-15"), None)
            con.execute("INSERT INTO cost_forms (work_id, status, form, ready, saved_by, "
                        "submitted_at) VALUES (%s,'submitted',%s,true,%s,'2026-04-15')",
                        (wid, Jsonb(form), f"kheda-agency-{i % agencies}"))
        con.commit()


def test_a_district_without_forms_is_priced_from_its_states_forms(client, api_db):
    # T135: the live check loads the state's other submitted forms, so a district with none of
    # its own still has fair rates (10% more lenient), and says where they came from
    before = client.get("/api/v1/cost/data-gaps?district=639").json()
    cement = next(m for m in before["materials"] if m["material"] == "cement")
    assert cement["source"] is None and cement["gap"]["reason"] == "none"
    _kheda_forms(api_db)
    after = client.get("/api/v1/cost/data-gaps?district=639").json()
    cement = next(m for m in after["materials"] if m["material"] == "cement")
    assert cement["source"] == "state" and "across the state" in cement["where"]
    assert cement["gap"]["reason"] == "none"            # the district itself still has none
    body = _check(client, ida_received_date="2026-05-20").json()
    cost = next(c for c in body["trace"]["checks"] if c["id"] == "cost_estimate")
    assert cost["status"] == "ASSESSED"
    assert not [f for f in cost["findings"] if f["risk"] > 0]      # the same honest rates
    assert "across the state" in cost["headline"]


def test_the_data_gaps_keep_to_the_users_area(client):
    assert client.get("/api/v1/cost/data-gaps?district=640",
                      headers=DISTRICT_ANAND).status_code == 404
    assert client.get("/api/v1/cost/data-gaps?district=999").status_code == 404
    body = client.get("/api/v1/cost/data-gaps?district=639", headers=DISTRICT_ANAND).json()
    assert body["gaps"] == len(body["materials"]) and body["priced"] == 0
