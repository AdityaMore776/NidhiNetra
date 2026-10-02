"""The engines in a random environment: malformed records, any order, any case, run twice.

Real records arrive with empty fields, impossible dates, scripts the readers do not know, sums of
zero or crores, and works filed in any order. None of that may crash an engine (a crash becomes an
ERROR result, which this test forbids), break the contract (risks in 0..1, plain language, parts
adding up to the score), or make the answer depend on things that carry no evidence: the order the
works were loaded in, whether a clerk typed in capitals, or whether a loader handed a date over as
text. Damaged rows inside the corpus may not stop the indexes or the statistics built from it.
"""

import json
import random
from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest

from drishti.agents.contract import Status
from drishti.batch import indexes
from drishti.evaluation.stats import build_store
from drishti.evaluation.synthetic import Generator
from drishti.pipeline.orchestrator import Context, assess_work

AS_OF = date(2026, 5, 26)
TEXTS = ["", " ", "NA", "Letter as per attached", "????", "मंदिर परिसर में शेड निर्माण",
         "கோவில் வளாகத்தில் கொட்டகை", "Construction of CC road 0 mtr", "x" * 2000,
         "Construction of CC road from A to B part-0", "1 no. high mast light",
         "Repair of hall", "चार्ज 9876543210 पर संपर्क करें", "road;DROP TABLE works;--",
         "Construction of temple", "à la carte \u0000 ​ zero width", "50 nos 50 nos 50 nos"]
TYPES = [None, "", "ROAD_CC", "COMMUNITY_HALL", "STREET_LIGHT", "NOT_A_TYPE", "OTHER",
         "VEHICLE", "BOREWELL"]
STATUSES = [None, "", "RECOMMENDED", "SANCTIONED", "COMPLETED", "REJECTED", "completed"]


@pytest.fixture(scope="module")
def world():
    corpus = Generator(seed=7, small=True).build()
    stats = build_store(corpus.works)
    return corpus, Context(stats=stats, as_of=AS_OF, data=indexes(corpus.works))


def _random_work(rng: random.Random, i: int) -> dict:
    def maybe_date():
        return rng.choice([None, AS_OF - timedelta(days=rng.randint(-400, 3000))])
    return {"work_id": f"RAND-{i}", "description": rng.choice(TEXTS),
            "work_type_code": rng.choice(TYPES), "status": rng.choice(STATUSES),
            "amount": rng.choice([None, 0, -5, 1, 499_999, 500_000, 1e9, 4.9e5, 1234.5]),
            "recommended_date": maybe_date(), "completed_date": maybe_date(),
            "sanction_date": maybe_date(), "district_lgd": rng.choice([None, "", "101", "999"]),
            "state_lgd": rng.choice([None, "10", "99"]), "agency_name": rng.choice(
                [None, "", "Block Development Officer X", "Unknown office"]),
            "mp_name": rng.choice([None, "LS Member 101-18"]),
            "term": rng.choice([None, "17th Lok Sabha", "18th Lok Sabha", "1st Lok Sabha"]),
            "house": rng.choice([None, "Lok Sabha", "Rajya Sabha"]),
            "is_outside_constituency": rng.choice([None, False, True]),
            "quantity": rng.choice([None, 0, 120]), "quantity_unit": rng.choice([None, "m", "km"])}


def _check(a):
    assert 0.0 <= a.fused.score <= 1.0
    assert sum(p.contribution for p in a.fused.parts) == pytest.approx(a.fused.score, abs=1e-9)
    for r in a.agents:
        assert r.status != Status.ERROR, (r.agent, r.limitations)
        assert 0.0 <= r.risk <= 1.0
        assert all(0.0 <= f.risk <= 1.0 for f in r.findings)
    json.dumps(a.to_row(), default=str)


def test_malformed_records_never_crash_an_engine(world):
    _corpus, ctx = world
    rng = random.Random(20261002)
    for i in range(400):
        _check(assess_work(_random_work(rng, i), ctx))


def _without_timing(row: dict) -> str:
    """The row as JSON, without the run-time each engine took (wall-clock, not evidence)."""
    for r in row["agents"]:
        r.pop("duration_ms", None)
    return json.dumps(row, default=str, sort_keys=True)


def test_the_same_work_gives_the_same_answer_twice(world):
    corpus, ctx = world
    for w in corpus.works[:150]:
        a, b = assess_work(w, ctx).to_row(), assess_work(w, ctx).to_row()
        assert _without_timing(a) == _without_timing(b)


def test_the_order_works_are_loaded_in_changes_nothing(world):
    corpus, ctx = world
    shuffled = list(corpus.works)
    random.Random(3).shuffle(shuffled)
    other = Context(stats=build_store(shuffled), as_of=AS_OF, data=indexes(shuffled))
    for w in corpus.works[:300]:
        a, b = assess_work(w, ctx), assess_work(w, other)
        assert a.fused.band == b.fused.band
        assert a.fused.score == pytest.approx(b.fused.score)


def _loose(rng: random.Random, w: dict) -> dict:
    """The same work as a loader that keeps fewer types would hand it over: dates as ISO,
    day-first or datetime values, the amount as Decimal or grouped text, codes as numbers."""
    out = dict(w)
    for k in ("recommended_date", "completed_date", "sanction_date"):
        d = w.get(k)
        if isinstance(d, date):
            out[k] = rng.choice([d.isoformat(), d.strftime("%d/%m/%Y"),
                                 datetime(d.year, d.month, d.day, 11, 5)])
    if isinstance(w.get("amount"), float):
        out["amount"] = rng.choice([Decimal(f"{w['amount']:.2f}"), f"{w['amount']:,.2f}"])
    for k in ("district_lgd", "state_lgd"):
        if (w.get(k) or "").isdigit():
            out[k] = int(w[k])
    return out


def test_a_loosely_typed_corpus_gives_the_same_answers(world):
    """records.work reads every column once: the indexes, the statistics and the engines must
    give a typed record and its loosely typed twin the same answer, finding for finding."""
    corpus, ctx = world
    rng = random.Random(11)
    loose = [_loose(rng, w) for w in corpus.works]
    other = Context(stats=build_store(loose), as_of=AS_OF, data=indexes(loose))
    for w, t in zip(corpus.works[:300], loose[:300], strict=True):
        a, b = assess_work(w, ctx), assess_work(t, other)
        assert a.fused.band == b.fused.band, w["work_id"]
        assert a.fused.score == pytest.approx(b.fused.score), w["work_id"]
        assert sorted((r.agent, f.code) for r in a.agents for f in r.findings) == \
            sorted((r.agent, f.code) for r in b.agents for f in r.findings)


def _damaged(rng: random.Random, w: dict, i: int) -> dict:
    """A work with one to four columns spoiled the ways real loads spoil them."""
    out = {**w, "work_id": f"DAMAGED-{i}"}
    for k in rng.sample(sorted(w), rng.randint(1, 4)):
        if k == "work_id":
            continue
        out[k] = rng.choice([None, float("nan"), "", 101, "2024-13-45", "01/02/2024",
                             datetime(2024, 1, 1, 9, 0), Decimal("-1"), "1,00,000", -1, 0])
    return out


def test_damaged_rows_in_the_corpus_never_stop_the_indexes_or_the_statistics(world):
    """One row the index builders could not read used to stop the whole batch (found by
    fuzzing, 2 Oct 2026): a NaN in a text column, a code as a number, a datetime, '1,00,000'."""
    corpus, _ctx = world
    rng = random.Random(5)
    damaged = [_damaged(rng, rng.choice(corpus.works), i) for i in range(300)]
    works = corpus.works + damaged
    ctx = Context(stats=build_store(works), as_of=AS_OF, data=indexes(works))  # must not raise
    for w in damaged:
        _check(assess_work(w, ctx))


def test_capitals_change_no_finding(world):
    corpus, ctx = world
    for w in corpus.works[:300]:
        a = assess_work(w, ctx)
        b = assess_work({**w, "description": (w["description"] or "").upper()}, ctx)
        codes = {(r.agent, f.code) for r in a.agents for f in r.findings if f.risk > 0}
        upper = {(r.agent, f.code) for r in b.agents for f in r.findings if f.risk > 0}
        # Duplicate & Split compares a work with the index, which holds the original wording,
        # so a re-typed copy is a new record; every other engine must read the two alike
        assert {c for c in codes if c[0] != "dup_split"} == \
            {c for c in upper if c[0] != "dup_split"}, w["description"]
