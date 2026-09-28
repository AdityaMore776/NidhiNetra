"use client";

import { useState } from "react";
import {
  Button,
  EmptyState,
  Field,
  FilterBar,
  Pagination,
  SegmentedControl,
  Select,
  StatusLabel,
} from "@/components/kit";
import { WorkTable } from "@/components/ui";
import { api, type DistrictRow, type Page, type WorkRow } from "@/lib/api";
import { count } from "@/lib/format";
import { useFetch } from "@/lib/useFetch";

export default function Queue() {
  const [band, setBand] = useState("");
  const [district, setDistrict] = useState("");
  const [page, setPage] = useState(1);

  const districtsRes = useFetch(
    () => api<DistrictRow[]>("/dashboard/districts").then((d) => [...d].sort((a, b) => a.name.localeCompare(b.name))),
    [],
  );
  const districts = districtsRes.data ?? [];

  const { data, error, loading, reload } = useFetch(
    () => api<Page<WorkRow>>("/queue", { band, district, page }),
    [band, district, page],
  );

  const filtered = band !== "" || district !== "";

  return (
    <div className="space-y-5">
      <header className="border-b-2 border-strong pb-4">
        <div className="flex flex-wrap items-center gap-2">
          <h1 className="text-2xl font-bold tracking-tight md:text-3xl">Review Queue</h1>
          {data && <StatusLabel tone="medium">{count(data.total)} works</StatusLabel>}
        </div>
        <p className="mt-1.5 max-w-3xl text-sm leading-relaxed text-muted">
          Works flagged Medium or High, most important first. Priority is the risk score weighted by the money at stake.
          Every entry is a request to look — not a finding of wrongdoing.
        </p>
      </header>

      <FilterBar>
        <SegmentedControl
          label="Risk band"
          value={band}
          onChange={(v) => {
            setBand(v);
            setPage(1);
          }}
          options={[
            { value: "", label: "All" },
            { value: "HIGH", label: "High" },
            { value: "MEDIUM", label: "Medium" },
          ]}
        />
        <div className="sm:w-64">
          <Field label="District" htmlFor="q-district">
            <Select
              id="q-district"
              value={district}
              onChange={(e) => {
                setDistrict(e.target.value);
                setPage(1);
              }}
            >
              <option value="">All districts</option>
              {districts.map((d) => (
                <option key={d.district_lgd} value={d.district_lgd}>
                  {d.name}, {d.state}
                </option>
              ))}
            </Select>
          </Field>
        </div>
        <div className="sm:ml-auto sm:self-end">
          <Button
            variant="ghost"
            disabled={!filtered}
            onClick={() => {
              setBand("");
              setDistrict("");
              setPage(1);
            }}
          >
            Reset filters
          </Button>
        </div>
      </FilterBar>

      <WorkTable
        items={data?.items ?? []}
        showRank
        loading={loading}
        error={error}
        onRetry={reload}
        empty={
          <EmptyState
            title="No works in the queue"
            message={filtered ? "No flagged works match these filters." : "Nothing is currently flagged for review."}
            action={
              filtered ? (
                <Button
                  variant="secondary"
                  onClick={() => {
                    setBand("");
                    setDistrict("");
                    setPage(1);
                  }}
                >
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
