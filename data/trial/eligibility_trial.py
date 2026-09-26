r"""Trial 5 - Eligibility (prohibited works, Annexure-II) on the real descriptions.

Three readers of the same 209,993 descriptions:
  keyword  - a prohibited word appears anywhere (simple keyword match)
  v1       - the built matcher: the word must be the OBJECT of the work ("construction of ... temple")
  v2       - v1 plus fixes found by reading v1's matches (this trial):
               * ration / fair-price / public-distribution shops are government PDS outlets, not
                 commercial establishments
               * Hindi and English landmark words AFTER the keyword ("mandir ke pas", "temple to ...",
                 "masjid road") mean the temple is a landmark
               * "Shishu Mandir", "Vidya Mandir", "Ranga Mandir", "... Memorial School" are schools,
                 halls and institutions, not places of worship
               * NEW: works inside temple premises ("mandir prangan", "temple premises") are caught
                 even when the verb is far away

Precision is judged by reading each sampled description (DRISHTI's reviewer, not an official):
  clear  - reads as a work Annexure-II prohibits (e.g. building a temple, a welcome arch)
  grey   - an officer should look (maintenance, statue surroundings, works named after a person)
  no     - legitimate (a road to a temple, a ration shop, a school named Shishu Mandir)

Run:  .venv-trial\Scripts\python.exe data\trial\eligibility_trial.py
"""

from __future__ import annotations

import json
import random
import re
import sys
from collections import Counter
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "apps" / "engine"))
from drishti import reference  # noqa: E402
from drishti.validation.prohibited import LANDMARK, _patterns, match  # noqa: E402

BUILD = ROOT / "data" / "build"
OUT = ROOT / "data" / "trial" / "results"

PDS_SHOP = re.compile(r"\b(?:ration|fair\s*price|public\s+distribution|p\.?\s?d\.?\s?s?|fps|amutham)"
                      r"\s+(?:system\s+)?shops?\b", re.I)
AFTER_LANDMARK = re.compile(
    r"^[\s,.-]*(?:(?:k[ei]?\s+)?pa+s+\b|k[ei]?\s+sam(?:a)?ne|k[ei]?\s+pi(?:ch|chh)e|k[ei]?\s+nikat|"
    r"k[ei]?\s+a+n?ge\b|k[ei]?\s+bagal|se\b|tak\b|(?:main\s+)?road\b|marg\b|to\b|towards\b|street\b|"
    r"chowk\b|gali\b|ki\s+or\b|ki\s+taraf\b|area\b|side\b)", re.I)
INSTITUTION = re.compile(
    r"\b(?:shishu|sishu|vidya|vidhya|bidya|siksha|shiksha|gyan|jnana|bal|ranga?|kala|natya|sangeet|samaj)"
    r"\s+mandir\b|"
    r"\bmemorial\s+(?:senior\s+|higher\s+|secondary\s+|primary\s+|public\s+)*"
    r"(?:school|college|hospital|hall|library|vidyalaya)\b|\bmandir\s+(?:school|vidyalaya|inter\s+college)\b", re.I)
WORSHIP = r"(?:temple|mandir|masjid|mosque|church|gurudwara|dargah|idgah|eidgah)"
PREMISES = re.compile(
    rf"\b(?:premises|campus|compound(?!\s+wall)|prangan|parisar|courtyard)\s+(?:of\s+)?(?:[\w.'-]+\s+){{0,3}}?"
    rf"{WORSHIP}\b|"
    rf"\b{WORSHIP}\s+(?:[\w.'-]+\s+)?(?:premises|campus|compound(?!\s+wall)|prangan|parisar|courtyard)\b"
    rf"(?!\s+(?:k[ei]\s+)?(?:nikat|pa+s|samne|bahar|near))", re.I)
NEAR_BEFORE = re.compile(r"\b(?:near|opposite|beside|behind|outside|in front of|nikat)\b(?:\s+[\w.'-]+){0,3}\s*$",
                         re.I)

# Reading of the 60 sampled v1 matches (index -> verdict); everything else is "no"
V1_LABELS = {6: "clear", 24: "clear", 37: "clear", 42: "clear", 43: "clear", 47: "clear", 53: "clear",
             5: "grey", 8: "grey", 9: "grey", 26: "grey", 27: "grey", 33: "grey", 51: "grey", 59: "grey"}
# Reading of the 40 sampled keyword matches
KEYWORD_LABELS = {19: "clear", 35: "clear", 2: "grey", 7: "grey", 15: "grey", 16: "grey", 22: "grey"}
# Development sample: 50 matches of the FIRST draft of v2 (seed 27), read to find its misses
DEV_LABELS = {i: "clear" for i in (1, 2, 3, 4, 5, 6, 9, 11, 12, 14, 15, 19, 20, 22, 25, 27, 28, 29, 30, 31, 33,
                                   35, 36, 37, 40, 42, 45, 48)} | {i: "grey" for i in (7, 10, 16, 17, 38, 39, 44, 49)}
# Test sample: 50 FRESH matches of the final v2 (seed 28, none seen before), read after the rules froze
TEST_LABELS = {i: "clear" for i in (2, 3, 4, 5, 9, 10, 11, 12, 15, 17, 18, 20, 21, 24, 25, 27, 29, 31, 34, 35,
                                    36, 38, 39, 41, 43, 45, 46, 49)} | {i: "grey" for i in (0, 1, 8, 14, 16, 19, 26,
                                                                                        28, 37, 40, 44, 47)}
# What v2 leaves behind: 60 keyword matches v2 does NOT flag (seed 29), read the same way
MISSED_LABELS = {6: "grey", 26: "grey"}


def v2(text: str | None) -> str | None:
    """Item id if the description reads as a prohibited work, else None."""
    t = text or ""
    for item, kw, rx in _patterns():
        for m in rx.finditer(t):
            if LANDMARK.search(m.group(1) or ""):
                continue
            if AFTER_LANDMARK.search(t[m.end():]):
                continue
            if item["id"] == "COMMERCIAL" and PDS_SHOP.search(t):
                continue
            if item["id"] in ("RELIGIOUS", "NAMED_ASSET") and INSTITUTION.search(t):
                continue
            return item["id"]
    m = PREMISES.search(t)
    if m and not NEAR_BEFORE.search(t[:m.start()]) and not INSTITUTION.search(t):
        return "RELIGIOUS"
    return None


def precision(labels: dict[int, str], n: int) -> dict:
    c = Counter(labels.values())
    return {"sampled": n, "clear": c["clear"], "grey": c["grey"],
            "clear_share": round(c["clear"] / n, 3), "clear_or_grey_share": round((c["clear"] + c["grey"]) / n, 3)}


def main() -> None:
    w = pd.read_parquet(BUILD / "works.parquet")
    desc = w.description.fillna("")
    kws = sorted({kw for it in reference.prohibited_items() if not it.get("superseded_likely")
                  for kw in (it.get("keywords") or [])})
    kw_rx = re.compile(r"\b(?:" + "|".join(map(re.escape, kws)) + r")\b", re.I)
    keyword_hits = int(desc.str.contains(kw_rx).sum())
    v1_hits = desc.map(lambda t: m.item_id if (m := match(t)) else None)
    v2_hits = desc.map(v2)

    v1_sample = json.loads((OUT / "eligibility_sample.json").read_text(encoding="utf-8"))
    v1_desc = [s[6] for s in v1_sample]
    kept = {i: lab for i, lab in V1_LABELS.items() if v2(v1_desc[i])}
    dropped_no = sum(1 for i, d in enumerate(v1_desc) if i not in V1_LABELS and not v2(d))
    dev = json.loads((OUT / "eligibility_dev_sample.json").read_text(encoding="utf-8"))

    seen = {s[2] for s in v1_sample} | {d[0] for d in dev}
    pool = w[v2_hits.notna() & ~w.work_id.isin(seen)]
    test = pool.sample(n=50, random_state=28)
    assert [r.work_id for r in test.itertuples()] == [t[0] for t in json.loads(
        (OUT / "eligibility_test_sample.json").read_text(encoding="utf-8"))], "test sample changed - re-read it"
    res = {
        "keyword_presence": {"matches": keyword_hits, **precision(KEYWORD_LABELS, 40)},
        "v1_object_of_work": {"matches": int(v1_hits.notna().sum()), "by_item": v1_hits.value_counts().to_dict(),
                              **precision(V1_LABELS, 60)},
        "v2_after_reading": {
            "matches": int(v2_hits.notna().sum()), "by_item": v2_hits.value_counts().to_dict(),
            "dev_sample_first_draft": precision(DEV_LABELS, 50),
            "test_sample_fresh": precision(TEST_LABELS, 50) if TEST_LABELS else "not read yet",
            "left_behind_keyword_only": {"works": int((desc.str.contains(kw_rx) & v2_hits.isna()).sum()),
                                         **precision(MISSED_LABELS, 60)},
            "of_v1_sample_clear_kept": sum(1 for v in kept.values() if v == "clear"),
            "of_v1_sample_grey_kept": sum(1 for v in kept.values() if v == "grey"),
            "of_v1_sample_legit_dropped": dropped_no,
            "of_v1_sample_legit_total": 60 - len(V1_LABELS),
            "of_dev_sample_legit_now_dropped": sum(1 for i, d in enumerate(dev)
                                                   if i not in DEV_LABELS and not v2(d[2])),
            "of_dev_sample_clear_still_caught": sum(1 for i, d in enumerate(dev)
                                                    if DEV_LABELS.get(i) == "clear" and v2(d[2]))},
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "eligibility_trial.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(json.dumps(res, indent=2))
    if not TEST_LABELS:
        for i, r in enumerate(test.itertuples()):
            print(i, v2(r.description), "|", (r.description or "")[:170])


if __name__ == "__main__":
    main()
