"use client";

import { useState } from "react";
import { ApiError, type Page as PageT, type WorkRow } from "@/lib/api";
import { useApi } from "@/lib/useApi";
import { ErrorState, Loading } from "@/components/ui";
import {
  ColumnControls,
  DEFAULT_SHOWN,
  downloadCsv,
  FilterSelect,
  Pager,
  SearchBox,
  toCsv,
  WorkTable,
} from "@/components/WorkTable";
import type { useUrlFilters } from "@/lib/useUrlFilters";

type Filters = ReturnType<typeof useUrlFilters>;

export interface ListOption {
  value: string;
  label: string;
}

export interface ListOptions {
  districts?: ListOption[];
  bands?: ListOption[];
  types?: ListOption[];
  statuses?: ListOption[];
  findings?: ListOption[];
}

/**
 * The two list screens — the review queue and all works — are the same screen with
 * different filters, so they share one component. Filters live in the address bar,
 * the table's columns can be chosen, and the page on screen can be downloaded as
 * CSV so an officer can take exactly what they can see into a meeting.
 */
export function WorkList({
  path,
  url,
  options,
  searchPlaceholder,
  exportName,
  title,
  intro,
  extraFilters,
  emptyTitle,
  emptyBody,
  note,
}: {
  path: string;
  url: Filters;
  options: ListOptions;
  searchPlaceholder?: string;
  exportName?: string;
  title: string;
  intro: string;
  extraFilters?: React.ReactNode;
  emptyTitle?: string;
  emptyBody?: string;
  note?: React.ReactNode;
}) {
  const { values, set, page, setPage, filtered, clear } = url;
  const [columns, setColumns] = useState<string[] | null>(null);
  const shown = columns ?? DEFAULT_SHOWN;
  const toggleColumn = (key: string) =>
    setColumns((cur) => {
      const on = cur ?? DEFAULT_SHOWN;
      return on.includes(key) ? on.filter((k) => k !== key) : [...on, key];
    });
  const list = useApi<PageT<WorkRow>>(path, { ...values, page: String(page) });
  const page_ = list.data;

  return (
    <section className="space-y-3">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold tracking-tight text-foreground">{title}</h1>
          <p className="mt-0.5 max-w-2xl text-xs text-secondary">{intro}</p>
        </div>
        <div className="flex items-center gap-2">
          {searchPlaceholder && (
            <SearchBox
              value={values.q}
              placeholder={searchPlaceholder}
              label="Search works"
              onSubmit={(q) => set({ q })}
            />
          )}
          <ColumnControls
            shown={shown}
            onToggle={toggleColumn}
            onExport={
              exportName && page_ ? () => downloadCsv(exportName, toCsv(page_.items)) : undefined
            }
          />
        </div>
      </header>

      <div className="panel flex flex-wrap items-end gap-x-4 gap-y-2 p-2.5">
        {options.districts && (
          <FilterSelect
            label="District"
            value={values.district}
            options={options.districts}
            onChange={(district) => set({ district })}
          />
        )}
        {options.bands && (
          <FilterSelect
            label="Band"
            value={values.band}
            options={options.bands}
            onChange={(band) => set({ band })}
          />
        )}
        {options.findings && (
          <FilterSelect
            label="Finding"
            value={values.finding}
            options={options.findings}
            onChange={(finding) => set({ finding })}
          />
        )}
        {options.types && (
          <FilterSelect
            label="Type"
            value={values.type}
            options={options.types}
            onChange={(type) => set({ type })}
          />
        )}
        {options.statuses && (
          <FilterSelect
            label="Status"
            value={values.status}
            options={options.statuses}
            onChange={(status) => set({ status })}
          />
        )}
        <FilterSelect
          label="Assessment"
          value={values.assess}
          options={[
            { value: "", label: "All works" },
            { value: "assessable", label: "A check could read it" },
            { value: "not_assessable", label: "Couldn't check" },
          ]}
          onChange={(assess) => set({ assess })}
        />
        <FilterSelect
          label="Evidence"
          value={values.evidence}
          options={[
            { value: "", label: "Any" },
            { value: "with", label: "Has papers or photos" },
            { value: "without", label: "Nothing attached" },
          ]}
          onChange={(evidence) => set({ evidence })}
        />
        {extraFilters}
        {filtered && (
          <button type="button" className="btn btn-ghost btn-sm" onClick={clear}>
            Clear {Object.values(values).filter(Boolean).length} filter
            {Object.values(values).filter(Boolean).length === 1 ? "" : "s"}
          </button>
        )}
      </div>

      {note}

      <div className="panel overflow-hidden">
        {list.error ? (
          <ErrorState
            title="This list could not be loaded"
            body={`Your filters are still in the address bar, so nothing has been lost. ${errorWords(list.error)} You can copy the address and send it to the data team.`}
            onRetry={list.reload}
          />
        ) : list.status === "loading" ? (
          <Loading label="Loading works" />
        ) : (
          <>
            <WorkTable
              items={page_?.items ?? []}
              shown={shown}
              emptyTitle={emptyTitle}
              emptyBody={emptyBody}
            />
            {!!page_?.total && (
              <div className="border-t border-line px-3 py-2">
                <Pager page={page_.page} total={page_.total} size={page_.page_size} onPage={setPage} />
              </div>
            )}
          </>
        )}
      </div>
    </section>
  );
}

/** Turn a 403 into words an officer can act on, not a stack trace. */
export function errorWords(e: unknown): string {
  if (e instanceof ApiError) {
    if (e.status === 403) return "Your account is not cleared to see this.";
    if (e.status === 404) return "There is nothing here for you to see.";
    return e.message;
  }
  return "The service did not answer.";
}