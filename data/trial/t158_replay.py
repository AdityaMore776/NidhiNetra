r"""T158 replay: recorded walks through the engine, and the phone's maths against the engine's.

Part 1, the engine (video/visit.py + Site Progress) on drawn site videos (the T124 test scenes:
five viewpoints, GPS and compass logs as a phone writes them):
    a  monthly visit from the same spots, panning the whole of last time's view
    b  the same, but viewpoint v2 filmed 25 m from its spot
    c  the same, but at viewpoint v3 only half of last time's view panned
    d  a phone with no compass
    e  a big work (8 spots needed) with 5 filmed: a part claim "not shown" at every spot, and a
       whole-work claim "not shown" at one spot
    f  a 190 m road: the stretches asked, walked halfway
Part 2, the phone (apps/web/src/lib/capture.ts, run in Node 24) on the same inputs as the engine's
spots.covered, sitemap.stretch_of and metres: they must agree.

Nothing here is real filming: it checks the guidance and the readings behave as the plan says
(docs/plans/T158-same-spot-filming.md). The proof on a real phone is the owner's walk test.
Run from the repo root with the engine's venv (+ OpenCV, data/requirements-video.txt):
    apps\engine\.venv\Scripts\python.exe data\trial\t158_replay.py
Writes data/trial/results/t158_replay.txt.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "apps" / "engine"))

from drishti.agents.site_progress import agent, sitemap, spots
from drishti.video import visit as vv
from tests.video.test_video_visit import (
    LINE,
    SITE,
    earlier_from,
    film,
    moved,
    scene,
    walked,
    with_compass,
)

OUT = ROOT / "data" / "trial" / "results" / "t158_replay.txt"


def judge_by(verdicts: dict):
    def judge(claims, photos):
        vid = photos[-1][0].split("-", 1)[1]
        return [{"verdict": verdicts.get(vid, "shown"), "reason": f"at {vid}"} for _ in claims]
    return judge


def notes_of(readings: dict, base_readings: dict) -> list[str]:
    w = {"work_id": "R1", "status": "SANCTIONED", "cost_form": {"work": {"nature": "new"}},
         "site_visits": [
             {"visit_id": "b", "kind": "baseline", "captured_at": "2026-03-01", "claim": None,
              "readings": base_readings},
             {"visit_id": "m", "kind": "monthly", "captured_at": "2026-04-01",
              "claim": "walls up to lintel level", "readings": readings}]}
    r = agent.assess(w, date(2026, 4, 2))
    return [f.code for f in r.findings] + [n for n in r.evidence.get("notes", [])
                                           if "spot" in n or "viewpoint v" in n
                                           or "stretch" in n]


def engine(lines: list[str]) -> None:
    d = Path(tempfile.mkdtemp(prefix="t158_"))
    base_log = with_compass(film(d / "base.mp4", scene(1)))
    # a wall built since: the same scene again would be the same pixels (reused footage)
    month_log = film(d / "m1.mp4", scene(1, wall=True))
    base_r, base_k = vv.read(d / "base.mp4", base_log, SITE, [], [], "baseline")
    prev = earlier_from("R1", "b", "baseline", base_k, base_r)
    lines.append("Part 1: the engine on drawn site videos (5 viewpoints, phone-style GPS + "
                 "compass logs)")
    lines.append(f"  baseline: spots kept {sorted(base_k['viewpoints'])}, v2 facing "
                 f"{base_k['viewpoints']['v2']['facing']}, pans per viewpoint "
                 f"{len(base_k['viewpoints']['v2']['pans'])}")

    cases = {
        "a same spots, whole pan": with_compass(month_log),
        "b v2 filmed 25 m off": moved(with_compass(month_log), "v2", 0.000225),
        "c v3 half panned": with_compass(month_log, only={"v3": (120.0, 20.0)}),
        "d no compass": month_log,
    }
    for name, log in cases.items():
        r, _ = vv.read(d / "m1.mp4", log, SITE, [prev], [], "monthly")
        lines.append(f"  {name}: offsets_m {r['spot_offsets_m']} coverage {r['spot_coverage']}")
        lines.append(f"      Site Progress: {notes_of(r, base_r) or ['nothing to note']}")

    no = {f"v{k}": "not_shown" for k in range(1, 6)}
    for claim, verdicts in (("toilet block roof cast", no),
                            ("walls up to lintel level in all rooms", {"v2": "not_shown"})):
        for needed in (8, 12):
            r, _ = vv.read(d / "m1.mp4", month_log, SITE, [prev], [], "monthly", claim=claim,
                           judge=judge_by(verdicts), spots_needed=needed)
            lines.append(f"  e {claim!r}, {needed} spots needed, {r['spots_filmed']} filmed, "
                         f"spot verdicts {r['spot_verdicts']} -> claim {r['claim_verdict']}")

    rb, kb = vv.read(d / "base.mp4", walked(base_log), LINE, [], [], "baseline")
    half = dict(walked(month_log))
    half["gps"] = [g for g in half["gps"] if g["lat"] < 25.7509]
    r, _ = vv.read(d / "m1.mp4", half, LINE, [earlier_from("R1", "b", "baseline", kb, rb)], [],
                   "monthly", claim="road surfaced", judge=judge_by({}),
                   stretches_asked=LINE.stretches())
    lines.append(f"  f road of {LINE.length_m:.0f} m, stretches {LINE.stretches()}: first visit "
                 f"kept {sorted(kb['stretches'])}; walked halfway -> judged "
                 f"{sorted(k for k in r['spot_verdicts'] if k.startswith('s'))}, missed "
                 f"{r['stretches_missed']}")


def parity(lines: list[str]) -> bool:
    road = sitemap.Site("linear", 25.75, 82.69, 12.5, 25.78, 82.70)
    arcs = [spots.arc([60, 150]), spots.arc([350, 20]), spots.arc([100, 102]), spots.arc([10, 300])]
    degs = [list(range(60, 151, 5)), list(range(60, 106, 5)), [355, 0, 5, 10, 15], [110], [150],
            [], list(range(300, 361, 7))]
    covered = [{"arc": a, "degs": g} for a in arcs for g in degs]
    pts = [(25.75 + i * 0.0021, 82.69 + i * 0.0007) for i in range(15)] + [(25.76, 82.72)]
    stretch = [{"site": road.to_json(), "lat": la, "lon": lo} for la, lo in pts]
    mpairs = [[25.75, 82.69, 25.75 + i * 0.0001, 82.69 + i * 0.00013] for i in range(6)]
    anchor = {"lat": 25.75, "lon": 82.69, "acc": 6.0, "box_m": 6.0}
    box = [{"anchor": anchor, "fix": {"lat": 25.75 + dl, "lon": 82.69, "accuracy": acc,
                                      "speed": None}}
           for dl, acc in ((0.00003, 5), (0.00009, 5), (0.00009, 12), (0.0003, 5))]
    cases = {"covered": covered, "stretch": stretch, "metres": mpairs, "box": box,
             "bearing": [[25.75, 82.69, 25.76, 82.69], [25.75, 82.69, 25.75, 82.70],
                         [25.75, 82.69, 25.74, 82.69], [25.75, 82.69, 25.75, 82.68]],
             "turn": [[350, 10], [10, 350], [0, 180], [90, 45]]}
    run = subprocess.run(["node", str(ROOT / "data" / "trial" / "t158_parity.ts")],
                         input=json.dumps(cases), capture_output=True, text=True, check=True)
    web = json.loads(run.stdout)
    want = {
        "covered": [spots.covered(c["arc"], c["degs"]) for c in covered],
        "stretch": [road.stretch_of(la, lo) for la, lo in pts],
        "metres": [round(sitemap.metres(*m), 3) for m in mpairs],
        "box": [sitemap.metres(25.75, 82.69, b["fix"]["lat"], 82.69) - b["fix"]["accuracy"]
                <= anchor["box_m"] for b in box],
    }
    ok = True
    lines.append("Part 2: the phone's maths (capture.ts in Node) against the engine's")
    for k, engine_vals in want.items():
        page = [round(x, 3) if isinstance(x, float) else x for x in web[k]]
        same = page == engine_vals
        ok &= same
        lines.append(f"  {k:8s} {len(engine_vals):3d} cases: {'same' if same else 'DIFFERENT'}"
                     + ("" if same else f"\n    engine {engine_vals}\n    page   {page}"))
    lines.append(f"  bearing  north/east/south/west: {[round(b) for b in web['bearing']]}")
    lines.append(f"  turn     350->10, 10->350, 0->180, 90->45: {web['turn']}")
    return ok


def main() -> int:
    lines = ["T158 replay (docs/plans/T158-same-spot-filming.md)", ""]
    engine(lines)
    lines.append("")
    ok = parity(lines)
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
