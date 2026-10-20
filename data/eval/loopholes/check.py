r"""Every known loophole against the current agents (T171; owner, 20 Oct 2026).

The owner: "everytime a loophole is found, write it in a file, including all the loopholes or methods to
bypass or situations where agents dont work you have found so far. then at the end, compare against all
these loopholes and check if the current agents can detect all of them".

Four sources, one registry:
  1. the agents' labelled eval cases (data/eval/<agent>/cases.py, holdout*.py; T167, T168): every case
     labelled fraud, evasion or broken is a way past an agent, and every case marked "limit" or "other"
     is a known gap. Each runs in both of its worlds; it counts as caught only when both catch it.
  2. the robustness loop's evasion and scarce-data probes (data/trial/agent_robustness_loop.py, T135-T164):
     PASS, FAIL or LIMIT as the loop judges them.
  3. the attacks on the form's text and numbers (data/eval/promptfoo, T168): their last promptfoo run.
  4. everything else (data/eval/loopholes/manual.py): design and data limits, process and system
     loopholes, the open ones, each with a runnable scenario or the test that guards its fix.

Writes docs/LOOPHOLES.md (the registry, with today's result for every entry) and
data/trial/results/loopholes_check.txt / .json.

  apps\engine\.venv\Scripts\python.exe data\eval\loopholes\check.py            # everything
  apps\engine\.venv\Scripts\python.exe data\eval\loopholes\check.py --no-loop  # skip the loop (faster)
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
EVAL = HERE.parent
sys.path.insert(0, str(EVAL / "common"))
import world as W  # noqa: E402,I001  (first: it sets sys.path)
import grade as G  # noqa: E402
import report as R  # noqa: E402

ROOT = W.ROOT
DOC = ROOT / "docs" / "LOOPHOLES.md"
OUT = ROOT / "data" / "trial" / "results" / "loopholes_check"
AGENT_NAME = {"cost_estimate": "Cost", "dup_split": "Duplicate Work", "time_rules": "Time & Rules",
              "site_progress": "Site Progress", "pipeline": "All four together",
              "planner": "Inspection Planner", "case status": "Case status",
              "scoring": "Scoring", "data": "Data loading", "form page": "Form page"}
# what each result means, in the order the summary lists them
RESULTS = {
    "caught": "Caught: asked",
    "checked": "Caught: \"check this\"",
    "other_agent": "Caught by another agent",
    "said_so": "Couldn't check, and says so",
    "fixed": "Fixed (guarded by a test)",
    "mitigated": "Made visible (not blocked)",
    "limit": "Known limit",
    "pending": "Being measured",
    "open": "OPEN: not caught",
    "missed": "MISSED: not caught",
}


def _use_research_export_if_needed() -> str:
    """The robustness loop and the examples read the eSAKSHI dashboard tables; without them on this
    PC, the research export stands in (the owner's choice, T170)."""
    from esakshi_dashboard import RAW
    if not (RAW / "Works_Recommended.csv").exists() and "--research" not in sys.argv:
        sys.argv.append("--research")
        return "research export (dashboard tables not on this PC)"
    return "eSAKSHI dashboard tables"


# ---- 1. the labelled eval cases -------------------------------------------------------------------

def _result(truth: str, scope: str, levels: list[str], bands: list[str]) -> str:
    if scope == "limit":
        return "limit"
    if truth == "broken":
        return "said_so" if all(x != "fits" for x in levels) else "missed"
    if scope == "other":
        return "other_agent" if all(b in G.QUEUE for b in bands) else "missed"
    if all(x == "ask" for x in levels):
        return "caught"
    if all(x in ("check", "ask") for x in levels):
        return "checked"
    if all(x in ("check", "ask", "na") for x in levels) and "na" in levels:
        return "said_so"
    return "missed"


def eval_cases() -> list[dict]:
    rows = []
    for agent in ("dup_split", "time_rules", "site_progress"):
        for set_name, cases in R.case_sets(agent).items():
            for c in cases:
                if c.truth not in ("fraud", "evasion", "broken") and c.scope == "self":
                    continue
                runs = [R.judge(c, W.world(n)) for n in W.WORLDS]
                levels, bands = [x["got"] for x in runs], [x["band"] for x in runs]
                rows.append({
                    "id": c.id, "source": f"eval {agent}/{set_name}", "agent": agent,
                    "kind": c.truth if c.scope == "self" else f"{c.truth} ({c.scope})",
                    "title": c.story, "how": c.why, "found": "T168 eval",
                    "result": _result(c.truth, c.scope, levels, bands),
                    "detail": "; ".join(f"{x['world']}: {x['got']} {x['band']} "
                                        f"{','.join(x['codes']) or '-'}" for x in runs)})
    sys.path.insert(0, str(EVAL / "cost"))
    import cases as C  # noqa: PLC0415
    import holdout as H  # noqa: PLC0415
    import holdout2 as H2  # noqa: PLC0415
    import levels as CL  # noqa: PLC0415
    worlds = {n: C.build_world(n, spread, seed) for n, (spread, seed) in C.WORLDS.items()}
    for set_name, cases in (("main", C.cases()), ("holdout", H.holdout()),
                            ("holdout2", H2.holdout2())):
        for c in cases:
            if c.truth != "fraud":
                continue
            got, codes = [], []
            for w in worlds.values():
                r = c.run(w)
                got.append(CL.level(r))
                codes.append(",".join(sorted(f.code for f in r.findings if f.risk > 0)) or "-")
            # judged on Cost's own answer; a fraud the estimate cannot show ("other": another
            # agent's job) that Cost misses is a known limit of Cost, not a miss
            result = _result("fraud", "self", got, [])
            if c.scope != "cost" and result == "missed":
                result = "limit"
            rows.append({"id": c.id, "source": f"eval cost/{set_name}", "agent": "cost_estimate",
                         "kind": "fraud" if c.scope == "cost" else f"fraud ({c.scope})",
                         "title": c.story, "how": c.why, "found": "T167 eval",
                         "result": result,
                         "detail": "; ".join(f"{n}: {g} {k}" for n, g, k in
                                             zip(worlds, got, codes, strict=True))})
    return rows


# ---- 2. the robustness loop ------------------------------------------------------------------------

def loop_probes() -> list[dict]:
    import agent_robustness_loop as L  # noqa: PLC0415
    world = L.build_world()
    rows = []
    for pr in L.PROBES:
        if pr.kind not in ("evasion", "scarce"):
            continue
        try:
            verdict, detail = pr.fn(world)
        except Exception as e:  # noqa: BLE001  (a probe that breaks is a finding, not a crash)
            verdict, detail = "FAIL", f"the probe raised {type(e).__name__}: {e}"
        result = {"PASS": "caught" if pr.kind == "evasion" else "said_so", "LIMIT": "limit",
                  "FAIL": "missed"}[verdict]
        rows.append({"id": pr.name[:60], "source": f"loop {pr.kind}", "agent": pr.agent,
                     "kind": pr.kind, "title": pr.name, "how": "", "found": "T135-T164 loop",
                     "result": result, "detail": detail[:300]})
    return rows


# ---- 3. the attacks on the form --------------------------------------------------------------------

def promptfoo_attacks() -> list[dict]:
    path = ROOT / "data" / "trial" / "results" / "t168_promptfoo.json"
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    rows = []
    for r in data["results"]["results"]:
        desc = (r.get("testCase") or {}).get("description") or ""
        if desc.startswith(("example ", "normal ", "edge ", "suspected ")):
            continue                     # the examples, not attacks
        rows.append({"id": desc[:60], "source": "promptfoo (last run)", "agent": "pipeline",
                     "kind": "attack", "title": desc, "how": "", "found": "T168 promptfoo",
                     "result": "caught" if r.get("success") else "missed",
                     "detail": "the form check stayed right" if r.get("success")
                     else (r.get("error") or "")[:200]})
    return rows


# ---- 4. everything else ----------------------------------------------------------------------------

def manual() -> list[dict]:
    import manual as M  # noqa: PLC0415
    rows = []
    for e in M.ENTRIES:
        result, detail = e.state, e.now
        if e.run is not None:
            try:
                got, said = e.run()
            except Exception as x:  # noqa: BLE001
                got, said = "missed", f"the scenario raised {type(x).__name__}: {x}"
            detail = f"{e.now} Today: {said}."
            if e.state in ("open", "limit") and got == "caught":
                result = "caught"        # the agents now catch it: the registry says so
            elif e.state not in ("open", "limit") and got != "caught":
                result = "missed"
        rows.append({"id": e.id, "source": "registry", "agent": e.agent, "kind": e.state,
                     "title": e.title, "how": e.how, "found": e.found, "result": result,
                     "detail": detail + (f" Guard: `{e.guard}`." if e.guard else "")})
    return rows


# ---- the registry ----------------------------------------------------------------------------------

def write(rows: list[dict], source_of_works: str) -> None:
    counts = Counter(r["result"] for r in rows)
    caught = sum(counts[k] for k in ("caught", "checked", "other_agent", "said_so", "fixed"))
    lines = [
        "# Loopholes: every known way past the agents, and today's result",
        "",
        "Every way found so far to get a fraud past NidhiNetra's agents, every bypass, and every situation "
        "where an agent cannot work, in one list, each run against the current agents. **When a new "
        "loophole is found, add it at once** (a labelled case in `data/eval/<agent>/`, a probe in "
        "`data/trial/agent_robustness_loop.py`, or an entry in `data/eval/loopholes/manual.py`) and run "
        "`data/eval/loopholes/check.py`, which rewrites this file (owner, 20 Oct 2026; T171).",
        "",
        f"**Last run:** {date.today():%d %b %Y}, on the {source_of_works}. **{len(rows)} entries.**",
        "",
        "| Today's result | Entries |",
        "|---|---|",
        *[f"| {RESULTS[k]} | {counts[k]} |" for k in RESULTS if counts[k]],
        "",
        f"**Caught or said so:** {caught} of {len(rows)}. **Known limits:** {counts['limit']}. "
        f"**Made visible:** {counts['mitigated']}. **Being measured:** {counts['pending']}. "
        f"**Open or missed:** {counts['open'] + counts['missed']}.",
        "",
        "How to read a result: *asked* = the agent raises a question (the work goes to the review queue); "
        "*check this* = a lighter follow-up; *another agent* = this agent cannot see it, but the four "
        "together still queue it; *couldn't check, and says so* = broken or missing data reads as "
        "\"couldn't check\", never as a clean chit; *known limit* = accepted by the owner's design or until "
        "data not on hand exists, listed so nobody mistakes it for coverage. A case counts as caught only "
        "when it is caught in every test district it runs in.",
        "",
    ]
    order = list(RESULTS)
    for heading, keep in (("Open and missed: not caught today", ("open", "missed")),
                          ("Known limits", ("limit",)),
                          ("Made visible, being measured", ("mitigated", "pending")),
                          ("Caught, fixed or said so", ("caught", "checked", "other_agent", "said_so",
                                                        "fixed"))):
        part = [r for r in rows if r["result"] in keep]
        if not part:
            continue
        lines += [f"## {heading} ({len(part)})", ""]
        by_agent: dict[str, list[dict]] = {}
        for r in part:
            by_agent.setdefault(AGENT_NAME.get(r["agent"], r["agent"]), []).append(r)
        for agent, items in by_agent.items():
            lines += [f"### {agent}", "", "| Loophole | How it works | Found | Today | Detail |",
                      "|---|---|---|---|---|"]
            for r in sorted(items, key=lambda x: (order.index(x["result"]), x["source"], x["id"])):
                cell = lambda s: str(s).replace("|", "/").replace("\n", " ")  # noqa: E731
                lines.append(f"| {cell(r['title'])} | {cell(r['how'])} | {cell(r['found'])}, "
                             f"`{cell(r['id'])}` | **{RESULTS[r['result']]}** | "
                             f"{cell(r['detail'])} |")
            lines.append("")
    DOC.write_text("\n".join(lines) + "\n", encoding="utf-8")
    OUT.with_suffix(".json").write_text(json.dumps(rows, ensure_ascii=False, indent=1),
                                        encoding="utf-8")
    summary = [f"{len(rows)} loopholes ({source_of_works}), {date.today()}",
               *[f"  {RESULTS[k]}: {counts[k]}" for k in RESULTS if counts[k]], ""]
    summary += [f"{r['result']:11} {r['source']:24} {r['id'][:60]:60} {r['detail'][:120]}"
                for r in sorted(rows, key=lambda x: (order.index(x["result"]), x["source"]))]
    OUT.with_suffix(".txt").write_text("\n".join(summary) + "\n", encoding="utf-8")
    print("\n".join(summary[:len(RESULTS) + 2]))
    for r in rows:
        if r["result"] in ("open", "missed"):
            print(f"  {RESULTS[r['result']]}: [{r['source']}] {r['title'][:90]}  ({r['detail'][:120]})")
    print(f"wrote {DOC.relative_to(ROOT)} and {OUT.relative_to(ROOT)}.txt/.json")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-loop", action="store_true", help="skip the robustness loop's probes")
    ap.add_argument("--research", action="store_true", help=argparse.SUPPRESS)
    args = ap.parse_args()
    source = _use_research_export_if_needed()
    rows = eval_cases()
    print(f"eval cases: {len(rows)}")
    if not args.no_loop:
        n = len(rows)
        rows += loop_probes()
        print(f"loop probes: {len(rows) - n}")
    n = len(rows)
    rows += promptfoo_attacks()
    print(f"form attacks: {len(rows) - n}")
    n = len(rows)
    rows += manual()
    print(f"registry entries: {len(rows) - n}")
    write(rows, source)


if __name__ == "__main__":
    main()
