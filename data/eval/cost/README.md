# The Cost agent's eval (T167)

An eval environment for the Cost agent, built on **Inspect AI** (the UK AI Security Institute's open-source eval
framework). It runs the real agent on labelled cost estimates: honest ones, honest-but-unusual ones (edge cases) and
frauds. Plan: [`docs/plans/T167-cost-eval.md`](../../../docs/plans/T167-cost-eval.md). Results: FINDINGS "T167".

| File | What it is |
|---|---|
| `cases.py` | the world (Jaunpur, other agencies' honest filings, two price spreads) and the main labelled cases |
| `holdout.py`, `holdout2.py` | two held-out sets, each committed before its first run |
| `levels.py` | the agent's answer as one level: fits, edge, check, ask (or na) |
| `run.py` | the cases without Inspect: a plain report in `data/trial/results/t167_cost_eval_<label>.txt` |
| `task.py` | the Inspect AI task (solver = the real agent, no AI model) |
| `sweep.py` | a random honest population and a dose curve for each fraud scheme |

The one rule: **a fraud never gets fits or edge** (that is a fraud excused); an honest case is never asked unless its
label says so. `apps/engine/tests/agents/cost_estimate/test_cost_t167.py` runs every case on each pull request.

```powershell
apps\engine\.venv\Scripts\python.exe -m pip install -r data\eval\requirements.txt   # once: Inspect AI
apps\engine\.venv\Scripts\python.exe data\eval\cost\run.py --label mine            # main cases
apps\engine\.venv\Scripts\python.exe data\eval\cost\run.py --holdout2 --label mine # a held-out set
apps\engine\.venv\Scripts\python.exe data\eval\cost\sweep.py                       # boundaries
apps\engine\.venv\Scripts\inspect.exe eval data\eval\cost\task.py --model mockllm/model -T set=all --log-dir data\eval\cost\logs
apps\engine\.venv\Scripts\inspect.exe view --log-dir data\eval\cost\logs           # browse every case
```

Adding a case: write it in a NEW held-out file, label it (truth, ideal, allowed levels, why), commit it, and only then
run it. A case the rules were changed for is "seen" and stops counting as a test of generalisation.
