"use client";

import { MapPin, Search, SlidersHorizontal, X } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { PageHeader } from "@/components/nn/layout-bits";
import { Pager, WorkTable } from "@/components/nn/work-table";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { api, type Band, type Page, type WorkRow } from "@/lib/api";
import { BAND_COLOR, BAND_LABEL, BAND_ORDER, WORK_TYPES } from "@/lib/format";

const ANY = "ANY";

export default function WorksPage() {
  return (
    <Suspense fallback={null}>
      <Works />
    </Suspense>
  );
}

function Works() {
  const params = useSearchParams();
  const router = useRouter();
  const path = usePathname();
  const query = params.get("q") ?? "";
  const type = params.get("type") ?? "";
  const band = params.get("band") ?? "";
  const district = params.get("district") ?? "";
  const page = Number(params.get("page") ?? 1) || 1;
  const [data, setData] = useState<{ key: string; page: Page<WorkRow> } | null>(null);
  const key = [query, type, band, district, page].join("|");

  useEffect(() => {
    let live = true;
    api<Page<WorkRow>>("/works", { q: query, type, band, district, page }).then((p) => live && setData({ key, page: p }));
    return () => {
      live = false;
    };
  }, [query, type, band, district, page, key]);

  function set(next: Record<string, string | number | null>) {
    const u = new URLSearchParams(params.toString());
    for (const [k, v] of Object.entries(next)) {
      if (v === null || v === "" || v === ANY || (k === "page" && Number(v) <= 1)) u.delete(k);
      else u.set(k, String(v));
    }
    if (!("page" in next)) u.delete("page");
    router.replace(`${path}${u.toString() ? `?${u}` : ""}`, { scroll: false });
  }

  const current = data?.key === key ? data.page : null;
  const districtName = district && current?.items[0]?.district_name;
  const chips = [
    query && { k: "q", label: `“${query}”` },
    type && { k: "type", label: WORK_TYPES[type] ?? type },
    band && { k: "band", label: BAND_LABEL[band as Band] ?? band, dot: BAND_COLOR[band as Band] },
    district && { k: "district", label: districtName ? `${districtName} district` : `District ${district}`, icon: true },
  ].filter(Boolean) as { k: string; label: string; dot?: string; icon?: boolean }[];

  return (
    <div className="space-y-7">
      <PageHeader
        eyebrow="Monitor · All works"
        title="Every work,"
        accent="searchable."
        lead="Every work in the data you can see. Search by a village, a road or a work id, and narrow by type and risk."
      />

      <div className="panel p-3 sm:p-4">
        <form
          className="flex flex-col gap-3 lg:flex-row"
          onSubmit={(e) => {
            e.preventDefault();
            set({ q: String(new FormData(e.currentTarget).get("q") ?? "").trim() });
          }}
        >
          <div className="relative flex-1">
            <Search className="absolute left-3.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
            {/* keyed on the address bar, so back/forward and the search palette refill it */}
            <input
              key={query}
              name="q"
              defaultValue={query}
              placeholder="Search a village, a road, a work id…"
              className="h-11 w-full rounded-xl border bg-white pl-10 pr-4 text-sm outline-none transition-shadow placeholder:text-subtle-foreground focus:border-brand-400 focus:shadow-[0_0_0_4px_rgb(78_163_230/0.15)]"
            />
          </div>
          <div className="flex flex-wrap gap-2">
            <Select value={type || ANY} onValueChange={(v) => set({ type: v })}>
              <SelectTrigger className="h-11 w-56 rounded-xl bg-white">
                <SlidersHorizontal className="size-4 text-muted-foreground" />
                <SelectValue placeholder="All work types" />
              </SelectTrigger>
              <SelectContent className="max-h-80 rounded-xl" data-lenis-prevent>
                <SelectItem value={ANY}>All work types</SelectItem>
                {Object.entries(WORK_TYPES).map(([k, v]) => (
                  <SelectItem key={k} value={k}>
                    {v}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select value={band || ANY} onValueChange={(v) => set({ band: v })}>
              <SelectTrigger className="h-11 w-40 rounded-xl bg-white">
                <SelectValue placeholder="Any risk" />
              </SelectTrigger>
              <SelectContent className="rounded-xl">
                <SelectItem value={ANY}>Any risk</SelectItem>
                {BAND_ORDER.map((b) => (
                  <SelectItem key={b} value={b}>
                    <span className="size-2 rounded-full" style={{ background: BAND_COLOR[b] }} />
                    {BAND_LABEL[b]}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Button type="submit" className="h-11 rounded-xl bg-brand-gradient px-5">
              <Search /> Search
            </Button>
          </div>
        </form>
        <AnimatePresence initial={false}>
          {chips.length > 0 && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              className="overflow-hidden"
            >
              <div className="flex flex-wrap items-center gap-2 pt-3">
                <span className="text-xs text-muted-foreground">Showing</span>
                {chips.map((c) => (
                  <button
                    key={c.k}
                    onClick={() => set({ [c.k]: null })}
                    className="group inline-flex items-center gap-1.5 rounded-full border bg-brand-50 px-3 py-1 text-xs font-medium text-brand-900 transition-colors hover:border-brand-200"
                  >
                    {c.dot && <span className="size-2 rounded-full" style={{ background: c.dot }} />}
                    {c.icon && <MapPin className="size-3" />}
                    {c.label}
                    <X className="size-3 text-muted-foreground group-hover:text-foreground" />
                  </button>
                ))}
                <button onClick={() => router.replace(path)} className="text-xs font-medium text-brand-700 hover:underline">
                  Clear all
                </button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      <div className="space-y-4">
        <WorkTable items={current?.items ?? []} loading={!current} emptyText="No work matches. Try fewer words or another filter." />
        {current && <Pager page={current.page} total={current.total} size={current.page_size} onPage={(p) => set({ page: p })} />}
      </div>
    </div>
  );
}
