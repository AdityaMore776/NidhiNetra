import type { AgentId, Band } from "./api";

/** Indian rupees in lakh / crore, as officers read them. */
export function inr(v: number | null | undefined): string {
  if (v === null || v === undefined || Number.isNaN(v)) return "—";
  if (v >= 1e10) return `₹${Math.round(v / 1e7).toLocaleString("en-IN")} Cr`;
  if (v >= 1e7) return `₹${(v / 1e7).toFixed(2)} Cr`;
  if (v >= 1e5) return `₹${(v / 1e5).toFixed(2)} L`;
  return `₹${Math.round(v).toLocaleString("en-IN")}`;
}

export function count(v: number | null | undefined): string {
  return v === null || v === undefined ? "—" : v.toLocaleString("en-IN");
}

export function pct(v: number, digits = 1): string {
  return `${(v * 100).toFixed(digits)}%`;
}

type AgentMeta = { n: string; name: string; color: string; question: string };

/** Display names and colours per engine. The engine registry is the source of truth; an engine
 *  missing here still renders, with the name and question the API sends. */
export const AGENTS: Record<AgentId, AgentMeta> = {
  compliance: { n: "01", name: "Guideline Compliance", color: "var(--navy)", question: "Does the work follow the MPLADS guidelines?" },
  cost_estimate: { n: "02", name: "Cost", color: "var(--statistical)", question: "Is the agency's cost estimate right for this size of work here?" },
  dup_split: { n: "03", name: "Duplicate Work", color: "var(--duplicate)", question: "Is this work already sanctioned at this site?" },
  delay: { n: "04", name: "Fund Flow", color: "var(--site)", question: "Is money stuck waiting for sanction?" },
  office_patterns: { n: "05", name: "Office Patterns", color: "var(--reuse)", question: "Does this work's office price or close works in an unusual way?" },
  paperwork: { n: "06", name: "Paperwork", color: "var(--inputs)", question: "Do the work's own papers agree with the portal?" },
  photo_evidence: { n: "07", name: "Photo Evidence", color: "var(--fusion)", question: "Are the work's photos new, from its place and from its time?" },
  // retired 3 Oct 2026 (T099): results stored before then still read by name until re-assessed
  statistical: { n: "··", name: "Cost Anomaly (retired)", color: "var(--muted)", question: "Is the project cost unusual for similar works?" },
};

// Ids stored before the engine registry (the deck's four agents).
const LEGACY: Record<string, string> = { duplicate_project: "dup_split", image_reuse: "photo_forensics" };

export function agentMeta(id: string, name?: string, question?: string): AgentMeta {
  const key = LEGACY[id] ?? id;
  return AGENTS[key] ?? { n: "··", name: name ?? key, color: "var(--muted)", question: question ?? "" };
}

export const AGENT_ORDER: AgentId[] = ["compliance", "cost_estimate", "dup_split", "delay",
  "office_patterns", "paperwork", "photo_evidence"];

export const BAND_COLOR: Record<Band, string> = {
  CRITICAL: "var(--critical)",
  HIGH: "var(--high)",
  MEDIUM: "var(--medium)",
  LOW: "var(--low)",
};

export const BAND_LABEL: Record<Band, string> = {
  CRITICAL: "Critical",
  HIGH: "High risk",
  MEDIUM: "Medium risk",
  LOW: "Low risk",
};

/** Work type names (mirror of apps/engine/drishti/reference/work_types.yaml). */
export const WORK_TYPES: Record<string, string> = {
  ROAD_CC: "Cement concrete road",
  ROAD_BT: "Bituminous road",
  FOOTPATH: "Footpath / paver block pathway",
  CULVERT: "Culvert / small bridge",
  BRIDGE: "Bridge",
  COMMUNITY_HALL: "Community hall / bhavan",
  SCHOOL_BUILDING: "School building / classroom",
  HEALTH_BUILDING: "Health sub-centre / PHC",
  LIBRARY: "Public library",
  BOUNDARY_WALL: "Boundary wall",
  TOILET_BLOCK: "Public toilet block",
  BUS_SHELTER: "Bus shelter",
  POND: "Pond / talab renovation",
  CHECK_DAM: "Check dam",
  BOREWELL: "Borewell / hand pump",
  WATER_TANK: "Overhead water tank",
  DRAIN: "Drainage / nala",
  PLAYGROUND: "Playground / open gym",
  SOLAR_PLANT: "Solar power plant",
  CREMATORIUM: "Crematorium / burial ground",
  STREET_LIGHT: "Solar / LED street light",
  WATER_SUPPLY: "Drinking water supply pipeline",
  EMBANKMENT: "Flood embankment / protection wall",
  ELECTRICITY: "Electricity distribution",
  VEHICLE: "Vehicle (van, bus, boat)",
  HIGH_MAST: "High mast light",
  CCTV: "CCTV system",
  COMPUTER: "Computers / smart class",
  FURNITURE: "Furniture",
  AMBULANCE: "Ambulance / hearse van",
  MEDICAL_EQUIPMENT: "Medical equipment",
  SPORTS_EQUIPMENT: "Sports / gym equipment",
  OTHER: "Other",
};

export function workType(code: string | null | undefined): string {
  if (!code) return "Unclassified";
  return WORK_TYPES[code] ?? code;
}

export function workHref(id: string): string {
  return `/work?id=${encodeURIComponent(id)}`;
}
