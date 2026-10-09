r"""T164 (9 Oct 2026): the owner's review: each of the Cost agent's checks, and the four agents end to
end. Two measurements, each written to data/trial/results/:

  live      every example filing on the website (13 on /work-form, 5 on /end-to-end) sent to the
            LIVE site's form check (POST /api/v1/work-form/check?demo=true, what "Check this form"
            does), each agent's questions compared with the verdict the page shows for it
            -> results/t164_live_<label>.txt
  guard     the Cost agent on Jaunpur's honest example road with one rate set just under and just
            over the form's typing-mistake guard (cement: Rs 3,000 a bag; masons: Rs 10,000 a
            day), the warning never answered -> results/t164_guard.txt

The live run needs only the internet. The guard run needs the district's works: the eSAKSHI
dashboard tables (data/raw/esakshi_dashboard, team pack), or with --standin the research export's
Uttar Pradesh works (data/build/works.parquet) dated as the examples' own day (2 Oct 2026), for a
machine without the tables (the agent robustness loop gives the same 118 answers on both).

Run:  apps\engine\.venv\Scripts\python.exe data\trial\t164_review.py live [--url URL] [--label L]
      apps\engine\.venv\Scripts\python.exe data\trial\t164_review.py guard [--standin]
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "data" / "trial" / "results"
PUBLIC = ROOT / "apps" / "web" / "public"
sys.path.insert(0, str(ROOT / "data"))
sys.path.insert(0, str(ROOT / "data" / "trial"))
sys.path.insert(0, str(ROOT / "apps" / "engine"))


# ---- live: the website's examples through the live form check ------------------------------------

def _asked(trace: dict) -> dict[str, tuple[str, list[str]]]:
    return {c["id"]: (c["status"], sorted(f["code"] for f in c.get("findings") or []
                                          if (f.get("risk") or 0) > 0))
            for c in trace["checks"]}


def _band(trace: dict):
    r = trace.get("result") or {}
    return r.get("score"), r.get("band")


def _post(req: urllib.request.Request) -> dict:
    for attempt in range(3):          # the host sometimes drops a connection: try again
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                return json.load(r)
        except OSError:
            if attempt == 2:
                raise
            time.sleep(5)
    raise AssertionError


def live(url: str, label: str) -> None:
    lines = [f"T164 live check: {url}/api/v1/work-form/check?demo=true, {time.strftime('%Y-%m-%d')}",
             ""]
    differ = 0
    for page in ("work-form", "end-to-end"):
        examples = json.loads((PUBLIC / page / "examples.json").read_text(encoding="utf-8"))
        for ex in examples["examples"]:
            req = urllib.request.Request(f"{url}/api/v1/work-form/check?demo=true",
                                         data=json.dumps(ex["form"]).encode(), method="POST",
                                         headers={"Content-Type": "application/json"})
            t0 = time.time()
            body = _post(req)
            got, want = _asked(body["trace"]), _asked(ex["trace"])
            same = got == want and _band(body["trace"]) == _band(ex["trace"])
            differ += not same
            lines.append(f"[{page}] {ex['id']:15s} {'same' if same else 'DIFFERS'} "
                         f"({time.time() - t0:.1f} s), as of {body['trace']['as_of']}: score "
                         f"page {_band(ex['trace'])} live {_band(body['trace'])}")
            for agent in sorted(got):
                mark = "" if got[agent] == want.get(agent) else f"   <- page {want.get(agent)}"
                lines.append(f"    {agent:14s} {got[agent][0]:15s} "
                             f"{', '.join(got[agent][1]) or '-'}{mark}")
    lines += ["", f"examples whose live answer differs from the page's: {differ}",
              ("(the /end-to-end page is a static file: its dup_pieces and many_flags lean on "
               "filings the live demo data does not hold, so those two cannot match live)")]
    out = RESULTS / f"t164_live_{label}.txt"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print(f"wrote {out.relative_to(ROOT)}")


# ---- guard: one rate just under and just over the form's typing-mistake guard --------------------

def _standin() -> None:
    import esakshi_dashboard
    import pandas as pd

    def load(verbose: bool = False):
        w = pd.read_parquet(ROOT / "data" / "build" / "works.parquet")
        w = w[w.state_name == "Uttar Pradesh"]
        works = [{k: (None if (isinstance(v, float) and math.isnan(v)) or v is pd.NaT else v)
                  for k, v in r.items()} for r in w.to_dict("records")]
        return works, {"as_of": date(2026, 10, 2)}

    esakshi_dashboard.load = load


def guard(standin: bool) -> None:
    if standin:
        _standin()
    import agent_robustness_loop as L

    world = L.build_world()
    works = "research export (stand-in)" if standin else "eSAKSHI dashboard tables"
    lines = [(f"T164 typing-mistake guard: Jaunpur's honest example road (as of {world.as_of}), "
              f"one rate changed, its warning never answered; works: {works}"), ""]

    def row(what: str, res: dict, total: float) -> None:
        r = res["cost_estimate"]
        lines.append(f"{what:44s} estimate Rs {total:>12,.0f}  asked: "
                     f"{', '.join(L.flags(res, 'cost_estimate')) or 'nothing'}  "
                     f"(score {res['_score']})")
        lines.append(f"{'':44s} {r.headline[:150]}")

    for rate in (2900, 3100, 3800):
        p = L.form_of(world, "clean")
        rows = L.boq(p)
        rows[0]["rate"] = str(rate)
        p = L.retotal(L.set_boq(p, rows))
        p["mp_recommended_amount"] = p["mplads_share"]
        res = L.run(world, L.work_of(p, L.record_of(world, "clean"), world.place, world.as_of))
        row(f"cement Rs {rate:,} a bag ({rate / 380:.1f}x Rs 380)", res,
            float(p["technical_estimate"]))
    for rate in (9500, 10500):
        p = L.form_of(world, "clean")
        n = next(k.removeprefix("lab_trade_") for k, v in p.items()
                 if k.startswith("lab_trade_") and v == "mason")
        p[f"lab_rate_{n}"] = str(rate)
        p = L.retotal(p)
        p["mp_recommended_amount"] = p["mplads_share"]
        res = L.run(world, L.work_of(p, L.record_of(world, "clean"), world.place, world.as_of))
        row(f"masons Rs {rate:,} a day ({rate / 750:.1f}x Rs 750)", res,
            float(p["technical_estimate"]))
    out = RESULTS / "t164_guard.txt"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print(f"wrote {out.relative_to(ROOT)}")


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("live")
    a.add_argument("--url", default="https://nidhinetra-sih.vercel.app")
    a.add_argument("--label", default="now")
    b = sub.add_parser("guard")
    b.add_argument("--standin", action="store_true")
    args = ap.parse_args()
    if args.cmd == "live":
        live(args.url.rstrip("/"), args.label)
    else:
        guard(args.standin)


if __name__ == "__main__":
    main()
