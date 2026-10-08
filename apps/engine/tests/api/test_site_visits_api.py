"""Site visits (T123, T124, migration 014): start filming, upload, done, read back, the job's
readings reaching Site Progress and Time & Rules, district scoping, settings that are missing."""

from __future__ import annotations

import psycopg
from psycopg.types.json import Jsonb

from drishti import capture
from tests.api.conftest import MINISTRY

KHEDA = {"X-Dev-Role": "DISTRICT", "X-Dev-District": "640"}
SHA = "a" * 64


def _setup(monkeypatch, storage=True):
    monkeypatch.setenv("DRISHTI_CAPTURE_SECRET", "test-secret-of-sixteen-plus")
    if storage:
        monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
        monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "service-key")
        monkeypatch.setattr(capture, "signed_upload",
                            lambda path, client=None: f"https://upload.example/{path}?t=1")
        monkeypatch.setattr(capture, "signed_download",
                            lambda path, seconds=3600, client=None: f"https://dl.example/{path}")
    else:
        monkeypatch.delenv("SUPABASE_URL", raising=False)
        monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)


def _start(client, work="W-TYPICAL", kind="baseline", headers=MINISTRY):
    return client.post("/api/v1/site-visits/start", headers=headers,
                       json={"work_id": work, "kind": kind})


def _done(client, visit_id, token, headers=MINISTRY, **kw):
    body = {"token": token, "sha256": SHA, "captured_at": "2026-04-01T10:00:00+05:30",
            "claim": "site cleared", "log": {"in_app": True, "viewpoints": [], "gps": []}}
    body.update(kw)
    return client.post(f"/api/v1/site-visits/{visit_id}/done", headers=headers, json=body)


def test_without_the_capture_secret_it_answers_503(client, monkeypatch):
    monkeypatch.delenv("DRISHTI_CAPTURE_SECRET", raising=False)
    assert _start(client).status_code == 503


def test_a_visit_from_start_to_uploaded(client, monkeypatch):
    _setup(monkeypatch)
    r = _start(client)
    assert r.status_code == 200
    v = r.json()
    assert v["kind"] == "baseline" and v["token"] and v["viewpoints"] == []
    up = client.post(f"/api/v1/site-visits/{v['visit_id']}/upload", headers=MINISTRY,
                     json={"token": v["token"]})
    assert up.status_code == 200 and up.json()["upload_url"].startswith("https://upload.example/")
    d = _done(client, v["visit_id"], v["token"])
    assert d.status_code == 200 and d.json()["status"] == "uploaded"
    back = client.get("/api/v1/site-visits/W-TYPICAL", headers=MINISTRY).json()
    assert back["visits"][0]["status"] == "uploaded" and back["next_kind"] == "monthly"
    # once uploaded, the visit cannot be re-sent
    assert _done(client, v["visit_id"], v["token"]).status_code == 409


def test_a_token_is_bound_to_its_visit_and_person(client, monkeypatch):
    _setup(monkeypatch)
    a, b = _start(client).json(), _start(client).json()
    assert _done(client, a["visit_id"], b["token"]).status_code == 403
    assert _done(client, a["visit_id"], "x" * 20).status_code == 403
    # a token issued to another person (dev sign-in gives everyone the same user id)
    theirs = capture.issue(a["visit_id"], "W-TYPICAL", "baseline", "someone-else")
    assert _done(client, a["visit_id"], theirs).status_code == 403


def test_an_expired_token_is_refused(client, monkeypatch):
    _setup(monkeypatch)
    v = _start(client).json()
    old = capture.issue(v["visit_id"], "W-TYPICAL", "baseline", "dev", now=0)
    assert capture.check(old) is None
    assert _done(client, v["visit_id"], old).status_code == 403


def test_a_district_officer_reaches_only_their_works(client, monkeypatch):
    _setup(monkeypatch)
    assert _start(client, headers=KHEDA).status_code == 404
    assert client.get("/api/v1/site-visits/W-TYPICAL", headers=KHEDA).status_code == 404
    assert _start(client, work="W-OTHER-DISTRICT", headers=KHEDA).status_code == 200


def test_a_bad_kind_or_a_huge_log_is_refused(client, monkeypatch):
    _setup(monkeypatch)
    assert _start(client, kind="selfie").status_code == 422
    v = _start(client).json()
    big = {"in_app": True, "gps": [{"t": i, "lat": 25.0, "lon": 82.0} for i in range(60000)]}
    assert _done(client, v["visit_id"], v["token"], log=big).status_code == 413


def test_without_storage_the_upload_url_is_503(client, monkeypatch):
    _setup(monkeypatch, storage=False)
    v = _start(client).json()
    r = client.post(f"/api/v1/site-visits/{v['visit_id']}/upload", headers=MINISTRY,
                    json={"token": v["token"]})
    assert r.status_code == 503


def test_read_visits_reach_site_progress_and_the_work_page(client, monkeypatch, api_db):
    _setup(monkeypatch)
    base = _start(client).json()
    _done(client, base["visit_id"], base["token"])
    copy = _start(client, kind="monthly").json()
    _done(client, copy["visit_id"], copy["token"], captured_at="2026-05-01T10:00:00+05:30")
    # what the video job writes: the second visit is the first one's footage again
    with psycopg.connect(api_db) as con:
        con.execute("UPDATE site_visits SET status = 'read', readings = %s, kept = %s "
                    "WHERE visit_id = %s",
                    (Jsonb({"sealed": True, "in_app": True, "gps_inside": True,
                            "views_match_site": None, "viewpoints_expected": 4,
                            "viewpoints_matched": 4, "zones_shown": ["v1", "v2", "v3", "v4"]}),
                     Jsonb({"viewpoints": {"v1": {"path": "frames/v1.jpg"}}}),
                     base["visit_id"]))
        con.execute("UPDATE site_visits SET status = 'read', readings = %s WHERE visit_id = %s",
                    (Jsonb({"sealed": True, "in_app": True, "reused_from": [
                        {"work_id": "W-TYPICAL", "visit_id": base["visit_id"], "frames": 40}]}),
                     copy["visit_id"]))
        con.commit()
    back = client.get("/api/v1/site-visits/W-TYPICAL", headers=MINISTRY).json()
    assert back["viewpoints"] == [{"id": "v1", "frame_url": "https://dl.example/frames/v1.jpg",
                                   "pan_urls": [], "anchor": None, "facing": None}]
    from drishti import batch, config
    from drishti.agents.statistical.cohort import StatsStore
    from drishti.pipeline.orchestrator import Context
    with psycopg.connect(api_db, row_factory=psycopg.rows.dict_row) as con:
        a = batch.assess_one(con, "W-TYPICAL",
                             Context(stats=StatsStore.load(api_db), as_of=config.snapshot_date()))
    site = next(r for r in a.agents if r.agent == "site_progress") if any(
        r.agent == "site_progress" for r in a.agents) else None
    from drishti.agents.site_progress import agent as sp
    with psycopg.connect(api_db, row_factory=psycopg.rows.dict_row) as con:
        w = batch.with_evidence(con, [{"work_id": "W-TYPICAL", "status": "SANCTIONED"}])[0]
    assert len(w["site_visits"]) == 2
    judged = sp.assess(w, config.snapshot_date())
    assert judged.findings[0].code == "FOOTAGE_USED_BEFORE"
    if site is not None:                      # once Site Progress is a core agent (T125)
        assert site.findings and site.findings[0].code == "FOOTAGE_USED_BEFORE"


def test_capture_tokens_need_a_long_secret(monkeypatch):
    monkeypatch.setenv("DRISHTI_CAPTURE_SECRET", "short")
    try:
        capture.issue("v", "w", "monthly", "u")
    except capture.NotSetUp:
        pass
    else:
        raise AssertionError("a short secret must not issue tokens")


def test_the_stretch_seed_is_fixed_per_visit_and_needs_the_secret(monkeypatch):
    # T158: which stretches of a long road a visit films is drawn from this seed
    monkeypatch.setenv("DRISHTI_CAPTURE_SECRET", "test-secret-of-sixteen-plus")
    a = capture.seed("visit-1")
    assert len(a) == 32 and capture.seed("visit-1") == a and capture.seed("visit-2") != a
    monkeypatch.setenv("DRISHTI_CAPTURE_SECRET", "another-secret-sixteen-plus")
    assert capture.seed("visit-1") != a



ROAD = {"work": {"work_type": "ROAD_CC"},
        "sites": [{"location": {"lat": 22.30, "lon": 72.90, "end_lat": 22.33, "end_lon": 72.90},
                   "size": {"length_m": 3300, "width_m": 3.75}}]}


def test_the_next_visit_is_told_where_to_stand_and_which_way_to_face(client, monkeypatch, api_db):
    # T158: each viewpoint's anchor is the first good fix; its facing comes from the same visit
    _setup(monkeypatch)
    ids = []
    for kind, day in (("baseline", "2026-04-01"), ("monthly", "2026-05-01")):
        v = _start(client, kind=kind).json()
        _done(client, v["visit_id"], v["token"], captured_at=f"{day}T10:00:00+05:30")
        ids.append(v["visit_id"])
    first = {"viewpoints": {"v1": {"path": "frames/b/v1.jpg",
                                   "spot": {"lat": 22.3000, "lon": 72.9, "acc": 6.0},
                                   "facing": {"from": 80, "to": 120, "mid": 100, "width": 40},
                                   "pans": ["frames/b/v1-pan1.jpg"]}}}
    later = {"viewpoints": {"v1": {"path": "frames/m/v1.jpg",
                                   "spot": {"lat": 22.3003, "lon": 72.9, "acc": 4.0},
                                   "facing": {"from": 0, "to": 10, "mid": 5, "width": 10},
                                   "pans": ["frames/m/v1-pan1.jpg", "frames/m/v1-pan2.jpg"]}}}
    with psycopg.connect(api_db) as con:
        for vid, kept in zip(ids, (first, later), strict=True):
            con.execute("UPDATE site_visits SET status = 'read', readings = %s, kept = %s "
                        "WHERE visit_id = %s", (Jsonb({"views_match_site": True}), Jsonb(kept),
                                                vid))
        con.commit()
    back = client.get("/api/v1/site-visits/W-TYPICAL", headers=MINISTRY).json()
    v1 = back["viewpoints"][0]
    assert v1["anchor"] == {"lat": 22.3, "lon": 72.9, "acc": 6.0, "box_m": 6.0}
    assert v1["facing"]["mid"] == 100
    assert v1["frame_url"].endswith("frames/m/v1.jpg") and len(v1["pan_urls"]) == 2
    assert back["spots_needed"] == 2                     # no submitted form: the minimum


def test_a_long_road_visit_is_given_its_stretches_when_filming_starts(client, monkeypatch, api_db):
    _setup(monkeypatch)
    with psycopg.connect(api_db) as con:
        con.execute("INSERT INTO cost_forms (work_id, status, form, ready, submitted_at) "
                    "VALUES ('W-TYPICAL', 'submitted', %s, true, now()) ON CONFLICT (work_id) "
                    "DO UPDATE SET form = EXCLUDED.form, status = 'submitted'", (Jsonb(ROAD),))
        con.commit()
    a, b = _start(client, kind="monthly").json(), _start(client, kind="monthly").json()
    assert a["site"]["kind"] == "linear" and a["spots_needed"] == 8
    assert len(a["stretches_asked"]) == 8 and a["stretches_asked"][0] == "s1"
    assert a["stretches_asked"][-1] == a["site"]["stretches"][-1]
    assert a["stretches_asked"] != b["stretches_asked"]     # a fresh draw for every visit
