import type { Band } from "@/lib/api";
import { BAND_LABEL, BAND_TONE } from "@/lib/format";
import { StatusLabel } from "./kit";

const BORDER: Record<Band, string> = {
  HIGH: "border-high",
  MEDIUM: "border-medium",
  LOW: "border-low",
};
const TEXT: Record<Band, string> = {
  HIGH: "text-high",
  MEDIUM: "text-medium",
  LOW: "text-low",
};

/**
 * The 0–100 risk block. Typography and borders carry the weight — no gauges,
 * meters or animation. `score` is the engine's 0–1 fusion score.
 */
export function RiskScore({
  score,
  band,
  limited,
  size = "lg",
}: {
  score: number;
  band: Band;
  limited?: boolean;
  size?: "lg" | "sm";
}) {
  const n = Math.round(score * 100);
  const big = size === "lg";
  return (
    <div className={`bg-surface border-2 ${BORDER[band]}`}>
      <div className="label border-b border-line px-3 py-1.5">Risk score</div>
      <div className="flex items-baseline gap-2 px-3 pt-2">
        <span className={`tnum font-bold leading-none ${TEXT[band]} ${big ? "text-6xl" : "text-4xl"}`}>{n}</span>
        <span className="tnum text-sm font-medium text-muted">/ 100</span>
      </div>
      <div className="flex flex-wrap items-center gap-2 px-3 pb-3 pt-2.5">
        <StatusLabel tone={BAND_TONE[band]} solid>
          {BAND_LABEL[band]}
        </StatusLabel>
        <StatusLabel tone={band === "LOW" ? "low" : "neutral"}>
          {band === "LOW" ? "For record" : "Needs verification"}
        </StatusLabel>
        {limited && band === "LOW" && <StatusLabel tone="neutral">Limited evidence</StatusLabel>}
      </div>
    </div>
  );
}
