"""promptfoo's provider for DRISHTI (T168): a filled work form through the four agents.

The same steps as POST /work-form/check?demo=true (api/routes.py work_form_check), without the
hosted database: the form becomes the engine's work record (pswif.to_work), the form check reads it
(validate), and the four agents and the risk score judge it (explain) against the form page's
demonstration data (drishti/demo.py), placed in Jaunpur. The route's other inputs (the district's
real eSAKSHI works) carry no forms, so they price nothing and repeat no pin.

The prompt is one JSON request:
  {"example": "<id in apps/web/public/work-form/examples.json>",   the form to start from
   "set": {"<form field>": value, ...},                              fields to overwrite
   "append": {"<form field>": "text"},                               text to add to a field
   "pad_bytes": n}                                                   n more bytes in scope_of_work
The answer is JSON: {"refused", "form_ready", "issues", "band", "score", "status", "level",
"codes", "headline"} (per agent where it says so).
"""

from __future__ import annotations

import copy
import json
import sys
from functools import cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "apps" / "engine"))
from drishti import demo  # noqa: E402
from drishti.agents.contract import Status  # noqa: E402
from drishti.api.routes import WORK_FORM_MAX  # noqa: E402
from drishti.batch import indexes  # noqa: E402
from drishti.cost_form import pswif  # noqa: E402
from drishti.cost_form.validate import validate  # noqa: E402
from drishti.evaluation.stats import build_store  # noqa: E402
from drishti.explain import explain  # noqa: E402
from drishti.pipeline.orchestrator import Context  # noqa: E402

EXAMPLES = ROOT / "apps" / "web" / "public" / "work-form" / "examples.json"
PLACE = {"district_lgd": "194", "district_name": "Jaunpur", "state_lgd": "09",
         "state_name": "Uttar Pradesh"}


@cache
def _examples() -> dict[str, dict]:
    data = json.loads(EXAMPLES.read_text(encoding="utf-8"))
    return {e["id"]: e["form"] for e in data["examples"]}


def _level(check: dict) -> str:
    if check["status"] != Status.ASSESSED.value:
        return "na"
    risks = [f["risk"] for f in check["findings"]]
    top = max(risks, default=0.0)
    return "ask" if top >= 0.4 else "check" if top >= 0.1 else "edge" if risks else "fits"


def check(form: dict) -> dict:
    """POST /work-form/check?demo=true, in process."""
    if len(json.dumps(form, default=str)) > WORK_FORM_MAX:
        return {"refused": 413}
    as_of = demo.as_of()
    work = pswif.to_work(form, district_lgd=PLACE["district_lgd"], today=as_of,
                         state_lgd=PLACE["state_lgd"], state_name=PLACE["state_name"],
                         district_name=PLACE["district_name"])
    work.update(demo.later(work["work_id"]))
    pool = [*demo.records(work), work]
    ctx = Context(stats=build_store(pool), as_of=as_of, data=indexes(pool))
    checked = validate(work["cost_form"], today=as_of)
    trace = explain(work, ctx)
    checks = {c["id"]: c for c in trace["checks"]}
    return {"refused": None, "form_ready": checked["ready"],
            "issues": sorted({i["key"].split(":")[0] for i in checked["issues"]
                              if i["level"] == "fix"}),
            "band": trace["result"]["band"], "score": round(trace["result"]["score"], 3),
            "status": {k: c["status"] for k, c in checks.items()},
            "level": {k: _level(c) for k, c in checks.items()},
            "codes": {k: sorted(f["code"] for f in c["findings"] if f["risk"] >= 0.1)
                      for k, c in checks.items()},
            "headline": {k: c.get("headline", "")[:200] for k, c in checks.items()}}


def build(request: dict) -> dict:
    form = copy.deepcopy(_examples()[request["example"]])
    form.update(request.get("set") or {})
    for k, text in (request.get("append") or {}).items():
        form[k] = f"{form.get(k) or ''} {text}".strip()
    if request.get("pad_bytes"):
        form["scope_of_work"] = (form.get("scope_of_work") or "") + " road" * (
            int(request["pad_bytes"]) // 5)
    return form


def call_api(prompt: str, options: dict, context: dict) -> dict:
    try:
        return {"output": json.dumps(check(build(json.loads(prompt))), ensure_ascii=False)}
    except Exception as exc:     # the route would answer 500: a test failure, never a pass
        return {"error": f"{type(exc).__name__}: {exc}"}


if __name__ == "__main__":       # a quick look: python provider.py '{"example": "clean"}'
    print(call_api(sys.argv[1], {}, {})["output"])
