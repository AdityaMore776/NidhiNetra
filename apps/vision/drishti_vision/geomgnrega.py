"""GeoMGNREGA before / during / after photos, read through the public map's own requests (T151,
T152).

The Ministry of Rural Development and ISRO's NRSC geotag every MGNREGA asset with photos at three
stages:
stage 1 before the work, stage 2 during it, stage 3 after it, two photos each, on the public Bhuvan
portal (https://bhuvan-app2.nrsc.gov.in/mgnrega/mgnrega_phase2.php). These are real Indian public
works
(CC and interlocking roads, drains, Anganwadi buildings, ponds) photographed on phones: the closest
public data to MPLADS (plan T150 §4.1, source S1).

The portal offers no bulk export (its WFS is switched off), so this module makes only the requests
the
public page itself makes when a person clicks an asset, at one request every POLITE_S seconds:

  1. WMS GetMap of the public asset layer over a small box   -> where assets are drawn
  2. WMS GetFeatureInfo at those places                      -> asset records (sid, category, stage)
  3. get_details.php?sno=<sid>&uname=empty&mode=nm           -> the details page: photo addresses
     for
                                                                each stage, the work's name and
                                                                dates
  4. the photos themselves                                    -> resized, metadata stripped

Privacy: work names can contain a beneficiary's name ("... TO <NAME> KE GHAR TAK ..."). The local
record keeps the name for building claims (masked before use), but nothing from this module enters
git except code and counts (AGENTS.md rule 6). Photos and records live on D:\\nidhinetra-data only.
"""

from __future__ import annotations

import html
import json
import re
import time
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass, field
from pathlib import Path

import cv2
import numpy as np

POLITE_S = 1.5
TIMEOUT_S = 60
UA = "Mozilla/5.0 (research; NidhiNetra SIH26102 construction-progress dataset)"
WMS = "https://bhuvan-vec3.nrsc.gov.in/bhuvan/wms"
APP = "https://bhuvan-app2.nrsc.gov.in/bhugram/"
LAYER = "nrega:nrega_phase2_poly"
LICENCE = "gov-public"
ATTRIBUTION = "Ministry of Rural Development and NRSC/ISRO, Bhuvan GeoMGNREGA"

# MGNREGA categories that look like MPLADS works, and the work type each becomes (stages.STAGES)
CATEGORIES: dict[str, str] = {
    "05": "road",            # Rural Connectivity: CC, interlocking, kharanja roads, culverts
    "17": "building",        # Anganwadi / other rural infrastructure
    "03": "building",        # Bharat Nirman Sewa Kendra (panchayat buildings)
    "04": "drain",           # Rural Sanitation: drains, soak pits
    "06": "other",           # Play ground
    "01": "other",           # Renovation of traditional water bodies (ponds)
    "02": "other",           # Water conservation and harvesting
    "14": "other",           # Rural drinking water
}

_PHOTO = re.compile(r"https://bhuvan-fdc\d*\.nrsc\.gov\.in/object/[^\"' )]+?\.jpe?g", re.I)
_STAGE_PART = re.compile(r"/photos/(\d)/(\d{4}-\d{2})/")
_PHOTO_N = re.compile(r"/photo(\d)_")
_STAMP = re.compile(r"_(\d{1,2})_(\d{1,2})_(\d{1,2})_(\d{1,2})_(\d{1,2})_(\d{4})\.jpe?g$", re.I)
_ROW = re.compile(r"<tr>\s*<td[^>]*>(.*?)</td>\s*<td[^>]*>(.*?)</td>\s*</tr>", re.I | re.S)
_DIST = re.compile(r"Distance from Photo (\d) *=([\d.]+)m")

_last = [0.0]


@dataclass
class Photo:
    stage: int              # 1 before, 2 during, 3 after
    n: int                  # 1 or 2: the two photos of a stage
    url: str
    month: str              # YYYY-MM from the address
    taken: str = ""         # YYYY-MM-DDTHH:MM:SS from the file name, when present
    file: str = ""          # local file once fetched


@dataclass
class Asset:
    sid: int
    category_id: str
    subcategory_id: str
    state_code: str
    district_code: str
    block_code: str
    panchayat_code: str
    work_type: str
    feature_type: str = ""
    category: str = ""
    subcategory: str = ""
    work_name: str = ""             # LOCAL ONLY: may contain a beneficiary's name
    work_code: str = ""
    lon: float | None = None
    lat: float | None = None
    work_start: str = ""
    work_completion: str = ""
    area_length: str = ""
    distances_m: dict = field(default_factory=dict)   # photo n -> metres from the geotag point
    photos: list[Photo] = field(default_factory=list)

    def stages(self) -> list[int]:
        return sorted({p.stage for p in self.photos})


def _wait() -> None:
    gap = POLITE_S - (time.monotonic() - _last[0])
    if gap > 0:
        time.sleep(gap)
    _last[0] = time.monotonic()


def _get(url: str, tries: int = 2) -> bytes:
    """One polite GET; a dropped or cut-off transfer is tried once more, then raised as OSError
    (the callers skip that asset or photo and go on)."""
    import http.client
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Referer": APP + "bhugram.php"})
    for k in range(tries):
        _wait()
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT_S) as r:  # noqa: S310 (fixed hosts)
                return r.read()
        except (OSError, http.client.HTTPException) as e:
            if k == tries - 1:
                raise OSError(f"{type(e).__name__}: {e}") from e
    raise OSError("unreachable")


def _wms(bbox: tuple[float, float, float, float], size: int, cql: str, **extra) -> str:
    p = {"SERVICE": "WMS", "VERSION": "1.1.1", "LAYERS": LAYER, "STYLES": "",
         "SRS": "EPSG:4326", "BBOX": ",".join(f"{v:.6f}" for v in bbox), "WIDTH": size,
         "HEIGHT": size, "CQL_FILTER": cql, "TRANSPARENT": "TRUE", "VIEWPARAMS": "fyear:all",
         **extra}
    return WMS + "?" + urllib.parse.urlencode(p)


def cql_for(categories: list[str] | None = None, phase: str = "3") -> str:
    """Phase II ('3') assets carry the before / during / after photos; only accepted ones (status
    1)."""
    q = f"stage='{phase}' and status=1"
    if categories:
        q += " and category_id in (" + ",".join(f"'{c}'" for c in categories) + ")"
    return q


def drawn_points(png: bytes, max_points: int = 40) -> list[tuple[int, int]]:
    """Pixel centres of the drawn assets on a GetMap image (one point a blob)."""
    img = cv2.imdecode(np.frombuffer(png, np.uint8), cv2.IMREAD_UNCHANGED)
    if img is None or img.ndim != 3:
        return []
    alpha = img[..., 3] if img.shape[2] == 4 else img.sum(2)
    n, _lab, _stats, cent = cv2.connectedComponentsWithStats((alpha > 0).astype(np.uint8))
    pts = [(int(round(x)), int(round(y))) for x, y in cent[1:]]
    return pts[:max_points]


def features_at(bbox, size: int, cql: str, x: int, y: int, count: int = 20,
                buffer: int = 12) -> list[dict]:
    url = _wms(bbox, size, cql, REQUEST="GetFeatureInfo", QUERY_LAYERS=LAYER,
               INFO_FORMAT="application/json", X=x, Y=y, FEATURE_COUNT=count,
               BUFFER=buffer, FORMAT="image/png")
    try:
        js = json.loads(_get(url).decode("utf-8", "replace"))
    except (json.JSONDecodeError, OSError):
        return []
    return [f.get("properties", {}) for f in js.get("features", [])]


def find_assets(bbox, categories: list[str], size: int = 512, max_points: int = 40) -> list[dict]:
    """Asset records inside `bbox`, found the way a person clicking the public map finds them."""
    cql = cql_for(categories)
    png = _get(_wms(bbox, size, cql, REQUEST="GetMap", FORMAT="image/png"))
    seen: dict[int, dict] = {}
    for x, y in drawn_points(png, max_points):
        for props in features_at(bbox, size, cql, x, y):
            sid = props.get("sid")
            if sid is not None and sid not in seen:
                seen[sid] = props
    return list(seen.values())


# the sub-category's words decide the work type when they are clearer than the category
_TYPE_WORDS = (       # first match wins: a school's compound wall is a wall, not a building
    ("boundary_wall", ("boundary wall", "compound wall", "cmpond wall")),
    ("building", ("sanitary complex", "anganwadi", "gp ", "gp bhawan", "panchayat", "bhawan",
                  "building", "kendra", "school", "kitchen", "godown", "shed", "toilet")),
    ("drain", ("drain", "nali", "naala", "nala")),
    ("road", ("road", "kharanja", "interlocking", "murram", "path", "culvert", "causeway")),
)


def work_type_of(category_id: str, subcategory: str) -> str:
    s = f" {subcategory.lower()} "
    for wt, words in _TYPE_WORDS:
        if any(w in s for w in words):
            return wt
    return CATEGORIES.get(category_id, "other")


def _text(cell: str) -> str:
    cell = re.sub(r"<br\s*/?>", ", ", cell, flags=re.I)
    return html.unescape(re.sub(r"<[^>]+>", "", cell)).replace("\xa0", " ").strip()


def taken_from_name(url: str) -> str:
    m = _STAMP.search(url)
    if not m:
        return ""
    hh, mi, ss, dd, mo, yy = (int(g) for g in m.groups())
    return f"{yy:04d}-{mo:02d}-{dd:02d}T{hh:02d}:{mi:02d}:{ss:02d}"


def parse_details(page: str, props: dict) -> Asset:
    """The details page -> an Asset with every stage photo's address."""
    rows = {_text(k).lower(): _text(v) for k, v in _ROW.findall(page)}
    a = Asset(sid=int(props["sid"]), category_id=str(props.get("category_id", "")),
              subcategory_id=str(props.get("subcategory_id", "")),
              state_code=str(props.get("state_code", "")),
              district_code=str(props.get("district_code", "")),
              block_code=str(props.get("block_code", "")),
              panchayat_code=str(props.get("panchayat_code", "")),
              work_type=CATEGORIES.get(str(props.get("category_id", "")), "other"),
              feature_type=str(props.get("feature_type", "")))
    a.category = rows.get("category", "")
    a.subcategory = rows.get("sub-category", "")
    a.work_type = work_type_of(a.category_id, a.subcategory)
    a.work_name = rows.get("work name", "")
    a.work_code = rows.get("work code", "")
    a.work_start = rows.get("work start date", "")
    a.work_completion = rows.get("work completion date", "")
    a.area_length = rows.get("work current area/length", "")
    ll = rows.get("longitude/latitude", "")
    m = re.match(r"\s*([\d.]+)\s*/\s*([\d.]+)", ll)
    if m:
        a.lon, a.lat = float(m.group(1)), float(m.group(2))
    a.distances_m = {int(n): float(d) for n, d in _DIST.findall(page)}
    seen = set()
    for url in _PHOTO.findall(page):
        if url in seen:
            continue
        seen.add(url)
        sm, nm = _STAGE_PART.search(url), _PHOTO_N.search(url)
        if not sm or not nm:
            continue
        a.photos.append(Photo(int(sm.group(1)), int(nm.group(1)), url, sm.group(2),
                              taken_from_name(url)))
    a.photos.sort(key=lambda p: (p.stage, p.n))
    return a


def details(props: dict) -> Asset:
    q = urllib.parse.urlencode({"sno": props["sid"], "uname": "empty", "mode": "nm",
                                "stage": "3", "block_code": props.get("block_code", ""),
                                "key": "0.5"})
    page = _get(APP + "usrtasks/nrega_phase2/get/get_details.php?" + q).decode("utf-8", "replace")
    return parse_details(page, props)


def save_photo(data: bytes, out: Path, max_side: int = 1280) -> bool:
    """Decode, shrink to `max_side`, re-encode: the saved JPEG carries no EXIF or GPS block."""
    img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        return False
    h, w = img.shape[:2]
    s = max_side / max(h, w)
    if s < 1:
        img = cv2.resize(img, (round(w * s), round(h * s)), interpolation=cv2.INTER_AREA)
    out.parent.mkdir(parents=True, exist_ok=True)
    return bool(cv2.imwrite(str(out), img, [cv2.IMWRITE_JPEG_QUALITY, 90]))


def fetch_photos(a: Asset, root: Path) -> int:
    got = 0
    for p in a.photos:
        out = root / f"mg-{a.sid}" / f"s{p.stage}_p{p.n}.jpg"
        if not out.exists():
            try:
                if not save_photo(_get(p.url), out):
                    continue
            except OSError:
                continue
        p.file = str(out.relative_to(root)).replace("\\", "/")
        got += 1
    return got


def to_row(a: Asset) -> dict:
    return asdict(a) | {"id": f"mg-{a.sid}", "source": "geomgnrega", "licence": LICENCE,
                        "attribution": ATTRIBUTION}


def harvest(boxes: list[tuple[str, tuple[float, float, float, float]]], categories: list[str],
            root: str | Path, records: str | Path, per_box: int = 25, max_assets: int = 100,
            need_stages: tuple[int, ...] = (1, 3), log=print) -> dict:
    """Walks `boxes` (name, bbox), keeps assets with photos at every stage in `need_stages`, and
    appends one JSON line an asset to `records`. Resumable: assets already recorded are skipped."""
    root, records = Path(root), Path(records)
    root.mkdir(parents=True, exist_ok=True)
    done = set()
    if records.exists():
        for line in records.read_text(encoding="utf-8").splitlines():
            if line.strip():
                done.add(json.loads(line)["sid"])
    stats = {"boxes": 0, "found": 0, "kept": 0, "skipped_stages": 0, "already": len(done)}
    with open(records, "a", encoding="utf-8") as out:
        for name, bbox in boxes:
            if stats["kept"] >= max_assets:
                break
            stats["boxes"] += 1
            try:
                found = find_assets(bbox, categories)
            except OSError as e:
                log(f"{name}: map not read ({e})")
                continue
            stats["found"] += len(found)
            kept_here = 0
            for props in found:
                if kept_here >= per_box or stats["kept"] >= max_assets:
                    break
                if props.get("sid") in done:
                    continue
                try:
                    a = details(props)
                except OSError as e:
                    log(f"{name} {props.get('sid')}: details not read ({e})")
                    continue
                if not all(s in a.stages() for s in need_stages):
                    stats["skipped_stages"] += 1
                    continue
                if fetch_photos(a, root) < 2:
                    continue
                out.write(json.dumps(to_row(a), ensure_ascii=False) + "\n")
                out.flush()
                done.add(a.sid)
                kept_here += 1
                stats["kept"] += 1
            log(f"{name}: {len(found)} assets on the map, {kept_here} kept "
                f"(total {stats['kept']})")
    return stats


# Rough centres of rural areas in districts spread over the country (lat, lon): the split is by
# district, so many districts give a test set from places the model never saw (plan T150 §4.2).
PLACES: dict[str, tuple[float, float]] = {
    "UP-Jaunpur": (25.75, 82.68), "UP-Ghazipur": (25.58, 83.58), "UP-Azamgarh": (26.07, 83.18),
    "UP-Pratapgarh": (25.90, 81.95), "UP-Sitapur": (27.57, 80.68), "UP-Gorakhpur": (26.76, 83.37),
    "UP-Bareilly": (28.37, 79.43), "UP-Banda": (25.48, 80.33),
    "BR-Gaya": (24.79, 85.00), "BR-Muzaffarpur": (26.12, 85.39), "BR-Purnia": (25.78, 87.47),
    "MP-Sagar": (23.84, 78.74), "MP-Rewa": (24.53, 81.30), "RJ-Bhilwara": (25.35, 74.63),
    "RJ-Nagaur": (27.20, 73.73), "MH-Ahmednagar": (19.09, 74.74), "MH-Nanded": (19.15, 77.31),
    "TN-Villupuram": (11.94, 79.49), "TN-Tiruvannamalai": (12.23, 79.07),
    "OD-Ganjam": (19.38, 84.98), "OD-Mayurbhanj": (21.93, 86.73), "WB-Bankura": (23.23, 87.07),
    "WB-Purulia": (23.33, 86.36), "KA-Belagavi": (15.85, 74.50), "KA-Tumakuru": (13.34, 77.10),
    "AP-Anantapur": (14.68, 77.60), "TG-Nalgonda": (17.05, 79.27), "GJ-Dahod": (22.83, 74.25),
    "JH-Ranchi": (23.35, 85.33), "CG-Bilaspur": (22.08, 82.15), "KL-Palakkad": (10.78, 76.65),
    "AS-Nagaon": (26.35, 92.68), "PB-Sangrur": (30.25, 75.84), "HR-Hisar": (29.15, 75.72),
    "HP-Mandi": (31.71, 76.93), "UK-Almora": (29.60, 79.66),
}


def boxes_around(name: str, lat: float, lon: float, half: float = 0.04,
                 grid: int = 2) -> list[tuple[str, tuple[float, float, float, float]]]:
    """A grid x grid set of small boxes around a point (a district's rural area)."""
    out = []
    step = 2 * half
    off = (grid - 1) / 2
    for i in range(grid):
        for j in range(grid):
            cx, cy = lon + (i - off) * step * 1.5, lat + (j - off) * step * 1.5
            out.append((f"{name}-{i}{j}", (cx - half, cy - half, cx + half, cy + half)))
    return out
