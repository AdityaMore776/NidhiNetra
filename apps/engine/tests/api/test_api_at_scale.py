"""The API on a realistic database (T056): every page's endpoint, every role, messy data.

The other API tests use four hand-made works. Here the test country's 1,302 made-up works across
several districts are loaded, a few made messy the way real rows are (other scripts, a person's
name and a phone number in the text, a 2,000-character description, none at all, a work id a URL
must escape), some with malformed evidence attached, and the real batch assesses them all. Then:
no endpoint may answer 500, a district officer never sees another district, the queue agrees with
the stored bands, and no text the API returns holds anything the masker would hide or a word the
engines may never say.
"""

from __future__ import annotations

import json
import random
from datetime import date
from urllib.parse import quote

import psycopg
import pytest
from fastapi.testclient import TestClient
from psycopg.types.json import Jsonb

from drishti import batch
from drishti.agents.contract import check_plain_language
from drishti.evaluation.stats import build_store
from drishti.evaluation.synthetic import Generator
from drishti.pipeline.orchestrator import Context
from drishti.validation.pii import mask

AS_OF = date(2026, 5, 26)
COLUMNS = ("work_id", "source", "house", "term", "state_lgd", "state_name", "district_lgd",
           "district_name", "constituency", "mp_name", "agency_name", "fy", "work_type_code",
           "category", "description", "amount", "recommended_date", "completed_date", "status",
           "quantity", "quantity_unit", "is_outside_constituency", "sanction_date")
ODD_ID = "WS/MP999/2024-2025/77 A&B?#%"
MESSY = ["PCC Road from Ramdev Bhagat house to school, contact 9061234567",
         "मंदिर परिसर में शेड निर्माण", "கோவில் வளாகத்தில் கொட்டகை", "x" * 2000, "", None,
         "SURAJ PATEL S/O DINESH PATEL K GHAR SOLAR LIGHT"]
EVIDENCE = [
    {"files": [{"id": "D1", "ext": "pdf", "sha256": "s1", "readable": True, "certificates": [
        {"sanctioned_amount": "1,00,000", "sanction_date": "2024-01-10",
         "payments": [["2024-03-01", 100000]], "location": "near Ramdev Bhagat house",
         "vendor_code": "V123456789012"}]}]},
    {"files": [None, "x", {}, {"id": 5, "ext": ".JPG", "phash": "zz", "stamps": "s"}]},
    {"files": "not a list"},
]


def _strings(x, path=""):
    if isinstance(x, str):
        yield path, x
    elif isinstance(x, dict):
        for k, v in x.items():
            yield from _strings(v, f"{path}.{k}")
    elif isinstance(x, list):
        for i, v in enumerate(x):
            yield from _strings(v, f"{path}[{i}]")


# identifiers, not text a person reads: a long digit run in a work id is not an account number
IDS = ("work_id", "case_id", "group_id", "id", "user_id", "sha256", "phash", "vendor_code",
       "code", "key")


def _clean(payload) -> None:
    """Nothing the masker would hide, no accusing word (in what the engines wrote)."""
    for path, s in _strings(payload):
        last = path.rsplit(".", 1)[-1].split("[", 1)[0]
        if last in IDS or ".others" in path:
            continue
        assert mask(s) == s, (path, s[:120])
        if path.endswith((".text", ".headline", ".verdict")):
            check_plain_language(s)


@pytest.fixture(scope="module")
def world(pg_server):
    admin = pg_server.get_uri()
    with psycopg.connect(admin, autocommit=True) as con:
        con.execute("DROP DATABASE IF EXISTS at_scale")
        con.execute("CREATE DATABASE at_scale")
    from urllib.parse import urlsplit, urlunsplit

    from drishti import migrate

    url = urlunsplit(urlsplit(admin)._replace(path="/at_scale"))
    migrate.apply(url)
    works = [dict(w) for w in Generator(seed=11, small=True).build().works]
    rng = random.Random(56)
    for w, text in zip(rng.sample(works, len(MESSY)), MESSY, strict=True):
        w["description"] = text
    works[0] = {**works[0], "work_id": ODD_ID}
    with psycopg.connect(url) as con:
        districts = {(w["district_lgd"], w["district_name"], w["state_lgd"], w["state_name"])
                     for w in works}
        for d in districts:
            con.execute("INSERT INTO districts VALUES (%s, %s, %s, %s)", d)
        with con.cursor().copy(f"COPY works ({', '.join(COLUMNS)}) FROM STDIN") as cp:
            for w in works:
                cp.write_row(["SCENARIO" if c == "source" else w.get(c) for c in COLUMNS])
        with_evidence = rng.sample(works, 30)
        for i, w in enumerate(with_evidence):
            con.execute("INSERT INTO evidence_facts (work_id, data, version) VALUES (%s, %s, 't')",
                        (w["work_id"], Jsonb(EVIDENCE[i % len(EVIDENCE)])))
        con.commit()
    store = build_store(works)
    bands = batch.assess_all(url, Context(stats=store, as_of=AS_OF))
    mp = pytest.MonkeyPatch()
    mp.setenv("DATABASE_URL", url)
    mp.setenv("DRISHTI_AUTH", "dev")
    mp.setenv("DRISHTI_SNAPSHOT_DATE", AS_OF.isoformat())
    mp.delenv("VERCEL", raising=False)
    from drishti.api import routes
    from drishti.main import app

    mp.setattr(routes, "_stats", lambda: store)
    batch._NATIONAL.clear()                 # office counts belong to this database
    yield {"client": TestClient(app), "works": works, "url": url, "bands": bands,
           "districts": sorted({d[0] for d in districts}),
           "with_evidence": [w["work_id"] for w in with_evidence]}
    batch._NATIONAL.clear()
    mp.undo()


def _roles(world):
    a, b = world["districts"][:2]
    return {"ministry": {"X-Dev-Role": "MINISTRY"},
            "district": {"X-Dev-Role": "DISTRICT", "X-Dev-District": a},
            "field": {"X-Dev-Role": "FIELD", "X-Dev-District": b}}


def test_the_batch_assessed_every_work(world):
    assert sum(world["bands"].values()) == len(world["works"])


@pytest.mark.parametrize("role", ["ministry", "district", "field"])
def test_every_listing_answers_for_every_role(world, role):
    c, h = world["client"], _roles(world)[role]
    for path in ("/api/v1/me", "/api/v1/dashboard/summary", "/api/v1/dashboard/districts",
                 "/api/v1/dashboard/offices", "/api/v1/dashboard/office-habits",
                 "/api/v1/presanction/options", "/api/v1/queue", "/api/v1/queue?page=2",
                 "/api/v1/works", "/api/v1/works?page=3", "/api/v1/works?q=road",
                 "/api/v1/works?q=%E0%A4%AE%E0%A4%82%E0%A4%A6%E0%A4%BF%E0%A4%B0",
                 "/api/v1/works?band=HIGH", "/api/v1/works?type=ROAD_CC",
                 "/api/v1/works?page=9999", "/api/v1/works?q=%27%3B%20DROP%20TABLE%20works"):
        r = c.get(path, headers=h)
        assert r.status_code == 200, (path, r.status_code, r.text[:200])
        if path != "/api/v1/me":                # the signed-in user's own name
            _clean(r.json())


def test_every_work_page_opens_and_shows_nothing_private(world):
    c, h = world["client"], _roles(world)["ministry"]
    with psycopg.connect(world["url"]) as con:
        full = [r[0] for r in con.execute("SELECT work_id FROM assessments WHERE NOT compact")]
    messy = [w["work_id"] for w in world["works"]
             if w["description"] in MESSY or w["work_id"] == ODD_ID]
    sample = messy + world["with_evidence"] + full[:20] + random.Random(3).sample(
        [w["work_id"] for w in world["works"]], 40)
    for wid in sample:
        r = c.get("/api/v1/works/" + quote(wid, safe="/"), headers=h)
        assert r.status_code == 200, (wid, r.status_code, r.text[:200])
        body = r.json()
        assert body["work"]["work_id"] == wid
        agents = body["assessment"]["agents"]
        assert agents and all(a["status"] != "ERROR" for a in agents), wid
        _clean(body)
        json.dumps(body)


def test_a_district_officer_never_sees_another_district(world):
    c = world["client"]
    a, b = world["districts"][:2]
    h = {"X-Dev-Role": "DISTRICT", "X-Dev-District": a}
    other = next(w["work_id"] for w in world["works"] if w["district_lgd"] == b)
    assert c.get("/api/v1/works/" + quote(other, safe="/"), headers=h).status_code == 404
    for path in ("/api/v1/works", "/api/v1/queue", "/api/v1/works?district=" + b):
        items = c.get(path, headers=h).json()["items"]
        assert all(i["district_lgd"] == a for i in items), path
    r = c.post("/api/v1/presanction", headers=h, json={
        "district_lgd": b, "description": "CC road in village X", "amount": 300000})
    assert r.status_code == 404


def test_the_queue_agrees_with_the_stored_bands(world):
    c, h = world["client"], _roles(world)["ministry"]
    with psycopg.connect(world["url"]) as con:
        cases = con.execute("SELECT count(DISTINCT coalesce(case_id, work_id)) FROM assessments "
                            "WHERE band IN ('HIGH', 'CRITICAL')").fetchone()[0]
    q = c.get("/api/v1/queue", headers=h).json()
    assert q["total"] == cases
    prio = [i["priority"] for i in q["items"]]
    assert prio == sorted(prio, reverse=True)


def test_the_pre_sanction_check_never_fails_on_odd_input(world):
    c, h = world["client"], _roles(world)["ministry"]
    d = world["districts"][0]
    rng = random.Random(9)
    bodies = [{}, {"district_lgd": d}, {"district_lgd": d, "description": "ab", "amount": 1},
              {"district_lgd": d, "description": "CC road", "amount": -5},
              {"district_lgd": d, "description": "CC road", "amount": "lots"},
              {"district_lgd": d, "description": "CC road", "amount": 1e11},
              {"district_lgd": "99999", "description": "CC road in X", "amount": 300000},
              {"district_lgd": d, "description": "x" * 2001, "amount": 300000},
              {"district_lgd": d, "description": "CC road", "amount": 300000,
               "work_type_code": "NOT_A_TYPE"}]
    for _ in range(25):
        bodies.append({"district_lgd": d, "amount": rng.choice([1, 4.99e5, 5e5, 2.5e6, 1e10]),
                       "description": rng.choice(MESSY[:3] + [
                           "Construction of temple", "CC road near Shiv temple",
                           "Purchase of 50 benches", "Boundary wall of school"]),
                       "work_type_code": rng.choice([None, "ROAD_CC", "COMMUNITY_HALL"]),
                       "is_outside_constituency": rng.choice([True, False])})
    for body in bodies:
        r = c.post("/api/v1/presanction", headers=h, json=body)
        assert r.status_code in (200, 404, 422), (body, r.status_code, r.text[:200])
        if r.status_code == 200:
            out = r.json()
            assert out["colour"] in ("RED", "AMBER", "GREEN")
            _clean(out)


def test_the_visualization_trace_runs_on_the_live_route(world):
    """POST /explain (T092): the same pipeline on a typed example, behind the same sign-in."""
    c, h = world["client"], _roles(world)["ministry"]
    a, b = world["districts"][:2]
    body = {"district_lgd": a, "description": "Construction of temple near Ramdev Bhagat house",
            "amount": 450000, "work_type_code": "COMMUNITY_HALL"}
    r = c.post("/api/v1/explain", headers=h, json=body)
    assert r.status_code == 200, r.text[:300]
    t = r.json()
    assert {"input", "privacy", "reading", "checks", "scoring", "result"} <= set(t)
    assert t["result"]["colour"] in ("RED", "AMBER", "GREEN")
    _clean(t)
    later = {**body, "status": "COMPLETED", "recommended_date": "2025-06-01",
             "sanction_date": "2025-07-01", "completed_date": "2025-01-01"}
    r = c.post("/api/v1/explain", headers=h, json=later)
    assert r.status_code == 200 and r.json()["input"]["completed"] == "2025-01-01"
    assert c.post("/api/v1/explain", json=body).status_code == 200      # open to all (T130)
    officer = {"X-Dev-Role": "DISTRICT", "X-Dev-District": a}
    assert c.post("/api/v1/explain", headers=officer,
                  json={**body, "district_lgd": b}).status_code == 404
    for bad in ({**body, "status": "PAID"}, {**body, "completed_date": "not a date"},
                {**body, "amount": 0}, {"district_lgd": a}):
        assert c.post("/api/v1/explain", headers=h, json=bad).status_code == 422
