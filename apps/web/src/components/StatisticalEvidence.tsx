import type { AgentResult } from "@/lib/api";
import { inr } from "@/lib/format";

/** The deck's "Cost Comparison" panel: this work against the typical range of its peers. */
export function StatisticalEvidence({ result }: { result: AgentResult }) {
  const rows = result.evidence.comparison ?? [];
  const cohort = result.evidence.cohort;
  if (rows.length === 0 && !cohort) return null;
  return (
    <div className="space-y-4">
      {rows.length > 0 && (
        <div className="scroll-thin overflow-x-auto border border-line">
          <table className="w-full text-sm">
            <thead className="bg-surface-2">
              <tr className="border-b-2 border-strong">
                <th className="label px-3 py-2 text-left">Metric</th>
                <th className="label px-3 py-2 text-right">This work</th>
                <th className="label px-3 py-2 text-right">Typical range</th>
                <th className="label px-3 py-2 text-right">Deviation</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => {
                const high = r.this_work > r.typical_high;
                const low = r.this_work < r.typical_low;
                const unit = r.unit === "Rs/m" ? "/m" : "";
                return (
                  <tr key={r.metric} className="border-b border-line last:border-0">
                    <td className="px-3 py-2">{r.metric}</td>
                    <td className="tnum px-3 py-2 text-right font-semibold">
                      {inr(r.this_work)}
                      {unit}
                    </td>
                    <td className="tnum px-3 py-2 text-right text-muted">
                      {inr(r.typical_low)}–{inr(r.typical_high)}
                      {unit}
                      {r.anchor_low !== undefined && (
                        <div className="text-[11px]">
                          published {inr(r.anchor_low)}–{inr(r.anchor_high)}/m
                        </div>
                      )}
                    </td>
                    <td
                      className="tnum px-3 py-2 text-right font-semibold"
                      style={{ color: high ? "var(--high)" : low ? "var(--medium)" : "var(--low)" }}
                    >
                      {r.deviation_pct >= 0 ? "▲" : "▼"}{" "}
                      {Math.abs(r.deviation_pct) >= 1000
                        ? `${(r.deviation_pct / 100 + 1).toFixed(1)}×`
                        : `${Math.round(r.deviation_pct)}%`}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
      {cohort && <BandStrip cohort={cohort} value={rows[0]?.this_work} />}
    </div>
  );
}

/** Where this work's cost sits on its peers' log-scale range. Sharp markers, no gauges. */
function BandStrip({ cohort, value }: { cohort: NonNullable<AgentResult["evidence"]["cohort"]>; value?: number }) {
  if (!value) return null;
  const lv = Math.log10(value);
  const lo = Math.min(cohort.p10 - 0.6, lv - 0.2);
  const hi = Math.max(cohort.p90 + 0.6, lv + 0.2);
  const x = (v: number) => ((v - lo) / (hi - lo)) * 100;
  return (
    <div className="border border-line p-3">
      <div className="relative h-9">
        <div className="absolute top-4 h-1.5 w-full bg-surface-2 outline outline-1 outline-line" />
        <div
          className="absolute top-4 h-1.5"
          style={{
            left: `${x(cohort.p10)}%`,
            width: `${x(cohort.p90) - x(cohort.p10)}%`,
            background: "color-mix(in srgb, var(--statistical) 30%, white)",
          }}
        />
        <div className="absolute top-2 h-5 w-0.5 bg-muted" style={{ left: `${x(cohort.p50)}%` }} title="median" />
        <div
          className="absolute top-1 h-7 w-2.5 -ml-1.5"
          style={{ left: `${x(lv)}%`, background: "var(--statistical)" }}
          title="this work"
        />
      </div>
      <div className="mt-1 flex flex-wrap justify-between gap-2 text-[11px] text-muted">
        <span>
          shaded: middle 80% of {cohort.n.toLocaleString("en-IN")} {cohort.description} · line: median{" "}
          {inr(10 ** cohort.p50)}
        </span>
        <span className="font-medium" style={{ color: "var(--statistical)" }}>
          ■ this work
        </span>
      </div>
    </div>
  );
}
