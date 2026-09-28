"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { IndiaMap } from "@/components/IndiaMap";
import {
  type Column,
  DataTable,
  EmptyState,
  ErrorState,
  LoadingState,
  MetricBlock,
  Panel,
  PanelHeader,
  SearchInput,
  StatusLabel,
} from "@/components/kit";
import { api, type DistrictRow } from "@/lib/api";
import { count, inr } from "@/lib/format";
import { useFetch } from "@/lib/useFetch";

export default function DistrictsPage() {
  const [q, setQ] = useState("");
  const { data, error, loading, reload } = useFetch(() => api<DistrictRow[]>("/dashboard/districts"), []);
  const rows = useMemo(() => data ?? [], [data]);

  const totals = useMemo(() => {
    const works = rows.reduce((s, r) => s + r.works, 0);
    const amount = rows.reduce((s, r) => s + r.amount, 0);
    const review = rows.reduce((s, r) => s + r.review, 0);
    return { works, amount, review, districts: rows.length };
  }, [rows]);

  const filtered = useMemo(() => {
    const needle = q.trim().toLowerCase();
    const list = needle
      ? rows.filter((r) => `${r.name} ${r.state}`.toLowerCase().includes(needle))
      : rows;
    return [...list].sort((a, b) => b.review - a.review);
  }, [rows, q]);

  const columns: Column<DistrictRow>[] = [
    {
      key: "name",
      header: "District",
      sortValue: (r) => r.name,
      cell: (r) => (
        <Link
          href={`/works?district=${encodeURIComponent(r.district_lgd)}`}
          className="font-semibold text-foreground underline-offset-2 hover:underline"
        >
          {r.name}
        </Link>
      ),
    },
    {
      key: "state",
      header: "State",
      hideBelowMd: true,
      sortValue: (r) => r.state,
      cell: (r) => <span className="text-muted">{r.state}</span>,
    },
    {
      key: "works",
      header: "Works",
      align: "right",
      sortValue: (r) => r.works,
      cell: (r) => <span className="tnum">{count(r.works)}</span>,
    },
    {
      key: "amount",
      header: "Amount",
      align: "right",
      hideBelowMd: true,
      sortValue: (r) => r.amount,
      cell: (r) => <span className="tnum whitespace-nowrap">{inr(r.amount)}</span>,
    },
    {
      key: "review",
      header: "In review",
      align: "right",
      sortValue: (r) => r.review,
      cell: (r) => <span className="tnum font-semibold text-medium">{count(r.review)}</span>,
    },
    {
      key: "share",
      header: "Review share",
      align: "right",
      sortValue: (r) => r.share,
      cell: (r) => {
        const tone = r.share >= 0.02 ? "high" : r.share >= 0.008 ? "medium" : "low";
        return (
          <div className="flex items-center justify-end gap-2">
            <div className="hidden h-2 w-20 border border-line bg-surface-2 sm:block">
              <div
                className={tone === "high" ? "h-full bg-high" : tone === "medium" ? "h-full bg-medium" : "h-full bg-low"}
                style={{ width: `${Math.min(100, r.share * 100 * 20)}%` }}
              />
            </div>
            <span className="tnum w-12 text-right">{(r.share * 100).toFixed(2)}%</span>
          </div>
        );
      },
    },
  ];

  if (error) return <ErrorState message={error} onRetry={reload} />;

  return (
    <div className="space-y-6">
      <header className="border-b-2 border-strong pb-4">
        <div className="flex flex-wrap items-center gap-2">
          <h1 className="text-2xl font-bold tracking-tight md:text-3xl">Districts</h1>
          {!loading && <StatusLabel tone="neutral">{count(totals.districts)} districts</StatusLabel>}
        </div>
        <p className="mt-1.5 max-w-3xl text-sm leading-relaxed text-muted">
          Works and review load by district. Open any district to see its works, or click the map.
        </p>
      </header>

      {loading ? (
        <LoadingState label="Loading districts" />
      ) : rows.length === 0 ? (
        <EmptyState title="No districts" message="No district-level works are visible for your role." />
      ) : (
        <>
          <section aria-label="Totals" className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <MetricBlock label="Districts" value={count(totals.districts)} emphasis />
            <MetricBlock label="Works" value={count(totals.works)} />
            <MetricBlock label="Money recommended" value={inr(totals.amount)} />
            <MetricBlock label="In review" value={count(totals.review)} accent="medium" />
          </section>

          <Panel as="section">
            <PanelHeader title="Review load map" desc="Share of works needing review, by district" />
            <div className="p-4">
              <IndiaMap rows={rows} />
            </div>
          </Panel>

          <section className="space-y-3">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <h2 className="text-base font-semibold">District table</h2>
              <div className="sm:w-72">
                <SearchInput
                  value={q}
                  onChange={(e) => setQ(e.target.value)}
                  placeholder="Filter by district or state…"
                  aria-label="Filter districts"
                />
              </div>
            </div>
            <DataTable
              columns={columns}
              rows={filtered}
              getRowKey={(r) => r.district_lgd}
              caption="Districts by review load"
              empty={<EmptyState title="No districts match" message="Try a different search." />}
            />
          </section>
        </>
      )}
    </div>
  );
}
