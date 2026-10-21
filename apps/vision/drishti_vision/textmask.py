"""Writing in a site photo is greyed out before NidhiLens reads it (T172).

T168 measured that a sign saying "WORK COMPLETE" / "काम पूरा" held to the camera makes NidhiLens say
"shown" for 29.7% of claims that are not (1.9% on the same photos without the sign): the model reads
the words. A completed MPLADS work is meant to carry a plaque, so writing in a photo cannot simply
mean "can't tell"; instead every patch of writing (a sign, a plaque, a date or GPS stamp) is filled
with flat grey in both photos, and the model judges what is left: the site itself.

The detector is RapidOCR's text detector alone (no reading), on the CPU, about 0.3 s a photo. It
runs in the trial venv with the model (pip install rapidocr-onnxruntime), never in the engine.
"""

from __future__ import annotations

from functools import cache

import numpy as np

GREY = (128, 128, 128)
PAD = 0.25          # each box grows by a quarter of its height on every side (a sign's border)


@cache
def _detector():
    from rapidocr_onnxruntime import RapidOCR
    return RapidOCR()


def boxes(im) -> list[tuple[int, int, int, int]]:
    """Every patch of writing in a PIL image, as (x0, y0, x1, y1), padded and clipped."""
    res, _ = _detector()(np.asarray(im.convert("RGB"))[:, :, ::-1], use_det=True, use_cls=False,
                         use_rec=False)
    out = []
    for quad in res or []:
        p = np.asarray(quad, dtype=float)
        (x0, y0), (x1, y1) = p.min(0), p.max(0)
        pad = PAD * (y1 - y0)
        out.append((max(0, int(x0 - pad)), max(0, int(y0 - pad)),
                    min(im.width, int(x1 + pad + 1)), min(im.height, int(y1 + pad + 1))))
    return out


def mask(im):
    """(the image with its writing greyed out, the share of the image greyed)."""
    from PIL import ImageDraw
    found = boxes(im)
    if not found:
        return im, 0.0
    im = im.convert("RGB").copy()
    d = ImageDraw.Draw(im)
    hit = np.zeros((im.height, im.width), dtype=bool)
    for x0, y0, x1, y1 in found:
        d.rectangle((x0, y0, x1 - 1, y1 - 1), fill=GREY)
        hit[y0:y1, x0:x1] = True
    return im, float(hit.mean())
