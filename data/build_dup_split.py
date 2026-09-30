r"""Duplicate & Split-Work engine, data job (T030): works that repeat, and jobs cut into pieces.

Every description is turned into a meaning vector with the free, local multilingual model
paraphrase-multilingual-MiniLM-L12-v2 (so "CC road from X to Y" and "X se Y tak CC sadak"
land close together). Works are compared only inside their own district.

DUPLICATES (the blueprint's pair score)
  candidate   cosine >= 0.85, same district, recommended within 24 months
  confirm     place: the rare, place-like words of both descriptions agree as whole lists
              (fuzzy sort-ratio >= 85, so a shared panchayat name alone is not a match);
              a pair with no place words cannot confirm a site and is not flagged;
              different numbers (survey no., property no., chainage) = different sites;
              wording one MP filed 3+ times in a district = a series, not a duplicate
  score       0.50 text + 0.20 place + 0.15 time + 0.15 amount (amounts within 25%);
              flagged at 0.75 or more
  timing      same MP within 60 days = a batch (the split rule looks at those, not this);
              repair / phase / balance words in the later work = staged, not flagged;
              the first COMPLETED before the second was recommended = "funded again after
              completion?" (strongest); otherwise "recommended again while the first was open"

SPLITS AND BULK ORDERS (groups)
  same district, work type and MP; each recommended within 30 days of the previous;
  text >= 0.80 alike; then cut by place words, because such a chain is usually one MP's
  batch for DIFFERENT villages (an ordinary batch, not a split); amounts alike
  (coefficient of variation < 0.15)
  same_site_split  2+ pieces naming the same place: one job at one site in pieces
  bulk_order       3+ pieces naming no place: one purchase filed as many works
  every piece at Rs 4-5 lakh while the total passes Rs 5 lakh raises the signal: amounts
  pile up 12x just under Rs 5 lakh nationally (split_trial.py)
  A group counts once: every member carries the group id.

Writes data/build/dup_split.parquet (per flagged work) and, for reading by eye,
data/trial/results/dup_split_{pairs,groups}_sample.csv and dup_split.json.
Run: .venv-trial\Scripts\python.exe data\build_dup_split.py
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
import time
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
from rapidfuzz import fuzz

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "engine"))
from drishti.agents.statistical.scope import GOODS, many_sites, scope, undescribed  # noqa: E402

BUILD = ROOT / "data" / "build"
CACHE = ROOT / "data" / "cache"
OUT = ROOT / "data" / "trial" / "results"
MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
VERSION = "dup-split-1"

DUP_COS, DUP_PLACE, DUP_MONTHS, DUP_AMOUNT, DUP_FLAG = 0.85, 85.0, 24, 0.25, 0.75
BATCH_DAYS = 60
SPLIT_COS, SPLIT_GAP_DAYS, SPLIT_MIN, SPLIT_CV = 0.80, 30, 3, 0.15
LIMIT, LIMIT_BAND = 500_000.0, (400_000.0, 500_000.0)
RARE_DF = 60
WORD = re.compile(r"[a-z]{4,}")
STOP = set("""construction installation providing supply work works road roads village near from
with under ward block district gram panchayat colony hall community school building drain drains
street light lights solar high mast cement concrete toilet public open repair renovation boundary
wall water tank borewell hand pump shed shelter the and for into interlocking karya nirman sadak
khadanja marg bhawan kaksha purchase books library installation center centre main house""".split())
STAGED = re.compile(r"\b(repair|renovation|marammat|maramat|extension|additional|phase|second|"
                    r"2nd|3rd|remaining|balance|continuation|continued|upgradation|widening|"
                    r"instal+ment|stage)\b", re.I)


def embed(texts: list[str]) -> np.ndarray:
    key = hashlib.sha256(("\n".join(texts) + MODEL).encode("utf-8")).hexdigest()[:16]
    path = CACHE / f"emb_{key}.npy"
    if path.exists():
        return np.load(path)
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(MODEL, device="cpu")
    t0 = time.time()
    e = model.encode(texts, batch_size=256, normalize_embeddings=True, show_progress_bar=False,
                     convert_to_numpy=True).astype(np.float32)
    print(f"embedded {len(texts):,} descriptions in {time.time() - t0:.0f}s", flush=True)
    CACHE.mkdir(parents=True, exist_ok=True)
    np.save(path, e)
    return e


def place_words(w: pd.DataFrame) -> pd.Series:
    norm = w.description.fillna("").str.lower().str.replace(r"[^a-z0-9]+", " ", regex=True)
    df = Counter()
    for t in norm:
        df.update({x for x in WORD.findall(t) if x not in STOP})
    rare = {t for t, c in df.items() if c <= RARE_DF}
    return norm.map(lambda t: " ".join(sorted({x for x in WORD.findall(t) if x in rare})))


def site_numbers(w: pd.DataFrame) -> pd.Series:
    """The numbers a description names (survey no., property no., chainage, ward).

    Read by eye (top 50 pairs, 30 Sept): "Sy.No. 661" vs "Sy.No. 715", "Property No. 197/1"
    vs "No. 57", "(0-0-0-300)" vs "(0-301-0-600)" were different plots or stretches of one
    village's list, matched because the place words ignore numbers.
    """
    return w.description.fillna("").str.findall(r"\d+").map(lambda xs: " ".join(sorted(set(xs))))


def pairs_in_district(idx: np.ndarray, emb: np.ndarray, w: pd.DataFrame) -> list[dict]:
    e = emb[idx]
    sim = e @ e.T
    ii, jj = np.where(np.triu(sim, 1) >= DUP_COS)
    out = []
    for a, b in zip(ii, jj, strict=True):
        ra, rb = w.iloc[idx[a]], w.iloc[idx[b]]
        if rb.rec < ra.rec:
            ra, rb = rb, ra
        gap = (rb.rec - ra.rec).days
        if gap > DUP_MONTHS * 30.4:
            continue
        if ra.mp_name == rb.mp_name and gap <= BATCH_DAYS:
            continue                                  # a batch: the split rule's business
        if not ra.place or not rb.place:
            continue                                  # no site named, cannot confirm
        if ra.copies >= 3 or rb.copies >= 3:
            continue                                  # a series of identical works
        if ra.nums and rb.nums and ra.nums != rb.nums:
            continue                                  # different plot / stretch numbers
        # the whole place lists must agree; token_set_ratio scored a subset as 100, so
        # "Parvatpur" matched "Lakhanpur, Parvatpur Panchayat" (TEST1, 30 Sept)
        place = fuzz.token_sort_ratio(ra.place, rb.place)
        if place < DUP_PLACE:
            continue
        amt_diff = abs(ra.amount - rb.amount) / max(ra.amount, rb.amount, 1.0)
        text = float(sim[a, b])
        score = (0.50 * text + 0.20 * place / 100 + 0.15 * max(0.0, 1 - gap / 730)
                 + 0.15 * (max(0.0, 1 - amt_diff / DUP_AMOUNT)))
        if score < DUP_FLAG:
            continue
        staged = bool(STAGED.search(rb.description or ""))
        after = pd.notna(ra.done) and ra.done < rb.rec
        kind = "staged" if staged else ("after_completed" if after else "while_open")
        out.append({"a": ra.work_id, "b": rb.work_id, "kind": kind, "score": round(score, 4),
                    "text": round(text, 4), "place": round(place, 1), "gap_days": int(gap),
                    "amount_a": ra.amount, "amount_b": rb.amount,
                    "same_mp": ra.mp_name == rb.mp_name, "district": ra.district_name,
                    "desc_a": ra.description, "desc_b": rb.description,
                    "status_a": ra.status, "status_b": rb.status})
    return out


def groups_in_block(idx: np.ndarray, emb: np.ndarray, w: pd.DataFrame) -> list[list[int]]:
    """Chains of alike works (same district, type, MP) recommended within 30 days."""
    sub = w.iloc[idx].assign(_i=idx).sort_values("rec")
    order = sub._i.to_numpy()
    recs = sub.rec.to_numpy()
    parent = {i: i for i in order}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    e = emb[order]
    sim = e @ e.T
    for a in range(len(order)):
        for b in range(a + 1, len(order)):
            gap = (recs[b] - recs[a]) / np.timedelta64(1, "D")
            if gap > SPLIT_GAP_DAYS:
                break
            if sim[a, b] >= SPLIT_COS:
                parent[find(order[a])] = find(order[b])
    groups: dict[int, list[int]] = {}
    for i in order:
        groups.setdefault(find(i), []).append(i)
    return [g for g in groups.values() if len(g) >= 2]


def split_groups(chains: list[list[int]], w: pd.DataFrame) -> list[dict]:
    """Inside each chain, only works naming the same place form a group.

    A chain is often one MP's batch of alike works for DIFFERENT villages ("CC road at
    Sapti", "CC road at Walki", ...): that is an ordinary batch, not a split. So a chain is
    cut by its place words: 2+ near-equal pieces naming one place = same_site_split;
    3+ near-equal pieces naming no place at all = bulk_order.
    """
    out = []
    for chain in chains:
        m = w.iloc[chain]
        for (place, _nums), idx in m.groupby(["place", "nums"]).indices.items():
            sub = m.iloc[idx]
            first = sub.description.iloc[0]
            # a purchase of goods, or text naming "different places", is not one site
            one_site = place and scope(first) != GOODS and not many_sites(first)
            kind = "same_site_split" if one_site else "bulk_order"
            if len(sub) < (2 if one_site else SPLIT_MIN):
                continue
            amounts = sub.amount.to_numpy()
            cv = float(amounts.std() / amounts.mean()) if amounts.mean() else 1.0
            if cv >= SPLIT_CV:
                continue
            under = bool(((amounts >= LIMIT_BAND[0]) & (amounts <= LIMIT_BAND[1])).all()
                         and amounts.sum() > LIMIT)
            out.append({"group_id": f"G{len(out):05d}", "kind": kind,
                        "size": len(sub), "total": float(amounts.sum()), "cv": round(cv, 4),
                        "under_limit": under, "shared_place": place if one_site else "",
                        "days": int((sub.rec.max() - sub.rec.min()).days),
                        "district": sub.district_name.iloc[0],
                        "type": sub.work_type_code.iloc[0],
                        "members": sub.work_id.tolist(), "amounts": amounts.tolist(),
                        "description": sub.description.iloc[0][:200]})
    return out


def main() -> None:
    t0 = time.time()
    w = pd.read_parquet(BUILD / "works.parquet")
    w = w[w.description.notna() & w.recommended_date.notna() & (w.amount > 0)].copy()
    w = w[~w.description.map(undescribed)].reset_index(drop=True)
    w["amount"] = w.amount.astype(float)
    w["rec"] = pd.to_datetime(w.recommended_date)
    w["done"] = pd.to_datetime(w.completed_date)
    w["place"] = place_words(w)
    w["nums"] = site_numbers(w)
    # the same wording filed 3+ times by one MP in a district is a series (7 identical water
    # coolers, 5 "culverts and bridges"): the bulk-order rule's business, not a duplicate pair.
    # A real duplicate is a cluster of 2 (the old build's finding, confirmed by eye 30 Sept).
    key = w.description.str.lower().str.replace(r"[^a-z0-9]+", "", regex=True)
    w["copies"] = key.groupby([w.district_lgd, w.mp_name, key]).transform("size")
    w["district_lgd"] = w.district_lgd.fillna("NA").astype(str)
    w["mp_name"] = w.mp_name.fillna("NA").astype(str)
    emb = embed(w.description.str.slice(0, 400).tolist())

    pairs = []
    for _, g in w.groupby("district_lgd").indices.items():
        pairs.extend(pairs_in_district(np.asarray(g), emb, w))
    p = pd.DataFrame(pairs)
    print(f"duplicate pairs: {len(p):,} ({p.kind.value_counts().to_dict() if len(p) else {}}) "
          f"at {time.time() - t0:.0f}s", flush=True)

    chains = []
    for _, g in w.groupby(["district_lgd", "work_type_code", "mp_name"]).indices.items():
        if len(g) >= 2:
            chains.extend(groups_in_block(np.asarray(g), emb, w))
    gdf = pd.DataFrame(split_groups(chains, w))
    print(f"groups: {len(gdf):,} ({gdf.kind.value_counts().to_dict() if len(gdf) else {}}), "
          f"{int(gdf['size'].sum()) if len(gdf) else 0:,} works", flush=True)

    # ---- per-work facts for the engine
    per: dict[str, dict] = {}
    for r in p[p.kind != "staged"].to_dict("records") if len(p) else []:
        for me, other, amt, first in ((r["b"], r["a"], r["amount_a"], True),
                                      (r["a"], r["b"], r["amount_b"], False)):
            cur = per.setdefault(me, {"pairs": []})
            cur["pairs"].append({"other": other, "kind": r["kind"], "score": r["score"],
                                 "gap_days": r["gap_days"], "other_amount": amt,
                                 "this_is_later": first})
    for g in gdf.to_dict("records") if len(gdf) else []:
        for wid in g["members"]:
            per.setdefault(wid, {"pairs": []})["group"] = {
                k: g[k] for k in ("group_id", "kind", "size", "total", "under_limit",
                                  "shared_place", "days")} | {
                "others": [x for x in g["members"] if x != wid][:5]}
    rows = []
    for wid, d in per.items():
        d["pairs"] = sorted(d["pairs"], key=lambda x: -x["score"])[:5]
        rows.append({"work_id": wid, "pairs": json.dumps(d["pairs"]),
                     "group": json.dumps(d.get("group")), "model_version": VERSION})
    pd.DataFrame(rows).to_parquet(BUILD / "dup_split.parquet", index=False)

    # ---- samples to read by eye
    OUT.mkdir(parents=True, exist_ok=True)
    flagged = p[p.kind != "staged"].sort_values("score", ascending=False) if len(p) else p
    flagged.head(50).to_csv(OUT / "dup_split_pairs_sample.csv", index=False)
    # TEST2: 40 random flags outside the top 50 never read before (TEST1, seed 41, led to the
    # place rule change; see dup_split_labels.py), read by eye, never used to change the rules
    if len(flagged) > 50:
        t1 = pd.read_csv(OUT / "dup_split_pairs_test1.csv") if (
            OUT / "dup_split_pairs_test1.csv").exists() else pd.DataFrame(columns=["a", "b"])
        seen = set(zip(t1.a, t1.b, strict=True))
        pool = flagged.iloc[50:]
        pool = pool[[(a, b) not in seen for a, b in zip(pool.a, pool.b, strict=True)]]
        pool.sample(n=min(40, len(pool)), random_state=42).to_csv(
            OUT / "dup_split_pairs_test2.csv", index=False)
    if len(gdf):
        gdf.sample(n=min(30, len(gdf)), random_state=26).to_csv(
            OUT / "dup_split_groups_sample.csv", index=False)
    nanded = gdf[gdf.description.str.contains("Sapti", case=False)] if len(gdf) else gdf
    res = {"version": VERSION, "works_compared": len(w),
           "duplicate_pairs": {"total": int(len(p)),
                               "by_kind": p.kind.value_counts().to_dict() if len(p) else {}},
           "groups": {"total": int(len(gdf)),
                      "by_kind": gdf.kind.value_counts().to_dict() if len(gdf) else {},
                      "works": int(gdf["size"].sum()) if len(gdf) else 0,
                      "under_limit": int(gdf.under_limit.sum()) if len(gdf) else 0},
           "works_flagged": len(rows),
           "nanded_sapti_split_found": nanded[["group_id", "size", "total", "amounts"]]
           .to_dict("records") if len(nanded) else [],
           "seconds": round(time.time() - t0)}
    (OUT / "dup_split.json").write_text(json.dumps(res, indent=2, ensure_ascii=False, default=str),
                                        encoding="utf-8")
    print(json.dumps(res, indent=2, default=str))


if __name__ == "__main__":
    main()
