"""The four agents on damaged forms and site videos (T135, the robustness loop's random damage,
data/trial/agent_robustness_loop.py, small enough for CI).

The agents now read mostly what agencies type: the website's work form (any field may hold junk),
the engine's own cost estimate form, and the site videos' readings. None of that may crash an
agent (an ERROR result), break the contract (risks in 0..1), or answer differently twice. The loop
found three crashes this way (infinity in the estimated duration, NaN and infinity as a frame
count, a list where a unit belongs)."""

from __future__ import annotations

import copy
import random
from datetime import date, timedelta

import pytest

from drishti.agents.contract import Status
from drishti.batch import indexes
from drishti.cost_form import pswif
from drishti.pipeline.orchestrator import Context, assess_work
from tests.cost_form.test_pswif import road

AS_OF = date(2026, 10, 2)
FOUR = ("cost_estimate", "dup_split", "time_rules", "site_progress")
JUNK = [None, "", " ", "abc", "NaN", float("nan"), float("inf"), -1, 0, 1e15, -1e9, "1,00,000",
        "₹5 lakh", [], {}, [1, 2], {"x": 1}, True, "2026-02-30", "31/12/2025", "9999-99-99",
        "मंदिर", "\u0000", "x" * 3000, 12.5, "12.5", "-0", "1e400"]


def _visits(start: date) -> list[dict]:
    out = []
    for i in range(4):
        out.append({"visit_id": f"V{i + 1}", "kind": "baseline" if i == 0 else "monthly",
                    "captured_at": (start + timedelta(days=30 * i)).isoformat(),
                    "claim": None if i == 0 else f"stage {i}",
                    "readings": {"sealed": True, "in_app": True, "gps_inside": True,
                                 "views_match_site": None if i == 0 else True,
                                 "change": None if i == 0 else "changed",
                                 "claim_verdict": None if i == 0 else "shown",
                                 "reused_from": [{"work_id": "W9", "frames": 1}],
                                 "same_place_as": [{"work_id": "W9", "inliers": 3}]}})
    return out


@pytest.fixture(scope="module")
def world():
    forms, works = [], []
    for i in range(8):
        p = road(recommendation_ref=f"WF-{i}", implementing_agency=f"Agency {i % 4}",
                 district="Jaunpur")
        forms.append(p)
        w = pswif.to_work(p, district_lgd="181", today=AS_OF, status="SANCTIONED",
                          site_visits=_visits(date(2026, 7, 1)))
        works.append(w)
    return forms, works, Context(stats=None, as_of=AS_OF, data=indexes(works))


def _walk(rng: random.Random, x):
    if isinstance(x, dict):
        for k in list(x):
            if rng.random() < 0.15:
                x[k] = rng.choice(JUNK)
            else:
                _walk(rng, x[k])
    elif isinstance(x, list):
        for i in range(len(x)):
            if rng.random() < 0.15:
                x[i] = rng.choice(JUNK)
            else:
                _walk(rng, x[i])


def _answers(a):
    return [(r.agent, r.status, tuple(sorted(f.code for f in r.findings))) for r in a.agents]


def test_damaged_forms_and_videos_never_break_an_agent(world):
    forms, works, ctx = world
    rng = random.Random(135)
    for i in range(300):
        k = rng.randrange(len(forms))
        if i % 2:
            p = copy.deepcopy(forms[k])
            for key in rng.sample(sorted(p), k=rng.randint(1, 25)):
                p[key] = rng.choice(JUNK)
            w = pswif.to_work(p, district_lgd="181", today=AS_OF,
                              site_visits=_visits(date(2026, 7, 1)))
        else:
            w = copy.deepcopy(works[k])
            _walk(rng, w.get("cost_form"))
            _walk(rng, w.get("site_visits"))
            for key in ("amount", "status", "sanction_date", "completed_date", "agency_name"):
                if rng.random() < 0.2:
                    w[key] = rng.choice(JUNK)
        a = assess_work(copy.deepcopy(w), ctx)
        for r in a.agents:
            if r.agent in FOUR:
                assert r.status != Status.ERROR, (i, r.agent, r.headline)
                assert 0.0 <= r.risk <= 1.0 and all(0 <= f.risk <= 1 for f in r.findings)
        assert _answers(a) == _answers(assess_work(copy.deepcopy(w), ctx)), i
