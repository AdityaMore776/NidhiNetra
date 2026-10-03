"use client";

import {
  ArrowLeft,
  Building,
  CalendarCheck2,
  CalendarPlus,
  CircleDot,
  Copy,
  IndianRupee,
  Landmark,
  MapPin,
  ShieldAlert,
  Users,
} from "lucide-react";
import { motion } from "motion/react";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { toast } from "sonner";
import { AgentCard, STATUS_NOTE } from "@/components/AgentCard";
import { FusionPanel } from "@/components/FusionPanel";
import { Reveal, Stagger, StaggerItem } from "@/components/motion/reveal";
import { EngineMark, SourceBadge } from "@/components/nn/badges";
import { SectionHeader } from "@/components/nn/layout-bits";
import { Button } from "@/components/ui/button";
import { api, ApiError, type WorkDetail } from "@/lib/api";
import { AGENT_ORDER, agentMeta, inr, workType } from "@/lib/format";
import { cn } from "@/lib/utils";

export default function WorkPage() {
  return (
    <Suspense fallback={null}>
      <Work />
    </Suspense>
  );
}

function Work() {
  const id = useSearchParams().get("id") ?? "";
  const router = useRouter();
  const [d, setD] = useState<{ id: string; detail: WorkDetail } | null>(null);
  const [error, setError] = useState<{ id: string; text: string } | null>(null);

  useEffect(() => {
    if (!id) return;
    let live = true;
    api<WorkDetail>(`/works/${id}`)
      .then((detail) => live && setD({ id, detail }))
      .catch((e: ApiError) => live && setError({ id, text: e.status === 404 ? "This work is not in your area, or does not exist." : e.message }));
    return () => {
      live = false;
    };
  }, [id]);

  if (error?.id === id)
    return (
      <div className="panel mx-auto max-w-lg p-8 text-center">
        <ShieldAlert className="mx-auto size-8 text-high" />
        <p className="mt-3 text-sm">{error.text}</p>
        <Button variant="outline" className="mt-5 rounded-xl" onClick={() => router.back()}>
          <ArrowLeft /> Go back
        </Button>
      </div>
    );
  if (!d || d.id !== id) return <WorkSkeleton />;
  const w = d.detail.work;
  const a = d.detail.assessment;
  const ordered = [...a.agents].sort((x, y) => {
    const ix = AGENT_ORDER.indexOf(x.agent);
    const iy = AGENT_ORDER.indexOf(y.agent);
    return (ix < 0 ? 99 : ix) - (iy < 0 ? 99 : iy);
  });

  return (
    <div className="space-y-6">
      <button onClick={() => router.back()} className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground">
        <ArrowLeft className="size-4" /> Back
      </button>

      {/* ------------------------------------------------------------------ the work */}
      <motion.section
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
        className="panel relative overflow-hidden p-5 sm:p-7"
      >
        <div className="pointer-events-none absolute -right-24 -top-24 size-72 rounded-full bg-brand-gradient opacity-[0.07] blur-3xl" />
        <div className="flex flex-wrap items-center gap-2">
          <SourceBadge source={w.source} />
          <button
            onClick={() => {
              navigator.clipboard?.writeText(w.work_id);
              toast.success("Work id copied");
            }}
            className="inline-flex items-center gap-1.5 rounded-full border bg-white px-2.5 py-0.5 font-mono text-[11px] text-muted-foreground hover:text-foreground"
            title="Copy the work id"
          >
            {w.work_id}
            <Copy className="size-3" />
          </button>
          {w.category && <span className="rounded-full bg-muted px-2.5 py-0.5 text-[11px] text-muted-foreground">{w.category}</span>}
        </div>
        <h1 className="mt-4 text-2xl font-semibold tracking-[-0.03em] text-brand-950 sm:text-3xl">{workType(w.work_type_code)}</h1>
        <p className="mt-2 max-w-4xl text-[15px] leading-relaxed text-foreground/85">{w.description}</p>

        <dl className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <Fact icon={<IndianRupee />} label="Amount" value={inr(w.amount)} strong />
          <Fact icon={<CircleDot />} label="Status" value={w.status} />
          <Fact icon={<MapPin />} label="District" value={`${w.district_name ?? "—"}, ${w.state_name ?? ""}`} />
          <Fact
            icon={<Landmark />}
            label="Constituency"
            value={w.house === "Rajya Sabha" ? `Rajya Sabha (whole of ${w.state_name ?? "the state"})` : w.constituency}
          />
          <Fact icon={<Users />} label="House" value={[w.house, w.term !== w.house ? w.term : null].filter(Boolean).join(" · ")} />
          <Fact icon={<Building />} label="Implementing agency" value={w.agency_name} className="lg:col-span-3" />
        </dl>

        <Timeline recommended={w.recommended_date} completed={w.completed_date} status={w.status} />
      </motion.section>

      {/* ------------------------------------------------------------------ the score */}
      <Reveal>
        <FusionPanel a={a} />
      </Reveal>

      {a.validation.length > 0 && (
        <Reveal>
          <section className="panel space-y-3 p-5 sm:p-6">
            <SectionHeader eyebrow="Data validation" title="Notes on the record itself" />
            <ul className="space-y-2 text-sm">
              {a.validation.map((i) => (
                <li key={i.code} className="flex gap-3 rounded-xl border bg-white p-3">
                  <span
                    className="h-fit rounded-md px-2 py-0.5 font-mono text-[10px] font-bold text-white"
                    style={{ background: i.severity === "WARN" ? "var(--medium)" : "var(--brand-600)" }}
                  >
                    {i.severity === "WARN" ? "CHECK" : "NOTE"}
                  </span>
                  <span className="leading-relaxed">{i.message}</span>
                </li>
              ))}
            </ul>
          </section>
        </Reveal>
      )}

      {/* ------------------------------------------------------------------ the engines */}
      <Reveal>
        <section className="panel p-5 sm:p-6">
          <SectionHeader
            eyebrow="Detect"
            title="What every engine said"
            description="Each engine answers its own question. One that could not look at this work says so: that is a status, never a low score."
          />
          <div className="mt-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
            {ordered.map((r) => {
              const m = agentMeta(r.agent, r.name, r.question);
              const assessed = r.status === "ASSESSED";
              const risk = Math.round(r.risk * 100);
              return (
                <a
                  key={r.agent}
                  href={`#engine-${r.agent}`}
                  className={cn("flex items-center gap-3 rounded-xl border bg-white p-3 transition-all hover:-translate-y-0.5 hover:shadow-card", !assessed && "bg-muted/40")}
                >
                  <EngineMark id={r.agent} size={30} />
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-[13px] font-medium">{m.name}</div>
                    <div className="text-[11px] text-muted-foreground">{assessed ? (risk > 0 ? "Raised a question" : "None found") : STATUS_NOTE[r.status]}</div>
                  </div>
                  {assessed && risk > 0 && (
                    <span className="num text-sm font-semibold" style={{ color: m.color }}>
                      {risk}
                    </span>
                  )}
                </a>
              );
            })}
          </div>
        </section>
      </Reveal>

      <Stagger className="grid gap-4 lg:grid-cols-2" gap={0.05}>
        {ordered.map((r) => (
          <StaggerItem key={r.agent}>
            <div id={`engine-${r.agent}`} className="scroll-mt-20">
              <AgentCard result={r} />
            </div>
          </StaggerItem>
        ))}
      </Stagger>

      <p className="text-xs text-muted-foreground">
        Assessed <span className="num">{new Date(a.assessed_at).toLocaleString("en-IN")}</span>. Officer decisions and the audit trail arrive
        with the review workflow.
      </p>
    </div>
  );
}

function Fact({ icon, label, value, strong, className }: { icon: React.ReactNode; label: string; value: string | null | undefined; strong?: boolean; className?: string }) {
  return (
    <div className={cn("flex gap-3 rounded-xl border bg-white/80 p-3", className)}>
      <span className="grid size-8 shrink-0 place-items-center rounded-lg bg-brand-50 text-brand-700 [&_svg]:size-4">{icon}</span>
      <div className="min-w-0">
        <dt className="text-[11px] text-muted-foreground">{label}</dt>
        <dd className={cn("truncate text-sm", strong && "num text-base font-semibold text-brand-950")} title={value ?? undefined}>
          {value || "—"}
        </dd>
      </div>
    </div>
  );
}

/** Only dates the record stores: a step that has not happened is left out, never shown as today. */
function Timeline({ recommended, completed, status }: { recommended: string | null; completed: string | null; status: string | null }) {
  const steps = [
    recommended && { label: "Recommended", date: recommended, icon: <CalendarPlus className="size-3.5" /> },
    completed && { label: "Completed", date: completed, icon: <CalendarCheck2 className="size-3.5" /> },
  ].filter(Boolean) as { label: string; date: string; icon: React.ReactNode }[];
  if (!steps.length) return null;
  const days = recommended && completed ? Math.round((Date.parse(completed) - Date.parse(recommended)) / 86_400_000) : null;
  return (
    <div className="mt-6 flex flex-wrap items-center gap-3 rounded-xl bg-muted/50 px-4 py-3 text-sm">
      {steps.map((s, i) => (
        <div key={s.label} className="flex items-center gap-3">
          {i > 0 && (
            <span className="flex items-center gap-2 text-[11px] text-muted-foreground">
              <span className="h-px w-10 bg-border" />
              {days != null && (
                <span className={cn("num rounded-full px-2 py-0.5", days < 0 ? "bg-high/10 font-semibold text-high" : "bg-white")}>
                  {days < 0 ? `${Math.abs(days)} days before` : `${days} days`}
                </span>
              )}
              <span className="h-px w-10 bg-border" />
            </span>
          )}
          <span className="flex items-center gap-2">
            <span className="grid size-7 place-items-center rounded-full bg-white text-brand-700 ring-1 ring-border">{s.icon}</span>
            <span>
              <span className="block text-[11px] text-muted-foreground">{s.label}</span>
              <span className="num font-medium">{s.date}</span>
            </span>
          </span>
        </div>
      ))}
      {status && !completed && <span className="ml-auto text-xs text-muted-foreground">Now: {status.toLowerCase()}</span>}
    </div>
  );
}

function WorkSkeleton() {
  return (
    <div className="space-y-6">
      <div className="h-5 w-20 rounded skeleton-shimmer" />
      <div className="panel space-y-4 p-7">
        <div className="h-5 w-48 rounded-full skeleton-shimmer" />
        <div className="h-8 w-2/5 rounded-lg skeleton-shimmer" />
        <div className="h-4 w-3/4 rounded skeleton-shimmer" />
        <div className="grid gap-3 sm:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-16 rounded-xl skeleton-shimmer" />
          ))}
        </div>
      </div>
      <div className="panel h-72 skeleton-shimmer" />
    </div>
  );
}
