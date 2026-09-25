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

export const AGENTS: Record<AgentId, { n: string; name: string; color: string; question: string }> = {
  site_progress: { n: "01", name: "Site Progress", color: "var(--site)", question: "Does the site evidence match the claimed progress?" },
  image_reuse: { n: "02", name: "Image Reuse", color: "var(--reuse)", question: "Has the same image appeared elsewhere?" },
  duplicate_project: { n: "03", name: "Duplicate Project", color: "var(--duplicate)", question: "Is a similar work already recorded nearby?" },
  statistical: { n: "04", name: "Statistical", color: "var(--statistical)", question: "Is the project cost unusual for similar works?" },
};

export const AGENT_ORDER: AgentId[] = ["site_progress", "image_reuse", "duplicate_project", "statistical"];

export const BAND_COLOR: Record<Band, string> = {
  HIGH: "var(--high)",
  MEDIUM: "var(--medium)",
  LOW: "var(--low)",
};

export const BAND_LABEL: Record<Band, string> = {
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
