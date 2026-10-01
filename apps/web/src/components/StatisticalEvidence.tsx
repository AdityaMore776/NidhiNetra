import type { AgentResult, ComparisonRow } from "@/lib/api";
import { inr } from "@/lib/format";

/** Where an amount sits: the usual range, the comfort zone above it (room for a bigger scope or a
 *  contingency margin, never questioned), or beyond the comfort limit, the only place the cost
 *  engine asks a question. Rows without a comfort limit (several sites, per unit) are shown, not judged. */
function zone(r: ComparisonRow): { label: string; color: string } {
  if (r.this_work <= r.typical_high && r.this_work >= r.typical_low) return { label: "usual", color: "var(--low)" };
  if (r.this_work < r.typical_low) return { label: "below usual", color: "var(--muted)" };
  if (r.comfort_high == null) return { label: "above usual, not judged", color: "var(--muted)" };
  if (r.this_work <= r.comfort_high) return { label: "comfort zone", color: "var(--low)" };
  return { label: `${(r.this_work / r.comfort_high).toFixed(1)}x the comfort limit`, color: "var(--high)" };
}

/** The deck's "Cost Comparison" panel: this work against the usual range and comfort zone of its peers. */
export function StatisticalEvidence({ result }: { result: AgentResult }) {
  const rows = result.evidence.comparison ?? [];
  const cohort = result.evidence.cohort;
  return (
    <div className="space-y-4">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-xs text-muted text-left border-b border-line">
            <th className="py-2 font-medium">Metric</th>
            <th className="py-2 font-medium text-right">This work</th>
            <th className="py-2 font-medium text-right">Usual range</th>
            <th className="py-2 font-medium text-right">Comfort limit</th>
            <th className="py-2 font-medium text-right">Where it sits</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => {
            const z = zone(r);
            const unit = r.unit === "Rs/m" ? "/m" : "";
            return (
              <tr key={r.metric} className="border-b border-line last:border-0">
                <td className="py-2">{r.metric}</td>
                <td className="py-2 text-right font-semibold">
                  {inr(r.this_work)}
                  {unit}
                </td>
                <td className="py-2 text-right text-muted">
                  {inr(r.typical_low)}–{inr(r.typical_high)}
                  {unit}
                  {r.anchor_low !== undefined && (
                    <div className="text-[11px]">
                      published rates {inr(r.anchor_low)}–{inr(r.anchor_high)}/m
                    </div>
                  )}
                </td>
                <td className="py-2 text-right text-muted">
                  {r.comfort_high != null ? `${inr(r.comfort_high)}${unit}` : "—"}
                </td>
                <td className="py-2 text-right font-semibold" style={{ color: z.color }}>
                  {z.label}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      {cohort && <BandStrip cohort={cohort} value={rows[0]?.this_work} comfort={rows[0]?.comfort_high ?? null} />}
      <p className="text-[11px] text-muted">
        The comfort zone runs from the top of the usual range to the comfort limit: room for a bigger scope or a
        contingency margin. DRISHTI asks a question only above the comfort limit.
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
  if (!value) return null;
  const lv = Math.log10(value);
  const lc = comfort ? Math.log10(comfort) : null;
  const lo = Math.min(cohort.p10 - 0.6, lv - 0.2);
  const hi = Math.max((lc ?? cohort.p90) + 0.3, lv + 0.2);
  const x = (v: number) => ((v - lo) / (hi - lo)) * 100;
  return (
    <div>
      <div className="relative h-10">
        <div className="absolute top-4 h-2 w-full rounded-full bg-line" />
        <div
          className="absolute top-4 h-2 rounded-full"
          style={{ left: `${x(cohort.p10)}%`, width: `${x(cohort.p90) - x(cohort.p10)}%`, background: "color-mix(in srgb, var(--statistical) 45%, white)" }}
        />
        {lc !== null && lc > cohort.p90 && (
          <div
            className="absolute top-4 h-2"
            style={{ left: `${x(cohort.p90)}%`, width: `${x(lc) - x(cohort.p90)}%`, background: "color-mix(in srgb, var(--low) 30%, white)" }}
            title="comfort zone"
          />
        )}
        <div className="absolute top-2.5 h-5 w-0.5 bg-muted" style={{ left: `${x(cohort.p50)}%` }} title="median" />
        {lc !== null && <div className="absolute top-2 h-6 w-0.5" style={{ left: `${x(lc)}%`, background: "var(--high)" }} title="comfort limit" />}
        <div
          className="absolute top-1.5 h-7 w-3 -ml-1.5 rounded"
          style={{ left: `${x(lv)}%`, background: "var(--statistical)" }}
          title="this work"
        />
      </div>
      <div className="flex justify-between text-[11px] text-muted">
        <span>
          shaded: the middle 80% of {cohort.n.toLocaleString("en-IN")} {cohort.description} · green: comfort zone · red line: comfort limit
        </span>
        <span className="font-medium" style={{ color: "var(--statistical)" }}>
          ■ this work
        </span>
      </div>
    </div>
  );
}
