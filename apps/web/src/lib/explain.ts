// The Visualization Engine's trace: one work through every step (mirror of
// apps/engine/drishti/explain.py, VERSION explain-1.0.0).

import type { Band, PreColour } from "./api";

/** What kind of word a run of the description is, as the page colours it. */
export type Kind = "private" | "not_allowed" | "quantity" | "goods" | "build" | "place";

export interface Segment {
  t: string;
  k: Kind | null;
}

export interface Facts {
  what: string;
  says_nothing: boolean;
  place_named: boolean;
  count: number | null;
  single_unit: boolean;
  length_m: number | null;
  several_sites: boolean;
  bundle: boolean;
  not_allowed: { word: string; item: string | null; rule: string } | null;
  era: string | null;
}

export interface RuleRow {
  id: string;
  title: string;
  ref: string | null;
  raised: boolean;
  severity: string | null;
}

export interface Neighbour {
  work_id: string;
  description: string;
  amount: number | null;
  date: string | null;
  likeness: number;
  place: number;
  flagged: boolean;
}

/** One office habit against the whole scheme (Office Patterns). */
export interface Habit {
  office: number;
  of: number;
  share: number;
  national_share: number;
}

export interface Picture {
  // Guideline Compliance
  rules?: RuleRow[];
  // Cost Anomaly (retired 3 Oct 2026, T099; kept for examples built before then)
  comparison?: {
    metric: string;
    unit: string;
    this_work: number;
    typical_low: number;
    typical_high: number;
    median: number;
    comfort_high?: number | null;
  }[];
  cohort?: { level: string; description: string; n: number };
  work_type_name?: string;
  // Duplicate Work (T100): "flag" is the look-alike line (a note); a repeat is asked by map pin
  compared?: number;
  text_min?: number;
  place_min?: number;
  flag?: number;
  pin_metres?: number;
  nearest?: Neighbour[];
  // Fund Flow
  recommended?: string | null;
  sanctioned?: string | null;
  completed?: string | null;
  as_of?: string;
  sanction_clock_days?: number;
  completion_clock_days?: number;
  // Office Patterns (retired, T125)
  priced_just_under_a_limit?: Habit;
  built_within_a_week_of_sanction?: Habit;
  // Time & Rules (T122): the dates above, its timing rules, and the comfort window
  window_start?: string | null;
  early_line?: string | null;
  late_line?: string | null;
  // Site Progress (T124): one row per site video read
  visits?: VisitSummary[];
  // Cost (T121): the whole estimate against its fair price
  grand_total?: number;
  mp_amount?: number;
  whole?: { verdict: string; fair_total: number; gap: number; gap_share: number; coverage: number };
}

/** One site video as Site Progress read it. */
export interface VisitSummary {
  visit: string;
  kind: "baseline" | "monthly" | "check" | "final";
  captured: string;
  change: "changed" | "no_change" | "cant_tell" | null;
  claim: "shown" | "not_shown" | "cant_tell" | null;
  zones_shown: number;
  viewpoints: [number | null, number | null];
}

export interface TraceFinding {
  code: string;
  text: string;
  risk: number;
  hard: boolean;
  rule: string | null;
  severity: string | null;
  /** the finding's numbers, dates and work IDs, for a short line beside it (T134) */
  facts?: Record<string, unknown>;
}

export interface Check {
  id: string;
  name: string;
  question: string;
  counted: boolean;
  status: "ASSESSED" | "NOT_APPLICABLE" | "NOT_ASSESSABLE" | "NOT_BUILT" | "ERROR";
  verdict: string;
  risk: number;
  headline: string;
  limitations: string[];
  findings: TraceFinding[];
  picture: Picture | null;
}

export interface ScoreFinding {
  code: string;
  risk: number;
  ref_risk: number;
  strength: number;
  hit_rate: number;
  basis: "measured" | "design" | "prior";
  /** [worth a look, read by eye] when the hit rate was measured */
  read: [number, number] | null;
  chance: number;
}

export interface Scoring {
  method: string;
  engines: { engine: string; name: string; chance: number; findings: ScoreFinding[] }[];
  chain: { engine: string; chance: number; score: number }[];
  raw: number;
  floor: boolean;
  score: number;
  band: Band;
  lines: { MEDIUM: number; HIGH: number; CRITICAL: number };
}

export interface Trace {
  version: string;
  as_of: string;
  input: {
    description: string;
    work_type: string | null;
    work_type_name: string | null;
    amount: number | null;
    district: string | null;
    state: string | null;
    office: string | null;
    status: string | null;
    recommended: string | null;
    sanctioned: string | null;
    completed: string | null;
    outside_constituency: boolean | null;
  };
  privacy: { hidden: { name: number; phone: number; number: number } };
  reading: { segments: Segment[]; facts: Facts };
  checks: Check[];
  scoring: Scoring;
  result: {
    band: Band;
    score: number;
    in_queue: boolean;
    limited: boolean;
    colour: PreColour | null;
    advice: string | null;
    reasons: {
      engine: string;
      text: string;
      text_hi: string | null;
      chance: number | null;
      basis: string | null;
      read: [number, number] | null;
    }[];
  };
}

export interface Example {
  id: string;
  title: string;
  story: string;
  trace: Trace;
}

export interface ExamplesFile {
  source: string;
  examples: Example[];
}
