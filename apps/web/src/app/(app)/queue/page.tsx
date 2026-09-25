"use client";

import { useEffect, useState } from "react";
import { Pager, WorkTable } from "@/components/ui";
import { api, type Page, type WorkRow } from "@/lib/api";

export default function Queue() {
  const [band, setBand] = useState("");
  const [page, setPage] = useState(1);
  const [data, setData] = useState<Page<WorkRow> | null>(null);

  useEffect(() => {
    api<Page<WorkRow>>("/queue", { band, page }).then(setData);
  }, [band, page]);

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-bold">Review queue</h1>
        <p className="text-sm text-muted">
          Step 5 of the pipeline: works flagged Medium or High, most important first. Importance is the risk score weighted by the money
          at stake. Every entry is a request to look, not a finding of wrongdoing.
        </p>
      </div>
      <div className="flex gap-2 text-sm">
        {[
          ["", "All"],
          ["HIGH", "High"],
          ["MEDIUM", "Medium"],
        ].map(([v, l]) => (
          <button
            key={v}
            onClick={() => {
              setBand(v);
              setPage(1);
            }}
            className={`rounded-lg px-3 py-1.5 border ${band === v ? "bg-navy text-white border-navy" : "border-line bg-surface"}`}
          >
            {l}
          </button>
        ))}
      </div>
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
