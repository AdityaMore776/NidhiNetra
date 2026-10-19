r"""The eval world shared by the four agents' evals (T168, plan docs/plans/T168-agent-evals.md §8).

A district (the real Jaunpur, made-up agencies and works) with honest background filings by other
agencies, and labelled cases run through the four agents exactly as the website's form check runs
them: `orchestrator.assess_work` with the district's indexes rebuilt with the case's own earlier
works and the case in it. Nothing here is a real agency, person or work.

A case carries its truth and the levels its label allows (levels.py):

  truth    honest   an ordinary honest work
           edge     honest, but unusual: it looks like a problem on some measure
           fraud    a scheme an agency could try
           evasion  a fraud dressed to slip past a rule
           broken   missing or damaged data: "couldn't check" is right, a clean chit is not
  agent    the agent the case is about (dup_split, time_rules, site_progress, or "pipeline")
  scope    "self", or "other" for a fraud this agent cannot see (another agent's job: listed,
           never counted as coverage)

Each case runs in two worlds: a sparse district (a dozen honest filings) and a dense one (seventy,
some of them honest street lights at houses 8-20 m apart, the T139 pattern), so a level must hold
however busy the district's index is.
"""

from __future__ import annotations

import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, timedelta
from functools import cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
for p in (ROOT / "data", ROOT / "data" / "trial", ROOT / "apps" / "engine"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))
import work_form_examples as wf  # noqa: E402

from drishti import records  # noqa: E402
from drishti.agents.contract import AgentResult  # noqa: E402
from drishti.batch import indexes  # noqa: E402
from drishti.cost_form import pswif  # noqa: E402
from drishti.evaluation.stats import build_store  # noqa: E402
from drishti.fusion.fuse import Fused  # noqa: E402
from drishti.pipeline.orchestrator import Context, assess_work  # noqa: E402

AS_OF = date(2026, 10, 2)
PLACE = {"district_lgd": "194", "state_lgd": "09", "state_name": "Uttar Pradesh",
         "district_name": "Jaunpur"}
METRE = wf.METRE
AGENCY = "Nirman Seva Agency"            # most cases' filing agency (never in the background)
OTHER = ["Lok Nirman Mandal", "Sadak Vikas Prakoshth", "Nagar Seva Kendra", "Gram Unnati Agency",
         "Shramik Works Cooperative"]
BG_K = 60                                # background sites start at pin 60: far from every case


def m(days: int) -> date:
    """`days` before the eval's today."""
    return AS_OF - timedelta(days=days)


def d(x: date) -> str:
    return x.isoformat()


def place(w: dict) -> dict:
    w.update(PLACE)
    return w


def filed(p: dict, **record) -> dict:
    """A filled form as the engine's work record, in the district (pswif.to_work)."""
    return place(pswif.to_work(p, today=AS_OF, **record))


@dataclass
class World:
    name: str
    background: list[dict]
    as_of: date = AS_OF


@dataclass
class Case:
    id: str
    agent: str
    truth: str
    ideal: str
    allowed: tuple[str, ...]
    family: str
    story: str
    why: str
    work: Callable[[], dict]                       # the work as the engine reads it
    extra: Callable[[], list[dict]] = list          # its earlier works in the district
    pair: str | None = None
    scope: str = "self"
    notes: dict = field(default_factory=dict)


@dataclass
class Run:
    results: dict[str, AgentResult]
    fused: Fused


def _background(n_roads: int, n_halls: int, n_light_runs: int) -> list[dict]:
    bg, k = [], BG_K
    for i in range(n_roads):
        p = wf.road(f"EV-BG-R{i}", OTHER[i % 5], wf.BG_VILLAGES[i % 7], k, m(400 - 9 * i),
                    m(360 - 9 * i), length=220 + 15 * i)
        bg.append(filed(p, status="COMPLETED", completed_date=d(m(200 - 4 * i))))
        k += 1
    for i in range(n_halls):
        p = wf.hall(f"EV-BG-H{i}", OTHER[(i + 2) % 5], wf.BG_VILLAGES[(i + 3) % 7], k,
                    m(380 - 11 * i), m(340 - 11 * i), area=140 + 10 * i)
        bg.append(filed(p, status="SANCTIONED"))
        k += 1
    for run in range(n_light_runs):
        # one programme: ten lights at ten houses 8-20 m apart, filed the same day (T139)
        lat, lon = wf.pin(k)
        for j in range(10):
            p = wf.lights(f"EV-BG-L{run}-{j}", OTHER[run % 5], f"Basti {run}", k, m(300 - run),
                          30_000, 300_000, latitude=f"{lat + 8 * j * METRE:.6f}",
                          longitude=f"{lon + (j % 2) * 12 * METRE:.6f}")
            bg.append(filed(p, status="COMPLETED", completed_date=d(m(250 - run)),
                            sanction_date=d(m(290 - run))))
        k += 1
    return bg


WORLDS = {"sparse": (8, 4, 0), "dense": (30, 20, 2)}


@cache
def world(name: str) -> World:
    return World(name, _background(*WORLDS[name]))


def run(case: Case, w: World) -> Run:
    """The four agents on the case, as POST /work-form/check runs them."""
    work = case.work()
    extra = case.extra()
    pool = [records.work(x) for x in [*w.background, *extra, work]]
    ctx = Context(stats=build_store(pool), as_of=w.as_of, data=indexes(pool))
    a = assess_work(work, ctx)
    return Run({r.agent: r for r in a.agents}, a.fused)
