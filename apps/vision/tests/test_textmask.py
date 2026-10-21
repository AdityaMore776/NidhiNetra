"""T172: writing in a site photo is greyed out before NidhiLens reads it (a fake detector: CI has
no OCR install)."""

from __future__ import annotations

import pytest
from PIL import Image

from drishti_vision import textmask


@pytest.fixture
def detector(monkeypatch):
    def fake(found):
        monkeypatch.setattr(textmask, "_detector", lambda: lambda arr, **kw: (found, 0.0))
    return fake


def test_a_sign_is_greyed_with_a_margin_and_its_share_reported(detector):
    detector([[[40, 40], [60, 40], [60, 50], [40, 50]]])          # 20 x 10 px of writing
    im = Image.new("RGB", (100, 100), (200, 30, 30))
    out, share = textmask.mask(im)
    assert out.getpixel((50, 45)) == textmask.GREY
    assert out.getpixel((38, 45)) == textmask.GREY                # the padding (a sign's border)
    assert out.getpixel((10, 10)) == (200, 30, 30)                # the site is left alone
    assert share == pytest.approx((25 * 15) / 10_000, abs=0.01)
    assert im.getpixel((50, 45)) == (200, 30, 30)                 # the original is untouched


def test_no_writing_leaves_the_photo_as_it_is(detector):
    detector(None)
    im = Image.new("RGB", (64, 48), (10, 20, 30))
    out, share = textmask.mask(im)
    assert out is im and share == 0.0


def test_boxes_are_clipped_to_the_photo(detector):
    detector([[[-5, -5], [30, -5], [30, 8], [-5, 8]]])
    assert textmask.boxes(Image.new("RGB", (40, 40))) == [(0, 0, 34, 12)]
