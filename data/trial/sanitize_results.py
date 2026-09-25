r"""Mask personal numbers in the trial results before they are committed.

Public eSAKSHI descriptions sometimes carry a private mobile number ("Mob.No. 62606....."),
and certificates carry vendors' bank account numbers. The results files keep neither:
  - 10-digit Indian mobile numbers  -> [phone]
  - 11-18 digit runs (bank accounts) -> [account]
Work ids (WS/MP807/2023-2024/32921), amounts, dates, PIN codes and vendor codes (V + 12
digits) are left alone.

Run:  .venv-trial\Scripts\python.exe data\trial\sanitize_results.py
"""

from __future__ import annotations

import re
from pathlib import Path

RESULTS = Path(__file__).resolve().parent / "results"
PHONE = re.compile(r"(?<![\d/V.])(?:\+91[\s-]?)?[6-9]\d{9}(?![\d.])")
ACCOUNT = re.compile(r"(?<![\d/V.])\d{11,18}(?![\d.])")


def main() -> None:
    for p in sorted(RESULTS.glob("*")):
        if p.suffix not in (".json", ".csv"):
            continue
        text = p.read_text(encoding="utf-8")
        clean = ACCOUNT.sub("[account]", PHONE.sub("[phone]", text))
        if clean != text:
            p.write_text(clean, encoding="utf-8")
            print(f"{p.name}: masked {len(PHONE.findall(text))} phone, {len(ACCOUNT.findall(text))} long numbers")


if __name__ == "__main__":
    main()
