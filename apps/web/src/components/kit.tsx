"use client";

/*
  DRISHTI design primitives — the shared, centralised building blocks.
  Everything here is flat, sharp-cornered and border-first by design.
*/
import Link from "next/link";
import { type ReactNode, useMemo, useState } from "react";
import { IconAlert, IconSearch, IconSort } from "./icons";

/* ------------------------------------------------------------------ Panel -- */

export function Panel({
  children,
  className = "",
  as: Tag = "div",
}: {
  children: ReactNode;
  className?: string;
  as?: "div" | "section" | "article";
}) {
  return <Tag className={`bg-surface border border-line ${className}`}>{children}</Tag>;
}

export function PanelHeader({
  title,
  desc,
  right,
  id,
}: {
  title: ReactNode;
  desc?: ReactNode;
  right?: ReactNode;
  id?: string;
}) {
  return (
    <div className="flex items-start justify-between gap-4 border-b border-line px-4 py-3">
      <div className="min-w-0">
        <h2 id={id} className="text-sm font-semibold text-foreground">
          {title}
        </h2>
        {desc && <p className="mt-0.5 text-xs text-muted">{desc}</p>}
      </div>
      {right && <div className="shrink-0">{right}</div>}
    </div>
  );
}

/* ----------------------------------------------------------- Page header -- */

export function PageHeader({
  title,
  lead,
  children,
}: {
  title: string;
  lead?: ReactNode;
  children?: ReactNode;
}) {
  return (
    <div className="flex flex-col gap-3 border-b-2 border-strong pb-4 md:flex-row md:items-end md:justify-between">
      <div className="max-w-3xl">
        <h1 className="text-2xl font-bold tracking-tight text-foreground md:text-3xl">{title}</h1>
        {lead && <p className="mt-1.5 text-sm leading-relaxed text-muted">{lead}</p>}
      </div>
      {children && <div className="flex shrink-0 flex-wrap items-center gap-2">{children}</div>}
    </div>
  );
}

export function SectionHeader({
  title,
  desc,
  right,
}: {
  title: ReactNode;
  desc?: ReactNode;
  right?: ReactNode;
}) {
  return (
    <div className="flex items-end justify-between gap-4">
      <div className="min-w-0">
        <h2 className="text-base font-semibold text-foreground">{title}</h2>
        {desc && <p className="mt-0.5 text-xs text-muted">{desc}</p>}
      </div>
      {right}
    </div>
  );
}

/* -------------------------------------------------------------- Metric -- */

export function MetricBlock({
  label,
  value,
  sub,
  accent,
  emphasis,
}: {
  label: string;
  value: ReactNode;
  sub?: ReactNode;
  accent?: "high" | "medium" | "low" | "info" | "neutral";
  emphasis?: boolean;
}) {
  const bar =
    accent === "high"
      ? "bg-high"
      : accent === "medium"
        ? "bg-medium"
        : accent === "low"
          ? "bg-low"
          : accent === "info"
            ? "bg-info"
            : "bg-strong";
  const valueColor =
    accent === "high"
      ? "text-high"
      : accent === "medium"
        ? "text-medium"
        : accent === "low"
          ? "text-low"
          : accent === "info"
            ? "text-info"
            : "text-foreground";
  return (
    <div className={`relative overflow-hidden border border-line bg-surface p-4 ${emphasis ? "border-strong" : ""}`}>
      <span className={`absolute left-0 top-0 h-full w-1 ${bar}`} aria-hidden />
      <div className="label pl-2">{label}</div>
      <div className={`tnum mt-2 pl-2 text-3xl font-bold leading-none ${valueColor}`}>{value}</div>
      {sub && <div className="mt-1.5 pl-2 text-xs text-muted">{sub}</div>}
    </div>
  );
}

/* ------------------------------------------------------------- Badges -- */

type Tone = "high" | "medium" | "low" | "info" | "neutral";

const TONE: Record<Tone, { fg: string; bg: string; bd: string }> = {
  high: { fg: "text-high", bg: "bg-high-bg", bd: "border-high" },
  medium: { fg: "text-medium", bg: "bg-medium-bg", bd: "border-medium" },
  low: { fg: "text-low", bg: "bg-low-bg", bd: "border-low" },
  info: { fg: "text-info", bg: "bg-info-bg", bd: "border-info" },
  neutral: { fg: "text-foreground", bg: "bg-surface-2", bd: "border-line" },
};

/** Rectangular status label. Meaning is carried by text, never colour alone. */
export function StatusLabel({
  children,
  tone = "neutral",
  solid = false,
  className = "",
}: {
  children: ReactNode;
  tone?: Tone;
  solid?: boolean;
  className?: string;
}) {
  const t = TONE[tone];
  return (
    <span
      className={`inline-flex items-center gap-1 whitespace-nowrap border px-1.5 py-0.5 text-[11px] font-semibold uppercase tracking-wider ${
        solid
          ? tone === "high"
            ? "bg-high text-white border-high"
            : tone === "medium"
              ? "bg-medium text-white border-medium"
              : tone === "low"
                ? "bg-low text-white border-low"
                : tone === "info"
                  ? "bg-info text-white border-info"
                  : "bg-strong text-white border-strong"
          : `${t.fg} ${t.bg} ${t.bd}`
      } ${className}`}
    >
      {children}
    </span>
  );
}

/* --------------------------------------------------------------- Button -- */

type ButtonVariant = "primary" | "secondary" | "danger" | "ghost";

const BTN: Record<ButtonVariant, string> = {
  primary: "bg-strong text-white border-strong hover:bg-black",
  secondary: "bg-surface text-foreground border-strong hover:bg-surface-2",
  danger: "bg-surface text-high border-high hover:bg-high-bg",
  ghost: "bg-transparent text-foreground border-line hover:bg-surface-2",
};

export function Button({
  variant = "secondary",
  className = "",
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: ButtonVariant }) {
  return (
    <button
      className={`inline-flex items-center justify-center gap-2 border px-3.5 py-2 text-sm font-semibold transition-colors disabled:cursor-not-allowed disabled:opacity-40 ${BTN[variant]} ${className}`}
      {...props}
    />
  );
}

export function LinkButton({
  variant = "secondary",
  className = "",
  href,
  children,
}: {
  variant?: ButtonVariant;
  className?: string;
  href: string;
  children: ReactNode;
}) {
  return (
    <Link
      href={href}
      className={`inline-flex items-center justify-center gap-2 border px-3.5 py-2 text-sm font-semibold transition-colors ${BTN[variant]} ${className}`}
    >
      {children}
    </Link>
  );
}

/* --------------------------------------------------------- Form controls -- */

export function Field({ label, htmlFor, children }: { label: string; htmlFor?: string; children: ReactNode }) {
  return (
    <label htmlFor={htmlFor} className="flex flex-col gap-1">
      <span className="label">{label}</span>
      {children}
    </label>
  );
}

export function TextInput({ className = "", ...props }: React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={`h-9 w-full border border-line bg-surface px-2.5 text-sm text-foreground placeholder:text-faint focus:border-info ${className}`}
      {...props}
    />
  );
}

export function SearchInput({ className = "", ...props }: React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <div className={`relative ${className}`}>
      <IconSearch className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-muted" />
      <input
        className="h-9 w-full border border-line bg-surface pl-9 pr-2.5 text-sm text-foreground placeholder:text-faint focus:border-info"
        {...props}
      />
    </div>
  );
}

export function Select({ className = "", children, ...props }: React.SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      className={`h-9 w-full appearance-none border border-line bg-surface bg-[length:16px] bg-[right_0.5rem_center] bg-no-repeat pl-2.5 pr-8 text-sm text-foreground focus:border-info ${className}`}
      style={{
        backgroundImage:
          "url(\"data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 24 24' fill='none' stroke='%23555' stroke-width='2'><path d='M6 9l6 6 6-6'/></svg>\")",
      }}
      {...props}
    >
      {children}
    </select>
  );
}

/** A horizontal bar of filter controls that stacks on small screens. */
export function FilterBar({ children }: { children: ReactNode }) {
  return (
    <div className="flex flex-col gap-3 border border-line bg-surface p-3 sm:flex-row sm:flex-wrap sm:items-end">
      {children}
    </div>
  );
}

/** Segmented button group (e.g. risk-band quick filter). */
export function SegmentedControl<T extends string>({
  label,
  options,
  value,
  onChange,
}: {
  label: string;
  options: { value: T; label: string }[];
  value: T;
  onChange: (v: T) => void;
}) {
  return (
    <div className="flex flex-col gap-1">
      <span className="label">{label}</span>
      <div role="group" aria-label={label} className="flex border border-line">
        {options.map((o, i) => {
          const active = o.value === value;
          return (
            <button
              key={o.value}
              type="button"
              aria-pressed={active}
              onClick={() => onChange(o.value)}
              className={`px-3 py-1.5 text-sm font-semibold transition-colors ${
                i > 0 ? "border-l border-line" : ""
              } ${active ? "bg-strong text-white" : "bg-surface text-muted hover:bg-surface-2"}`}
            >
              {o.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------ States -- */

export function LoadingState({ label = "Loading" }: { label?: string }) {
  return (
    <div
      role="status"
      aria-live="polite"
      className="flex items-center gap-3 border border-line bg-surface px-4 py-8 text-sm text-muted"
    >
      <span className="inline-block h-3 w-3 animate-pulse bg-strong" aria-hidden />
      {label}…
    </div>
  );
}

export function SkeletonRows({ rows = 6, cols = 5 }: { rows?: number; cols?: number }) {
  return (
    <div className="border border-line bg-surface" aria-hidden>
      {Array.from({ length: rows }).map((_, r) => (
        <div key={r} className="flex gap-4 border-b border-line px-4 py-3 last:border-0">
          {Array.from({ length: cols }).map((_, c) => (
            <div key={c} className="h-4 flex-1 animate-pulse bg-line" />
          ))}
        </div>
      ))}
    </div>
  );
}

export function EmptyState({
  title,
  message,
  action,
}: {
  title: string;
  message?: string;
  action?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center gap-3 border border-dashed border-line bg-surface px-6 py-12 text-center">
      <div className="text-sm font-semibold uppercase tracking-wider text-foreground">{title}</div>
      {message && <p className="max-w-sm text-sm text-muted">{message}</p>}
      {action}
    </div>
  );
}

export function ErrorState({
  title = "Data could not be loaded",
  message,
  onRetry,
}: {
  title?: string;
  message?: string;
  onRetry?: () => void;
}) {
  return (
    <div
      role="alert"
      className="flex flex-col items-start gap-3 border-2 border-high bg-high-bg px-4 py-4 text-sm"
    >
      <div className="flex items-center gap-2 font-semibold uppercase tracking-wider text-high">
        <IconAlert className="text-high" />
        {title}
      </div>
      {message && <p className="text-foreground">{message}</p>}
      {onRetry && (
        <Button variant="danger" onClick={onRetry} className="bg-white">
          Retry
        </Button>
      )}
    </div>
  );
}

/* ---------------------------------------------------------- Pagination -- */

export function Pagination({
  page,
  total,
  size,
  onPage,
  unit = "records",
}: {
  page: number;
  total: number;
  size: number;
  onPage: (p: number) => void;
  unit?: string;
}) {
  const last = Math.max(1, Math.ceil(total / size));
  const from = total === 0 ? 0 : (page - 1) * size + 1;
  const to = Math.min(total, page * size);
  return (
    <nav
      aria-label="Pagination"
      className="flex flex-col gap-2 border border-line bg-surface px-4 py-2.5 text-sm text-muted sm:flex-row sm:items-center sm:justify-between"
    >
      <span className="tnum">
        {from.toLocaleString("en-IN")}–{to.toLocaleString("en-IN")} of{" "}
        <span className="font-semibold text-foreground">{total.toLocaleString("en-IN")}</span> {unit}
      </span>
      <div className="flex items-center gap-2">
        <span className="tnum hidden sm:inline">
          Page {page.toLocaleString("en-IN")} / {last.toLocaleString("en-IN")}
        </span>
        <Button variant="ghost" disabled={page <= 1} onClick={() => onPage(page - 1)} aria-label="Previous page">
          Prev
        </Button>
        <Button variant="ghost" disabled={page >= last} onClick={() => onPage(page + 1)} aria-label="Next page">
          Next
        </Button>
      </div>
    </nav>
  );
}

/* ----------------------------------------------------------- DataTable -- */

export interface Column<T> {
  key: string;
  header: string;
  align?: "left" | "right" | "center";
  sortValue?: (row: T) => number | string | null | undefined;
  cell: (row: T) => ReactNode;
  className?: string;
  headClassName?: string;
  /** Hide on narrow viewports (below md). */
  hideBelowMd?: boolean;
}

/**
 * Accessible, sortable data table with sticky header and built-in states.
 * Sorting acts on the currently loaded rows (server pagination stays authoritative).
 */
export function DataTable<T>({
  columns,
  rows,
  getRowKey,
  caption,
  loading,
  error,
  onRetry,
  empty,
  maxHeightClass = "",
}: {
  columns: Column<T>[];
  rows: T[];
  getRowKey: (row: T) => string;
  caption?: string;
  loading?: boolean;
  error?: string | null;
  onRetry?: () => void;
  empty?: ReactNode;
  maxHeightClass?: string;
}) {
  const [sort, setSort] = useState<{ key: string; dir: 1 | -1 } | null>(null);

  const sorted = useMemo(() => {
    if (!sort) return rows;
    const col = columns.find((c) => c.key === sort.key);
    if (!col?.sortValue) return rows;
    const get = col.sortValue;
    return [...rows].sort((a, b) => {
      const av = get(a);
      const bv = get(b);
      if (av == null && bv == null) return 0;
      if (av == null) return 1;
      if (bv == null) return -1;
      if (typeof av === "number" && typeof bv === "number") return (av - bv) * sort.dir;
      return String(av).localeCompare(String(bv)) * sort.dir;
    });
  }, [rows, sort, columns]);

  if (error) return <ErrorState message={error} onRetry={onRetry} />;
  if (loading) return <SkeletonRows cols={columns.length} />;

  function toggleSort(key: string) {
    setSort((s) => (s?.key === key ? (s.dir === 1 ? { key, dir: -1 } : null) : { key, dir: 1 }));
  }

  const align = (a?: string) => (a === "right" ? "text-right" : a === "center" ? "text-center" : "text-left");

  return (
    <div className={`scroll-thin overflow-x-auto border border-line bg-surface ${maxHeightClass}`}>
      <table className="w-full border-collapse text-sm">
        {caption && <caption className="sr-only">{caption}</caption>}
        <thead className="sticky top-0 z-10 bg-surface-2">
          <tr className="border-b-2 border-strong">
            {columns.map((c) => {
              const isSorted = sort?.key === c.key;
              return (
                <th
                  key={c.key}
                  scope="col"
                  aria-sort={isSorted ? (sort!.dir === 1 ? "ascending" : "descending") : "none"}
                  className={`label whitespace-nowrap px-3 py-2.5 font-semibold ${align(c.align)} ${
                    c.hideBelowMd ? "hidden md:table-cell" : ""
                  } ${c.headClassName ?? ""}`}
                >
                  {c.sortValue ? (
                    <button
                      type="button"
                      onClick={() => toggleSort(c.key)}
                      className="inline-flex items-center gap-1 uppercase tracking-wider hover:text-foreground"
                    >
                      {c.header}
                      <IconSort
                        width={13}
                        height={13}
                        className={isSorted ? "text-foreground" : "text-faint"}
                      />
                    </button>
                  ) : (
                    c.header
                  )}
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody>
          {sorted.length === 0 && (
            <tr>
              <td colSpan={columns.length} className="px-4 py-12">
                {empty ?? <EmptyState title="No records" message="Nothing matches the current view." />}
              </td>
            </tr>
          )}
          {sorted.map((row) => (
            <tr
              key={getRowKey(row)}
              className="group border-b border-line align-top last:border-0 hover:bg-surface-2"
            >
              {columns.map((c) => (
                <td
                  key={c.key}
                  className={`px-3 py-3 ${align(c.align)} ${c.hideBelowMd ? "hidden md:table-cell" : ""} ${
                    c.className ?? ""
                  }`}
                >
                  {c.cell(row)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
