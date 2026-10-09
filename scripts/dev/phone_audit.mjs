// T143: the website on a phone. Opens each page in Chromium as a phone (390 px wide by default,
// touch, Lighthouse's mobile throttling: 150 ms round trip, 1.6 Mbps down, CPU 4x slower) and
// prints, per page:
//   - what it downloads (KB as sent over the network, by kind) and when its text and its largest
//     element first paint (FCP, LCP);
//   - its layout: text cut off at the screen's edge, boxes that scroll sideways, and the same
//     inside the work-form frame.
//
// Needs a production build running (cd apps/web && npm run build && npx next start -p 3100) and
// Playwright with Chromium (npm i -g playwright && npx playwright install chromium).
//
// usage: node scripts/dev/phone_audit.mjs [base=http://localhost:3100] [width=390] > out.txt
// Results: data/trial/results/phone_audit_before.txt (main before T143), phone_audit_after.txt.
import { createRequire } from "module";
import { execSync } from "child_process";

let pw;
try {
  pw = createRequire(import.meta.url)("playwright");
} catch {
  pw = createRequire(execSync("npm root -g").toString().trim() + "/")("playwright");
}

const base = process.argv[2] || "http://localhost:3100";
const width = Number(process.argv[3] || 390);
const PAGES = ["/", "/queue", "/works", "/work?id=WF-COST-4", "/work-form", "/work-form?example=cost_labour", "/explain", "/how-it-works", "/end-to-end", "/login"];
const RUNS = 3; // the median of three loads, each in a fresh browser profile

function layout() {
  const vw = document.documentElement.clientWidth;
  let cut = 0;
  let sideways = 0;
  for (const el of document.querySelectorAll("body *")) {
    const r = el.getBoundingClientRect();
    if (!r.width || !r.height || getComputedStyle(el).visibility === "hidden") continue;
    const s = getComputedStyle(el);
    if ((s.overflowX === "auto" || s.overflowX === "scroll") && el.scrollWidth > el.clientWidth + 2) sideways++;
    if (r.right > vw + 1 && el.childElementCount === 0 && (el.textContent || "").trim()) {
      let scrolled = false;
      for (let p = el.parentElement; p && p !== document.body; p = p.parentElement) {
        const o = getComputedStyle(p).overflowX;
        if (o === "auto" || o === "scroll") scrolled = true;
        if (o !== "visible") break;
      }
      if (!scrolled) cut++;
    }
  }
  return { cut, sideways, wider: document.documentElement.scrollWidth > vw + 1 };
}

const median = (xs) => [...xs].sort((a, b) => a - b)[Math.floor(xs.length / 2)];
const browser = await pw.chromium.launch();
console.log(`phone audit: ${base}, ${width} px, throttled (150 ms, 1.6 Mbps, CPU 4x), median of ${RUNS} loads`);
console.log("page | KB total (script, font) | FCP ms | LCP ms | text cut off | sideways boxes (in form frame)");
const totals = { kb: [], lcp: [] };
for (const path of PAGES) {
  const runs = [];
  for (let i = 0; i < RUNS; i++) {
    const ctx = await browser.newContext({ viewport: { width, height: 844 }, deviceScaleFactor: 2, isMobile: true, hasTouch: true });
    const page = await ctx.newPage();
    const cdp = await ctx.newCDPSession(page);
    await cdp.send("Network.enable");
    await cdp.send("Network.emulateNetworkConditions", { offline: false, latency: 150, downloadThroughput: (1638.4 * 1024) / 8, uploadThroughput: (675 * 1024) / 8 });
    await cdp.send("Emulation.setCPUThrottlingRate", { rate: 4 });
    const kinds = {};
    const bytes = { all: 0, Script: 0, Font: 0 };
    cdp.on("Network.responseReceived", (e) => (kinds[e.requestId] = e.type));
    cdp.on("Network.loadingFinished", (e) => {
      const k = kinds[e.requestId] ?? "Other";
      bytes.all += e.encodedDataLength;
      if (k in bytes) bytes[k] += e.encodedDataLength;
    });
    await page.addInitScript(() => {
      window.__lcp = 0;
      new PerformanceObserver((l) => l.getEntries().forEach((e) => (window.__lcp = e.startTime))).observe({ type: "largest-contentful-paint", buffered: true });
    });
    await page.goto(base + path, { waitUntil: "networkidle", timeout: 120000 });
    await page.waitForTimeout(1500);
    const t = await page.evaluate(() => ({ fcp: performance.getEntriesByName("first-contentful-paint")[0]?.startTime ?? 0, lcp: window.__lcp }));
    const main = await page.evaluate(layout);
    let frame = { cut: 0, sideways: 0 };
    for (const f of page.frames()) if (f !== page.mainFrame()) frame = await f.evaluate(layout).catch(() => frame);
    runs.push({ kb: bytes.all / 1024, script: bytes.Script / 1024, font: bytes.Font / 1024, ...t, main, frame });
    await ctx.close();
  }
  const m = (k) => Math.round(median(runs.map((r) => r[k])));
  const last = runs[runs.length - 1];
  totals.kb.push(m("kb"));
  totals.lcp.push(m("lcp"));
  console.log(
    `${path} | ${m("kb")} (${m("script")}, ${m("font")}) | ${m("fcp")} | ${m("lcp")} | ${last.main.cut}${last.main.wider ? " + page wider than the screen" : ""} | ${last.main.sideways} (${last.frame.sideways}, ${last.frame.cut} cut)`,
  );
}
await browser.close();
console.log(`median over the pages: ${median(totals.kb)} KB, LCP ${median(totals.lcp)} ms`);
