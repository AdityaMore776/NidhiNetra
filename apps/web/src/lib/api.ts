import { NOT_FOUND, SHOWCASE_ON, showcaseAnswer } from "./showcase";
import { devRole, mayHaveSession, supabase, SUPABASE_ON } from "./supabase";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

/**
 * The signed-in user's session token, or the dev role locally. With no sign-in cookie there is no
 * session, so the visitor is answered without loading the sign-in code (T143).
 */
async function signInHeaders(): Promise<Record<string, string>> {
  const headers: Record<string, string> = {};
  if (SUPABASE_ON) {
    const sb = mayHaveSession() ? await supabase() : null;
    const session = sb ? (await sb.auth.getSession()).data.session : null;
    if (session) headers.Authorization = `Bearer ${session.access_token}`;
  } else {
    const role = devRole();
    if (role) headers["X-Dev-Role"] = role;
    const district = process.env.NEXT_PUBLIC_DEV_DISTRICT;
    if (district) headers["X-Dev-District"] = district;
  }
  return headers;
}

/** Call the engine at /api/v1 with the signed-in user's session token. */
export async function api<T>(path: string, params?: Record<string, string | number | undefined>): Promise<T> {
  const url = new URL(`/api/v1${path}`, window.location.origin);
  for (const [k, v] of Object.entries(params ?? {})) {
    if (v !== undefined && v !== "") url.searchParams.set(k, String(v));
  }
  const headers = await signInHeaders();
  // T132: a visitor without a sign-in gets the prototype examples from a static file
  if (SHOWCASE_ON && !headers.Authorization && !headers["X-Dev-Role"]) {
    const answer = await showcaseAnswer(path, params);
    if (answer === NOT_FOUND) throw new ApiError(404, "This work is not one of the prototype examples.");
    if (answer !== undefined) return answer as T;
  }
  const res = await fetch(url, { headers, cache: "no-store" });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      detail = (await res.json()).detail ?? detail;
    } catch {}
    throw new ApiError(res.status, detail);
  }
  return res.json() as Promise<T>;
}

// ---- response shapes (mirror apps/engine/drishti/api/routes.py) ----------------

export type Band = "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";
/** Engine ids come from the engine registry (apps/engine/drishti/agents/registry.py). */
export type AgentId = string;

export interface AgentSummary {
  id: AgentId;
  name: string;
  question: string;
  built: boolean;
  weight?: number;
  /** why the weight differs from the blueprint, e.g. "Shown, not counted: ..." */
  weight_note?: string;
  alerts: number;
}

export interface Summary {
  works: number;
  amount: number;
  bands: Record<Band, number>;
  agents: AgentSummary[];
  snapshot_date: string;
}

export interface DistrictRow {
  district_lgd: string;
  name: string;
  state: string;
  works: number;
  amount: number;
  review: number;
  share: number;
}

export interface OfficeRow {
  agency_name: string;
  completed: number;
  bad: number;
  rate: number;
  lift: number;
  district_lgd: string | null;
  district_name: string | null;
  state_name: string | null;
}

/** An office with a routine habit (Office Patterns), listed once; never an MP. */
export interface OfficeHabit {
  district_lgd: string;
  office: string;
  habit: string;
  count: number;
  total: number;
  share: number;
  national: number;
  lift: number;
  district_name: string | null;
  state_name: string | null;
}

export interface WorkRow {
  work_id: string;
  source: "REAL" | "SCENARIO" | "LIVE";
  district_lgd: string | null;
  district_name: string | null;
  state_name: string | null;
  work_type_code: string | null;
  description: string | null;
  amount: number | null;
  status: string | null;
  recommended_date: string | null;
  band: Band | null;
  score: number | null;
  priority: number | null;
  limited: boolean | null;
  alerts: string[] | null;
  headline: string | null;
  /** One case per group of works filed together (same wording, MP and day; the queue shows it once). */
  case_id?: string | null;
  case_size?: number | null;
}

export interface Page<T> {
  total: number;
  page: number;
  page_size: number;
  items: T[];
}

export interface Finding {
  code: string;
  text: string;
  hard: boolean;
  risk: number;
  evidence: Record<string, unknown>;
}

export interface ComparisonRow {
  metric: string;
  unit: string;
  this_work: number;
  typical_low: number;
  typical_high: number;
  median: number;
  deviation_pct: number;
  anchor_low?: number;
  anchor_high?: number;
  /** the line above which the cost engine asks a question; up to it is the comfort zone */
  comfort_high?: number | null;
}

export interface AgentResult {
  agent: AgentId;
  name?: string;
  question?: string;
  status: "ASSESSED" | "NOT_APPLICABLE" | "NOT_ASSESSABLE" | "NOT_BUILT" | "ERROR";
  verdict: string;
  risk: number;
  confidence: number;
  hard: boolean;
  headline: string;
  version: string;
  findings: Finding[];
  limitations: string[];
  evidence: {
    comparison?: ComparisonRow[];
    cohort?: { level: string; description: string; n: number; p10: number; p50: number; p90: number; sd: number; z: number };
    work_type_name?: string;
    comfort_high?: number | null;
  };
  duration_ms: number;
}

export interface Issue {
  code: string;
  severity: "BLOCK" | "WARN" | "INFO";
  message: string;
  risk: number;
  clause: string | null;
}

export interface Part {
  source: string;
  label: string;
  weight: number;
  contribution: number;
}

/** One of the score's top three reasons (fusion/fuse.py), in English and Hindi. */
export interface Reason {
  source: string;
  label: string;
  contribution: number;
  code: string;
  text_en: string;
  text_hi: string;
  /** Fusion v3: this finding's chance of being worth a look, and the by-eye reads behind it. */
  chance?: number;
  hit_rate?: number;
  basis?: "measured" | "design" | "prior";
  read?: [number, number] | null;
}

export interface WorkDetail {
  work: {
    work_id: string;
    source: string;
    house: string | null;
    term: string | null;
    state_name: string | null;
    district_lgd: string | null;
    district_name: string | null;
    constituency: string | null;
    mp_name: string | null;
    agency_name: string | null;
    fy: string | null;
    work_type_code: string | null;
    category: string | null;
    description: string | null;
    amount: number | null;
    recommended_date: string | null;
    completed_date: string | null;
    status: string | null;
  };
  assessment: {
    score: number;
    band: Band;
    limited: boolean;
    priority: number;
    parts: { parts: Part[]; hard_trigger: string | null; reasons?: Reason[] };
    validation: Issue[];
    agents: AgentResult[];
    assessed_at: string;
  };
}

export interface Me {
  user_id: string;
  /** PUBLIC = anyone without a sign-in: views every district, saves nothing (T130) */
  role: "PUBLIC" | "MINISTRY" | "DISTRICT" | "FIELD";
  district_lgd: string | null;
  name: string | null;
}

/** POST JSON to the engine at /api/v1 with the same sign-in headers as api() (T064). */
export async function apiPost<T>(path: string, body: unknown): Promise<T> {
  const headers = { "Content-Type": "application/json", ...(await signInHeaders()) };
  const res = await fetch(new URL(`/api/v1${path}`, window.location.origin), {
    method: "POST",
    headers,
    body: JSON.stringify(body),
    cache: "no-store",
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const d = (await res.json()).detail;
      detail = typeof d === "string" ? d : "Please check the details entered.";
    } catch {}
    throw new ApiError(res.status, detail);
  }
  return res.json() as Promise<T>;
}

// ---- pre-sanction check (mirror apps/engine/drishti/presanction.py) -------------

export type PreColour = "GREEN" | "AMBER" | "RED";

export interface PreReason {
  engine: string;
  code: string;
  text: string;
  risk: number;
  serious: boolean;
}

export interface PreSanction {
  colour: PreColour;
  advice: string;
  score: number;
  band: Band;
  reasons: PreReason[];
  not_checked: { engine: string; why: string }[];
  as_of: string;
  district_name: string;
}

export interface PreOptions {
  districts: { district_lgd: string; name: string; state_name: string }[];
  work_types: { code: string; name: string }[];
  as_of: string;
}

// ---- site visits (T123; mirror apps/engine/drishti/api/site_visits.py) -------------------

export type VisitKind = "baseline" | "monthly" | "check" | "final";

export interface SiteMap {
  kind: "compact" | "linear";
  lat: number;
  lon: number;
  radius_m: number;
  end_lat: number | null;
  end_lon: number | null;
  length_m: number;
  stretches: string[];
  gps_margin_m: number;
  stretch_m: number;
}

export interface Viewpoint {
  id: string;
  frame_url: string | null;
}

export interface SiteVisitRow {
  visit_id: string;
  kind: VisitKind;
  status: "started" | "uploaded" | "read" | "rejected";
  claim: string | null;
  note: string | null;
  captured_at: string | null;
  readings: Record<string, unknown> | null;
}

export interface SiteVisits {
  work_id: string;
  site: SiteMap | null;
  next_kind: VisitKind;
  viewpoints: Viewpoint[];
  visits: SiteVisitRow[];
}

export interface VisitStart {
  visit_id: string;
  token: string;
  kind: VisitKind;
  site: SiteMap | null;
  viewpoints: Viewpoint[];
}
