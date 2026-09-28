"use client";

import { IndiaMap } from "@/components/IndiaMap";
import {
  EmptyState,
  ErrorState,
  LinkButton,
  LoadingState,
  MetricBlock,
  Panel,
  PanelHeader,
  SectionHeader,
  StatusLabel,
} from "@/components/kit";
import { WorkTable } from "@/components/ui";
import { api, type DistrictRow, type OfficeRow, type Page, type Summary, type WorkRow } from "@/lib/api";
import { AGENTS, count, inr } from "@/lib/format";
import { useFetch } from "@/lib/useFetch";

export default function Dashboard() {
  const { data, error, loading, reload } = useFetch(
    () =>
      Promise.all([
        api<Summary>("/dashboard/summary"),
        api<DistrictRow[]>("/dashboard/districts"),
        api<Page<WorkRow>>("/queue"),
        api<OfficeRow[]>("/dashboard/offices"),
      ]).then(([summary, districts, queue, offices]) => ({
        s: summary,
        districts,
        top: queue.items.slice(0, 8),
        offices,
      })),
    [],
  );

  if (error) return <ErrorState message={error} onRetry={reload} />;
  if (loading || !data) return <LoadingState label="Loading operational summary" />;

  const { s, districts, top, offices } = data;
  const review = s.bands.HIGH + s.bands.MEDIUM;
  const reviewPct = s.works ? (review / s.works) * 100 : 0;
  const bandRows: { key: keyof Summary["bands"]; label: string; tone: "high" | "medium" | "low" }[] = [
    { key: "HIGH", label: "High", tone: "high" },
    { key: "MEDIUM", label: "Medium", tone: "medium" },
    { key: "LOW", label: "Low", tone: "low" },
  ];
  const maxBand = Math.max(1, s.bands.HIGH, s.bands.MEDIUM, s.bands.LOW);

  return (
    <div className="space-y-8">
      <header className="border-b-2 border-strong pb-4">
        <div className="flex flex-wrap items-center gap-2">
          <h1 className="text-2xl font-bold tracking-tight md:text-3xl">Operational Overview</h1>
          <StatusLabel tone="info">Snapshot {s.snapshot_date}</StatusLabel>
        </div>
        <p className="mt-1.5 max-w-3xl text-sm leading-relaxed text-muted">
          Real MPLADS works from the eSAKSHI public export, each assessed and ranked by how much an officer should verify
          it first. DRISHTI flags — it never accuses.
        </p>
      </header>

      {/* KPI blocks */}
      <section aria-label="Key figures" className="grid grid-cols-2 gap-3 lg:grid-cols-5">
        <MetricBlock label="Total works" value={count(s.works)} sub="assessed" emphasis />
        <MetricBlock label="Money recommended" value={inr(s.amount)} sub="across all works" />
        <MetricBlock
          label="Review queue"
          value={count(review)}
          sub={`${reviewPct.toFixed(2)}% of works`}
          accent="medium"
        />
        <MetricBlock label="High risk" value={count(s.bands.HIGH)} sub="need verification" accent="high" />
        <MetricBlock label="Record issues" value={count(s.validation_alerts)} sub="data validation" accent="info" />
      </section>

      {/* Risk distribution + detection agents */}
      <section className="grid gap-6 lg:grid-cols-5">
        <Panel className="lg:col-span-2" as="section">
          <PanelHeader title="Risk distribution" desc="Works by fused risk band" />
          <div className="space-y-3 p-4">
            {bandRows.map((b) => {
              const n = s.bands[b.key];
              const w = (n / maxBand) * 100;
              return (
                <div key={b.key}>
                  <div className="mb-1 flex items-baseline justify-between text-sm">
                    <span className="flex items-center gap-2">
                      <StatusLabel tone={b.tone} solid>
                        {b.label}
                      </StatusLabel>
                    </span>
                    <span className="tnum font-semibold">
                      {count(n)}
                      <span className="ml-1 text-xs font-normal text-muted">
                        {s.works ? ((n / s.works) * 100).toFixed(2) : "0"}%
                      </span>
                    </span>
                  </div>
                  <div className="h-3 w-full border border-line bg-surface-2">
                    <div
                      className={
                        b.tone === "high" ? "h-full bg-high" : b.tone === "medium" ? "h-full bg-medium" : "h-full bg-low"
                      }
                      style={{ width: `${w}%` }}
                    />
                  </div>
                </div>
              );
            })}
            <p className="border-t border-line pt-3 text-[11px] leading-relaxed text-muted">
              A low score built on a single check is not a clean chit. Such works are marked{" "}
              <strong className="text-foreground">limited evidence</strong> until more checks can look at them.
            </p>
          </div>
        </Panel>

        <Panel className="lg:col-span-3" as="section">
          <PanelHeader
            title="Detection agents"
            desc="Each agent checks one kind of problem, independently"
          />
          <div className="grid grid-cols-1 divide-y divide-line sm:grid-cols-2 sm:divide-y-0">
            {s.agents.map((a, i) => {
              const meta = AGENTS[a.id];
              return (
                <div
                  key={a.id}
                  className={`flex items-start gap-3 p-4 ${i % 2 === 0 ? "sm:border-r sm:border-line" : ""} ${
                    i < s.agents.length - (s.agents.length % 2 === 0 ? 2 : 1) ? "sm:border-b sm:border-line" : ""
                  }`}
                >
                  <span
                    className="tnum mt-0.5 grid h-8 w-8 shrink-0 place-items-center border text-xs font-bold"
                    style={{ borderColor: meta.color, color: meta.color }}
                  >
                    {meta.n}
                  </span>
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-semibold">{meta.name}</span>
                      {a.built ? (
                        <StatusLabel tone="low">Live</StatusLabel>
                      ) : (
                        <StatusLabel tone="neutral">In development</StatusLabel>
                      )}
                    </div>
                    <p className="mt-0.5 text-xs text-muted">{a.question}</p>
                    {a.built && (
                      <p className="tnum mt-1.5 text-sm">
                        <span className="text-lg font-bold">{count(a.alerts)}</span>{" "}
                        <span className="text-muted">works flagged</span>
                      </p>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </Panel>
      </section>

      {/* Map */}
      <Panel as="section">
        <PanelHeader
          title="Geographic distribution"
          desc="Share of works needing review, by district"
          right={<LinkButton href="/districts" variant="ghost">District table</LinkButton>}
        />
        <div className="p-4">
          {districts.length > 0 ? (
            <IndiaMap rows={districts} />
          ) : (
            <EmptyState title="No district data" message="No district-level works are visible for your role." />
          )}
          <p className="mt-2 text-xs text-muted">Click a district to open its works.</p>
        </div>
      </Panel>

      {/* Offices needing checking */}
      {offices.length > 0 && (
        <Panel as="section">
          <PanelHeader
            title="Offices whose completion dates need checking"
            desc="Recorded as completed before recommendation — a record-keeping pattern, listed once per office rather than flooding the queue"
          />
          <div className="scroll-thin overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-surface-2">
                <tr className="border-b-2 border-strong">
                  <th className="label px-4 py-2.5 text-left">Implementing office</th>
                  <th className="label px-4 py-2.5 text-left">District</th>
                  <th className="label px-4 py-2.5 text-right">Dated before recommendation</th>
                  <th className="label px-4 py-2.5 text-right">vs national rate</th>
                </tr>
              </thead>
              <tbody>
                {offices.slice(0, 8).map((o) => (
                  <tr key={o.agency_name} className="border-b border-line last:border-0 hover:bg-surface-2">
                    <td className="px-4 py-3 font-medium">{o.agency_name}</td>
                    <td className="whitespace-nowrap px-4 py-3">
                      {o.district_name}
                      <span className="text-xs text-muted">, {o.state_name}</span>
                    </td>
                    <td className="tnum whitespace-nowrap px-4 py-3 text-right">
                      {count(o.bad)} / {count(o.completed)} ({(o.rate * 100).toFixed(1)}%)
                    </td>
                    <td className="px-4 py-3 text-right">
                      <StatusLabel tone="medium">{o.lift.toFixed(0)}× higher</StatusLabel>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {offices.length > 8 && (
            <p className="border-t border-line px-4 py-2 text-xs text-muted">and {offices.length - 8} more offices.</p>
          )}
        </Panel>
      )}

      {/* Top of queue */}
      <section className="space-y-3">
        <SectionHeader
          title="Top of the review queue"
          desc="Highest-priority works: risk weighted by money at stake"
          right={<LinkButton href="/queue" variant="secondary">Open full queue</LinkButton>}
        />
        <WorkTable
          items={top}
          showRank
          empty={<EmptyState title="Queue is clear" message="No works are currently flagged for review." />}
        />
      </section>
    </div>
  );
}
