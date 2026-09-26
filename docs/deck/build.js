// DRISHTI — SIH26102 idea deck, v2 (12 agents), rebuilt in the team's own template.
//
// Every position, size, colour and font below was measured from the team's deck
// (Downloads/DRISHTI_SIH26102_Final.pptx.pdf, 1440 x 810 pt = 20 x 11.25 in) with
// PyMuPDF, so these slides drop straight into that deck. Coordinates are written in
// points exactly as measured; P() converts to the inches pptxgenjs expects.
//
// Run:  node build.js            ->  DRISHTI_SIH26102_v2.pptx

const pptxgen = require("pptxgenjs");
const path = require("path");

const pres = new pptxgen();
pres.defineLayout({ name: "SIH", width: 20, height: 11.25 });
pres.layout = "SIH";
pres.author = "NeuralNexus";
pres.title = "DRISHTI — SIH26102 — NeuralNexus";

const P = (pt) => pt / 72;
const C = {
  navy: "2A4D88", dark: "1A2F57", light: "EDF0F5", border: "B1BBC8", num: "7C94B8",
  gold: "D9962B", goldText: "B87512", grey: "D9D9D8", muted: "5B6B84", white: "FFFFFF",
  black: "000000", tick: "2E7D4F", cross: "B23B3B", partial: "8A6D1F", goldTint: "FBF3E6",
  divider: "C2CCDA", sub: "B1BBC8",
};
const icon = (name, tone = "w") => path.join(__dirname, "assets", "icons", `${name}_${tone}.png`);
const asset = (f) => path.join(__dirname, "assets", f);

// ---------------------------------------------------------------- primitives
function box(s, x, y, w, h, o = {}) {
  const shape = o.r ? pres.shapes.ROUNDED_RECTANGLE : pres.shapes.RECTANGLE;
  const opts = { x: P(x), y: P(y), w: P(w), h: P(h), fill: { color: o.fill || C.white } };
  if (o.r) opts.rectRadius = P(Math.min(o.r, Math.min(w, h) / 2));
  opts.line = o.line ? { color: o.line, width: o.lineW || 1.5 } : { type: "none" };
  s.addShape(shape, opts);
}
function pill(s, x, y, w, h, fill) { box(s, x, y, w, h, { fill, r: h / 2 }); }
function circle(s, x, y, d, fill = C.navy) {
  s.addShape(pres.shapes.OVAL, { x: P(x), y: P(y), w: P(d), h: P(d), fill: { color: fill }, line: { type: "none" } });
}
function img(s, file, x, y, w, h) { s.addImage({ path: file, x: P(x), y: P(y), w: P(w), h: P(h) }); }
function iconCircle(s, name, x, y, d, { fill = C.navy, tone = "w", scale = 0.5 } = {}) {
  circle(s, x, y, d, fill);
  const i = d * scale;
  img(s, icon(name, tone), x + (d - i) / 2, y + (d - i) / 2, i, i);
}
function text(s, content, x, y, w, h, o = {}) {
  s.addText(content, {
    x: P(x), y: P(y), w: P(w), h: P(h), margin: 0, isTextBox: true,
    fontFace: o.font || "Calibri", fontSize: o.size || 16, color: o.color || C.dark,
    bold: !!o.bold, italic: !!o.italic, align: o.align || "left", valign: o.valign || "top",
    charSpacing: o.spacing, lineSpacingMultiple: o.lineMult, paraSpaceAfter: o.paraAfter,
  });
}
// A run list for one bulleted paragraph: bold label + body. The bullet takes the
// label's colour, which is how the template's own gold and navy bullets behave.
function para(label, body, { labelColor = C.dark, bodyColor = C.dark, joiner = ": ", joinColor = C.navy, bullet = true } = {}) {
  const runs = [];
  const first = { bold: true, color: labelColor };
  if (bullet) first.bullet = { characterCode: "2022", indent: 14 };
  runs.push({ text: label, options: first });
  if (joiner) runs.push({ text: joiner, options: { bold: true, color: joinColor } });
  runs.push({ text: body, options: { color: bodyColor, breakLine: true } });
  return runs;
}
function bullets(items, color = C.dark) {
  return items.map((t, i) => ({
    text: t,
    options: { color, bullet: { characterCode: "2022", indent: 14 }, breakLine: i < items.length - 1 },
  }));
}
function label(s, t, x, y, w = 900) {
  text(s, t, x, y, w, 22, { bold: true, size: 17.2, color: C.navy, spacing: 3 });
}
function arrow(s, x, y, size = 22) { img(s, icon("arrow-right", "n"), x, y, size, size); }

// ---------------------------------------------------------------- template chrome
function chrome(s, title, pageNo, { logoTitle = false } = {}) {
  s.background = { color: C.white };
  // team badge
  s.addShape(pres.shapes.OVAL, {
    x: P(36.7), y: P(22.6), w: P(169.6), h: P(73.6), fill: { color: C.white },
    line: { color: C.navy, width: 4.5 },
  });
  text(s, "NeuralNexus", 36.7, 22.6, 169.6, 73.6, { bold: true, size: 20.5, color: C.navy, align: "center", valign: "middle" });
  // title
  if (logoTitle) {
    img(s, asset("drishti_icon.png"), 586, 18, 88, 72.2);
    text(s, "DRISHTI", 677, 26, 240, 60, { font: "Cambria", bold: true, size: 42, color: C.black, valign: "middle" });
  } else {
    text(s, title, 246.6, 30, 900, 62, { font: "Cambria", bold: true, size: 42, color: C.navy, align: "center", valign: "middle" });
  }
  // SIH mark
  img(s, asset("sih_logo_wide.png"), 1212, 6, 213, 100.6);
  // footer bar
  box(s, 0, 768.2, 1440, 42, { fill: C.navy });
  text(s, "@SIH Idea submission – Template", 470, 778, 500, 22, { size: 15, color: C.white, align: "center", valign: "middle" });
  text(s, String(pageNo), 1340, 778, 53, 22, { bold: true, size: 16.5, color: C.white, align: "right", valign: "middle" });
}

// ================================================================= SLIDE 1 — TITLE
{
  const s = pres.addSlide();
  s.background = { color: C.white };
  text(s, "SMART INDIA HACKATHON 2026", 0, 40, 933, 68, { font: "Cambria", bold: true, size: 48, color: C.navy, align: "center", valign: "middle" });

  const rowsY = [128.7, 248, 355, 433, 513, 591, 670, 809.7];
  const rows = [
    ["Problem Statement ID", "SIH26102"],
    ["Problem Statement Title", "Development of an AI-powered system to detect anomalies, fraud, and inefficiencies in MPLAD Scheme implementation regd."],
    ["Organisation", "Ministry of Statistics & Programme Implementation (MoSPI)"],
    ["Theme", "Smart Automation"],
    ["PS Category", "Software"],
    ["Team ID", "121911"],
    ["Team Name", "NeuralNexus"],
  ];
  const tableRows = rows.map(([k, v]) => [
    { text: k, options: { fill: { color: C.navy }, color: C.white, bold: true, fontFace: "Montserrat", fontSize: 18.8, valign: "middle", margin: [0, 0, 0, P(8)] } },
    { text: v, options: { fill: { color: C.white }, color: C.dark, bold: true, fontFace: "Bookman Old Style", fontSize: 18.8, valign: "middle", margin: [0, P(8), 0, P(8)] } },
  ]);
  s.addTable(tableRows, {
    x: 0, y: P(128.7), colW: [P(302.5), P(630.5)],
    rowH: rowsY.slice(1).map((y, i) => P(y - rowsY[i])),
    border: { type: "solid", pt: 1, color: C.border },
  });

  box(s, 933.5, 0, 506.5, 810, { fill: C.navy });
  box(s, 992.8, 58.6, 390, 190.5, { fill: C.white, r: 11 });
  img(s, asset("sih_logo_wide.png"), 1031, 75, 312, 147.4);
  text(s, "DRISHTI", 933.5, 358, 506.5, 84, { font: "Cambria", bold: true, size: 62, color: C.white, align: "center", valign: "middle" });
  text(s, "The AI-eye on every MPLADS rupee", 933.5, 440, 506.5, 34, { bold: true, size: 28.5, color: C.sub, align: "center", valign: "middle" });
  text(s, ["Detect anomalies. Explain risks.", "Enable smarter oversight of public", "funds."].join("\n"), 933.5, 500, 506.5, 96,
    { italic: true, size: 27.5, color: C.grey, align: "center" });
  s.addNotes("Title slide — unchanged from the team's deck.");
}

// ================================================================= SLIDE 2 — PROPOSED SOLUTION
{
  const s = pres.addSlide();
  chrome(s, "", 2, { logoTitle: true });

  // banner
  box(s, 47.8, 126.7, 1344.3, 90.1, { fill: C.light, r: 11 });
  box(s, 47.8, 126.7, 255.5, 90.1, { fill: C.navy, r: 11 });
  img(s, icon("lightbulb"), 68, 154, 34, 34);
  text(s, "PROPOSED\nSOLUTION", 114, 147, 180, 46, { font: "Cambria", bold: true, size: 18, color: C.white, valign: "middle" });
  text(s, [
    { text: "DRISHTI", options: { bold: true, color: C.navy } },
    { text: " is an AI-powered risk-intelligence layer on top of " },
    { text: "eSAKSHI", options: { bold: true } },
    { text: ". " },
    { text: "12 AI agents", options: { bold: true, color: C.navy } },
    { text: " check every MPLADS work at every stage — before sanction, during construction, on money & time, and after completion — reading not just the records but the " },
    { text: "certificates, bills and geo-tagged photos", options: { bold: true } },
    { text: " already on eSAKSHI, and turn what they find into a " },
    { text: "daily inspection plan", options: { bold: true, color: C.navy } },
    { text: " for District Authorities." },
  ], 324, 134, 1052, 76, { size: 17.2, color: C.dark, valign: "middle" });

  // three columns
  const cols = [
    { x: 47.8, pillW: 287.7, fill: C.navy, icon: "bullseye", head: "DETAILED EXPLANATION", labelColor: C.dark, items: [
      ["12 specialist agents", "each checks one kind of problem CAG audits have found — cost, duplicates, delays, fake evidence."],
      ["Reads the evidence", "completion certificates, bills, Hindi utilisation certificates and geo-tagged photos."],
      ["Explainable Risk Score (0–100)", "fuses all agents + top-3 reasons in plain Hindi/English."],
      ["Inspection Planner + Field App", "picks works for mandatory inspections, routed; verdicts retrain the agents."],
    ] },
    { x: 506.2, pillW: 378.4, fill: C.navy, icon: "circle-check", head: "HOW IT ADDRESSES THE PROBLEM", labelColor: C.dark, arrowJoin: true, items: [
      ["Manual monitoring can't scale", "every work screened automatically, every day."],
      ["Money moves before checks", "pre-sanction check inside the 45-day window."],
      ["Evidence uploaded, never checked", "every photo & bill read, compared and placed on the map."],
      ["Many alerts, few officers", "risk-ranked queue + optimised visit route."],
    ] },
    { x: 964.6, pillW: 321.8, fill: C.gold, icon: "star", head: "INNOVATION & UNIQUENESS", labelColor: C.goldText, items: [
      ["Reads eSAKSHI's own evidence", "spots reused photos, wrong locations, missing plaques and bills that don't add up."],
      ["Proven, then measured", "methods India already runs at scale (PMAY-G, Amrit Sarovar); each agent is measured on real data first."],
      ["Clause-cited, human-in-the-loop", "every flag cites the guideline; flags for review, never accuses."],
      ["Learns from the field", "officer verdicts become labels, solving the “no fraud labels” problem."],
    ] },
  ];
  for (const c of cols) {
    box(s, c.x, 263.8, 427.6, 282.3, { fill: C.light, r: 11 });
    pill(s, c.x + 19.5, 242.2, c.pillW, 44.7, c.fill);
    img(s, icon(c.icon), c.x + 33, 251, 25, 25);
    text(s, c.head, c.x + 66.3, 243, c.pillW - 50, 43, { font: "Cambria", bold: true, size: 15.8, color: C.white, valign: "middle" });
    const runs = c.items.flatMap(([l, b]) => para(l, b, {
      labelColor: c.labelColor, joiner: c.arrowJoin ? " → " : ": ",
      joinColor: c.labelColor === C.goldText ? C.goldText : C.navy,
    }));
    runs[runs.length - 1].options.breakLine = false;
    text(s, runs, c.x + 39, 297, 375, 244, { size: 18.2, color: C.dark });
  }

  // 12 agents across the life of a work
  label(s, "12 AI AGENTS ACROSS THE LIFE OF A WORK  —  EVERY PS REQUIREMENT COVERED", 48.6, 566, 1300);
  const stages = [
    { head: "BEFORE SANCTION", icon: "file-signature", agents: [
      ["Eligibility", "works the rules don't allow"],
      ["Duplicate & Split", "funded twice, or split up"],
      ["Cost", "cost overruns & padded estimates"],
    ] },
    { head: "DURING CONSTRUCTION", icon: "helmet-safety", agents: [
      ["Site Progress", "claim vs photo, plaque check"],
      ["Photo Forensics", "reused or edited photos"],
      ["Geo-Location", "photo taken elsewhere"],
      ["Document", "bills that don't add up"],
      ["Satellite", "ghost ponds & long roads"],
    ] },
    { head: "MONEY & TIME", icon: "chart-line", agents: [
      ["Delay Prediction", "likely to miss 12 months"],
      ["Fund Flow", "idle funds, year-end rush"],
      ["Contractor Network", "a few firms win all"],
    ] },
    { head: "AFTER COMPLETION", icon: "people-roof", agents: [
      ["Citizen Verification", "asset exists & is used"],
    ] },
  ];
  const sx = 47.8, sw = (1344.4 - 3 * 20) / 4, sy = 596, sh = 160;
  stages.forEach((st, i) => {
    const x = sx + i * (sw + 20);
    box(s, x, sy, sw, sh, { fill: C.white, r: 11, line: C.border, lineW: 1.5 });
    iconCircle(s, st.icon, x + 12, sy + 11, 36);
    text(s, st.head, x + 56, sy + 11, sw - 66, 36, { bold: true, size: 16.5, color: C.navy, valign: "middle", spacing: 1 });
    const lines = st.agents.map(([n, d], k) => [
      { text: n, options: { bold: true, color: C.navy } },
      { text: " — " + d, options: { color: C.dark, breakLine: k < st.agents.length - 1 } },
    ]).flat();
    text(s, lines, x + 14, sy + 55, sw - 24, st.agents.length * 18.5 + 4, { size: 14.5 });
    if (i === 3) {
      s.addShape(pres.shapes.LINE, { x: P(x + 14), y: P(sy + 86), w: P(sw - 28), h: 0, line: { color: C.border, width: 1 } });
      text(s, [
        { text: "Then, for every work:", options: { color: C.muted, breakLine: true } },
        { text: "Risk Fusion · Inspection Planner · Ask DRISHTI", options: { bold: true, color: C.navy } },
      ], x + 14, sy + 94, sw - 24, 58, { size: 14.5 });
    }
  });
  s.addNotes([
    "Twelve agents in four stages of a work's life. Each maps to a problem the PS names or a CAG audit found:",
    "cost overruns (Cost, Document), duplicate works (Duplicate & Split), delayed projects (Delay Prediction),",
    "misuse of funds (Photo Forensics, Geo-Location, Document, Fund Flow, Contractor Network), non-compliance",
    "(Eligibility), early warning (Delay Prediction, pre-sanction checks). Satellite runs only for big works",
    "(ponds, long roads) and only after it passes a go/no-go test on real works.",
    "45-day window: the team's reading of the MPLADS Guidelines 2023 — confirm against the 2023 text",
    "(the 2016 edition says sanction within 75 days, rejection within 45).",
  ].join(" "));
}

// ================================================================= SLIDE 3 — TECHNICAL APPROACH
{
  const s = pres.addSlide();
  chrome(s, "TECHNICAL APPROACH", 3);
  label(s, "SYSTEM ARCHITECTURE & WORKFLOW", 48.6, 122);

  const steps = [
    { n: "01", icon: "database", head: "Data Ingestion", items: ["2.1 lakh eSAKSHI works", "Certificates, bills & photos", "Field app & citizen uploads"] },
    { n: "02", icon: "filter", head: "Data Validation", items: ["Date & amount checks", "Read documents & photo stamps", "Mask names & phone numbers"] },
    { n: "03", icon: "brain", head: "12 AI Agents", hi: true, items: ["Before sanction (3)", "During construction (5)", "Money & time (3), after (1)"] },
    { n: "04", icon: "shield-halved", head: "Risk Fusion", items: ["Weighted fusion → 0–100", "Top-3 reasons + evidence", "Low / Med / High / Critical"] },
    { n: "05", icon: "desktop", head: "Alerts & Dashboards", items: ["4 role-based views", "Inspection plan + field app", "SMS / email / PDF brief"] },
  ];
  const stepX = [47.8, 324.0, 600.1, 876.2, 1152.3], stepW = 240.2, stepY = 150, stepH = 166;
  steps.forEach((st, i) => {
    const x = stepX[i];
    box(s, x, stepY, stepW, stepH, { fill: st.hi ? C.navy : C.light, r: 11 });
    if (st.hi) iconCircle(s, st.icon, x + 16, stepY + 14, 48, { fill: C.white, tone: "n" });
    else iconCircle(s, st.icon, x + 16, stepY + 14, 48);
    text(s, st.n, x + stepW - 70, stepY + 14, 54, 34, { font: "Cambria", bold: true, size: 26, color: st.hi ? C.border : C.num, align: "right" });
    text(s, st.head, x + 16, stepY + 70, stepW - 30, 24, { bold: true, size: 18, color: st.hi ? C.white : C.navy });
    text(s, bullets(st.items, st.hi ? C.white : C.dark), x + 16, stepY + 97, stepW - 26, 62, { size: 14.5 });
    if (i < 4) arrow(s, x + stepW + 7, stepY + stepH / 2 - 11, 22);
  });

  label(s, "12 AI AGENTS  —  HOW EACH ONE WORKS", 48.6, 330);
  label(s, "TECHNOLOGY STACK", 972, 330, 420);
  const agents = [
    ["scale-balanced", "Eligibility", "guideline rules + AI that reads the clause", "works the guidelines don't allow"],
    ["clone", "Duplicate & Split", "DIGIPIN map grid + Hindi & English text match", "same work funded twice, or split up"],
    ["indian-rupee-sign", "Cost", "cost range of similar works in the district", "estimates far above similar works"],
    ["camera", "Site Progress", "vision AI checks each claim against photos", "“roof done” with no roof; no plaque"],
    ["fingerprint", "Photo Forensics", "image fingerprints across all works", "same photo or certificate reused"],
    ["location-dot", "Geo-Location", "photo GPS & stamp vs district map", "photos taken elsewhere, or too early"],
    ["file-invoice", "Document", "AI reads certificates, bills & UCs", "amounts & dates that don't add up"],
    ["satellite", "Satellite", "Sentinel-2 before/after, big works only", "ponds & long roads never built"],
    ["hourglass-half", "Delay Prediction", "model trained on real completion history", "works likely to miss 12 months"],
    ["money-bill-trend-up", "Fund Flow", "MP & district money funnel over time", "idle funds, year-end rush"],
    ["diagram-project", "Contractor Network", "contractor–agency–district graph", "a few firms winning most works"],
    ["users", "Citizen Verification", "QR code at site → photo + GPS", "assets missing or not in use"],
  ];
  const gx = 47.8, gw = 896.2, cw = (gw - 3 * 12) / 4, gy = 358, rh = (756 - gy - 2 * 10) / 3;
  agents.forEach(([ic, name, how, catches], k) => {
    const x = gx + (k % 4) * (cw + 12), y = gy + Math.floor(k / 4) * (rh + 10);
    box(s, x, y, cw, rh, { fill: C.white, r: 9, line: C.border, lineW: 1.5 });
    iconCircle(s, ic, x + 10, y + 10, 36);
    text(s, name, x + 54, y + 10, cw - 62, 36, { bold: true, size: 15.5, color: C.navy, valign: "middle" });
    text(s, [
      { text: "How: ", options: { bold: true, color: C.navy } },
      { text: how, options: { color: C.dark, breakLine: true } },
      { text: "Catches: ", options: { bold: true, color: C.navy } },
      { text: catches, options: { color: C.dark } },
    ], x + 12, y + 52, cw - 22, rh - 58, { size: 13.5, paraAfter: 3 });
  });

  const stack = [
    ["Frontend", "Next.js (React), Tailwind CSS, MapLibre maps"],
    ["Backend / APIs", "Python FastAPI, role-based access (JWT)"],
    ["AI / ML", "LightGBM, scikit-learn, sentence-transformers"],
    ["Vision & Documents", "Vision AI (Gemini; open-weight option), OpenCV"],
    ["Maps & Satellite", "LGD boundaries, DIGIPIN, Sentinel-2"],
    ["Data & Security", "PostgreSQL + pgvector, hash-chained audit log"],
  ];
  s.addTable(stack.map(([k, v]) => [
    { text: k, options: { fill: { color: C.navy }, color: C.white, bold: true, fontSize: 15, valign: "middle", margin: [0, P(8), 0, P(8)] } },
    { text: v, options: { fill: { color: C.light }, color: C.dark, fontSize: 14.5, valign: "middle", margin: [0, P(8), 0, P(10)] } },
  ]), {
    x: P(972), y: P(gy), colW: [P(148), P(272)], rowH: Array(6).fill(P((756 - gy) / 6)),
    fontFace: "Calibri", border: { type: "solid", pt: 1.5, color: C.white },
  });
  s.addNotes([
    "Stage order: before sanction (Eligibility, Duplicate & Split, Cost); during construction (Site Progress,",
    "Photo Forensics, Geo-Location, Document, Satellite); money & time (Delay Prediction, Fund Flow,",
    "Contractor Network); after completion (Citizen Verification). Each agent is tested on held-out real",
    "eSAKSHI data and stays switched off until it meets its accuracy target.",
  ].join(" "));
}

// ================================================================= SLIDE 4 — FEASIBILITY AND VIABILITY
{
  const s = pres.addSlide();
  chrome(s, "FEASIBILITY AND VIABILITY", 4);
  label(s, "FEASIBILITY ANALYSIS", 48.6, 124);
  const feas = [
    [48, 161, "gears", "Technical Feasibility", "Proven Methods", "Every agent reuses a method India already runs at scale: PMAY-G geo-tagged photos, Amrit Sarovar ponds."],
    [372, 161, "database", "Data Feasibility", "Real eSAKSHI Data", "2,09,993 works already loaded; 2 in 3 completed works carry certificates or photos to check."],
    [48, 347, "users-gear", "Operational Feasibility", "Workflow Fit", "Read-only layer on eSAKSHI; fits the MP → District → Agency flow, no new data entry."],
    [372, 347, "coins", "Economic Feasibility", "Low Cost", "Open-source tools; pay-per-use AI at well under ₹1 a document; no licence fees."],
  ];
  for (const [x, y, ic, head, sub, body] of feas) {
    box(s, x, y, 304, 166, { fill: C.light, r: 11 });
    iconCircle(s, ic, x + 16, y + 16, 51);
    text(s, head, x + 78, y + 16, 216, 51, { bold: true, size: 18, color: C.navy, valign: "middle" });
    text(s, [
      { text: sub, options: { bold: true, breakLine: true } },
      { text: body },
    ], x + 22, y + 76, 266, 84, { size: 16, color: C.dark });
  }

  label(s, "CHALLENGES & RISKS", 718, 124, 320);
  label(s, "STRATEGIES TO OVERCOME", 1085, 124, 320);
  const risks = [
    ["No Confirmed Fraud Labels", "Few proven cases to learn from.", "Real Outcomes as Labels", "Completion history & planted tests; officer verdicts retrain."],
    ["False Alerts", "Terrain, rates or bulk orders can look like overpricing.", "Independent Checks Must Agree", "High risk needs separate agents to agree."],
    ["Handwritten & Hinglish Records", "Hindi certificates and messy text are hard to read.", "Confidence Gate", "Unclear readings become “can't tell”, never an alert."],
    ["Sensitive Data", "Named officials, contractors and personal details.", "Fair & Secure by Design", "“Needs verification”, never “fraud”; role-based access."],
  ];
  const ry = [161, 250, 338, 427];
  risks.forEach(([ct, cb, st, sb], i) => {
    const y = ry[i];
    box(s, 718, y, 309, 77, { fill: C.grey, r: 9 });
    img(s, icon("triangle-exclamation", "g"), 731, y + 24, 28, 28);
    text(s, [{ text: ct, options: { bold: true, breakLine: true } }, { text: cb }], 768, y + 8, 252, 64, { size: 15.3, color: C.dark, valign: "middle" });
    arrow(s, 1043, y + 27, 23);
    box(s, 1085, y, 307, 77, { fill: C.white, r: 9, line: C.num, lineW: 1.5 });
    img(s, icon("circle-check", "n"), 1098, y + 24, 28, 28);
    text(s, [{ text: st, options: { bold: true, breakLine: true } }, { text: sb }], 1135, y + 8, 250, 64, { size: 15.3, color: C.dark, valign: "middle" });
  });

  label(s, "VIABILITY", 48.6, 545);
  const via = [
    ["Human Control", "Human-in-the-Loop", "AI flags risks; officials verify and decide."],
    ["Existing Workflow", "Workflow Compatibility", "Works alongside existing eSAKSHI workflows."],
    ["Priority-Based Action", "Risk-Based Verification", "Picks higher-risk works for mandatory inspections."],
    ["Future Expansion", "Modular and Expandable", "Agents added one by one; fits PMAY-G & MGNREGA."],
  ];
  const vx = [48, 285, 523, 761];
  via.forEach(([p, t, b], i) => {
    const x = vx[i];
    box(s, x, 582, 212, 164, { fill: C.light, r: 11 });
    pill(s, x + 13, 595, 186, 41, i === 3 ? C.gold : C.navy);
    text(s, p, x + 13, 595, 186, 41, { bold: true, size: 16.5, color: C.white, align: "center", valign: "middle" });
    text(s, [{ text: t, options: { bold: true, breakLine: true } }, { text: b }], x + 14, 646, 188, 94, { size: 16.5, color: C.dark });
    if (i < 3) arrow(s, x + 214, 604, 20);
  });
  box(s, 998, 582, 394, 164, { fill: C.navy, r: 11 });
  iconCircle(s, "flask-vial", 1016, 598, 44, { fill: C.white, tone: "n" });
  text(s, "PROOF BEFORE LAUNCH", 1072, 598, 310, 44, { font: "Cambria", bold: true, size: 18, color: C.white, valign: "middle" });
  text(s, "Every agent is tested on real eSAKSHI data and must meet its accuracy target before it goes live. If it fails, it stays switched off.",
    1016, 652, 362, 88, { size: 16, color: C.white });
  s.addNotes([
    "Precedents: PMAY-G releases instalments only on geo-tagged stage photos (3.84 crore house sites geo-tagged by",
    "July 2025); Mission Amrit Sarovar monitors 68,000+ ponds with remote sensing (BISAG-N). Data: 2,09,993 works",
    "from the public eSAKSHI export are loaded in the prototype; about two-thirds of completed works carry an",
    "attachment on eSAKSHI (completion certificates, bills, utilisation certificates, geo-stamped photos).",
    "AI cost: an estimate from list prices for a low-cost vision model, not a measurement.",
  ].join(" "));
}

// ================================================================= SLIDE 5 — IMPACT AND BENEFITS
{
  const s = pres.addSlide();
  chrome(s, "IMPACT AND BENEFITS", 5);
  label(s, "IMPACT ON TARGET STAKEHOLDERS", 48.6, 124);
  const who = [
    [48, "landmark", "Ministry (MoSPI)", ["National risk heat-map by state & district", "Spot systemic issues & guideline gaps", "Evidence-backed reports for Parliament", "Agent accuracy tracked openly"]],
    [390, "sitemap", "State Nodal Authorities", ["District & agency league tables", "Escalate stalled or high-risk works", "Track follow-up on every alert", "Spot contractor concentration"]],
    [733, "map-location-dot", "District Authorities", ["Daily ranked alert queue with evidence", "Inspection plan with optimised route", "Pre-sanction check in the 45-day window", "One-click PDF evidence brief"]],
    [1075, "user-tie", "Members of Parliament", ["Live status of recommended works", "Early warning on delays & idle funds", "Citizens confirm completed assets", "Transparent record builds public trust"]],
  ];
  for (const [x, ic, head, items] of who) {
    box(s, x, 161, 317, 266, { fill: C.light, r: 11 });
    iconCircle(s, ic, x + 19, 181, 64);
    text(s, head, x + 96, 181, 212, 64, { bold: true, size: 19.7, color: C.navy, valign: "middle" });
    text(s, bullets(items), x + 30, 262, 276, 160, { size: 17.5, paraAfter: 2 });
  }

  label(s, "BENEFITS", 48.6, 457);
  const ben = [
    [48, "handshake", "SOCIAL", ["Faster delivery of community assets", "Public trust through transparency", "Citizens get assets that truly exist", "Fairer spread of works across areas"]],
    [348, "coins", "ECONOMIC", ["Flag risks before funds move", "Targeted visits save officer time", "Catch reused photos & padded bills", "Fewer cost overruns and rework"]],
    [649, "leaf", "ENVIRONMENTAL", ["Paperless, digital monitoring", "Fewer wasted site trips and fuel", "Durable assets built right first time", "Assets tracked through their life cycle"]],
  ];
  for (const [x, ic, head, items] of ben) {
    box(s, x, 509, 275, 239, { fill: C.white, r: 11, line: C.border, lineW: 1.5 });
    pill(s, x + 19, 487, 237, 45, C.navy);
    img(s, icon(ic), x + 33, 496, 25, 25);
    text(s, head, x + 70, 487, 180, 45, { bold: true, size: 16.7, color: C.white, valign: "middle" });
    text(s, bullets(items), x + 30, 545, 236, 196, { size: 17 });
  }

  label(s, "EXPECTED OUTCOMES", 961, 457, 430);
  const out = [
    [487, true, "100%", "of works screened daily; 2,09,993 real works already done"],
    [580, false, "0.13%", "flagged for review: a queue District Authorities can clear"],
    [673, false, "2 in 3", "completed works have certificates or photos DRISHTI can verify"],
  ];
  for (const [y, dark, big, small] of out) {
    box(s, 960, y, 432, 75, { fill: dark ? C.navy : C.light, r: 9 });
    text(s, big, 977, y, 120, 75, { font: "Cambria", bold: true, size: 31.5, color: dark ? C.white : C.navy, valign: "middle" });
    if (!dark) s.addShape(pres.shapes.LINE, { x: P(1100), y: P(y + 11), w: 0, h: P(53), line: { color: C.divider, width: 1.5 } });
    text(s, small, 1116, y + 6, 266, 63, { size: 16.5, color: dark ? C.grey : C.dark, valign: "middle" });
  }
  s.addNotes([
    "Measured on the real eSAKSHI export in the live prototype (2026-09-26): 2,09,993 works screened; 276 (0.13%)",
    "flagged Medium for review (253 on price), none High yet. Date errors from bulk entry when eSAKSHI opened are",
    "listed once per office (22 offices) instead of filling the queue. 'Two in three': about two-thirds of",
    "completed works carry an attachment on eSAKSHI (65.9% of completed 18th Lok Sabha works in the export).",
  ].join(" "));
}

// ================================================================= SLIDE 6 — RESEARCH AND REFERENCES
{
  const s = pres.addSlide();
  chrome(s, "RESEARCH AND REFERENCES", 6);
  label(s, "WHAT DRISHTI CHECKS — AND HOW", 48.6, 124);
  const rowsCap = [
    ["AI anomaly detection in spending", "Cost range of similar works in the same district", "Before sanction"],
    ["Duplicate & split works (Hindi + English)", "Same-site and bulk-order patterns, meaning match", "Before sanction"],
    ["Guideline compliance with para cited", "Rules + the clause quoted on every flag", "Before sanction"],
    ["Reads certificates & bills (Hindi/English)", "Sanction date, payments and contractor read", "During work"],
    ["Spots reused or edited photos", "Image fingerprints + feature matching", "During work"],
    ["Checks where & when photos were taken", "GPS stamp read; district, PIN and date checked", "During work"],
    ["Delay & stuck-work early warning", "Stuck works + each office's track record", "Money & time"],
    ["Citizen confirmation & field learning", "QR at site; officer verdicts retrain agents", "After completion"],
    ["Explainable 0–100 risk score", "All agents fused + top-3 reasons", "Every work"],
    ["Risk-based inspection route plan", "Picks the mandatory 10% of visits, routed", "Every work"],
  ];
  const head = ["Capability", "How DRISHTI does it", "Stage"].map((t, i) => ({
    text: t, options: { fill: { color: i === 1 ? C.gold : C.navy }, color: C.white, bold: true, fontSize: 15.5, align: "left", valign: "middle", margin: [0, P(6), 0, P(8)] },
  }));
  const body = rowsCap.map((r) => [
    { text: r[0], options: { fill: { color: C.light }, bold: true, color: C.dark, fontSize: 14.5, valign: "middle", margin: [0, P(6), 0, P(6)] } },
    { text: r[1], options: { fill: { color: C.goldTint }, color: C.dark, fontSize: 14.5, valign: "middle", margin: [0, P(6), 0, P(8)] } },
    { text: r[2], options: { fill: { color: C.white }, bold: true, color: C.navy, fontSize: 14, valign: "middle", margin: [0, P(6), 0, P(8)] } },
  ]);
  s.addTable([head, ...body], {
    x: P(49), y: P(156), colW: [P(300), P(360), P(151)],
    rowH: [P(48), ...Array(10).fill(P(33))], fontFace: "Calibri",
    border: { type: "solid", pt: 1, color: C.border },
  });

  label(s, "KEY RESEARCH INSIGHTS", 48.6, 553);
  const ins = [
    ["₹5 Cr", "per MP per year, non-lapsable funds (MoSPI)"],
    ["~₹4,000 Cr", "annual outlay, run on eSAKSHI since Apr 2023 (PIB)"],
    ["4,918", "works without the mandatory MPLADS plaque (CAG audit, 31 districts)"],
    ["₹280 Cr", "in 12,006 works left incomplete (CAG audit, 71 districts)"],
  ];
  const iw = (812 - 3 * 20) / 4;
  ins.forEach(([big, small], i) => {
    const x = 48 + i * (iw + 20);
    box(s, x, 585, iw, 163, { fill: C.light, r: 11 });
    text(s, big, x + 16, 598, iw - 28, 44, { font: "Cambria", bold: true, size: 28, color: C.navy, valign: "middle" });
    text(s, small, x + 16, 650, iw - 28, 92, { size: 16, color: C.dark });
  });

  label(s, "REFERENCES", 886, 124, 500);
  const refs = [
    [161, "landmark", "Government & Policy Sources", [
      ["MPLADS Guidelines 2016 & 2023", " — mplads.gov.in"],
      ["eSAKSHI portal & revised fund flow", " — MoSPI / PIB"],
      ["CAG Performance Audit of MPLADS", " — Report 31 of 2010-11"],
      ["PMAY-G AwaasApp · Mission Amrit Sarovar", " — MoRD / BISAG-N"],
    ]],
    [361, "book", "Research Papers", [
      ["Perceptual image hashing", " — Zauner, 2010"],
      ["ORB feature matching", " — Rublee et al., ICCV 2011"],
      ["Multilingual sentence embeddings", " — Reimers & Gurevych, EMNLP 2020"],
      ["LightGBM", " — Ke et al., NeurIPS 2017"],
    ]],
    [561, "database", "Datasets & Tools", [
      ["eSAKSHI public works data", " + uploaded certificates & photos"],
      ["LGD boundaries · India Post DIGIPIN", " — official maps"],
      ["Copernicus Sentinel-2", " — free satellite imagery"],
      ["Gemini vision · OpenCV · scikit-learn", ""],
    ]],
  ];
  for (const [y, ic, head2, items] of refs) {
    box(s, 885, y, 507, 187, { fill: C.white, r: 11, line: C.border, lineW: 1.5 });
    iconCircle(s, ic, 901, y + 16, 47);
    text(s, head2, 959, y + 16, 420, 47, { bold: true, size: 18, color: C.navy, valign: "middle" });
    const runs = items.flatMap(([b, m], k) => [
      { text: b, options: { bold: true, color: C.dark } },
      { text: m, options: { color: C.muted, breakLine: k < items.length - 1 } },
    ]);
    text(s, runs, 916, y + 74, 462, 108, { size: 15.3, paraAfter: 2 });
  }
  s.addNotes([
    "Citizen ratings on eSAKSHI are almost all empty (21,789 of 21,793 on completed 18th LS works are zero), so",
    "citizen confirmation is a new channel. CAG figures are totals from the annexures",
    "of CAG Report No. 31 of 2010-11 (TOTAL rows, sampled districts): Annex 7.2 plaques not erected - 4,918 works in 31",
    "District Authorities (Rs 100.20 crore); Annex 4.7 incomplete works - 12,006 works in 71 DAs, Rs 279.99 crore. The earlier '₹9.16 Cr on 518 works' figure was replaced because it could not be traced",
    "to that report; restore it if the team has the source. Outlay ~Rs 4,000 crore: PIB 2027330 (June 2024).",
  ].join(" "));
}

pres.writeFile({ fileName: path.join(__dirname, "DRISHTI_SIH26102_v2.pptx") }).then((f) => console.log("wrote", f));
