"use client";

import Link from "next/link";
import type { Band, WorkRow } from "@/lib/api";
import { AGENTS, BAND_LABEL, BAND_TONE, inr, workHref, workType } from "@/lib/format";
import { IconArrowRight } from "./icons";
import { type Column, DataTable, StatusLabel } from "./kit";

/** Risk band as a rectangular, text-labelled badge. */
export function BandBadge({ band, limited }: { band: Band | null; limited?: boolean | null }) {
  if (!band) return <span className="text-xs text-muted">Not assessed</span>;
  return (
    <span className="inline-flex items-center gap-1.5 whitespace-nowrap">
      <StatusLabel tone={BAND_TONE[band]} solid>
        {BAND_LABEL[band]}
      </StatusLabel>
      {limited && band === "LOW" && <span className="text-[11px] text-muted">limited</span>}
    </span>
  );
}

export function SourceBadge({ source }: { source: string }) {
  const map: Record<string, string> = {
    REAL: "Real eSAKSHI record",
    SCENARIO: "Demo scenario",
    LIVE: "Live submission",
  };
  return <StatusLabel tone="neutral">{map[source] ?? source}</StatusLabel>;
}

/** Compact square codes for the agents (and DV) that flagged a work. */
export function AgentDots({ alerts }: { alerts: string[] | null }) {
  const list = (alerts ?? []).filter((a) => a in AGENTS) as (keyof typeof AGENTS)[];
  const hasValidation = alerts?.includes("validation");
  if (list.length === 0 && !hasValidation) return <span className="text-xs text-muted">—</span>;
  return (
    <span className="flex flex-wrap gap-1">
      {list.map((a) => (
        <span
          key={a}
          title={`${AGENTS[a].name} agent`}
          className="tnum border border-line bg-surface-2 px-1.5 text-[11px] font-bold text-foreground"
        >
          {AGENTS[a].n}
        </span>
      ))}
      {hasValidation && (
        <span
          title="Data Validation"
          className="border border-info bg-info-bg px-1.5 text-[11px] font-bold uppercase text-info"
        >
          DV
        </span>
      )}
    </span>
  );
}

/** The primary works table. Priority-ranked, dense, sortable on the loaded page. */
export function WorkTable({
  items,
  loading,
  error,
  onRetry,
  showRank = false,
  showFinding = true,
  empty,
}: {
  items: WorkRow[];
  loading?: boolean;
  error?: string | null;
  onRetry?: () => void;
  showRank?: boolean;
  showFinding?: boolean;
  empty?: React.ReactNode;
}) {
  const columns: Column<WorkRow>[] = [];

  if (showRank) {
    columns.push({
      key: "rank",
      header: "#",
      align: "right",
      className: "tnum text-muted w-10",
      headClassName: "w-10",
      cell: (_w) => {
        const i = items.indexOf(_w);
        return String(i + 1).padStart(2, "0");
      },
    });
  }

  columns.push(
    {
      key: "score",
      header: "Score",
      align: "right",
      sortValue: (w) => w.score ?? -1,
      cell: (w) =>
        w.score == null ? (
          <span className="text-muted">—</span>
        ) : (
          <span
            className={`tnum text-base font-bold ${
              w.band === "HIGH" ? "text-high" : w.band === "MEDIUM" ? "text-medium" : "text-low"
            }`}
          >
            {Math.round(w.score * 100)}
          </span>
        ),
    },
    {
      key: "work",
      header: "Work",
      sortValue: (w) => workType(w.work_type_code),
      cell: (w) => (
        <div className="max-w-md">
          <Link
            href={workHref(w.work_id)}
            className="font-semibold text-foreground underline-offset-2 hover:underline focus-visible:underline"
          >
            {workType(w.work_type_code)}
          </Link>
          <div className="tnum text-[11px] text-muted">{w.work_id}</div>
          {w.description && <div className="mt-0.5 line-clamp-1 text-xs text-muted">{w.description}</div>}
        </div>
      ),
    },
    {
      key: "district",
      header: "District",
      hideBelowMd: true,
      sortValue: (w) => w.district_name ?? "",
      cell: (w) => (
        <div className="whitespace-nowrap">
          <div>{w.district_name ?? "—"}</div>
          <div className="text-[11px] text-muted">{w.state_name}</div>
        </div>
      ),
    },
    {
      key: "amount",
      header: "Amount",
      align: "right",
      sortValue: (w) => w.amount ?? -1,
      cell: (w) => <span className="tnum whitespace-nowrap">{inr(w.amount)}</span>,
    },
    {
      key: "band",
      header: "Risk band",
      sortValue: (w) => (w.band === "HIGH" ? 3 : w.band === "MEDIUM" ? 2 : w.band === "LOW" ? 1 : 0),
      cell: (w) => <BandBadge band={w.band} limited={w.limited} />,
    },
  );

  if (showFinding) {
    columns.push({
      key: "finding",
      header: "Primary finding",
      hideBelowMd: true,
      cell: (w) =>
        w.headline ? <span className="text-xs text-foreground">{w.headline}</span> : <span className="text-muted">—</span>,
    });
  }

  columns.push(
    {
      key: "flagged",
      header: "Flagged by",
      cell: (w) => <AgentDots alerts={w.alerts} />,
    },
    {
      key: "__go",
      header: "",
      align: "right",
      cell: (w) => (
        <a
          href={workHref(w.work_id)}
          aria-label={`Open ${workType(w.work_type_code)} ${w.work_id}`}
          className="inline-flex text-muted hover:text-foreground"
        >
          <IconArrowRight />
        </a>
      ),
    },
  );

  return (
    <DataTable
      columns={columns}
      rows={items}
      getRowKey={(w) => w.work_id}
      caption="Works ranked by review priority"
      loading={loading}
      error={error}
      onRetry={onRetry}
      empty={empty}
    />
  );
}

// Back-compat pager wrapper (pages now use Pagination from kit directly).
export { Pagination as Pager } from "./kit";
