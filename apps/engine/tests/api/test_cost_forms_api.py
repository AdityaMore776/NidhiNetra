"""Saved cost estimate forms (T099, migration 013): draft, submit, read back, scoping, and the
Cost and Duplicate checks answering from a submitted form at once."""

import copy

from tests.api.conftest import DISTRICT_ANAND, MINISTRY
from tests.cost_form.test_cost_form import road_form

KHEDA = {"X-Dev-Role": "DISTRICT", "X-Dev-District": "640"}


def _form(**work):
    f = copy.deepcopy(road_form())
    f["work"].update(work)
    return f


def _agent(client, work_id, agent):
    a = client.get(f"/api/v1/works/{work_id}", headers=MINISTRY).json()["assessment"]
    return next(r for r in a["agents"] if r["agent"] == agent)


def test_a_work_with_no_form_reads_back_none_and_its_recommendation(client):
    r = client.get("/api/v1/cost-forms/W-TYPICAL", headers=MINISTRY)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] is None and body["form"] is None and body["ready"] is False
    assert body["recommendation"]["mp_amount"] == 160_000
    assert body["recommendation"]["recommended_type"] == "ROAD_CC"
    assert isinstance(body["earlier_candidates"], list)


def test_a_draft_is_saved_whatever_its_state(client):
    half = {"work": {"work_type": "ROAD_CC"}}
    r = client.post("/api/v1/cost-forms", headers=MINISTRY,
                    json={"work_id": "W-TYPICAL", "form": half})
    assert r.status_code == 200 and r.json()["status"] == "draft" and not r.json()["ready"]
    back = client.get("/api/v1/cost-forms/W-TYPICAL", headers=MINISTRY).json()
    assert back["status"] == "draft" and back["form"]["work"] == {"work_type": "ROAD_CC"}
    # a draft never reaches the engines
    assert _agent(client, "W-TYPICAL", "cost_estimate")["status"] == "NOT_APPLICABLE"


def test_a_form_with_fields_to_fix_cannot_be_submitted(client):
    r = client.post("/api/v1/cost-forms", headers=MINISTRY,
                    json={"work_id": "W-TYPICAL", "form": {"work": {}}, "submit": True})
    assert r.status_code == 422 and r.json()["detail"]["issues"]


def test_a_submitted_form_reaches_the_cost_check_and_is_read_only(client):
    before = _agent(client, "W-TYPICAL", "cost_estimate")
    assert before["status"] == "NOT_APPLICABLE" and before["name"] == "Cost"
    form = _form()
    form["recommendation"]["mp_amount"] = 1          # ignored: the MP's amount is the record's
    # ... Rs 1.6 lakh against an estimate of Rs 23 lakh: the form asks why, so say why
    form["totals"]["reason_differs_from_mp"] = ("the MP's amount was a first guess for a short "
                                                "stretch; the survey found the full 250 m road")
    r = client.post("/api/v1/cost-forms", headers=MINISTRY,
                    json={"work_id": "W-TYPICAL", "form": form, "submit": True})
    assert r.status_code == 200, r.json()
    body = r.json()
    assert body["status"] == "submitted" and body["ready"] and body["assessed"]
    back = client.get("/api/v1/cost-forms/W-TYPICAL", headers=MINISTRY).json()
    assert back["form"]["recommendation"]["mp_amount"] == 160_000
    assert back["submitted_at"]
    # re-assessed at once: the Cost check now reads the form (Gujarat has no price reference
    # yet, so it says it could not compare; never "no form")
    after = _agent(client, "W-TYPICAL", "cost_estimate")
    assert after["status"] == "NOT_ASSESSABLE" and "no cost estimate form" not in \
        after["headline"].lower()
    assert client.post("/api/v1/cost-forms", headers=MINISTRY,
                       json={"work_id": "W-TYPICAL", "form": form}).status_code == 409


def test_a_district_officer_reaches_only_their_districts_forms(client):
    assert client.get("/api/v1/cost-forms/W-OTHER-DISTRICT",
                      headers=DISTRICT_ANAND).status_code == 404
    assert client.post("/api/v1/cost-forms", headers=DISTRICT_ANAND,
                       json={"work_id": "W-OTHER-DISTRICT", "form": {}}).status_code == 404
    assert client.get("/api/v1/cost-forms/W-OTHER-DISTRICT", headers=KHEDA).status_code == 200


def test_saving_needs_sign_in(client):
    assert client.get("/api/v1/cost-forms/W-TYPICAL").status_code == 401
    assert client.post("/api/v1/cost-forms", json={"work_id": "W-TYPICAL",
                                                   "form": {}}).status_code == 401
