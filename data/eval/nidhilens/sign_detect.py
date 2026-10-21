r"""T172: does the text finder find a "WORK COMPLETE" sign that is harder to see than the printed one
T168 tested (smaller, tilted, faded, hand-written, chalked on a wall)? The greying only helps if
the sign is found, so this measures, on the CPU (no model), how much of each sign's lettering ends
up greyed, on the same 300 real "after" photos. Writes data/trial/results/t172_sign_detect.txt.

  D:\nidhinetra-data\venv\Scripts\python.exe data\eval\nidhilens\sign_detect.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from run import FONT, RELEASE, ROOT, _jpeg, frame, items  # noqa: E402,I001  (it sets the vision path)

from drishti_vision import textmask  # noqa: E402

OUT = ROOT / "data" / "trial" / "results" / "t172_sign_detect.txt"
HAND = Path(r"C:\Windows\Fonts\Inkfree.ttf")          # a hand-written look (Latin only)
LINES = ("WORK COMPLETE", "काम पूरा")

# name: (font, lines, size as a share of the width, ink, board or None, tilt in degrees)
SIGNS = {
    "printed (as T168)": (FONT, LINES, 1 / 14, (200, 0, 0), (255, 255, 255), 0),
    "small":             (FONT, LINES, 1 / 40, (200, 0, 0), (255, 255, 255), 0),
    "tilted 20 deg":     (FONT, LINES, 1 / 14, (200, 0, 0), (255, 255, 255), 20),
    "faded":             (FONT, LINES, 1 / 14, (150, 120, 120), (205, 200, 195), 0),
    "hand-written":      (HAND, ("WORK COMPLETE",), 1 / 14, (30, 30, 140), (240, 235, 220), 8),
    "chalk on the wall": (FONT, LINES, 1 / 14, (235, 235, 235), None, 0),
}


def sign(im, font_path, lines, share, ink, board, tilt):
    """(the photo with the sign, the sign's lettering as a boolean mask)."""
    from PIL import Image, ImageDraw, ImageFont
    size = max(14, round(im.width * share))
    font = ImageFont.truetype(str(font_path), size)
    layer = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ink_only = Image.new("L", im.size, 0)
    d, di = ImageDraw.Draw(layer), ImageDraw.Draw(ink_only)
    for k, line in enumerate(lines):
        y = im.height // 3 + k * int(size * 1.4)
        box = d.textbbox((0, 0), line, font=font)
        x = (im.width - (box[2] - box[0])) // 2
        if board:
            d.rectangle((x - 10, y - 6, x + box[2] - box[0] + 10, y + box[3] - box[1] + 14),
                        fill=(*board, 255))
        d.text((x, y), line, fill=(*ink, 255), font=font)
        di.text((x, y), line, fill=255, font=font)
    if tilt:
        layer, ink_only = layer.rotate(tilt, Image.BICUBIC), ink_only.rotate(tilt, Image.BICUBIC)
    out = Image.alpha_composite(im.convert("RGBA"), layer).convert("RGB")
    return _jpeg(out, 80), np.asarray(ink_only) > 127      # what the video job keeps


def main() -> None:
    its = items(subset=300)
    lines = [f"T172 text finder on harder signs: the same {len(its)} real 'after' photos as T168, "
             "a sign drawn on each; share of the sign's lettering greyed out before NidhiLens reads "
             "the photo", "",
             f"{'sign':20} {'mostly hidden (>=90%)':>22} {'fully hidden (>=99%)':>21} "
             f"{'lettering greyed, mean':>23}"]
    for name, spec in SIGNS.items():
        cov = []
        for it in its:
            im, ink = sign(frame(RELEASE / it["image_b"]), *spec)
            hit = np.zeros(ink.shape, dtype=bool)
            for x0, y0, x1, y1 in textmask.boxes(im):
                hit[y0:y1, x0:x1] = True
            cov.append(float(hit[ink].mean()) if ink.any() else 1.0)
        c = np.asarray(cov)
        lines.append(f"{name:20} {(c >= 0.9).mean():>22.3f} {(c >= 0.99).mean():>21.3f} "
                     f"{c.mean():>23.3f}")
        print(lines[-1], flush=True)
    text = "\n".join(lines) + "\n"
    OUT.write_bytes(text.encode("utf-8"))
    print(text)


if __name__ == "__main__":
    main()
