r"""The work intelligence form page end to end, in a real browser (T134).

A local Postgres (pgserver) holds the district of Jaunpur's 1,038 real works from the eSAKSHI
dashboard tables; the engine (uvicorn, the public view: no sign-in) and the web app (next dev)
run on top. Headless Chromium then does what a judge would on /work-form:

  0. the public dashboard's card opens the page;
  1. every example filing: the chip fills the framed form (its own fields, read back), and the
     side panel shows the agents' verdict the examples file holds for it;
  2. a deep link /work-form?example=<id> opens with that filing;
  3. "Check this form with the agents" on each loaded example sends the form to
     POST /api/v1/work-form/check?demo=true (the same example data, nothing stored): the same
     flags, the flagged fields outlined in the form; "Show in form" scrolls to one; the cement
     of "twice the cement" set back to what the road needs clears Cost's flags; the Data tab;
  4. the same on a form with its district removed: a plain message, no error page.

Needs: the engine's requirements and Playwright for Python (the video job's environment has
both, plus pgserver), the web app's node_modules, Chromium. Writes results/work_form_e2e.txt
(+ .json) and screenshots to a temporary folder it names.
"""

from __future__ import annotations

import glob
import json
import os
import signal
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

import pgserver
import psycopg
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "data"))
sys.path.insert(0, str(ROOT / "apps" / "engine"))
from esakshi_dashboard import load  # noqa: E402

from drishti import migrate  # noqa: E402

OUT = ROOT / "data" / "trial" / "results" / "work_form_e2e"
EXAMPLES = ROOT / "apps" / "web" / "public" / "work-form" / "examples.json"
COLUMNS = ("work_id", "source", "state_lgd", "state_name", "district_lgd", "district_name",
           "agency_name", "work_type_code", "description", "amount", "status",
           "recommended_date", "sanction_date", "completed_date")


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def wait_http(url: str, seconds: float) -> None:
    end = time.time() + seconds
    while time.time() < end:
        try:
            urllib.request.urlopen(url, timeout=3)
            return
        except OSError:
            time.sleep(1)
    raise SystemExit(f"{url} did not come up")


def main() -> None:
    tmp = Path(tempfile.mkdtemp(prefix="work-form-e2e-"))
    shots = tmp / "shots"
    shots.mkdir()
    works, info = load()
    jaunpur = [w for w in works if w.get("district_name") == "Jaunpur"]
    d = jaunpur[0]
    srv = pgserver.get_server(str(tmp / "pg"), cleanup_mode="stop")
    url = srv.get_uri()
    migrate.apply(url)
    with psycopg.connect(url) as con:
        con.execute("INSERT INTO districts VALUES (%s, 'Jaunpur', %s, %s)",
                    (d["district_lgd"], d.get("state_lgd"), d.get("state_name")))
        with con.cursor() as cur:
            cur.executemany(f"INSERT INTO works ({', '.join(COLUMNS)}) VALUES "
                            f"({', '.join(['%s'] * len(COLUMNS))}) ON CONFLICT DO NOTHING",
                            [tuple("REAL" if c == "source" else w.get(c) for c in COLUMNS)
                             for w in jaunpur])
        con.commit()

    eport, wport = free_port(), free_port()
    env = {**os.environ, "DATABASE_URL": url, "DRISHTI_AUTH": "dev",
           "DRISHTI_SNAPSHOT_DATE": str(info["as_of"])}
    env.pop("VERCEL", None)
    engine = subprocess.Popen([sys.executable, "-m", "uvicorn", "drishti.main:app", "--port",
                               str(eport)], cwd=ROOT / "apps" / "engine", env=env,
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    web_env = {**os.environ, "ENGINE_DEV_URL": f"http://127.0.0.1:{eport}",
               "NEXT_TELEMETRY_DISABLED": "1"}
    for k in ("NEXT_PUBLIC_SUPABASE_URL", "NEXT_PUBLIC_SUPABASE_ANON_KEY", "NEXT_PUBLIC_DEV_ROLE"):
        web_env.pop(k, None)
    web = subprocess.Popen(["npx", "next", "dev", "-p", str(wport)], cwd=ROOT / "apps" / "web",
                           env=web_env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           start_new_session=True)
    examples = json.loads(EXAMPLES.read_text(encoding="utf-8"))["examples"]
    out: dict = {"works_loaded": len(jaunpur), "examples": [], "checks": []}
    errors: list[str] = []
    try:
        wait_http(f"http://127.0.0.1:{eport}/api/v1/health", 60)
        wait_http(f"http://localhost:{wport}/login", 240)
        exe = os.environ.get("PLAYWRIGHT_CHROMIUM") or (
            glob.glob("/opt/pw-browsers/chromium-*/chrome-linux*/chrome") or [None])[0]
        with sync_playwright() as p:
            b = p.chromium.launch(executable_path=exe)
            page = b.new_page(viewport={"width": 1440, "height": 1000})
            page.on("pageerror", lambda e: errors.append(str(e)))
            # the public dashboard links to the filings
            page.goto(f"http://localhost:{wport}/", wait_until="networkidle")
            page.get_by_text("Twelve example filings of the work intelligence form").click(
                timeout=120_000)
            page.wait_for_url("**/work-form", timeout=120_000)
            page.get_by_role("heading", name="Example filings").wait_for(timeout=120_000)
            out["from_dashboard"] = page.evaluate("location.pathname")
            frame = page.frame_locator("iframe[title*='Work Intelligence Form']")
            for ex in examples:
                page.get_by_role("button", name=ex["title"], exact=True).click()
                page.wait_for_timeout(500)
                title = frame.locator("input[name='work_title']").input_value()
                agency = frame.locator("input[name='implementing_agency']").input_value()
                rows = frame.locator("#boqBody tr").count()
                aside = page.locator("aside")
                codes = sorted(f["code"] for c in ex["trace"]["checks"]
                               for f in c["findings"] if f["risk"] > 0)
                asked = [c["id"] for c in ex["trace"]["checks"]
                         if any(f["risk"] > 0 for f in c["findings"])]
                flagged = aside.get_by_text("Flagged", exact=True).count()
                marks = frame.locator(".nn-flag").count()
                ok = (title == ex["form"]["work_title"]
                      and agency == ex["form"]["implementing_agency"]
                      and ex["title"] in aside.inner_text() and flagged == len(asked)
                      and (marks > 0) == bool(asked))
                page.screenshot(path=str(shots / f"{ex['id']}.png"))
                # the live check of the loaded filing, against the same example data
                with page.expect_response(lambda r: "/api/v1/work-form/check" in r.url,
                                          timeout=180_000) as r:
                    page.get_by_role("button", name="Check this form with the agents").click()
                live = r.value.json()
                page.get_by_text("Your form, checked just now").wait_for(timeout=60_000)
                page.wait_for_timeout(300)
                live_codes = sorted(f["code"] for c in live["trace"]["checks"]
                                    for f in c["findings"] if f["risk"] > 0)
                out["examples"].append({
                    "id": ex["id"], "filled": title == ex["form"]["work_title"],
                    "boq_rows": rows, "panel_ok": ok, "flagged_agents": flagged,
                    "fields_marked": marks, "codes": codes, "live_codes": live_codes,
                    "live_marks": frame.locator(".nn-flag").count()})
                page.screenshot(path=str(shots / f"check_{ex['id']}.png"))
            # "Show in form" scrolls the form to the flagged field
            page.get_by_role("button", name="Twice the cement the road can use").click()
            page.wait_for_timeout(500)
            page.locator("aside").get_by_role("button", name="Show in form").first.click()
            page.wait_for_timeout(1200)
            out["show_in_form"] = frame.locator(".nn-flag").first.evaluate(
                "e => { const r = e.getBoundingClientRect(); "
                "return r.top >= 0 && r.bottom <= window.innerHeight; }")
            page.screenshot(path=str(shots / "show_in_form.png"))
            # an officer's fix: the cement back to what the road needs, then check again
            need = next(c for c in examples if c["id"] == "cost_quantity")
            honest = round(float(need["form"]["boq_qty_1"]) / 2)
            frame.locator("input[name='boq_qty_1']").fill(str(honest))
            with page.expect_response(lambda r: "/api/v1/work-form/check" in r.url,
                                      timeout=180_000) as r:
                page.get_by_role("button", name="Check this form with the agents").click()
            fixed = r.value.json()
            page.get_by_text("Your form, checked just now").wait_for(timeout=60_000)
            out["fixed_cement"] = {
                "bags": honest,
                "codes": sorted(f["code"] for c in fixed["trace"]["checks"]
                                for f in c["findings"] if f["risk"] > 0),
                "band": fixed["trace"]["result"]["band"]}
            page.screenshot(path=str(shots / "fixed_cement.png"))
            # the Data tab, and back to a form that is still filled
            page.get_by_role("tab", name="Data the agents use").click()
            page.get_by_text("Prices other agencies filed").wait_for(timeout=30_000)
            data_text = page.locator("main").last.inner_text()
            out["data_tab"] = all(x in data_text for x in (
                "Cement OPC 43 grade", "WF-OLD-ROAD", "Rules the agents use", "After sanction"))
            page.screenshot(path=str(shots / "data_tab.png"), full_page=True)
            page.get_by_role("tab", name="Form and flags").click()
            out["form_kept"] = frame.locator("input[name='boq_qty_1']").input_value() == str(honest)
            # a deep link opens with its filing
            page.goto(f"http://localhost:{wport}/work-form?example=time_fast",
                      wait_until="networkidle")
            page.get_by_text("Recorded complete 6 days after sanction", exact=False).first.wait_for(
                timeout=60_000)
            page.wait_for_timeout(1500)
            out["deep_link"] = frame.locator("input[name='recommendation_ref']").input_value()
            # no district: a plain message
            page.get_by_role("button", name="Every line a little high", exact=False).click()
            page.wait_for_timeout(400)
            frame.locator("input[name='district']").fill("")
            page.get_by_role("button", name="Check this form with the agents").click()
            page.get_by_text("Write the district in section C").wait_for(timeout=60_000)
            out["checks"].append({"form": "no district", "answer": "asks for the district"})
            b.close()
    finally:
        os.killpg(web.pid, signal.SIGTERM)
        engine.terminate()
        try:
            srv.cleanup()
        except OSError as exc:            # a sandbox that cannot run pg_ctl as its own user
            print(f"local Postgres not stopped cleanly ({exc}); stop it by hand")
    out["page_errors"] = errors
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.with_suffix(".json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    lines = [f"Work intelligence form page end to end: {len(jaunpur)} real Jaunpur works loaded",
             f"public dashboard link opened {out.get('from_dashboard')}", ""]
    for e in out["examples"]:
        lines.append(f"{e['id']:15} form filled {e['filled']!s:5} BOQ rows {e['boq_rows']:2} "
                     f"verdict panel {'ok' if e['panel_ok'] else 'WRONG'}")
    lines += ["", "Live check of each loaded filing (POST /work-form/check?demo=true, the same "
              "example data):"]
    for e in out["examples"]:
        same = "same" if e["codes"] == e["live_codes"] else "DIFFERS"
        lines.append(f"{e['id']:15} flags {', '.join(e['codes']) or '-'}; live {same}; "
                     f"fields marked {e['fields_marked']} (after the live check "
                     f"{e['live_marks']})")
    fx = out.get("fixed_cement") or {}
    lines += ["", f"\"Show in form\" brought the flagged field into view: {out.get('show_in_form')}",
              f"cost_quantity with the cement set to {fx.get('bags')} bags: flags "
              f"{', '.join(fx.get('codes') or []) or 'none'}; band {fx.get('band')}",
              f"Data tab shows prices, works on record, after sanction, rules: "
              f"{out.get('data_tab')}; the form kept its edit: {out.get('form_kept')}"]
    lines += ["", f"deep link ?example=time_fast opened {out.get('deep_link')}"]
    lines.append(f"live check without a district: {out['checks'][0]['answer']}")
    lines.append(f"page errors: {len(errors)}")
    OUT.with_suffix(".txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print(f"screenshots: {shots}")


if __name__ == "__main__":
    main()
