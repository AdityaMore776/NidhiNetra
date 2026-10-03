"use client";

import Link from "next/link";
import { useState } from "react";
import { Suspense } from "react";
import {
  apiPatch,
  ApiError,
  type AlertRow,
  type AlertState,
  type Page as PageT,
} from "@/lib/api";
import { useApi } from "@/lib/useApi";
import { count, inr, workHref, workType } from "@/lib/format";
import { ALERT_LABEL } from "@/lib/tokens";
import { useUrlFilters } from "@/lib/useUrlFilters";
import { useMe } from "@/components/me";
import { BandBadge, Button, Empty, ErrorState, Loading, Note, Panel, PanelHeader, Pill } from "@/components/ui";

const ORDER: AlertState[] = ["NEW", "ACKNOWLEDGED", "INVESTIGATING", "RESOLVED"];

const NEXT: Record<AlertState, AlertState[]> = {
  NEW: ["ACKNOWLEDGED", "RESOLVED"],
  ACKNOWLEDGED: ["INVESTIGATING", "RESOLVED"],
  INVESTIGATING: ["RESOLVED"],
  RESOLVED: [],
};

/**
 * Alerts: a request to look, and what has happened to that request.
 *
 * An alert is not a finding and carries no score of its own — it points at a work
 * the engines already assessed. The steps cannot be skipped by a mistyped click,
 * and closing an alert without investigating requires a reason, because "we looked
 * and it is fine" and "we never looked" must not read the same in the record.
 */
export default function AlertsPage() {
  return (
    <Suspense fallback={null}>
      <Alerts />
    </Suspense>
  );
}

function Alerts() {
  const url = useUrlFilters({ state: "", page: "" });
  const { values, set, page, setPage, filtered, clear } = url;
  const me = useMe();
  const list = useApi<PageT<AlertRow>>("/alerts", { state: values.state, page: String(page) });
  const data = list.data;
  const [busyId, setBusyId] = useState<number | null>(null);
  const [closing, setClosing] = useState<AlertRow | null>(null);
  const [note, setNote] = useState("");
  const [say, setSay] = useState<string | null>(null);

  async function move(row: AlertRow, state: AlertState) {
    if (state === "RESOLVED") {
      setClosing(row);
      setNote("");
      return;
    }
    setBusyId(row.alert_id);
    try {
      await apiPatch(`/alerts/${row.alert_id}`, {
        state,
        actor: me?.user_id ?? null,
      });
      setSay(`Alert ${state.toLowerCase().replace("_", " ")}.`);
      list.reload();
    } catch (e) {
      setSay(e instanceof ApiError ? e.message : "That step did not go through.");
    } finally {
      setBusyId(null);
    }
  }

  async function confirmClose() {
    if (!closing) return;
    setBusyId(closing.alert_id);
    try {
      await apiPatch(`/alerts/${closing.alert_id}`, {
        state: "RESOLVED",
        note: note.trim(),
        actor: me?.user_id ?? null,
      });
      setSay("Alert resolved. Your reason is on the record.");
      setClosing(null);
      list.reload();
    } catch (e) {
      setSay(e instanceof ApiError ? e.message : "That did not go through.");
    } finally {
      setBusyId(null);
    }
  }

  const counts = data?.counts ?? {};

  return (
    <div className="space-y-3">
      <header>
        <h1 className="text-xl font-semibold tracking-tight text-foreground">Alerts</h1>
        <p className="mt-0.5 max-w-3xl text-xs text-secondary">
          One alert per work the engines put in the review queue. An alert asks a person to look; it
          is not a finding, and nothing about a work&apos;s risk score changes when one is opened,
          moved or closed.
        </p>
      </header>

      {/* the lifecycle, with the real counts beside each step */}
      <Panel className="p-0">
        <PanelHeader
          title="Where every alert stands"
          hint="Counted live from the alerts table, in your area only."
        />
        <ol className="grid gap-2 border-t border-line p-3 sm:grid-cols-2 xl:grid-cols-4">
          {ORDER.map((s) => {
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
                  <span className="tnum block text-lg font-semibold leading-none">
                    {count(counts[s] ?? 0)}
                  </span>
                  <span className="mt-1 block text-xs font-medium text-secondary">{ALERT_LABEL[s]}</span>
                  <span className="block text-2xs text-muted">{ALERT_WHY[s]}</span>
                </button>
              </li>
            );
          })}
        </ol>
      </Panel>

      {say && (
        <Note tone={say.startsWith("Alert") ? "info" : "caution"}>
          {say}
        </Note>
      )}

      {closing && (
        <Panel className="p-3">
          <PanelHeader
            title="Close this alert"
            hint="Closing without investigating is allowed — say why in one line so the record is worth reading later."
          />
          <div className="flex flex-wrap items-end gap-2 pt-2">
            <label className="flex-1">
              <span className="eyebrow">Reason</span>
              <input
                className="field mt-1 w-full"
                value={note}
                onChange={(e) => setNote(e.target.value)}
                placeholder="e.g. site visit done on 4 June, work is recorded"
                autoFocus
              />
            </label>
            <Button variant="primary" disabled={!note.trim() || busyId === closing.alert_id} onClick={confirmClose}>
              Close alert
            </Button>
            <Button variant="ghost" onClick={() => setClosing(null)}>
              Cancel
            </Button>
          </div>
        </Panel>
      )}

      <Panel className="overflow-hidden">
        <div className="flex items-center justify-between gap-2 border-b border-line px-3 py-2">
          <p className="text-xs text-secondary">
            {list.status === "loading"
              ? "Loading alerts…"
              : `${count(data?.total ?? 0)} alert${data?.total === 1 ? "" : "s"}`}
            {filtered && " with this filter"}
            {list.refetching && " · refreshing"}
          </p>
          {filtered && (
            <button type="button" className="btn btn-ghost btn-sm" onClick={clear}>
              Clear filter
            </button>
          )}
        </div>

        {list.error ? (
          <ErrorState
            title="Alerts could not be loaded"
            body="Nothing has been changed. Try again, or copy the address and send it to the data team."
            onRetry={list.reload}
          />
        ) : list.status === "loading" ? (
          <Loading label="Loading alerts" />
        ) : !data?.items.length ? (
          <Empty
            title={values.state ? "No alerts at this step" : "No alerts are open"}
            body={
              values.state
                ? "Nothing sits at this step in your area. That is a real answer, not an error."
                : "No work in your area is currently asking for a look. Open the review queue to see the works themselves."
            }
          />
        ) : (
          <>
            <ul className="divide-y divide-[var(--line)]">
              {data.items.map((a) => (
                <li key={a.alert_id} className="px-3 py-2.5">
                  <div className="flex flex-wrap items-start gap-x-3 gap-y-1.5">
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <BandBadge band={a.band} limited={null} size="sm" />
                        <Pill glyph="◎">{ALERT_LABEL[a.state]}</Pill>
                        <Link
                          href={workHref(a.work_id)}
                          className="truncate text-sm font-medium text-navy underline-offset-2 hover:underline"
                        >
                          {workType(a.work_type_code)}
                        </Link>
                        <span className="tnum text-2xs text-muted">{a.work_id}</span>
                      </div>
                      <p className="mt-0.5 line-clamp-1 text-xs text-secondary">{a.description}</p>
                      <p className="mt-0.5 text-2xs text-muted">
                        {[a.district_name, a.state_name].filter(Boolean).join(", ")} ·{" "}
                        <span className="tnum"> {inr(a.amount)}</span> · opened{" "}
                        <time dateTime={a.opened_at}>{a.opened_at.slice(0, 10)}</time>
                        {a.case_size && a.case_size > 1 && ` · one case of ${a.case_size} alike works`}
                      </p>
                      {a.note && (
                        <p className="mt-1 border-l-2 border-[var(--line-strong)] pl-2 text-2xs text-muted">
                          {a.actor ? <span className="font-medium text-secondary">{a.actor}: </span> : null}
                          {a.note}
                        </p>
                      )}
                    </div>
                    <div className="flex shrink-0 flex-wrap items-center gap-1.5">
                      {NEXT[a.state].length === 0 ? (
                        <span className="text-2xs text-muted">Closed {a.updated_at.slice(0, 10)}</span>
                      ) : (
                        NEXT[a.state].map((next) => (
                          <Button
                            key={next}
                            size="sm"
                            variant={next === "RESOLVED" ? "ghost" : next === "ACKNOWLEDGED" ? "primary" : "secondary"}
                            disabled={busyId === a.alert_id}
                            title={ALERT_WHY[next]}
                            onClick={() => move(a, next)}
                          >
                            {ALERT_ACTION[next]}
                          </Button>
                        ))
                      )}
                    </div>
                  </div>
                </li>
              ))}
            </ul>
            <Pager page={data.page} total={data.total} size={data.page_size} onPage={setPage} />
          </>
        )}
      </Panel>

      <p className="text-2xs text-muted">
        Alerts are opened from the assessment run, never by hand, so the list can always be
        rebuilt from the works. Moving or closing an alert never changes a score.
      </p>
    </div>
  );
}

const ALERT_WHY: Record<AlertState, string> = {
  NEW: "the engines asked for a look, nobody has picked it up",
  ACKNOWLEDGED: "an officer has seen it",
  INVESTIGATING: "someone is checking it now",
  RESOLVED: "closed, with a reason on the record",
};

const ALERT_ACTION: Record<AlertState, string> = {
  NEW: "Acknowledge",
  ACKNOWLEDGED: "Start investigating",
  INVESTIGATING: "Resolve",
  RESOLVED: "Resolve",
};

function Pager({
  page,
  total,
  size,
  onPage,
}: {
  page: number;
  total: number;
  size: number;
  onPage: (p: number) => void;
}) {
  const last = Math.max(1, Math.ceil(total / size));
  if (last <= 1) return null;
  return (
    <nav className="flex items-center justify-between border-t border-line px-3 py-2 text-2xs text-muted" aria-label="Alert pages">
      <span className="tnum">
        Page {page} of {last}
      </span>
      <span className="flex gap-1.5">
        <Button size="sm" disabled={page <= 1} onClick={() => onPage(page - 1)}>
          ← Previous
        </Button>
        <Button size="sm" disabled={page >= last} onClick={() => onPage(page + 1)}>
          Next →
        </Button>
      </span>
    </nav>
  );
}