"""The image tools of the site video job (OpenCV + NumPy; free, CPU only).

Every threshold here is a design value to be measured in the field trial (T126): the trial plants
each trick (an old video, another site's video, a filmed screen, a new corner shown as progress)
and records whether these readings catch it, before Site Progress counts.
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

WIDTH = 640                 # frames are read at this width
EVERY_S = 0.5               # one frame every half second
MAX_FRAMES = 600            # five minutes at that rate
STRICT_BITS = 10            # fingerprints this close are the same frame (re-encoded at most)
MATCH_RATIO = 0.75          # Lowe's ratio test for matching points
RANSAC_PX = 5.0
MIN_GOOD = 12               # fewer good matches than this: no geometry is fitted
CHANGE_PIXEL = 40           # grey levels a pixel must change by, after lighting is evened out
SKY_SHARE = 0.25            # the top quarter of a view is left out of the change (sky, trees)
DARK, SHARP = 40.0, 60.0    # mean grey below DARK, or Laplacian variance below SHARP: poor frame


@dataclass
class Frame:
    t: float                # seconds from the start
    grey: np.ndarray        # WIDTH wide
    colour: np.ndarray      # WIDTH wide, BGR (only kept for viewpoint frames)
    brightness: float
    sharpness: float

    @property
    def usable(self) -> bool:
        return self.brightness >= DARK and self.sharpness >= SHARP


def _resize(img: np.ndarray) -> np.ndarray:
    h, w = img.shape[:2]
    return img if w <= WIDTH else cv2.resize(img, (WIDTH, round(h * WIDTH / w)),
                                             interpolation=cv2.INTER_AREA)


def frames(path: str, every_s: float = EVERY_S, max_frames: int = MAX_FRAMES) -> list[Frame]:
    """Frames every `every_s` seconds (by the video's own clock)."""
    cap = cv2.VideoCapture(str(path))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    step = max(1, round(fps * every_s))
    out, i = [], 0
    while len(out) < max_frames:
        ok, img = cap.read()
        if not ok:
            break
        if i % step == 0:
            colour = _resize(img)
            grey = cv2.cvtColor(colour, cv2.COLOR_BGR2GRAY)
            out.append(Frame(i / fps, grey, colour, float(grey.mean()),
                             float(cv2.Laplacian(grey, cv2.CV_64F).var())))
        i += 1
    cap.release()
    return out


def fingerprint(grey: np.ndarray) -> str:
    """256-bit perceptual fingerprint: 32x32 DCT, the 16x16 low frequencies against their median
    (the photo fingerprint's method, agents/photo_evidence/fingerprint.py), as 64 hex digits."""
    small = cv2.resize(grey, (32, 32), interpolation=cv2.INTER_AREA).astype(np.float32)
    d = cv2.dct(small)[:16, :16].reshape(256)
    return np.packbits(d > np.median(d[1:])).tobytes().hex()


def bits_apart(a: str, b: str) -> int:
    return (int(a, 16) ^ int(b, 16)).bit_count()


_ORB = None


def features(grey: np.ndarray):
    global _ORB
    if _ORB is None:
        _ORB = cv2.ORB_create(nfeatures=1500)
    return _ORB.detectAndCompute(grey, None)


def match(a, b) -> tuple[int, np.ndarray | None]:
    """(matching points in one geometry, homography mapping a onto b) between two (keypoints,
    descriptors) pairs. Many inliers mean the same scene, seen from about the same place."""
    (ka, da), (kb, db) = a, b
    if da is None or db is None or len(ka) < MIN_GOOD or len(kb) < MIN_GOOD:
        return 0, None
    pairs = cv2.BFMatcher(cv2.NORM_HAMMING).knnMatch(da, db, k=2)
    good = [m for m, *n in pairs if n and m.distance < MATCH_RATIO * n[0].distance]
    if len(good) < MIN_GOOD:
        return 0, None
    src = np.float32([ka[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
    dst = np.float32([kb[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)
    h, mask = cv2.findHomography(src, dst, cv2.RANSAC, RANSAC_PX)
    return (int(mask.sum()) if mask is not None else 0), h


def _even(grey: np.ndarray) -> np.ndarray:
    return cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(
        cv2.GaussianBlur(grey, (5, 5), 0))


def change(before: np.ndarray, after: np.ndarray, h: np.ndarray) -> float:
    """Share of the view (below the sky band) that changed from `before` to `after`, once
    `before` is warped onto `after` with homography `h` and lighting is evened out."""
    rows, cols = after.shape[:2]
    warped = cv2.warpPerspective(_even(before), h, (cols, rows))
    valid = cv2.warpPerspective(np.full(before.shape[:2], 255, np.uint8), h, (cols, rows)) > 0
    valid[: int(rows * SKY_SHARE), :] = False
    diff = cv2.absdiff(warped, _even(after)) > CHANGE_PIXEL
    diff = cv2.morphologyEx(diff.astype(np.uint8), cv2.MORPH_OPEN, np.ones((5, 5), np.uint8)) > 0
    n = int(valid.sum())
    return float((diff & valid).sum()) / n if n else 0.0


def flow(a: np.ndarray, b: np.ndarray) -> float:
    """Mean image motion between two frames, in pixels (dense optical flow at quarter size)."""
    sa = cv2.resize(a, (a.shape[1] // 4, a.shape[0] // 4))
    sb = cv2.resize(b, (b.shape[1] // 4, b.shape[0] // 4))
    f = cv2.calcOpticalFlowFarneback(sa, sb, None, 0.5, 3, 15, 3, 5, 1.2, 0)
    return float(np.linalg.norm(f, axis=2).mean()) * 4


_FACES = None


def blur_faces(colour: np.ndarray) -> tuple[np.ndarray, int]:
    """The frame with every detected face blurred, and how many there were (privacy, §9.9)."""
    global _FACES
    if _FACES is None:
        if not hasattr(cv2, "CascadeClassifier"):
            # OpenCV 5 moved the face detector out; never keep an unblurred frame (fail closed)
            raise RuntimeError("no face detector in this OpenCV: install opencv-python-headless "
                               "4.x (data/requirements-video.txt)")
        _FACES = cv2.CascadeClassifier(cv2.data.haarcascades
                                       + "haarcascade_frontalface_default.xml")
    out = colour.copy()
    grey = cv2.cvtColor(colour, cv2.COLOR_BGR2GRAY)
    faces = _FACES.detectMultiScale(grey, 1.1, 5, minSize=(24, 24))
    for x, y, w, h in faces:
        out[y:y + h, x:x + w] = cv2.GaussianBlur(out[y:y + h, x:x + w], (51, 51), 0)
    return out, len(faces)


def jpeg(colour: np.ndarray, quality: int = 80) -> bytes:
    ok, buf = cv2.imencode(".jpg", colour, [cv2.IMWRITE_JPEG_QUALITY, quality])
    return buf.tobytes() if ok else b""


def decode(data: bytes) -> np.ndarray:
    return cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
