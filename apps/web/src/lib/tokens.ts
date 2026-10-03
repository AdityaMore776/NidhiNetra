import type { Band } from "./api";

/**
 * Risk-band semantics for the interface.
 *
 * Four roles per band, and each is measured by `npm run contrast`:
 *   `ink`   text and badge labels  (>= 4.5:1 on its own tint and on white)
 *   `mark`  bars, dots, borders    (>= 3:1 on the canvas)
 *   `tint`  the surface behind it
 *   `edge`  its 1px border
 *
 * `glyph` and `label` exist because colour must never be the only carrier of
 * meaning: each band also gets a shape and a word.
 */
export interface BandSemantics {
  label: string;
  short: string;
  glyph: string;
  ink: string;
  mark: string;
  tint: string;
  edge: string;
  /** plain-language reading, shown in the "what does this mean" help */
  meaning: string;
}

export const BANDS: Record<Band, BandSemantics> = {
  CRITICAL: {
    label: "Critical",
    short: "CRIT",
    glyph: "▲",
    ink: "var(--critical-ink)",
    mark: "var(--critical)",
    tint: "var(--critical-tint)",
    edge: "var(--critical-edge)",
    meaning:
      "Two or more checks agree, or a check found a break of a guideline rule. Look at this one first.",
  },
  HIGH: {
    label: "High",
    short: "HIGH",
    glyph: "◆",
    ink: "var(--high-ink)",
    mark: "var(--high)",
    tint: "var(--high-tint)",
    edge: "var(--high-edge)",
    meaning:
      "One check that is usually right on its own, or two that are each right about half the time. Worth a look this week.",
  },
  MEDIUM: {
    label: "Medium",
    short: "MED",
    glyph: "●",
    ink: "var(--medium-ink)",
    mark: "var(--medium-mark)",
    tint: "var(--medium-tint)",
    edge: "var(--medium-edge)",
    meaning:
      "A signal on its own. It stays here until a second check agrees or someone reads it by eye.",
  },
  LOW: {
    label: "Low",
    short: "LOW",
    glyph: "○",
    ink: "var(--low-ink)",
    mark: "var(--low-mark)",
    tint: "var(--low-tint)",
    edge: "var(--low-edge)",
    meaning:
      "No check raised a signal above its threshold. This is not a certificate that the work is correct.",
  },
};

export const BAND_ORDER: Band[] = ["CRITICAL", "HIGH", "MEDIUM", "LOW"];

/** The two bands that enter the review queue. The queue is exactly these two. */
export const QUEUE_BANDS: Band[] = ["CRITICAL", "HIGH"];

/**
 * What a check can tell us about one work. `NOT_ASSESSABLE` and `NOT_APPLICABLE`
 * are statuses, never a low score: each one carries no risk weight and stays
 * visible on the screen instead of being hidden.
 */
export type AssessStatus =
  | "ASSESSED"
  | "NOT_APPLICABLE"
  | "NOT_ASSESSABLE"
  | "NOT_BUILT"
  | "ERROR";

export const STATUS_META: Record<
  AssessStatus,
  { label: string; ink: string; tint: string; edge: string; glyph: string; note: string }
> = {
  ASSESSED: {
    label: "Checked",
    ink: "var(--secondary)",
    tint: "var(--sunken)",
    edge: "var(--line-strong)",
    glyph: "✓",
    note: "The check ran and read the available data.",
  },
  NOT_APPLICABLE: {
    label: "Does not apply",
    ink: "var(--secondary)",
    tint: "var(--sunken)",
    edge: "var(--line-strong)",
    glyph: "–",
    note: "The question does not arise for this work, so nothing was weighed.",
  },
  NOT_ASSESSABLE: {
    label: "Could not check",
    ink: "var(--medium-ink)",
    tint: "var(--medium-tint)",
    edge: "var(--medium-edge)",
    glyph: "◐",
    note: "The question arises but the available data cannot answer it. This is not a pass.",
  },
  NOT_BUILT: {
    label: "In development",
    ink: "var(--muted)",
    tint: "var(--sunken)",
    edge: "var(--line-strong)",
    glyph: "○",
    note: "The check exists but is not switched on, so it weighed nothing.",
  },
  ERROR: {
    label: "Check did not run",
    ink: "var(--high-ink)",
    tint: "var(--high-tint)",
    edge: "var(--high-edge)",
    glyph: "!",
    note: "The check failed on this record. It weighed nothing, so nothing is claimed about the work.",
  },
};

/** Where a work sits in the scheme's life, as the portal records it. */
export const LIFECYCLE: Record<string, { label: string; stage: number }> = {
  RECOMMENDED: { label: "Recommended", stage: 1 },
  SANCTIONED: { label: "Sanctioned", stage: 2 },
  COMPLETED: { label: "Completed", stage: 5 },
};
