"""Odd Overall (#63): per-type z values and a stored Isolation Forest scored in plain Python."""

from datetime import date

import pytest

from drishti.agents.contract import Status
from drishti.agents.outlier.agent import assess
from drishti.agents.outlier.model import Forest, OutlierStats, avg_path, features

Q = {"*": {"amount": (5.0, 5.5, 6.0), "speed": (2.0, 2.6, 3.0), "words": (1.6, 1.9, 2.2)},
     "ROAD_CC": {"amount": (5.0, 5.5, 6.0), "speed": (2.0, 2.6, 3.0), "words": (1.6, 1.9, 2.2)}}


def _tree_isolating_fast_and_costly() -> dict:
    """One hand-built tree: a record with speed z < -2 AND amount z > 2 is isolated at depth 2;
    everything else ends at depth 1 in a leaf of 200 points."""
    return {"cols": [0, 1, 2], "feature": [1, -2, 0, -2, -2], "threshold": [-2.0, 0, 2.0, 0, 0],
            "left": [2, -1, 3, -1, -1], "right": [1, -1, 4, -1, -1], "n": [256, 200, 56, 55, 1]}


def _stats(threshold=0.6) -> OutlierStats:
    forest = Forest(max_samples=256, trees=[_tree_isolating_fast_and_costly()],
                    threshold=threshold)
    return OutlierStats(version="t", quantiles=Q, threshold=3.0, forest=forest)


def _work(**kw):
    w = {"work_id": "W1", "work_type_code": "ROAD_CC", "amount": 316_000.0,
         "recommended_date": date(2024, 1, 1), "completed_date": date(2025, 1, 15),
         "description": "Construction of CC road at Sitapur village 200 m"}
    w.update(kw)
    return w


def test_features_are_logs_and_skip_what_is_missing():
    f = features(_work())
    assert set(f) == {"amount", "speed", "words"}
    assert set(features(_work(completed_date=None))) == {"amount", "words"}


def test_path_length_matches_the_isolation_forest_formula():
    assert avg_path(1) == 0 and avg_path(2) == 1
    assert avg_path(256) == pytest.approx(10.2448, abs=1e-3)


def test_an_ordinary_record_is_usual():
    r = assess(_work(), _stats())
    assert r.status == Status.ASSESSED and r.verdict == "USUAL_RECORD" and r.risk == 0


def test_costly_and_done_in_two_days_is_odd_and_named_with_this_works_numbers():
    odd = _work(amount=31_600_000.0, completed_date=date(2024, 1, 3))
    s = _stats()
    assert s.forest.score(s.vector(odd)) > s.forest.score(s.vector(_work()))
    r = assess(odd, s)
    assert r.verdict == "ODD_COMBINATION" and 0.30 <= r.risk <= 0.70
    assert "completed 2 days after recommendation" in r.headline
    assert "Rs 3.16 crore" in r.headline and "Cement concrete road" in r.headline


def test_a_new_work_type_borrows_the_schemes_statistics():
    r = assess(_work(work_type_code="SOMETHING_NEW"), _stats())
    assert r.status == Status.ASSESSED


def test_not_assessable_without_statistics_or_with_one_field():
    assert assess(_work(), None).status == Status.NOT_ASSESSABLE
    one = _work(completed_date=None, description="")
    assert assess(one, _stats()).status == Status.NOT_ASSESSABLE
