"""A quality gate in CI: the engines on two small synthetic countries they have never seen.

The full measurement is data/trial/synthetic_eval.py (three ~19,000-work countries) and
data/trial/dashboard_trial.py (40,935 real works read by eye). This gate is the same pipeline on
two small seeded countries (about 1,500 works each, a few seconds), so a change that stops an
engine finding a planted problem, or makes it flag a look-alike, fails a pull request instead of
reaching the live queue. Thresholds sit below what the engines reach on 2 Oct 2026; they are
floors against regression, not targets.
"""

import pytest

from drishti.evaluation.harness import run, summarise
from drishti.evaluation.synthetic import Generator

SEEDS = (1, 2)


@pytest.fixture(scope="module")
def report(monkeypatch_module):
    rows = []
    for seed in SEEDS:
        r, _ = run(Generator(seed=seed, small=True).build())
        rows += r
    return summarise(rows)


@pytest.fixture(scope="module")
def monkeypatch_module():
    mp = pytest.MonkeyPatch()
    mp.setenv("DRISHTI_FUSION", "v3")
    yield mp
    mp.undo()


def _k(report, kind):
    return report["kinds"][kind]


@pytest.mark.parametrize("kind,meant", [
    ("RULE_TEMPLE", 0.75), ("RULE_DATES_IMPOSSIBLE", 1.0), ("RULE_OUTSIDE_CEILING", 1.0),
    ("RULE_BIG_VAGUE", 1.0), ("SPLIT_SAME_SITE", 0.8), ("SPLIT_STRETCHES", 0.8),
    ("REPAIR_SOON_AFTER_BUILT", 0.5), ("OFFICE_PRICES_AT_LIMIT", 0.8),
    ("COST_SMALL_SCOPE_X10", 0.5)])
def test_planted_problems_are_found_by_the_engine_meant_for_them(report, kind, meant):
    assert _k(report, kind)["meant_code_fired"] >= meant


@pytest.mark.parametrize("kind", ["RULE_OUTSIDE_CEILING", "RULE_BIG_VAGUE", "RULE_TEMPLE"])
def test_one_well_measured_rule_breach_reaches_the_review_queue(report, kind):
    assert _k(report, kind)["queued"] == 1.0


@pytest.mark.parametrize("kind,most", [
    ("HN_LANDMARK_TEMPLE", 0.0), ("HN_SCHOOL_NAMED_MANDIR", 0.0), ("HN_OPPOSITE_SIDES", 0.0),
    ("HN_BATCH_DIFFERENT_VILLAGES", 0.05), ("HN_REPAIR_ELSEWHERE", 0.0)])
def test_look_alikes_are_left_alone(report, kind, most):
    assert _k(report, kind)["meant_code_fired"] <= most


def test_the_queue_is_mostly_planted_problems_and_ordinary_works_stay_out(report):
    assert report["queue_precision"] >= 0.75
    assert report["background_queued"] <= 0.005
    assert _k(report, "HN_BULK_ENTRY_BACKFILL")["queued"] <= 0.1
