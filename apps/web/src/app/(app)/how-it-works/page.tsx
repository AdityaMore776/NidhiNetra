"use client";

import { Combine, Inbox, ScanSearch, ShieldCheck, UserCheck } from "lucide-react";
import { motion, useMotionTemplate, useMotionValue, useReducedMotion, useScroll, useSpring } from "motion/react";
import Link from "next/link";
import { useRef } from "react";
import { Reveal, Stagger, StaggerItem } from "@/components/motion/reveal";
import { EngineMark } from "@/components/nn/badges";
import { PageHeader, SectionHeader } from "@/components/nn/layout-bits";
import { Button } from "@/components/ui/button";
import type { Summary } from "@/lib/api";
import { useApiData } from "@/lib/cache";
import { AGENT_ORDER, agentMeta } from "@/lib/format";
import { cn } from "@/lib/utils";

const STEPS = [
  { n: 1, title: "Work enters NidhiNetra", text: "Records, the agency's cost estimate form and monthly site videos come in.", icon: Inbox, color: "var(--brand-600)" },
  { n: 2, title: "The checkers, in parallel", text: "Each independently checks for a different kind of problem.", icon: ScanSearch, color: "var(--brand-900)" },
  {
    n: 3,
    title: "Risk fusion",
    text: "Combine the checks into the chance a work is worth a look, using how often each kind of flag proved right when read by eye, with the top three reasons.",
    icon: Combine,
    color: "var(--eng-flow)",
  },
  { n: 4, title: "Risk review", text: "Rank works Low, Medium, High or Critical, and queue High and Critical for a look.", icon: ShieldCheck, color: "var(--medium)" },
  { n: 5, title: "Officer verification", text: "An officer reviews the evidence and makes the decision.", icon: UserCheck, color: "var(--low)" },
];

const FACETS: Record<string, string[]> = {
  cost_estimate: [
    "Reads the implementing agency's cost estimate form: size, specification and every expense line",
    "Prices every line at a fair rate: the state's Schedule of Rates item, or what 3+ other agencies in the district paid on 5+ recent forms (never the agency's own), and a fair quantity for the stated size",
    "Then judges the whole estimate: asked only when it is at least 15% and Rs 50,000 above the fair price, so one odd line or a small rounding never counts",
    "A work with no form is not judged: an amount alone does not say what is built",
  ],
  dup_split: [
    "Is this work already sanctioned here, or one job cut to stay under a limit? The form's map pin against the pins of sanctioned works of the same kind",
    "A continuation, extension or rebuild is declared on the form and never asked about, unless it rebuilds a work completed under three years ago",
    "One job cut into pieces to stay under the Rs 5 or 10 lakh limit, asked only when every piece sits within 4% under it (12 of 14 such groups read as one job)",
    "Works that read alike are shown as notes for the agency to answer, never counted: words alone are right about 2 times in 3",
  ],
  time_rules: [
    "The 75-day sanction clock: a late sanction is told as a fact about the office, with little weight (6 in 10 of the 15,662 works with both dates pass it)",
    "A comfort window from the agency's own estimated time to completion, checked first against the usual time for that kind and size of work",
    "Finished before the window opens is asked only when no site video shows the work; past the window, after allowing monsoon months and approved extensions, is asked",
    "Dates that cannot be true, and constructions recorded complete within days of their sanction",
  ],
  site_progress: [
    "A short video each month, filmed in the app at the same marked spots on the site, with GPS and the phone's motion",
    "Judges the agency's own claim (\"walls up to lintel\") against what the video shows: shown, not shown, or can't tell",
    "Asks when footage was used before, when the site is another work's, or when both GPS and the views say it was not filmed here",
    "A blurry, dark or uploaded-from-gallery video is never a finding: the visit is simply not accepted and filmed again",
  ],
};

export default function HowItWorks() {
  const { data: s } = useApiData<Summary>("/dashboard/summary");
  const built = new Set(s?.agents.filter((a) => a.built).map((a) => a.id) ?? []);
  const pipe = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({ target: pipe, offset: ["start 85%", "end 45%"] });
  const draw = useSpring(scrollYProgress, { stiffness: 120, damping: 30 });

  return (
    <div className="space-y-12">
      <PageHeader
        eyebrow="Understand"
        title="How NidhiNetra"
        accent="works."
        lead="The five steps from the team's design, and where each engine stands today."
        actions={
          <Button asChild className="rounded-xl bg-brand-gradient">
            <Link href="/explain">Watch one work, step by step</Link>
          </Button>
        }
      />

      {/* ------------------------------------------------------------------ the pipeline */}
      <section ref={pipe} className="relative">
        <svg className="pointer-events-none absolute left-0 top-[34px] hidden h-1 w-full overflow-visible lg:block" preserveAspectRatio="none" viewBox="0 0 100 1">
          <line x1="10" y1="0.5" x2="90" y2="0.5" stroke="var(--border)" strokeWidth="2" vectorEffect="non-scaling-stroke" strokeDasharray="4 6" />
          <motion.line
            x1="10"
            y1="0.5"
            x2="90"
            y2="0.5"
            stroke="url(#pipe-grad)"
            strokeWidth="3"
            vectorEffect="non-scaling-stroke"
            strokeLinecap="round"
            style={{ pathLength: draw }}
          />
          <defs>
            {/* user-space units: a bounding-box gradient on a zero-height line does not render at all */}
            <linearGradient id="pipe-grad" gradientUnits="userSpaceOnUse" x1="10" y1="0" x2="90" y2="0">
              <stop offset="0" stopColor="var(--brand-600)" />
              <stop offset="0.5" stopColor="var(--eng-flow)" />
              <stop offset="1" stopColor="var(--low)" />
            </linearGradient>
          </defs>
        </svg>
        <Stagger className="relative grid gap-4 md:grid-cols-3 lg:grid-cols-5" gap={0.1}>
          {STEPS.map((st) => (
            <StaggerItem key={st.n}>
              <div className="flex h-full flex-col items-center text-center lg:px-1">
                <span
                  className="relative z-10 grid size-[68px] place-items-center rounded-2xl bg-white text-white shadow-lift ring-1 ring-border"
                  style={{ boxShadow: `0 14px 30px -14px ${st.color}` }}
                >
                  <span className="grid size-12 place-items-center rounded-xl" style={{ background: st.color }}>
                    <st.icon className="size-6" />
                  </span>
                  <span className="num absolute -right-2 -top-2 grid size-6 place-items-center rounded-full bg-brand-950 font-mono text-[10px] font-semibold text-white">
                    {st.n}
                  </span>
                </span>
                <div className="mt-4 font-semibold text-brand-950">{st.title}</div>
                <p className="mt-1.5 text-[13px] leading-relaxed text-muted-foreground">{st.text}</p>
              </div>
            </StaggerItem>
          ))}
        </Stagger>
      </section>

      {/* ------------------------------------------------------------------ the engines */}
      <section className="space-y-5">
        <Reveal>
          <SectionHeader
            eyebrow="The engines"
            title="One specialist per problem the auditors found"
            description="Each answers one question about a work and never talks to the others. Move across a card to light it."
          />
        </Reveal>
        <Stagger className="grid gap-4 md:grid-cols-2" gap={0.06}>
          {AGENT_ORDER.filter((id) => FACETS[id]).map((id) => (
            <StaggerItem key={id}>
              <EngineCard id={id} live={built.has(id)} />
            </StaggerItem>
          ))}
        </Stagger>
      </section>
    </div>
  );
}

/** An engine card with a spotlight that follows the pointer, in the engine's own colour. */
function EngineCard({ id, live }: { id: string; live: boolean }) {
  const meta = agentMeta(id);
  const reduce = useReducedMotion();
  const mx = useMotionValue(-200);
  const my = useMotionValue(-200);
  const bg = useMotionTemplate`radial-gradient(320px circle at ${mx}px ${my}px, color-mix(in srgb, ${meta.color} 14%, transparent), transparent 70%)`;
  return (
    <motion.section
      onMouseMove={(e) => {
        const r = e.currentTarget.getBoundingClientRect();
        mx.set(e.clientX - r.left);
        my.set(e.clientY - r.top);
      }}
      onMouseLeave={() => {
        mx.set(-200);
        my.set(-200);
      }}
      whileHover={reduce ? undefined : { y: -4 }}
      transition={{ type: "spring", stiffness: 300, damping: 24 }}
      className="panel group relative h-full overflow-hidden"
    >
      <motion.div className="pointer-events-none absolute inset-0" style={{ background: bg }} />
      <div className="absolute inset-x-0 top-0 h-[3px]" style={{ background: meta.color }} />
      <header className="relative flex items-center gap-3 px-5 pb-2 pt-5">
        <EngineMark id={id} size={38} />
        <div className="min-w-0">
          <div className="font-semibold text-brand-950">{meta.name}</div>
          <div className="text-xs text-muted-foreground">{meta.question}</div>
        </div>
        <span
          className={cn(
            "ml-auto inline-flex shrink-0 items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-semibold",
            live ? "bg-low/10 text-low" : "bg-muted text-muted-foreground",
          )}
        >
          {live && <span className="size-1.5 rounded-full bg-low" />}
          {live ? "Live" : "In development"}
        </span>
      </header>
      <ol className="relative space-y-2.5 px-5 pb-5 pt-2 text-sm">
        {(FACETS[id] ?? []).map((f, i) => (
          <li key={f} className="flex gap-3">
            <span
              className="grid size-6 shrink-0 place-items-center rounded-md font-mono text-[11px] font-bold"
              style={{ background: `color-mix(in srgb, ${meta.color} 12%, white)`, color: meta.color }}
            >
              {String.fromCharCode(65 + i)}
            </span>
            <span className="leading-relaxed text-foreground/85">{f}</span>
          </li>
        ))}
      </ol>
    </motion.section>
  );
}
