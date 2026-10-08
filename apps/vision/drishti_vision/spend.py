"""A hard spending ceiling for paid API calls (owner, 8 Oct 2026: Rs 800 of Gemini credit, "not a
single rupee more").

Every paid call is priced BEFORE it is made, at its worst case (its input tokens at the published
price plus the output-token cap it is sent with), and refused if the money already spent plus
that worst case would pass the stop line (`stop_share` of the limit; the rest is a margin for
rounding and exchange rates). After the call its real billed tokens are recorded. The ledger is
one JSON file kept with the runs, so every container and every session shares one total.

Rupees come from dollars at a deliberately high exchange rate, so the ledger over-counts rather
than under-counts. Which Google money pays (prepaid credit or card) is Google's decision and is not
visible here: the owner checks it in Google's billing pages.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

USD_PER_M = {        # published Gemini API prices, (input, output incl. thinking) per 1M tokens,
    # read 8 Oct 2026 at ai.google.dev/gemini-api/docs/pricing (prompts <= 200k tokens)
    "gemini-3.1-pro-preview": (2.00, 12.00),
    "gemini-3.8-flash": (0.75, 3.75),
}
BATCH_SHARE = 0.5    # Batch API: "50% of the standard cost"
INR_PER_USD = 95.0   # deliberately above the market rate: the ledger over-counts


class OverBudget(RuntimeError):
    """The next call could pass the ceiling: the run stops (vlmeval.predict honours stop_run)."""
    stop_run = True


def usd(model: str, tokens_in: int, tokens_out: int, batch: bool = False) -> float:
    if model not in USD_PER_M:
        raise OverBudget(f"no published price on record for {model}: not calling it")
    pin, pout = USD_PER_M[model]
    c = (tokens_in * pin + tokens_out * pout) / 1e6
    return c * BATCH_SHARE if batch else c


class Ledger:
    def __init__(self, path: str | Path, limit_inr: float, stop_share: float = 0.875,
                 inr_per_usd: float = INR_PER_USD) -> None:
        self.path, self.limit, self.stop = Path(path), limit_inr, limit_inr * stop_share
        self.fx = inr_per_usd
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write({"limit_inr": limit_inr, "spent_inr": 0.0, "entries": []})

    def _read(self) -> dict:
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _write(self, d: dict) -> None:
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(d, indent=1), encoding="utf-8")
        tmp.replace(self.path)

    @property
    def spent_inr(self) -> float:
        return float(self._read()["spent_inr"])

    def check(self, worst_usd: float, what: str = "") -> None:
        """Refuse a call whose worst case could pass the stop line."""
        worst = worst_usd * self.fx
        if self.spent_inr + worst > self.stop:
            raise OverBudget(f"{what}: worst case Rs {worst:.2f} on top of Rs "
                             f"{self.spent_inr:.2f} spent would pass the stop line Rs "
                             f"{self.stop:.0f} (ceiling Rs {self.limit:.0f})")

    def add(self, cost_usd: float, what: str = "") -> float:
        d = self._read()
        inr = cost_usd * self.fx
        d["spent_inr"] = round(d["spent_inr"] + inr, 4)
        d["entries"].append({"t": time.strftime("%Y-%m-%d %H:%M:%S"), "what": what[:120],
                             "usd": round(cost_usd, 6), "inr": round(inr, 4)})
        self._write(d)
        return d["spent_inr"]
