"use client";

import Link from "next/link";
import { Suspense, useMemo, useState } from "react";
import {
  apiPatch,
  apiPost,
  ApiError,
  type InspectionRow,
  type InspectionState,
  type Outcome,
  type Page as PageT,
} from "@/lib/api";
import { useApi } from "@/lib/useApi";
import { count, inr, workHref, workType } from "@/lib/format";
import { INSPECTION_STEPS, OUTCOME_LABEL, OUTCOME_WHY } from "@/lib/tokens";
import { useUrlFilters } from "@/lib/useUrlFilters";
import { useMe } from "@/components/me";
import { BandBadge, Button, Empty, ErrorState, Loading, Note, Panel, PanelHeader, Pill } from "@/components/ui";

/**
 * The inspection planner: works asked to be verified on the ground.
 *
 * Six fixed steps, none of which can be skipped, because the value of this screen
 * is the record: who was asked, who went, what they saw, and when. A work whose
 * risk score is untouched by anything here — this screen answers questions, it does
 * not raise them.
 */
export default function InspectionsPage() {
  return (
    <Suspense fallback={null}>
      <Planner />
    </Suspense>
  );
}

function Planner() {
  const url = useUrlFilters({ state: "" });
  const { values, set, page, setPage } = url;
  const me = useMe();
  const list = useApi<PageT<InspectionRow>>("/inspections", {
    state: values.state,
    page: String(page),
  });
  const data = list.data;
  const [busyId, setBusyId] = useState<number | null>(null);
  const [say, setSay] = useState<string | null>(null);
  const [assignTo, setAssignTo] = useState<Record<number, string>>({});
  const [result, setResult] = useState<Record<number, Outcome>>({});
  const [observed, setObserved] = useState<Record<number, string>>({});

  const steps = data?.states ?? [];
  const next = data?.next ?? {};
  const counts = data?.counts ?? {};

  async function act(row: InspectionRow, fn: () => Promise<unknown>, ok: string) {
    setBusyId(row.inspection_id);
    try {
      await fn();
      setSay(ok);
      list.reload();
    } catch (e) {
      setSay(e instanceof ApiError ? e.message : "That step did not go through.");
    } finally {
      setBusyId(null);
    }
  }

  const planned = useMemo(
    () => (data?.items ?? []).filter((i) => i.state === "INSPECTION_REQUIRED"),
    [data],
  );

  return (
    <div className="space-y-3">
      <header>
        <h1 className="text-xl font-semibold tracking-tight text-foreground">Inspection planner</h1>
        <p className="mt-0.5 max-w-3xl text-xs text-secondary">
          Works asked to be verified on the ground, in the order they should be tackled: highest
          money at stake first. Every step an officer records here stays on the work; none of it
          changes the risk score.
        </p>
      </header>

      <Panel className="p-0">
        <PanelHeader
          title="The six steps, and how many visits are at each"
          hint="An officer can only offer the next step. Nothing here can jump the queue, so the record is complete by construction."
        />
        <ol className="grid gap-2 border-t border-line p-3 sm:grid-cols-2 xl:grid-cols-3">
          {steps.map((s) => {
            const st = s as InspectionState;
            const here = values.state === s;
            return (
              <li key={s}>
                <button
                  type="button"
                  aria-pressed={here}
                  onClick={() => set({ state: here ? "" : s })}
                  className={`w-full rounded border px-3 py-2 text-left transition-colors ${
                    here ? "border-navy bg-sunken" : "border-line hover:bg-sunken"
                  }`}
                >
                  <span className="flex items-baseline gap-2">
                    <span className="tnum text-lg font-semibold leading-none">
                      {count(counts[s] ?? 0)}
                    </span>
                    <span className="text-xs font-medium text-secondary">
                      {INSPECTION_STEPS[st]?.label ?? s}
                    </span>
                  </span>
                  <span className="mt-1 block text-2xs text-muted">
                    {INSPECTION_STEPS[st]?.why}
                  </span>
                </button>
              </li>
            );
          })}
        </ol>
      </Panel>

      {say && <Note tone="info">{say}</Note>}

      {planned.length > 0 && me?.role !== "FIELD" && (
        <Panel className="p-0">
          <PanelHeader
            title="Waiting to be assigned"
            hint="Name the officer going out. Until a visit is assigned it cannot be marked seen on the ground."
          />
          <ul className="divide-y divide-[var(--line)] border-t border-line">
            {planned.map((r) => (
              <li key={r.inspection_id} className="flex flex-wrap items-end gap-2 px-3 py-2">
                <Link href={workHref(r.work_id)} className="min-w-0 flex-1 text-sm text-navy underline-offset-2 hover:underline">
                  {r.district_name} · {workType(r.work_type_code)}
                </Link>
                <input
                  className="field w-52"
                  placeholder="Officer going out"
                  aria-label={`Officer assigned to ${r.work_id}`}
                  value={assignTo[r.inspection_id] ?? ""}
                  onChange={(e) => setAssignTo((a) => ({ ...a, [r.inspection_id]: e.target.value }))}
                />
                <Button
                  size="sm"
                  variant="primary"
                  disabled={busyId === r.inspection_id || !(assignTo[r.inspection_id] ?? "").trim()}
                  onClick={() =>
                    act(
                      r,
                      () =>
                        apiPatch(`/inspections/${r.inspection_id}`, {
                          state: "ASSIGNED",
                          assigned_to: assignTo[r.inspection_id].trim(),
                          actor: me?.user_id ?? null,
                        }),
                      `Assigned. ${r.work_id} is now with ${assignTo[r.inspection_id].trim()}.`,
                    )
                  }
                >
                  Assign
                </Button>
              </li>
            ))}
          </ul>
        </Panel>
      )}

      <Panel className="overflow-hidden">
        <div className="flex items-center justify-between gap-2 border-b border-line px-3 py-2">
          <p className="text-xs text-secondary">
            {list.status === "loading" ? "Loading visits…" : `${count(data?.total ?? 0)} visits`}
            {list.refetching && " · refreshing"}
          </p>
          {values.state && (
            <button type="button" className="btn btn-ghost btn-sm" onClick={() => set({ state: "" })}>
              Show every step
            </button>
          )}
        </div>

        {list.error ? (
          <ErrorState
            title="The planner could not be loaded"
            body="Nothing has been changed. Try again in a moment."
            onRetry={list.reload}
          />
        ) : list.status === "loading" ? (
          <Loading label="Loading visits" />
        ) : !data?.items.length ? (
          <Empty
            title={values.state ? "No visit at this step" : "No work is being verified on the ground"}
            body={
              <>
                Nothing has been asked for a visit yet. Open a work from the{" "}
                <Link href="/queue" className="underline underline-offset-2">
                  review queue
                </Link>{" "}
                and choose <em>Ask for a site visit</em>, or move an alert to Investigating, which
                opens the visit that answers it.
              </>
            }
          />
        ) : (
          <ul className="divide-y divide-[var(--line)]">
            {data.items.map((r) => (
              <Visit
                key={r.inspection_id}
                row={r}
                next={next[r.state] ?? []}
                busy={busyId === r.inspection_id}
                result={result[r.inspection_id]}
                observed={observed[r.inspection_id] ?? ""}
                onResult={(o) => setResult((m) => ({ ...m, [r.inspection_id]: o }))}
                onObserved={(t) => setObserved((m) => ({ ...m, [r.inspection_id]: t }))}
                onAssign={(who) =>
                  act(
                    r,
                    () =>
                      apiPatch(`/inspections/${r.inspection_id}`, {
                        state: "ASSIGNED",
                        assigned_to: who,
                        actor: me?.user_id ?? null,
                      }),
                    `Assigned to ${who}.`,
                  )
                }
                onSeen={() =>
                  act(
                    r,
                    () =>
                      apiPatch(`/inspections/${r.inspection_id}`, {
                        state: "FIELD_VERIFIED",
                        actor: me?.user_id ?? null,
                      }),
                    "Marked seen on the ground.",
                  )
                }
                onRecord={(o, seen) =>
                  act(
                    r,
                    () =>
                      apiPost(`/inspections/${r.inspection_id}/result`, {
                        outcome: o,
                        observed: seen,
                        recorded_by: me?.user_id ?? null,
                      }),
                    "Recorded. This stays on the work for good.",
                  )
                }
                onClose={() =>
                  act(
                    r,
                    () =>
                      apiPatch(`/inspections/${r.inspection_id}`, {
                        state: "CLOSED",
                        actor: me?.user_id ?? null,
                      }),
                    "Visit closed.",
                  )
                }
              />
            ))}
          </ul>
        )}
      </Panel>

      {!!data?.total && (
        <nav className="flex items-center justify-between text-2xs text-muted" aria-label="Planner pages">
          <span className="tnum">
            Page {data.page} of {Math.max(1, Math.ceil(data.total / data.page_size))}
          </span>
          <span className="flex gap-1.5">
            <Button size="sm" disabled={page <= 1} onClick={() => setPage(page - 1)}>
              ← Previous
            </Button>
            <Button size="sm" disabled={page >= Math.ceil(data.total / data.page_size)} onClick={() => setPage(page + 1)}>
              Next →
            </Button>
          </span>
        </nav>
      )}
    </div>
  );
}

function Visit({
  row,
  next,
  busy,
  result,
  observed,
  onResult,
  onObserved,
  onAssign,
  onSeen,
  onRecord,
  onClose,
}: {
  row: InspectionRow;
  next: string[];
  busy: boolean;
  result?: Outcome;
  observed: string;
  onResult: (o: Outcome) => void;
  onObserved: (t: string) => void;
  onAssign: (who: string) => void;
  onSeen: () => void;
  onRecord: (o: Outcome, seen: string) => void;
  onClose: () => void;
}) {
  const step = INSPECTION_STEPS[row.state];
  return (
    <li className="px-3 py-2.5">
      <div className="flex flex-wrap items-start gap-x-3 gap-y-1.5">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <BandBadge band={row.band} limited={null} size="sm" />
            <Pill glyph="◈">{step?.label ?? row.state}</Pill>
            <Link
              href={workHref(row.work_id)}
              className="truncate text-sm font-medium text-navy underline-offset-2 hover:underline"
            >
              {workType(row.work_type_code)}
            </Link>
            <span className="tnum text-2xs text-muted">{row.work_id}</span>
            {!row.has_evidence && (
              <span
                className="text-2xs text-muted"
                title="No papers or photos are attached, so nothing on this page could be checked against the work's own records."
              >
                nothing attached to check against
              </span>
            )}
          </div>
          <p className="mt-0.5 line-clamp-1 text-xs text-secondary">{row.description}</p>
          <p className="mt-0.5 text-2xs text-muted">
            {[row.district_name, row.state_name].filter(Boolean).join(", ")} ·{" "}
            <span className="tnum">{inr(row.amount)}</span>
            {row.agency_name && <> · {row.agency_name}</>}
            {row.due_date && (
              <>
                {" "}
                · due <time dateTime={row.due_date}>{row.due_date}</time>
              </>
            )}
          </p>
          {row.assigned_to && (
            <p className="mt-0.5 text-2xs text-muted">Assigned to {row.assigned_to}</p>
          )}
          {row.note && (
            <p className="mt-1 border-l-2 border-[var(--line-strong)] pl-2 text-2xs text-muted">
              {row.note}
            </p>
          )}
        </div>
        <div className="flex shrink-0 flex-wrap items-center gap-1.5">
          {next.includes("ASSIGNED") && !row.assigned_to && (
            <AssignButton busy={busy} onAssign={onAssign} />
          )}
          {next.includes("FIELD_VERIFIED") && (
            <Button size="sm" variant="primary" disabled={busy} onClick={onSeen}>
              Mark seen on the ground
            </Button>
          )}
          {next.includes("RESULT_RECORDED") && (
            <RecordOutcome busy={busy} outcome={result} observed={observed} onResult={onResult} onObserved={onObserved} onRecord={onRecord} />
          )}
          {next.includes("CLOSED") && (
            <Button size="sm" disabled={busy} onClick={onClose}>
              Close visit
            </Button>
          )}
          {next.length === 0 && <span className="text-2xs text-muted">Closed</span>}
        </div>
      </div>
      {row.results > 0 && row.state === "RESULT_RECORDED" && (
        <p className="mt-1 text-2xs text-muted">{row.results} result recorded</p>
      )}
    </li>
  );
}

function AssignButton({ busy, onAssign }: { busy: boolean; onAssign: (who: string) => void }) {
  const [who, setWho] = useState("");
  return (
    <span className="flex items-center gap-1.5">
      <input
        className="field w-40 py-1 text-xs"
        placeholder="Officer"
        value={who}
        onChange={(e) => setWho(e.target.value)}
      />
      <Button size="sm" disabled={busy || !who.trim()} onClick={() => onAssign(who.trim())}>
        Assign
      </Button>
    </span>
  );
}

function RecordOutcome({
  busy,
  outcome,
  observed,
  onResult,
  onObserved,
  onRecord,
}: {
  busy: boolean;
  outcome?: Outcome;
  observed: string;
  onResult: (o: Outcome) => void;
  onObserved: (t: string) => void;
  onRecord: (o: Outcome, seen: string) => void;
}) {
  const [open, setOpen] = useState(false);
  if (!open) {
    return (
      <Button size="sm" variant="primary" onClick={() => setOpen(true)}>
        Record what was seen
      </Button>
    );
  }
  return (
    <div className="panel-inset w-full space-y-2 p-2">
      <fieldset className="space-y-1">
        <legend className="eyebrow">What did the officer see?</legend>
        {(Object.keys(OUTCOME_LABEL) as Outcome[]).map((o) => (
          <label key={o} className="flex items-start gap-2 text-xs">
            <input
              type="radio"
              name="outcome"
              checked={outcome === o}
              onChange={() => onResult(o)}
              className="mt-0.5"
            />
            <span>
              <span className="font-medium text-foreground">{OUTCOME_LABEL[o]}</span>
              <span className="block text-2xs text-muted">{OUTCOME_WHY[o]}</span>
            </span>
          </label>
        ))}
      </fieldset>
      <label className="block">
        <span className="eyebrow">Note (optional)</span>
        <input
          className="field mt-1 w-full"
          value={observed}
          onChange={(e) => onObserved(e.target.value)}
          placeholder="what the officer wrote down"
        />
      </label>
      <div className="flex gap-1.5">
        <Button
          size="sm"
          variant="primary"
          disabled={busy || !outcome}
          onClick={() => outcome && onRecord(outcome, observed.trim())}
        >
          Save result
        </Button>
        <Button size="sm" variant="ghost" onClick={() => setOpen(false)}>
          Cancel
        </Button>
      </div>
    </div>
  );
}
