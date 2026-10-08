"""T151-T155: the GeoMGNREGA reader, the certainty check, the claim ladder and its scoring.

Every fixture is made up (no real names, places or photos). The tests hold the owner's rules of
7 Oct 2026: no edited photo in a test or calibration item; "shown" only where progress is certain;
every edit applied to both answers; headline scores on real photos only.
"""

from __future__ import annotations

import json
import random

import cv2
import numpy as np
import pytest

from drishti_vision import change, geomgnrega, vlmdata, vlmeval
from drishti_vision.vlm import TrainConfig, parse, training_items

FDC = ("https://bhuvan-fdc1.nrsc.gov.in/object/nrega_fdc/upload/photos/"
       "{s}/{m}/2024-2025/99/9901/9901001/9901001001/photo{n}_fdc_X_{t}.jpg")
P3 = FDC.format(s=3, m="2025-04", n=1, t="line_abc_8_9_13_11_4_2025")
P11 = FDC.format(s=1, m="2024-11", n=1, t="Point_def_8_58_29_25_11_2024")
P12 = FDC.format(s=1, m="2024-11", n=2, t="Point_def_8_58_29_25_11_2024")
PAGE = (
    f"<table><tr><td colspan='2'><img id='attachphoto' src='{P3}'/></td></tr>\n"
    f'<a href="#" onclick=changeImage("{P11}") >1</a>\n'
    f'<a href="#" onclick=changeImage("{P12}") >2</a>\n'
    f'<a href="#" onclick=changeImage("{P3}") >1</a>\n'
    "<tr><td>Category</td><td>Rural Connectivity</td></tr>\n"
    "<tr><td>Sub-Category</td><td>Constr of Interlocking block/tiles Roads for Comm</td></tr>\n"
    "<tr><td>Longitude/Latitude</td><td>80.10/20.20&nbsp;<a onclick=\"alert('Geo-tagged "
    "point =80.10/20.20\\nDistance from Photo 1=7.71m \\nDistance from Photo 2 =4.51m')\">"
    "Analyse</a></td></tr>\n"
    "<tr><td>Work Name</td><td>MADE UP LANE INTERLOCKING WORK</td></tr>\n"
    "<tr><td>Work Start Date</td><td>2024-04-15 00:00:00</td></tr></table>")

PROPS = {"sid": 123, "category_id": "05", "subcategory_id": "05041", "state_code": "99",
         "district_code": "9901", "block_code": "9901001", "panchayat_code": "9901001001",
         "feature_type": "line"}


def test_details_page_parsed_into_stage_photos():
    a = geomgnrega.parse_details(PAGE, PROPS)
    assert a.work_type == "road"
    assert a.subcategory.startswith("Constr of Interlocking")
    assert (a.lon, a.lat) == (80.10, 20.20)
    assert a.distances_m == {1: 7.71, 2: 4.51}
    assert [(p.stage, p.n) for p in a.photos] == [(1, 1), (1, 2), (3, 1)]
    assert a.photos[0].taken == "2024-11-25T08:58:29"
    assert a.stages() == [1, 3]


@pytest.mark.parametrize("sub,cat,want", [
    ("Construction of Community Sanitary Complex", "04", "building"),
    ("Constr of GP for community", "17", "building"),
    ("Construction of Mitti Murram Roads", "05", "road"),
    ("Construction of pucca drain", "04", "drain"),
    ("Construction of Play field", "17", "building"),          # by category; never progress
    ("Renovation of pond", "01", "other"),
    ("Roof top rain wat. har. str. in gov/panchayat bldg", "01", "other"),   # not a building
])
def test_work_type_from_sub_category(sub, cat, want):
    assert geomgnrega.work_type_of(cat, sub) == want


def test_saved_photo_is_shrunk_and_carries_no_metadata(tmp_path):
    img = np.full((3000, 2000, 3), 120, np.uint8)
    ok, buf = cv2.imencode(".jpg", img)
    out = tmp_path / "p.jpg"
    assert geomgnrega.save_photo(buf.tobytes(), out, max_side=1280)
    back = cv2.imread(str(out))
    assert max(back.shape[:2]) == 1280
    assert b"Exif" not in out.read_bytes()[:200]


def _asset(tmp_path, sid, district, wt="road", sub="Constr of Interlocking block/tiles Roads",
           ok=True):
    root = tmp_path / "photos"
    photos = []
    for s in (1, 2, 3):
        for n in (1, 2):
            f = f"mg-{sid}/s{s}_p{n}.jpg"
            (root / f).parent.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(str(root / f), np.full((120, 90, 3), 40 * s + n, np.uint8))
            photos.append({"stage": s, "n": n, "file": f})
    return {"id": f"mg-{sid}", "sid": sid, "work_type": wt, "subcategory": sub,
            "district_code": district, "photos": photos,
            "change": {"ok_13": ok, "ok_12": ok, "d11": 0.02, "d22": 0.02, "d33": 0.02}}


def _district(split: str, start: int = 0) -> str:
    for i in range(start, start + 5000):
        if vlmdata.split_of(f"D{i}") == split:
            return f"D{i}"
    raise AssertionError


def _items(tmp_path, assets, synthetic=True):
    cut = [np.dstack([np.full((40, 20, 3), 200, np.uint8), np.full((40, 20), 255, np.uint8)])]
    out = []
    rng = random.Random(0)
    for a in assets:
        out += vlmdata.mgnrega_items(a, tmp_path, "photos", "made", rng, assets, cut, synthetic)
    return out


def test_district_decides_the_split():
    assert vlmdata.split_of("9901") == vlmdata.split_of("9901")
    splits = {vlmdata.split_of(f"D{i}") for i in range(300)}
    assert splits == {"train", "calib", "test"}


def test_no_edited_photo_ever_reaches_test_or_calibration(tmp_path):
    assets = [_asset(tmp_path, 1, _district("test")), _asset(tmp_path, 2, _district("calib")),
              _asset(tmp_path, 3, _district("train")),
              _asset(tmp_path, 4, _district("test", 9000), wt="building", sub="Constr of GP")]
    items = _items(tmp_path, assets)
    held = [i for i in items if i.split in ("test", "calib")]
    assert held and all(i.real and not i.edits for i in held)
    assert any(not i.real for i in items if i.split == "train")


def test_shown_only_where_progress_is_certain(tmp_path):
    d = _district("train")
    unsure = _asset(tmp_path, 5, d, ok=False)
    play = _asset(tmp_path, 6, d, wt="building", sub="Construction of Play field", ok=True)
    items = _items(tmp_path, [unsure, play])
    assert items
    assert not [i for i in items if i.target["verdict"] == "shown"]


def test_every_edit_goes_into_both_answers(tmp_path):
    items = _items(tmp_path, [_asset(tmp_path, 7, _district("train"))])
    for edit in ("paste", "relight"):
        verdicts = {i.target["verdict"] for i in items if edit in i.edits}
        assert verdicts == {"shown", "not_shown"}, edit


def test_other_site_is_a_clearly_different_work(tmp_path):
    d = _district("train")
    items = _items(tmp_path, [_asset(tmp_path, 8, d), _asset(tmp_path, 9, d),
                              _asset(tmp_path, 10, d, wt="building", sub="Constr of GP")])
    for it in [i for i in items if i.trick == "other_site"]:
        b_site = it.image_b.split("/")[1]
        a_type = it.work_type
        assert b_site != it.site
        assert {"mg-8": "road", "mg-9": "road", "mg-10": "building"}[b_site] != a_type
        assert it.target["verdict"] == "cant_tell"


def test_no_progress_pairs_are_never_shown(tmp_path):
    items = _items(tmp_path, [_asset(tmp_path, 11, _district("train"))])
    for it in items:
        if it.trick in vlmdata.NO_PROGRESS_TRICKS and it.claim_kind == "period":
            assert it.target["verdict"] == "not_shown"


def test_real_only_switch_makes_no_edits(tmp_path):
    items = _items(tmp_path, [_asset(tmp_path, 12, _district("train"))], synthetic=False)
    assert items and all(i.real for i in items)


def test_certainty_needs_change_beyond_the_assets_own_noise():
    class Fake:
        def __init__(self, vecs):
            self.vecs = vecs

        def __call__(self, path):
            return self.vecs[path.name]

    def unit(v):
        v = np.array(v, float)
        return v / np.linalg.norm(v)

    asset = {"photos": [{"stage": s, "n": n, "file": f"s{s}_p{n}.jpg"}
                        for s in (1, 2, 3) for n in (1, 2)]}
    from pathlib import Path
    big = Fake({"s1_p1.jpg": unit([1, 0, 0]), "s1_p2.jpg": unit([1, .05, 0]),
                "s2_p1.jpg": unit([.5, 1, 0]), "s2_p2.jpg": unit([.5, 1, .05]),
                "s3_p1.jpg": unit([0, 1, 0]), "s3_p2.jpg": unit([0, 1, .05])})
    assert change.asset_change(asset, Path("."), big)["ok_13"]
    small = Fake({k: unit([1, 0.02 * i, 0]) for i, k in enumerate(big.vecs)})
    assert not change.asset_change(asset, Path("."), small)["ok_13"]


@pytest.mark.parametrize("text,want", [
    ('```json\n{"verdict": "shown", "reason": "x"}\n```', "shown"),
    ('{"verdict": "not shown"}', "not_shown"),
    ('{"verdict": "cannot tell"}', "cant_tell"),
    ('{"verdict": "maybe"}', None),
    ("no json here", None),
])
def test_answers_are_parsed_forgivingly(text, want):
    got = parse(text)
    assert (got["verdict"] if got else None) == want


def test_edited_items_are_capped_in_training(tmp_path):
    rows = ([{"split": "train", "real": True, "id": i} for i in range(80)]
            + [{"split": "train", "real": False, "id": 100 + i} for i in range(80)]
            + [{"split": "test", "real": True, "id": 200 + i} for i in range(10)])
    p = tmp_path / "items.jsonl"
    p.write_text("".join(json.dumps(r) + "\n" for r in rows))
    cfg = TrainConfig(base="x", items=str(p), root=".", out=".")
    got = training_items(str(p), cfg)
    assert all(r["split"] == "train" for r in got)
    edited = sum(not r["real"] for r in got)
    assert edited / len(got) <= 0.2 + 1e-9
    cfg.real_only = True
    assert all(r["real"] for r in training_items(str(p), cfg))


def test_headline_counts_real_photos_only():
    rows = [{"site": "a", "trick": "none", "real": True, "truth": "shown", "pred": "shown",
             "conf": .9, "seconds": 1.0},
            {"site": "b", "trick": "view", "real": True, "truth": "not_shown", "pred": "shown",
             "conf": .6, "seconds": 1.0},
            {"site": "c", "trick": "staged", "real": False, "truth": "not_shown",
             "pred": "not_shown", "conf": .9, "seconds": 1.0}]
    s = vlmeval.score(rows)
    h = s["headline_real_only"]
    assert h["n"] == 2
    assert h["fooled_rate"] == 1.0          # the real view pair was called shown
    assert s["edited_items_apart"]["n"] == 1
    assert vlmeval.macro_f1(["shown", "not_shown"], ["shown", "not_shown"]) == 1.0


def test_mcnemar_compares_two_judges_on_the_same_items():
    def rows(right):
        return [{"id": str(k), "truth": "shown", "pred": "shown" if r else "not_shown"}
                for k, r in enumerate(right)]
    a = rows([True] * 20 + [False] * 20)
    b = rows([True] * 20 + [True] * 12 + [False] * 8)          # b fixes 12, breaks none
    m = vlmeval.mcnemar(a, b)
    assert (m["n"], m["only_a_right"], m["only_b_right"]) == (40, 0, 12)
    assert m["p"] < 0.001
    assert vlmeval.mcnemar(a, a)["p"] == 1.0
    assert vlmeval.mcnemar(a, rows([False] * 3))["n"] == 3     # shared items only


def test_flagship_gets_full_resolution_photos_unless_asked_for_the_judges_view(tmp_path):
    """Owner (8 Oct 2026): each model at its best; the flagship is not held to the judge's
    512 px."""
    import base64
    import io

    from PIL import Image

    from drishti_vision import flagship_other, vlm

    def size(**kw):
        return Image.open(io.BytesIO(base64.b64decode(flagship_other._jpeg_b64(p, **kw)))).size
    p = tmp_path / "a.jpg"
    Image.new("RGB", (2000, 1500), (90, 120, 30)).save(p)
    assert size() == (2000, 1500)
    assert size(max_side=vlm.MAX_SIDE) == vlm.load_image(p).size == (512, 384)


def test_flagship_waits_on_rate_limits_and_stops_on_the_daily_quota():
    from drishti_vision import flagship_other as fo
    minute = ('{"error": {"code": 429, "status": "RESOURCE_EXHAUSTED", "details": ['
              '{"@type": "type.googleapis.com/google.rpc.QuotaFailure", "violations": ['
              '{"quotaId": "GenerateRequestsPerMinutePerProjectPerModel-FreeTier"}]},'
              '{"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": "17s"}]}}')
    day = minute.replace("PerMinute", "PerDay")
    assert fo.retry_after(minute) == 17.0 and not fo.daily_quota(minute)
    assert fo.daily_quota(day)


def test_flagship_examples_come_from_training_only_and_cover_every_answer(tmp_path):
    from drishti_vision import flagship_other as fo
    a = _asset(tmp_path, 71, _district("train"))
    b = _asset(tmp_path, 72, _district("train"), wt="building",
               sub="Construction of Anganwadi Centre")
    t = _asset(tmp_path, 73, _district("test"))
    items = _items(tmp_path, [a, b, t], synthetic=False)
    ex = fo.few_shot_examples(items, k=4, seed=0)
    assert all(i.split == "train" and i.real for i in ex)
    assert {i.target["verdict"] for i in ex} == {"shown", "not_shown", "cant_tell"}
    assert fo.few_shot_examples(items, k=4, seed=0) == ex                 # fixed for every item


def test_batch_requests_ask_exactly_what_the_live_judge_asks(tmp_path):
    from drishti_vision import flagship_batch, flagship_other
    a = _asset(tmp_path, 81, _district("test"))
    items = _items(tmp_path, [a], synthetic=False)
    line = json.loads(flagship_batch.request_line(items[0], tmp_path))
    assert line["key"] == items[0].id
    req = line["request"]
    assert req["system_instruction"]["parts"][0]["text"] == vlmdata.SYSTEM
    assert req["contents"][-1]["parts"] == flagship_other._gemini_turn(items[0].__dict__, tmp_path)
    assert req["generationConfig"]["temperature"] == 0


def test_batch_answers_become_the_same_rows_as_live_answers(tmp_path):
    from drishti_vision import flagship_batch
    a = _asset(tmp_path, 82, _district("test"))
    it = _items(tmp_path, [a], synthetic=False)[0]
    ans = {"same_place": "yes", "stage_A": "not started", "stage_B": "complete",
           "permanent_change": "yes", "verdict": "shown", "reason": "built"}
    resp = {"key": it.id, "response": {
        "candidates": [{"content": {"parts": [{"text": "thinking...", "thought": True},
                                              {"text": json.dumps(ans)}]}}],
        "usageMetadata": {"promptTokenCount": 2300, "candidatesTokenCount": 90,
                          "thoughtsTokenCount": 300}, "modelVersion": "gemini-x"}}
    rows = flagship_batch.rows_from_results([json.dumps(resp)], [it])
    assert rows[0]["pred"] == "shown" and rows[0]["usage"] == {"in": 2300, "out": 390}
    assert rows[0]["served_by"] == "gemini-x (batch)"
    bad = {"key": it.id, "error": {"code": 500, "message": "x"}}
    assert flagship_batch.rows_from_results([json.dumps(bad)], [it]) == []


def test_rl_practice_aims_at_the_weak_tricks():
    from drishti_vision import vlmrl
    items = ([{"id": f"s{k}", "trick": "swapped", "split": "train"} for k in range(10)]
             + [{"id": f"b{k}", "trick": "busy", "split": "train"} for k in range(100)])
    got = vlmrl.focus_prompts(items, ("swapped",), keep_other=0.5, seed=0)
    ids = [r["id"] for r in got]
    assert sum(i.startswith("s") for i in ids) == 10          # every focused item
    assert sum(i.startswith("b") for i in ids) == 5            # plus half as many others
    assert len(set(ids)) == len(ids)


def test_rewards_punish_being_fooled_most():
    from drishti_vision.vlmrl import reward
    item = {"trick": "busy", "target": {"verdict": "not_shown", "stage_A": "unknown",
                                        "stage_B": "unknown"}}
    fooled = reward('{"verdict": "shown"}', item)["total"]
    right = reward('{"verdict": "not_shown"}', item)["total"]
    unsure = reward('{"verdict": "cant_tell"}', item)["total"]
    unreadable = reward("no answer", item)["total"]
    assert fooled < unreadable < unsure < right
    prog = {"trick": "none", "target": {"verdict": "shown", "stage_A": "not started",
                                        "stage_B": "complete"}}
    full = reward('{"verdict": "shown", "stage_A": "not started", "stage_B": "complete"}', prog)
    half = reward('{"verdict": "shown", "stage_A": "not started", "stage_B": "work under way"}',
                  prog)
    assert full["total"] > half["total"] > 0


@pytest.mark.parametrize("sub,ok", [
    ("Constr of Interlocking block/tiles Roads for Comm", True),
    ("Constr of Anganwadi for community", True),
    ("Constr of GP for community", True),
    ("Constr of CmpOnd wall for gov schools for Comm", True),
    ("Constr of Kharanja (brick/stone) Roads for Comm", True),
    ("Construction of Mitti Murram Roads for Community", False),     # earth can look the same
    ("Renovtion of Community Ponds for Comm", False),
    ("Repair-maint Interlocking block/tiles roads-Comm", False),
    ("Construction of Play field for Community", False),
    ("Constr of Water Absorption Trench Trench for Comm", False),
    # a pit beside a building that was already there (7 of 7 such test assets, by eye, 8 Oct)
    ("Roof top rain wat. har. str. in gov/panchayat bldg", False),
])
def test_progress_only_for_unmistakable_structures(sub, ok):
    assert vlmdata.structural({"subcategory": sub}) is ok


def test_a_schools_compound_wall_is_a_wall():
    assert geomgnrega.work_type_of("17", "Constr of CmpOnd wall for gov schools for Comm") \
        == "boundary_wall"


def test_finished_claims_only_where_a_photo_can_decide(tmp_path):
    d = _district("train")
    grove = _asset(tmp_path, 13, d, wt="other", sub="Constr of Water Absorption Trench",
                   ok=True)
    items = _items(tmp_path, [grove], synthetic=False)
    assert items
    assert not [i for i in items if i.claim_kind == "reached"]
    assert {i.trick for i in items} <= {"view", "busy", "double_claim", "other_site"}


def test_claims_read_naturally():
    assert vlmdata.claim_text(vlmdata.CLAIM_STARTED_PERIOD, "road",
                              "Constr of Interlocking block/tiles Roads", "en") \
        == "Work started on the interlocking tile road since the last visit"
    assert vlmdata.claim_text(vlmdata.CLAIM_DONE, "other", "", "en") == "Site work completed"


def test_training_has_other_places_of_the_same_type(tmp_path):
    """The 4B tuned without these called a photo of ANOTHER finished road 'shown' 38 times in 44
    (8 Oct 2026): it had only ever seen other places of another work type."""
    d = _district("train")
    x, y = _asset(tmp_path, 41, d), _asset(tmp_path, 42, d)
    y["block_code"] = "elsewhere"
    near = _asset(tmp_path, 43, d)                         # same block as x: never used
    t1, t2 = _asset(tmp_path, 44, _district("test")), _asset(tmp_path, 45, _district("test"))
    t2["block_code"] = "elsewhere"
    items = _items(tmp_path, [x, y, near, t1, t2])
    same = [i for i in items if i.trick == "other_site_same"]
    assert {(i.site, i.image_b.split("/")[-2]) for i in same if i.site == x["id"]} \
        == {(x["id"], y["id"])}
    assert all(i.split == "train" and i.real and i.target["verdict"] == "cant_tell"
               and i.target["same_place"] == "no" for i in same)


def test_a_bigger_harvest_leaves_earlier_items_as_they_were(tmp_path):
    from drishti_vision import eyecheck
    d = _district("test")
    first = [_asset(tmp_path, 51 + k, d) for k in range(4)]
    for k, a in enumerate(first):
        a["block_code"] = f"b{k}"
    more = first + [_asset(tmp_path, 61 + k, _district("train")) for k in range(3)]
    p1, p2 = tmp_path / "a1.jsonl", tmp_path / "a2.jsonl"
    p1.write_text("\n".join(json.dumps(a) for a in first))
    p2.write_text("\n".join(json.dumps(a) for a in more))
    k1 = {eyecheck.key(i) for i in vlmdata.build_mgnrega(p1, tmp_path, "photos", "made", [],
                                                         synthetic=False)}
    k2 = {eyecheck.key(i) for i in vlmdata.build_mgnrega(p2, tmp_path, "photos", "made", [],
                                                         synthetic=False)}
    assert k1 <= k2


def test_same_type_other_site_probe(tmp_path):
    d = _district("test")
    x = _asset(tmp_path, 31, d)                        # a road, not yet certain to be finished
    x["change"]["ok_13"] = False
    y = _asset(tmp_path, 32, d)                        # a finished road elsewhere in the district
    y["block_code"] = "elsewhere"
    near = _asset(tmp_path, 33, d)                     # a finished road in the same block
    b = _asset(tmp_path, 34, d, wt="building", sub="Construction of Anganwadi Centre")
    t = _asset(tmp_path, 35, _district("train"))       # training photos never reach a probe
    t["block_code"] = "far"
    items = vlmdata.same_type_other_site([x, y, near, b, t], "gov/mgnrega/photos",
                                         ("test",), random.Random(0), per_asset=3)
    pairs = {(i.site, i.image_b.split("/")[-2]) for i in items}
    # B: a finished road (certain), another block, same split; never the unfinished x, the
    # building, or a training photo
    assert pairs == {(x["id"], y["id"]), (y["id"], near["id"]), (near["id"], y["id"])}
    assert all(i.split == "probe" and i.trick == "other_site_same" and i.real
               and i.target["verdict"] == "cant_tell" and "/s1_" in i.image_a
               and "/s3_" in i.image_b for i in items)


def test_same_moment_items_need_the_same_scene(tmp_path):
    a = _asset(tmp_path, 14, _district("train"))
    a["change"].update({"d11": 0.4, "d22": 0.4, "d33": 0.4})      # far-apart views
    items = _items(tmp_path, [a], synthetic=False)
    assert not [i for i in items if i.trick in ("view", "busy", "double_claim")
                and i.claim_kind == "period"]


def _timelapse(tmp_path, pairs, T=20, unknown=0.0, rgb=(200, 40, 10), lo=0.1):
    """A made-up `build --keep-raw` folder: one shot of T plain frames and the hindsight
    teacher's pairs [(a, b, label, kind, progress share)]; `unknown` of every pair's patches
    could not be judged; `lo` is the shot's own noise level (hindsight.calibrate)."""
    d = tmp_path / "built"
    (d / "labels").mkdir(parents=True)
    (d / "shots").mkdir()
    (d / "shots.jsonl").write_text(json.dumps({"shot_id": "s0", "split": "test", "lo": lo,
                                               "work_type": "building"}) + "\n")
    raw = np.zeros((T, 24, 32, 3), np.uint8)
    raw[...] = rgb                                       # RGB, as frames.read_video gives
    np.savez(d / "shots" / "s0.npz", raw=raw, activity=np.zeros((T, 4, 4), np.float16))
    n = 100
    pts = []
    for _, _, _, _, share in pairs:
        p = np.zeros(n, np.int8)
        p[: round(unknown * n)] = -1
        p[round(unknown * n): round(unknown * n) + round(share * n)] = 1
        pts.append(p.reshape(10, 10))
    np.savez(d / "labels" / "s0.npz", a=np.array([p[0] for p in pairs]),
             b=np.array([p[1] for p in pairs]), label=np.array([p[2] for p in pairs]),
             kind=np.array([p[3] for p in pairs]), patches=np.stack(pts))
    return vlmdata.timelapse_items(d, tmp_path, "frames", random.Random(0), per_shot=50)


def test_timelapse_frames_keep_their_colours(tmp_path):
    items = _timelapse(tmp_path, [(0, 2, 0, 0, 0.0)])
    img = cv2.imread(str(tmp_path / items[0].image_a))        # BGR
    assert img[..., 2].mean() > 150 and img[..., 0].mean() < 60   # red stays red


def test_timelapse_no_progress_needs_most_of_the_view_judged(tmp_path):
    assert _timelapse(tmp_path / "a", [(0, 2, 0, 0, 0.0)], unknown=0.1)
    assert not _timelapse(tmp_path / "b", [(0, 2, 0, 0, 0.0)], unknown=0.4)


def test_timelapse_no_progress_never_spans_real_work(tmp_path):
    items = _timelapse(tmp_path, [(4, 12, 1, 0, 0.3), (0, 15, 0, 0, 0.0), (16, 18, 0, 0, 0.0)])
    nop = {(i.image_a[-8:-4], i.image_b[-8:-4]) for i in items
           if i.target["verdict"] == "not_shown" and i.trick != "swapped"}
    assert nop == {("f016", "f018")}


def test_timelapse_shots_from_a_shaky_camera_give_no_items(tmp_path):
    items = _timelapse(tmp_path, [(0, 2, 0, 0, 0.0)], lo=0.6)
    assert not items


def test_eye_checks_follow_the_pair_not_the_position(tmp_path):
    from drishti_vision import eyecheck
    items = _timelapse(tmp_path, [(0, 2, 0, 0, 0.0), (4, 6, 0, 0, 0.0), (8, 10, 0, 0, 0.0)])
    bad, good = items[0], items[1]
    p = tmp_path / "checks.jsonl"
    p.write_text(json.dumps({"checked_keys": [eyecheck.key(good), eyecheck.key(bad)],
                             "wrong_keys": [eyecheck.key(bad)]}) + "\n")
    kept, info = eyecheck.apply(list(reversed(items)), p)      # order no longer matters
    assert bad.id not in {i.id for i in kept} and len(kept) == 2
    assert {i.id: i.label_check for i in kept}[good.id] == "eye"
    assert info["wrong"] == 1
    old = good.__class__(**{**good.__dict__, "image_a": "vlm/v4/frames/x/f001.jpg",
                            "image_b": "vlm/v4/frames/x/f002.jpg"})
    new = good.__class__(**{**good.__dict__, "image_a": "vlm/v5/frames/x/f001.jpg",
                            "image_b": "vlm/v5/frames/x/f002.jpg"})
    assert eyecheck.key(old) == eyecheck.key(new)              # same frames, another version


def test_timelapse_pairs_are_not_repeated(tmp_path):
    items = _timelapse(tmp_path, [(0, 2, 0, 0, 0.0), (0, 2, 0, 1, 0.0)])
    assert len(items) == 1


def test_jitter_makes_twin_photos_differ_but_keeps_the_scene():
    from PIL import Image

    from drishti_vision.vlm import jitter
    rng = random.Random(0)
    base = Image.fromarray(np.tile(np.linspace(0, 255, 200, dtype=np.uint8), (150, 1))[..., None]
                           .repeat(3, 2))
    a, b = jitter(base, rng, p=1.0), jitter(base, rng, p=1.0)
    assert a.size != b.size or np.abs(np.asarray(a, int) - np.asarray(b, int)).mean() > 1
    assert min(a.size) >= 0.7 * min(base.size) - 1
