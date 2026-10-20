r"""The Cost agent's eval as an Inspect AI task (T167, plan docs/plans/T167-cost-eval.md).

Inspect AI (UK AI Security Institute) runs the real Cost agent as the solver: no AI model is
called (`mockllm/model` only fills Inspect's model slot). One sample per case and world; the scorer
reads the agent's level and grades it against the case's label.

  apps\engine\.venv\Scripts\inspect.exe eval data\eval\cost\task.py --model mockllm/model ^
      -T set=all --log-dir data\eval\cost\logs
  apps\engine\.venv\Scripts\inspect.exe view --log-dir data\eval\cost\logs

Scores per sample (each a metric, the mean over its samples):
  pass            the level is one the label allows
  fraud_caught    a fraud reaches check or ask (frauds only)
  fraud_excused   a fraud left at fits or edge: must be 0 (frauds only)
  honest_clear    an honest or edge case left at fits or edge (honest and edge only)
  honest_asked    an honest or edge case asked when its label does not allow it: must be 0
  ideal           the level is the label's ideal one
"""

from __future__ import annotations

import sys
from functools import cache
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cases as C  # noqa: E402
import levels as L  # noqa: E402
from inspect_ai import Task, task  # noqa: E402
from inspect_ai.dataset import MemoryDataset, Sample  # noqa: E402
from inspect_ai.model import ModelOutput  # noqa: E402
from inspect_ai.scorer import Score, Target, mean, scorer  # noqa: E402
from inspect_ai.solver import Generate, TaskState, solver  # noqa: E402

KEYS = ("pass", "fraud_caught", "fraud_excused", "honest_clear", "honest_asked", "ideal")


@cache
def _world(name: str) -> C.World:
    spread, seed = C.WORLDS[name]
    return C.build_world(name, spread, seed)


@cache
def _sets() -> dict[str, list[C.Case]]:
    import holdout
    import holdout2
    return {"main": C.cases(), "holdout": holdout.holdout(), "holdout2": holdout2.holdout2()}


@cache
def _cases() -> dict[str, C.Case]:
    return {c.id: c for cases in _sets().values() for c in cases}


def samples(which: str = "all") -> list[Sample]:
    out = []
    for name, cases in _sets().items():
        if which not in ("all", name):
            continue
        out += _samples(name, cases)
    return out


def _samples(set_name: str, cases: list[C.Case]) -> list[Sample]:
    out = []
    for case in cases:
        if case.scope != "cost":
            continue
        for name in C.WORLDS:
            out.append(Sample(
                id=f"{case.id}@{name}",
                input=f"[{case.truth}] {case.story}",
                target=case.ideal,
                metadata={"case": case.id, "world": name, "truth": case.truth, "set": set_name,
                          "family": case.family, "allowed": list(case.allowed),
                          "pair": case.pair or "", "why": case.why}))
    return out


@solver
def cost_agent():
    """The real Cost agent on the case's filing in the case's world."""
    async def solve(state: TaskState, generate: Generate) -> TaskState:
        case = _cases()[state.metadata["case"]]
        r = case.run(_world(state.metadata["world"]))
        got = L.level(r)
        state.output = ModelOutput.from_content(model="drishti/cost_estimate", content=got)
        state.metadata.update(level=got, codes=sorted(f.code for f in r.findings if f.risk > 0),
                              headline=r.headline, leeway=r.evidence.get("leeway"),
                              version=r.version)
        return state
    return solve


@scorer(metrics={k: [mean()] for k in KEYS})
def level_grade():
    async def score(state: TaskState, target: Target) -> Score:
        md = state.metadata
        got, truth, allowed = md["level"], md["truth"], tuple(md["allowed"])
        fraud = truth == "fraud"
        nan = float("nan")
        value = {
            "pass": float(got in allowed),
            "fraud_caught": float(got in ("check", "ask")) if fraud else nan,
            "fraud_excused": float(got in ("fits", "edge")) if fraud else nan,
            "honest_clear": nan if fraud else float(got in ("fits", "edge")),
            "honest_asked": nan if fraud else float(got == "ask" and "ask" not in allowed),
            "ideal": float(got == target.text),
        }
        verdict = L.verdict(truth, allowed, got)
        return Score(value=value, answer=got,
                     explanation=f"{verdict}: {truth} case got {got} (allowed "
                                 f"{'/'.join(allowed)}, ideal {target.text}); "
                                 f"{', '.join(md['codes']) or 'no finding'}. "
                                 f"{md['headline'][:300]}",
                     metadata={"verdict": verdict, "family": md["family"]})
    return score


@task
def cost_eval(set: str = "all") -> Task:
    """`set`: main (the cases the rules were built on), holdout, holdout2, or all."""
    return Task(dataset=MemoryDataset(samples(set), name=f"t167_cost_cases_{set}"),
                solver=cost_agent(), scorer=level_grade())
