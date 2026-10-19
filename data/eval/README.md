# DRISHTI's eval environments (T167, T168)

Every agent is tested in popular eval environments, each used for what it does best. Plans:
[`docs/plans/T167-cost-eval.md`](../../docs/plans/T167-cost-eval.md),
[`docs/plans/T168-agent-evals.md`](../../docs/plans/T168-agent-evals.md). Results: FINDINGS "T167" and "T168".

| Environment | What it tests | Where |
|---|---|---|
| **Inspect AI** (UK AI Security Institute) | labelled cases per agent (honest, edge, fraud, evasion, broken) in two worlds; the four agents together (the risk score's band); NidhiLens's answers on altered photos | `cost/task.py`, `agents_task.py`, `nidhilens/task.py` |
| **promptfoo** | the whole system through the form check's own steps: the website's 13 example filings and 14 attacks on the form | `promptfoo/` |
| **Hypothesis** | rules that hold for every generated input (invariance, monotonicity, room for error, the contract) | `apps/engine/tests/properties/` (CI) |

| Folder | What it is |
|---|---|
| `common/` | the shared world (Jaunpur, made-up agencies), the levels and their grades, the plain report |
| `cost/` | the Cost agent's cases, held-out sets, sweep and Inspect task (T167) |
| `dup_split/`, `time_rules/`, `site_progress/` | each agent's `cases.py` (main) and `holdout.py` (committed before its first run) |
| `pipeline/` | every case of the three sets through all four agents: a fraud must reach the queue, an honest filing stay LOW |
| `nidhilens/` | `run.py` (the GPU run: 10 photo scenarios) and `task.py` (scored through the engine's own reader) |
| `promptfoo/` | `promptfooconfig.yaml` and its Python provider |

The one rule, for every agent: **a fraud is never fits or edge, an honest case is never asked, broken data is never
a clean chit.** `apps/engine/tests/eval/test_agent_evals.py` and `tests/agents/cost_estimate/test_cost_t167.py` gate
every case on each pull request.

```powershell
# the plain reports (results in data/trial/results/t168_<agent>_<set>_<label>.txt)
apps\engine\.venv\Scripts\python.exe data\eval\common\report.py dup_split --set main --label mine
apps\engine\.venv\Scripts\python.exe data\eval\common\report.py pipeline --set holdout --label mine

# Inspect AI (pip install -r data\eval\requirements.txt once)
apps\engine\.venv\Scripts\inspect.exe eval data\eval\agents_task.py@dup_split_eval --model mockllm/model -T set=all --log-dir data\eval\logs
apps\engine\.venv\Scripts\inspect.exe view --log-dir data\eval\logs

# promptfoo (installed off C:, which is full: D:\nidhinetra-data\tools\promptfoo; any npx promptfoo@0.123.1 works)
cd data\eval\promptfoo
$env:PROMPTFOO_DISABLE_TELEMETRY="1"; promptfoo eval -c promptfooconfig.yaml --no-cache -o ..\..\trial\results\t168_promptfoo.json

# NidhiLens on this PC's GPU (the trial venv on D:), then scored in the engine's venv
D:\nidhinetra-data\venv\Scripts\python.exe data\eval\nidhilens\run.py --scenario all --subset 300
apps\engine\.venv\Scripts\python.exe data\eval\nidhilens\task.py
```

Adding a case: write it in a NEW held-out file (or the agent's `holdout.py` before its first run), label it (truth,
ideal, allowed levels, why), commit it, and only then run it. A case a rule was changed for is marked SEEN in its
`why` and stops counting as a test of generalisation. A known edge of a measured rule that needs data not on hand is
`scope="limit"`: listed apart, never counted.
