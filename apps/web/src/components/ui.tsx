import Link from "next/link";
import type { Band, WorkRow } from "@/lib/api";
import { agentMeta, BAND_COLOR, BAND_LABEL, inr, workHref, workType } from "@/lib/format";

export function BandBadge({ band, limited }: { band: Band | null; limited?: boolean | null }) {
  if (!band) return <span className="text-xs text-muted">not assessed</span>;
  return (
    <span className="inline-flex items-center gap-1.5 whitespace-nowrap">
      <span
        className="rounded-full px-2.5 py-0.5 text-xs font-semibold text-white"
        style={{ background: BAND_COLOR[band] }}
      >
        {BAND_LABEL[band]}
      </span>
      {limited && band === "LOW" && <span className="text-[11px] text-muted">limited evidence</span>}
    </span>
  );
}

export function SourceBadge({ source }: { source: string }) {
  const map: Record<string, [string, string]> = {
    REAL: ["Real eSAKSHI record", "var(--inputs)"],
    SCENARIO: ["Demo scenario", "var(--reuse)"],
    LIVE: ["Live submission", "var(--fusion)"],
  };
  const [label, color] = map[source] ?? [source, "var(--muted)"];
  return (
    <span className="rounded-md border px-2 py-0.5 text-[11px] font-medium" style={{ color, borderColor: color }}>
      {label}
    </span>
  );
}

export function AgentDots({ alerts }: { alerts: string[] | null }) {
  const list = (alerts ?? []).filter((a) => a !== "validation").map((a) => agentMeta(a));
  return (
    <span className="flex gap-1">
      {list.map((m) => (
        <span key={m.name} title={m.name} className="rounded px-1.5 text-[10px] font-bold text-white" style={{ background: m.color }}>
          {m.n}
        </span>
      ))}
      {alerts?.includes("validation") && (
        <span title="Data Validation" className="rounded px-1.5 text-[10px] font-bold text-white bg-inputs">
          DV
        </span>
      )}
    </span>
  );
}

export function WorkTable({ items, showWhy = true }: { items: WorkRow[]; showWhy?: boolean }) {
  return (
    <div className="card overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-xs text-muted border-b border-line">
            <th className="px-4 py-3 font-medium">Work</th>
            <th className="px-4 py-3 font-medium">District</th>
            <th className="px-4 py-3 font-medium text-right">Amount</th>
            <th className="px-4 py-3 font-medium">Risk</th>
            <th className="px-4 py-3 font-medium">Flagged by</th>
          </tr>
        </thead>
        <tbody>
          {items.map((w) => (
            <tr key={w.work_id} className="border-b border-line last:border-0 hover:bg-background align-top">
              <td className="px-4 py-3 max-w-md">
                <Link href={workHref(w.work_id)} className="font-medium text-navy hover:underline">
                  {workType(w.work_type_code)}
                </Link>
                <div className="text-xs text-muted line-clamp-2">{w.description}</div>
                {showWhy && w.headline && <div className="mt-1 text-xs">{w.headline}</div>}
                {w.case_size && w.case_size > 1 ? (
                  <div className="mt-1 text-xs text-muted">One case: {w.case_size} alike works, shown once</div>
                ) : null}
              </td>
              <td className="px-4 py-3 whitespace-nowrap">
                {w.district_name}
                <div className="text-xs text-muted">{w.state_name}</div>
              </td>
              <td className="px-4 py-3 text-right whitespace-nowrap">{inr(w.amount)}</td>
              <td className="px-4 py-3">
                <BandBadge band={w.band} limited={w.limited} />
              </td>
              <td className="px-4 py-3">
                <AgentDots alerts={w.alerts} />
              </td>
            </tr>
          ))}
          {items.length === 0 && (
            <tr>
              <td colSpan={5} className="px-4 py-10 text-center text-muted">
                Nothing here.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

export function Pager({ page, total, size, onPage }: { page: number; total: number; size: number; onPage: (p: number) => void }) {
  const last = Math.max(1, Math.ceil(total / size));
  return (
    <div className="flex items-center justify-between text-sm text-muted">
      <span>
        {total.toLocaleString("en-IN")} works · page {page} of {last.toLocaleString("en-IN")}
      </span>
      <div className="flex gap-2">
        <button disabled={page <= 1} onClick={() => onPage(page - 1)} className="rounded-lg border border-line px-3 py-1 disabled:opacity-40">
          Previous
        </button>
        <button disabled={page >= last} onClick={() => onPage(page + 1)} className="rounded-lg border border-line px-3 py-1 disabled:opacity-40">
          Next
        </button>
      </div>
    </div>
  );
}
