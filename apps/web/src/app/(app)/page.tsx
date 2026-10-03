"use client";

import {
  AlertOctagon,
  ArrowRight,
  Building2,
  Camera,
  CheckCircle2,
  IndianRupee,
  Inbox,
  Layers3,
  MapPin,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import dynamic from "next/dynamic";
import Link from "next/link";
import { useMemo, useState } from "react";
import { DistrictScatter, EngineFindings, MoneyTreemap, RiskMix, StatesBar } from "@/components/charts/DashboardCharts";
import type { GlobeMetric } from "@/components/map/IndiaGlobe";
import { Reveal, Stagger, StaggerItem } from "@/components/motion/reveal";
import { useMe } from "@/components/me";
import { PageHeader, SectionHeader, StatTile } from "@/components/nn/layout-bits";
import { WorkTable } from "@/components/nn/work-table";
import { Button } from "@/components/ui/button";
import type { Band, DistrictRow, OfficeHabit, OfficeRow, Page, Summary, WorkRow } from "@/lib/api";
import { useApiData } from "@/lib/cache";
import { BAND_COLOR, BAND_LABEL, count, inr } from "@/lib/format";
import { cn } from "@/lib/utils";

const RiskVortex = dynamic(() => import("@/components/three/RiskVortex"), {
  ssr: false,
  loading: () => <div className="size-full rounded-2xl skeleton-shimmer" />,
});
const IndiaGlobe = dynamic(() => import("@/components/map/IndiaGlobe").then((m) => m.IndiaGlobe), {
  ssr: false,
  loading: () => <div className="size-full rounded-2xl skeleton-shimmer" />,
});

function greeting(): string {
  const h = new Date().getHours();
  return h < 12 ? "Good morning" : h < 17 ? "Good afternoon" : "Good evening";
}

export default function Dashboard() {
  const me = useMe();
  const { data: s } = useApiData<Summary>("/dashboard/summary");
  const { data: districts } = useApiData<DistrictRow[]>("/dashboard/districts");
  const { data: queue } = useApiData<Page<WorkRow>>("/queue");
  const { data: offices } = useApiData<OfficeRow[]>("/dashboard/offices");
  const { data: habits } = useApiData<OfficeHabit[]>("/dashboard/office-habits");
  const [metric, setMetric] = useState<GlobeMetric>("share");
  const [focus, setFocus] = useState<string | null>(null);

  const topDistricts = useMemo(
    () => (districts ?? []).filter((d) => d.review > 0).sort((a, b) => b.review - a.review || b.share - a.share).slice(0, 8),
    [districts],
  );

  const review = s ? (s.bands.CRITICAL ?? 0) + s.bands.HIGH : 0;
  const scope = me?.role === "MINISTRY" ? "All of India" : me?.role === "DISTRICT" ? "Your district" : "Your area";

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow={`${greeting()} · ${scope}`}
        title="Every MPLADS rupee,"
        accent="watched."
        lead={
          <>
            Real works from the eSAKSHI public export{s ? <> (data up to <span className="num font-medium text-foreground">{s.snapshot_date}</span>)</> : null}.
            NidhiNetra ranks which ones an officer should verify first. It flags; it never accuses.
          </>
        }
        actions={
          <>
            <Button asChild variant="outline" className="rounded-xl">
              <Link href="/presanction">
                <ShieldCheck /> Pre-sanction check
              </Link>
            </Button>
            <Button asChild className="rounded-xl bg-brand-gradient shadow-[0_10px_24px_-12px_rgb(10_102_194/0.8)] hover:opacity-95">
              <Link href="/queue">
                <Inbox /> Open review queue <ArrowRight />
              </Link>
            </Button>
          </>
        }
      />

      {/* ---------------------------------------------------------------- hero: figures + 3D */}
      <section className="grid gap-5 lg:grid-cols-12">
        <Stagger className="grid grid-cols-2 gap-4 lg:col-span-5">
          <StaggerItem>
            <StatTile label="Works monitored" value={s?.works ?? 0} icon={<Layers3 className="size-4" />} note="every work on the export, assessed" />
          </StaggerItem>
          <StaggerItem>
            <StatTile
              label="Money recommended"
              value={s?.amount ?? 0}
              format={(v) => inr(v)}
              icon={<IndianRupee className="size-4" />}
              tone="var(--teal)"
              note="across those works"
            />
          </StaggerItem>
          <StaggerItem>
            <StatTile
              label="Need review"
              value={review}
              icon={<Inbox className="size-4" />}
              tone="var(--high)"
              note={s ? <span className="num">{((review / Math.max(1, s.works)) * 100).toFixed(2)}% of works · High + Critical</span> : null}
            />
          </StaggerItem>
          <StaggerItem>
            <StatTile
              label="Critical"
              value={s?.bands.CRITICAL ?? 0}
              icon={<AlertOctagon className="size-4" />}
              tone="var(--critical)"
              note="look at these first"
            />
          </StaggerItem>
          <StaggerItem className="col-span-2">
            <div className="panel flex items-start gap-3 p-4 text-[13px] leading-relaxed text-muted-foreground">
              <Sparkles className="mt-0.5 size-4 shrink-0 text-brand-600" />
              <p>
                A work reaches <b className="text-foreground">High</b> only when two checks agree. A low score where a check could not
                look at the work is marked <b className="text-foreground">limited evidence</b>: it is not a clean chit.
              </p>
            </div>
          </StaggerItem>
        </Stagger>

        <Reveal className="lg:col-span-7" delay={0.1}>
          <div className="panel relative h-[440px] overflow-hidden">
            <div className="absolute inset-0 grid-bg opacity-60 [mask-image:radial-gradient(ellipse_at_center,black,transparent_75%)]" />
            <div className="absolute inset-0">{s && <RiskVortex bands={s.bands} />}</div>
            <div className="pointer-events-none absolute left-5 top-5 max-w-60">
              <div className="eyebrow">The review funnel</div>
              <div className="mt-1 text-lg font-semibold tracking-[-0.02em] text-brand-950">From every work to the few that need a look</div>
            </div>
            <div className="glass absolute bottom-4 right-4 w-56 rounded-xl p-3 shadow-card">
              {(["CRITICAL", "HIGH", "MEDIUM", "LOW"] as Band[]).map((b) => (
                <div key={b} className="flex items-center gap-2 py-0.5 text-xs">
                  <span className="size-2.5 rounded-full" style={{ background: b === "LOW" ? "#9cc4ee" : BAND_COLOR[b] }} />
                  <span className="text-muted-foreground">{BAND_LABEL[b]}</span>
                  <span className="num ml-auto font-semibold text-foreground">{s ? count(s.bands[b] ?? 0) : "—"}</span>
                </div>
              ))}
              <div className="mt-1.5 border-t pt-1.5 text-[10px] leading-snug text-muted-foreground">
                Points are a sample of the works; the counts are exact. Move the pointer: the eye follows.
              </div>
            </div>
          </div>
        </Reveal>
      </section>

      {/* ---------------------------------------------------------------- globe */}
      <Reveal>
        <section className="panel p-5 sm:p-6">
          <SectionHeader
            eyebrow="Geography"
            title="Where the works needing review are"
            description="Each district rises by the measure you pick. Hover a district for its numbers; click it to open its works. Ctrl + scroll to zoom."
          />
          <div className="mt-5 grid gap-5 lg:grid-cols-12">
            <div className="h-[560px] lg:col-span-8">{districts && <IndiaGlobe rows={districts} metric={metric} onMetric={setMetric} focus={focus} className="size-full" />}</div>
            <div className="lg:col-span-4">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold text-brand-950">Districts to look at first</h3>
                <span className="text-[11px] text-muted-foreground">by works needing review</span>
              </div>
              <ol className="mt-3 space-y-2" onMouseLeave={() => setFocus(null)}>
                {topDistricts.map((d, i) => {
                  const max = topDistricts[0]?.review || 1;
                  return (
                    <li key={d.district_lgd}>
                      <Link
                        href={`/works?district=${d.district_lgd}`}
                        onMouseEnter={() => setFocus(d.district_lgd)}
                        className={cn(
                          "group flex items-center gap-3 rounded-xl border bg-white p-3 transition-all hover:-translate-y-0.5 hover:border-brand-200 hover:shadow-card",
                          focus === d.district_lgd && "border-brand-200 shadow-card",
                        )}
                      >
                        <span className="num grid size-7 shrink-0 place-items-center rounded-lg bg-muted font-mono text-[11px] font-semibold text-brand-900">
                          {i + 1}
                        </span>
                        <div className="min-w-0 flex-1">
                          <div className="flex items-baseline gap-1.5">
                            <span className="truncate text-sm font-medium">{d.name}</span>
                            <span className="truncate text-[11px] text-muted-foreground">{d.state}</span>
                          </div>
                          <div className="mt-1.5 h-1 overflow-hidden rounded-full bg-muted">
                            <div className="h-full rounded-full bg-brand-gradient" style={{ width: `${(d.review / max) * 100}%` }} />
                          </div>
                        </div>
                        <div className="text-right">
                          <div className="num text-sm font-semibold">{count(d.review)}</div>
                          <div className="num text-[10px] text-muted-foreground">{(d.share * 100).toFixed(1)}%</div>
                        </div>
                        <MapPin className="size-3.5 text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100" />
                      </Link>
                    </li>
                  );
                })}
                {districts && topDistricts.length === 0 && <li className="text-sm text-muted-foreground">No district has works needing review.</li>}
                {!districts && Array.from({ length: 6 }).map((_, i) => <li key={i} className="h-14 rounded-xl skeleton-shimmer" />)}
              </ol>
            </div>
          </div>
        </section>
      </Reveal>

      {/* ---------------------------------------------------------------- engines + risk mix */}
      <section className="grid gap-5 lg:grid-cols-12">
        <Reveal className="lg:col-span-7">
          <div className="panel h-full p-5 sm:p-6">
            <SectionHeader
              eyebrow="Detect"
              title="What each engine found"
              description="Works where the engine raised something. Faded bars are shown to officers but do not add to the score."
              actions={
                <Button asChild variant="ghost" size="sm" className="text-brand-700">
                  <Link href="/how-it-works">
                    How they work <ArrowRight />
                  </Link>
                </Button>
              }
            />
            <div className="mt-4">{s ? <EngineFindings agents={s.agents} /> : <div className="h-64 rounded-xl skeleton-shimmer" />}</div>
          </div>
        </Reveal>
        <Reveal className="lg:col-span-5" delay={0.08}>
          <div className="panel h-full p-5 sm:p-6">
            <SectionHeader eyebrow="Explain" title="Risk mix" description="How the flagged works split across the bands." />
            <div className="mt-4">{s ? <RiskMix summary={s} /> : <div className="h-64 rounded-xl skeleton-shimmer" />}</div>
          </div>
        </Reveal>
      </section>

      {/* ---------------------------------------------------------------- states + districts */}
      <section className="grid gap-5 lg:grid-cols-12">
        <Reveal className="lg:col-span-5">
          <div className="panel h-full p-5 sm:p-6">
            <SectionHeader eyebrow="States" title="Works needing review, by state" description="Top states by count. Hover for works, share and money." />
            <div className="mt-4">{districts ? <StatesBar rows={districts} /> : <div className="h-80 rounded-xl skeleton-shimmer" />}</div>
          </div>
        </Reveal>
        <Reveal className="lg:col-span-7" delay={0.08}>
          <div className="panel h-full p-5 sm:p-6">
            <SectionHeader
              eyebrow="Districts"
              title="Size against share needing review"
              description="Each dot is a district; its size is the money recommended. Blue dots have works needing review. Click one to open its works."
            />
            <div className="mt-4">{districts ? <DistrictScatter rows={districts} /> : <div className="h-72 rounded-xl skeleton-shimmer" />}</div>
          </div>
        </Reveal>
      </section>

      {/* ---------------------------------------------------------------- money + what the data says */}
      <section className="grid gap-5 lg:grid-cols-12">
        <Reveal className="lg:col-span-8">
          <div className="panel h-full p-5 sm:p-6">
            <SectionHeader eyebrow="Money" title="Where the money goes" description="Each state's block is sized by the money recommended and shaded by its share of works needing review." />
            <div className="mt-4">{districts ? <MoneyTreemap rows={districts} /> : <div className="h-80 rounded-xl skeleton-shimmer" />}</div>
          </div>
        </Reveal>
        <Reveal className="lg:col-span-4" delay={0.08}>
          <div className="panel h-full space-y-4 p-5 sm:p-6">
            <SectionHeader eyebrow="Evidence" title="What the published data can and cannot tell us" />
            <Fact icon={<CheckCircle2 className="size-4" />} tone="var(--low)" title="Checked on every work">
              The export gives each work&apos;s type, description, amount, dates and district: enough for the guideline, price, duplicate and
              delay checks, which run on every work today.
            </Fact>
            <Fact icon={<Camera className="size-4" />} tone="var(--medium)" title="Not in the export">
              No GPS location, no quantities, no site photos. eSAKSHI publishes those for completed works, so the photo and location checks
              are being built on that real evidence.
            </Fact>
            <Fact icon={<MapPin className="size-4" />} tone="var(--brand-600)" title="Why repeats say “check”">
              Without a location, two works can only be matched by their wording, so every repeat is a question, never proof.
            </Fact>
          </div>
        </Reveal>
      </section>

      {/* ---------------------------------------------------------------- offices */}
      {offices && offices.length > 0 && (
        <Reveal>
          <section className="panel p-5 sm:p-6">
            <SectionHeader
              eyebrow="Offices"
              title="Offices whose completion dates need checking"
              description="These offices record many works as completed before they were recommended. That is a record-keeping habit, so it is listed here once per office instead of filling the review queue work by work."
            />
            <OfficeTable
              head={["Implementing office", "District", "Works dated before recommendation", "vs national rate"]}
              rows={offices.slice(0, 8).map((o) => ({
                key: o.agency_name,
                a: o.agency_name,
                b: (
                  <>
                    {o.district_name}
                    <span className="text-xs text-muted-foreground">, {o.state_name}</span>
                  </>
                ),
                c: `${count(o.bad)} of ${count(o.completed)} (${(o.rate * 100).toFixed(1)}%)`,
                lift: o.lift,
              }))}
            />
            {offices.length > 8 && <p className="mt-3 text-xs text-muted-foreground">and {offices.length - 8} more offices.</p>}
          </section>
        </Reveal>
      )}

      {habits && habits.length > 0 && (
        <Reveal>
          <section className="panel p-5 sm:p-6">
            <SectionHeader
              eyebrow="Office patterns"
              title="Offices with an unusual habit"
              description="Offices that price most of their works just under the Rs 5 or 10 lakh limit, or record constructions complete within a week of sanction, far more often than the scheme as a whole. A habit of the office, listed once: look at its works together. Never a judgement about a Member of Parliament."
            />
            <OfficeTable
              head={["Office", "Habit", "Its works", "vs the scheme"]}
              rows={habits.slice(0, 8).map((o) => ({
                key: `${o.district_lgd}|${o.office}|${o.habit}`,
                a: (
                  <>
                    {o.office}
                    {o.district_name && <span className="text-xs text-muted-foreground">, {o.district_name}</span>}
                  </>
                ),
                b: o.habit,
                c: `${count(o.count)} of ${count(o.total)} (${(o.share * 100).toFixed(0)}%) · scheme ${(o.national * 100).toFixed(1)}%`,
                lift: o.lift,
              }))}
            />
            {habits.length > 8 && <p className="mt-3 text-xs text-muted-foreground">and {habits.length - 8} more.</p>}
          </section>
        </Reveal>
      )}

      {/* ---------------------------------------------------------------- queue */}
      <Reveal>
        <section className="space-y-4">
          <SectionHeader
            eyebrow="Act"
            title="Top of the review queue"
            description="Most important first: the risk score weighted by the money at stake. Click a work to see why."
            actions={
              <Button asChild variant="outline" className="rounded-xl">
                <Link href="/queue">
                  Open the full queue <ArrowRight />
                </Link>
              </Button>
            }
          />
          <WorkTable items={queue?.items.slice(0, 8) ?? []} loading={!queue} rank />
        </section>
      </Reveal>
    </div>
  );
}

function Fact({ icon, tone, title, children }: { icon: React.ReactNode; tone: string; title: string; children: React.ReactNode }) {
  return (
    <div className="flex gap-3">
      <span className="mt-0.5 grid size-8 shrink-0 place-items-center rounded-lg" style={{ background: `color-mix(in srgb, ${tone} 10%, white)`, color: tone }}>
        {icon}
      </span>
      <div>
        <div className="text-sm font-semibold text-brand-950">{title}</div>
        <p className="mt-0.5 text-[13px] leading-relaxed text-muted-foreground">{children}</p>
      </div>
    </div>
  );
}

function OfficeTable({
  head,
  rows,
}: {
  head: [string, string, string, string];
  rows: { key: string; a: React.ReactNode; b: React.ReactNode; c: string; lift: number }[];
}) {
  const maxLift = Math.max(1, ...rows.map((r) => r.lift));
  return (
    <div className="mt-4 overflow-x-auto rounded-xl border">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b bg-muted/60 text-left">
            <th className="px-4 py-2.5 eyebrow">{head[0]}</th>
            <th className="px-4 py-2.5 eyebrow">{head[1]}</th>
            <th className="px-4 py-2.5 text-right eyebrow">{head[2]}</th>
            <th className="w-56 px-4 py-2.5 eyebrow">{head[3]}</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.key} className="border-b transition-colors last:border-0 hover:bg-brand-50/50">
              <td className="px-4 py-3 font-medium">
                <span className="inline-flex items-center gap-2">
                  <Building2 className="size-3.5 shrink-0 text-muted-foreground" />
                  {r.a}
                </span>
              </td>
              <td className="px-4 py-3">{r.b}</td>
              <td className="num whitespace-nowrap px-4 py-3 text-right">{r.c}</td>
              <td className="px-4 py-3">
                <div className="flex items-center gap-2">
                  <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-muted">
                    <div className="h-full rounded-full" style={{ width: `${(r.lift / maxLift) * 100}%`, background: "var(--medium)" }} />
                  </div>
                  <span className="num w-20 text-right text-xs font-semibold text-foreground">{r.lift.toFixed(0)}× higher</span>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
