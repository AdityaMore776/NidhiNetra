/*
  DEV-ONLY mock of the DRISHTI engine API (apps/engine/drishti/api/routes.py).

  This exists solely so the web UI can be previewed without the Python engine and
  its Postgres corpus. It serves the exact response shapes with clearly-synthetic
  SAMPLE data — it is never imported by the app and never deployed. Do not use any
  figure from here as real.

  Run:  node scripts/mock-engine.mjs   (listens on :8000; next dev proxies /api/v1)
*/
import { createServer } from "node:http";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const HERE = dirname(fileURLToPath(import.meta.url));
const PORT = 8000;

// Deterministic PRNG so pagination and detail lookups are stable across requests.
function rng(seed) {
  let s = seed >>> 0;
  return () => {
    s = (s * 1664525 + 1013904223) >>> 0;
    return s / 0xffffffff;
  };
}
const pick = (r, arr) => arr[Math.floor(r() * arr.length)];

// Real district codes/names from the shipped geo file (so the map lights up).
const geo = JSON.parse(readFileSync(join(HERE, "..", "public", "geo", "districts.json"), "utf8"));
const geoDistricts = geo.features
  .map((f) => f.properties)
  .filter((p) => p.code && p.name)
  .slice(0, 90);

const WORK_TYPES = [
  ["ROAD_CC", "Cement concrete road"],
  ["ROAD_BT", "Bituminous road"],
  ["CULVERT", "Culvert / small bridge"],
  ["COMMUNITY_HALL", "Community hall / bhavan"],
  ["SCHOOL_BUILDING", "School building / classroom"],
  ["DRAIN", "Drainage / nala"],
  ["STREET_LIGHT", "Solar / LED street light"],
  ["BOREWELL", "Borewell / hand pump"],
  ["TOILET_BLOCK", "Public toilet block"],
  ["WATER_TANK", "Overhead water tank"],
  ["CCTV", "CCTV system"],
  ["BUS_SHELTER", "Bus shelter"],
];
const VILLAGES = ["Rampur", "Lakshmipur", "Govindpur", "Shivpur", "Krishnanagar", "Bhagatpur", "Mohanpur", "Narayanpur"];
const AGENCIES = ["PWD Sub-Division", "Rural Engineering Service", "Zilla Parishad", "Municipal Council", "Panchayati Raj Dept"];
const HEADLINES_HIGH = [
  "Cost is 3.4× the district median for this work type",
  "Reported cost far above the peer range and published rates",
  "Road cost per metre well above the state schedule of rates",
];
const HEADLINES_MED = [
  "Cost above the typical range for similar works nearby",
  "Amount just under the ₹5 lakh limit for this work type",
  "Cost higher than most peers in the same district",
];
const HEADLINES_LOW = ["Cost within the typical range for peers", "No cost anomaly found"];

function makeWorks(n) {
  const r = rng(20260526);
  const works = [];
  for (let i = 0; i < n; i++) {
    const d = pick(r, geoDistricts);
    const [code, name] = pick(r, WORK_TYPES);
    const roll = r();
    const band = roll > 0.86 ? "HIGH" : roll > 0.62 ? "MEDIUM" : "LOW";
    const score = band === "HIGH" ? 0.6 + r() * 0.38 : band === "MEDIUM" ? 0.3 + r() * 0.29 : r() * 0.29;
    const amount = Math.round((40000 + r() * 4800000) / 1000) * 1000;
    const village = pick(r, VILLAGES);
    const limited = band === "LOW" && r() > 0.7;
    const alerts = [];
    if (band !== "LOW") alerts.push("statistical");
    if (r() > 0.7) alerts.push("validation");
    const headline =
      band === "HIGH" ? pick(r, HEADLINES_HIGH) : band === "MEDIUM" ? pick(r, HEADLINES_MED) : pick(r, HEADLINES_LOW);
    works.push({
      work_id: `SAMPLE-${String(100000 + i)}`,
      source: "SCENARIO",
      district_lgd: d.code,
      district_name: d.name,
      state_name: d.state,
      work_type_code: code,
      description: `${name} at ${village}, near the ${pick(r, ["primary school", "panchayat office", "market", "bus stand"])}`,
      amount,
      status: pick(r, ["Completed", "In progress", "Sanctioned"]),
      recommended_date: `2025-${String(1 + Math.floor(r() * 12)).padStart(2, "0")}-${String(1 + Math.floor(r() * 27)).padStart(2, "0")}`,
      band,
      score: Number(score.toFixed(3)),
      priority: Number((score * Math.log10(amount)).toFixed(3)),
      limited,
      alerts,
      headline,
      _name: name,
      _village: village,
      _agency: pick(r, AGENCIES),
      _completed: `2025-${String(1 + Math.floor(r() * 12)).padStart(2, "0")}-${String(1 + Math.floor(r() * 27)).padStart(2, "0")}`,
    });
  }
  return works;
}

const ALL = makeWorks(240);
const REVIEW = ALL.filter((w) => w.band !== "HIGH" ? w.band === "MEDIUM" : true).sort((a, b) => b.priority - a.priority);
const byId = new Map(ALL.map((w) => [w.work_id, w]));

function summary() {
  const bands = { HIGH: 0, MEDIUM: 0, LOW: 0 };
  for (const w of ALL) bands[w.band]++;
  // Scale to a realistic corpus size for display.
  const scale = 875;
  return {
    works: 209993,
    amount: 1.94e12,
    bands: { HIGH: bands.HIGH * scale, MEDIUM: bands.MEDIUM * scale, LOW: 209993 - (bands.HIGH + bands.MEDIUM) * scale },
    agents: [
      { id: "site_progress", name: "Site Progress", question: "Does the site evidence match the claimed progress?", built: false, alerts: 0 },
      { id: "image_reuse", name: "Image Reuse", question: "Has the same image appeared elsewhere?", built: false, alerts: 0 },
      { id: "duplicate_project", name: "Duplicate Project", question: "Is a similar work already recorded nearby?", built: false, alerts: 0 },
      { id: "statistical", name: "Statistical", question: "Is the project cost unusual for similar works?", built: true, alerts: 1841 },
    ],
    validation_alerts: 3427,
    snapshot_date: "2026-05-26",
  };
}

function districts() {
  const r = rng(7);
  const agg = new Map();
  for (const d of geoDistricts) {
    const works = 40 + Math.floor(r() * 900);
    const review = Math.floor(works * (0.002 + r() * 0.03));
    agg.set(d.code, {
      district_lgd: d.code,
      name: d.name,
      state: d.state,
      works,
      amount: works * (300000 + Math.floor(r() * 500000)),
      review,
      share: review / works,
    });
  }
  return [...agg.values()];
}

function offices() {
  const r = rng(11);
  return geoDistricts.slice(0, 9).map((d) => {
    const completed = 60 + Math.floor(r() * 300);
    const bad = Math.floor(completed * (0.1 + r() * 0.4));
    return {
      agency_name: `${pick(r, AGENCIES)}, ${d.name}`,
      completed,
      bad,
      rate: bad / completed,
      lift: 3 + Math.floor(r() * 9),
      district_lgd: d.code,
      district_name: d.name,
      state_name: d.state,
    };
  });
}

function page(list, params) {
  const size = 25;
  let items = list;
  if (params.band) items = items.filter((w) => w.band === params.band);
  if (params.district) items = items.filter((w) => w.district_lgd === params.district);
  if (params.type) items = items.filter((w) => w.work_type_code === params.type);
  if (params.q) {
    const q = params.q.toLowerCase();
    items = items.filter((w) => w.description.toLowerCase().includes(q) || w.work_id.toLowerCase().includes(q));
  }
  const p = Math.max(1, parseInt(params.page || "1", 10));
  const start = (p - 1) * size;
  const strip = (w) => {
    const out = {};
    for (const [k, v] of Object.entries(w)) if (!k.startsWith("_")) out[k] = v;
    return out;
  };
  return { total: items.length, page: p, page_size: size, items: items.slice(start, start + size).map(strip) };
}

function detail(id) {
  const w = byId.get(id);
  if (!w) return null;
  const r = rng(id.split("").reduce((a, c) => a + c.charCodeAt(0), 0));
  const median = Math.round(w.amount / (1 + (w.score - 0.2) * 3));
  const dev = Math.round(((w.amount - median) / median) * 100);
  const parts = [];
  if (w.band !== "LOW") parts.push({ source: "statistical", label: "Statistical", weight: Number((w.score * 0.9).toFixed(2)), contribution: Number((w.score * 0.78).toFixed(2)) });
  if (w.alerts.includes("validation")) parts.push({ source: "validation", label: "Data Validation", weight: 0.22, contribution: Number((w.score * 0.22).toFixed(2)) });
  const statistical = {
    agent: "statistical",
    status: "ASSESSED",
    verdict: w.band === "LOW" ? "PASS" : "FLAGGED",
    risk: w.band === "LOW" ? 0 : Number((w.score).toFixed(2)),
    confidence: Number((0.82 + r() * 0.15).toFixed(2)),
    hard: w.band === "HIGH",
    headline: w.headline,
    version: "cost-1.2.0",
    findings:
      w.band === "LOW"
        ? []
        : [
            { code: "COST_HIGH", text: w.headline, hard: w.band === "HIGH", risk: w.score, evidence: {} },
          ],
    limitations: ["Cannot see quantities or site photos in the public export", "Peer band is district-level, not village-level"],
    evidence: {
      comparison: [
        {
          metric: "Total cost",
          unit: "Rs",
          this_work: w.amount,
          typical_low: Math.round(median * 0.6),
          typical_high: Math.round(median * 1.5),
          median,
          deviation_pct: dev,
        },
      ],
      cohort: {
        level: "district+type",
        description: `${w._name.toLowerCase()} works in ${w.district_name}`,
        n: 40 + Math.floor(r() * 300),
        p10: Math.log10(median * 0.5),
        p50: Math.log10(median),
        p90: Math.log10(median * 1.8),
        sd: 0.28,
        z: Number(((Math.log10(w.amount) - Math.log10(median)) / 0.28).toFixed(2)),
      },
      work_type_name: w._name,
    },
    duration_ms: 12,
  };
  const others = ["site_progress", "image_reuse", "duplicate_project"].map((a) => ({
    agent: a,
    status: "NOT_BUILT",
    verdict: "NOT_BUILT",
    risk: 0,
    confidence: 0,
    hard: false,
    headline: "In development",
    version: "none",
    findings: [],
    limitations: [],
    evidence: {},
    duration_ms: 0,
  }));
  const validation = w.alerts.includes("validation")
    ? [{ code: "DATE_ORDER", severity: "WARN", message: "Recorded as completed before it was recommended — please check the dates.", risk: 0.2, clause: "Guidelines 3.9 (monitoring)" }]
    : [];
  return {
    work: {
      work_id: w.work_id,
      source: w.source,
      house: pick(r, ["Lok Sabha", "Rajya Sabha"]),
      term: "17th",
      state_name: w.state_name,
      district_lgd: w.district_lgd,
      district_name: w.district_name,
      constituency: `${w.district_name} constituency`,
      mp_name: null,
      agency_name: w._agency,
      fy: "2025-26",
      work_type_code: w.work_type_code,
      category: "Infrastructure",
      description: w.description,
      amount: w.amount,
      recommended_date: w.recommended_date,
      completed_date: w._completed,
      status: w.status,
    },
    assessment: {
      score: w.score,
      band: w.band,
      limited: w.limited,
      priority: w.priority,
      parts: { parts, hard_trigger: w.band === "HIGH" ? "statistical" : null },
      validation,
      agents: [...others.slice(0, 3), statistical],
      assessed_at: new Date().toISOString(),
    },
  };
}

const server = createServer((req, res) => {
  const u = new URL(req.url, "http://localhost");
  const p = u.pathname.replace(/^\/api\/v1/, "");
  const params = Object.fromEntries(u.searchParams.entries());
  const send = (body, code = 200) => {
    res.writeHead(code, { "content-type": "application/json", "access-control-allow-origin": "*" });
    res.end(JSON.stringify(body));
  };

  if (p === "/health") return send({ ok: true, service: "mock" });
  if (p === "/me") return send({ user_id: "sample-ministry-user", role: "MINISTRY", district_lgd: null, name: "Demo Officer" });
  if (p === "/dashboard/summary") return send(summary());
  if (p === "/dashboard/districts") return send(districts());
  if (p === "/dashboard/offices") return send(offices());
  if (p === "/queue") return send(page(REVIEW, params));
  if (p === "/works") return send(page(ALL, params));
  if (p.startsWith("/works/")) {
    const id = decodeURIComponent(p.slice("/works/".length));
    const d = detail(id);
    return d ? send(d) : send({ detail: "no such work in your area" }, 404);
  }
  return send({ detail: "not found" }, 404);
});

server.listen(PORT, "0.0.0.0", () => console.log(`[mock-engine] SAMPLE data on http://0.0.0.0:${PORT}/api/v1`));
