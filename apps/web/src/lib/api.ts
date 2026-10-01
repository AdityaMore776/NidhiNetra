import { devRole, supabase } from "./supabase";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

/** Call the engine at /api/v1 with the signed-in user's session token. */
export async function api<T>(path: string, params?: Record<string, string | number | undefined>): Promise<T> {
  const url = new URL(`/api/v1${path}`, window.location.origin);
  for (const [k, v] of Object.entries(params ?? {})) {
    if (v !== undefined && v !== "") url.searchParams.set(k, String(v));
  }
  const headers: Record<string, string> = {};
  const sb = supabase();
  if (sb) {
    const { data } = await sb.auth.getSession();
    if (data.session) headers.Authorization = `Bearer ${data.session.access_token}`;
  } else {
    const role = devRole();
    if (role) headers["X-Dev-Role"] = role;
    const district = process.env.NEXT_PUBLIC_DEV_DISTRICT;
    if (district) headers["X-Dev-District"] = district;
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
  role: "MINISTRY" | "DISTRICT" | "FIELD";
  district_lgd: string | null;
  name: string | null;
}
