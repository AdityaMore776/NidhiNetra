r"""Mask personal numbers and people's names in the trial results before they are committed.

Public eSAKSHI descriptions sometimes carry a private mobile number ("Mob.No. 62606....."),
and certificates carry vendors' bank account numbers. The results files keep neither:
  - 10-digit Indian mobile numbers  -> [phone]
  - 11-18 digit runs (bank accounts) -> [account]
Work ids (WS/MP807/2023-2024/32921), amounts, dates, PIN codes and vendor codes (V + 12
digits) are left alone.

Names (T056, 2 Oct 2026): every text value in a CSV cell or a JSON string also goes through the
site's own masker (apps/engine/drishti/validation/pii.py), so a results file never shows a name
the site would hide ("road from <name> house to <name> house", "<name> S/O [name]"). Only the
changed words are replaced in the file's own text, so its formatting and line endings stay.

Run:  .venv-trial\Scripts\python.exe data\trial\sanitize_results.py
"""

from __future__ import annotations

import csv
import io
import json
import re
import sys
from pathlib import Path

RESULTS = Path(__file__).resolve().parent / "results"
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "apps" / "engine"))
from drishti.validation.pii import mask  # noqa: E402

# A number may end a sentence ("Contact:8896852222. Executing agency"): a full stop after it
# is not a decimal point unless a digit follows (missed until 1 Oct 2026).
PHONE = re.compile(r"(?<![\d/V.])(?:\+91[\s-]?)?[6-9]\d{9}(?!\d|\.\d)")
ACCOUNT = re.compile(r"(?<![\d/V.])\d{11,18}(?!\d|\.\d)")


def _strings(x):
    if isinstance(x, str):
        yield x
    elif isinstance(x, dict):
        for v in x.values():
            yield from _strings(v)
    elif isinstance(x, list):
        for v in x:
            yield from _strings(v)


def _texts(p: Path, text: str) -> set[str]:
    """Every text value in the file, as the reader of the file sees it."""
    if p.suffix == ".json":
        try:
            return set(_strings(json.loads(text)))
        except json.JSONDecodeError:
            return set()
    return {c for row in csv.reader(io.StringIO(text)) for c in row}


def _names_masked(p: Path, text: str) -> tuple[str, int]:
    n = 0
    for value in sorted(_texts(p, text), key=len, reverse=True):
        masked = mask(value)
        if masked == value:
            continue
        if p.suffix == ".json":
            forms = {(json.dumps(value)[1:-1], json.dumps(masked)[1:-1]),
                     (json.dumps(value, ensure_ascii=False)[1:-1],
                      json.dumps(masked, ensure_ascii=False)[1:-1])}
        else:
            forms = {(value.replace('"', '""'), masked.replace('"', '""'))}
        for raw, new in forms:
            if raw in text:
                n += text.count(raw)
                text = text.replace(raw, new)
    return text, n


def main() -> None:
    for p in sorted(RESULTS.glob("*")):
        if p.suffix not in (".json", ".csv"):
            continue
        text = p.read_text(encoding="utf-8")
        clean, names = text, 0
        for _ in range(3):      # a name masked can uncover a number glued to it ("...V98765...")
            before = clean
            clean = ACCOUNT.sub("[account]", PHONE.sub("[phone]", clean))
            clean, n = _names_masked(p, clean)
            names += n
            if clean == before:
                break
        if clean != text:
            p.write_text(clean, encoding="utf-8")
            print(f"{p.name}: masked {len(PHONE.findall(text))} phone, "
                  f"{len(ACCOUNT.findall(text))} long numbers, {names} texts with names")


if __name__ == "__main__":
    main()
