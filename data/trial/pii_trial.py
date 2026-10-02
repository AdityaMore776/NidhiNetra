r"""How much the masker (apps/engine/drishti/validation/pii.py) hides in real descriptions (T056).

Reads the eSAKSHI dashboard tables (data/raw/esakshi_dashboard/Works_*.csv, 57,508 descriptions)
and counts the descriptions each masking rule touches. With --sample N it also prints N random
spans masked by the home-word rules (OWNER_HOME, HI_HOME) and N random "word + home word" spans
left unmasked, to read by eye in the terminal. The spans carry people's names: they are only
printed, never saved. The counts go to results/pii_trial.json.

Read by eye, 2 Oct 2026 (labels by kind only, no text kept):
  design sample (seed 56, 40 spans): 28 names, 9 double masks of "[name]'s house" (fixed: not
      after an apostrophe), 3 not names: "SADAK" (road) before a name, an association's hall,
      a shop named after a place (fixed: Hindi road words and association names are ordinary)
  second sample (seed 2026, 40 fresh spans): 36 names, 1 unclear (a title or a surname), 3 wrong:
      a misspelt "towords", a "row house", a curly-apostrophe double mask (all three fixed)
  final sample (seed 2027, 40 fresh spans, the rules frozen): see FINDINGS "T056"
  left unmasked (seed 7, 40 spans): 0 names; the rest are "[name] ke ghar", "near the house",
      "Panchayat Ghar" and the like

Run:  apps\engine\.venv\Scripts\python.exe data\trial\pii_trial.py [--sample 40 --seed 2027]
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "apps" / "engine"))
from drishti.validation import pii  # noqa: E402

RAW = ROOT / "data" / "raw" / "esakshi_dashboard"
OUT = ROOT / "data" / "trial" / "results" / "pii_trial.json"
HOME_WORD = re.compile(r"(?:\S+\s+){0,3}[A-Za-z.']+\s+(?:house|home|residence|makan|"
                       r"ghar|farm|field|land|shop|dukan|khet|bari)\b", re.I)
RULES = ("PHONE", "ACCOUNT", "RELATION", "HONORIFIC", "HOUSE", "POSSESSIVE", "HI_HOME",
         "OWNER_HOME", "BEFORE_RELATION")


def descriptions() -> list[str]:
    out = []
    for f in sorted(RAW.glob("Works_*.csv")):
        with open(f, encoding="utf-8-sig", errors="replace") as fh:
            rows = csv.DictReader(fh)
            col = next(c for c in rows.fieldnames if c.lower() == "work description")
            out += [" ".join((r[col] or "").split()) for r in rows]
    return [d for d in out if d]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", type=int, default=0)
    ap.add_argument("--seed", type=int, default=2027)
    args = ap.parse_args()
    descs = descriptions()
    masked = [pii.mask(d) for d in descs]
    per_rule = {name: sum(1 for d in descs if getattr(pii, name).search(d)) for name in RULES}
    out = {"descriptions": len(descs), "masked": sum(1 for d, m in zip(descs, masked) if d != m),
           "touched_by_rule": per_rule,
           "home_word_spans_left": sum(len(HOME_WORD.findall(m)) for m in masked)}
    OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out, indent=2))
    if args.sample:
        spans = []
        for d in descs:
            t = d
            for name in RULES[:-3]:
                t = getattr(pii, name).sub("[x]", t)
            spans += [m.group(0) for m in pii.HI_HOME.finditer(t)]
            t = pii.HI_HOME.sub("[x]", t)
            spans += [m.group(0) for m in pii.OWNER_HOME.finditer(t)]
        rng = random.Random(args.seed)
        print(f"\n{args.sample} of {len(spans)} spans masked by the home-word rules:")
        for i, s in enumerate(rng.sample(spans, args.sample)):
            print(i, "|", s)
        left = [m.group(0) for m in masked for m in HOME_WORD.finditer(m)]
        print(f"\n{args.sample} of {len(left)} 'word + home word' spans left unmasked:")
        for i, s in enumerate(rng.sample(left, args.sample)):
            print(i, "|", s)


if __name__ == "__main__":
    main()
