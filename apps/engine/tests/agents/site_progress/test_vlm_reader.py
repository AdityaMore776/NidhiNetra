"""T156: the fine-tuned claim judge as a Site Progress reader (a fake model; no GPU in CI)."""

from __future__ import annotations

import pytest

from drishti.agents.site_progress.readers import VLMReader, work_type_of


def runner(answers: dict):
    """answers: (a_jpeg, b_jpeg) -> (verdict, prob). Records every call."""
    calls = []

    def run(a, b, wt, claim, kind):
        calls.append((a, b, wt, claim, kind))
        v, p = answers.get((a, b), ("cant_tell", 0.9))
        return {"verdict": v, "probs": {v: p}, "reason": f"{v} on {a.decode()}>{b.decode()}"}
    run.calls = calls
    return run


PHOTOS = [("before-v1", b"B1"), ("before-v2", b"B2"), ("now-v1", b"N1"), ("now-v2", b"N2"),
          ("now-v3", b"N3")]


def test_judged_only_on_views_seen_both_times():
    r = runner({})
    VLMReader(runner=r).judge(["walls up to lintel level"], PHOTOS)
    assert [(a, b) for a, b, *_ in r.calls] == [(b"B1", b"N1"), (b"B2", b"N2")]


def test_one_confident_shown_view_is_enough():
    r = runner({(b"B1", b"N1"): ("shown", 0.9), (b"B2", b"N2"): ("not_shown", 0.8)})
    out = VLMReader(runner=r).judge(["walls up to lintel level"], PHOTOS)[0]
    assert out["verdict"] == "shown" and out["reason"].startswith("shown on B1")


def test_not_shown_needs_every_view_confident():
    sure = runner({(b"B1", b"N1"): ("not_shown", 0.9), (b"B2", b"N2"): ("not_shown", 0.9)})
    assert VLMReader(runner=sure).judge(["roof slab cast"], PHOTOS)[0]["verdict"] == "not_shown"
    unsure = runner({(b"B1", b"N1"): ("not_shown", 0.9), (b"B2", b"N2"): ("not_shown", 0.4)})
    assert VLMReader(runner=unsure).judge(["roof slab cast"], PHOTOS)[0]["verdict"] == "cant_tell"
    mixed = runner({(b"B1", b"N1"): ("not_shown", 0.9), (b"B2", b"N2"): ("cant_tell", 0.9)})
    assert VLMReader(runner=mixed).judge(["roof slab cast"], PHOTOS)[0]["verdict"] == "cant_tell"


def test_an_unsure_shown_is_cant_tell():
    r = runner({(b"B1", b"N1"): ("shown", 0.5), (b"B2", b"N2"): ("shown", 0.55)})
    assert VLMReader(runner=r).judge(["roof slab cast"], PHOTOS)[0]["verdict"] == "cant_tell"


def test_without_a_before_view_only_state_claims_are_judged():
    now_only = [("now-v1", b"N1")]
    r = runner({(b"N1", b"N1"): ("shown", 0.9)})
    rd = VLMReader(runner=r)
    assert rd.judge(["community hall is already built and standing"], now_only)[0]["verdict"] \
        == "shown"
    out = rd.judge(["roof slab cast this month"], now_only)[0]
    assert out["verdict"] == "cant_tell" and "no view" in out["reason"]


def test_claim_kind_and_work_type_are_passed():
    r = runner({})
    VLMReader(runner=r, asset="Panchayat bhawan").judge(["roof cast since the last visit"],
                                                        PHOTOS)
    assert {(wt, kind) for _a, _b, wt, _c, kind in r.calls} == {("building", "period")}


@pytest.mark.parametrize("asset,wt", [("CC road from school to temple", "road"),
                                      ("Pucca nali in ward 3", "drain"),
                                      ("Community hall", "building"), ("Solar lights", "other")])
def test_work_type_from_the_asset_words(asset, wt):
    assert work_type_of(asset) == wt


def test_off_without_an_adapter(monkeypatch):
    monkeypatch.delenv("DRISHTI_VLM_ADAPTER", raising=False)
    with pytest.raises(ValueError):
        VLMReader()
