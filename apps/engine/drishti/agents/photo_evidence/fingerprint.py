"""A photo's fingerprint, and how alike two fingerprints are (T310, from T301).

The 256-bit perceptual fingerprint of data/trial/photo_trial.py: a 32x32 greyscale DCT, the
16x16 low frequencies against their median. Two photos within 51 differing bits are the same
picture (the loosest setting that confused no two different pilot photos); re-saved, resized,
brightened and stamped copies are caught, an 8% crop or a screenshot frame mostly not (70% of
all edited copies overall; feature matching (ORB), which caught 99.4%, needs OpenCV and is not
in the engine).

Computing a fingerprint needs Pillow, NumPy and SciPy (the evidence job's environment);
comparing two needs nothing: fingerprints are 64-character hex strings.
"""

from __future__ import annotations

MAX_BITS = 51


def phash256(path) -> str:
    """Fingerprint of an image file (imports the imaging libraries only when called)."""
    import numpy as np
    from PIL import Image, ImageOps
    from scipy.fftpack import dct

    img = ImageOps.exif_transpose(Image.open(path)).convert("L")
    a = np.asarray(img.resize((32, 32), Image.LANCZOS), dtype=np.float64)
    d = dct(dct(a, axis=1, norm="ortho"), axis=0, norm="ortho")[:16, :16].reshape(256)
    return np.packbits(d > np.median(d[1:])).tobytes().hex()


def bits_apart(a: str, b: str) -> int:
    return (int(a, 16) ^ int(b, 16)).bit_count()


def same_picture(a: str | None, b: str | None) -> bool:
    return bool(a and b) and bits_apart(a, b) <= MAX_BITS
