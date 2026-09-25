import type { AgentResult } from "@/lib/api";
import { inr } from "@/lib/format";

/** The deck's "Cost Comparison" panel: this work against the typical range of its peers. */
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
            <th className="py-2 font-medium text-right">Typical range</th>
            <th className="py-2 font-medium text-right">Deviation</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => {
            const high = r.this_work > r.typical_high;
            const low = r.this_work < r.typical_low;
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
                <td className="py-2 text-right font-semibold" style={{ color: high ? "var(--high)" : low ? "var(--medium)" : "var(--low)" }}>
                  {r.deviation_pct >= 0 ? "▲" : "▼"} {Math.abs(r.deviation_pct) >= 1000 ? `${(r.deviation_pct / 100 + 1).toFixed(1)}x` : `${Math.round(r.deviation_pct)}%`}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      {cohort && <BandStrip cohort={cohort} value={rows[0]?.this_work} />}
    </div>
  );
}

/** Where this work's cost sits on its peers' log-scale range. */
function BandStrip({ cohort, value }: { cohort: NonNullable<AgentResult["evidence"]["cohort"]>; value?: number }) {
  if (!value) return null;
  const lv = Math.log10(value);
  const lo = Math.min(cohort.p10 - 0.6, lv - 0.2);
  const hi = Math.max(cohort.p90 + 0.6, lv + 0.2);
  const x = (v: number) => ((v - lo) / (hi - lo)) * 100;
  return (
    <div>
      <div className="relative h-10">
        <div className="absolute top-4 h-2 w-full rounded-full bg-line" />
        <div
          className="absolute top-4 h-2 rounded-full"
          style={{ left: `${x(cohort.p10)}%`, width: `${x(cohort.p90) - x(cohort.p10)}%`, background: "color-mix(in srgb, var(--statistical) 45%, white)" }}
        />
        <div className="absolute top-2.5 h-5 w-0.5 bg-muted" style={{ left: `${x(cohort.p50)}%` }} title="median" />
        <div
          className="absolute top-1.5 h-7 w-3 -ml-1.5 rounded"
          style={{ left: `${x(lv)}%`, background: "var(--statistical)" }}
          title="this work"
        />
      </div>
      <div className="flex justify-between text-[11px] text-muted">
        <span>
          shaded: the middle 80% of {cohort.n.toLocaleString("en-IN")} {cohort.description} · line: median {inr(10 ** cohort.p50)}
        </span>
        <span className="font-medium" style={{ color: "var(--statistical)" }}>
          ■ this work
        </span>
      </div>
    </div>
  );
}
