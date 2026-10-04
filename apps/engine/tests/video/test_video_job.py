"""The site video job end to end (T124): visits uploaded through the API's table, videos in a
local store, the job reads them, deletes the videos, keeps blurred frames and readings, and
Site Progress answers from them. Needs OpenCV; skipped where it is not installed."""

from __future__ import annotations

from datetime import date

import psycopg
import pytest
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

pytest.importorskip("cv2")

from drishti import batch, capture  # noqa: E402
from drishti.agents.site_progress import agent as sp  # noqa: E402
from drishti.video import job  # noqa: E402
from tests.video.test_video_visit import film, scene  # noqa: E402

FORM = {"work": {"work_type": "COMMUNITY_HALL", "nature": "new"},
        "sites": [{"location": {"lat": 25.75, "lon": 82.69}, "size": {"built_up_area_m2": 400}}]}


def _upload(con, store, work_id, visit_id, kind, video, log, day):
    data = video.read_bytes()
    store.put(f"videos/{visit_id}.webm", data, "video/webm")
    con.execute("INSERT INTO site_visits (visit_id, work_id, kind, status, captured_at, "
                "uploaded_at, video_path, video_sha256, log, claim) VALUES "
                "(%s,%s,%s,'uploaded',%s,%s,%s,%s,%s,%s)",
                (visit_id, work_id, kind, day, day, f"videos/{visit_id}.webm",
                 log["sealed_sha256"], Jsonb(log), "walls up to lintel level"))
    con.commit()


@pytest.fixture()
def db(migrated_url):
    with psycopg.connect(migrated_url, row_factory=dict_row) as con:
        con.execute("INSERT INTO districts VALUES ('639','Anand','24','Gujarat')")
        for wid in ("H1", "H2"):
            con.execute("INSERT INTO works (work_id, source, state_lgd, state_name, district_lgd, "
                        "district_name, work_type_code, description, amount, status, "
                        "recommended_date) VALUES (%s,'REAL','24','Gujarat','639','Anand',"
                        "'COMMUNITY_HALL','Community hall',900000,'SANCTIONED','2026-01-10')",
                        (wid,))
            con.execute("INSERT INTO cost_forms (work_id, status, form, ready, submitted_at) "
                        "VALUES (%s,'submitted',%s,true,now())", (wid, Jsonb(FORM)))
        con.commit()
        yield con


def test_the_job_reads_keeps_deletes_and_site_progress_answers(db, tmp_path):
    store = capture.LocalStore(tmp_path / "store")
    vids = tmp_path / "v"
    vids.mkdir()
    base_log = film(vids / "base.mp4", scene(1))
    wall_log = film(vids / "wall.mp4", scene(1, wall=True))
    _upload(db, store, "H1", "b1", "baseline", vids / "base.mp4", base_log, date(2026, 2, 1))
    done = job.process(db, store)
    assert [d["status"] for d in done] == ["read"]
    assert not (tmp_path / "store" / "videos" / "b1.webm").exists()          # video deleted
    row = db.execute("SELECT * FROM site_visits WHERE visit_id = 'b1'").fetchone()
    assert row["video_path"] is None and row["readings"]["sealed"] is True
    assert len(row["kept"]["viewpoints"]) == 5 and row["kept"]["hashes"]
    assert (tmp_path / "store" / row["kept"]["viewpoints"]["v1"]["path"]).exists()

    # a month later: a wall at the same viewpoints
    _upload(db, store, "H1", "m1", "monthly", vids / "wall.mp4", wall_log, date(2026, 3, 1))
    # and the baseline video again, filed for the other hall
    _upload(db, store, "H2", "x1", "baseline", vids / "base.mp4", base_log, date(2026, 3, 2))
    job.process(db, store)
    m1 = db.execute("SELECT readings FROM site_visits WHERE visit_id = 'm1'").fetchone()
    assert m1["readings"]["views_match_site"] is True and m1["readings"]["change"] == "changed"
    x1 = db.execute("SELECT readings FROM site_visits WHERE visit_id = 'x1'").fetchone()
    assert x1["readings"]["reused_from"][0]["work_id"] == "H1"
    assert x1["readings"]["same_place_as"][0]["work_id"] == "H1"

    h1 = batch.with_evidence(db, [{"work_id": "H1", "status": "SANCTIONED"}])[0]
    assert not sp.assess(h1, date(2026, 3, 5)).findings
    h2 = batch.with_evidence(db, [{"work_id": "H2", "status": "SANCTIONED",
                                   "cost_form": FORM}])[0]
    codes = [f.code for f in sp.assess(h2, date(2026, 3, 5)).findings]
    assert codes[:2] == ["FOOTAGE_USED_BEFORE", "SAME_PLACE_AS_ANOTHER_WORK"]


def test_a_visit_whose_video_never_arrived_is_rejected(db, tmp_path):
    store = capture.LocalStore(tmp_path / "store")
    db.execute("INSERT INTO site_visits (visit_id, work_id, kind, status, uploaded_at) VALUES "
               "('lost','H1','monthly','uploaded',now())")
    db.commit()
    done = job.process(db, store)
    assert done[0]["status"] == "rejected" and "film the visit again" in done[0]["note"]
