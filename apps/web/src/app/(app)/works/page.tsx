"use client";

import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { Pager, WorkTable } from "@/components/ui";
import { api, type Page, type WorkRow } from "@/lib/api";
import { WORK_TYPES } from "@/lib/format";

export default function WorksPage() {
  return (
    <Suspense fallback={<p className="text-muted text-sm">Loading…</p>}>
      <Works />
    </Suspense>
  );
}

function Works() {
  const params = useSearchParams();
  const [q, setQ] = useState("");
  const [query, setQuery] = useState("");
  const [type, setType] = useState("");
  const [band, setBand] = useState("");
  const [page, setPage] = useState(1);
  const district = params.get("district") ?? "";
  const [data, setData] = useState<Page<WorkRow> | null>(null);

  useEffect(() => {
    api<Page<WorkRow>>("/works", { q: query, type, band, district, page }).then(setData);
  }, [query, type, band, district, page]);

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-bold">All works</h1>
        <p className="text-sm text-muted">
          Every work in the data you can see.
          {district && data?.items[0]?.district_name && <> Showing the district of {data.items[0].district_name}.</>}
        </p>
      </div>
      <form
        className="flex flex-wrap gap-2 text-sm"
        onSubmit={(e) => {
          e.preventDefault();
          setQuery(q);
          setPage(1);
        }}
      >
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search a village, a road, a work id…"
          className="flex-1 min-w-60 rounded-lg border border-line bg-surface px-3 py-2"
        />
        <select value={type} onChange={(e) => { setType(e.target.value); setPage(1); }} className="rounded-lg border border-line bg-surface px-3 py-2">
          <option value="">All work types</option>
          {Object.entries(WORK_TYPES).map(([k, v]) => (
            <option key={k} value={k}>
              {v}
            </option>
          ))}
        </select>
        <select value={band} onChange={(e) => { setBand(e.target.value); setPage(1); }} className="rounded-lg border border-line bg-surface px-3 py-2">
          <option value="">Any risk</option>
          <option value="HIGH">High</option>
          <option value="MEDIUM">Medium</option>
          <option value="LOW">Low</option>
        </select>
        <button className="rounded-lg bg-navy px-4 py-2 text-white">Search</button>
      </form>
      {data ? (
        <>
          <WorkTable items={data.items} />
          <Pager page={data.page} total={data.total} size={data.page_size} onPage={setPage} />
        </>
      ) : (
        <p className="text-muted text-sm">Loading…</p>
      )}
    </div>
  );
}
