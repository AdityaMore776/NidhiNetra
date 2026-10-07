r"""T151-T155: the claim judge's data and scores, as sanitised counts (no names, no photos, no work names).

Reads the data folder on D: (never in git) and writes data/trial/results/vlm_trial.txt and .json:
    sources     MGNREGA assets by split, district count, work type, stages present; certainty pass rates
    items       the claim-ladder card: items by split, trick, verdict, real vs edited
    scores      every *_score.json under the runs folder: the headline (real photos only), per trick

    python data/trial/vlm_trial.py --data D:\nidhinetra-data --items D:\nidhinetra-data\vlm\v1
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _vlmdata():
    import sys
    sys.path.insert(0, str(ROOT / "apps" / "vision"))
    from drishti_vision import vlmdata
    return vlmdata


def split_of(district: str) -> str:
    return _vlmdata().split_of(district)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--items", required=True, help="the vlmbuild output folder")
    ap.add_argument("--runs", default="", help="folder with *_score.json files")
    a = ap.parse_args()
    data, items_dir = Path(a.data), Path(a.items)
    out: dict = {}
    lines = ["T151-T155: the claim judge's data and scores (sanitised counts)", ""]

    assets = [json.loads(x) for x in (items_dir / "assets.jsonl").read_text(
        encoding="utf-8").splitlines() if x.strip()]
    by_split = Counter(split_of(x["district_code"]) for x in assets)
    districts = {sp: len({x["district_code"] for x in assets if split_of(x["district_code"]) == sp})
                 for sp in by_split}
    stages = Counter(tuple(sorted({p["stage"] for p in x["photos"]})) for x in assets)
    ok13 = sum(bool((x.get("change") or {}).get("ok_13")) and _vlmdata().structural(x)
               for x in assets)
    out["sources"] = {"mgnrega_assets": len(assets), "by_split": dict(by_split),
                      "districts_by_split": districts,
                      "work_types": dict(Counter(x["work_type"] for x in assets)),
                      "stages_present": {"-".join(map(str, k)): v for k, v in stages.items()},
                      "certain_progress_assets": ok13}
    lines += ["1. GeoMGNREGA assets (photos at stage 1 before, 2 during, 3 after)", "",
              f"  assets {len(assets)}: " + ", ".join(f"{k} {v} ({districts[k]} districts)"
                                                    for k, v in sorted(by_split.items())),
              "  work types: " + ", ".join(f"{k} {v}" for k, v in
                                           Counter(x["work_type"] for x in assets).most_common()),
              "  stages present: " + ", ".join(f"{'-'.join(map(str, k))}: {v}"
                                               for k, v in stages.most_common()),
              f"  progress certain (change beats own noise, structural): {ok13} of {len(assets)}",
              ""]

    rows = [json.loads(x) for x in (items_dir / "items.jsonl").read_text(
        encoding="utf-8").splitlines() if x.strip()]
    out["items"] = {}
    lines += ["2. Claim-ladder items", ""]
    for sp in ("train", "calib", "test"):
        its = [r for r in rows if r["split"] == sp]
        if not its:
            continue
        c = {"n": len(its), "real": sum(r["real"] for r in its),
             "verdicts": dict(Counter(r["target"]["verdict"] for r in its)),
             "tricks": dict(Counter(r["trick"] + ("" if r["real"] else " (edited)") for r in its)),
             "sources": dict(Counter(r["source"] for r in its))}
        out["items"][sp] = c
        lines += [f"  {sp}: {c['n']} items, {c['real']} real and unedited",
                  "    verdicts: " + ", ".join(f"{k} {v}" for k, v in sorted(c["verdicts"].items())),
                  "    tricks: " + ", ".join(f"{k} {v}" for k, v in sorted(c["tricks"].items())),
                  "    sources: " + ", ".join(f"{k} {v}" for k, v in sorted(c["sources"].items()))]
    lines.append("")

    if a.runs:
        out["scores"] = {}
        lines += ["3. Scores (headline: real, unedited test photos only)", ""]
        for p in sorted(Path(a.runs).rglob("*_score.json")):
            s = json.loads(p.read_text())
            h = s["headline_real_only"]
            name = str(p.relative_to(a.runs)).replace("\\", "/")
            out["scores"][name] = s
            fmt = (lambda v: "n/a" if v is None else f"{v:.3f}")
            ci = h.get("fooled_rate_ci95") or (None, None)
            lines += [f"  {name}: n {h['n']}, macro-F1 {fmt(h['macro_f1'])}, accuracy "
                      f"{fmt(h['accuracy'])}, fooled {fmt(h['fooled_rate'])} "
                      f"[{fmt(ci[0])}, {fmt(ci[1])}] of {h['n_no_progress']} no-progress pairs, "
                      f"missed {fmt(h['missed_rate'])} of {h['n_progress']} progress pairs, "
                      f"answers {fmt(h['answered_share'])}, ECE {fmt(h.get('ece'))}"]
            if s.get("cost"):
                lines.append(f"    {s['cost']['seconds_per_check']} s a check, "
                             f"Rs {s['cost']['rupees_per_1000_checks_local']} per 1,000 checks")
            per = s.get("per_trick", {})
            lines.append("    per trick: " + ", ".join(f"{k} {v['accuracy']:.2f} (n {v['n']})"
                                                     for k, v in per.items()))
        lines.append("")
    res = ROOT / "data" / "trial" / "results"
    (res / "vlm_trial.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (res / "vlm_trial.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
