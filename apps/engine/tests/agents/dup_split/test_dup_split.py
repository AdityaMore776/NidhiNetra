from datetime import date

import pytest

from drishti.agents.contract import Status
from drishti.agents.dup_split.agent import assess


def _pair(kind="after_completed", other="W0", score=0.9):
    return {"other": other, "kind": kind, "score": score, "gap_days": 400,
            "other_amount": 480000.0, "this_is_later": True}


def _group(kind="same_site_split", under=False):
    return {"group_id": "G00001", "kind": kind, "size": 3, "total": 1488000.0,
            "under_limit": under, "shared_place": "sapti", "days": 12,
            "others": ["W2", "W3"]}


def _work(**sig):
    return {"work_id": "W1", "amount": 496000.0, "recommended_date": date(2023, 5, 1),
            "description": "CC road at Sapti village from temple to school",
            "signals": {"dup_split": sig} if sig else {}}


def test_funded_again_after_completion_is_the_strongest_case():
    r = assess(_work(pairs=[_pair("while_open", "W9"), _pair("after_completed")]), True)
    assert r.status == Status.ASSESSED and r.verdict == "FUNDED_AGAIN_AFTER_COMPLETION"
    assert r.risk == pytest.approx(0.85)
    assert "W0" in r.headline and "that work had already been completed" in r.headline
    assert [f.code for f in r.findings] == ["FUNDED_AGAIN_AFTER_COMPLETION",
                                            "REPEATED_WHILE_OPEN"]


def test_the_earlier_work_of_a_pair_is_worded_from_its_own_side():
    p = _pair() | {"this_is_later": False}
    r = assess(_work(pairs=[p]), True)
    assert "400 days after this one" in r.headline
    assert "this work had already been completed" in r.headline


def test_a_group_on_one_day_says_so():
    r = assess(_work(group=_group() | {"days": 0}), True)
    assert "on the same day" in r.headline and "within 0 days" not in r.headline


def test_split_under_the_limit_gets_the_bonus_and_carries_its_group_id():
    r = assess(_work(pairs=[], group=_group(under=True)), True)
    assert r.verdict == "SPLIT_AT_ONE_SITE" and r.risk == pytest.approx(0.80)
    assert r.evidence["group_id"] == "G00001"
    assert "sapti" in r.headline and "between Rs 4 and 5 lakh" in r.headline
    assert "W2, W3" in r.headline


def test_bulk_order_is_a_mild_signal():
    r = assess(_work(pairs=[], group=_group("bulk_order")), True)
    assert r.verdict == "BULK_ORDER" and r.risk == pytest.approx(0.35)


def test_staged_pairs_and_unknown_kinds_are_ignored():
    r = assess(_work(pairs=[_pair("staged")], group=None), True)
    assert r.verdict == "NO_REPEAT_FOUND" and r.risk == 0.0 and not r.findings


def test_compared_work_with_no_links_is_assessed_clean():
    r = assess(_work(), True)
    assert r.status == Status.ASSESSED and r.verdict == "NO_REPEAT_FOUND"


def test_not_built_or_uncomparable_is_not_assessable():
    assert assess(_work(pairs=[_pair()]), False).status == Status.NOT_ASSESSABLE
    for bad in ({"description": "-"}, {"recommended_date": None}, {"amount": 0}):
        w = _work() | bad
        assert assess(w, True).status == Status.NOT_ASSESSABLE
