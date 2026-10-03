"use client";

import { AlertOctagon, IndianRupee, Inbox, Scale } from "lucide-react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { Reveal } from "@/components/motion/reveal";
import { PageHeader, StatTile } from "@/components/nn/layout-bits";
import { Segmented } from "@/components/nn/segmented";
import { Pager, WorkTable } from "@/components/nn/work-table";
import { api, type Page, type Summary, type WorkRow } from "@/lib/api";
import { useApiData } from "@/lib/cache";
import { BAND_COLOR, inr } from "@/lib/format";

type BandFilter = "" | "CRITICAL" | "HIGH";

export default function QueuePage() {
  return (
    <Suspense fallback={null}>
      <Queue />
    </Suspense>
  );
}

function Queue() {
  const params = useSearchParams();
  const router = useRouter();
  const path = usePathname();
  const band = (params.get("band") ?? "") as BandFilter;
  const page = Number(params.get("page") ?? 1) || 1;
  const [data, setData] = useState<{ key: string; page: Page<WorkRow> } | null>(null);
  const { data: s } = useApiData<Summary>("/dashboard/summary");
  const key = `${band}|${page}`;

  useEffect(() => {
    let live = true;
    api<Page<WorkRow>>("/queue", { band, page }).then((p) => live && setData({ key, page: p }));
    return () => {
      live = false;
    };
  }, [band, page, key]);

  function set(next: { band?: BandFilter; page?: number }) {
    const q = new URLSearchParams(params.toString());
    const b = next.band ?? band;
    const p = next.page ?? 1;
    if (b) q.set("band", b);
    else q.delete("band");
    if (p > 1) q.set("page", String(p));
    else q.delete("page");
    router.replace(`${path}${q.toString() ? `?${q}` : ""}`, { scroll: false });
  }

  const current = data?.key === key ? data.page : null;
  const crit = s?.bands.CRITICAL ?? null;
  const high = s?.bands.HIGH ?? null;
  const onPage = current?.items.reduce((sum, w) => sum + (w.amount ?? 0), 0) ?? 0;

  return (
    <div className="space-y-7">
      <PageHeader
        eyebrow="Act · Review queue"
        title="Works to verify"
        accent="first."
        lead="Works flagged Critical or High, most important first. Importance is the risk score weighted by the money at stake. Every entry is a request to look, not a finding of wrongdoing."
      />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatTile label="In the queue" value={(crit ?? 0) + (high ?? 0)} icon={<Inbox className="size-4" />} note="High + Critical" />
        <StatTile label="Critical" value={crit ?? 0} icon={<AlertOctagon className="size-4" />} tone="var(--critical)" note="highest priority" />
        <StatTile label="High" value={high ?? 0} icon={<Scale className="size-4" />} tone="var(--high)" note="two checks agree" />
        <StatTile label="Money on this page" value={onPage} format={(v) => inr(v)} icon={<IndianRupee className="size-4" />} tone="var(--teal)" note="the works listed below" />
      </div>

      <Reveal className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <Segmented<BandFilter>
            value={band}
            onChange={(b) => set({ band: b, page: 1 })}
            options={[
              { value: "", label: "All" },
              { value: "CRITICAL", label: "Critical", dot: BAND_COLOR.CRITICAL, count: crit },
              { value: "HIGH", label: "High", dot: BAND_COLOR.HIGH, count: high },
            ]}
          />
          <span className="text-xs text-muted-foreground">Alike works found by Duplicate &amp; Split are shown once, as one case.</span>
        </div>
        <WorkTable
          items={current?.items ?? []}
          loading={!current}
          rank
          start={current ? (current.page - 1) * current.page_size : 0}
          emptyText="No works in this band."
        />
        {current && <Pager page={current.page} total={current.total} size={current.page_size} onPage={(p) => set({ page: p })} />}
      </Reveal>
    </div>
  );
}
