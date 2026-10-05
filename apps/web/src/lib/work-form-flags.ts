import type { Check, Trace, TraceFinding } from "@/lib/explain";
import { AGENT_ORDER, agentMeta, inr } from "@/lib/format";

/**
 * T134, the work intelligence form's demo: what each agent flagged, in one short line, and which of
 * the form's fields it is about, so the framed form can be marked in the agent's colour. The lines
 * come from the finding's facts (the engine's numbers), never invented here.
 */

/** The agents' colours inside the framed form, which cannot read the site's CSS variables. */
export const AGENT_HEX: Record<string, string> = {
  cost_estimate: "#ea6a2a",
  dup_split: "#c026d3",
  time_rules: "#2563eb",
  site_progress: "#0d9488",
};

export type FieldMark = { name: string; label: string };
export type Flag = { agent: string; code: string; why: string; fields: FieldMark[] };
export type AgentState = "flagged" | "clear" | "not_checked" | "later";
export type AgentLine = { id: string; state: AgentState; flags: Flag[]; note: string | null };

type Facts = Record<string, unknown>;
type Form = Record<string, unknown>;
type Row = { n: number; desc: string; qty: number; rate: number };

const num = (v: unknown) => (typeof v === "number" ? v : Number(v));
const n = (v: unknown) => Math.round(num(v)).toLocaleString("en-IN");
const rs = (v: unknown) => `₹${n(v)}`;
const day = (iso: unknown) =>
  new Date(`${String(iso).slice(0, 10)}T00:00:00`).toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" });
const cap = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);
const list = (v: unknown) => (Array.isArray(v) ? v : []) as Record<string, unknown>[];

function unitWord(unit: unknown, q: number): string {
  const u = String(unit ?? "");
  if (u === "m3") return "m³";
  if (u === "m2") return "m²";
  if (u === "nos") return "";
  return q === 1 ? u : `${u}s`;
}

function rows(form: Form): Row[] {
  const out: Row[] = [];
  for (const k of Object.keys(form)) {
    const m = /^boq_desc_(\d+)$/.exec(k);
    if (m)
      out.push({ n: Number(m[1]), desc: String(form[k] ?? "").trim(), qty: num(form[`boq_qty_${m[1]}`]), rate: num(form[`boq_rate_${m[1]}`]) });
  }
  return out.sort((a, b) => a.n - b.n);
}

/** The form's row of an estimate line the engine names: the same quantity and rate (the engine
 *  names lines by its catalogue, not by the agency's words), else the first row naming its material. */
function rowOf(boq: Row[], t: Facts): Row | undefined {
  const same = (a: number, b: unknown) => Math.abs(a - num(b)) < 0.005;
  const word = String(t.material ?? "").split("_")[0];
  return (
    boq.find((r) => same(r.qty, t.quantity) && (t.rate == null || same(r.rate, t.rate))) ??
    (word ? boq.find((r) => r.desc.toLowerCase().includes(word)) : undefined)
  );
}

/** The site's pin: a linear work's start, else its point. */
function pinField(form: Form): string {
  return String(form.start_lat ?? "").trim() ? "start_lat" : "latitude";
}

function firstSentence(text: string): string {
  const s = text.split(/(?<=\.)\s/)[0] ?? text;
  return s.length > 140 ? `${s.slice(0, 137)}…` : s;
}

/** One finding: why, in a line, and the fields it is about. */
export function flagOf(agent: string, f: TraceFinding, form: Form): Flag {
  const x: Facts = f.facts ?? {};
  const boq = rows(form);
  let why = firstSentence(f.text);
  const fields: FieldMark[] = [];
  switch (f.code) {
    case "MATERIAL_QUANTITY_ABOVE_SIZE": {
      const word = String(x.material ?? "").split("_")[0];
      const q = num(x.quantity);
      why = `${cap(word)}: ${n(q)} ${unitWord(x.unit, q)} in the estimate, but the work's size needs only ${n(x.needed)}.`;
      const row = rowOf(boq, { material: x.material, quantity: x.quantity });
      if (row) fields.push({ name: `boq_qty_${row.n}`, label: `needs ${n(x.needed)}` });
      break;
    }
    case "ESTIMATE_ABOVE_FAIR_PRICE": {
      why = `Estimate ${inr(num(x.grand_total))}; a fair price for this work here is ${inr(num(x.fair_total))} (${Math.round(num(x.gap_share) * 100)}% more).`;
      {
        // where the gap is: the lines that make it, then money no line explains
        const parts = list(x.top).map((t) => `${String(t.label ?? t.material).toLowerCase()} +${inr(num(t.extra))}`);
        const loose = (x.unexplained ?? {}) as Record<string, number>;
        const words: Record<string, string> = {
          unread_items: "items no price list covers",
          lump_sums: "lump sums",
          other_charges: "'other' charges",
          contingency: "contingency",
        };
        for (const [k, v] of Object.entries(loose)) if (v > 0) parts.push(`${words[k] ?? k} +${inr(v)}`);
        if (parts.length) why += ` Most of the gap: ${parts.join(", ")}.`;
      }
      fields.push({ name: "technical_estimate", label: `fair price ${inr(num(x.fair_total))}` });
      for (const t of list(x.top)) {
        const row = rowOf(boq, t);
        if (!row) continue;
        if (num(t.quantity) > num(t.fair_quantity) * 1.001) fields.push({ name: `boq_qty_${row.n}`, label: `fair ${n(t.fair_quantity)}` });
        if (t.fair_rate != null && num(t.rate) > num(t.fair_rate) * 1.001)
          fields.push({ name: `boq_rate_${row.n}`, label: `usual ${rs(t.fair_rate)}` });
      }
      const loose = (x.unexplained ?? {}) as Record<string, number>;
      if (loose.lump_sums) fields.push({ name: "lumpsum_components", label: `${inr(loose.lump_sums)} not itemised` });
      if (loose.other_charges) fields.push({ name: "other_charges", label: `${inr(loose.other_charges)} not explained` });
      break;
    }
    case "SIZE_NOT_AS_DESCRIBED": {
      why = `The form says ${x.form_size}, but its own scope says ${x.scope_size}: at that size the ${String(x.material ?? "").split("_")[0]} is ${num(x.ratio).toFixed(1)}× what is needed.`;
      const key = String(x.form_size ?? "").includes("wide") ? "road_width_m" : "road_length_m";
      fields.push({ name: key, label: `scope says ${x.scope_size}` });
      break;
    }
    case "ESTIMATE_NOT_ITEMISED":
      why = `${Math.round(num(x.share) * 100)}% of the estimate (${inr(num(x.amount))}) is lump sums or items no standard name fits, so its price cannot be checked.`;
      fields.push({ name: "technical_estimate", label: "not itemised" });
      if (num(form.lumpsum_components) > 0) fields.push({ name: "lumpsum_components", label: "itemise this" });
      break;
    case "ESTIMATE_ABOVE_STANDARD_AND_MP": {
      const times = Math.round((1 + num(x.mp_gap)) * 10) / 10;
      why = `${rs(x.price_per_unit)} per ${x.unit ?? "unit"}; it usually costs ${rs(x.median)}. The estimate is ${times}× what the MP recommended.`;
      const row = boq.find((r) => Math.abs(r.rate - num(x.price_per_unit)) < 0.5) ?? boq[0];
      if (row) fields.push({ name: `boq_rate_${row.n}`, label: `usually ${rs(x.median)}` });
      fields.push({ name: "mp_recommended_amount", label: `estimate is ${times}× this` });
      break;
    }
    case "SANCTIONED_WORK_AT_THIS_SITE":
      why = x.overlap
        ? `Its alignment runs over ${Math.round(num(x.overlap) * 100)}% of work ${x.other}, already sanctioned${x.other_completed ? ` and completed on ${day(x.other_completed)}` : ""}.`
        : `The map pin is ${n(x.metres)} m from work ${x.other}, already sanctioned${x.other_completed ? ` and completed on ${day(x.other_completed)}` : ""}.`;
      why += x.declared ? " The form calls it a continuation, but it lies on that work's own ground." : " The form does not mention it.";
      fields.push({ name: pinField(form), label: `${n(x.metres)} m from ${x.other}` });
      fields.push({ name: "known_nearby_work_ids", label: `${x.other} not named` });
      break;
    case "REBUILT_SOON_AFTER_COMPLETION":
      why = x.same_ground
        ? `Called a continuation or repair of work ${x.other}, but it covers the same ground with the same size, finished only ${x.months_after_completion} months earlier.`
        : `Rebuilds work ${x.other}, which was finished only ${x.months_after_completion} months earlier.`;
      fields.push({ name: "prior_work_id", label: `finished ${x.months_after_completion} months before` });
      break;
    case "SPLIT_JUST_UNDER_LIMIT":
      why = `${x.size} parts of one job filed within ${x.days} days, each just under ${inr(num(x.limit))}: ${inr(num(x.total))} together.`;
      fields.push({ name: "mp_recommended_amount", label: `just under ${inr(num(x.limit))}` });
      fields.push({ name: "work_title", label: `1 of ${x.size} parts` });
      break;
    case "FINISHED_TOO_FAST":
      why = `Recorded complete ${x.value} days after sanction; a work this size needs at least ${x.limit} days.${num(x.videos) === 0 ? " No site video shows it." : ""}`;
      fields.push({ name: "estimated_duration_days", label: `done in ${x.value} days?` });
      break;
    case "PAST_PROMISED_TIME":
      why = `${x.value} days past its due date (${day(x.late)}, with the grace period)${x.stalled ? ", and the site videos show no work" : ""}.`;
      fields.push({ name: "expected_completion_date", label: `${x.value} days late` });
      break;
    case "FOOTAGE_USED_BEFORE": {
      const r = list(x.reused_from)[0] ?? {};
      why = `Video ${x.visit} reuses ${r.frames} frames from the video of work ${r.work_id}.`;
      fields.push({ name: "baseline_video_date", label: "first video: reused footage" });
      break;
    }
    case "SAME_PLACE_AS_ANOTHER_WORK": {
      const s = list(x.same_place_as)[0] ?? {};
      why = `Video ${x.visit} shows the same place as the site of work ${s.work_id}.`;
      fields.push({ name: "fixed_viewpoint_count", label: `same place as ${s.work_id}` });
      break;
    }
    case "CLAIM_NOT_SHOWN": {
      const claims = (Array.isArray(x.claims) ? x.claims : []).filter(Boolean).map(String);
      const visits = (Array.isArray(x.visits) ? x.visits : []).map(String);
      why = `${claims[0] ? `"${claims[0]}" claimed` : "Claimed work"} in videos ${visits.join(" and ")}, but the videos do not show it.`;
      fields.push({ name: "capture_frequency", label: "claim not shown, twice" });
      break;
    }
    case "NO_SITE_VIDEO":
      why = `No site video ${n(x.days)} days past its planned start${num(x.filmed) > 0 ? ` (${n(x.filmed)} filmed, none accepted)` : ""}.`;
      fields.push({ name: "baseline_video_date", label: "no video yet" });
      break;
    case "SITE_VIDEOS_UNUSABLE": {
      const visits = (Array.isArray(x.visits) ? x.visits : []).map(String);
      const whys = (Array.isArray(x.why) ? x.why : []).map(String);
      why = `${visits.length} recent site videos (${visits.join(", ")}) cannot show the work: ${[...new Set(whys)].join("; ")}. A poor video now and then is forgiven, not this many.`;
      fields.push({ name: "capture_frequency", label: "videos unusable" });
      break;
    }
    case "COMPLETE_NOT_FILMED":
      why = `Recorded complete ${n(x.days)} days ago, but no final site video shows the finished work.`;
      fields.push({ name: "completion_capture_required", label: "no final video" });
      break;
    case "SITE_NOT_AT_FORM_PIN":
      why = `Every site video is filmed about ${n(x.metres)} m from the form's map pin: the work is not where the form puts it.`;
      fields.push({ name: pinField(form), label: `videos ${n(x.metres)} m away` });
      break;
    case "NOT_FILMED_AT_THIS_SITE":
      why = x.mock_location
        ? `Video ${x.visit}: the phone faked its location, and the views do not match the site.`
        : `Video ${x.visit} was filmed ${(num(x.metres) / 1000).toFixed(1)} km from the site, and its views do not match.`;
      fields.push({ name: pinField(form), label: `video ${x.visit} filmed elsewhere` });
      break;
    case "SANCTION_OVERDUE":
    case "SANCTIONED_LATE":
      fields.push({ name: "ida_received_date", label: `${n(x.value)} days to sanction (limit ${n(x.limit)})` });
      break;
    case "NEAR_SANCTIONED_WORK":
    case "LOOKS_LIKE_SANCTIONED_WORK":
      fields.push({ name: "known_nearby_work_ids", label: "a similar work nearby" });
      break;
    case "ALREADY_BUILT_AT_START":
      fields.push({ name: "baseline_existing_condition", label: "already built in the first video" });
      break;
    case "ASSET_NOT_SHOWN":
    case "COMPLETE_NOT_SHOWN":
      fields.push({ name: "completion_evidence_definition", label: "not shown in the videos" });
      break;
    case "PLAQUE_DATED_BEFORE_RECOMMENDATION":
      fields.push({ name: "plaque_provision", label: "plaque dated before the recommendation" });
      break;
  }
  // every question points somewhere on the form: the field each agent reads first
  if (!fields.length) fields.push({ name: FALLBACK[agent] ?? "technical_estimate", label: "see why" });
  return { agent, code: f.code, why, fields };
}

const FALLBACK: Record<string, string> = {
  cost_estimate: "technical_estimate",
  dup_split: "known_nearby_work_ids",
  time_rules: "expected_completion_date",
  site_progress: "capture_frequency",
};

const LATER: Record<string, string> = {
  time_rules: "Starts at sanction.",
  site_progress: "Starts with the first site video, after sanction.",
};
const NOT_CHECKED: Record<string, string> = {
  cost_estimate: "No prices to compare with for this date yet.",
  dup_split: "Nothing on record to compare with.",
  time_rules: "Not enough dates to check.",
  site_progress: "No readable site video yet.",
};

/** The four agents, in order: flagged (with why), clear, not checked, or not yet (after sanction). */
export function agentLines(trace: Trace, form: Form): AgentLine[] {
  return AGENT_ORDER.map((id) => {
    const c: Check | undefined = trace.checks.find((x) => x.id === id);
    if (!c) return { id, state: "not_checked", flags: [], note: "Not run." };
    const flags = c.findings.filter((f) => f.risk > 0).map((f) => flagOf(id, f, form));
    if (flags.length) return { id, state: "flagged", flags, note: null };
    if (c.status === "ASSESSED") return { id, state: "clear", flags, note: null };
    if (c.status === "NOT_APPLICABLE") return { id, state: "later", flags, note: LATER[id] ?? null };
    return { id, state: "not_checked", flags, note: NOT_CHECKED[id] ?? null };
  });
}

// ---- marking the framed form --------------------------------------------------------------------

const STYLE_ID = "nn-flag-style";
const CSS = `
.nn-flag{outline:3px solid var(--nn-c);outline-offset:2px;border-radius:6px;background:color-mix(in srgb,var(--nn-c) 8%,transparent);transition:box-shadow .3s}
.nn-flag.nn-pulse{box-shadow:0 0 0 7px color-mix(in srgb,var(--nn-c) 35%,transparent)}
.nn-tag{display:inline-block;margin-top:5px;padding:2px 8px;border-radius:999px;background:var(--nn-c);color:#fff;font:600 11px/1.45 system-ui,sans-serif;white-space:nowrap}
td .nn-tag{display:block;width:max-content;max-width:180px;white-space:normal}
tr.nn-row>td{background:color-mix(in srgb,var(--nn-c) 6%,transparent)}
`;

function boxOf(el: Element): HTMLElement | null {
  return (el.closest("td") ?? el.closest(".field") ?? el.parentElement) as HTMLElement | null;
}

/** Remove every mark this page put on the form. */
export function clearMarks(doc: Document | null | undefined) {
  if (!doc) return;
  doc.querySelectorAll(".nn-tag").forEach((e) => e.remove());
  doc.querySelectorAll<HTMLElement>(".nn-flag, .nn-row").forEach((e) => {
    e.classList.remove("nn-flag", "nn-pulse", "nn-row");
    e.style.removeProperty("--nn-c");
  });
}

/** Outline each flagged field in its agent's colour, with a short label under it. */
export function markForm(doc: Document | null | undefined, flags: Flag[]) {
  if (!doc) return;
  if (!doc.getElementById(STYLE_ID)) {
    const style = doc.createElement("style");
    style.id = STYLE_ID;
    style.textContent = CSS;
    doc.head.appendChild(style);
  }
  clearMarks(doc);
  const done = new Set<string>(); // one label per field: the first flag about it says it
  for (const flag of flags) {
    const color = AGENT_HEX[flag.agent] ?? "#e11d48";
    for (const field of flag.fields) {
      if (done.has(field.name)) continue;
      done.add(field.name);
      const el = doc.querySelector(`[name="${field.name}"]`);
      const box = el && boxOf(el);
      if (!el || !box) continue;
      box.classList.add("nn-flag");
      box.style.setProperty("--nn-c", color);
      const tag = doc.createElement("span");
      tag.className = "nn-tag";
      tag.style.setProperty("--nn-c", color);
      tag.textContent = box.tagName === "TD" ? field.label : `${agentMeta(flag.agent).name}: ${field.label}`;
      box.appendChild(tag);
      const tr = el.closest("tr") as HTMLElement | null;
      if (tr) {
        tr.classList.add("nn-row");
        tr.style.setProperty("--nn-c", color);
      }
    }
  }
}

/** Scroll the form to a field and make it pulse once. */
export function showField(doc: Document | null | undefined, name: string) {
  const el = doc?.querySelector(`[name="${name}"]`);
  const box = el && boxOf(el);
  if (!box) return;
  box.scrollIntoView({ behavior: "smooth", block: "center" });
  box.classList.add("nn-pulse");
  window.setTimeout(() => box.classList.remove("nn-pulse"), 1400);
}
