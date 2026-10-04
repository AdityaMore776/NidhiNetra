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
  // the four agents (owner, 3 Oct 2026; plan docs/plans/T120-four-agents.md; T125)
  cost_estimate: { n: "01", name: "Cost", color: "var(--eng-cost)", question: "Is every line of the estimate fairly priced for this district, and is the whole estimate fair?" },
  dup_split: { n: "02", name: "Duplicate Work", color: "var(--eng-dup)", question: "Is this work already sanctioned here, or one job cut to stay under a limit?" },
  time_rules: { n: "03", name: "Time & Rules", color: "var(--eng-compliance)", question: "Was it sanctioned on time, and is it being finished in a believable time?" },
  site_progress: { n: "04", name: "Site Progress", color: "var(--eng-flow)", question: "Do the monthly site videos show real, new work, at this work's site, for this work only?" },
  // retired (T099, T125): results stored before then still read by name until re-assessed
  compliance: { n: "··", name: "Guideline Compliance (retired)", color: "var(--muted-foreground)", question: "Does the work follow the MPLADS guidelines?" },
  delay: { n: "··", name: "Fund Flow (retired)", color: "var(--muted-foreground)", question: "Is money stuck waiting for sanction?" },
  office_patterns: { n: "··", name: "Office Patterns (retired)", color: "var(--muted-foreground)", question: "Does the office record works in an unusual way?" },
  paperwork: { n: "··", name: "Paperwork (retired)", color: "var(--muted-foreground)", question: "Do the work's papers agree with its record?" },
  photo_evidence: { n: "··", name: "Photo Evidence (retired)", color: "var(--muted-foreground)", question: "Are the work's photos its own, from its place and time?" },
  statistical: { n: "··", name: "Cost Anomaly (retired)", color: "var(--muted-foreground)", question: "Is the project cost unusual for similar works?" },
};

// Ids stored before the engine registry (the deck's four agents).
const LEGACY: Record<string, string> = { duplicate_project: "dup_split", image_reuse: "photo_forensics" };

export function agentMeta(id: string, name?: string, question?: string): AgentMeta {
  const key = LEGACY[id] ?? id;
  return AGENTS[key] ?? { n: "··", name: name ?? key, color: "var(--muted-foreground)", question: question ?? "" };
}

export const AGENT_ORDER: AgentId[] = ["cost_estimate", "dup_split", "time_rules", "site_progress"];

export const BAND_COLOR: Record<Band, string> = {
  CRITICAL: "var(--critical)",
  HIGH: "var(--high)",
  MEDIUM: "var(--medium)",
  LOW: "var(--low)",
};

/** Soft fills behind a band's word (badges, row tints). */
export const BAND_SOFT: Record<Band, string> = {
  CRITICAL: "var(--critical-soft)",
  HIGH: "var(--high-soft)",
  MEDIUM: "var(--medium-soft)",
  LOW: "var(--low-soft)",
};

export const BAND_ORDER: Band[] = ["CRITICAL", "HIGH", "MEDIUM", "LOW"];

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
