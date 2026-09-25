r"""Trial 9 - Duplicate works: the same named site recommended again.

A description that names a specific place ("CC road from Ram Singh's house to the school in
village X") pins a work to a site. The same site-specific text appearing on two works in one
district is the strongest duplicate signal the export holds - strongest of all when the first
work was already COMPLETED before the second was recommended.

  site-specific = at least two rare words (used in <= 60 descriptions nationally)
  timing        - within 60 days of each other: a batch or a split (see split_trial.py)
                - later, while the first was still open
                - later, AFTER the first was completed  <- "already built, funded again?"

Run:  .venv-trial\Scripts\python.exe data\trial\dup_trial.py
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
BUILD = ROOT / "data" / "build"
OUT = ROOT / "data" / "trial" / "results"
WORD = re.compile(r"[a-z]{4,}")
STOP = set("""construction installation providing supply work works road roads village near from with
under ward block district gram panchayat colony hall community school building drain drains
street light lights solar high mast cement concrete toilet public open repair renovation
boundary wall water tank borewell hand pump shed shelter the and for into interlocking karya
nirman sadak khadanja marg bhawan kaksha""".split())
RARE_DF = 60
BATCH_DAYS = 60
REPAIR = re.compile(r"\b(repair|renovation|marammat|maramat|extension|additional|phase|second|2nd|"
                    r"remaining|balance|continuation|continued|upgradation|widening)\b", re.I)


def main() -> None:
    w = pd.read_parquet(BUILD / "works.parquet")
    w = w[w.description.notna() & w.recommended_date.notna()].copy()
    w["norm"] = w.description.str.lower().str.replace(r"[^a-z0-9]+", " ", regex=True).str.strip()
    df = Counter()
    for t in w.norm:
        df.update({x for x in WORD.findall(t) if x not in STOP})
    rare = {t for t, c in df.items() if c <= RARE_DF}
    w["rare_n"] = w.norm.map(lambda t: len({x for x in WORD.findall(t) if x in rare}))
    s = w[w.rare_n >= 2]
    s = s[s.duplicated(["district_lgd", "norm"], keep=False)].copy()
    s["rec"] = pd.to_datetime(s.recommended_date)
    s["done"] = pd.to_datetime(s.completed_date)

    pairs = []
    for _, g in s.sort_values("rec").groupby(["district_lgd", "norm"]):
        rows = g.to_dict("records")
        for a, b in zip(rows, rows[1:]):
            gap = (b["rec"] - a["rec"]).days
            if gap <= BATCH_DAYS:
                kind = "within_60_days"
            elif pd.notna(a["done"]) and a["done"] < b["rec"]:
                kind = "after_first_completed"
            else:
                kind = "while_first_open"
            pairs.append({"kind": kind, "gap_days": gap, "repair_words": bool(REPAIR.search(b["description"])),
                          "same_type": a["work_type_code"] == b["work_type_code"],
                          "a": {k: str(a[k]) for k in ("work_id", "amount", "recommended_date", "completed_date",
                                                        "status", "work_type_code")},
                          "b": {k: str(b[k]) for k in ("work_id", "amount", "recommended_date", "completed_date",
                                                        "status", "work_type_code")},
                          "district": a["district_name"], "state": a["state_name"],
                          "description": a["description"][:160]})
    p = pd.DataFrame(pairs)
    res = {"site_specific_works": int((w.rare_n >= 2).sum()),
           "works_sharing_site_text_in_district": int(len(s)),
           "pairs_by_timing": p.kind.value_counts().to_dict(),
           "after_first_completed": {
               "pairs": int((p.kind == "after_first_completed").sum()),
               "with_repair_or_extension_words": int(((p.kind == "after_first_completed") & p.repair_words).sum()),
               "same_work_type": int(((p.kind == "after_first_completed") & p.same_type).sum())}}
    after = p[(p.kind == "after_first_completed") & ~p.repair_words & p.same_type]
    res["after_first_completed"]["clean_candidates"] = int(len(after))
    # The pairs recommended again while the first was open, read one by one (index in this order):
    # "same asset" = the same named asset, both funded; "grey" = staged/top-up/resubmission;
    # the rest name no real site (generic text that happened to have rare words).
    open_pairs = p[p.kind == "while_first_open"].reset_index(drop=True)
    same_asset = {4, 12, 13, 19, 20, 22, 24, 27, 29, 30, 31, 34, 36, 38, 39, 40, 41, 42, 43}
    no_site = {1, 2, 8, 9, 10, 16, 17, 18, 46}
    open_pairs["reading"] = ["same_asset" if i in same_asset else "no_site" if i in no_site else "grey"
                             for i in open_pairs.index]
    res["while_first_open_reading"] = open_pairs.reading.value_counts().to_dict()
    res["while_first_open_pairs"] = open_pairs.to_dict("records")
    res["examples"] = after.sample(n=min(30, len(after)), random_state=26).to_dict("records")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "dup_trial.json").write_text(json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: v for k, v in res.items() if k != "examples"}, indent=2))
    for i, e in enumerate(res["examples"]):
        print(i, e["district"], "|", e["a"]["amount"], e["a"]["recommended_date"], "->", e["a"]["completed_date"],
              "||", e["b"]["amount"], e["b"]["recommended_date"], e["b"]["status"], "|", e["description"][:120])


if __name__ == "__main__":
    main()
