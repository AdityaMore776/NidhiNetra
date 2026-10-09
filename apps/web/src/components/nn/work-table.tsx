"use client";

import { ArrowUpRight, ChevronLeft, ChevronRight, Layers } from "lucide-react";
import { motion, useReducedMotion } from "motion/react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import type { WorkRow } from "@/lib/api";
import { agentMeta, BAND_COLOR, inr, workHref, workType } from "@/lib/format";
import { cn } from "@/lib/utils";
import { BandBadge, EngineChips } from "./badges";

/** Works as rows: what it is, where, how much, the band and which engines raised it. */
export function WorkTable({
  items,
  showWhy = true,
  loading = false,
  rank = false,
  start = 0,
  emptyText = "Nothing here.",
}: {
  items: WorkRow[];
  showWhy?: boolean;
  loading?: boolean;
  rank?: boolean;
  /** rank of the first row minus one (for later pages) */
  start?: number;
  emptyText?: string;
}) {
  const router = useRouter();
  const reduce = useReducedMotion();
  return (
    <div className="panel overflow-hidden">
      {/* T143: on a phone each work is a card, every column readable without sideways scrolling */}
      <ul className="divide-y md:hidden">
        {loading &&
          Array.from({ length: 4 }).map((_, i) => (
            <li key={`s${i}`} className="px-4 py-4">
              <div className="h-4 w-2/3 rounded-md skeleton-shimmer" />
              <div className="mt-2 h-3 w-1/2 rounded-md skeleton-shimmer" />
            </li>
          ))}
        {!loading &&
          items.map((w, i) => (
            <li key={w.work_id} className="relative">
              <span className="absolute left-0 top-0 h-full w-[3px]" style={{ background: w.band ? BAND_COLOR[w.band] : "var(--border)" }} />
              <Link href={workHref(w.work_id)} className="block px-4 py-3.5 active:bg-brand-50/70">
                <div className="flex items-start gap-2">
                  {rank && <span className="num mt-0.5 font-mono text-xs text-subtle-foreground">{String(start + i + 1).padStart(2, "0")}</span>}
                  <span className="min-w-0 flex-1 font-medium text-brand-900">{workType(w.work_type_code)}</span>
                  <BandBadge band={w.band} limited={w.limited} />
                </div>
                <div className="mt-0.5 line-clamp-2 text-xs text-muted-foreground">{w.description}</div>
                <div className="mt-1.5 flex flex-wrap items-baseline gap-x-2 text-xs">
                  <span className="font-medium">{w.district_name ?? "—"}</span>
                  <span className="text-muted-foreground">{w.state_name}</span>
                  <span className="num ml-auto text-sm font-semibold">{inr(w.amount)}</span>
                </div>
                {showWhy && w.headline && (
                  <div className="mt-2 rounded-lg border-l-2 border-brand-200 bg-muted/70 px-2.5 py-1.5 text-xs leading-relaxed text-foreground/80">
                    <p className="line-clamp-3">{w.headline}</p>
                  </div>
                )}
                <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1">
                  <AgentNames alerts={w.alerts} />
                  {w.case_size && w.case_size > 1 ? (
                    <span className="inline-flex items-center gap-1 text-[11px] text-muted-foreground">
                      <Layers className="size-3" /> One case: {w.case_size} alike works
                    </span>
                  ) : null}
                </div>
              </Link>
            </li>
          ))}
        {!loading && items.length === 0 && <li className="px-5 py-12 text-center text-sm text-muted-foreground">{emptyText}</li>}
      </ul>
      <div className="hidden overflow-x-auto md:block">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b bg-muted/60 text-left">
              {rank && <th className="w-12 py-3 pl-5 eyebrow">#</th>}
              <th className={cn("py-3 eyebrow", rank ? "pl-2" : "pl-5")}>Work</th>
              <th className="px-4 py-3 eyebrow">District</th>
              <th className="px-4 py-3 text-right eyebrow">Amount</th>
              <th className="px-4 py-3 eyebrow">Risk</th>
              <th className="py-3 pl-4 pr-5 eyebrow">Raised by</th>
            </tr>
          </thead>
          <tbody>
            {loading &&
              Array.from({ length: 6 }).map((_, i) => (
                <tr key={`s${i}`} className="border-b last:border-0">
                  <td colSpan={rank ? 6 : 5} className="px-5 py-4">
                    <div className="h-4 w-2/3 rounded-md skeleton-shimmer" />
                    <div className="mt-2 h-3 w-1/2 rounded-md skeleton-shimmer" />
                  </td>
                </tr>
              ))}
            {!loading &&
              items.map((w, i) => (
                <motion.tr
                  key={w.work_id}
                  initial={reduce ? false : { opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.4, delay: Math.min(i, 12) * 0.035, ease: [0.22, 1, 0.36, 1] }}
                  onClick={() => router.push(workHref(w.work_id))}
                  className="group relative cursor-pointer border-b align-top transition-colors last:border-0 hover:bg-brand-50/70"
                >
                  {rank && (
                    <td className="py-4 pl-5">
                      <span className="num font-mono text-xs text-subtle-foreground">{String(start + i + 1).padStart(2, "0")}</span>
                    </td>
                  )}
                  <td className={cn("max-w-md py-4 pr-4", rank ? "pl-2" : "pl-5")}>
                    <span
                      className="absolute left-0 top-0 h-full w-[3px] origin-top scale-y-0 transition-transform duration-300 group-hover:scale-y-100"
                      style={{ background: w.band ? BAND_COLOR[w.band] : "var(--border)" }}
                    />
                    <Link
                      href={workHref(w.work_id)}
                      onClick={(e) => e.stopPropagation()}
                      className="inline-flex items-center gap-1 font-medium text-brand-900 underline-offset-4 group-hover:underline"
                    >
                      {workType(w.work_type_code)}
                      <ArrowUpRight className="size-3.5 opacity-0 transition-all group-hover:translate-x-0.5 group-hover:opacity-100" />
                    </Link>
                    <div className="mt-0.5 line-clamp-2 text-xs text-muted-foreground">{w.description}</div>
                    {showWhy && w.headline && (
                      <div className="mt-2 rounded-lg border-l-2 border-brand-200 bg-muted/70 px-2.5 py-1.5 text-xs leading-relaxed text-foreground/80">
                        <p className="line-clamp-2">{w.headline}</p>
                      </div>
                    )}
                    {w.case_size && w.case_size > 1 ? (
                      <div className="mt-1.5 inline-flex items-center gap-1 text-[11px] text-muted-foreground">
                        <Layers className="size-3" /> One case: {w.case_size} alike works, shown once
                      </div>
                    ) : null}
                  </td>
                  <td className="whitespace-nowrap px-4 py-4">
                    <div className="font-medium">{w.district_name ?? "—"}</div>
                    <div className="text-xs text-muted-foreground">{w.state_name}</div>
                  </td>
                  <td className="num whitespace-nowrap px-4 py-4 text-right font-semibold">{inr(w.amount)}</td>
                  <td className="px-4 py-4">
                    <BandBadge band={w.band} limited={w.limited} />
                    {w.score != null && (
                      <div className="mt-2 h-1 w-24 overflow-hidden rounded-full bg-muted">
                        <div
                          className="h-full rounded-full"
                          style={{ width: `${Math.round(w.score * 100)}%`, background: w.band ? BAND_COLOR[w.band] : "var(--brand-600)" }}
                        />
                      </div>
                    )}
                  </td>
                  <td className="py-4 pl-4 pr-5">
                    <EngineChips alerts={w.alerts} />
                  </td>
                </motion.tr>
              ))}
            {!loading && items.length === 0 && (
              <tr>
                <td colSpan={rank ? 6 : 5} className="px-5 py-16 text-center text-sm text-muted-foreground">
                  {emptyText}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

/** The checks that raised a work, by name: a phone has no hover to read a chip's tooltip. */
function AgentNames({ alerts }: { alerts: string[] | null }) {
  const list = (alerts ?? []).filter((a) => a !== "validation");
  if (!list.length) return <span className="text-[11px] text-subtle-foreground">No check asked</span>;
  return (
    <span className="flex flex-wrap gap-x-2.5 gap-y-1">
      {list.map((a) => {
        const m = agentMeta(a);
        return (
          <span key={a} className="inline-flex items-center gap-1 text-[11px] font-medium" style={{ color: m.color }}>
            <span className="size-1.5 rounded-full" style={{ background: m.color }} />
            {m.name}
          </span>
        );
      })}
    </span>
  );
}

export function Pager({ page, total, size, onPage }: { page: number; total: number; size: number; onPage: (p: number) => void }) {
  const last = Math.max(1, Math.ceil(total / size));
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 text-sm text-muted-foreground">
      <span className="num">
        <span className="font-semibold text-foreground">{total.toLocaleString("en-IN")}</span> works · page {page} of{" "}
        {last.toLocaleString("en-IN")}
      </span>
      <div className="flex gap-2">
        <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => onPage(page - 1)}>
          <ChevronLeft /> Previous
        </Button>
        <Button variant="outline" size="sm" disabled={page >= last} onClick={() => onPage(page + 1)}>
          Next <ChevronRight />
        </Button>
      </div>
    </div>
  );
}
