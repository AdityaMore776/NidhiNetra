"""The report's headline chart (T155) as SVG: accuracy and cost side by side, two panels, one
x-axis each (never a dual axis). Values are read from the comparison results, not typed in.

    python scripts/report_chart.py <vlm_compare_test_rules_subset.json> <out.svg>
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

OURS, GEMINI, OTHER = "#2a78d6", "#eb6834", "#a8a7a1"     # validated pair + a neutral
INK, MUTED, GRID, SURFACE = "#0b0b0b", "#52514e", "#e6e5e0", "#fcfcfb"
ROWS = [   # (judge key, label, colour)
    ("ours4b", "NidhiLens-FineTuned-Qwen4B (ours)", OURS),
    ("ours2b", "NidhiLens-FineTuned-Qwen2B (ours)", OURS),
    ("gem_pro31_rules", "Gemini 3.1 Pro, its best prompt", GEMINI),
    ("gem_pro31_batch", "Gemini 3.1 Pro, our prompt", GEMINI),
]


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;")


def main() -> None:
    res = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    n = next(iter(res.values()))["n"]
    f1 = {k: res[k]["macro_f1"] for k, *_ in ROWS}
    cost = {k: res[k]["usd_per_1000_checks"] for k, *_ in ROWS}
    W, label_w, panel_w, gap, top, row_h = 1100, 300, 330, 60, 92, 46
    H = top + row_h * len(ROWS) + 56
    x1 = label_w
    x2 = label_w + panel_w + gap
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
           f'viewBox="0 0 {W} {H}" font-family="Inter, Segoe UI, Arial, sans-serif">',
           f'<rect width="{W}" height="{H}" fill="{SURFACE}"/>',
           f'<text x="16" y="30" font-size="19" font-weight="600" fill="{INK}">Same {n} real '
           f'site-photo checks, labels checked by eye</text>',
           f'<text x="{x1}" y="68" font-size="14" font-weight="600" fill="{INK}">Macro-F1 '
           f'(higher is better)</text>',
           f'<text x="{x2}" y="68" font-size="14" font-weight="600" fill="{INK}">US$ per '
           f'1,000 checks (lower is better)</text>']
    cmax = max(cost.values()) * 1.15
    for t in (0, 0.25, 0.5, 0.75, 1.0):                    # recessive grid
        gx = x1 + t * panel_w
        out.append(f'<line x1="{gx:.1f}" y1="{top - 8}" x2="{gx:.1f}" '
                   f'y2="{top + row_h * len(ROWS)}" stroke="{GRID}" stroke-width="1"/>')
        out.append(f'<text x="{gx:.1f}" y="{top + row_h * len(ROWS) + 18}" font-size="11" '
                   f'fill="{MUTED}" text-anchor="middle">{t:.2f}</text>')
    for r, (k, label, col) in enumerate(ROWS):
        y = top + r * row_h
        out.append(f'<text x="{x1 - 12}" y="{y + 21}" font-size="13" fill="{INK}" '
                   f'text-anchor="end">{esc(label)}</text>')
        bw = f1[k] * panel_w
        out.append(f'<rect x="{x1}" y="{y + 6}" width="{bw:.1f}" height="22" rx="4" '
                   f'fill="{col}"/>')
        out.append(f'<text x="{x1 + bw + 6:.1f}" y="{y + 22}" font-size="13" fill="{INK}">'
                   f'{f1[k]:.3f}</text>')
        cw = max(2.0, cost[k] / cmax * panel_w)
        out.append(f'<rect x="{x2}" y="{y + 6}" width="{cw:.1f}" height="22" rx="4" '
                   f'fill="{col}"/>')
        out.append(f'<text x="{x2 + cw + 6:.1f}" y="{y + 22}" font-size="13" fill="{INK}">'
                   f'${cost[k]:.2f}</text>')
    out.append(f'<text x="16" y="{H - 12}" font-size="11" fill="{MUTED}">Costs: ours = '
               f'measured seconds on an NVIDIA L4 x Modal\'s price; Gemini = its billed tokens '
               f'(thinking included) x Google\'s Batch API price (live calls cost twice '
               f'this).</text>')
    out.append("</svg>")
    Path(sys.argv[2]).write_text("\n".join(out), encoding="utf-8")
    print("wrote", sys.argv[2])


if __name__ == "__main__":
    main()
