r"""The four agents' evals as Inspect AI tasks (T168, plan docs/plans/T168-agent-evals.md).

Inspect AI (UK AI Security Institute) runs the real agents as the solver, exactly as the website's
form check runs them (data/eval/common/world.py); no AI model is called (`mockllm/model` only
fills Inspect's model slot). One sample per case and world; the scorer grades the agent's level
(or, for the four together, the risk score's band) against the case's label. The Cost agent's own
task is data/eval/cost/task.py (T167).

  apps\engine\.venv\Scripts\inspect.exe eval data\eval\agents_task.py@dup_split_eval ^
      --model mockllm/model -T set=all --log-dir data\eval\logs
  (also time_rules_eval, site_progress_eval, pipeline_eval)
  apps\engine\.venv\Scripts\inspect.exe view --log-dir data\eval\logs

Metrics (each the mean over the samples it applies to; the hard ones must be 0):
  agents     pass, fraud_caught, fraud_excused, honest_clear, honest_asked, broken_cleared, ideal
  together   pass, fraud_queued, fraud_excused, honest_low, honest_queued, honest_high, ideal
Cases scoped "other" or "limit" are left out of the samples (listed apart by report.py).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "common"))
import world as W  # noqa: E402,I001  (first: it sets the paths)
import grade as L  # noqa: E402
import report as R  # noqa: E402
from inspect_ai import Task, task  # noqa: E402
from inspect_ai.dataset import MemoryDataset, Sample  # noqa: E402
from inspect_ai.model import ModelOutput  # noqa: E402
from inspect_ai.scorer import Score, Target, mean, scorer  # noqa: E402
from inspect_ai.solver import Generate, TaskState, solver  # noqa: E402

AGENT_KEYS = ("pass", "fraud_caught", "fraud_excused", "honest_clear", "honest_asked",
              "broken_cleared", "ideal")
BAND_KEYS = ("pass", "fraud_queued", "fraud_excused", "honest_low", "honest_queued",
             "honest_high", "ideal")


def _samples(agent: str, which: str) -> list[Sample]:
    out = []
    for set_name, cases in R.case_sets(agent).items():
        if which not in ("all", set_name):
            continue
        for c in cases:
            if c.scope != "self":
                continue
            for world in W.WORLDS:
                out.append(Sample(
                    id=f"{c.id}@{world}", input=f"[{c.truth}] {c.story}", target=c.ideal,
                    metadata={"agent": agent, "case": c.id, "world": world, "set": set_name,
                              "truth": c.truth, "family": c.family, "allowed": list(c.allowed),
                              "pair": c.pair or "", "why": c.why}))
    return out


@solver
def drishti_agents():
    """The four agents (and the risk fusion) on the case's filing in the case's world."""
    async def solve(state: TaskState, generate: Generate) -> TaskState:
        md = state.metadata
        case = next(c for c in R.case_sets(md["agent"])[md["set"]] if c.id == md["case"])
        row = R.judge(case, W.world(md["world"]))
        state.output = ModelOutput.from_content(model=f"drishti/{md['agent']}", content=row["got"])
        state.metadata.update(got=row["got"], codes=row["codes"], notes=row["notes"],
                              band=row["band"], score=row["score"], headline=row["headline"],
                              verdict=row["verdict"])
        return state
    return solve


def _grade(band: bool):
    keys = BAND_KEYS if band else AGENT_KEYS
    grade = L.band_scores if band else L.scores

    @scorer(metrics={k: [mean()] for k in keys})
    def level_grade():
        async def score(state: TaskState, target: Target) -> Score:
            md = state.metadata
            value = grade(md["truth"], tuple(md["allowed"]), target.text, md["got"])
            return Score(value=value, answer=md["got"],
                         explanation=f"{md['verdict']}: {md['truth']} case got {md['got']} "
                                     f"(allowed {'/'.join(md['allowed'])}, ideal {target.text}); "
                                     f"{', '.join(md['codes']) or 'nothing counted'}; band "
                                     f"{md['band']} {md['score']}. {md['headline']}",
                         metadata={"verdict": md["verdict"], "family": md["family"]})
        return score
    return level_grade()


def _task(agent: str, which: str) -> Task:
    return Task(dataset=MemoryDataset(_samples(agent, which), name=f"t168_{agent}_{which}"),
                solver=drishti_agents(), scorer=_grade(agent == "pipeline"))


@task
def dup_split_eval(set: str = "all") -> Task:
    """Duplicate Work. `set`: main, holdout or all."""
    return _task("dup_split", set)


@task
def time_rules_eval(set: str = "all") -> Task:
    """Time & Rules. `set`: main, holdout or all."""
    return _task("time_rules", set)


@task
def site_progress_eval(set: str = "all") -> Task:
    """Site Progress (the rules over the video readings; NidhiLens: data/eval/nidhilens/)."""
    return _task("site_progress", set)


@task
def pipeline_eval(set: str = "all") -> Task:
    """The four agents together: the risk score's band for every case of the three sets."""
    return _task("pipeline", set)
