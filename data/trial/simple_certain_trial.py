r"""The owner's "simple and certain" pivot (3 Oct 2026): can a cost or repeat question be certain
from the eSAKSHI record alone?

COST (T099). The Cost Estimate engine's reference (agents/cost_estimate/reference.py) is built
for every state from the dashboard's 40,935 works. A record states its size only as a count of a
standard item (solar street lights, high masts, CCTV, water tanks); for those, the record's price
per unit is compared with the engine's question line (more than 25% above the 98th percentile of
a tight group of the same item in the district or state):
  in-sample   the reference from every year, every real work compared
  hold-out    the reference from works before 2026, the works of 2026 compared, and the same
              works priced 1.1x to 3x (planted)
Every real work above the line is listed by work id and read by eye (simple_certain_labels.py).

REPEAT (T100). The team's 289 repeat pairs read by eye for T030 and T051 (dup_split_labels.py,
dup_split_v2_labels.py; "same" = one asset funded twice) are re-read from their saved
descriptions by stricter and stricter text rules (agents/dup_split/match.py's word readers):
precision and recall of each. Then the strictest rule on the dashboard's own works: its pairs by
how far apart they are, and the 25 more than 60 days apart read by eye.

Writes results/simple_certain_trial.json (work ids, counts and rates only) and prints a summary.

Run:  apps\engine\.venv\Scripts\python.exe data\trial\simple_certain_trial.py
"""

from __future__ import annotations

import csv
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "data"))
sys.path.insert(0, str(ROOT / "data" / "trial"))
sys.path.insert(0, str(ROOT / "apps" / "engine"))
import dup_split_labels as L1  # noqa: E402
import dup_split_v2_labels as L2  # noqa: E402
import simple_certain_labels as LS  # noqa: E402
from esakshi_dashboard import load  # noqa: E402

from drishti.agents.cost_estimate import reference as R  # noqa: E402
from drishti.agents.dup_split import match as M  # noqa: E402

RESULTS = ROOT / "data" / "trial" / "results"
OUT = RESULTS / "simple_certain_trial.json"
LINE = 1.25                      # the Cost engine's PRICE_MARGIN over the 98th percentile
PLANTED = (1.1, 1.25, 1.5, 2.0, 3.0)
PAIR_FILES = [(L1.DEV, "dup_split_pairs_dev.csv"), (L1.TEST1, "dup_split_pairs_test1.csv"),
              (L1.TEST2, "dup_split_pairs_test2.csv"), (L2.DEV1, "dup_split_v2_pairs_dev1.csv"),
              (L2.DEV2, "dup_split_v2_pairs_dev2.csv"), (L2.TEST, "dup_split_v2_pairs_test.csv"),
              (L2.TEST2, "dup_split_v2_pairs_test2.csv")]
MANY = re.compile(r"various|different|vibhinn|vividh|several|villages|schools|places|sthano",
                  re.I)


def _year(w: dict) -> int | None:
    d = w.get("recommended_date") or w.get("completed_date")
    return d.year if isinstance(d, date) else None


def cost(works: list[dict]) -> dict:
    states = sorted({w["state_name"] for w in works if w.get("state_name")})
    used: Counter = Counter()
    above: list[dict] = []
    for st in states:
        ref = R.build(works, st, "every year")
        for w in works:
            if w.get("state_name") != st or not (got := R.record_price(w)):
                continue
            g, where, _ = R.group(ref, got[0], w.get("district_name"))
            if not g:
                continue
            used[f"{st} | {got[0]}"] += 1
            if got[2] > LINE * g["p98"]:
                above.append({"work_id": w["work_id"], "group": got[0], "where": where,
                              "price": round(got[2]), "median": g["median"], "p98": g["p98"]})
    hold = {"compared": 0, "above": [], "planted": {f"x{k:g}": 0 for k in PLANTED}}
    for st in states:
        train = [w for w in works if w.get("state_name") == st and (_year(w) or 9999) < 2026]
        ref = R.build(train, st, "before 2026")
        for w in works:
            if w.get("state_name") != st or _year(w) != 2026 or not (got := R.record_price(w)):
                continue
            g, where, _ = R.group(ref, got[0], w.get("district_name"))
            if not g:
                continue
            hold["compared"] += 1
            if got[2] > LINE * g["p98"]:
                hold["above"].append({"work_id": w["work_id"], "group": got[0], "where": where,
                                      "price": round(got[2]), "median": g["median"],
                                      "p98": g["p98"]})
            for k in PLANTED:
                hold["planted"][f"x{k:g}"] += got[2] * k > LINE * g["p98"]
    read = Counter(LS.COST_RECORD_ABOVE.get(a["work_id"], "unread")
                   for a in {a["work_id"]: a for a in above + hold["above"]}.values())
    return {"works": len(works), "compared_in_sample": sum(used.values()),
            "groups_used": dict(sorted(used.items())), "above_in_sample": above,
            "hold_out": hold, "above_read_by_eye": dict(read)}


def _features(a: str, b: str) -> dict:
    pa, pb = M.place_words(a), M.place_words(b)
    return {"normeq": " ".join(x for x in M.words(a) if x not in M.FILLER)
            == " ".join(x for x in M.words(b) if x not in M.FILLER),
            "text": M.text_sim(a, b), "places": min(len(pa.split()), len(pb.split())),
            "place": M.place_agreement(pa, pb),
            "apart": (M.site_numbers(a) != M.site_numbers(b) or bool(M.sides(a) ^ M.sides(b))
                      or bool(M.genders(a) ^ M.genders(b))),
            "staged": bool(M.STAGED.search(a) or M.STAGED.search(b)),
            "many": bool(MANY.search(a + " " + b))}


RULES = {
    "every pair the engine flagged": lambda f: True,
    "identical wording": lambda f: f["normeq"],
    "90%+ alike": lambda f: f["text"] >= 0.9,
    "90%+ alike, every place word shared": lambda f: f["text"] >= 0.9 and f["place"] == 100,
    "... and nothing apart, no continuation word, not many sites": lambda f: (
        f["text"] >= 0.9 and f["place"] == 100 and f["places"] >= 1 and not f["apart"]
        and not f["staged"] and not f["many"]),
    "... and two or more place words": lambda f: (
        f["text"] >= 0.9 and f["place"] == 100 and f["places"] >= 2 and not f["apart"]
        and not f["staged"] and not f["many"]),
    "identical wording, two or more place words, nothing apart": lambda f: (
        f["normeq"] and f["places"] >= 2 and not f["apart"] and not f["staged"]
        and not f["many"]),
}


def repeat_labelled() -> dict:
    pairs: dict[tuple, dict] = {}
    for labels, name in PAIR_FILES:
        with open(RESULTS / name, encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                lab = labels.get((r["a"], r["b"])) or labels.get((r["b"], r["a"]))
                key = tuple(sorted((r["a"], r["b"])))
                if lab is not None and key not in pairs:
                    pairs[key] = {"label": lab, **_features(r["desc_a"], r["desc_b"])}
    same = sum(p["label"] == "same" for p in pairs.values())
    out = {"pairs": len(pairs), "same": same, "rules": {}}
    for name, rule in RULES.items():
        hit = [p for p in pairs.values() if rule(p)]
        s = sum(p["label"] == "same" for p in hit)
        out["rules"][name] = {"flagged": len(hit), "same": s,
                              "precision": round(s / max(1, len(hit)), 3),
                              "recall": round(s / max(1, same), 3)}
    return out


def repeat_dashboard(works: list[dict]) -> dict:
    idx = M.DupIndex.build(works)
    gaps: Counter = Counter()
    found = []
    for recs in idx.by_district.values():
        postings: dict[str, list[int]] = defaultdict(list)
        for i, r in enumerate(recs):
            for p in set(r.place.split()):
                postings[p].append(i)
        for i, ra in enumerate(recs):
            for j in {j for p in set(ra.place.split()) for j in postings[p] if j > i}:
                rb = recs[j]
                f = _features(ra.description, rb.description)
                if (ra.work_type != rb.work_type or not RULES[
                        "... and nothing apart, no continuation word, not many sites"](f)
                        or ra.copies >= M.SERIES_COPIES or rb.copies >= M.SERIES_COPIES
                        or ra.segment != rb.segment):
                    continue
                da, db = ra.done or ra.rec, rb.done or rb.rec
                gap = abs((da - db).days) if da and db else None
                band = ("unknown" if gap is None else "0-7 days" if gap <= 7 else
                        "8-60 days" if gap <= 60 else "over 60 days")
                gaps[band] += 1
                if gap is not None and gap > 60:
                    found.append((ra.work_id, rb.work_id))
    read = Counter(LS.REPEAT_DASHBOARD_PAIRS.get(p) or LS.REPEAT_DASHBOARD_PAIRS.get(p[::-1])
                   or "unread" for p in found)
    return {"pairs_by_gap": dict(gaps), "over_60_days_read_by_eye": dict(read)}


def main() -> None:
    works, info = load()
    out = {"source": f"eSAKSHI dashboard tables, {info['works']:,} works, as of {info['as_of']}",
           "cost": cost(works), "repeat_labelled_pairs": repeat_labelled(),
           "repeat_dashboard": repeat_dashboard(works)}
    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    c, h = out["cost"], out["cost"]["hold_out"]
    print(f"COST: {c['compared_in_sample']:,} of {c['works']:,} works can be priced from the "
          f"record ({len(c['groups_used'])} groups)")
    print(f"  in-sample above the line: {len(c['above_in_sample'])}; hold-out: "
          f"{len(h['above'])} of {h['compared']} real 2026 works")
    print(f"  read by eye: {c['above_read_by_eye']}")
    print(f"  planted (hold-out): " + ", ".join(f"{k} {v}/{h['compared']}"
                                                for k, v in h["planted"].items()))
    r = out["repeat_labelled_pairs"]
    print(f"REPEAT: {r['pairs']} labelled pairs, {r['same']} read as one asset funded twice")
    for name, s in r["rules"].items():
        print(f"  {name:62} {s['same']:3}/{s['flagged']:<3} right ({s['precision']:.0%}), "
              f"recall {s['recall']:.0%}")
    d = out["repeat_dashboard"]
    print(f"  dashboard, strictest rule: {d['pairs_by_gap']}; over 60 days read: "
          f"{d['over_60_days_read_by_eye']}")
    print(f"wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
