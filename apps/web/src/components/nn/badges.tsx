"use client";

import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import type { Band } from "@/lib/api";
import { agentMeta, BAND_COLOR, BAND_LABEL, BAND_SOFT } from "@/lib/format";
import { cn } from "@/lib/utils";

/** A risk band: always its word, its colour as a dot and a soft fill (never colour alone). */
export function BandBadge({
  band,
  limited,
  score,
  size = "md",
  className,
}: {
  band: Band | null;
  limited?: boolean | null;
  score?: number | null;
  size?: "sm" | "md" | "lg";
  className?: string;
}) {
  if (!band) return <span className="text-xs text-muted-foreground">Not assessed</span>;
  const pad = size === "lg" ? "px-3 py-1 text-sm" : size === "sm" ? "px-2 py-0.5 text-[11px]" : "px-2.5 py-0.5 text-xs";
  return (
    <span className={cn("inline-flex items-center gap-1.5 whitespace-nowrap", className)}>
      <span
        className={cn("inline-flex items-center gap-1.5 rounded-full font-semibold ring-1 ring-inset", pad)}
        style={{ background: BAND_SOFT[band], color: BAND_COLOR[band], ["--tw-ring-color" as string]: `color-mix(in srgb, ${BAND_COLOR[band]} 22%, transparent)` }}
      >
        <span className="relative grid size-2 place-items-center">
          {(band === "CRITICAL" || band === "HIGH") && (
            <span className="absolute size-2 rounded-full animate-pulse-ring" style={{ background: BAND_COLOR[band] }} />
          )}
          <span className="relative size-2 rounded-full" style={{ background: BAND_COLOR[band] }} />
        </span>
        {BAND_LABEL[band]}
        {score != null && <span className="num font-medium opacity-80">· {Math.round(score * 100)}</span>}
      </span>
      {limited && band === "LOW" && <span className="text-[11px] text-muted-foreground">limited evidence</span>}
    </span>
  );
}

/** Which engines raised something: numbered chips in each engine's colour, named on hover. */
export function EngineChips({ alerts, className }: { alerts: string[] | null; className?: string }) {
  const list = (alerts ?? []).filter((a) => a !== "validation");
  if (!list.length && !alerts?.includes("validation")) return <span className="text-xs text-subtle-foreground">None</span>;
  return (
    <span className={cn("flex flex-wrap gap-1", className)}>
      {list.map((a) => {
        const m = agentMeta(a);
        return (
          <Tooltip key={a}>
            <TooltipTrigger asChild>
              <span
                className="inline-flex h-5 items-center gap-1 rounded-md px-1.5 font-mono text-[10px] font-semibold text-white shadow-sm"
                style={{ background: m.color }}
              >
                {m.n}
              </span>
            </TooltipTrigger>
            <TooltipContent side="top">{m.name}</TooltipContent>
          </Tooltip>
        );
      })}
      {alerts?.includes("validation") && (
        <Tooltip>
          <TooltipTrigger asChild>
            <span className="inline-flex h-5 items-center rounded-md bg-brand-600 px-1.5 font-mono text-[10px] font-semibold text-white">DV</span>
          </TooltipTrigger>
          <TooltipContent side="top">Data Validation</TooltipContent>
        </Tooltip>
      )}
    </span>
  );
}

export function SourceBadge({ source }: { source: string }) {
  const map: Record<string, [string, string]> = {
    REAL: ["Real eSAKSHI record", "var(--brand-600)"],
    SCENARIO: ["Demo scenario", "var(--eng-office)"],
    LIVE: ["Live submission", "var(--eng-flow)"],
  };
  const [label, color] = map[source] ?? [source, "var(--muted-foreground)"];
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[11px] font-medium"
      style={{ color, borderColor: `color-mix(in srgb, ${color} 35%, transparent)`, background: `color-mix(in srgb, ${color} 6%, white)` }}
    >
      <span className="size-1.5 rounded-full" style={{ background: color }} />
      {label}
    </span>
  );
}

/** The engine's round number badge, used in cards and lists. */
export function EngineMark({ id, size = 32 }: { id: string; size?: number }) {
  const m = agentMeta(id);
  return (
    <span
      className="grid shrink-0 place-items-center rounded-xl font-mono text-[11px] font-semibold text-white shadow-sm"
      style={{
        width: size,
        height: size,
        background: `linear-gradient(140deg, color-mix(in srgb, ${m.color} 78%, white), ${m.color})`,
        boxShadow: `0 6px 16px -8px ${m.color}`,
      }}
    >
      {m.n}
    </span>
  );
}
