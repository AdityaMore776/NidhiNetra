r"""Trial 2 - threshold bunching and possible split works, on the real export.

Bunching: amounts pile up just below Rs 5 lakh (12x more works in the 4% band below than
above, against 2-5x at other round numbers). A split work would show as several works just
under a threshold, same MP, same type, same place, recommended close together, whose total
crosses the threshold.

Cluster rule (kept deliberately strict, so a match is worth reading):
  - amount in [Rs 4.0 lakh, Rs 5.0 lakh)
  - same MP, same district, same work type
  - recommended within 60 days of the previous work in the cluster
  - descriptions share at least one RARE place-like word (appears in <= 60 descriptions
    nationally), so two ordinary "CC road" works in different villages do not pair up

Run:  .venv-trial\Scripts\python.exe data\trial\split_trial.py
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
boundary wall water tank borewell hand pump shed shelter the and for into""".split())
RARE_DF = 60
LO, HI = 400_000, 500_000
GAP_DAYS = 60


def tokens(text: str | None) -> set[str]:
    return {t for t in WORD.findall((text or "").lower()) if t not in STOP}


def bunching(w: pd.DataFrame) -> dict:
    """Works just below a round amount vs just above it (4% bands), and where the
    Rs 4.8-5 lakh band is crowded."""
    a = w.amount.astype(float)
    out = {}
    for t in (100_000, 200_000, 300_000, 500_000, 1_000_000, 2_000_000, 2_500_000):
        below = int(((a >= t * 0.96) & (a < t)).sum())
        above = int(((a > t) & (a <= t * 1.04)).sum())          # the round sum itself is counted apart
        out[f"{t // 100_000}_lakh"] = {"just_below": below, "exactly": int((a == t).sum()), "just_above": above,
                                       "below_to_above": round(below / max(above, 1), 1)}
    band = (a >= 480_000) & (a < 500_000)
    by = w.assign(band=band).groupby(["state_name", "district_name"]).agg(works=("band", "size"), in_band=("band", "sum"))
    by = by[by.works >= 200]
    by["share"] = (by.in_band / by.works).round(3)
    return {"thresholds": out, "national_share_4_8_to_5_lakh": round(float(band.mean()), 4),
            "districts_most_crowded_below_5_lakh": by.sort_values("share", ascending=False).head(8)
            .reset_index().to_dict("records")}


def identical_groups(w: pd.DataFrame) -> tuple[list[dict], dict]:
    """Works with the SAME text (lower-cased, punctuation dropped), same district and work type,
    each recommended within 60 days of the previous one. A group whose every piece costs
    Rs 4-5 lakh while the total passes Rs 5 lakh is a bulk order kept under the limit - or,
    when the text names one site, a split work."""
    x = w[w.description.notna() & w.recommended_date.notna()].copy()
    x["rec"] = pd.to_datetime(x.recommended_date)
    x["k"] = x.description.str.lower().str.replace(r"[^a-z0-9]+", " ", regex=True).str.strip()
    x = x[x.duplicated(["district_lgd", "work_type_code", "k"], keep=False)]
    groups = []
    for _, g in x.sort_values("rec").groupby(["district_lgd", "work_type_code", "k"]):
        chain = [g.iloc[0]]
        for r in list(g.itertuples(index=False))[1:] + [None]:
            if r is not None and (r.rec - chain[-1].rec).days <= GAP_DAYS:
                chain.append(r)
                continue
            if len(chain) >= 2:
                amounts = [float(c.amount) for c in chain]
                groups.append({"district": chain[0].district_name, "state": chain[0].state_name,
                               "type": chain[0].work_type_code, "n": len(chain), "total": sum(amounts),
                               "each_4_to_5_lakh": all(LO <= a < HI for a in amounts),
                               "same_amount": len(set(amounts)) == 1,
                               "span_days": (chain[-1].rec - chain[0].rec).days,
                               "desc": chain[0].description[:160], "ids": [c.work_id for c in chain]})
            if r is not None:
                chain = [r]
    under = [g for g in groups if g["each_4_to_5_lakh"] and g["total"] >= HI]
    summary = {"groups": len(groups), "works": sum(g["n"] for g in groups),
               "every_piece_4_to_5_lakh_total_over_5_lakh": {"groups": len(under), "works": sum(g["n"] for g in under)},
               "largest_under_limit": [{k: g[k] for k in ("district", "state", "type", "n", "total", "span_days", "desc")}
                                       for g in sorted(under, key=lambda g: -g["total"])[:6]]}
    return groups, summary


def main() -> None:
    w = pd.read_parquet(BUILD / "works.parquet")
    bunch = bunching(w)
    groups, identical = identical_groups(w)
    (OUT / "identical_groups.json").write_text(json.dumps(groups, indent=1, ensure_ascii=False), encoding="utf-8")
    df = Counter()
    for t in w.description.fillna(""):
        df.update(tokens(t))
    rare = {t for t, c in df.items() if c <= RARE_DF}

    c = w[(w.amount >= LO) & (w.amount < HI) & w.recommended_date.notna()
          & w.mp_name.notna() & w.work_type_code.notna()].copy()
    c["rec"] = pd.to_datetime(c.recommended_date)
    c["rare"] = c.description.map(lambda t: tokens(t) & rare)

    clusters = []
    for _, g in c.sort_values("rec").groupby(["mp_name", "district_lgd", "work_type_code"]):
        if len(g) < 2:
            continue
        rows = g.to_dict("records")
        used = set()
        for i, a in enumerate(rows):
            if i in used or not a["rare"]:
                continue
            members = [a]
            for j in range(i + 1, len(rows)):
                b = rows[j]
                if j in used or (b["rec"] - members[-1]["rec"]).days > GAP_DAYS:
                    continue
                if a["rare"] & b["rare"]:
                    members.append(b)
                    used.add(j)
            if len(members) >= 2:
                used.add(i)
                clusters.append(members)

    sizes = Counter(len(m) for m in clusters)
    works_in = sum(len(m) for m in clusters)
    over = [m for m in clusters if sum(x["amount"] for x in m) >= 500_000]
    by_district = Counter(m[0]["district_name"] for m in over)
    examples = []
    for m in sorted(over, key=lambda m: -len(m))[:12]:
        examples.append({
            "district": m[0]["district_name"], "state": m[0]["state_name"],
            "type": m[0]["work_type_code"], "total": float(sum(x["amount"] for x in m)),
            "shared_words": sorted(set.intersection(*[x["rare"] for x in m]))[:5],
            "works": [{"work_id": x["work_id"], "amount": float(x["amount"]),
                       "recommended": str(x["rec"].date()), "description": (x["description"] or "")[:110]}
                      for x in m],
        })
    result = {"bunching": bunch, "identical_text": identical,
              "candidate_works_4_to_5_lakh": len(c), "clusters": len(clusters),
              "works_in_clusters": works_in, "cluster_sizes": dict(sorted(sizes.items())),
              "clusters_totalling_5_lakh_or_more": len(over),
              "top_districts": by_district.most_common(10), "examples": examples}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "split_trial.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "examples"}, indent=2))
    for e in examples[:6]:
        print("\n", e["district"], e["state"], e["type"], "total", e["total"], e["shared_words"])
        for x in e["works"]:
            print("   ", x["recommended"], x["amount"], "|", x["description"])


if __name__ == "__main__":
    main()
