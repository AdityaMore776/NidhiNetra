"use client";

import Link from "next/link";
import dynamic from "next/dynamic";
import { useEffect, useState } from "react";
import {
  api,
  type AssessmentCoverage,
  type DistrictRow,
  type FindingRow,
  type OfficeHabit,
  type OfficeRow,
  type Page as PageT,
  type Summary,
  type WorkRow,
} from "@/lib/api";
import { agentMeta, BAND_LABEL, count, inr } from "@/lib/format";
import { BAND_ORDER, QUEUE_BANDS } from "@/lib/tokens";
import { useMe } from "@/components/me";
import { BandBadge, ErrorState, Loading, Metric, Panel, PanelHeader, Pill } from "@/components/ui";
import { WorkTable } from "@/components/WorkTable";

// MapLibre is a large library and nothing else on this screen needs it, so the map
// arrives on its own after the numbers are already readable.
const IndiaMap = dynamic(() => import("@/components/IndiaMap").then((m) => m.IndiaMap), {
  ssr: false,
  loading: () => <div className="skeleton h-72" aria-hidden />,
});

/**
 * The overview.
 *
 * Ordered the way an officer actually starts work: what needs a look, what each
 * check could and could not read, where it is, which offices have a habit worth
 * one conversation, and only then the queue itself. Every number here is measured
 * by a script whose output is saved in data/trial/results; none is estimated.
 */
export default function Dashboard() {
  const me = useMe();
  const [s, setS] = useState<Summary | null>(null);
  const [cover, setCover] = useState<AssessmentCoverage | null>(null);
  const [districts, setDistricts] = useState<DistrictRow[]>([]);
  const [top, setTop] = useState<WorkRow[]>([]);
  const [offices, setOffices] = useState<OfficeRow[]>([]);
  const [habits, setHabits] = useState<OfficeHabit[]>([]);
  const [findings, setFindings] = useState<FindingRow[]>([]);
  const [error, setError] = useState<unknown>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const ac = new AbortController();
    const get = <T,>(path: string) =>
      api<T>(path, undefined, ac.signal).then((d) => d).catch((e: unknown) => {
        if (!(e instanceof DOMException && e.name === "AbortError")) setError(e);
        return null;
      });
    void Promise.all([
      get<Summary>("/dashboard/summary").then((d) => d && setS(d)),
      get<AssessmentCoverage>("/dashboard/assessment").then((d) => d && setCover(d)),
      get<DistrictRow[]>("/dashboard/districts").then((d) => d && setDistricts(d)),
      get<PageT<WorkRow>>("/queue").then((d) => d && setTop(d.items.slice(0, 8))),
      get<OfficeRow[]>("/dashboard/offices").then((d) => d && setOffices(d)),
      get<OfficeHabit[]>("/dashboard/office-habits").then((d) => d && setHabits(d)),
      get<FindingRow[]>("/dashboard/findings").then((d) => d && setFindings(d)),
    ]).then(() => setReady(true));
    return () => ac.abort();
  }, []);

  if (error) {
    return (
      <Panel className="p-5">
        <ErrorState
          title="The overview could not be loaded"
          body="Nothing is wrong with the data itself. Try again in a moment; if it keeps happening, send the page address to the data team."
          onRetry={() => window.location.reload()}
        />
      </Panel>
    );
  }
  if (!s) {
    return (
      <div className="space-y-4">
        <div className="skeleton h-8 w-80" />
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {[0, 1, 2, 3].map((i) => (
            <div key={i} className="skeleton h-24" />
          ))}
        </div>
        <Panel>
          <Loading label="Loading the overview" />
        </Panel>
      </div>
    );
  }

  const review = QUEUE_BANDS.reduce((n, b) => n + (s.bands[b] ?? 0), 0);
  const share = s.works ? review / s.works : 0;
  const roleNote =
    me?.role === "MINISTRY"
      ? "All districts and states in this release."
      : me?.role === "STATE"
        ? "One state, as set on your account."
        : me?.role === "DISTRICT"
          ? "One district, as set on your account."
          : "One district, field view.";

  return (
    <div className="space-y-5">
      <header>
        <h1 className="text-xl font-semibold tracking-tight text-foreground">
          {count(s.works)} MPLADS works monitored
        </h1>
        <p className="mt-0.5 max-w-3xl text-xs text-secondary">
          Real works from the eSAKSHI public export, as of{" "}
          <time dateTime={s.snapshot_date}>{s.snapshot_date}</time>. DRISHTI reads every one of them
          and puts the works an officer should verify first at the top. It flags; it never accuses.
          {roleNote && <> {roleNote}</>}
        </p>
      </header>

      {/* ---- the four numbers an officer opens this page for ---- */}
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Metric label="Works assessed" value={count(s.works)} sub={inr(s.amount) + " recommended"} />
        <Metric
          label="Need a look"
          value={count(review)}
          sub={`${(share * 100).toFixed(2)}% of all works`}
          tone="HIGH"
          href="/queue"
        />
        <Metric
          label="Critical"
          value={count(s.bands.CRITICAL ?? 0)}
          sub={`${count(s.bands.HIGH ?? 0)} more at high`}
          tone="CRITICAL"
          href="/queue?band=CRITICAL"
        />
        <Metric
          label="Couldn't check"
          value={cover ? count(cover.not_assessable) : "—"}
          sub="a check had nothing to read"
          href="/works?assess=not_assessable"
        />
      </div>

      {/* ---- risk bands, as one comparable bar ---- */}
      <Panel>
        <PanelHeader
          title="Risk bands across every work"
          hint="Bands come from the score; the band a work sits in is never hidden behind a total."
          actions={
            <Link href="/works" className="btn btn-ghost btn-sm">
              All works →
            </Link>
          }
        />
        <BandBar bands={s.bands} total={s.works} />
      </Panel>

      <div className="grid gap-4 xl:grid-cols-3">
        {/* ---- what the engines could actually read ---- */}
        <Panel className="p-0 xl:col-span-1">
          <PanelHeader
            title="What each check could read"
            hint="A check with nothing to look at says so. It never turns into a low score."
            actions={
              <Link href="/works?assess=not_assessable" className="btn btn-ghost btn-sm">
                See them →
              </Link>
            }
          />
          {cover && (
            <div className="border-t border-line px-3 py-2.5">
              <p className="text-2xs text-muted">{cover.note}</p>
              <dl className="mt-2 grid grid-cols-3 gap-2 text-center">
                <div>
                  <dt className="text-2xs text-muted">With papers</dt>
                  <dd className="tnum text-sm font-semibold">{count(cover.with_evidence)}</dd>
                </div>
                <div>
                  <dt className="text-2xs text-muted">Nothing attached</dt>
                  <dd className="tnum text-sm font-semibold">{count(cover.without_evidence)}</dd>
                </div>
                <div>
                  <dt className="text-2xs text-muted">Limited evidence</dt>
                  <dd className="tnum text-sm font-semibold">{count(cover.not_assessable)}</dd>
                </div>
              </dl>
            </div>
          )}
          <ul className="divide-y divide-[var(--line)] border-t border-line">
            {s.agents.map((a) => {
              const meta = agentMeta(a.id, a.name, a.question);
              return (
                <li key={a.id} className="flex items-start gap-2.5 px-3 py-2">
                  <span
                    aria-hidden
                    className="mt-px grid h-6 w-6 shrink-0 place-items-center rounded text-2xs font-bold"
                    style={{ color: "#fff", background: meta.color }}
                  >
                    {meta.n}
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-baseline gap-2">
                      <span className="text-sm font-medium text-foreground">{meta.name}</span>
                      {a.built ? (
                        <span className="tnum text-2xs text-muted">
                          {count(a.alerts)} with a finding
                        </span>
                      ) : (
                        <Pill glyph="◌">in development</Pill>
                      )}
                    </div>
                    <p className="text-2xs text-muted">{a.question}</p>
                    {a.weight_note && (
                      <p className="mt-0.5 text-2xs text-muted">{a.weight_note}</p>
                    )}
                  </div>
                </li>
              );
            })}
          </ul>
        </Panel>

        {/* ---- where ---- */}
        <Panel className="p-0 xl:col-span-2">
          <PanelHeader
            title="Where the works needing a look are"
            hint="Shaded by the share of a district's works that are in the queue. Click a district to open its works."
            actions={
              <Link href="/works" className="btn btn-ghost btn-sm">
                District list →
              </Link>
            }
          />
          <div className="px-3 pb-3">
            {districts.length ? <IndiaMap rows={districts} /> : <div className="skeleton h-72" />}
          </div>
        </Panel>
      </div>

      {/* ---- what the engines found ---- */}
      {findings.length > 0 && (
        <Panel className="p-0">
          <PanelHeader
            title="What the engines found on queued works"
            hint="Every finding raised on a work currently in the review queue. The queue stores full detail, so these counts are complete; a low work keeps only its summary and is never counted here."
          />
          <FindingBars rows={findings} />
        </Panel>
      )}

      {/* ---- office patterns: one conversation, not one queue item per work ---- */}
      {habits.length > 0 && (
        <Panel className="p-0">
          <PanelHeader
            title="Offices with an unusual habit"
            hint="Offices that price most of their works just under a limit, or record constructions complete within a week of sanction, far more often than the scheme as a whole. A habit of the office, listed once — look at its works together. Never a judgement about a Member of Parliament."
          />
          <div className="overflow-x-auto border-t border-line">
            <table className="data-table">
              <thead>
                <tr>
                  <th scope="col">Office</th>
                  <th scope="col">Habit</th>
                  <th scope="col" className="text-right">Its works</th>
                  <th scope="col" className="text-right">vs the scheme</th>
                </tr>
              </thead>
              <tbody>
                {habits.slice(0, 10).map((o) => (
                  <tr key={`${o.district_lgd}|${o.office}|${o.habit}`}>
                    <td>
                      {o.office}
                      {o.district_name && <div className="text-2xs text-muted">{o.district_name}</div>}
                    </td>
                    <td className="text-secondary">{o.habit}</td>
                    <td className="tnum whitespace-nowrap text-right">
                      {count(o.count)} of {count(o.total)} ({(o.share * 100).toFixed(0)}%)
                    </td>
                    <td className="tnum whitespace-nowrap text-right">
                      {(o.national * 100).toFixed(1)}% · {o.lift.toFixed(0)}× higher
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {habits.length > 10 && (
            <p className="border-t border-line px-3 py-1.5 text-2xs text-muted">
              and {(habits.length - 10).toLocaleString("en-IN")} more offices.
            </p>
          )}
        </Panel>
      )}

      {offices.length > 0 && (
        <Panel className="p-0">
          <PanelHeader
            title="Offices whose completion dates need checking as a whole"
            hint="These offices record many works as completed before they were recommended. That is a recording habit, so it is listed once per office instead of filling the queue work by work."
          />
          <div className="overflow-x-auto border-t border-line">
            <table className="data-table">
              <thead>
                <tr>
                  <th scope="col">Implementing office</th>
                  <th scope="col">District</th>
                  <th scope="col" className="text-right">Dated before recommendation</th>
                  <th scope="col" className="text-right">vs national rate</th>
                </tr>
              </thead>
              <tbody>
                {offices.slice(0, 10).map((o) => (
                  <tr key={o.agency_name}>
                    <td>{o.agency_name}</td>
                    <td className="whitespace-nowrap">
                      {o.district_name}
                      <div className="text-2xs text-muted">{o.state_name}</div>
                    </td>
                    <td className="tnum whitespace-nowrap text-right">
                      {count(o.bad)} of {count(o.completed)} ({(o.rate * 100).toFixed(1)}%)
                    </td>
                    <td className="tnum whitespace-nowrap text-right font-medium">
                      {o.lift.toFixed(0)}× higher
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>
      )}

      {/* ---- the queue itself ---- */}
      <section className="space-y-2">
        <div className="flex flex-wrap items-end justify-between gap-2">
          <div>
            <h2 className="text-base font-semibold">Top of the review queue</h2>
            <p className="text-2xs text-muted">
              Highest money at stake first. Every row opens the work&apos;s own evidence page.
            </p>
          </div>
          <div className="flex gap-2">
            <Link href="/alerts" className="btn btn-ghost btn-sm">
              Alerts →
            </Link>
            <Link href="/inspections" className="btn btn-sm">
              Inspection planner →
            </Link>
          </div>
        </div>
        <Panel className="overflow-hidden">
          <WorkTable
            items={top}
            emptyTitle="Nothing in the queue"
            emptyBody="No work in your area is currently asking for a look. That is a real answer, not an error."
          />
        </Panel>
      </section>

      <p className="text-2xs text-muted">
        Figures come from scripts kept in <code>data/trial/results</code>.{" "}
        {ready ? "" : ""}Snapshot {s.snapshot_date}. DRISHTI flags works that need verification;
        officers decide.
      </p>
    </div>
  );
}

/** One stacked bar, every band labelled beside it. Never colour on its own. */
function BandBar({ bands, total }: { bands: Summary["bands"]; total: number }) {
  return (
    <div className="px-3 pb-3">
      <div
        className="meter"
        role="img"
        aria-label={BAND_ORDER.map((b) => `${BAND_LABEL[b]}: ${bands[b] ?? 0} works`).join(", ")}
      >
        {BAND_ORDER.map((b) => {
          const n = bands[b] ?? 0;
          if (!n) return null;
          return (
            <span
              key={b}
              style={{ width: `${(n / Math.max(1, total)) * 100}%`, background: `var(--${b.toLowerCase()}-mark)` }}
            />
          );
        })}
      </div>
      <ul className="mt-2 flex flex-wrap gap-x-4 gap-y-1">
        {BAND_ORDER.map((b) => {
          const n = bands[b] ?? 0;
          return (
            <li key={b} className="flex items-center gap-1.5 text-2xs">
              <span
                aria-hidden
                className="h-2.5 w-2.5 rounded-sm"
                style={{ background: `var(--${b.toLowerCase()}-mark)`, border: `1px solid var(--${b.toLowerCase()}-edge)` }}
              />
              <BandBadge band={b} size="sm" />
              <span className="tnum text-secondary">{count(n)}</span>
              <span className="text-muted">({total ? ((n / total) * 100).toFixed(1) : "0.0"}%)</span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

/** Findings as horizontal bars. The label and the number always travel with the bar. */
function FindingBars({ rows }: { rows: FindingRow[] }) {
  const max = Math.max(...rows.map((r) => r.works), 1);
  const shown = rows.slice(0, 12);
  return (
    <div className="border-t border-line px-3 py-2">
      <ul className="space-y-1.5">
        {shown.map((f) => {
          const meta = agentMeta(f.agent, f.name, f.question);
          return (
            <li key={`${f.agent}-${f.code}`} className="grid grid-cols-[1fr_auto] items-center gap-2">
              <div className="min-w-0">
                <div className="flex items-baseline gap-1.5">
                  <span
                    aria-hidden
                    className="grid h-4 w-4 shrink-0 place-items-center rounded text-[9px] font-bold"
                    style={{ color: "#fff", background: meta.color }}
                  >
                    {meta.n}
                  </span>
                  <Link
                    href={`/queue?finding=${encodeURIComponent(f.code)}`}
                    className="truncate text-xs text-foreground underline-offset-2 hover:underline"
                  >
                    {f.text}
                  </Link>
                  {f.hard && (
                    <span className="text-2xs text-muted" title="A serious finding on its own is enough to raise the band.">
                      serious
                    </span>
                  )}
                </div>
                <div className="meter mt-1">
                  <span
                    style={{ width: `${(f.works / max) * 100}%`, background: meta.color }}
                  />
                </div>
              </div>
              <span className="tnum whitespace-nowrap text-xs text-secondary">
                {count(f.works)} {f.works === 1 ? "work" : "works"}
              </span>
            </li>
          );
        })}
      </ul>
      {rows.length > shown.length && (
        <p className="mt-2 text-2xs text-muted">
          and {(rows.length - shown.length).toLocaleString("en-IN")} more findings —{" "}
          <Link href="/queue" className="underline underline-offset-2">
            the queue lists them per work
          </Link>
          .
        </p>
      )}
    </div>
  );
}