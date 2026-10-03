"use client";

import { motion, useReducedMotion } from "motion/react";
import type { AgentResult, ComparisonRow } from "@/lib/api";
import { inr } from "@/lib/format";

/** Where an amount sits: the usual range, the comfort zone above it (room for a bigger scope or a
 *  contingency margin, never questioned), or beyond the comfort limit, the only place the cost
 *  engine asks a question. Rows without a comfort limit (several sites, per unit) are shown, not judged. */
function zone(r: ComparisonRow): { label: string; color: string } {
  if (r.this_work <= r.typical_high && r.this_work >= r.typical_low) return { label: "usual", color: "var(--low)" };
  if (r.this_work < r.typical_low) return { label: "below usual", color: "var(--muted-foreground)" };
  if (r.comfort_high == null) return { label: "above usual, not judged", color: "var(--muted-foreground)" };
  if (r.this_work <= r.comfort_high) return { label: "comfort zone", color: "var(--low)" };
  return { label: `${(r.this_work / r.comfort_high).toFixed(1)}x the comfort limit`, color: "var(--high)" };
}

/** This work against the usual range and comfort zone of its peers. */
export function StatisticalEvidence({ result }: { result: AgentResult }) {
  const rows = result.evidence.comparison ?? [];
  const cohort = result.evidence.cohort;
  return (
    <div className="space-y-4">
      <div className="overflow-x-auto rounded-xl border">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b bg-muted/60 text-left">
              <th className="px-3 py-2 eyebrow">Metric</th>
              <th className="px-3 py-2 text-right eyebrow">This work</th>
              <th className="px-3 py-2 text-right eyebrow">Usual range</th>
              <th className="px-3 py-2 text-right eyebrow">Comfort limit</th>
              <th className="px-3 py-2 text-right eyebrow">Where it sits</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => {
              const z = zone(r);
              const unit = r.unit === "Rs/m" ? "/m" : "";
              return (
                <tr key={r.metric} className="border-b last:border-0">
                  <td className="px-3 py-2.5">{r.metric}</td>
                  <td className="num px-3 py-2.5 text-right font-semibold">
                    {inr(r.this_work)}
                    {unit}
                  </td>
                  <td className="num px-3 py-2.5 text-right text-muted-foreground">
                    {inr(r.typical_low)}–{inr(r.typical_high)}
                    {unit}
                    {r.anchor_low !== undefined && (
                      <div className="text-[11px]">
                        published rates {inr(r.anchor_low)}–{inr(r.anchor_high)}/m
                      </div>
                    )}
                  </td>
                  <td className="num px-3 py-2.5 text-right text-muted-foreground">{r.comfort_high != null ? `${inr(r.comfort_high)}${unit}` : "—"}</td>
                  <td className="px-3 py-2.5 text-right">
                    <span className="inline-flex items-center gap-1.5 whitespace-nowrap text-xs font-semibold text-foreground">
                      <span className="size-2 rounded-full" style={{ background: z.color }} />
                      {z.label}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      {cohort && <BandStrip cohort={cohort} value={rows[0]?.this_work} comfort={rows[0]?.comfort_high ?? null} />}
      <p className="text-[11px] leading-relaxed text-muted-foreground">
        The comfort zone runs from the top of the usual range to the comfort limit: room for a bigger scope or a contingency margin.
        NidhiNetra asks a question only above the comfort limit.
      </p>
    </div>
  );
}

/** Where this work's cost sits on its peers' log-scale range, with the comfort zone above it. */
function BandStrip({
  cohort,
  value,
  comfort,
}: {
  cohort: NonNullable<AgentResult["evidence"]["cohort"]>;
  value?: number;
  comfort: number | null;
}) {
  const reduce = useReducedMotion();
  if (!value) return null;
  const lv = Math.log10(value);
  const lc = comfort ? Math.log10(comfort) : null;
  const lo = Math.min(cohort.p10 - 0.6, lv - 0.2);
  const hi = Math.max((lc ?? cohort.p90) + 0.3, lv + 0.2);
  const x = (v: number) => ((v - lo) / (hi - lo)) * 100;
  return (
    <div className="rounded-xl bg-muted/50 p-3">
      <div className="relative h-12">
        <div className="absolute top-5 h-2 w-full rounded-full bg-white ring-1 ring-border" />
        <div
          className="absolute top-5 h-2 rounded-full"
          style={{ left: `${x(cohort.p10)}%`, width: `${x(cohort.p90) - x(cohort.p10)}%`, background: "color-mix(in srgb, var(--eng-cost) 40%, white)" }}
        />
        {lc !== null && lc > cohort.p90 && (
          <div
            className="absolute top-5 h-2"
            style={{ left: `${x(cohort.p90)}%`, width: `${x(lc) - x(cohort.p90)}%`, background: "color-mix(in srgb, var(--low) 30%, white)" }}
            title="comfort zone"
          />
        )}
        <div className="absolute top-3.5 h-5 w-0.5 bg-muted-foreground" style={{ left: `${x(cohort.p50)}%` }} title="median" />
        {lc !== null && <div className="absolute top-3 h-6 w-0.5" style={{ left: `${x(lc)}%`, background: "var(--high)" }} title="comfort limit" />}
        <motion.div
          className="absolute top-2 -ml-2 size-4 rounded-full border-2 border-white shadow-md"
          style={{ background: "var(--eng-cost)" }}
          initial={reduce ? false : { left: "0%" }}
          whileInView={{ left: `${x(lv)}%` }}
          viewport={{ once: true }}
          transition={{ duration: 1.2, ease: [0.2, 0.8, 0.2, 1] }}
          title="this work"
        />
      </div>
      <div className="flex flex-wrap justify-between gap-2 text-[11px] text-muted-foreground">
        <span>
          shaded: the middle 80% of {cohort.n.toLocaleString("en-IN")} {cohort.description} · green: comfort zone · red line: comfort limit
        </span>
        <span className="inline-flex items-center gap-1 font-medium text-foreground">
          <span className="size-2.5 rounded-full" style={{ background: "var(--eng-cost)" }} /> this work
        </span>
      </div>
    </div>
  );
}
