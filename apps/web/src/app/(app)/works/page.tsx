"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import {
  Button,
  EmptyState,
  Field,
  FilterBar,
  LoadingState,
  Pagination,
  SearchInput,
  Select,
  StatusLabel,
} from "@/components/kit";
import { WorkTable } from "@/components/ui";
import { api, type DistrictRow, type Page, type WorkRow } from "@/lib/api";
import { count, WORK_TYPES } from "@/lib/format";
import { useFetch } from "@/lib/useFetch";

export default function WorksPage() {
  return (
    <Suspense fallback={<LoadingState label="Loading works" />}>
      <Works />
    </Suspense>
  );
}

function Works() {
  const params = useSearchParams();
  const router = useRouter();
  const district = params.get("district") ?? "";

  const [q, setQ] = useState("");
  const [query, setQuery] = useState("");
  const [type, setType] = useState("");
  const [band, setBand] = useState("");
  const [page, setPage] = useState(1);

  const districtsRes = useFetch(
    () => api<DistrictRow[]>("/dashboard/districts").then((d) => [...d].sort((a, b) => a.name.localeCompare(b.name))),
    [],
  );
  const districts = districtsRes.data ?? [];

  const { data, error, loading, reload } = useFetch(
    () => api<Page<WorkRow>>("/works", { q: query, type, band, district, page }),
    [query, type, band, district, page],
  );

  function setDistrictParam(next: string) {
    const usp = new URLSearchParams(params.toString());
    if (next) usp.set("district", next);
    else usp.delete("district");
    router.replace(`/works${usp.toString() ? `?${usp}` : ""}`);
    setPage(1);
  }

  const activeDistrictName = districts.find((d) => d.district_lgd === district)?.name;
  const filtered = query !== "" || type !== "" || band !== "" || district !== "";

  function reset() {
    setQ("");
    setQuery("");
    setType("");
    setBand("");
    setDistrictParam("");
    setPage(1);
  }

  return (
    <div className="space-y-5">
      <header className="border-b-2 border-strong pb-4">
        <div className="flex flex-wrap items-center gap-2">
          <h1 className="text-2xl font-bold tracking-tight md:text-3xl">Works</h1>
          {data && <StatusLabel tone="neutral">{count(data.total)} records</StatusLabel>}
          {activeDistrictName && <StatusLabel tone="info">{activeDistrictName}</StatusLabel>}
        </div>
        <p className="mt-1.5 max-w-3xl text-sm leading-relaxed text-muted">
          Every MPLADS work visible to your role. Search, filter and open any work to see its full assessment.
        </p>
      </header>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          setQuery(q);
          setPage(1);
        }}
      >
        <FilterBar>
          <div className="min-w-0 flex-1 sm:min-w-[16rem]">
            <Field label="Search" htmlFor="w-search">
              <SearchInput
                id="w-search"
                value={q}
                onChange={(e) => setQ(e.target.value)}
                placeholder="Village, road, description or work ID…"
              />
            </Field>
          </div>
          <div className="sm:w-56">
            <Field label="Work type" htmlFor="w-type">
              <Select
                id="w-type"
                value={type}
                onChange={(e) => {
                  setType(e.target.value);
                  setPage(1);
                }}
              >
                <option value="">All work types</option>
                {Object.entries(WORK_TYPES).map(([k, v]) => (
                  <option key={k} value={k}>
                    {v}
                  </option>
                ))}
              </Select>
            </Field>
          </div>
          <div className="sm:w-40">
            <Field label="Risk" htmlFor="w-band">
              <Select
                id="w-band"
                value={band}
                onChange={(e) => {
                  setBand(e.target.value);
                  setPage(1);
                }}
              >
                <option value="">Any risk</option>
                <option value="HIGH">High</option>
                <option value="MEDIUM">Medium</option>
                <option value="LOW">Low</option>
              </Select>
            </Field>
          </div>
          <div className="sm:w-56">
            <Field label="District" htmlFor="w-district">
              <Select id="w-district" value={district} onChange={(e) => setDistrictParam(e.target.value)}>
                <option value="">All districts</option>
                {districts.map((d) => (
                  <option key={d.district_lgd} value={d.district_lgd}>
                    {d.name}, {d.state}
                  </option>
                ))}
              </Select>
            </Field>
          </div>
          <div className="flex items-end gap-2">
            <Button variant="primary" type="submit">
              Search
            </Button>
            <Button variant="ghost" type="button" disabled={!filtered} onClick={reset}>
              Reset
            </Button>
          </div>
        </FilterBar>
      </form>

      <WorkTable
        items={data?.items ?? []}
        loading={loading}
        error={error}
        onRetry={reload}
        empty={
          <EmptyState
            title="No works found"
            message={filtered ? "No works match the selected filters." : "There are no works to show."}
            action={
              filtered ? (
                <Button variant="secondary" onClick={reset}>
                  Clear filters
                </Button>
              ) : undefined
            }
          />
        }
      />

      {data && data.total > 0 && (
        <Pagination page={data.page} total={data.total} size={data.page_size} onPage={setPage} unit="works" />
      )}
    </div>
  );
}
