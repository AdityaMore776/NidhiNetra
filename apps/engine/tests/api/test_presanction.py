"""Pre-sanction check (T064): one test per colour, scoping, and that nothing is stored."""

from __future__ import annotations

import psycopg

from tests.api.conftest import DISTRICT_ANAND, MINISTRY


def _check(client, headers=MINISTRY, **kw):
    body = {"district_lgd": "639", "work_type_code": "ROAD_CC",
            "description": "CC road in village Sundarpur", "amount": 150_000} | kw
    return client.post("/api/v1/presanction", json=body, headers=headers)


def test_an_ordinary_new_road_is_green_and_says_it_is_not_a_clean_chit(client):
    r = _check(client).json()
    assert r["colour"] == "GREEN" and r["reasons"] == []
    assert "not a clean chit" in r["advice"] and r["district_name"] == "Anand"


def test_a_work_already_recommended_in_the_district_is_amber(client):
    # W-TYPICAL is "CC road in village Bijdih", Rs 1.6 lakh, in Anand
    r = _check(client, description="CC road in village Bijdih", amount=160_000).json()
    assert r["colour"] == "AMBER"
    assert any(x["engine"] == "Duplicate & Split Work" and "W-TYPICAL" in x["text"]
               for x in r["reasons"])
    assert "questions, not findings" in r["advice"]


def test_a_prohibited_work_is_amber_with_the_guideline_reason(client):
    r = _check(client, description="Construction of temple in village Sundarpur",
               work_type_code="COMMUNITY_HALL").json()
    assert r["colour"] == "AMBER"
    assert any(x["code"] == "POSSIBLY_INADMISSIBLE" for x in r["reasons"])


def test_above_the_outside_area_ceiling_is_red_and_never_blocks(client):
    r = _check(client, is_outside_constituency=True, amount=3_000_000).json()
    assert r["colour"] == "RED"
    top = r["reasons"][0]
    assert top["code"] == "OUTSIDE_AREA_CEILING" and top["serious"] and "para 2.9" in top["text"]
    assert "never blocks" in r["advice"]


def test_a_district_officer_checks_only_their_own_district(client):
    assert _check(client, headers=DISTRICT_ANAND).status_code == 200
    assert _check(client, headers=DISTRICT_ANAND, district_lgd="640").status_code == 404
    assert _check(client, district_lgd="999").status_code == 404


def test_bad_input_is_refused_and_nothing_is_stored(client, api_db):
    assert _check(client, amount=0).status_code == 422
    assert _check(client, description="").status_code == 422
    _check(client)
    with psycopg.connect(api_db) as con:
        n = con.execute("SELECT count(*) FROM works WHERE work_id = 'PRE-SANCTION'").fetchone()
        a = con.execute("SELECT count(*) FROM assessments "
                        "WHERE work_id = 'PRE-SANCTION'").fetchone()
    assert n[0] == 0 and a[0] == 0


def test_the_form_offers_only_the_users_districts_and_every_work_type(client):
    allx = client.get("/api/v1/presanction/options", headers=MINISTRY).json()
    mine = client.get("/api/v1/presanction/options", headers=DISTRICT_ANAND).json()
    assert {d["district_lgd"] for d in allx["districts"]} == {"639", "640"}
    assert [d["district_lgd"] for d in mine["districts"]] == ["639"]
    codes = {t["code"] for t in allx["work_types"]}
    assert {"ROAD_CC", "COMMUNITY_HALL"} <= codes and all(t["name"] for t in allx["work_types"])
