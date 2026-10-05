r"""End to end on one machine: the capture page -> the engine -> storage -> the video job -> Site
Progress (T123 + T124). A browser films a made-up site through a fake camera:

    visit 1  first visit (baseline) of hall H1: five viewpoints
    visit 2  monthly visit of H1: the same viewpoints, a wall built since
    visit 3  monthly visit of H1, done badly but honestly (T136, room for error): three viewpoints
             marked, two "can't reach", weak GPS (+-90 m) 150 m off the pin. The page lets it be
             uploaded with tips, and the reader says "can't tell" for the GPS
    visit 4  first visit of hall H2, filmed at H1's site (another work's place)

Pieces: a local Postgres (pgserver), the engine (uvicorn, dev sign-in), the web app (next dev),
a stand-in for Supabase Storage (a small HTTP server writing to a temporary folder), headless
Chromium with --use-file-for-fake-video-capture, and the video job with a local store. Nothing
real is filmed or kept: the scenes are drawn, and everything lives in a temporary folder.

Needs the video job's environment (OpenCV 4.x), Playwright for Python, the web app's
node_modules, and Chromium (PLAYWRIGHT_CHROMIUM or /opt/pw-browsers). Writes
data/trial/results/capture_e2e.json and .txt.
"""

from __future__ import annotations

import glob
import http.server
import json
import os
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
from datetime import date
from pathlib import Path

import cv2
import numpy as np
import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

ROOT = Path(__file__).resolve().parents[2]
ENGINE = ROOT / "apps" / "engine"
sys.path.insert(0, str(ENGINE))
from drishti import capture, migrate  # noqa: E402
from drishti.agents.site_progress import agent as site_progress  # noqa: E402
from drishti.batch import with_evidence  # noqa: E402
from drishti.video import job  # noqa: E402

OUT = ROOT / "data" / "trial" / "results" / "capture_e2e"
W, H, FPS = 480, 360, 10
VIEWS, DWELL, PAN = 5, 3.0, 1.5
SITE = (25.75, 82.69)
FORM = {"work": {"work_type": "COMMUNITY_HALL", "nature": "new"},
        "sites": [{"location": {"lat": SITE[0], "lon": SITE[1]},
                   "size": {"built_up_area_m2": 400}}]}


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def scene(seed: int, wall: bool = False, plaster: bool = False) -> np.ndarray:
    rng = np.random.default_rng(seed)
    img = np.full((H, W * 4, 3), 150, np.uint8)
    img[: H // 3] = (200, 180, 140)
    for _ in range(260):
        x, y = int(rng.integers(0, W * 4)), int(rng.integers(H // 3, H))
        c = tuple(int(v) for v in rng.integers(0, 255, 3))
        if rng.random() < 0.5:
            w, h = int(rng.integers(10, 70)), int(rng.integers(10, 60))
            cv2.rectangle(img, (x, y), (x + w, y + h), c, -1)
        else:
            cv2.circle(img, (x, y), int(rng.integers(5, 30)), c, -1)
    img = cv2.add(img, rng.integers(0, 40, img.shape, dtype=np.uint8))
    if wall:
        for k in range(VIEWS):
            x0 = int(k * (W * 3) / (VIEWS - 1)) + 60
            cv2.rectangle(img, (x0, H // 2), (x0 + 300, H - 20), (60, 60, 160), -1)
            for row in range(H // 2, H - 20, 24):
                cv2.line(img, (x0, row), (x0 + 300, row), (230, 230, 230), 2)
            if plaster:              # the next month: the walls plastered (new pixels to film)
                cv2.rectangle(img, (x0, H // 2), (x0 + 300, H - 20), (205, 215, 225), -1)
    return img


def y4m(path: Path, img: np.ndarray) -> None:
    """A walk past five viewpoints as a Y4M file, the format Chromium's fake camera reads."""
    xs = [int(k * (W * 3) / (VIEWS - 1)) for k in range(VIEWS)]
    with open(path, "wb") as f:
        f.write(f"YUV4MPEG2 W{W} H{H} F{FPS}:1 Ip A1:1 C420jpeg\n".encode())

        def put(crop):
            f.write(b"FRAME\n" + cv2.cvtColor(crop, cv2.COLOR_BGR2YUV_I420).tobytes())
        for k, x in enumerate(xs):
            for _ in range(int(DWELL * FPS)):
                put(img[:, x:x + W].copy())
            if k + 1 < len(xs):
                steps = int(PAN * FPS)
                for s in range(steps):
                    xx = int(x + (xs[k + 1] - x) * (s + 1) / steps)
                    put(img[:, xx:xx + W].copy())
        for _ in range(int(DWELL * FPS)):           # back at the first viewpoint
            put(img[:, xs[0]:xs[0] + W].copy())


class Storage(http.server.BaseHTTPRequestHandler):
    """Just enough of Supabase Storage: sign an upload, take the PUT, sign and serve a download."""
    root: Path

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "content-type, x-upsert, authorization")

    def _json(self, body: dict, code: int = 200):
        data = json.dumps(body).encode()
        self.send_response(code)
        self._cors()
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def _path(self, prefix: str) -> str:
        return self.path.split("?")[0][len(prefix):]

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        self.rfile.read(n)
        up = "/storage/v1/object/upload/sign/site-visits/"
        down = "/storage/v1/object/sign/site-visits/"
        if self.path.startswith(up):
            return self._json({"url": f"/object/upload/sign/site-visits/{self._path(up)}?token=t"})
        if self.path.startswith(down):
            return self._json({"signedURL": f"/object/sign/site-visits/{self._path(down)}?token=t"})
        self._json({"error": "not found"}, 404)

    def do_PUT(self):
        p = self.root / self._path("/storage/v1/object/upload/sign/site-visits/")
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(self.rfile.read(int(self.headers.get("Content-Length") or 0)))
        self._json({"Key": str(p.name)})

    def do_GET(self):
        p = self.root / self._path("/storage/v1/object/sign/site-visits/")
        if not p.exists():
            return self._json({"error": "not found"}, 404)
        data = p.read_bytes()
        self.send_response(200)
        self._cors()
        self.send_header("Content-Type", "image/jpeg")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *a):
        pass


def wait_http(url: str, seconds: float) -> None:
    end = time.time() + seconds
    while time.time() < end:
        try:
            urllib.request.urlopen(url, timeout=3)
            return
        except Exception:
            time.sleep(1)
    raise SystemExit(f"{url} did not come up")


def film(page, url: str, kind_label: str, claim: str | None, marks: list[str],
         skip: tuple[str, ...] = ()) -> str:
    page.goto(url)
    page.get_by_text("Start filming").wait_for(timeout=120_000)
    page.get_by_label(kind_label).check()
    if claim:
        page.get_by_placeholder("e.g. walls up to lintel level in all rooms").fill(claim)
    page.get_by_role("button", name="Start filming").click()
    page.get_by_text("Stop and upload").wait_for(timeout=30_000)
    for i, vid in enumerate(marks):
        if i:
            time.sleep(PAN)
        page.get_by_role("button", name=f"At viewpoint {vid}").click()
        time.sleep(DWELL - 0.6)
        page.get_by_role("button", name=f"Done at {vid}").click()
    for vid in skip:
        page.get_by_role("button", name=f"Can't reach viewpoint {vid}").click()
    time.sleep(2.5)
    stop = page.get_by_role("button", name="Stop and upload")
    for _ in range(30):
        if stop.is_enabled():
            break
        time.sleep(1)
    problems = page.locator("li.text-medium").all_inner_texts()
    stop.click()
    page.get_by_text("Uploaded.").wait_for(timeout=60_000)
    return "; ".join(problems)


def main() -> None:
    import pgserver
    from playwright.sync_api import sync_playwright

    tmp = Path(tempfile.mkdtemp(prefix="capture-e2e-"))
    store_dir = tmp / "store"
    store_dir.mkdir()
    vids = {"h1_base": tmp / "h1_base.y4m", "h1_wall": tmp / "h1_wall.y4m",
            "h1_plaster": tmp / "h1_plaster.y4m"}
    y4m(vids["h1_base"], scene(1))
    y4m(vids["h1_wall"], scene(1, wall=True))
    y4m(vids["h1_plaster"], scene(1, wall=True, plaster=True))

    srv = pgserver.get_server(str(tmp / "pg"), cleanup_mode="stop")
    url = srv.get_uri()
    migrate.apply(url)
    with psycopg.connect(url) as con:
        con.execute("INSERT INTO districts VALUES ('639','Anand','24','Gujarat')")
        for wid in ("H1", "H2"):
            con.execute("INSERT INTO works (work_id, source, state_lgd, state_name, district_lgd, "
                        "district_name, work_type_code, description, amount, status, "
                        "recommended_date) VALUES (%s,'SCENARIO','24','Gujarat','639','Anand',"
                        "'COMMUNITY_HALL','Community hall (made up)',900000,'SANCTIONED',"
                        "'2026-01-10')", (wid,))
            con.execute("INSERT INTO cost_forms (work_id, status, form, ready, submitted_at) "
                        "VALUES (%s,'submitted',%s,true,now())", (wid, Jsonb(FORM)))
        con.commit()

    sport = free_port()
    Storage.root = store_dir
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", sport), Storage)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()

    eport, wport = free_port(), free_port()
    env = {**os.environ, "DATABASE_URL": url, "DRISHTI_AUTH": "dev",
           "DRISHTI_CAPTURE_SECRET": "e2e-secret-sixteen-chars",
           "SUPABASE_URL": f"http://127.0.0.1:{sport}", "SUPABASE_SERVICE_ROLE_KEY": "e2e"}
    env.pop("VERCEL", None)
    engine = subprocess.Popen([sys.executable, "-m", "uvicorn", "drishti.main:app", "--port",
                               str(eport)], cwd=ENGINE, env=env, stdout=subprocess.DEVNULL,
                              stderr=subprocess.DEVNULL)
    web_env = {**os.environ, "ENGINE_DEV_URL": f"http://127.0.0.1:{eport}",
               "NEXT_PUBLIC_DEV_ROLE": "MINISTRY", "NEXT_TELEMETRY_DISABLED": "1"}
    for k in ("NEXT_PUBLIC_SUPABASE_URL", "NEXT_PUBLIC_SUPABASE_ANON_KEY"):
        web_env.pop(k, None)
    # its own process group, so stopping it stops next-server too (npx alone leaves it running)
    web = subprocess.Popen(["npx", "next", "dev", "-p", str(wport)], cwd=ROOT / "apps" / "web",
                           env=web_env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           start_new_session=True)
    out: dict = {"visits": []}
    try:
        wait_http(f"http://127.0.0.1:{eport}/api/v1/health", 60)
        wait_http(f"http://localhost:{wport}/login", 180)
        exe = os.environ.get("PLAYWRIGHT_CHROMIUM") or (
            glob.glob("/opt/pw-browsers/chromium-*/chrome-linux*/chrome") or [None])[0]
        every = [f"v{i + 1}" for i in range(VIEWS)]
        good_gps = {"latitude": SITE[0], "longitude": SITE[1], "accuracy": 6}
        weak_gps = {"latitude": SITE[0] + 150 / 111_195, "longitude": SITE[1], "accuracy": 90}
        plan = [("H1", "h1_base", "First visit", None, every, (), good_gps),
                ("H1", "h1_wall", "Monthly visit", "walls built", every, (), good_gps),
                ("H1", "h1_plaster", "Monthly visit", "walls plastered", every[:3],
                 ("v4", "v5"), weak_gps),
                ("H2", "h1_base", "First visit", None, every, (), good_gps)]
        with sync_playwright() as p:
            for work, video, label, claim, marks, skip, gps in plan:
                b = p.chromium.launch(executable_path=exe, args=[
                    "--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream",
                    f"--use-file-for-fake-video-capture={vids[video]}"])
                ctx = b.new_context(geolocation=gps, permissions=["geolocation", "camera"])
                page = ctx.new_page()
                warned = film(page, f"http://localhost:{wport}/capture?work={work}", label,
                              claim, marks, skip)
                b.close()
                with psycopg.connect(url, row_factory=dict_row) as con:
                    done = job.process(con, capture.LocalStore(store_dir))
                out["visits"].append({"work": work, "video": video, "kind": label,
                                      "page_warnings_at_stop": warned,
                                      "job": [d["status"] for d in done]})
        with psycopg.connect(url, row_factory=dict_row) as con:
            rows = con.execute("SELECT work_id, kind, status, readings, kept, video_path "
                               "FROM site_visits ORDER BY captured_at").fetchall()
            for v, r in zip(out["visits"], rows, strict=False):
                rd = r["readings"] or {}
                v["readings"] = {k: rd.get(k) for k in (
                    "sealed", "in_app", "quality_ok", "gps_inside", "views_match_site",
                    "viewpoints_expected", "viewpoints_matched", "change", "reused_from",
                    "same_place_as", "motion_consistent", "gps_weak", "viewpoints_skipped")}
                v["video_deleted"] = r["video_path"] is None
                v["frames_kept"] = len((r["kept"] or {}).get("viewpoints") or {})
            for wid in ("H1", "H2"):
                w = with_evidence(con, [{"work_id": wid, "status": "SANCTIONED",
                                         "cost_form": FORM}])[0]
                res = site_progress.assess(w, date.today())
                out[wid] = {"status": res.status.value, "findings": [f.code for f in res.findings],
                            "headline": res.headline}
    finally:
        os.killpg(web.pid, signal.SIGTERM)
        engine.terminate()
        httpd.shutdown()
        try:
            srv.cleanup()
        except OSError as exc:            # a sandbox that cannot run pg_ctl as its own user
            print(f"local Postgres not stopped cleanly ({exc}); stop it by hand")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.with_suffix(".json").write_text(json.dumps(out, indent=2, default=str) + "\n",
                                        encoding="utf-8")
    lines = ["Site capture end to end (made-up scenes, fake camera, local storage)", ""]
    for v in out["visits"]:
        lines.append(f"{v['work']} {v['kind']} ({v['video']}): job {v['job']}, video deleted "
                     f"{v.get('video_deleted')}, frames kept {v.get('frames_kept')}")
        lines.append(f"    readings {json.dumps(v.get('readings'))}")
        if v["page_warnings_at_stop"]:
            lines.append(f"    page warnings at stop: {v['page_warnings_at_stop']}")
    for wid in ("H1", "H2"):
        lines.append(f"Site Progress on {wid}: {out[wid]['status']}, findings "
                     f"{out[wid]['findings']}")
    OUT.with_suffix(".txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
