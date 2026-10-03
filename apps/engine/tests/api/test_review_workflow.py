"""The officer-facing review loop: alerts, the inspection planner, and field results.

Everything here is about what an officer *does* with a signal. Two rules run
through all of it: a step cannot be skipped, and a work's risk score is never
touched by any of these endpoints.
"""

from __future__ import annotations

import psycopg
import pytest
from psycopg.rows import dict_row

from drishti import audit
from drishti.batch import sync_alerts
from tests.api.conftest import DISTRICT_ANAND, MINISTRY

STATE_GUJARAT = {"X-Dev-Role": "STATE", "X-Dev-State": "24"}
DISTRICT_KHEDA = {"X-Dev-Role": "DISTRICT", "X-Dev-District": "640"}


@pytest.fixture()
def queued(api_db):
    """The same database, with one alert open per work in the review queue.

    This is exactly what data/batch_assess.py does after a real run, so the tests
    see the same rows the site does rather than a hand-made fixture.
    """
    opened, closed = sync_alerts(api_db)
    assert closed == 0
    return api_db, opened


# --- the audit trail (T060) -------------------------------------------------


def ack(client, work_id: str = "W-COSTLY", note: str | None = None):
    """One ordinary officer action on a known work, so there is something in the
    trail to test and the test can say which work it belongs to."""
    alert = next(a for a in client.get("/api/v1/alerts", headers=MINISTRY).json()["items"]
                 if a["work_id"] == work_id)
    client.patch(f"/api/v1/alerts/{alert['alert_id']}",
                 json={"state": "ACKNOWLEDGED", "actor": "officer@example.gov.in",
                       **({"note": note} if note else {})},
                 headers=MINISTRY)


def audit_rows(db):
    with psycopg.connect(db, row_factory=dict_row) as con:
        return con.execute("SELECT * FROM audit_log ORDER BY entry_id").fetchall()


def test_every_officer_action_is_audited(client, queued):
    """Nothing an officer does leaves a trace: not the alert, not the visit, not
    what the field officer saw."""
    db, _opened = queued
    alert = client.get("/api/v1/alerts", headers=MINISTRY).json()["items"][0]
    client.patch(f"/api/v1/alerts/{alert['alert_id']}",
                 json={"state": "ACKNOWLEDGED", "actor": "officer@example.gov.in"},
                 headers=MINISTRY)
    client.post("/api/v1/inspections", json={"work_id": "W-TYPICAL"}, headers=MINISTRY)
    iid = client.get("/api/v1/inspections", headers=MINISTRY).json()["items"][0]["inspection_id"]
    client.patch(f"/api/v1/inspections/{iid}",
                 json={"state": "ASSIGNED", "assigned_to": "field@example.gov.in",
                       "actor": "officer@example.gov.in"}, headers=MINISTRY)
    actions = {r["action"] for r in audit_rows(db)}
    assert {"ALERT_ACKNOWLEDGED", "INSPECTION_REQUESTED", "INSPECTION_ADVANCED"} <= actions
    for row in audit_rows(db):
        assert row["actor"] and row["role"] and row["entity"] and row["entity_id"]
        # the trail records what was done to a work record, never a name
        assert "MP" not in (row["note"] or "")
        assert row["work_id"], "an action on a work must say which work"


def test_the_audit_chain_verifies(client, queued):
    db, _opened = queued
    with psycopg.connect(db, row_factory=dict_row) as con:
        assert audit.verify_chain(con) == {"ok": True, "entries": len(audit_rows(db))}


def test_editing_a_past_entry_breaks_the_chain(client, queued):
    """The reason for the chain: a rewritten trail must be detectable.

    Someone with database access changes what an earlier row says. Without the
    hashes nothing downstream would notice.
    """
    db, _opened = queued
    ack(client)                                    # something must have happened
    with psycopg.connect(db, row_factory=dict_row) as con:
        before = audit.verify_chain(con)
        assert before["ok"] and before["entries"] >= 1
    with psycopg.connect(db) as con:          # the one way to rewrite history
        con.execute("UPDATE audit_log SET note = 'nothing to see here' WHERE entry_id = 1")
        con.commit()
    with psycopg.connect(db, row_factory=dict_row) as con:
        after = audit.verify_chain(con)
    assert not after["ok"]
    assert after["broken_at"] == 1
    assert "edited" in after["why"]


def test_removing_a_past_entry_breaks_the_chain(client, queued):
    db, _opened = queued
    ack(client)
    ack(client)
    assert len(audit_rows(db)) > 1
    with psycopg.connect(db) as con:
        con.execute("DELETE FROM audit_log WHERE entry_id = 1")
        con.commit()
    with psycopg.connect(db, row_factory=dict_row) as con:
        after = audit.verify_chain(con)
    assert not after["ok"]
    assert "changed or removed" in after["why"]


def test_the_work_page_lists_what_was_done_to_it(client, queued):
    db, _opened = queued
    with psycopg.connect(db, row_factory=dict_row) as con:
        assert audit.for_work(con, "W-COSTLY") == []
    ack(client, "W-COSTLY")
    with psycopg.connect(db, row_factory=dict_row) as con:
        history = audit.for_work(con, "W-COSTLY")
    assert [h["action"] for h in history] == ["ALERT_ACKNOWLEDGED"]
    assert history[0]["actor"] == "officer@example.gov.in"


def test_the_work_page_shows_the_trail_and_whether_it_still_verifies(client, queued):
    """An officer can read what was done, and the page also says out loud whether
    the trail still holds. A claim of accountability is worth nothing if it cannot
    be checked from the same screen."""
    ack(client, "W-COSTLY")
    review = client.get("/api/v1/works/W-COSTLY", headers=MINISTRY).json()["review"]
    assert review["chain"] == {"ok": True, "entries": 1}
    assert [h["action"] for h in review["history"]] == ["ALERT_ACKNOWLEDGED"]
    # and the standalone check an officer or an auditor can call at any time
    assert client.get("/api/v1/audit/verify", headers=MINISTRY).json()["ok"] is True


def test_an_audit_note_is_masked_like_every_other_free_text(client, queued):
    """A note is typed by hand and can name someone by accident."""
    ack(client, "W-COSTLY",
        note="the contractor can be reached on 9876543210, account 123456789012")
    review = client.get("/api/v1/works/W-COSTLY", headers=MINISTRY).json()["review"]
    note = review["history"][0]["note"]
    assert "9876543210" not in note and "123456789012" not in note, note
    assert "[phone]" in note and "[number]" in note


# --- alerts -----------------------------------------------------------------


def test_me_carries_the_snapshot_date(client):
    """Every screen shows the snapshot date beside its numbers, so /me carries it."""
    me = client.get("/api/v1/me", headers=MINISTRY).json()
    assert me["role"] == "MINISTRY"
    assert me["snapshot_date"] == "2026-05-26"


def test_state_role_sees_one_state_only(client):
    me = client.get("/api/v1/me", headers=STATE_GUJARAT).json()
    assert me["role"] == "STATE"
    districts = client.get("/api/v1/dashboard/districts", headers=STATE_GUJARAT).json()
    assert {d["state"] for d in districts} == {"Gujarat"}   # both fixture districts are
    assert {d["district_lgd"] for d in districts} == {"639", "640"}   # and both are in scope


def test_state_role_is_narrowed_by_the_state_header(client):
    """A state officer sees one state. Asking for another state yields nothing."""
    bodies = [client.get("/api/v1/dashboard/districts",
                         headers={"X-Dev-Role": "STATE", "X-Dev-State": "27"}).json()
              for _ in (0,)]
    assert bodies[0] == []


def test_district_role_cannot_see_another_district(client):
    districts = client.get("/api/v1/dashboard/districts", headers=DISTRICT_ANAND).json()
    assert [d["district_lgd"] for d in districts] == ["639"]


def test_alerts_open_only_for_queued_works(client, queued):
    body = client.get("/api/v1/alerts", headers=MINISTRY).json()
    assert body["total"] >= 1
    works = client.get("/api/v1/works", headers=MINISTRY).json()["items"]
    queue_bands = {"CRITICAL", "HIGH"}
    for alert in body["items"]:
        band = next(w["band"] for w in works if w["work_id"] == alert["work_id"])
        assert band in queue_bands
        assert alert["state"] == "NEW"


def test_alert_opens_once_per_work(client, queued):
    """Re-running the batch must not lengthen an officer's list."""
    before = client.get("/api/v1/alerts", headers=MINISTRY).json()["total"]
    opened, closed = sync_alerts(queued[0])
    assert (opened, closed) == (0, 0)
    assert client.get("/api/v1/alerts", headers=MINISTRY).json()["total"] == before


def test_alert_walks_new_acknowledged_investigating_resolved(client, queued):
    alert = client.get("/api/v1/alerts", headers=MINISTRY).json()["items"][0]
    steps = [("ACKNOWLEDGED", {"note": "seen"}), ("INVESTIGATING", {}),
             ("RESOLVED", {"note": "site visit done on 4 June"})]
    for state, body in steps:
        r = client.patch(f"/api/v1/alerts/{alert['alert_id']}",
                         json={"state": state, "actor": "officer@example.gov.in", **body},
                         headers=MINISTRY)
        assert r.status_code == 200, r.text
    assert client.get("/api/v1/alerts", headers=MINISTRY).json()["counts"]["RESOLVED"] >= 1


def test_alert_cannot_jump_past_investigating(client, queued):
    alert = client.get("/api/v1/alerts", headers=MINISTRY).json()["items"][0]
    r = client.patch(f"/api/v1/alerts/{alert['alert_id']}",
                     json={"state": "INVESTIGATING"}, headers=MINISTRY)
    assert r.status_code == 409
    client.patch(f"/api/v1/alerts/{alert['alert_id']}", json={"state": "ACKNOWLEDGED"},
                 headers=MINISTRY)
    assert client.patch(f"/api/v1/alerts/{alert['alert_id']}",
                        json={"state": "INVESTIGATING"}, headers=MINISTRY).status_code == 200


def test_closing_an_alert_without_looking_needs_a_reason(client, queued):
    """An officer may close an alert they decided needs no visit. They must say why."""
    alert = client.get("/api/v1/alerts", headers=MINISTRY).json()["items"][0]
    assert client.patch(f"/api/v1/alerts/{alert['alert_id']}", json={"state": "RESOLVED"},
                        headers=MINISTRY).status_code == 422
    assert client.patch(f"/api/v1/alerts/{alert['alert_id']}",
                        json={"state": "RESOLVED", "note": "site visit done on 4 June"},
                        headers=MINISTRY).status_code == 200


def test_a_closed_alert_stays_closed(client, queued, api_db):
    alert = client.get("/api/v1/alerts", headers=MINISTRY).json()["items"][0]
    client.patch(f"/api/v1/alerts/{alert['alert_id']}",
                 json={"state": "ACKNOWLEDGED", "note": "asked the block office"},
                 headers=MINISTRY)
    r = client.patch(f"/api/v1/alerts/{alert['alert_id']}",
                     json={"state": "RESOLVED", "note": "work was recorded already"},
                     headers=MINISTRY)
    assert r.status_code == 200
    assert client.patch(f"/api/v1/alerts/{alert['alert_id']}",
                        json={"state": "ACKNOWLEDGED"},
                        headers=MINISTRY).status_code == 409
    with psycopg.connect(api_db, row_factory=dict_row) as con:
        row = con.execute("SELECT state, note, closed_at FROM alerts WHERE alert_id = %s",
                          (alert["alert_id"],)).fetchone()
    assert row["state"] == "RESOLVED"
    assert row["note"] == "work was recorded already"   # the officer's own words are kept
    assert row["closed_at"] is not None


def test_a_district_officer_cannot_move_another_districts_alert(client, queued):
    alerts = client.get("/api/v1/alerts", headers=MINISTRY).json()["items"]
    mine = next(a for a in alerts if a["district_lgd"] == "639")
    theirs = next(a for a in alerts if a["district_lgd"] == "640")
    assert client.patch(f"/api/v1/alerts/{mine['alert_id']}",
                        json={"state": "ACKNOWLEDGED"},
                        headers=DISTRICT_KHEDA).status_code == 404
    assert client.patch(f"/api/v1/alerts/{theirs['alert_id']}",
                        json={"state": "ACKNOWLEDGED"},
                        headers=DISTRICT_ANAND).status_code == 404
    # ...and their own does move
    assert client.patch(f"/api/v1/alerts/{mine['alert_id']}",
                        json={"state": "ACKNOWLEDGED"},
                        headers=DISTRICT_ANAND).status_code == 200


def test_investigating_opens_the_inspection_that_answers_it(client, queued):
    """The planner and the alert list must never disagree."""
    alert = client.get("/api/v1/alerts", headers=MINISTRY).json()["items"][0]
    client.patch(f"/api/v1/alerts/{alert['alert_id']}",
                 json={"state": "ACKNOWLEDGED"}, headers=MINISTRY)
    client.patch(f"/api/v1/alerts/{alert['alert_id']}",
                 json={"state": "INVESTIGATING", "assigned_to": None}, headers=MINISTRY)
    inspections = client.get("/api/v1/inspections", headers=MINISTRY).json()
    opened = [i for i in inspections["items"] if i["work_id"] == alert["work_id"]]
    assert len(opened) == 1
    assert opened[0]["state"] == "INSPECTION_REQUIRED"


# --- inspections ------------------------------------------------------------


def test_asking_for_an_inspection_adds_it_to_the_planner(client):
    r = client.post("/api/v1/inspections",
                    json={"work_id": "W-TYPICAL", "note": "check the culvert",
                          "due_date": "2026-06-30"}, headers=MINISTRY)
    assert r.status_code == 200, r.text
    assert r.json()["state"] == "INSPECTION_REQUIRED"
    body = client.get("/api/v1/inspections", headers=MINISTRY).json()
    assert body["total"] == 1
    assert body["items"][0]["due_date"] == "2026-06-30"
    assert body["items"][0]["has_evidence"] is False


def test_asking_twice_updates_the_same_visit(client):
    client.post("/api/v1/inspections", json={"work_id": "W-TYPICAL"}, headers=MINISTRY)
    r = client.post("/api/v1/inspections",
                    json={"work_id": "W-TYPICAL", "due_date": "2026-07-15"}, headers=MINISTRY)
    assert r.status_code == 200
    body = client.get("/api/v1/inspections", headers=MINISTRY).json()
    assert body["total"] == 1
    assert body["items"][0]["due_date"] == "2026-07-15"


def test_asking_for_a_visit_the_officer_cannot_see_is_a_404(client):
    r = client.post("/api/v1/inspections",
                    json={"work_id": "W-OTHER-DISTRICT"}, headers=DISTRICT_ANAND)
    assert r.status_code == 404


def test_a_visit_walks_its_six_steps(client):
    client.post("/api/v1/inspections", json={"work_id": "W-TYPICAL"}, headers=MINISTRY)
    iid = client.get("/api/v1/inspections", headers=MINISTRY).json()["items"][0]["inspection_id"]
    # a result cannot be recorded while nobody has been assigned
    assert client.post(f"/api/v1/inspections/{iid}/result",
                       json={"outcome": "OBSERVED"}, headers=MINISTRY).status_code == 409
    assert client.patch(f"/api/v1/inspections/{iid}",
                        json={"state": "ASSIGNED", "assigned_to": "field@example.gov.in"},
                        headers=MINISTRY).status_code == 200
    assert client.patch(f"/api/v1/inspections/{iid}", json={"state": "FIELD_VERIFIED"},
                        headers=MINISTRY).status_code == 200
    r = client.post(f"/api/v1/inspections/{iid}/result",
                    json={"outcome": "OBSERVED", "observed": "culvert present",
                          "recorded_by": "field@example.gov.in"}, headers=MINISTRY)
    assert r.status_code == 200, r.text
    assert client.patch(f"/api/v1/inspections/{iid}", json={"state": "CLOSED"},
                        headers=MINISTRY).status_code == 200
    counts = client.get("/api/v1/inspections", headers=MINISTRY).json()["counts"]
    assert counts["CLOSED"] == 1


def test_the_work_page_shows_only_steps_that_really_happened(client, queued):
    """A timeline must never show a date we did not store.

    Asking for a visit records one moment; nothing else gets a timestamp, so the
    work's page cannot imply that anyone was assigned or that anyone went out.
    """
    client.post("/api/v1/inspections", json={"work_id": "W-COSTLY"}, headers=MINISTRY)
    review = client.get("/api/v1/works/W-COSTLY", headers=MINISTRY).json()["review"]
    asked = [e["step"] for e in review["timeline"]]
    assert "INSPECTION_REQUIRED" in asked
    for step in ("ASSIGNED", "FIELD_VERIFIED", "RESULT_RECORDED", "CLOSED"):
        assert step not in asked, f"{step} has not happened, so it must not appear"
    assert all(e["at"] for e in review["timeline"]), "every entry needs a stored date"
    # the timeline reads in order, so "seen on the ground" cannot come before the asking
    dates = [e["at"] for e in review["timeline"]]
    assert dates == sorted(dates)
    assert review["inspection"]["requested_by"] is not None
    assert review["inspection"]["assigned_to"] is None


def test_the_work_page_carries_the_alert_and_the_visit_together(client, queued):
    """One work, one story: the page must not show an alert with no visit behind it."""
    client.post("/api/v1/inspections", json={"work_id": "W-COSTLY"}, headers=MINISTRY)
    review = client.get("/api/v1/works/W-COSTLY", headers=MINISTRY).json()["review"]
    assert review["alert"] is not None
    assert review["inspection"]["alert_id"] == review["alert"]["alert_id"]


def test_a_closed_visit_keeps_the_date_it_was_closed(client):
    client.post("/api/v1/inspections", json={"work_id": "W-TYPICAL"}, headers=MINISTRY)
    iid = client.get("/api/v1/inspections", headers=MINISTRY).json()["items"][0]["inspection_id"]
    client.patch(f"/api/v1/inspections/{iid}",
                 json={"state": "ASSIGNED", "assigned_to": "field@example.gov.in"},
                 headers=MINISTRY)
    client.patch(f"/api/v1/inspections/{iid}", json={"state": "FIELD_VERIFIED"}, headers=MINISTRY)
    client.post(f"/api/v1/inspections/{iid}/result", json={"outcome": "OBSERVED"},
                headers=MINISTRY)
    client.patch(f"/api/v1/inspections/{iid}", json={"state": "CLOSED"}, headers=MINISTRY)
    review = client.get("/api/v1/works/W-TYPICAL", headers=MINISTRY).json()["review"]
    seen = [e["step"] for e in review["timeline"]]
    assert seen[-1] == "CLOSED"
    assert review["inspection"]["closed_at"] is not None
    assert review["inspection"]["result"]["outcome"] == "OBSERVED"
    # every step kept a note of who did it, and nothing was back-dated to one moment
    stamps = [review["inspection"][c] for c in
              ("requested_at", "assigned_at", "verified_at", "recorded_at", "closed_at")]
    assert all(stamps)
    assert stamps == sorted(stamps)


def test_a_visit_cannot_skip_a_step(client):
    client.post("/api/v1/inspections", json={"work_id": "W-TYPICAL"}, headers=MINISTRY)
    iid = client.get("/api/v1/inspections", headers=MINISTRY).json()["items"][0]["inspection_id"]
    r = client.patch(f"/api/v1/inspections/{iid}", json={"state": "CLOSED"}, headers=MINISTRY)
    assert r.status_code == 409


def test_unable_to_verify_is_a_real_answer(client):
    """It records nothing either way, exactly like NOT_ASSESSABLE in an engine."""
    client.post("/api/v1/inspections", json={"work_id": "W-TYPICAL"}, headers=MINISTRY)
    iid = client.get("/api/v1/inspections", headers=MINISTRY).json()["items"][0]["inspection_id"]
    client.patch(f"/api/v1/inspections/{iid}", json={"state": "ASSIGNED",
                                                     "assigned_to": "field@example.gov.in"},
                 headers=MINISTRY)
    client.patch(f"/api/v1/inspections/{iid}", json={"state": "FIELD_VERIFIED"},
                 headers=MINISTRY)
    r = client.post(f"/api/v1/inspections/{iid}/result",
                    json={"outcome": "UNABLE_TO_VERIFY", "observed": "road under water"},
                    headers=MINISTRY)
    assert r.status_code == 200
    body = client.get("/api/v1/inspections", headers=MINISTRY).json()
    assert body["items"][0]["state"] == "RESULT_RECORDED"
    assert body["items"][0]["results"] == 1


def test_no_result_touches_the_risk_score(client, api_db):
    """The workflow records what an officer did. It never re-scores a work."""
    before = psycopg.connect(api_db).execute(
        "SELECT band, score, priority FROM assessments WHERE work_id = 'W-TYPICAL'"
    ).fetchone()
    client.post("/api/v1/inspections", json={"work_id": "W-TYPICAL"}, headers=MINISTRY)
    client.patch("/api/v1/inspections", json={"work_id": "W-TYPICAL"}, headers=MINISTRY)
    after = psycopg.connect(api_db).execute(
        "SELECT band, score, priority FROM assessments WHERE work_id = 'W-TYPICAL'"
    ).fetchone()
    assert before == after


# --- coverage, search, related works ----------------------------------------


def test_assessment_reports_what_no_check_could_read(client):
    """'Couldn't check' is a status, not a low score, so it gets its own numbers."""
    body = client.get("/api/v1/dashboard/assessment", headers=MINISTRY).json()
    assert body["works"] == 4
    assert body["assessed"] == 4
    assert body["with_evidence"] == 0
    assert body["without_evidence"] == 4
    assert body["snapshot_date"] == "2026-05-26"
    assert set(body["bands"]) <= {"CRITICAL", "HIGH", "MEDIUM", "LOW"}


def test_assessment_is_scoped_like_everything_else(client):
    all_ = client.get("/api/v1/dashboard/assessment", headers=MINISTRY).json()["works"]
    one = client.get("/api/v1/dashboard/assessment", headers=DISTRICT_ANAND).json()["works"]
    assert one < all_


def test_search_is_grouped_and_scoped(client):
    body = client.get("/api/v1/search", params={"q": "CC road"}, headers=DISTRICT_ANAND).json()
    assert set(body) == {"q", "works", "districts", "offices", "checks"}
    assert {w["district_name"] for w in body["works"]["items"]} == {"Anand"}
    places = client.get("/api/v1/search", params={"q": "Anand"},
                        headers=DISTRICT_ANAND).json()["districts"]
    assert [d["name"] for d in places] == ["Anand"]
    assert client.get("/api/v1/search", params={"q": "Kheda"},
                      headers=DISTRICT_ANAND).json()["districts"] == []
    # the same query as MINISTRY also finds Kheda, so the scoping is doing the work
    wide = client.get("/api/v1/search", params={"q": "CC road"}, headers=MINISTRY).json()
    assert "Kheda" in {w["district_name"] for w in wide["works"]["items"]}


def test_search_finds_a_work_by_its_id(client):
    body = client.get("/api/v1/search", params={"q": "W-COSTLY"}, headers=MINISTRY).json()
    assert body["works"]["items"][0]["work_id"] == "W-COSTLY"


def test_search_finds_a_check_by_the_question_it_asks(client):
    body = client.get("/api/v1/search", params={"q": "unusual for similar"},
                      headers=MINISTRY).json()
    assert [c["id"] for c in body["checks"]] == ["statistical"]
    assert body["checks"][0]["question"].startswith("Is the project cost")


def test_search_finds_a_check_by_its_name(client):
    body = client.get("/api/v1/search", params={"q": "Photo"}, headers=MINISTRY).json()
    assert [c["id"] for c in body["checks"]] == ["photo_evidence"]


def test_a_check_result_links_to_works_the_way_the_works_list_filters(client, queued):
    """A check name is not a filter. The codes it raises are, so the link must carry one.

    The site's works list filters on a finding code; a search result that linked with
    the check's own id would come back empty every time, with no clue why.
    """
    seen: set[str] = set()
    checks: dict[str, list[str]] = {}
    for word in ("does", "is", "photo", "cost", "wait", "alike"):
        for check in client.get("/api/v1/search", params={"q": word},
                                headers=MINISTRY).json()["checks"]:
            checks.setdefault(check["id"], check["codes"])
    for codes in checks.values():
        for code in codes:
            seen.add(code)
            listed = client.get("/api/v1/works", params={"finding": code},
                                headers=MINISTRY).json()
            assert listed["total"] > 0, f"nothing carries {code}, so the link would be empty"
            # the filter has to be honoured, not quietly dropped on the way through
            assert listed["filters"]["finding"] == code
    assert seen, "no check reported a finding code, so no check could be linked"


def test_search_masks_names_like_every_other_screen(client):
    body = client.get("/api/v1/search", params={"q": "CC road"}, headers=MINISTRY).json()
    for w in body["works"]["items"]:
        assert "<" not in (w["description"] or "")


def test_case_endpoint_lists_the_works_of_one_case(client, api_db):
    """A purchase filed as many works is one question; the page links them all."""
    with psycopg.connect(api_db) as con:
        con.execute("UPDATE assessments SET case_id = 'C-1', case_size = 2 "
                    "WHERE work_id = 'W-TYPICAL'")
        con.execute("UPDATE assessments SET case_id = 'C-1', case_size = 2 "
                    "WHERE work_id = 'W-NO-TYPE'")
        con.commit()
    body = client.get("/api/v1/works/W-TYPICAL/case", headers=MINISTRY).json()
    assert body["case_id"] == "C-1"
    assert {w["work_id"] for w in body["items"]} == {"W-TYPICAL", "W-NO-TYPE"}


def test_case_rows_carry_what_the_table_renders(client, api_db):
    """A case row is shown in the same table as the queue, so it must carry the
    same fields. Missing ones once left the table rendering blanks."""
    with psycopg.connect(api_db) as con:
        con.execute("UPDATE assessments SET case_id = 'C-2', case_size = 2 "
                    "WHERE work_id = 'W-TYPICAL'")
        con.execute("UPDATE assessments SET case_id = 'C-2', case_size = 2 "
                    "WHERE work_id = 'W-NO-TYPE'")
        con.commit()
    row = client.get("/api/v1/works/W-TYPICAL/case", headers=MINISTRY).json()["items"][0]
    for field in ("work_id", "source", "district_lgd", "district_name", "state_name",
                  "work_type_code", "description", "amount", "status", "recommended_date",
                  "band", "score", "priority", "limited", "alerts", "headline"):
        assert field in row, f"the work page's table needs {field}"


def test_case_endpoint_of_a_lone_work_is_empty(client):
    body = client.get("/api/v1/works/W-COSTLY/case", headers=MINISTRY).json()
    assert body["case_id"] is None
    assert body["size"] == 1
    assert body["items"] == []


def test_works_can_be_filtered_by_what_a_check_could_not_read(client):
    """The two filters that say "no check could look at this" without scoring it."""
    body = client.get("/api/v1/works", params={"assess": "not_assessable"},
                      headers=MINISTRY).json()
    assert body["filters"]["assess"] == "not_assessable"
    for w in body["items"]:
        assert w["limited"] is True
    assessable = client.get("/api/v1/works", params={"assess": "assessable"},
                            headers=MINISTRY).json()
    assert all(w["limited"] is not True for w in assessable["items"])
    assert assessable["total"] + body["total"] == 4


def test_works_can_be_filtered_by_evidence(client, api_db):
    with psycopg.connect(api_db) as con:
        con.execute("INSERT INTO evidence_facts VALUES ('W-TYPICAL', '{\"files\": []}', 'v1')")
        con.commit()
    body = client.get("/api/v1/works", params={"evidence": "with"}, headers=MINISTRY).json()
    assert [w["work_id"] for w in body["items"]] == ["W-TYPICAL"]
    assert client.get("/api/v1/works", params={"evidence": "without"},
                      headers=MINISTRY).json()["total"] == 3