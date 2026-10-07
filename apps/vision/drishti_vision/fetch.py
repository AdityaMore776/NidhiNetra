"""Fetching videos named in the manifest, politely, with a checksum (plan §4.1, §4.2).

- direct links (university archives, webcam timelapses, Wikimedia's upload server): downloaded once,
  the sha256 recorded, a later fetch verified against it;
- Wikimedia Commons file pages: the file's real address and licence come from the Commons API, and
  a licence different from the manifest's is refused;
- YouTube: the Data API's Creative Commons search proposes manifest rows. DOWNLOADING from YouTube
  is off until the owner decides (its terms are separate from the CC licence); then yt-dlp is used.

One request every POLITE_S seconds. Nothing is ever sent but the request itself; a YouTube API key
travels in a header, never in a URL.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import time
import urllib.parse
import urllib.request
from pathlib import Path

from drishti_vision.manifest import Video, problems

POLITE_S = 1.5
TIMEOUT_S = 60
UA = "DRISHTI-T146/0.1 (research; construction progress dataset)"
COMMONS_API = "https://commons.wikimedia.org/w/api.php"
YOUTUBE_SEARCH = "https://www.googleapis.com/youtube/v3/search"

# the licence names Commons reports, as manifest licences
COMMONS_LICENCES = {"cc0": "cc0", "public domain": "pd", "pd": "pd", "cc by": "cc-by",
                    "cc by-sa": "cc-by-sa"}

_last = 0.0


def _wait() -> None:
    global _last
    gap = POLITE_S - (time.monotonic() - _last)
    if gap > 0:
        time.sleep(gap)
    _last = time.monotonic()


def _get(url: str, headers: dict | None = None) -> urllib.request.addinfourl:
    _wait()
    req = urllib.request.Request(url, headers={"User-Agent": UA, **(headers or {})})
    return urllib.request.urlopen(req, timeout=TIMEOUT_S)  # noqa: S310 (http/https only, checked)


def sha256_of(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def commons_licence(short_name: str) -> str | None:
    """A Commons LicenseShortName ("CC BY-SA 4.0", "Public domain") as a manifest licence."""
    s = short_name.strip().lower()
    for prefix in sorted(COMMONS_LICENCES, key=len, reverse=True):
        if s.startswith(prefix):
            rest = s[len(prefix):]
            # "cc by" must not swallow "cc by-nc" or "cc by-nd"
            if prefix == "cc by" and rest.startswith("-"):
                continue
            return COMMONS_LICENCES[prefix]
    return None


def commons_file(info: dict) -> tuple[str, str | None]:
    """(download address, licence) from a Commons API `imageinfo` answer."""
    pages = info["query"]["pages"]
    page = next(iter(pages.values()))
    ii = page["imageinfo"][0]
    meta = ii.get("extmetadata", {})
    short = meta.get("LicenseShortName", {}).get("value", "")
    return ii["url"], commons_licence(short)


def _commons_lookup(title: str) -> dict:
    q = urllib.parse.urlencode({"action": "query", "titles": title, "prop": "imageinfo",
                                "iiprop": "url|extmetadata", "format": "json"})
    with _get(f"{COMMONS_API}?{q}") as r:
        return json.load(r)


def fetch(v: Video, dest: str | Path, allow_youtube: bool = False) -> Path:
    """Downloads one manifest row to `dest/<id><ext>` and fills v.sha256 (or checks it). Raises
    on a refused licence, a refused source, a changed file or a licence that does not match."""
    bad = problems(v)
    if bad:
        raise ValueError(f"{v.id}: " + "; ".join(bad))
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    url = v.url
    if v.source == "youtube":
        if not allow_youtube:
            raise PermissionError("downloading from YouTube waits for the owner's decision")
        return _yt_dlp(v, dest)
    if v.source == "wikimedia" and "/wiki/File:" in url:
        title = urllib.parse.unquote(url.split("/wiki/", 1)[1])
        url, lic = commons_file(_commons_lookup(title))
        if lic != v.licence:
            raise ValueError(f"{v.id}: Commons says the licence is {lic!r}, "
                             f"the manifest {v.licence!r}")
    if urllib.parse.urlparse(url).scheme not in ("http", "https"):
        raise ValueError(f"{v.id}: only http(s) addresses are fetched")
    ext = Path(urllib.parse.urlparse(url).path).suffix or ".mp4"
    out = dest / f"{v.id}{ext}"
    if not out.exists():
        tmp = out.with_suffix(out.suffix + ".part")
        with _get(url) as r, open(tmp, "wb") as f:
            shutil.copyfileobj(r, f)
        tmp.replace(out)
    digest = sha256_of(out)
    if v.sha256 and v.sha256 != digest:
        raise ValueError(f"{v.id}: the file changed since it was recorded (sha256 differs)")
    v.sha256 = digest
    return out


def _yt_dlp(v: Video, dest: Path) -> Path:
    if shutil.which("yt-dlp") is None:
        raise RuntimeError("yt-dlp is not installed")
    template = str(dest / f"{v.id}.%(ext)s")
    # video only (no audio, so no merging tool is needed), at most 720 lines
    cmd = ["yt-dlp", "-f", "bv*[height<=720][ext=mp4]/bv*[height<=720]/b[height<=720]",
           "-o", template, "--no-playlist", "--sleep-requests", str(POLITE_S), "--no-progress"]
    if shutil.which("node"):
        cmd += ["--js-runtimes", "node"]             # yt-dlp needs a JavaScript runtime for YouTube
    try:
        subprocess.run(cmd + [v.url], check=True)
    except subprocess.CalledProcessError as e:      # a removed or blocked video: skip it, go on
        raise RuntimeError(f"yt-dlp failed ({e.returncode})") from e
    out = next(dest.glob(f"{v.id}.*"))
    digest = sha256_of(out)
    if v.sha256 and v.sha256 != digest:
        raise ValueError(f"{v.id}: the file changed since it was recorded (sha256 differs)")
    v.sha256 = digest
    return out


def youtube_cc_search(query: str, max_results: int = 25, key: str | None = None,
                      page_token: str | None = None) -> tuple[list[dict], str | None]:
    """Creative Commons videos for `query` (the Data API's videoLicense=creativeCommon). Returns
    candidate rows for a person to check (work type, material, camera are not guessed here) and
    the next page's token. Needs YOUTUBE_API_KEY (free quota)."""
    key = key or os.environ.get("YOUTUBE_API_KEY")
    if not key:
        raise RuntimeError("set YOUTUBE_API_KEY")
    params = {"part": "snippet", "q": query, "type": "video", "videoLicense": "creativeCommon",
              "maxResults": max_results}
    if page_token:
        params["pageToken"] = page_token
    with _get(f"{YOUTUBE_SEARCH}?{urllib.parse.urlencode(params)}",
              headers={"X-goog-api-key": key}) as r:
        data = json.load(r)
    return [youtube_candidate(item) for item in data.get("items", [])], data.get("nextPageToken")


def youtube_candidate(item: dict) -> dict:
    vid = item["id"]["videoId"]
    sn = item["snippet"]
    return {"id": f"yt-{vid}", "url": f"https://www.youtube.com/watch?v={vid}",
            "source": "youtube", "licence": "cc-by", "attribution": sn.get("channelTitle", ""),
            "channel": sn.get("channelId", ""), "title": sn.get("title", ""),
            "published": sn.get("publishedAt", "")}
