"use client";

import { ChevronDown, CircleSlash, Info } from "lucide-react";
import { motion, useReducedMotion } from "motion/react";
import { useState } from "react";
import type { AgentResult } from "@/lib/api";
import { agentMeta } from "@/lib/format";
import { cn } from "@/lib/utils";
import { EngineMark } from "./nn/badges";
import { StatisticalEvidence } from "./StatisticalEvidence";

export const STATUS_NOTE: Record<AgentResult["status"], string> = {
  ASSESSED: "",
  NOT_APPLICABLE: "Not applicable yet",
  NOT_ASSESSABLE: "Could not be assessed",
  NOT_BUILT: "In development",
  ERROR: "Check did not run",
};

/** One engine's answer for this work: its headline, findings, evidence and what it cannot tell. */
export function AgentCard({ result }: { result: AgentResult }) {
  const meta = agentMeta(result.agent, result.name, result.question);
  const quiet = result.status !== "ASSESSED";
  const reduce = useReducedMotion();
  const [open, setOpen] = useState(false);
  const risk = Math.round(result.risk * 100);

  return (
    <section className={cn("panel group relative overflow-hidden transition-shadow hover:shadow-lift", result.status === "NOT_BUILT" && "opacity-70")}>
      <div className="absolute inset-x-0 top-0 h-[3px]" style={{ background: quiet ? "var(--border)" : meta.color }} />
      {/* the status wraps under the question on a narrow card instead of squeezing it (T143) */}
      <header className="flex flex-wrap items-start gap-3 px-4 pb-3 pt-5 sm:px-5">
        <EngineMark id={result.agent} size={36} />
        <div className="min-w-0 flex-[1_1_12rem]">
          <div className="font-semibold text-brand-950">{meta.name}</div>
          <div className="text-xs leading-snug text-muted-foreground">{meta.question}</div>
        </div>
        <div className="ml-auto shrink-0 text-right">
          {quiet ? (
            <span className="inline-flex items-center gap-1 rounded-full bg-muted px-2.5 py-1 text-[11px] font-medium text-muted-foreground">
              <CircleSlash className="size-3" />
              {STATUS_NOTE[result.status]}
            </span>
          ) : risk > 0 ? (
            <div>
              <div className="num text-xl font-semibold leading-none tracking-[-0.03em]" style={{ color: meta.color }}>
                {risk}
                <span className="text-xs font-normal text-muted-foreground"> /100</span>
              </div>
              <div className="mt-1 text-[10px] text-muted-foreground">risk from this check</div>
            </div>
          ) : (
            <span className="inline-flex items-center gap-1 rounded-full bg-low/10 px-2.5 py-1 text-[11px] font-semibold text-low">None found</span>
          )}
        </div>
      </header>

      {!quiet && (
        <div className="mx-5 h-1 overflow-hidden rounded-full bg-muted">
          <motion.div
            className="h-full rounded-full"
            style={{ background: meta.color }}
            initial={reduce ? false : { width: 0 }}
            whileInView={{ width: `${Math.max(risk, risk > 0 ? 3 : 0)}%` }}
            viewport={{ once: true }}
            transition={{ duration: 1, ease: [0.22, 1, 0.36, 1] }}
          />
        </div>
      )}

      <div className="space-y-4 px-5 py-4">
        <p className="text-sm leading-relaxed text-foreground/90">{result.headline}</p>
        {result.agent === "statistical" && result.status === "ASSESSED" && <StatisticalEvidence result={result} />}
        {result.findings.length > 1 && (
          <ul className="space-y-2 text-sm">
            {result.findings.map((f) => (
              <li key={f.code} className="flex gap-2.5 rounded-lg bg-muted/60 px-3 py-2">
                <span className="mt-1.5 size-2 shrink-0 rounded-full" style={{ background: f.hard ? "var(--high)" : "var(--medium)" }} />
                <span className="leading-relaxed">{f.text}</span>
              </li>
            ))}
          </ul>
        )}
        {result.limitations.length > 0 && (
          <div className="rounded-xl border border-dashed">
            <button
              type="button"
              onClick={() => setOpen((o) => !o)}
              className="flex w-full items-center gap-2 px-3 py-2 text-left text-xs font-medium text-muted-foreground hover:text-foreground"
            >
              <Info className="size-3.5" />
              What this check cannot tell ({result.limitations.length})
              <ChevronDown className={cn("ml-auto size-3.5 transition-transform", open && "rotate-180")} />
            </button>
            <motion.div initial={false} animate={{ height: open ? "auto" : 0, opacity: open ? 1 : 0 }} className="overflow-hidden">
              <ul className="list-disc space-y-1 px-3 pb-3 pl-8 text-xs leading-relaxed text-muted-foreground">
                {result.limitations.map((l) => (
                  <li key={l}>{l}</li>
                ))}
              </ul>
            </motion.div>
          </div>
        )}
      </div>
    </section>
  );
}
