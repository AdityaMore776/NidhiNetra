"""T060: alerts, their lifecycle and the hash-chained audit log (migration 015, drishti/alerts.py).

The fixture database has one queue case in Kheda (W-OTHER-DISTRICT, recorded complete two days
after its sanction); these tests raise W-COSTLY in Anand to HIGH so each district has one.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import psycopg
import pytest

from drishti import alerts
from tests.api.conftest import DISTRICT_ANAND, MINISTRY

FIELD_ANAND = {"X-Dev-Role": "FIELD", "X-Dev-District": "639"}
DISTRICT_KHEDA = {"X-Dev-Role": "DISTRICT", "X-Dev-District": "640"}
FIELD_KHEDA = {"X-Dev-Role": "FIELD", "X-Dev-District": "640"}
KHEDA = "W-OTHER-DISTRICT"
ANAND = "W-COSTLY"


@pytest.fixture()
def two_cases(client, api_db):
    with psycopg.connect(api_db) as con:
        con.execute("UPDATE assessments SET band = 'HIGH', priority = 0.5 WHERE work_id = %s",
                    (ANAND,))
    return client


def _move(client, alert_id, frm, to, headers, note=None):
    return client.patch(f"/api/v1/alerts/{alert_id}",
                        json={"from_state": frm, "to_state": to, "note": note}, headers=headers)


def _chain(url):
    with psycopg.connect(url, row_factory=psycopg.rows.dict_row) as con:
        return alerts.verify_chain(con)


# ---- listing and scoping -------------------------------------------------------------------

def test_every_queue_case_is_a_new_alert_before_anyone_touches_it(two_cases):
    r = two_cases.get("/api/v1/alerts", headers=MINISTRY).json()
    by_id = {a["alert_id"]: a for a in r["items"]}
    assert set(by_id) == {KHEDA, ANAND}
    assert all(a["state"] == "NEW" and a["in_queue"] for a in by_id.values())
    assert r["counts"]["NEW"] == 2
    assert by_id[KHEDA]["moves"] == ["TRIAGED"]          # what this user may do next


def test_a_district_officer_sees_and_moves_only_their_district(two_cases):
    ids = {a["alert_id"] for a in two_cases.get("/api/v1/alerts", headers=DISTRICT_ANAND)
           .json()["items"]}
    assert ids == {ANAND}
    assert two_cases.get(f"/api/v1/alerts/{KHEDA}", headers=DISTRICT_ANAND).status_code == 404
    assert _move(two_cases, KHEDA, "NEW", "TRIAGED", DISTRICT_ANAND).status_code == 404
    ids = {a["alert_id"] for a in two_cases.get("/api/v1/alerts", headers=FIELD_KHEDA)
           .json()["items"]}
    assert ids == {KHEDA}


def test_alerts_need_a_signed_in_account(two_cases):
    assert two_cases.get("/api/v1/alerts").status_code == 401
    assert _move(two_cases, KHEDA, "NEW", "TRIAGED", {}).status_code == 401


def test_a_work_outside_the_queue_is_no_alert(two_cases):
    assert two_cases.get("/api/v1/alerts/W-TYPICAL", headers=MINISTRY).status_code == 404
    assert _move(two_cases, "W-TYPICAL", "NEW", "TRIAGED", MINISTRY).status_code == 404


# ---- the lifecycle ---------------------------------------------------------------------------

def test_a_case_walks_the_whole_lifecycle_and_every_change_is_audited(two_cases, api_db):
    steps = [("NEW", "TRIAGED", DISTRICT_KHEDA, None),
             ("TRIAGED", "IN_PLAN", DISTRICT_KHEDA, None),
             ("IN_PLAN", "INSPECTED", FIELD_KHEDA, None),
             ("INSPECTED", "CLEARED", FIELD_KHEDA, "Road seen complete, 340 m as filed"),
             ("CLEARED", "CLOSED", DISTRICT_KHEDA, None)]
    for frm, to, who, note in steps:
        r = _move(two_cases, KHEDA, frm, to, who, note)
        assert r.status_code == 200, r.text
        assert r.json()["state"] == to
    a = two_cases.get(f"/api/v1/alerts/{KHEDA}", headers=MINISTRY).json()
    trail = [(e["action"], e["from_state"], e["to_state"], e["actor_role"]) for e in a["trail"]]
    assert trail == [("open", None, "NEW", "DISTRICT"),
                     ("move", "NEW", "TRIAGED", "DISTRICT"),
                     ("move", "TRIAGED", "IN_PLAN", "DISTRICT"),
                     ("move", "IN_PLAN", "INSPECTED", "FIELD"),
                     ("move", "INSPECTED", "CLEARED", "FIELD"),
                     ("move", "CLEARED", "CLOSED", "DISTRICT")]
    assert a["trail"][4]["note"] == "Road seen complete, 340 m as filed"
    assert a["moves"] == []                                # closed is the end
    assert _chain(api_db) == {"ok": True, "entries": 6, "broken_at": None}


def test_only_the_named_roles_may_make_each_move(two_cases):
    assert _move(two_cases, KHEDA, "NEW", "TRIAGED", FIELD_KHEDA).status_code == 403
    assert _move(two_cases, KHEDA, "NEW", "TRIAGED", MINISTRY).status_code == 200
    # planning visits is the district's job, not the ministry's
    assert _move(two_cases, KHEDA, "TRIAGED", "IN_PLAN", MINISTRY).status_code == 403


def test_a_move_that_skips_steps_is_refused(two_cases):
    r = _move(two_cases, KHEDA, "NEW", "INSPECTED", DISTRICT_KHEDA)
    assert r.status_code == 400 and "cannot move" in r.json()["detail"]
    r = _move(two_cases, KHEDA, "NEW", "SOLVED", DISTRICT_KHEDA)
    assert r.status_code == 422                            # not a state at all


def test_a_move_from_an_old_state_is_refused_so_two_officers_never_both_win(two_cases):
    assert _move(two_cases, KHEDA, "NEW", "TRIAGED", DISTRICT_KHEDA).status_code == 200
    r = _move(two_cases, KHEDA, "NEW", "TRIAGED", MINISTRY)
    assert r.status_code == 409 and "Read by the office" in r.json()["detail"]


def test_a_verdict_or_a_close_without_a_visit_needs_a_note(two_cases):
    for frm, to in [("NEW", "TRIAGED"), ("TRIAGED", "IN_PLAN"), ("IN_PLAN", "INSPECTED")]:
        assert _move(two_cases, KHEDA, frm, to, DISTRICT_KHEDA).status_code == 200
    r = _move(two_cases, KHEDA, "INSPECTED", "ISSUE_CONFIRMED", FIELD_KHEDA, note="  ")
    assert r.status_code == 400 and "note" in r.json()["detail"]
    assert _move(two_cases, KHEDA, "INSPECTED", "ISSUE_CONFIRMED", FIELD_KHEDA,
                 note="Only 180 m laid of the 340 m filed").status_code == 200
    assert _move(two_cases, ANAND, "NEW", "TRIAGED", DISTRICT_ANAND).status_code == 200
    assert _move(two_cases, ANAND, "TRIAGED", "CLOSED", DISTRICT_ANAND).status_code == 400
    assert _move(two_cases, ANAND, "TRIAGED", "CLOSED", DISTRICT_ANAND,
                 note="Same road already inspected last month").status_code == 200


def test_filters_by_state_and_hides_closed_cases_by_default(two_cases):
    _move(two_cases, ANAND, "NEW", "TRIAGED", DISTRICT_ANAND)
    _move(two_cases, ANAND, "TRIAGED", "CLOSED", DISTRICT_ANAND, note="Already inspected")
    _move(two_cases, KHEDA, "NEW", "TRIAGED", DISTRICT_KHEDA)
    open_ids = [a["alert_id"] for a in two_cases.get("/api/v1/alerts", headers=MINISTRY)
                .json()["items"]]
    assert open_ids == [KHEDA]
    r = two_cases.get("/api/v1/alerts", params={"state": "CLOSED"}, headers=MINISTRY).json()
    assert [a["alert_id"] for a in r["items"]] == [ANAND]
    assert r["counts"] == {"NEW": 0, "TRIAGED": 1, "IN_PLAN": 0, "INSPECTED": 0,
                           "ISSUE_CONFIRMED": 0, "CLEARED": 0, "CLOSED": 1}
    everything = two_cases.get("/api/v1/alerts", params={"state": "ALL"}, headers=MINISTRY)
    assert {a["alert_id"] for a in everything.json()["items"]} == {KHEDA, ANAND}


def test_a_case_keeps_its_history_after_it_leaves_the_queue_or_the_works_are_reloaded(
        two_cases, api_db):
    _move(two_cases, KHEDA, "NEW", "TRIAGED", DISTRICT_KHEDA)
    with psycopg.connect(api_db) as con:
        con.execute("UPDATE assessments SET band = 'LOW' WHERE work_id = %s", (KHEDA,))
    r = two_cases.get("/api/v1/alerts", headers=DISTRICT_KHEDA).json()
    item = next(a for a in r["items"] if a["alert_id"] == KHEDA)
    assert item["state"] == "TRIAGED" and item["in_queue"] is False
    # a reload empties the works (data/load_db.py): no alert row may block it or go with it
    with psycopg.connect(api_db) as con:
        fks = con.execute("SELECT conname FROM pg_constraint WHERE contype = 'f' AND conrelid "
                          "IN ('alerts'::regclass, 'audit_log'::regclass)").fetchall()
        con.execute("DELETE FROM works")
        n = con.execute("SELECT count(*) FROM alerts").fetchone()[0]
    assert fks == [] and n == 1 and _chain(api_db)["ok"]


# ---- the audit chain -------------------------------------------------------------------------

def test_the_database_refuses_to_change_or_delete_a_past_entry(two_cases, api_db):
    _move(two_cases, KHEDA, "NEW", "TRIAGED", DISTRICT_KHEDA)
    for sql in ("UPDATE audit_log SET note = 'x'", "DELETE FROM audit_log",
                "TRUNCATE audit_log"):
        with psycopg.connect(api_db) as con, pytest.raises(psycopg.errors.RaiseException):
            con.execute(sql)


def test_the_chain_check_finds_an_entry_changed_or_removed_behind_the_triggers(
        two_cases, api_db):
    for frm, to in [("NEW", "TRIAGED"), ("TRIAGED", "IN_PLAN"), ("IN_PLAN", "INSPECTED")]:
        _move(two_cases, KHEDA, frm, to, DISTRICT_KHEDA)
    assert _chain(api_db) == {"ok": True, "entries": 4, "broken_at": None}
    with psycopg.connect(api_db) as con:            # a database owner can switch triggers off
        con.execute("ALTER TABLE audit_log DISABLE TRIGGER audit_log_no_change")
        con.execute("UPDATE audit_log SET actor_role = 'MINISTRY' WHERE seq = 2")
    assert _chain(api_db) == {"ok": False, "entries": 4, "broken_at": 2}
    with psycopg.connect(api_db) as con:
        con.execute("UPDATE audit_log SET actor_role = 'DISTRICT' WHERE seq = 2")
        con.execute("DELETE FROM audit_log WHERE seq = 3")
    assert _chain(api_db) == {"ok": False, "entries": 3, "broken_at": 4}


def test_the_chain_check_is_open_to_the_ministry_only(two_cases):
    _move(two_cases, KHEDA, "NEW", "TRIAGED", DISTRICT_KHEDA)
    r = two_cases.get("/api/v1/alerts/audit/verify", headers=MINISTRY)
    assert r.status_code == 200 and r.json() == {"ok": True, "entries": 2, "broken_at": None}
    assert two_cases.get("/api/v1/alerts/audit/verify",
                         headers=DISTRICT_KHEDA).status_code == 403


def test_each_hash_covers_every_field_of_its_entry():
    at = datetime(2026, 10, 20, 9, 30, tzinfo=UTC)
    e = {"seq": 1, "at": at, "alert_id": "W-1", "actor_id": "u", "actor_role": "DISTRICT",
         "actor_name": "A", "action": "open", "from_state": None, "to_state": "NEW",
         "note": None}
    h = alerts.entry_hash(alerts.GENESIS, e)
    assert h == alerts.entry_hash(alerts.GENESIS, dict(e))
    for k, v in [("seq", 2), ("at", at + timedelta(microseconds=1)), ("note", ""),
                 ("actor_name", "B"), ("to_state", "TRIAGED")]:
        assert alerts.entry_hash(alerts.GENESIS, {**e, k: v}) != h, k
    assert alerts.entry_hash("f" * 64, e) != h


# ---- set-up and the digest -------------------------------------------------------------------

def test_without_migration_015_the_alerts_answer_503_and_the_queue_still_works(two_cases, api_db):
    with psycopg.connect(api_db) as con:
        con.execute("DROP TABLE audit_log, alerts")
    r = two_cases.get("/api/v1/alerts", headers=MINISTRY)
    assert r.status_code == 503 and "015_alerts.sql" in r.json()["detail"]
    assert two_cases.get("/api/v1/queue", headers=MINISTRY).status_code == 200


def test_the_daily_digest_counts_each_district_and_names_closes_without_a_visit(
        two_cases, api_db):
    _move(two_cases, ANAND, "NEW", "TRIAGED", DISTRICT_ANAND)
    _move(two_cases, ANAND, "TRIAGED", "CLOSED", DISTRICT_ANAND, note="Already inspected")
    with psycopg.connect(api_db, row_factory=psycopg.rows.dict_row) as con:
        text = alerts.digest(con, now=datetime.now(UTC))
    assert "Kheda: 1 not read yet" in text
    assert "Anand:" in text and "1 closed without a visit" in text
    assert "audit chain: intact, 3 entries" in text
    with psycopg.connect(api_db, row_factory=psycopg.rows.dict_row) as con:
        later = alerts.digest(con, now=datetime.now(UTC) + timedelta(days=20))
    assert "Kheda: 1 not read yet (1 waiting over 14 days)" in later
