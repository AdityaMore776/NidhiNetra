import sys
import textwrap
from datetime import date

import pytest

from drishti.agents import registry
from drishti.agents.contract import Status
from drishti.agents.registry import CORE, EngineSpec, canonical_id, discover
from drishti.agents.statistical.cohort import StatsStore
from drishti.pipeline import orchestrator
from drishti.pipeline.orchestrator import Context, assess_work


@pytest.fixture()
def ctx():
    stats = StatsStore.from_rows(
        cohorts=[{"level": "type", "work_type_code": "ROAD_CC", "key": "", "n": 1000,
                  "p10": 4.9, "p50": 5.2, "p90": 5.5, "sd": 0.2}],
        durations=[], unit_models=[])
    return Context(stats=stats, as_of=date(2026, 5, 26))


def _work(**kw):
    w = {"work_id": "W1", "work_type_code": "ROAD_CC", "district_lgd": "1", "state_lgd": "2",
         "district_name": "X", "amount": 158_000.0, "description": "CC road in village Y",
         "status": "SANCTIONED", "recommended_date": date(2026, 1, 1), "completed_date": None,
         "quantity": None, "quantity_unit": None, "is_outside_constituency": False}
    w.update(kw)
    return w


def test_core_slots_come_first_in_blueprint_order():
    ids = [e.id for e in discover()]
    assert ids[:4] == ["compliance", "statistical", "dup_split", "delay"]


def test_blueprint_weights_without_the_outlier_slot():
    # the blueprint's 0.10 outlier slot became Guideline Compliance R12/R13 (T053)
    assert sum(e.weight for e in CORE) == pytest.approx(0.90)


def test_statistical_folder_is_discovered_as_built():
    spec = {e.id: e for e in discover()}["statistical"]
    assert spec.assess is not None and spec.weight == pytest.approx(0.20)


def test_missing_engine_reports_not_built(ctx, monkeypatch):
    engines = tuple(EngineSpec(e.id, e.name, e.question, None, e.weight, e.order)
                    if e.id == "delay" else e for e in registry.engines())
    monkeypatch.setattr(registry, "_CACHE", engines)
    a = assess_work(_work(), ctx)
    r = next(r for r in a.agents if r.agent == "delay")
    assert r.status == Status.NOT_BUILT and r.risk == 0.0


def test_an_engine_that_raises_becomes_error_not_a_crash(ctx, monkeypatch):
    def boom(*_a, **_k):
        raise RuntimeError("disk on fire")

    engines = tuple(EngineSpec(e.id, e.name, e.question, boom, e.weight, e.order)
                    if e.id == "statistical" else e for e in registry.engines())
    monkeypatch.setattr(registry, "_CACHE", engines)
    a = assess_work(_work(), ctx)
    r = next(r for r in a.agents if r.agent == "statistical")
    assert r.status == Status.ERROR and "RuntimeError" in r.limitations[0]
    assert a.fused.score == 0.0


def test_a_new_engine_folder_is_found_without_editing_central_files(tmp_path, monkeypatch):
    pkg = tmp_path / "fakeagents"
    (pkg / "dummy").mkdir(parents=True)
    (pkg / "notanengine").mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "dummy" / "__init__.py").write_text("")
    (pkg / "notanengine" / "__init__.py").write_text("")
    (pkg / "dummy" / "engine.py").write_text(textwrap.dedent("""
        from drishti.agents.contract import AgentResult, Status
        from drishti.agents.registry import EngineSpec

        def _assess(work, ctx):
            return AgentResult(agent="dummy", status=Status.ASSESSED, verdict="OK", risk=0.0,
                               confidence=1.0, hard=False, headline="Nothing unusual.",
                               version="dummy-1")

        ENGINE = EngineSpec(id="dummy", name="Dummy", question="Is it a test?",
                            assess=_assess, order=50)
    """))
    monkeypatch.syspath_prepend(str(tmp_path))
    try:
        found = discover("fakeagents")
    finally:
        for m in [m for m in sys.modules if m.startswith("fakeagents")]:
            del sys.modules[m]
    ids = [e.id for e in found]
    assert ids[-1] == "dummy" and "notanengine" not in ids
    # the four core slots are still listed, unbuilt, when a package has none of them
    assert all(e.assess is None for e in found[:4])


def test_new_engine_runs_in_the_pipeline(ctx, monkeypatch):
    from drishti.agents.contract import AgentResult

    def extra(work, ctx):
        return AgentResult(agent="extra", status=Status.ASSESSED, verdict="OK", risk=0.0,
                           confidence=1.0, hard=False, headline="Nothing unusual.",
                           version="x")

    monkeypatch.setattr(registry, "_CACHE",
                        registry.engines() + (EngineSpec("extra", "Extra", "q?", extra),))
    a = assess_work(_work(), ctx)
    assert a.agents[-1].agent == "extra" and a.agents[-1].status == Status.ASSESSED
    assert orchestrator.PIPELINE_VERSION


def test_legacy_ids_map_to_engine_ids():
    assert canonical_id("duplicate_project") == "dup_split"
    assert canonical_id("image_reuse") == "photo_forensics"
    assert canonical_id("statistical") == "statistical"
