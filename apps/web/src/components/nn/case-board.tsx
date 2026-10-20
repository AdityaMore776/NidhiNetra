"use client";

import { History, Layers, ShieldCheck } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import { api, ApiError, apiPost, type AlertEntry, type AlertPage, type AlertRow, type AlertState } from "@/lib/api";
import { inr, workHref, workType } from "@/lib/format";
import { cn } from "@/lib/utils";
import { BandBadge } from "./badges";
import { Pager } from "./work-table";
import { Segmented } from "./segmented";

/** plain words, not office jargon (the engine's drishti/alerts.py LABELS say the same) */
const LABEL: Record<AlertState, string> = {
  NEW: "Not read yet",
  TRIAGED: "Read by the office",
  IN_PLAN: "Visit planned",
  INSPECTED: "Site visited",
  ISSUE_CONFIRMED: "Problem found",
  CLEARED: "No problem found",
  CLOSED: "Closed",
};
/** what each step means, shown on the page and in the confirm box */
const MEANS: Record<AlertState, string> = {
  NEW: "NidhiNetra flagged this work. No officer has read it yet.",
  TRIAGED: "A district officer has read why it was flagged, and will either plan a site visit or close it with a reason.",
  IN_PLAN: "An officer is to go and see the work at the site.",
  INSPECTED: "An officer has been to the site. What they saw is still to be written down.",
  ISSUE_CONFIRMED: "At the site, the work did not match what was filed. The officer's note says what was seen.",
  CLEARED: "At the site, the work matched what was filed.",
  CLOSED: "Nothing more to do. The full history is kept.",
};
const ORDER = Object.keys(LABEL) as AlertState[];
/** the engine asks for a note on these moves (drishti/alerts.py NOTE_NEEDED) */
const NOTE_NEEDED = new Set(["INSPECTED>ISSUE_CONFIRMED", "INSPECTED>CLEARED", "TRIAGED>CLOSED"]);
const CHIP: Record<AlertState, string> = {
  NEW: "border-brand-200 bg-brand-50 text-brand-800",
  TRIAGED: "border-brand-300 bg-brand-100 text-brand-900",
  IN_PLAN: "border-brand-300 bg-brand-100 text-brand-900",
  INSPECTED: "border-brand-300 bg-brand-100 text-brand-900",
  ISSUE_CONFIRMED: "border-[var(--high)] bg-[color-mix(in_srgb,var(--high)_12%,transparent)] text-foreground",
  CLEARED: "border-[var(--teal)] bg-[color-mix(in_srgb,var(--teal)_12%,transparent)] text-foreground",
  CLOSED: "border-border bg-muted text-muted-foreground",
};
/** each button says what the officer is doing */
function moveText(from: AlertState, to: AlertState): string {
  if (to === "CLOSED") return from === "TRIAGED" ? "Close without a visit" : "Close the case";
  return {
    NEW: LABEL.NEW,
    TRIAGED: "I have read it",
    IN_PLAN: "Plan a site visit",
    INSPECTED: "The site has been visited",
    ISSUE_CONFIRMED: "Problem found at the site",
    CLEARED: "No problem found at the site",
  }[to];
}

type Filter = "" | AlertState;

export function StateChip({ state }: { state: AlertState }) {
  return <span className={cn("inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] font-semibold", CHIP[state])}>{LABEL[state]}</span>;
}

/**
 * The review queue's cases as an officer works them (T060): Not read yet -> Read by the office -> Visit
 * planned -> Site visited -> Problem found / No problem found -> Closed. Staff only; each move is checked by the engine (who may make it,
 * from which state) and written to a hash-chained audit log, shown under "History".
 */
export function CaseBoard() {
  const [filter, setFilter] = useState<Filter>("");
  const [page, setPage] = useState(1);
  const [data, setData] = useState<AlertPage | null>(null);
  const [off, setOff] = useState<string | null>(null);
  const [moving, setMoving] = useState<{ row: AlertRow; to: AlertState } | null>(null);

  const load = useCallback(() => {
    api<AlertPage>("/alerts", { state: filter || undefined, page })
      .then((p) => {
        setData(p);
        setOff(null);
      })
      .catch((e) => setOff(e instanceof ApiError && e.status === 503 ? "Case tracking is not switched on for this database yet." : String(e.message ?? e)));
  }, [filter, page]);

  useEffect(() => {
    load();
  }, [load]);

  const counts = data?.counts;
  const open = counts ? ORDER.filter((s) => s !== "CLOSED").reduce((n, s) => n + counts[s], 0) : null;

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-brand-900">Case status</h2>
          <p className="max-w-2xl text-sm text-muted-foreground">
            Every case from the queue, as your office works it. Each move is checked (who may make it, and from which step) and written to a log that cannot be edited afterwards.
          </p>
        </div>
        <span className="inline-flex items-center gap-1.5 text-xs text-muted-foreground">
          <ShieldCheck className="size-3.5" /> Tamper-evident history
        </span>
      </div>
      <details open className="panel px-4 py-3 text-sm sm:px-5">
        <summary className="cursor-pointer font-medium text-brand-900">What each step means</summary>
        <ol className="mt-2 grid gap-x-6 gap-y-1.5 sm:grid-cols-2">
          {ORDER.map((s, i) => (
            <li key={s} className="flex gap-2">
              <span className="num w-4 shrink-0 text-xs text-muted-foreground">{i + 1}.</span>
              <span>
                <StateChip state={s} /> <span className="text-xs text-muted-foreground">{MEANS[s]}</span>
              </span>
            </li>
          ))}
        </ol>
      </details>
      {off ? (
        <div className="panel px-5 py-6 text-sm text-muted-foreground">{off}</div>
      ) : (
        <>
          <div className="overflow-x-auto pb-1">
            <Segmented<Filter>
              size="sm"
              value={filter}
              onChange={(f) => {
                setFilter(f);
                setPage(1);
              }}
              options={[{ value: "" as Filter, label: "All not closed", count: open }, ...ORDER.map((s) => ({ value: s as Filter, label: LABEL[s], count: counts?.[s] ?? null }))]}
            />
          </div>
          <ul className="panel divide-y overflow-hidden">
            {!data &&
              Array.from({ length: 3 }).map((_, i) => (
                <li key={`s${i}`} className="px-5 py-4">
                  <div className="h-4 w-2/3 rounded-md skeleton-shimmer" />
                  <div className="mt-2 h-3 w-1/2 rounded-md skeleton-shimmer" />
                </li>
              ))}
            {data?.items.map((row) => <CaseRow key={row.alert_id} row={row} onMove={(to) => setMoving({ row, to })} />)}
            {data && data.items.length === 0 && <li className="px-5 py-10 text-center text-sm text-muted-foreground">No cases at this step.</li>}
          </ul>
          {data && <Pager page={data.page} total={data.total} size={data.page_size} onPage={setPage} />}
        </>
      )}
      <MoveDialog
        key={moving ? `${moving.row.alert_id}>${moving.to}` : "none"}
        moving={moving}
        onClose={() => setMoving(null)}
        onDone={() => {
          setMoving(null);
          load();
        }}
      />
    </section>
  );
}

function CaseRow({ row, onMove }: { row: AlertRow; onMove: (to: AlertState) => void }) {
  const [trail, setTrail] = useState<AlertEntry[] | null>(null);
  const [showing, setShowing] = useState(false);

  function toggle() {
    const next = !showing;
    setShowing(next);
    if (next) api<{ trail: AlertEntry[] }>(`/alerts/${row.alert_id}`).then((a) => setTrail(a.trail), () => setTrail([]));
  }

  return (
    <li className="px-4 py-4 sm:px-5">
      <div className="flex flex-wrap items-start gap-x-3 gap-y-1.5">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <Link href={workHref(row.work_id)} className="font-medium text-brand-900 underline-offset-4 hover:underline">
              {workType(row.work_type_code)}
            </Link>
            <StateChip state={row.state} />
            {!row.in_queue && <span className="text-[11px] text-muted-foreground">no longer in the queue</span>}
          </div>
          <div className="mt-0.5 line-clamp-2 text-xs text-muted-foreground">{row.description}</div>
          <div className="mt-1 flex flex-wrap items-baseline gap-x-2 text-xs">
            <span className="font-medium">{row.district_name ?? "—"}</span>
            <span className="text-muted-foreground">{row.state_name}</span>
            <span className="num font-semibold">{inr(row.amount)}</span>
            {row.case_size && row.case_size > 1 ? (
              <span className="inline-flex items-center gap-1 text-[11px] text-muted-foreground">
                <Layers className="size-3" /> {row.case_size} alike works
              </span>
            ) : null}
          </div>
          {row.note && <p className="mt-1.5 rounded-lg border-l-2 border-brand-200 bg-muted/70 px-2.5 py-1.5 text-xs text-foreground/80">{row.note}</p>}
        </div>
        <BandBadge band={row.band} size="sm" />
      </div>
      <div className="mt-2.5 flex flex-wrap items-center gap-2">
        {row.moves.map((to) => (
          <Button key={to} size="sm" variant={to === "CLOSED" ? "outline" : "default"} onClick={() => onMove(to)}>
            {moveText(row.state, to)}
          </Button>
        ))}
        <Button size="sm" variant="ghost" onClick={toggle} aria-expanded={showing}>
          <History className="size-3.5" /> History
        </Button>
      </div>
      {showing && (
        <ol className="mt-2 space-y-1 border-l border-brand-200 pl-3 text-xs">
          {trail === null && <li className="text-muted-foreground">Loading…</li>}
          {trail?.length === 0 && <li className="text-muted-foreground">Nothing yet: no officer has read this case.</li>}
          {trail?.map((e) => (
            <li key={e.seq}>
              <span className="num text-muted-foreground">{new Date(e.at).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" })}</span>{" "}
              <span className="font-medium">{e.action === "open" ? "Case opened" : `Moved from “${LABEL[e.from_state ?? "NEW"]}” to “${LABEL[e.to_state]}”`}</span>{" "}
              <span className="text-muted-foreground">
                by {e.actor_name ?? "an officer"} ({e.actor_role.toLowerCase()})
              </span>
              {e.note && <div className="text-foreground/80">“{e.note}”</div>}
            </li>
          ))}
        </ol>
      )}
    </li>
  );
}

function MoveDialog({ moving, onClose, onDone }: { moving: { row: AlertRow; to: AlertState } | null; onClose: () => void; onDone: () => void }) {
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const needsNote = moving ? NOTE_NEEDED.has(`${moving.row.state}>${moving.to}`) : false;

  async function save() {
    if (!moving) return;
    setBusy(true);
    setError(null);
    try {
      await apiPost(`/alerts/${moving.row.alert_id}`, { from_state: moving.row.state, to_state: moving.to, note: note.trim() || null }, "PATCH");
      onDone();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Dialog open={moving !== null} onOpenChange={(o) => !o && onClose()}>
      <DialogContent>
        {moving && (
          <>
            <DialogHeader>
              <DialogTitle>{moveText(moving.row.state, moving.to)}</DialogTitle>
              <DialogDescription>
                {workType(moving.row.work_type_code)}, {moving.row.district_name ?? "district not known"}. The case will show as “{LABEL[moving.to]}”: {MEANS[moving.to]}
              </DialogDescription>
              <p className="text-xs text-muted-foreground">This step is saved with your name and the time, and cannot be undone or edited later.</p>
            </DialogHeader>
            <label className="space-y-1.5 text-sm">
              <span className="font-medium">
                Note {needsNote ? <span className="text-[var(--high)]">(needed)</span> : <span className="text-muted-foreground">(optional)</span>}
              </span>
              <Textarea
                value={note}
                maxLength={500}
                onChange={(e) => setNote(e.target.value)}
                placeholder={needsNote ? (moving.to === "CLOSED" ? "Why no visit is needed" : "What was seen at the site") : ""}
              />
            </label>
            {error && <p className="text-sm text-[var(--critical)]">{error}</p>}
            <DialogFooter>
              <Button variant="outline" onClick={onClose} disabled={busy}>
                Cancel
              </Button>
              <Button onClick={save} disabled={busy || (needsNote && !note.trim())}>
                {busy ? "Saving…" : "Save this step"}
              </Button>
            </DialogFooter>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}
