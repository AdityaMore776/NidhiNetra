r"""Duplicate & Split v2 (T051): the engine's own rules, run on every real work, scored against
the pairs and groups read by eye for T030 (data/trial/dup_split_labels.py).

v1 compared descriptions with a meaning model offline; v2 runs the same rules inside the
engine with a lexical similarity, so any new recommendation can be compared. This script
measures what that costs or gains on the real corpus:

  labelled pairs   of the 130 T030 pairs read by eye (51 "same", 79 "different"), how many v2
                   still flags, split by label: it should keep the "same" ones
  labelled groups  of the 30 T030 groups (GROUPS_TEST), how many members v2 still groups
  counts           pairs / groups / works flagged, v1 vs v2
  fresh samples    40 random v2 pairs and 15 random v2 same-site groups that v1 never
                   flagged (never read before), written out for reading by eye; their labels
                   go in dup_split_v2_labels.py and the result in results/dup_split_v2.json

Run: apps\engine\.venv\Scripts\python.exe data\trial\dup_split_v2_trial.py
"""

from __future__ import annotations

import importlib.util
import json
import random
import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "data"))
from common import BUILD, works_records  # noqa: E402
from drishti.agents.dup_split.match import DupIndex  # noqa: E402

OUT = ROOT / "data" / "trial" / "results"


def _labels():
    spec = importlib.util.spec_from_file_location("l", ROOT / "data/trial/dup_split_labels.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def main() -> None:
    t0 = time.time()
    works = pd.read_parquet(BUILD / "works.parquet")
    recs = list(works_records(works))
    idx = DupIndex.build(recs)
    t_build = time.time() - t0
    for d in list(idx.by_district):
        idx._solve_district(d)
    t_solve = time.time() - t0 - t_build
    pairs = {(min(a, p["other"]), max(a, p["other"])): p
             for a, ps in idx._pairs.items() for p in ps}
    groups = {g["group_id"]: g for g in idx._groups.values()}
    print(f"index {t_build:.0f}s, solve {t_solve:.0f}s; pairs {len(pairs):,}, groups "
          f"{len(groups):,}", flush=True)

    L = _labels()
    lab = {}
    for name in ("DEV", "TEST1", "TEST2"):
        for (a, b), v in getattr(L, name).items():
            lab[(min(a, b), max(a, b))] = (name, v)
    spec = importlib.util.spec_from_file_location("l2", ROOT / "data/trial/dup_split_v2_labels.py")
    L2 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(L2)
    read_v2 = {}
    for name in ("DEV1", "DEV2", "TEST", "TEST2"):
        for (a, b), v in getattr(L2, name, {}).items():
            read_v2[(min(a, b), max(a, b))] = (name, v)
    read_group_ids = set(getattr(L2, "GROUPS_TEST", {})) | set(getattr(L2, "GROUPS_TEST2", {}))
    kept = {"same": [0, 0], "different": [0, 0]}
    for k, (_n, v) in lab.items():
        kept[v][1] += 1
        kept[v][0] += k in pairs
    gl = pd.read_csv(OUT / "dup_split_groups_test.csv")
    g_kept = []
    for r in gl.itertuples():
        members = r.members.strip("[]").replace("'", "").split(", ")
        mine = {idx._groups.get(m, {}).get("group_id") for m in members} - {None}
        g_kept.append({"group_id": r.group_id, "label": L.GROUPS_TEST.get(r.group_id),
                       "kind": r.kind, "kept": bool(mine)})
    gk = pd.DataFrame(g_kept)

    v1 = pd.read_parquet(BUILD / "dup_split.parquet")
    v1_pairs = set()
    for r in v1.itertuples():
        for p in json.loads(r.pairs or "[]"):
            v1_pairs.add((min(r.work_id, p["other"]), max(r.work_id, p["other"])))
    v1_grouped = {r.work_id for r in v1.itertuples() if r.group and r.group != "null"}
    kinds = pd.Series([p["kind"] for p in pairs.values()]).value_counts().to_dict()
    gkinds = pd.Series([g["kind"] for g in groups.values()]).value_counts().to_dict()
    res = {"seconds": {"index": round(t_build), "solve_all_districts": round(t_solve)},
           "works_compared": sum(len(v) for v in idx.by_district.values()),
           "pairs": {"v2": len(pairs), "v2_by_kind": kinds, "v1": len(v1_pairs),
                     "in_both": len(set(pairs) & v1_pairs)},
           "groups": {"v2": len(groups), "v2_by_kind": gkinds,
                      "v2_works": sum(g["size"] for g in groups.values()),
                      "v1_works": len(v1_grouped),
                      "works_in_both": len(set(idx._groups) & v1_grouped)},
           "t030_labelled_pairs_still_flagged": {k: {"kept": a, "of": b} for k, (a, b)
                                                 in kept.items()},
           "t030_labelled_groups_still_grouped": gk.groupby("label").kept.agg(
               ["sum", "count"]).to_dict("index")}
    # fresh samples never read before, for reading by eye. DEV1/DEV2 drew from v2-only pairs
    # (what the rules added); the TEST sample draws from ALL v2 pairs once the rules froze.
    res["v2_labels_still_flagged"] = {
        n: {v: sum(1 for k, (nn, vv) in read_v2.items() if nn == n and vv == v and k in pairs)
            for v in ("same", "different")} for n in {x for x, _ in read_v2.values()}}
    names = {x for x, _ in read_v2.values()}
    stage = ("test3" if "TEST2" in names else "test2" if "TEST" in names
             else "test" if "DEV2" in names else "fresh")
    rng = random.Random(51 + len({x for x, _ in read_v2.values()}))
    w = works.set_index("work_id")
    fresh = sorted(k for k in pairs if k not in lab and k not in read_v2
                   and (stage.startswith("test") or k not in v1_pairs))
    rows = []
    for a, b in rng.sample(fresh, min(40, len(fresh))):
        p = pairs[(a, b)]
        rows.append({"a": a, "b": b, "kind": p["kind"], "score": p["score"], "text": p["text"],
                     "gap_days": p["gap_days"], "amount_a": w.at[a, "amount"],
                     "amount_b": w.at[b, "amount"], "district": w.at[a, "district_name"],
                     "desc_a": w.at[a, "description"], "desc_b": w.at[b, "description"]})
    pd.DataFrame(rows).to_csv(OUT / f"dup_split_v2_pairs_{stage}.csv", index=False)
    read_groups = {m for r in gl.itertuples() for m in r.members.strip("[]").replace("'", "")
                   .split(", ")}
    for f in OUT.glob("dup_split_v2_groups_test*.csv"):
        for r in pd.read_csv(f).itertuples():
            if r.group_id in read_group_ids:
                read_groups.update(r.members.strip("[]").replace("'", "").split(", "))
    sites = sorted((g for g in groups.values() if g["kind"] == "same_site_split"
                    and g["size"] < 6 and not set(g["members"]) & read_groups
                    and (stage.startswith("test") or not set(g["members"]) & v1_grouped)),
                   key=lambda g: g["group_id"])
    rows = [{"group_id": g["group_id"], "size": g["size"], "total": g["total"], "days": g["days"],
             "amounts": g["amounts"], "members": g["members"],
             "descriptions": " || ".join(str(w.at[m, "description"])[:140] for m in g["members"])}
            for g in rng.sample(sites, min(15, len(sites)))]
    pd.DataFrame(rows).to_csv(OUT / f"dup_split_v2_groups_{stage}.csv", index=False)
    res["fresh_samples_written"] = {"pairs": min(40, len(fresh)), "groups": len(rows),
                                    "pairs_only_in_v2": len(fresh), "site_groups_only_in_v2":
                                    len(sites)}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "dup_split_v2.json").write_text(json.dumps(res, indent=2, default=str),
                                           encoding="utf-8")
    print(json.dumps(res, indent=2, default=str))


if __name__ == "__main__":
    main()
