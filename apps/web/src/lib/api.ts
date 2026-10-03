import { devRole, supabase } from "./supabase";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

/** Call the engine at /api/v1 with the signed-in user's session token.
 *
 *  `signal` lets a screen cancel an in-flight request when its filters change or
 *  the user navigates away, so a slow answer can never overwrite a newer one.
 */
export async function api<T>(
  path: string,
  params?: Record<string, string | number | undefined>,
  signal?: AbortSignal,
): Promise<T> {
  const url = new URL(`/api/v1${path}`, window.location.origin);
  for (const [k, v] of Object.entries(params ?? {})) {
    if (v !== undefined && v !== "") url.searchParams.set(k, String(v));
  }
  const res = await fetch(url, { headers: await authHeaders(), cache: "no-store", signal });
  return unwrap<T>(res);
}

/** The headers that carry the caller's identity. Supabase session, or dev mode. */
async function authHeaders(): Promise<Record<string, string>> {
  const headers: Record<string, string> = {};
  const sb = supabase();
  if (sb) {
    const { data } = await sb.auth.getSession();
    if (data.session) headers.Authorization = `Bearer ${data.session.access_token}`;
    return headers;
  }
  const role = devRole();
  if (role) headers["X-Dev-Role"] = role;
  const district = process.env.NEXT_PUBLIC_DEV_DISTRICT;
  if (district) headers["X-Dev-District"] = district;
  // A STATE officer's scope is the whole state, so it has to be told which one.
  const state = process.env.NEXT_PUBLIC_DEV_STATE;
  if (state) headers["X-Dev-State"] = state;
  return headers;
}

/** Turn a response into data, or into an ApiError carrying the engine's message. */
async function unwrap<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      if (typeof body?.detail === "string") detail = body.detail;
      else if (Array.isArray(body?.detail) && body.detail[0]?.msg) detail = body.detail[0].msg;
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
  agency_name?: string | null;
  completed_date?: string | null;
  band: Band | null;
  score: number | null;
  priority: number | null;
  limited: boolean | null;
  alerts: string[] | null;
  headline: string | null;
  /** One case per Duplicate & Split group (the queue shows the group once). */
  case_id?: string | null;
  case_size?: number | null;
  /** the work has attached papers or photos a check could read */
  has_evidence?: boolean;
}

export interface Page<T> {
  total: number;
  page: number;
  page_size: number;
  items: T[];
  filters?: Record<string, string | null>;
  counts?: Record<string, number>;
  states?: string[];
  next?: Record<string, string[]>;
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

/** GET /works/{id}/case — the other works filed as this one question.
 *  A case row is narrower than a queue row: it carries no signals or filters,
 *  because it exists to be linked to, not filtered. */
export interface WorkCaseItem {
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

export interface WorkCase {
  case_id: string | null;
  /** how many works the case holds, including this one */
  size: number;
  items: WorkCaseItem[];
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
    sanction_date: string | null;
    completed_date: string | null;
    status: string | null;
  };
  assessment: {
    score: number;
    band: Band;
    limited: boolean;
    priority: number;
    headline: string | null;
    parts: { parts: Part[]; hard_trigger: string | null; reasons?: Reason[] };
    validation: Issue[];
    agents: AgentResult[];
    assessed_at: string;
  };
  /** What an officer has already done about this work, and when (migration 014). */
  review: {
    alert: {
      alert_id: number;
      code: string;
      engine: string | null;
      state: AlertState;
      opened_at: string;
      updated_at: string;
      closed_at: string | null;
      actor: string | null;
      note: string | null;
    } | null;
    inspection: {
      inspection_id: number;
      alert_id: number | null;
      state: InspectionState;
      assigned_to: string | null;
      assigned_by: string | null;
      requested_by: string | null;
      requested_at: string | null;
      assigned_at: string | null;
      verified_at: string | null;
      recorded_at: string | null;
      closed_at: string | null;
      due_date: string | null;
      note: string | null;
      history: { step: string; at: string; by: string | null; note: string | null }[];
      result: {
        outcome: Outcome;
        observed: string | null;
        recorded_by: string | null;
        recorded_at: string;
        gps_source: string | null;
      } | null;
    } | null;
    /** Only steps that really happened, each with the date we stored for it. */
    timeline: { step: string; at: string; what: string }[];
    /** Every action taken on this work, oldest first, from the hash-chained log. */
    history: {
      entry_id: number;
      at: string;
      actor: string;
      role: string;
      action: string;
      note: string | null;
    }[];
    /** Whether that log still verifies, checked at the moment this page loaded. */
    chain: { ok: boolean; entries: number; broken_at?: number; why?: string };
  };
}

export type Role = "MINISTRY" | "STATE" | "DISTRICT" | "FIELD";

export interface Me {
  user_id: string;
  role: Role;
  district_lgd: string | null;
  /** set only for the STATE role; that user sees one state, not all of India */
  state_lgd: string | null;
  name: string | null;
  /** the data's as-of date; shown beside every number on the site */
  snapshot_date: string;
}

/** How much of the corpus each check could actually read (/dashboard/assessment). */
export interface AssessmentCoverage {
  works: number;
  assessed: number;
  not_assessable: number;
  not_assessable_amount: number;
  with_evidence: number;
  without_evidence: number;
  bands: Partial<Record<Band, { works: number; not_assessable: number; with_evidence: number }>>;
  evidence_by_band: Partial<Record<Band, number>>;
  snapshot_date: string;
  note: string;
}

/** One finding code raised on queued works, with the check that raised it. */
export interface FindingRow {
  agent: AgentId;
  code: string;
  text: string;
  hard: boolean;
  works: number;
  amount: number;
  name: string;
  question: string;
}

/** Everything the search box offers, grouped so each result says where it lives. */
export interface SearchResults {
  q: string;
  works: { total: number; items: WorkRow[] };
  districts: DistrictRow[];
  offices: { agency_name: string; district_name: string | null; state_name: string | null; works: number }[];
  /** `codes` are the finding codes this check actually raises in the queue, so a
   *  result can link to the works it flagged. */
  checks: { id: AgentId; name: string; question: string; built: boolean; codes: string[] }[];
}

/** The other works in one Duplicate & Split case. */
export interface CaseMembers {
  case_id: string | null;
  size: number;
  items: Pick<WorkRow, "work_id" | "district_name" | "state_name" | "work_type_code" | "description" | "amount" | "status" | "band" | "score" | "headline">[];
}

export type AlertState = "NEW" | "ACKNOWLEDGED" | "INVESTIGATING" | "RESOLVED";

export interface AlertRow {
  alert_id: number;
  work_id: string;
  code: string;
  engine: string | null;
  state: AlertState;
  opened_at: string;
  updated_at: string;
  actor: string | null;
  note: string | null;
  district_lgd: string | null;
  district_name: string | null;
  state_name: string | null;
  work_type_code: string | null;
  description: string | null;
  amount: number | null;
  status: string | null;
  band: Band | null;
  score: number | null;
  priority: number | null;
  case_size: number | null;
}

export type InspectionState =
  | "REVIEW"
  | "INSPECTION_REQUIRED"
  | "ASSIGNED"
  | "FIELD_VERIFIED"
  | "RESULT_RECORDED"
  | "CLOSED";

export interface InspectionRow {
  inspection_id: number;
  work_id: string;
  state: InspectionState;
  band: Band | null;
  assigned_to: string | null;
  due_date: string | null;
  priority: number | null;
  note: string | null;
  created_at: string;
  updated_at: string;
  district_lgd: string | null;
  district_name: string | null;
  state_name: string | null;
  work_type_code: string | null;
  description: string | null;
  amount: number | null;
  status: string | null;
  agency_name: string | null;
  case_size: number | null;
  alerts: string[] | null;
  has_evidence: boolean;
  results: number;
}

/** What the field officer saw. UNABLE_TO_VERIFY records nothing either way. */
export type Outcome = "OBSERVED" | "NOT_OBSERVED" | "PARTIALLY_OBSERVED" | "UNABLE_TO_VERIFY";

/** PATCH JSON: used by the alert and inspection step buttons. */
export async function apiPatch<T>(path: string, body: unknown, signal?: AbortSignal): Promise<T> {
  const res = await fetch(new URL(`/api/v1${path}`, window.location.origin), {
    method: "PATCH",
    headers: { "Content-Type": "application/json", ...(await authHeaders()) },
    body: JSON.stringify(body),
    cache: "no-store",
    signal,
  });
  return unwrap<T>(res);
}

/** POST JSON to the engine at /api/v1 with the same sign-in headers as api() (T064). */
export async function apiPost<T>(path: string, body: unknown, signal?: AbortSignal): Promise<T> {
  const res = await fetch(new URL(`/api/v1${path}`, window.location.origin), {
    method: "POST",
    headers: { "Content-Type": "application/json", ...(await authHeaders()) },
    body: JSON.stringify(body),
    cache: "no-store",
    signal,
  });
  return unwrap<T>(res);
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
