"""The Visualization Engine's trace (T092): the same answer as the pipeline, nothing private.

The page shows judges what DRISHTI does at each step. It may only show what the engines really did:
the trace's score must be the pipeline's, its arithmetic must add up, its coloured words must be the
masked description exactly, and nothing in it may hold a name, a number or an accusing word.
"""

import json
import random
from datetime import date

import pytest

from drishti.agents.contract import check_plain_language
from drishti.batch import indexes
from drishti.evaluation.stats import build_store
from drishti.evaluation.synthetic import Generator
from drishti.explain import explain
from drishti.pipeline.orchestrator import Context, assess_work
from drishti.validation.pii import mask

AS_OF = date(2026, 5, 26)
IDS = ("work_id", "code", "rule", "id", "engine")


@pytest.fixture(scope="module")
def world():
    works = Generator(seed=11, small=True).build().works
    return works, Context(stats=build_store(works), as_of=AS_OF, data=indexes(works))


def _strings(x, path=""):
    if isinstance(x, str):
        yield path, x
    elif isinstance(x, dict):
        for k, v in x.items():
            yield from _strings(v, f"{path}.{k}")
    elif isinstance(x, list):
        for i, v in enumerate(x):
            yield from _strings(v, f"{path}[{i}]")


def _private_free(trace):
    for path, s in _strings(trace):
        if path.rsplit(".", 1)[-1].split("[", 1)[0] in IDS:
            continue
        assert mask(s) == s, (path, s[:100])
        if path.endswith((".text", ".headline")):
            check_plain_language(s)


def test_the_trace_gives_the_pipelines_answer(world):
    works, ctx = world
    sample = random.Random(1).sample(works, 60)
    for w in sample:
        t = explain(w, ctx)
        a = assess_work(w, ctx)
        s = t["scoring"]
        assert s["score"] == pytest.approx(a.fused.score, abs=1e-4), w["work_id"]
        assert s["band"] == a.fused.band == t["result"]["band"]
        if s["chain"]:
            assert s["chain"][-1]["score"] == pytest.approx(s["raw"], abs=1e-4)
            scores = [c["score"] for c in s["chain"]]
            assert scores == sorted(scores)                      # each engine adds, never takes
        if not s["floor"]:
            assert s["raw"] == pytest.approx(s["score"], abs=1e-4)
        for e in s["engines"]:
            for f in e["findings"]:
                assert f["chance"] == pytest.approx(f["hit_rate"] * f["strength"], abs=1e-3)


def test_the_coloured_words_are_the_masked_description(world):
    works, ctx = world
    for w in random.Random(2).sample(works, 80):
        t = explain(w, ctx)
        assert "".join(s["t"] for s in t["reading"]["segments"]) == t["input"]["description"]
        assert t["input"]["description"] == (mask(w.get("description") or "") or "")


def test_nothing_private_or_accusing_leaves_the_trace(world):
    works, ctx = world
    w = {**works[3], "work_id": "EX", "status": "RECOMMENDED", "recommended_date": AS_OF,
         "description": "Construction of temple near Ramdev Bhagat house, contact 9061234567",
         "agency_name": "Office of Mr Mohan Lal"}
    t = explain(w, ctx)
    assert t["privacy"]["hidden"] == {"name": 1, "phone": 1, "number": 0}
    assert "Mohan" not in t["input"]["office"]
    kinds = {s["k"] for s in t["reading"]["segments"]}
    assert {"private", "not_allowed", "build"} <= kinds
    assert t["reading"]["facts"]["not_allowed"]["word"] == "temple"
    rules = next(c for c in t["checks"] if c["id"] == "compliance")["picture"]["rules"]
    assert any(r["id"] == "R07" and r["raised"] for r in rules)
    assert t["result"]["colour"] in ("RED", "AMBER")
    for x in random.Random(3).sample(works, 40):
        _private_free(explain(x, ctx))
    _private_free(t)


def test_the_picture_data_is_there_for_each_check(world):
    works, ctx = world
    t = explain({**works[7], "work_id": "EX", "status": "RECOMMENDED", "recommended_date": AS_OF},
                ctx)
    pics = {c["id"]: c["picture"] for c in t["checks"] if c["status"] == "ASSESSED"}
    assert "rules" in pics["compliance"]
    if pics.get("dup_split"):
        near = pics["dup_split"]["nearest"]
        assert pics["dup_split"]["compared"] > 0 and near
        assert [n["likeness"] for n in near] == sorted((n["likeness"] for n in near),
                                                        reverse=True)
    assert set(t["scoring"]["lines"]) == {"MEDIUM", "HIGH", "CRITICAL"}


@pytest.mark.parametrize("seed", [4, 5])
def test_odd_works_never_break_the_trace(world, seed):
    works, ctx = world
    rng = random.Random(seed)
    for i in range(60):
        w = {**rng.choice(works), "work_id": f"ODD-{i}"}
        for k in rng.sample(sorted(w), 3):
            if k != "work_id":
                w[k] = rng.choice([None, "", "x" * 3000, float("nan"), -1, "1,00,000",
                                   "2024-13-45", "मंदिर परिसर", 0])
        json.dumps(explain(w, ctx))
