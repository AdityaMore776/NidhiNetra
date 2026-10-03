"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import type { WorkRow } from "@/lib/api";
import { agentMeta, inr, workHref, workType } from "@/lib/format";
import { Button, BandBadge, Empty, Pill } from "./ui";

/** Which columns the officer wants to see, and whether the table is dense. */
interface Column {
  key: string;
  label: string;
  /** shown by default; the rest can be switched on */
  on?: boolean;
  /** columns that only make sense with a wide screen */
  wide?: boolean;
  align?: "left" | "right";
}

export const WORK_COLUMNS: Column[] = [
  { key: "work", label: "Work", on: true },
  { key: "priority", label: "Priority", align: "right" },
  { key: "band", label: "Risk band", on: true },
  { key: "district", label: "District", on: true },
  { key: "type", label: "Work type", wide: true },
  { key: "amount", label: "Amount", align: "right", on: true },
  { key: "finding", label: "Finding", wide: true },
  { key: "engines", label: "Signals from", on: true },
  { key: "status", label: "Lifecycle", wide: true },
  { key: "checked", label: "Checked", wide: true },
];

function useColumns() {
  const [hidden, setHidden] = useState<string[]>([]);
  const shown = WORK_COLUMNS.filter((c) => (c.on ?? false) || !hidden.includes(c.key));
  const toggle = (key: string) =>
    setHidden((h) => (h.includes(key) ? h.filter((k) => k !== key) : [...h, key]));
  return { shown, toggle, hidden };
}

/** A `select` that adds a filter to the page. Shared by the queue and works list. */
export function FilterSelect({
  label,
  value,
  options,
  onChange,
  className = "",
}: {
  label: string;
  value: string;
  options: { value: string; label: string }[];
  onChange: (v: string) => void;
  className?: string;
}) {
  return (
    <label className={`inline-flex items-center gap-1.5 ${className}`}>
      <span className="text-2xs font-medium uppercase tracking-wide text-muted">{label}</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="field max-w-56 py-1"
      >
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    </label>
  );
}

/** Search box that only fires on submit, so typing does not query on every key. */
export function SearchBox({
  value,
  onSubmit,
  placeholder,
  label,
  className = "",
}: {
  value: string;
  onSubmit: (v: string) => void;
  placeholder: string;
  label: string;
  className?: string;
}) {
  const [text, setText] = useState(value);
  return (
    <form
      className={className}
      role="search"
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit(text.trim());
      }}
    >
      <label className="sr-only" htmlFor="work-search">
        {label}
      </label>
      <div className="flex">
        <input
          id="work-search"
          className="field rounded-r-none"
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder={placeholder}
        />
        <button type="submit" className="field rounded-l-none border-l-0 px-3 font-medium">
          Search
        </button>
      </div>
    </form>
  );
}

/** Show, hide and export the table's columns. */
export function ColumnControls({
  hidden,
  onToggle,
  onExport,
  exportName,
}: {
  hidden: string[];
  onToggle: (key: string) => void;
  onExport?: () => void;
  exportName?: string;
}) {
  return (
    <details className="relative">
      <summary className="inline-flex cursor-pointer list-none items-center gap-1 rounded border border-line-strong bg-surface px-2.5 py-1 text-xs font-medium hover:bg-sunken">
        Columns <span className="text-muted">({WORK_COLUMNS.length - hidden.length})</span>
      </summary>
      <div className="absolute right-0 z-20 mt-1 w-52 rounded border border-line-strong bg-surface p-2 shadow-sm">
        <p className="mb-1 px-1 text-2xs uppercase tracking-wide text-muted">Show columns</p>
        {WORK_COLUMNS.map((c) => (
          <label key={c.key} className="flex items-center gap-2 rounded px-1 py-0.5 text-xs hover:bg-sunken">
            <input
              type="checkbox"
              checked={(c.on ?? false) || !hidden.includes(c.key)}
              onChange={() => onToggle(c.key)}
            />
            {c.label}
          </label>
        ))}
        {onExport && (
          <Button size="sm" variant="ghost" className="mt-2 w-full" onClick={onExport}>
            Download this page as CSV
          </Button>
        )}
      </div>
    </details>
  );
}

/** CSV of exactly the rows on screen, so the file can never be mistaken for the corpus. */
export function toCsv(rows: WorkRow[]): string {
  const head = ["work_id", "district", "work_type", "amount", "status", "band", "score", "signals", "finding"];
  const esc = (v: unknown) => {
    const s = v === null || v === undefined ? "" : String(v);
    return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  return [
    head.join(","),
    ...rows.map((w) =>
      [
        w.work_id,
        [w.district_name, w.state_name].filter(Boolean).join(", "),
        workType(w.work_type_code),
        w.amount ?? "",
        w.status ?? "",
        w.band ?? "",
        w.score ?? "",
        (w.alerts ?? []).join(" "),
        w.headline ?? "",
      ]
        .map(esc)
        .join(","),
    ),
  ].join("\n");
}

export function downloadCsv(name: string, csv: string) {
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${name}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

/**
 * The works table.
 *
 * Every row links to the work's own page, where the evidence is. The table
 * itself only ever states what the engine measured, and says so when a check
 * could not look at the work.
 */
export function WorkTable({
  items,
  showWhy = true,
  emptyTitle = "No works match these filters.",
  emptyBody = "Clear a filter, or widen the search. Nothing has been hidden from you.",
  dense = false,
}: {
  items: WorkRow[];
  showWhy?: boolean;
  emptyTitle?: string;
  emptyBody?: string;
  dense?: boolean;
}) {
  const { shown, toggle, hidden } = useColumns();
  const cell = shown.length;
  return (
    <div className="overflow-x-auto">
      <table className="data-table" style={dense ? { fontSize: "var(--text-sm)" } : undefined}>
        <caption className="sr-only">
          {items.length} works. Each row links to the work's evidence page.
        </caption>
        <thead>
          <tr>
            {shown.map((c) => (
              <th
                key={c.key}
                scope="col"
                className={c.align === "right" ? "text-right" : undefined}
              >
                {c.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {items.map((w) => (
            <tr key={w.work_id}>
              {shown.map((c) => (
                <WorkCell key={c.key} column={c.key} w={w} showWhy={showWhy} />
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {items.length === 0 && <Empty title={emptyTitle} body={emptyBody} />}
      <ColumnSummary hidden={hidden} count={cell} />
    </div>
  );
}

function ColumnSummary({ hidden, count }: { hidden: string[]; count: number }) {
  if (!hidden.length) return null;
  return (
    <p className="border-t border-line px-3 py-1.5 text-2xs text-muted">
      {count} of {WORK_COLUMNS.length} columns shown.
    </p>
  );
}

function WorkCell({ column, w, showWhy }: { column: string; w: WorkRow; showWhy: boolean }) {
  switch (column) {
    case "work":
      return (
        <td className="max-w-sm">
          <Link href={workHref(w.work_id)} className="font-medium text-navy underline-offset-2 hover:underline">
            {workType(w.work_type_code)}
          </Link>
          <div className="tnum text-2xs text-muted">{w.work_id}</div>
          {showWhy && w.description && (
            <div className="mt-0.5 line-clamp-2 text-xs text-secondary">{w.description}</div>
          )}
          {w.case_size && w.case_size > 1 && (
            <div className="mt-1">
              <Pill glyph="≡" title="Alike works grouped into one question, so the queue stays short.">
                {w.case_size} alike works, one case
              </Pill>
            </div>
          )}
        </td>
      );
    case "priority":
      return (
        <td className="tnum text-right text-secondary">
          {w.priority == null ? "—" : w.priority.toFixed(2)}
          <div className="text-2xs text-muted">score × amount</div>
        </td>
      );
    case "band":
      return (
        <td>
          <BandBadge band={w.band} limited={w.limited} />
        </td>
      );
    case "district":
      return (
        <td className="whitespace-nowrap">
          {w.district_name ?? <span className="text-muted">Not recorded</span>}
          <div className="text-2xs text-muted">{w.state_name}</div>
        </td>
      );
    case "type":
      return <td className="text-secondary">{workType(w.work_type_code)}</td>;
    case "amount":
      return <td className="tnum text-right whitespace-nowrap">{inr(w.amount)}</td>;
    case "finding":
      return (
        <td className="max-w-sm text-xs">
          {w.headline ?? <span className="text-muted">No finding recorded.</span>}
        </td>
      );
    case "engines":
      return <SignalChips alerts={w.alerts} />;
    case "status":
      return (
        <td className="whitespace-nowrap text-secondary">
          {w.status ?? <span className="text-muted">—</span>}
        </td>
      );
    case "checked":
      return (
        <td className="whitespace-nowrap text-2xs text-muted">
          {w.recommended_date ? `Recommended ${w.recommended_date}` : "No recommendation date"}
        </td>
      );
    default:
      return <td />;
  }
}

/** Which checks raised a signal, as a word chip with a number, never colour alone. */
export function SignalChips({ alerts }: { alerts: string[] | null }) {
  const list = useMemo(
    () => (alerts ?? []).filter((a) => a !== "validation").map((a) => agentMeta(a)),
    [alerts],
  );
  if (!list.length && !alerts?.includes("validation")) {
    return <span className="text-2xs text-muted">None</span>;
  }
  return (
    <span className="flex flex-wrap gap-1">
      {list.map((m) => (
        <span
          key={m.name}
          title={m.name}
          className="rounded px-1 py-px text-2xs font-medium"
          style={{ color: "var(--foreground)", background: "var(--sunken)", border: `1px solid ${m.color}` }}
        >
          <span className="tnum" style={{ color: m.color }} aria-hidden>
            {m.n}
          </span>{" "}
          <span className="sr-only">{m.name} raised a signal. </span>
          <span aria-hidden>{m.name.split(" ")[0]}</span>
        </span>
      ))}
      {alerts?.includes("validation") && (
        <span
          title="Data Validation"
          className="rounded px-1 py-px text-2xs font-medium"
          style={{ color: "var(--foreground)", background: "var(--sunken)", border: "1px solid var(--inputs)" }}
        >
          <span className="sr-only">Data Validation raised a note. </span>
          <span aria-hidden>Records</span>
        </span>
      )}
    </span>
  );
}

export function Pager({
  page,
  total,
  size,
  onPage,
}: {
  page: number;
  total: number;
  size: number;
  onPage: (p: number) => void;
}) {
  const last = Math.max(1, Math.ceil(total / size));
  const from = total === 0 ? 0 : (page - 1) * size + 1;
  const to = Math.min(page * size, total);
  return (
    <nav
      className="flex flex-wrap items-center justify-between gap-2 text-xs text-muted"
      aria-label="Table pages"
    >
      <span className="tnum">
        {from.toLocaleString("en-IN")}–{to.toLocaleString("en-IN")} of{" "}
        {total.toLocaleString("en-IN")} works · page {page.toLocaleString("en-IN")} of{" "}
        {last.toLocaleString("en-IN")}
      </span>
      <div className="flex gap-1.5">
        <Button size="sm" disabled={page <= 1} onClick={() => onPage(page - 1)}>
          ← Previous
        </Button>
        <Button size="sm" disabled={page >= last} onClick={() => onPage(page + 1)}>
          Next →
        </Button>
      </div>
    </nav>
  );
}
