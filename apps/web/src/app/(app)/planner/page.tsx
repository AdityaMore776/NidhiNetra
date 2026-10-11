"use client";

import { CalendarClock, Car, Clock3, MapPin, MapPinned, Route, Shuffle } from "lucide-react";
import dynamic from "next/dynamic";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useMemo, useState } from "react";
import { Reveal } from "@/components/motion/reveal";
import { BandBadge } from "@/components/nn/badges";
import { PageHeader, SectionHeader, StatTile } from "@/components/nn/layout-bits";
import { Segmented } from "@/components/nn/segmented";
import { type Me, type Plan, type PlanDistrict, type PlanPlace, type PlanStop, type PlanWork } from "@/lib/api";
import { useApiData } from "@/lib/cache";
import { inr, workHref, workType } from "@/lib/format";
import { cn } from "@/lib/utils";

const PlanMap = dynamic(() => import("@/components/map/PlanMap").then((m) => m.PlanMap), {
  ssr: false,
  loading: () => <div className="h-full min-h-[420px] animate-pulse rounded-2xl border bg-muted/50" />,
});

type Hours = "6" | "8" | "10";

const PRECISION: Record<PlanPlace["precision"], { label: string; note: string }> = {
  village: { label: "Village", note: "found by the village named in the work (approximate)" },
  area: { label: "Area", note: "found by name; the post office's position is shared with nearby offices" },
  block: { label: "Block", note: "the taluka or mandal named in the work: somewhere in that block" },
  district: { label: "District only", note: "no place named that the planner could find: shown at the district's start point" },
};

function today(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

function title(s: string | null | undefined): string {
  return (s ?? "").toLowerCase().replace(/\b\w/g, (c) => c.toUpperCase());
}

export default function PlannerPage() {
  return (
    <Suspense fallback={null}>
      <Planner />
    </Suspense>
  );
}

function Planner() {
  const params = useSearchParams();
  const router = useRouter();
  const path = usePathname();
  const { data: me } = useApiData<Me>("/me");
  const { data: districts, error: dErr } = useApiData<PlanDistrict[]>("/plans/districts");
  // an address with a district the planner does not know opens the busiest district instead
  const asked = params.get("d");
  const district = districts ? (districts.find((d) => d.district_lgd === asked) ?? districts[0])?.district_lgd ?? null : null;
  const hours = (["6", "8", "10"].includes(params.get("h") ?? "") ? params.get("h") : "8") as Hours;
  const [day] = useState(today);
  const id = district ? `${district}_${day}_${hours}` : null;
  const { data: plan, error } = useApiData<Plan>(id ? `/plans/${id}` : null);
  // the chosen stop belongs to one plan: another district or day starts with none chosen
  const [chosen, setChosen] = useState<{ id: string | null; order: number } | null>(null);
  const selected = chosen?.id === id ? chosen.order : null;
  const setSelected = (order: number) => setChosen({ id, order });
  const [hindi, setHindi] = useState(false);
  const shown = plan?.id === id ? plan : null;

  useEffect(() => {
    if (selected == null) return;
    document.getElementById(`stop-${selected}`)?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [selected]);

  function set(next: { d?: string; h?: Hours }) {
    const q = new URLSearchParams(params.toString());
    if (next.d) q.set("d", next.d);
    if (next.h) q.set("h", next.h);
    router.replace(`${path}?${q}`, { scroll: false });
  }

  const byState = useMemo(() => {
    const m = new Map<string, PlanDistrict[]>();
    for (const d of districts ?? []) m.set(d.state, [...(m.get(d.state) ?? []), d]);
    return [...m.entries()].sort(([a], [b]) => a.localeCompare(b));
  }, [districts]);
  const staff = me != null && me.role !== "PUBLIC";
  const t = shown?.totals;
  const located = shown ? shown.stops.filter((s) => s.location.precision !== "district").length : 0;

  return (
    <div className="space-y-7">
      <PageHeader
        eyebrow="Act · Inspection Planner"
        title="One day's visits,"
        accent="planned."
        lead="Pick a district. The planner takes its review-queue cases, finds each work's village from its description, and fits the most important visits into one working day, in the order that drives least. A few random lower-risk works are added as spot checks. Every stop is a request to look, not a finding."
      />

      <div className="panel flex flex-wrap items-end gap-4 p-4">
        <label className="flex min-w-[16rem] flex-1 flex-col gap-1.5 text-[13px] font-medium text-muted-foreground">
          District
          <select
            className="h-10 rounded-xl border bg-white px-3 text-sm text-foreground"
            value={district ?? ""}
            onChange={(e) => set({ d: e.target.value })}
            disabled={!districts}
          >
            {!districts && <option>Loading districts…</option>}
            {byState.map(([state, ds]) => (
              <optgroup key={state} label={title(state)}>
                {ds.map((d) => (
                  <option key={d.district_lgd} value={d.district_lgd}>
                    {d.name} · {d.cases} {d.cases === 1 ? "case" : "cases"}
                  </option>
                ))}
              </optgroup>
            ))}
          </select>
        </label>
        <div className="flex flex-col gap-1.5 text-[13px] font-medium text-muted-foreground">
          Hours in the day
          <Segmented<Hours>
            value={hours}
            onChange={(h) => set({ h })}
            options={[
              { value: "6", label: "6 h" },
              { value: "8", label: "8 h" },
              { value: "10", label: "10 h" },
            ]}
          />
        </div>
        <div className="text-xs text-muted-foreground">
          Plan <span className="num font-medium text-foreground">{id ?? "—"}</span>
          <br />
          the same plan opens again from this address
        </div>
      </div>

      {(dErr || error) && (
        <div className="panel p-5 text-sm text-muted-foreground">The planner could not answer just now ({(dErr ?? error)?.message}). Please try again in a moment.</div>
      )}

      <div className="grid grid-cols-2 gap-3 sm:gap-4 lg:grid-cols-4">
        <StatTile
          label="Visits in the day"
          value={t?.stops ?? 0}
          icon={<MapPinned className="size-4" />}
          note={t ? `${t.flagged_visited} of ${t.flagged_in_queue} queue cases, ${t.stops - t.flagged_visited} spot check${t.stops - t.flagged_visited === 1 ? "" : "s"}` : "…"}
        />
        <StatTile
          label="Estimated road km"
          value={t?.road_km ?? 0}
          format={(v) => `${Math.round(v)} km`}
          icon={<Car className="size-4" />}
          tone="var(--teal)"
          note={t ? (t.km_saved > 0 ? `${Math.round(t.km_saved)} km less than in queue order` : "the queue order is already the shortest here") : "…"}
        />
        <StatTile
          label="Back at the start by"
          value={t?.minutes ?? 0}
          format={() => t?.back_by ?? "—"}
          icon={<Clock3 className="size-4" />}
          tone="var(--medium)"
          note={t ? `leaving at 09:00, ${Math.floor(t.minutes / 60)} h ${t.minutes % 60} min on the road and at sites` : "…"}
        />
        <StatTile
          label="Stops placed by name"
          value={located}
          icon={<MapPin className="size-4" />}
          tone="var(--brand-600)"
          note={shown ? `of ${shown.stops.length}: the rest sit at the district's start point` : "…"}
        />
      </div>

      {shown && shown.stops.length === 0 && (
        <div className="panel p-6 text-sm text-muted-foreground">
          {t?.flagged_in_queue === 0 ? "No works in this district are in the review queue, so there is nothing to plan." : `No visit fits in ${hours} hours from the start point. Try a longer day.`}
        </div>
      )}

      {shown && shown.stops.length > 0 && (
        <div className="grid gap-5 xl:grid-cols-[minmax(0,1.15fr)_minmax(0,1fr)]">
          <Reveal className="space-y-3">
            <PlanMap plan={shown} selected={selected} onSelect={setSelected} className="h-[440px] sm:h-[560px]" />
            <Legend />
          </Reveal>

          <Reveal className="space-y-3">
            <SectionHeader
              eyebrow={`${shown.district.name} · ${title(shown.district.state)} · ${shown.date}`}
              title="The route"
              description={`Start at ${shown.start.label} at 09:00, then each stop in order.`}
              actions={
                <Segmented<"en" | "hi">
                  value={hindi ? "hi" : "en"}
                  onChange={(v) => setHindi(v === "hi")}
                  options={[
                    { value: "en", label: "English" },
                    { value: "hi", label: "हिन्दी" },
                  ]}
                />
              }
            />
            <ol className="space-y-3 xl:max-h-[640px] xl:overflow-y-auto xl:pr-1">
              {shown.stops.map((s) => (
                <StopCard key={s.work_id} stop={s} hindi={hindi} staff={staff} active={selected === s.order} onClick={() => setSelected(s.order)} />
              ))}
            </ol>
          </Reveal>
        </div>
      )}

      {shown && shown.next_trip.length > 0 && (
        <Reveal className="space-y-3">
          <SectionHeader
            eyebrow="Next trip"
            title={`${shown.next_trip.length} queue ${shown.next_trip.length === 1 ? "case" : "cases"} that did not fit today`}
            description="Most important first. Plan another day, or a longer one, to reach them."
          />
          <div className="grid gap-3 md:grid-cols-2">
            {shown.next_trip.map((w) => (
              <WorkLine key={w.work_id} work={w} staff={staff} />
            ))}
          </div>
        </Reveal>
      )}

      {shown && (
        <Reveal className="panel space-y-2 p-5 text-xs leading-relaxed text-muted-foreground">
          <div className="flex items-center gap-2 font-semibold text-foreground">
            <CalendarClock className="size-4" /> How this plan is made
          </div>
          <p>
            Each queue case is valued by its risk score weighted by the money at stake (the queue&apos;s own order). The planner adds the case with the most value per extra
            minute of the day, again and again, until the day is full, then puts the stops in the order that drives least (exactly, for up to 12 places).
            Spot checks fill any time left: {Math.round(shown.rules.spot_share * 100)}% as many random lower-risk works as queue cases, a fresh draw each day, so a visit
            to them says nothing about the work. Measured on the live queue: the planner fits 198 cases into one day per district where working down the queue fits 192, and
            the route is 4% shorter (data/trial/results/t062_planner.txt).
          </p>
          {shown.notes.map((n) => (
            <p key={n}>{n}</p>
          ))}
        </Reveal>
      )}
    </div>
  );
}

function Legend() {
  return (
    <div className="flex flex-wrap items-center gap-x-5 gap-y-2 px-1 text-xs text-muted-foreground">
      <span className="flex items-center gap-1.5">
        <span className="grid size-5 place-items-center rounded-full text-[10px] font-semibold text-white" style={{ background: "var(--high)" }}>
          1
        </span>
        queue case
      </span>
      <span className="flex items-center gap-1.5">
        <span className="grid size-5 place-items-center rounded-full border-2 bg-white text-[10px] font-semibold" style={{ borderColor: "var(--teal)", color: "var(--teal)" }}>
          2
        </span>
        <Shuffle className="size-3" /> random spot check
      </span>
      <span className="flex items-center gap-1.5">
        <span className="size-5 rounded-full border-2 border-dashed" style={{ borderColor: "var(--brand-600)" }} />
        place not found: at the district&apos;s start point
      </span>
      <span className="flex items-center gap-1.5">
        <Route className="size-3.5" /> drive between stops (straight line; roads wind)
      </span>
    </div>
  );
}

function PlaceChip({ loc }: { loc: PlanPlace }) {
  const p = PRECISION[loc.precision];
  return (
    <span title={p.note} className={cn("inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-medium ring-1 ring-inset", loc.precision === "district" ? "bg-muted text-muted-foreground ring-border" : "bg-brand-50 text-brand-700 ring-brand-100")}>
      <MapPin className="size-3" />
      {loc.place ? `${loc.place} · ` : ""}
      {p.label}
    </span>
  );
}

function StopCard({ stop, hindi, staff, active, onClick }: { stop: PlanStop; hindi: boolean; staff: boolean; active: boolean; onClick: () => void }) {
  const spot = stop.kind === "spot";
  return (
    <li id={`stop-${stop.order}`} onClick={onClick} className={cn("panel cursor-pointer p-4 transition-shadow", active ? "ring-2 ring-brand-400" : "hover:shadow-lift")}>
      <div className="flex items-start gap-3">
        <span
          className={cn("grid size-8 shrink-0 place-items-center rounded-full text-sm font-semibold", spot ? "border-2 bg-white" : "text-white")}
          style={spot ? { borderColor: "var(--teal)", color: "var(--teal)" } : { background: stop.band === "CRITICAL" ? "var(--critical)" : "var(--high)" }}
        >
          {stop.order}
        </span>
        <div className="min-w-0 flex-1 space-y-2">
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
            <span className="num font-semibold text-foreground">
              {stop.arrive}–{stop.leave}
            </span>
            <span>{stop.drive_km} km drive</span>
            <PlaceChip loc={stop.location} />
            {spot ? (
              <span className="inline-flex items-center gap-1 font-medium" style={{ color: "var(--teal)" }}>
                <Shuffle className="size-3" /> spot check
              </span>
            ) : (
              <BandBadge band={stop.band} score={stop.score} size="sm" />
            )}
          </div>
          <WorkTitle work={stop} staff={staff} />
          <ul className="space-y-1.5 border-l-2 pl-3 text-[13px] leading-relaxed" style={{ borderColor: spot ? "var(--teal)" : "var(--high)" }}>
            {stop.checklist.map((c, i) => (
              <li key={i}>{hindi && c.hi ? c.hi : c.en}</li>
            ))}
          </ul>
        </div>
      </div>
    </li>
  );
}

function WorkTitle({ work, staff }: { work: PlanWork; staff: boolean }) {
  return (
    <div className="space-y-0.5">
      <p className="text-sm font-medium leading-snug text-brand-950">{work.description ?? "No description recorded"}</p>
      <p className="text-xs text-muted-foreground">
        {staff ? (
          <Link href={workHref(work.work_id)} className="num text-brand-600 hover:underline" onClick={(e) => e.stopPropagation()}>
            {work.work_id}
          </Link>
        ) : (
          <span className="num">{work.work_id}</span>
        )}
        {" · "}
        {workType(work.work_type_code)} · {inr(work.amount)} · {title(work.status)}
        {work.case_size && work.case_size > 1 ? ` · one case of ${work.case_size} alike works` : ""}
      </p>
    </div>
  );
}

function WorkLine({ work, staff }: { work: PlanWork; staff: boolean }) {
  return (
    <div className="panel space-y-2 p-4">
      <div className="flex flex-wrap items-center gap-2">
        <BandBadge band={work.band} score={work.score} size="sm" />
        <PlaceChip loc={work.location} />
      </div>
      <WorkTitle work={work} staff={staff} />
    </div>
  );
}
