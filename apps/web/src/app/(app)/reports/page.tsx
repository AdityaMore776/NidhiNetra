"use client";

import {
  Button,
  ErrorState,
  LoadingState,
  MetricBlock,
  Panel,
  PanelHeader,
  StatusLabel,
} from "@/components/kit";
import { api, type DistrictRow, type OfficeRow, type Summary } from "@/lib/api";
import { AGENTS, count, inr } from "@/lib/format";
import { useFetch } from "@/lib/useFetch";

export default function ReportsPage() {
  const { data, error, loading, reload } = useFetch(
    () =>
      Promise.all([
        api<Summary>("/dashboard/summary"),
        api<DistrictRow[]>("/dashboard/districts"),
        api<OfficeRow[]>("/dashboard/offices"),
      ]).then(([s, districts, offices]) => ({ s, districts, offices })),
    [],
  );

  if (error) return <ErrorState message={error} onRetry={reload} />;
  if (loading || !data) return <LoadingState label="Compiling report" />;

  const { s, districts, offices } = data;
  const review = s.bands.HIGH + s.bands.MEDIUM;
  const topDistricts = [...districts].sort((a, b) => b.share - a.share).slice(0, 15);
  const bandRows: { key: keyof Summary["bands"]; label: string; tone: "high" | "medium" | "low" }[] = [
    { key: "HIGH", label: "High", tone: "high" },
    { key: "MEDIUM", label: "Medium", tone: "medium" },
    { key: "LOW", label: "Low", tone: "low" },
  ];

  return (
    <div className="space-y-6">
      <header className="flex flex-col gap-3 border-b-2 border-strong pb-4 md:flex-row md:items-end md:justify-between print:border-black">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight md:text-3xl">Assessment Report</h1>
            <StatusLabel tone="info">Snapshot {s.snapshot_date}</StatusLabel>
          </div>
          <p className="mt-1.5 max-w-3xl text-sm leading-relaxed text-muted">
            A tabular summary of every assessed work in your scope. All figures come directly from the engine.
          </p>
        </div>
        <Button variant="secondary" onClick={() => window.print()} className="print:hidden">
          Print / export
        </Button>
      </header>

      <section aria-label="Headline figures" className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <MetricBlock label="Total works" value={count(s.works)} emphasis />
        <MetricBlock label="Money recommended" value={inr(s.amount)} />
        <MetricBlock label="Need review" value={count(review)} accent="medium" />
        <MetricBlock label="High risk" value={count(s.bands.HIGH)} accent="high" />
      </section>

      {/* Risk distribution */}
      <Panel as="section">
        <PanelHeader title="Risk distribution" desc="All assessed works by fused risk band" />
        <div className="scroll-thin overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-surface-2">
              <tr className="border-b-2 border-strong">
                <th className="label px-4 py-2.5 text-left">Band</th>
                <th className="label px-4 py-2.5 text-right">Works</th>
                <th className="label px-4 py-2.5 text-right">Share</th>
                <th className="label px-4 py-2.5 text-left">Distribution</th>
              </tr>
            </thead>
            <tbody>
              {bandRows.map((b) => {
                const n = s.bands[b.key];
                const share = s.works ? (n / s.works) * 100 : 0;
                return (
                  <tr key={b.key} className="border-b border-line last:border-0">
                    <td className="px-4 py-2.5">
                      <StatusLabel tone={b.tone} solid>
                        {b.label}
                      </StatusLabel>
                    </td>
                    <td className="tnum px-4 py-2.5 text-right font-semibold">{count(n)}</td>
                    <td className="tnum px-4 py-2.5 text-right">{share.toFixed(2)}%</td>
                    <td className="px-4 py-2.5">
                      <div className="h-2.5 w-full max-w-xs border border-line bg-surface-2">
                        <div
                          className={
                            b.tone === "high" ? "h-full bg-high" : b.tone === "medium" ? "h-full bg-medium" : "h-full bg-low"
                          }
                          style={{ width: `${share}%` }}
                        />
                      </div>
                    </td>
                  </tr>
                );
              })}
              <tr className="border-t-2 border-strong bg-surface-2">
                <td className="label px-4 py-2.5">Total assessed</td>
                <td className="tnum px-4 py-2.5 text-right font-bold">{count(s.works)}</td>
                <td className="tnum px-4 py-2.5 text-right">100%</td>
                <td />
              </tr>
            </tbody>
          </table>
        </div>
      </Panel>

      {/* Agent coverage */}
      <Panel as="section">
        <PanelHeader title="Detection agents" desc="Coverage and findings by agent" />
        <div className="scroll-thin overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-surface-2">
              <tr className="border-b-2 border-strong">
                <th className="label px-4 py-2.5 text-left">Agent</th>
                <th className="label px-4 py-2.5 text-left">Question</th>
                <th className="label px-4 py-2.5 text-left">Status</th>
                <th className="label px-4 py-2.5 text-right">Works flagged</th>
              </tr>
            </thead>
            <tbody>
              {s.agents.map((a) => (
                <tr key={a.id} className="border-b border-line last:border-0">
                  <td className="px-4 py-2.5">
                    <span className="flex items-center gap-2">
                      <span
                        className="tnum grid h-6 w-6 place-items-center border text-[11px] font-bold"
                        style={{ borderColor: AGENTS[a.id].color, color: AGENTS[a.id].color }}
                      >
                        {AGENTS[a.id].n}
                      </span>
                      <span className="font-medium">{a.name}</span>
                    </span>
                  </td>
                  <td className="px-4 py-2.5 text-muted">{a.question}</td>
                  <td className="px-4 py-2.5">
                    {a.built ? <StatusLabel tone="low">Live</StatusLabel> : <StatusLabel tone="neutral">In development</StatusLabel>}
                  </td>
                  <td className="tnum px-4 py-2.5 text-right font-semibold">{a.built ? count(a.alerts) : "—"}</td>
                </tr>
              ))}
              <tr className="border-t border-line">
                <td className="px-4 py-2.5 font-medium">Data validation</td>
                <td className="px-4 py-2.5 text-muted">Record checks: impossible dates, prohibited-work notes</td>
                <td className="px-4 py-2.5">
                  <StatusLabel tone="low">Live</StatusLabel>
                </td>
                <td className="tnum px-4 py-2.5 text-right font-semibold">{count(s.validation_alerts)}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </Panel>

      {/* Districts by review share */}
      {topDistricts.length > 0 && (
        <Panel as="section">
          <PanelHeader title="Districts by review share" desc="Highest concentration of works needing review" />
          <div className="scroll-thin overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-surface-2">
                <tr className="border-b-2 border-strong">
                  <th className="label px-4 py-2.5 text-left">#</th>
                  <th className="label px-4 py-2.5 text-left">District</th>
                  <th className="label px-4 py-2.5 text-right">Works</th>
                  <th className="label px-4 py-2.5 text-right">In review</th>
                  <th className="label px-4 py-2.5 text-right">Share</th>
                </tr>
              </thead>
              <tbody>
                {topDistricts.map((d, i) => (
                  <tr key={d.district_lgd} className="border-b border-line last:border-0">
                    <td className="tnum px-4 py-2.5 text-muted">{String(i + 1).padStart(2, "0")}</td>
                    <td className="px-4 py-2.5 font-medium">
                      {d.name}
                      <span className="text-xs text-muted">, {d.state}</span>
                    </td>
                    <td className="tnum px-4 py-2.5 text-right">{count(d.works)}</td>
                    <td className="tnum px-4 py-2.5 text-right font-semibold text-medium">{count(d.review)}</td>
                    <td className="tnum px-4 py-2.5 text-right">{(d.share * 100).toFixed(2)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>
      )}

      {/* Offices */}
      {offices.length > 0 && (
        <Panel as="section">
          <PanelHeader
            title="Offices whose completion dates need checking"
            desc="Recorded as completed before recommendation — a record-keeping pattern"
          />
          <div className="scroll-thin overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-surface-2">
                <tr className="border-b-2 border-strong">
                  <th className="label px-4 py-2.5 text-left">Office</th>
                  <th className="label px-4 py-2.5 text-left">District</th>
                  <th className="label px-4 py-2.5 text-right">Before recommendation</th>
                  <th className="label px-4 py-2.5 text-right">vs national</th>
                </tr>
              </thead>
              <tbody>
                {offices.map((o) => (
                  <tr key={o.agency_name} className="border-b border-line last:border-0">
                    <td className="px-4 py-2.5 font-medium">{o.agency_name}</td>
                    <td className="whitespace-nowrap px-4 py-2.5">
                      {o.district_name}
                      <span className="text-xs text-muted">, {o.state_name}</span>
                    </td>
                    <td className="tnum whitespace-nowrap px-4 py-2.5 text-right">
                      {count(o.bad)} / {count(o.completed)} ({(o.rate * 100).toFixed(1)}%)
                    </td>
                    <td className="px-4 py-2.5 text-right">
                      <StatusLabel tone="medium">{o.lift.toFixed(0)}× higher</StatusLabel>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>
      )}

      <p className="text-[11px] text-muted">
        DRISHTI flags works that need verification; it never accuses. Findings are leads for an officer to check.
      </p>
    </div>
  );
}
