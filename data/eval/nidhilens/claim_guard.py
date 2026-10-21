r"""T172: the claim guard (readers.instructs_reader) on every real claim NidhiLens was built and
tested on: how many honest claims would it refuse to read? Writes
data/trial/results/t172_claim_guard.txt.

  apps\engine\.venv\Scripts\python.exe data\eval\nidhilens\claim_guard.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "apps" / "engine"))
from drishti.agents.site_progress.readers import instructs_reader  # noqa: E402

DATA = Path(r"D:\nidhinetra-data")
FILES = [DATA / "release" / "siteclaim_test_v1" / f"items_{k}.jsonl" for k in ("test", "fresh", "probe")]
FILES += sorted((DATA / "vlm").glob("*/items*.jsonl"))
OUT = ROOT / "data" / "trial" / "results" / "t172_claim_guard.txt"


# the site-visit claims written into the agents' eval cases and the website's examples
CASES = [*sorted((ROOT / "data" / "eval").rglob("*.py")), ROOT / "data" / "trial" / "work_form_examples.py"]
CLAIM = re.compile(r"""claim=(["'])(.+?)\1""")
NOT_HONEST = ("instruct", "ignore", "reply", "answer")    # the guard's own attack cases


def main() -> None:
    claims: dict[str, str] = {}
    for f in FILES:
        for line in f.read_text(encoding="utf-8").splitlines():
            if line.strip():
                it = json.loads(line)
                claims.setdefault(it["claim"], f.parent.name + "/" + f.name)
    n_items = len(claims)
    for f in CASES:
        for m in CLAIM.finditer(f.read_text(encoding="utf-8")):
            if not any(w in m.group(2).lower() for w in NOT_HONEST):
                claims.setdefault(m.group(2), str(f.relative_to(ROOT)))
    hit = sorted(c for c in claims if instructs_reader(c))
    lines = [f"T172 claim guard on every distinct honest claim: {n_items} in {len(FILES)} NidhiLens "
             f"item files (train, validation, test, fresh, probe), {len(claims) - n_items} more in "
             f"the eval cases and the website's examples; {len(claims)} in all, refused {len(hit)}"]
    lines += [f"  refused: {c!r} ({claims[c]})" for c in hit]
    text = "\n".join(lines) + "\n"
    print(text)
    OUT.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
