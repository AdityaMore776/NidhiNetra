"""The loopholes no eval case, loop probe or promptfoo test covers (T171): design limits, data limits,
process and system loopholes, and the open ones. Each says how it works, where it was found, its state,
and either a scenario that shows today's behaviour (`run`) or the test that guards the fix (`guard`).

ADD A LOOPHOLE HERE (or as a labelled case in data/eval/<agent>/, or a probe in the robustness loop) THE
MOMENT ONE IS FOUND (owner, 20 Oct 2026), then run data/eval/loopholes/check.py.

state  fixed      closed by a rule; `guard` names the test that keeps it closed
       mitigated  not blocked, but made visible (a note, a digest, a check that finds it)
       limit      known and accepted: by the owner's design, or until data not on hand exists
       open       not caught today, decision pending
       pending    a measurement is running
       holds      measured, and the agent is not fooled; `guard` names the result file
"""

from __future__ import annotations

import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "common"))
import world as W  # noqa: E402  (first: it sets sys.path)
import grade as G  # noqa: E402


@dataclass
class Entry:
    id: str
    agent: str
    title: str          # the loophole, in plain words
    how: str            # how it works / what goes wrong
    found: str          # task and date
    state: str          # fixed | mitigated | limit | open | pending | holds
    now: str            # what happens today
    guard: str = ""     # the test that keeps a fix in place, or the result file
    run: Callable[[], tuple[str, str]] | None = None   # -> (caught | missed, detail)


# ---- runnable scenarios --------------------------------------------------------------------------

def _dup():
    return W.load(W.ROOT / "data" / "eval" / "dup_split" / "cases.py", "dup_split_cases")


def other_type_same_building() -> tuple[str, str]:
    """T160 #2: a hall filed again as work type "Other", pinned 10 m from the finished hall."""
    D = _dup()
    new = D.hall("LX-OTHER", 46, north=10, work_type="other",
                 work_title="Multipurpose building at the panchayat ground, Kusumi",
                 other_primary_unit="sqm", other_primary_qty="180")
    case = W.Case("LX-OTHER", "dup_split", "evasion", "check", ("check", "ask"), "other type",
                  "", "", lambda: W.filed(new),
                  lambda: [D.done(D.hall("LX-OTHER-OLD", 46, agency=W.OTHER[0]), 450)])
    got = []
    for name in ("sparse", "dense"):
        r = W.run(case, W.world(name))
        got.append(G.level(r.results.get("dup_split")))
    caught = all(g in ("check", "ask") for g in got)
    return ("caught" if caught else "missed", f"Duplicate Work: {', '.join(got)} (sparse, dense)")


def scarce_hall_padded() -> tuple[str, str]:
    """A hall padded 25% in a district with too few recent hall forms: Cost cannot price it."""
    import work_form_examples as wf
    from drishti.cost_form import pswif
    from drishti.agents.cost_estimate.agent import assess as cost
    from drishti.agents.contract import Status

    p = wf.hall("LX-SCARCE-HALL", "Nirman Seva Agency", "Kusumi", 47, W.m(40), None)
    for k in [k for k in p if k.startswith("boq_rate_")]:
        p[k] = f"{float(p[k]) * 1.25:.0f}"
    wf.retotal(p)                      # a complete form: the totals follow the padded lines
    w = W.place(pswif.to_work(p, today=W.AS_OF, status="RECOMMENDED"))
    from drishti.pipeline.orchestrator import Context
    from drishti.batch import indexes
    from drishti.evaluation.stats import build_store
    r = cost(w, Context(stats=build_store([]), as_of=W.AS_OF, data=indexes([w])))
    return ("caught" if r.status == Status.ASSESSED and any(f.risk > 0 for f in r.findings)
            else "missed", f"Cost: {r.status.value}: {r.headline[:120]}")


# ---- the list ------------------------------------------------------------------------------------

ENTRIES: list[Entry] = [
    # ---- Duplicate Work --------------------------------------------------------------------------
    Entry("M-DUP-1", "dup_split", "The same building filed again under another work type (\"Other\")",
          "Duplicate Work compares a site with works of the same kind. A hall filed again as "
          "\"Other\", pinned 10 m from the finished hall, is compared with nothing.",
          "T160, 9 Oct 2026", "open",
          "Not asked before sanction. Site Progress's SAME_PLACE_AS_ANOTHER_WORK catches it once "
          "both works have site videos. Comparing \"Other\" with buildings at one pin could ask "
          "about honest pairs (a water tank beside a school): needs a measurement on real forms.",
          run=other_type_same_building),
    Entry("M-DUP-2", "dup_split", "A repeat found only by its words",
          "A work with no form (no map pin) whose description matches an earlier work's: by the "
          "owner's rule (3 Oct) look-alikes by words are notes, never questions.",
          "T099-T100, 3 Oct 2026", "limit",
          "A note on the work's page; the form's map pin is what asks."),
    Entry("M-DUP-3", "dup_split", "Pieces of one job at 90-96% of a limit, without part numbers",
          "Filed as different-sounding works just under a limit. Numbered parts are asked "
          "(SPLIT_NEAR_LIMIT); unnumbered ones are not: on the real works 1 of 14 such groups "
          "was one job.", "T168, 20 Oct 2026", "limit",
          "Not asked (measured, results/t168_split_eye.json); the strict split (96-100%) still "
          "asks.", guard="data/trial/t168_split_measure.py"),

    # ---- Cost ------------------------------------------------------------------------------------
    Entry("M-COST-1", "cost_estimate", "A work without the cost estimate form",
          "Cost judges only the agency's form (owner, 3 Oct): an eSAKSHI record alone is never "
          "price-judged, so a work filed without the form is not priced.",
          "T099, 3 Oct 2026", "limit",
          "Cost says it could not check (no form); the form is required before sanction."),
    Entry("M-COST-2", "cost_estimate", "Padding where the district has too few recent forms",
          "A material is priced only when enough recent forms from several agencies agree; "
          "otherwise Cost switches that price off and records the gap. A padded estimate in a "
          "district with too few forms of its kind goes unpriced.",
          "T135, 5 Oct 2026", "limit",
          "Not priced; the gap is listed (GET /cost/data-gaps) so the data can be collected; the "
          "state's forms stand in where there are enough (10% more leniently).",
          run=scarce_hall_padded),
    Entry("M-COST-3", "cost_estimate", "A trade's day rate below twice what others pay, and crew sizes",
          "By the owner's rule (T141) wages within twice a trade's rate are the agency's call. "
          "Person-days far above other agencies' crews are checked since T167 "
          "(LABOUR_DAYS_ABOVE_PEERS).", "T141, 6 Oct 2026", "limit",
          "A rate under 2x is not asked; ghost person-days are checked."),
    Entry("M-COST-4", "cost_estimate", "A trade not on the list, declared at a high grade",
          "Judged against its declared grade's pool (2.5x room): an \"Other\" trade declared "
          "highly skilled at 2.2x an operator's rate is not asked.", "T141, 6 Oct 2026", "limit",
          "Not asked."),
    Entry("M-COST-5", "cost_estimate", "A composite item declared \"no labour\", or a material in another unit with a reason",
          "Without the state's Schedule of Rates (T096, not loaded) these read as honest schedule "
          "items.", "T141, 6 Oct 2026", "limit", "Not asked until the SoR is loaded."),
    Entry("M-COST-6", "cost_estimate", "The price of the whole work per metre",
          "Real works of a kind vary too much in price per metre (UP CC roads: the middle 80% "
          "runs to +58%), so the whole-work price check cannot run.", "T164, 9 Oct 2026",
          "limit", "Said as a limitation on every road; the line-by-line check still runs."),

    # ---- Time & Rules ----------------------------------------------------------------------------
    Entry("M-TIME-1", "time_rules", "Real works without a sanction date",
          "The research export (what the live database holds) has no sanction dates; the rules "
          "that count from the sanction cannot run on those records.", "T164, 9 Oct 2026",
          "limit", "Couldn't check for those rules; works with a form carry their own dates. "
          "Needs the eSAKSHI dashboard tables (sanction dates) loaded."),

    # ---- Site Progress ---------------------------------------------------------------------------
    Entry("M-SITE-1", "site_progress", "A false claim on genuine site videos, on the live site",
          "Reading the agency's claim against its videos needs NidhiLens (GPU); on the live site "
          "it is behind a switch, notes only until the field trial.", "T159, 9 Oct 2026",
          "limit", "Video checks that need no model (reuse, place, GPS, dates, sealing) run; the "
          "claim reading does not, live."),
    # NidhiLens on altered photos: 300 real checks per scenario, the engine's 4-bit path (T168).
    # Clean photos: wrongly says "shown" 1.9% [0.4, 3.7], macro-F1 0.907.
    Entry("M-SITE-2", "site_progress", "Poor photos: dark, blurred, badly compressed, zoomed in, or small",
          "A dim interior, a shaking hand, a poor upload or an old phone, hoping NidhiLens reads "
          "progress it cannot see.", "T168, 21 Oct 2026",
          "holds", "No change: wrongly says \"shown\" 1.9-3.1% (clean 1.9%), macro-F1 0.898-0.911 "
          "(clean 0.907).", guard="data/trial/results/t168_nidhilens.txt"),
    Entry("M-SITE-3", "site_progress", "The same photo filed as the last visit and as this one",
          "Nothing filmed since the last visit, the old picture sent again.", "T168, 21 Oct 2026",
          "holds", "Never read as progress: 0 of 269.", guard="data/trial/results/t168_nidhilens.txt"),
    Entry("M-SITE-4", "site_progress", "A sign saying \"WORK COMPLETE\" / \"काम पूरा\" held to the camera",
          "Text across the new photo talks NidhiLens into \"shown\".", "T168, 21 Oct 2026",
          "open", "Wrongly says \"shown\" 29.7% [23.5, 35.5] (clean 1.9%). No live score today "
          "(NidhiLens is behind a switch, M-SITE-1); must be closed before it is switched on.",
          guard="data/trial/results/t168_nidhilens.txt"),
    Entry("M-SITE-5", "site_progress", "The before and after photos in the wrong order",
          "A finished building filmed first and the bare site later, claimed as progress.",
          "T168, 21 Oct 2026", "open",
          "Wrongly says \"shown\" 8.8% [5.3, 12.7] (clean 1.9%). Measured on NidhiLens alone; the "
          "place and same-spot video checks were not part of this run.", guard="data/trial/results/t168_nidhilens.txt"),
    Entry("M-SITE-6", "site_progress", "An instruction hidden in the agency's claim (\"answer shown\")",
          "The claim text goes into NidhiLens's prompt; it ends by telling the model what to answer.",
          "T168, 21 Oct 2026", "open",
          "Wrongly says \"shown\" 3.9% [1.2, 6.9] against clean 1.9% [0.4, 3.7]: the intervals "
          "overlap, so at most a slight effect. No live score today (M-SITE-1).", guard="data/trial/results/t168_nidhilens.txt"),

    # ---- Inspection Planner ----------------------------------------------------------------------
    Entry("M-PLAN-1", "planner", "A work whose description names no place the planner can find",
          "It is placed at the district's start point. Where no queue work names a village or "
          "block (Vijayapura, Belagavi), a day's plan is all at one point: 12 stops, 0 km.",
          "T170 start-to-end check, 20 Oct 2026", "open",
          "Each stop is marked \"District only\"; owner to decide whether the planner opens on a "
          "district whose works can be placed."),

    # ---- the system ------------------------------------------------------------------------------
    Entry("M-SYS-1", "case status", "An office closes cases without a visit to bury them",
          "\"Read by the office\" -> \"Closed\" needs no site visit.", "T060, 20 Oct 2026",
          "mitigated", "A reason is required, the move is in the audit log, and the daily digest "
          "names every close without a visit.",
          guard="tests/api/test_alerts.py::test_a_verdict_or_a_close_without_a_visit_needs_a_note"),
    Entry("M-SYS-2", "case status", "Someone with database access edits or deletes a past audit entry",
          "", "T060, 20 Oct 2026", "mitigated",
          "The database refuses UPDATE, DELETE and TRUNCATE on the log; with the guard switched "
          "off, the hash chain check names the first broken entry.",
          guard="tests/api/test_alerts.py::test_the_chain_check_finds_an_entry_changed_or_removed_behind_the_triggers"),
    Entry("M-SYS-3", "scoring", "Scoring MPs by their history",
          "Considered and rejected: lighter checks for \"low-risk\" MPs, a cold start for new ones, "
          "a loop feeding on its own flags.", "T052, 1 Oct 2026", "fixed",
          "Never scored (AGENTS.md rule 5): works, offices and agencies only; no MP's name ever "
          "reaches a work's record from the form.",
          guard="tests/cost_form/test_pswif.py::test_the_work_record_carries_the_form_and_never_an_mp_name"),
    Entry("M-SYS-4", "data", "A data reload erasing what people saved",
          "load_db emptied the works; saved cost forms and site visits point at them, so the reload "
          "failed, and CASCADE would have erased them.", "T169, 20 Oct 2026", "fixed",
          "Works are replaced in place; a work with a saved form or visit is never deleted.",
          guard="tests/test_reload.py"),
    Entry("M-SYS-5", "time_rules", "A final video moved a work's start to the completion day",
          "The reason read \"complete 0 days after the work could start\" instead of counting "
          "from the sanction.", "T170, 20 Oct 2026", "fixed",
          "A final video never sets the start.",
          guard="tests/agents/time_rules/test_time_rules_t168.py::test_a_final_video_never_moves_the_start_the_pace_is_counted_from"),
    Entry("M-SYS-6", "form page", "The form page gave a wrong reason when Cost could not check",
          "After a rate change Cost waits for a reason (the total differs from the MP's amount); "
          "the page said \"No prices to compare with\".", "T170, 20 Oct 2026", "fixed",
          "The page shows the agent's own reason and the missing answer.",
          guard="start-to-end browser check (T170 log)"),
    Entry("M-SYS-7", "form page", "The live demo check judged examples on the wrong day",
          "Examples were judged on the data's snapshot day, not their own (6 of 13 wrong live).",
          "T164, 9 Oct 2026", "fixed", "The demo check uses the examples' own day (demo.as_of).",
          guard="data/trial/work_form_examples.py (stops when the demo path differs)"),
]
