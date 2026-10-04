"""The cost estimate form's two routes (T093): the fields for a work type, and the checks.
Neither needs the database; both need a signed-in user; no body ever gets an error."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from tests.cost_form.test_cost_form import road_form

DEV = {"X-Dev-Role": "DISTRICT", "X-Dev-District": "9999"}


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setenv("DRISHTI_AUTH", "dev")
    monkeypatch.delenv("VERCEL", raising=False)
    from drishti.main import app

    return TestClient(app)


def test_the_form_gets_the_fields_of_its_work_type(client):
    r = client.get("/api/v1/cost-form/catalog", params={"work_type": "ROAD_CC"}, headers=DEV)
    assert r.status_code == 200
    body = r.json()
    ids = {f["id"] for f in body["size_fields"]}
    assert {"length_m", "width_m", "concrete_grade", "cc_thickness_mm"} <= ids
    assert "bt_layer" not in ids                       # bituminous roads only
    assert body["linear"] and not body["goods"] and body["family"] == "road"
    assert {m["id"] for m in body["materials"]} >= {"cement", "sand", "steel_rebar"}
    other = client.get("/api/v1/cost-form/catalog", params={"work_type": "OTHER"}, headers=DEV)
    assert {f["id"] for f in other.json()["size_fields"]} >= {"size_measure", "size_value"}
    assert client.get("/api/v1/cost-form/catalog", params={"work_type": "NOPE"},
                      headers=DEV).status_code == 404


def test_the_checks_answer_any_body(client):
    ok = client.post("/api/v1/cost-form/validate", json=road_form(), headers=DEV).json()
    assert ok["computed"]["lines_total"] == 1_876_000
    for body in (None, [], "x", 3, {"sites": "x"}, {"work": {"work_type": ["ROAD_CC"]}}):
        r = client.post("/api/v1/cost-form/validate", json=body, headers=DEV)
        assert r.status_code == 200 and r.json()["ready"] is False


def test_both_routes_are_open_to_view(client):
    """They store nothing: the blank form and its checks are public, like the site (T130)."""
    assert client.get("/api/v1/cost-form/catalog").status_code == 200
    assert client.post("/api/v1/cost-form/validate", json={}).status_code == 200
