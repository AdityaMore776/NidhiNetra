"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { AgentCard } from "@/components/AgentCard";
import { FusionPanel } from "@/components/FusionPanel";
import { useMe } from "@/components/me";
import {
  BandBadge,
  Button,
  ErrorState,
  Loading,
  Note,
  Panel,
  PanelHeader,
  Pill,
  SourceBadge,
} from "@/components/ui";
import { WorkTable } from "@/components/WorkTable";
import { apiPost, ApiError, type WorkDetail, type WorkRow } from "@/lib/api";
import { inr, workType } from "@/lib/format";
import {
  ALERT_LABEL,
  INSPECTION_STEPS,
  LIFECYCLE,
  OUTCOME_LABEL,
  OUTCOME_WHY,
} from "@/lib/tokens";
import { useApi } from "@/lib/useApi";

export default function WorkPage() {
  return (
    <Suspense fallback={<Loading label="Loading the work…" />}>
      <Work />
    </Suspense>
  );
}

function Work() {
  const id = useSearchParams().get("id") ?? "";
  const me = useMe();
  // the detail depends on the id in the address bar, so the key is the query
  const detail = useApi<WorkDetail>(
    id ? `/works/${encodeURIComponent(id)}` : "/works",
    id ? undefined : { q: "" },
  );

  if (!id) {
    return (
      <Panel>
        <PanelHeader title="No work chosen" hint="Open a work from the queue or the works list." />
        <Link href="/queue" className="btn">
          Go to the review queue
        </Link>
      </Panel>
    );
  }
  if (detail.error) {
    const e = detail.error as ApiError;
    return (
      <ErrorState
        title={e.status === 404 ? "This work is not in your area" : "This work could not be loaded"}
        body={
          e.status === 404
            ? "It may not exist, or it sits outside the area you are responsible for. That is a scoping answer, not a missing page."
            : e.message
        }
        onRetry={detail.reload}
      />
    );
  }
  if (detail.status === "loading" || !detail.data) return <Loading label="Loading the work…" />;

  const d = detail.data;
  const w = d.work;
  const a = d.assessment;
  const review = d.review;

  return (
    <div className="space-y-4">
      <Panel>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <SourceBadge source={w.source} />
              <span className="font-mono text-xs text-muted">{w.work_id}</span>
              <BandBadge band={a.band} limited={a.limited} />
            </div>
            <h1 className="mt-2 text-xl font-semibold tracking-tight text-foreground">
              {workType(w.work_type_code)}
            </h1>
            {w.description && (
              <p className="mt-1 max-w-3xl text-sm text-secondary">{w.description}</p>
            )}
          </div>
          <div className="text-right">
            <p className="tnum text-lg font-semibold text-foreground">{inr(w.amount)}</p>
            <p className="text-2xs uppercase tracking-wide text-muted">amount on record</p>
          </div>
        </div>

        <dl className="mt-4 grid grid-cols-2 gap-x-6 gap-y-3 text-sm sm:grid-cols-3 lg:grid-cols-4">
          <Field label="Status" value={w.status} />
          <Field label="District" value={join(w.district_name, w.state_name)} />
          <Field label="Recommended" value={fmtDate(w.recommended_date)} />
          <Field label="Sanctioned" value={fmtDate(w.sanction_date)} />
          <Field label="Completed" value={fmtDate(w.completed_date)} />
          <Field label="Financial year" value={w.fy} />
          <Field label="Implementing agency" value={w.agency_name} />
          <Field label="Constituency" value={w.constituency} />
        </dl>
      </Panel>

      {/* What has happened to this work, in order, with only the dates we hold. */}
      <Panel>
        <PanelHeader
          title="What has happened so far"
          hint="Only steps we hold a date for. A step that has not happened is left out, not guessed."
        />
        {review.timeline.length === 0 ? (
          <p className="text-sm text-muted">
            Nothing beyond the record itself yet. No date has been entered for this work.
          </p>
        ) : (
          <ol className="space-y-0">
            {review.timeline.map((e, i) => {
              const meta = LIFECYCLE[e.step];
              return (
                <li key={`${e.step}-${e.at}-${i}`} className="flex gap-3">
                  <div className="flex flex-col items-center">
                    <span
                      className="mt-1.5 h-2 w-2 rounded-full bg-accent"
                      aria-hidden
                    />
                    {i < review.timeline.length - 1 && (
                      <span className="w-px flex-1 bg-line" aria-hidden />
                    )}
                  </div>
                  <div className="pb-4">
                    <p className="text-sm font-medium text-foreground">
                      {meta?.label ?? e.what}
                      <span className="ml-2 font-normal text-muted">{fmtDate(e.at)}</span>
                    </p>
                    <p className="text-xs text-secondary">{e.what}</p>
                  </div>
                </li>
              );
            })}
          </ol>
        )}
      </Panel>

      <div className="grid gap-4 lg:grid-cols-3">
        <ReviewPanel
          review={review}
          workId={id}
          me={me?.user_id ?? null}
          onChanged={detail.reload}
        />
        <div className="space-y-4 lg:col-span-2">
          <AlikeWorks workId={id} />
        </div>
      </div>

      <Panel>
        <PanelHeader title="Why this work is in front of you" hint={a.headline ?? undefined} />
        <FusionPanel a={a} />
      </Panel>

      {a.validation.length > 0 && (
        <Panel>
          <PanelHeader title="Data validation" hint="What the record itself is missing or odd." />
          <ul className="space-y-2 text-sm">
            {a.validation.map((i) => (
              <li key={i.code} className="flex gap-2">
                <Pill glyph={i.severity === "WARN" ? "!" : "i"} ink={i.severity === "WARN" ? "var(--medium-ink)" : undefined}
                  tint={i.severity === "WARN" ? "var(--medium-tint)" : undefined}>
                  {i.severity === "WARN" ? "check" : "note"}
                </Pill>
                <span className="text-secondary">{i.message}</span>
              </li>
            ))}
          </ul>
        </Panel>
      )}

      <Panel>
        <PanelHeader
          title="Every check that looked at this work"
          hint="Including the ones that could not look, which is why a low band is not a clean chit."
        />
        <div className="grid gap-3 lg:grid-cols-2">
          {a.agents.map((r) => (
            <AgentCard key={r.agent} result={r} />
          ))}
        </div>
      </Panel>

      <Note>
        Assessed {new Date(a.assessed_at).toLocaleString("en-IN")} · snapshot {me?.snapshot_date ?? "unknown"}.
        Every figure above comes from the eSAKSHI record and the engine outputs stored for it. Nothing on
        this page was estimated.
      </Note>
    </div>
  );
}

/** The alert on this work, the visit behind it, and the one button an officer needs here. */
function ReviewPanel({
  review,
  workId,
  me,
  onChanged,
}: {
  review: WorkDetail["review"];
  workId: string;
  me: string | null;
  onChanged: () => void;
}) {
  const [asking, setAsking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [note, setNote] = useState("");
  const visit = review.inspection;
  const alert = review.alert;

  const atGround = visit ? ["FIELD_VERIFIED", "RESULT_RECORDED", "CLOSED"].includes(visit.state) : false;

  async function ask() {
    setAsking(true);
    setError(null);
    try {
      await apiPost("/inspections", { work_id: workId, note: note.trim() || undefined, requested_by: me });
      setNote("");
      onChanged();
    } catch (e) {
      setError((e as ApiError).message ?? "That did not go through.");
    } finally {
      setAsking(false);
    }
  }

  return (
    <Panel as="aside">
      <PanelHeader title="Your side of this work" hint="What has been asked, and what came back." />

      {alert && (
        <div className="mb-3 rounded border border-line bg-sunken p-3">
          <div className="flex items-center justify-between gap-2">
            <span className="text-xs font-semibold uppercase tracking-wide text-muted">
              Alert
            </span>
            <Pill glyph="!" ink={alert.state === "RESOLVED" ? undefined : "var(--high-ink)"}
              tint={alert.state === "RESOLVED" ? undefined : "var(--high-tint)"}>
              {ALERT_LABEL[alert.state]}
            </Pill>
          </div>
          <p className="mt-1 text-sm text-foreground">{alert.code.replace(/_/g, " ").toLowerCase()}</p>
          <p className="mt-1 text-2xs text-muted">
            opened {fmtDate(alert.opened_at)}
            {alert.actor ? ` by ${alert.actor}` : ""}
          </p>
          {alert.note && <p className="mt-2 text-xs text-secondary">{alert.note}</p>}
        </div>
      )}

      {visit ? (
        <div className="rounded border border-line bg-sunken p-3">
          <div className="flex items-center justify-between gap-2">
            <span className="text-xs font-semibold uppercase tracking-wide text-muted">Site visit</span>
            <Pill glyph="→" >
              {INSPECTION_STEPS[visit.state]?.label ?? visit.state}
            </Pill>
          </div>
          <p className="mt-1 text-xs text-secondary">
            {INSPECTION_STEPS[visit.state]?.why ?? "in progress"}
          </p>
          <dl className="mt-2 space-y-1 text-xs text-secondary">
            <Row k="Asked by" v={visit.requested_by ?? "not recorded"} />
            <Row k="Officer going out" v={visit.assigned_to ?? "nobody assigned yet"} />
            <Row k="Due" v={fmtDate(visit.due_date) ?? "not set"} />
          </dl>
          {visit.result && (
            <div className="mt-3 rounded border border-line-strong bg-surface p-2">
              <p className="text-xs font-semibold text-foreground">
                {OUTCOME_LABEL[visit.result.outcome] ?? visit.result.outcome}
              </p>
              <p className="mt-0.5 text-2xs text-muted">
                {OUTCOME_WHY[visit.result.outcome] ?? ""}
              </p>
              {visit.result.observed && (
                <p className="mt-1 text-xs text-secondary">{visit.result.observed}</p>
              )}
              <p className="mt-1 text-2xs text-muted">
                recorded {fmtDate(visit.result.recorded_at)}
                {visit.result.recorded_by ? ` by ${visit.result.recorded_by}` : ""}
              </p>
            </div>
          )}
          <Link href="/inspections" className="btn btn-ghost mt-3 w-full">
            Open in the planner
          </Link>
        </div>
      ) : (
        <div className="rounded border border-dashed border-line-strong p-3">
          <p className="text-sm text-secondary">
            No site visit has been asked for. Asking for one puts this work on a field officer&apos;s list; it
            does not change the risk score.
          </p>
          <label className="mt-3 block text-xs font-medium text-foreground" htmlFor="visit-note">
            Why a visit is needed <span className="font-normal text-muted">(optional)</span>
          </label>
          <input
            id="visit-note"
            className="field mt-1"
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder="e.g. the culvert is not visible from the road"
            maxLength={1000}
          />
          <Button className="mt-3 w-full" onClick={ask} disabled={asking}>
            {asking ? "Asking…" : "Ask for a site visit"}
          </Button>
          {error && <p className="mt-2 text-xs text-high">{error}</p>}
        </div>
      )}

      {alert && visit && atGround && (
        <p className="mt-3 text-2xs text-muted">
          The visit reached the ground. Close the alert from the{" "}
          <Link href="/alerts" className="underline">
            alerts list
          </Link>{" "}
          with a line saying what was found — that note is the audit trail.
        </p>
      )}
    </Panel>
  );
}

/** Alike works: one question, so they must be answered together. */
function AlikeWorks({ workId }: { workId: string }) {
  const members = useApi<{ members: WorkRow[]; case_size: number }>(
    `/works/${encodeURIComponent(workId)}/case`,
  );
  if (members.status === "loading") return <Loading label="Checking for alike works…" />;
  if (members.error) {
    return (
      <Panel>
        <PanelHeader title="Alike works" />
        <p className="text-sm text-muted">
          Could not check whether this work belongs to a group. The work itself is unaffected.
        </p>
      </Panel>
    );
  }
  const rows = (members.data?.members ?? []).filter((m) => m.work_id !== workId);
  if (!rows.length) {
    return (
      <Panel>
        <PanelHeader title="Alike works" hint="This work stands on its own." />
        <p className="text-sm text-muted">
          No other work here was filed as part of the same purchase or project.
        </p>
      </Panel>
    );
  }
  return (
    <Panel>
      <PanelHeader
        title="Alike works"
        hint={`${members.data?.case_size ?? rows.length + 1} works filed as one question. They should be looked at together, not one at a time.`}
      />
      <WorkTable items={rows} dense showWhy={false} />
    </Panel>
  );
}

function Row({ k, v }: { k: string; v: string }) {
  return (
    <div className="flex justify-between gap-3">
      <dt className="text-muted">{k}</dt>
      <dd className="text-right text-foreground">{v}</dd>
    </div>
  );
}

function Field({ label, value }: { label: string; value: string | null | undefined }) {
  return (
    <div>
      <dt className="text-2xs uppercase tracking-wide text-muted">{label}</dt>
      <dd className="text-sm text-foreground">{value || "—"}</dd>
    </div>
  );
}

function join(...parts: (string | null | undefined)[]) {
  return parts.filter(Boolean).join(", ") || null;
}

/** Dates are shown as they are stored: an ISO day needs no reformatting to be readable,
 *  and a timestamp says when in the day an officer acted. */
function fmtDate(value: string | null | undefined): string | null {
  if (!value) return null;
  const day = /^\d{4}-\d{2}-\d{2}$/.test(value);
  const d = new Date(day ? `${value}T00:00:00` : value);
  if (Number.isNaN(d.getTime())) return value;
  return day
    ? d.toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" })
    : d.toLocaleString("en-IN", { day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" });
}