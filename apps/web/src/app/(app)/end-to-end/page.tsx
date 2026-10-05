"use client";

import { ArrowRight, ClipboardCheck, Construction, Gauge, ListChecks, PenLine, Play, RotateCcw, Video } from "lucide-react";
import { motion, useReducedMotion } from "motion/react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useRef, useState } from "react";
import { BandBadge, EngineMark } from "@/components/nn/badges";
import { PageHeader } from "@/components/nn/layout-bits";
import { Button } from "@/components/ui/button";
import type { Trace } from "@/lib/explain";
import { agentMeta, inr } from "@/lib/format";
import { type AgentLine, agentLines } from "@/lib/work-form-flags";
import { cn } from "@/lib/utils";

/**
 * Five filings, end to end (T136): from the form an implementing agency fills to the risk score an
 * officer sees, through the form's own check and the agents. Built by data/trial/end_to_end_examples.py
 * through the real engine (the same path as POST /api/v1/work-form/check) into
 * public/end-to-end/examples.json. Site Progress is a placeholder here: it starts after sanction, with
 * the first site video, and its field trial (T126) comes first.
 */

interface Yardstick {
  per?: number;
  unit?: string;
  works?: number;
  p10?: number;
  median?: number;
  p90?: number;
  inside?: boolean;
  district?: { works: number; median: number } | null;
  note?: string;
}

interface Filing {
  id: string;
  title: string;
  story: string;
  flagged: boolean;
  form: Record<string, unknown>;
  typed: { section: string; fields: [string, string][] }[];
  boq: { n: number; item: string; unit: string; qty: number; rate: number; amount: number; source: string }[];
  check: {
    ready: boolean;
    fix: string[];
    confirm: string[];
    grand_total: number;
    mp_amount: number;
    mp_gap: number | null;
    passed: string[];
  };
  time_plan: { start: string; early: string | null; late: string; accepted_days: number; notes: string[] } | null;
  yardstick: Yardstick | null;
  decision: string;
  trace: Trace;
}

interface E2EFile {
  source: string;
  as_of: string;
  district: string;
  real_works: number;
  examples: Filing[];
}

const STEPS = [
  { title: "The agency fills the form", icon: PenLine },
  { title: "The form checks itself", icon: ClipboardCheck },
  { title: "The agents read it", icon: ListChecks },
  { title: "The risk score", icon: Gauge },
] as const;
const STEP_MS = 2600;

const day = (iso: string | null | undefined) =>
  iso ? new Date(`${iso.slice(0, 10)}T00:00:00`).toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" }) : "—";
const rs = (v: number) => `₹${Math.round(v).toLocaleString("en-IN")}`;

export default function EndToEndPage() {
  return (
    <Suspense fallback={null}>
      <EndToEnd />
    </Suspense>
  );
}

function EndToEnd() {
  const wanted = useSearchParams().get("example");
  const [file, setFile] = useState<E2EFile | null>(null);
  const [failed, setFailed] = useState(false);
  const [picked, setPicked] = useState<string | null>(null);
  const [step, setStep] = useState<number>(STEPS.length); // every step shown until the loop is played
  const [playing, setPlaying] = useState(false);
  const timers = useRef<number[]>([]);
  const reduce = useReducedMotion();

  useEffect(() => {
    fetch("/end-to-end/examples.json")
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(String(r.status)))))
      .then(setFile)
      .catch(() => setFailed(true));
  }, []);

  useEffect(() => {
    const pending = timers.current;
    return () => pending.forEach((id) => window.clearTimeout(id));
  }, []);

  function stop() {
    timers.current.forEach((id) => window.clearTimeout(id));
    timers.current = [];
    setPlaying(false);
  }

  /** Show the steps one at a time, STEP_MS apart. */
  function play() {
    stop();
    setStep(1);
    setPlaying(true);
    for (let i = 2; i <= STEPS.length; i++) timers.current.push(window.setTimeout(() => setStep(i), (i - 1) * STEP_MS));
    timers.current.push(window.setTimeout(() => setPlaying(false), (STEPS.length - 1) * STEP_MS));
  }

  function pick(id: string) {
    setPicked(id);
    play();
  }

  const ex = file?.examples.find((e) => e.id === (picked ?? wanted)) ?? file?.examples[0];

  return (
    <div className="space-y-5">
      <PageHeader
        eyebrow="Understand · End to end"
        title="From the form to"
        accent="the risk score."
        lead="Five filings in Jaunpur, Uttar Pradesh, each followed from the form an agency fills to the score an officer sees. Two are honest; three hide something the agents should find."
        actions={
          <Button asChild variant="outline" className="rounded-xl">
            <Link href="/work-form">
              Try the form yourself <ArrowRight />
            </Link>
          </Button>
        }
      />

      {failed && <p className="text-sm text-destructive">The examples could not be loaded.</p>}
      {!file && !failed && <p className="text-sm text-muted-foreground">Loading the five filings…</p>}

      {file && ex && (
        <>
          <section className="grid gap-2 sm:grid-cols-2 xl:grid-cols-5" aria-label="The five filings">
            {file.examples.map((e, i) => {
              const on = e.id === ex.id;
              return (
                <button
                  key={e.id}
                  type="button"
                  onClick={() => pick(e.id)}
                  className={cn(
                    "rounded-xl border bg-white p-3 text-left transition-colors",
                    on ? "border-brand-600 ring-1 ring-brand-600" : "hover:bg-muted",
                  )}
                >
                  <div className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                    <span className="num">{i + 1}</span>
                    <span
                      className={cn(
                        "rounded-full px-2 py-0.5 normal-case tracking-normal",
                        e.flagged ? "bg-[var(--high-soft)] text-[var(--high)]" : "bg-[var(--low-soft)] text-[var(--low)]",
                      )}
                    >
                      {e.flagged ? "Something to find" : "Honest"}
                    </span>
                  </div>
                  <p className="mt-1.5 text-sm font-semibold leading-snug text-balance">{e.title}</p>
                </button>
              );
            })}
          </section>

          <section className="panel space-y-1 p-4 sm:p-5">
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="min-w-0 flex-1 text-lg font-semibold leading-snug text-balance">{ex.title}</h2>
              <Button size="sm" className="rounded-xl" onClick={play} disabled={playing}>
                {playing ? <Play /> : <RotateCcw />} {playing ? "Playing…" : "Play the loop"}
              </Button>
            </div>
            <p className="text-sm text-muted-foreground">{ex.story}</p>
            <ol className="flex flex-wrap gap-1.5 pt-2" aria-label="Steps">
              {STEPS.map((s, i) => (
                <li key={s.title}>
                  <button
                    type="button"
                    onClick={() => {
                      stop();
                      setStep(i + 1);
                    }}
                    className={cn(
                      "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium transition-colors",
                      step >= i + 1 ? "border-brand-600 bg-brand-50 text-brand-900" : "text-muted-foreground",
                    )}
                  >
                    <s.icon className="size-3.5" /> {i + 1}. {s.title}
                  </button>
                </li>
              ))}
            </ol>
          </section>

          <ol className="space-y-4" key={ex.id}>
            {STEPS.map((s, i) =>
              step >= i + 1 ? (
                <motion.li
                  key={s.title}
                  initial={reduce ? false : { opacity: 0, y: 16 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
                  className="panel p-4 sm:p-5"
                >
                  <h3 className="mb-3 flex items-center gap-2 font-semibold">
                    <span className="grid size-7 place-items-center rounded-lg bg-brand-50 text-brand-700">
                      <s.icon className="size-4" />
                    </span>
                    <span className="text-muted-foreground">{i + 1}.</span> {s.title}
                  </h3>
                  {i === 0 && <FormStep ex={ex} />}
                  {i === 1 && <CheckStep ex={ex} />}
                  {i === 2 && <AgentsStep ex={ex} />}
                  {i === 3 && <ScoreStep ex={ex} />}
                </motion.li>
              ) : null,
            )}
          </ol>

          {step >= STEPS.length && <AfterSanction ex={ex} />}

          <p className="text-xs text-muted-foreground">
            Made-up agencies and villages; the record they are compared with is real: {file.real_works.toLocaleString("en-IN")} works
            of the district on the eSAKSHI dashboard ({file.source}). Built by data/trial/end_to_end_examples.py through the same
            engine as the live form check.
          </p>
        </>
      )}
    </div>
  );
}

function FormStep({ ex }: { ex: Filing }) {
  const total = ex.boq.reduce((a, r) => a + r.amount, 0);
  const y = ex.yardstick;
  return (
    <div className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        {ex.typed.map((sec) => (
          <div key={sec.section} className="min-w-0 rounded-xl border p-3">
            <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">{sec.section}</p>
            <dl className="mt-1.5 space-y-1 text-[13px]">
              {sec.fields.map(([k, v]) => (
                <div key={k} className="flex gap-2">
                  <dt className="w-28 shrink-0 text-muted-foreground">{k}</dt>
                  <dd className="min-w-0 break-words font-medium">{v}</dd>
                </div>
              ))}
            </dl>
          </div>
        ))}
      </div>
      <div className="overflow-x-auto rounded-xl border">
        <table className="w-full min-w-[560px] text-[13px]">
          <thead className="bg-muted/60 text-left text-[11px] uppercase tracking-wider text-muted-foreground">
            <tr>
              <th className="px-3 py-2 font-semibold">E. Estimate line</th>
              <th className="px-3 py-2 text-right font-semibold">Quantity</th>
              <th className="px-3 py-2 text-right font-semibold">Rate</th>
              <th className="px-3 py-2 text-right font-semibold">Amount</th>
            </tr>
          </thead>
          <tbody>
            {ex.boq.map((r) => (
              <tr key={r.n} className="border-t">
                <td className="px-3 py-1.5">{r.item}</td>
                <td className="num px-3 py-1.5 text-right">
                  {r.qty.toLocaleString("en-IN")} {r.unit}
                </td>
                <td className="num px-3 py-1.5 text-right">{rs(r.rate)}</td>
                <td className="num px-3 py-1.5 text-right">{rs(r.amount)}</td>
              </tr>
            ))}
            <tr className="border-t bg-muted/40 font-semibold">
              <td className="px-3 py-1.5" colSpan={3}>
                F. The estimate (the MP recommended {inr(ex.check.mp_amount)})
              </td>
              <td className="num px-3 py-1.5 text-right">{rs(total)}</td>
            </tr>
          </tbody>
        </table>
      </div>
      {y && (
        <p className="rounded-xl bg-muted/50 px-3 py-2 text-[13px]">
          <span className="font-semibold">Against real works in Uttar Pradesh: </span>
          {y.note ??
            `${rs(y.per ?? 0)} a ${y.unit}. ${y.works?.toLocaleString("en-IN")} real ${
              y.unit === "light" ? "solar street lights" : "CC roads"
            } cost ${rs(y.p10 ?? 0)} to ${rs(y.p90 ?? 0)} a ${y.unit} (middle 80%, median ${rs(y.median ?? 0)})${
              y.district ? `; in Jaunpur, ${y.district.works} works, median ${rs(y.district.median)}` : ""
            }. ${y.inside ? "Inside the real range" : "Outside the real range"}.`}
        </p>
      )}
    </div>
  );
}

function CheckStep({ ex }: { ex: Filing }) {
  const c = ex.check;
  return (
    <div className="space-y-3 text-[13px]">
      <p className="flex flex-wrap items-center gap-2">
        <span
          className={cn(
            "rounded-full px-2.5 py-0.5 text-xs font-semibold",
            c.ready ? "bg-[var(--low-soft)] text-[var(--low)]" : "bg-[var(--high-soft)] text-[var(--high)]",
          )}
        >
          {c.ready ? "Ready to file" : "Not ready"}
        </span>
        <span className="text-muted-foreground">
          The estimate {inr(c.grand_total)} · the MP recommended {inr(c.mp_amount)}
          {c.mp_gap !== null && ` (${Math.abs(c.mp_gap) < 0.0005 ? "the same" : `${(c.mp_gap * 100).toFixed(1)}% apart`})`}
        </span>
      </p>
      <ul className="grid gap-1.5 sm:grid-cols-2">
        {c.passed.map((p) => (
          <li key={p} className="flex items-center gap-2">
            <span className="grid size-4 place-items-center rounded-full bg-[var(--low)] text-[10px] text-white">✓</span> {p}
          </li>
        ))}
      </ul>
      {[...c.fix, ...c.confirm].length > 0 && (
        <ul className="space-y-1 text-muted-foreground">
          {[...c.fix, ...c.confirm].map((m) => (
            <li key={m}>· {m}</li>
          ))}
        </ul>
      )}
      <p className="text-muted-foreground">
        The form catches honest mistakes before filing (a missing answer, lines that do not add up, a quantity the size cannot use).
        What it lets through, the agents read.
      </p>
    </div>
  );
}

const CHIP: Record<AgentLine["state"], { label: string; className: string }> = {
  flagged: { label: "Asks", className: "bg-[var(--high)] text-white" },
  clear: { label: "Clear", className: "bg-[var(--low-soft)] text-[var(--low)]" },
  not_checked: { label: "Not checked", className: "bg-muted text-muted-foreground" },
  later: { label: "After sanction", className: "bg-muted text-muted-foreground" },
};

function AgentsStep({ ex }: { ex: Filing }) {
  const lines = agentLines(ex.trace, ex.form).filter((l) => l.id !== "site_progress");
  const tp = ex.time_plan;
  return (
    <ul className="grid gap-2 lg:grid-cols-2">
      {lines.map((l) => {
        const meta = agentMeta(l.id);
        const flagged = l.state === "flagged";
        const check = ex.trace.checks.find((c) => c.id === l.id);
        return (
          <li
            key={l.id}
            className="rounded-xl border p-3"
            style={flagged ? { borderColor: meta.color, background: `color-mix(in srgb, ${meta.color} 6%, transparent)` } : undefined}
          >
            <div className="flex items-center gap-2">
              <EngineMark id={l.id} size={22} />
              <span className="text-sm font-semibold" style={{ color: flagged ? meta.color : undefined }}>
                {meta.name}
              </span>
              <span className={cn("ml-auto rounded-full px-2 py-0.5 text-[11px] font-semibold", CHIP[l.state].className)}>
                {CHIP[l.state].label}
              </span>
            </div>
            {flagged ? (
              l.flags.map((f) => (
                <p key={f.code} className="mt-2 text-[13px] leading-snug">
                  {f.why}
                </p>
              ))
            ) : (
              <p className="mt-2 text-[13px] leading-snug text-muted-foreground">{check?.headline}</p>
            )}
            {l.id === "time_rules" && tp && (
              <p className="mt-2 rounded-lg bg-muted/60 px-2 py-1.5 text-xs">
                If sanctioned today, it watches the agency&apos;s own estimate: done {tp.early ? `no earlier than ${day(tp.early)} and ` : ""}by{" "}
                {day(tp.late)} (grace included). Finishing earlier with no site video, or later, is asked.
              </p>
            )}
          </li>
        );
      })}
      <li className="rounded-xl border-2 border-dashed p-3" style={{ borderColor: agentMeta("site_progress").color }}>
        <div className="flex items-center gap-2">
          <EngineMark id="site_progress" size={22} />
          <span className="text-sm font-semibold">{agentMeta("site_progress").name}</span>
          <span className="ml-auto inline-flex items-center gap-1 rounded-full bg-muted px-2 py-0.5 text-[11px] font-semibold text-muted-foreground">
            <Construction className="size-3" /> Placeholder
          </span>
        </div>
        <p className="mt-2 text-[13px] leading-snug text-muted-foreground">
          Starts after sanction: a first site video before work begins, then one a month from the same fixed viewpoints, each with the
          agency&apos;s claim for the month. It will join this walk-through once its field trial on real site videos (T126) is done.
        </p>
      </li>
    </ul>
  );
}

function ScoreStep({ ex }: { ex: Filing }) {
  const s = ex.trace.scoring;
  const r = ex.trace.result;
  const score = Math.round(r.score * 100);
  return (
    <div className="grid gap-4 lg:grid-cols-[220px_minmax(0,1fr)]">
      <div className="rounded-xl border p-4 text-center">
        <p className="num text-5xl font-bold tracking-tight">{score}</p>
        <p className="text-xs text-muted-foreground">out of 100</p>
        <div className="mt-2 flex justify-center">
          <BandBadge band={r.band} />
        </div>
      </div>
      <div className="min-w-0 space-y-3 text-[13px]">
        {s.chain.length === 0 ? (
          <p>No agent asks anything, so nothing adds to the score.</p>
        ) : (
          <ul className="space-y-2">
            {s.chain.map((c) => {
              const meta = agentMeta(c.engine);
              return (
                <li key={c.engine} className="space-y-1">
                  <div className="flex items-center gap-2">
                    <EngineMark id={c.engine} size={18} />
                    <span className="font-medium">{meta.name}</span>
                    <span className="ml-auto text-muted-foreground">
                      chance it needs checking <span className="num font-semibold text-foreground">{Math.round(c.chance * 100)}%</span> ·
                      together <span className="num font-semibold text-foreground">{Math.round(c.score * 100)}</span>
                    </span>
                  </div>
                  <div className="h-2 overflow-hidden rounded-full bg-muted">
                    <motion.div
                      className="h-full rounded-full"
                      style={{ background: meta.color }}
                      initial={{ width: 0 }}
                      animate={{ width: `${c.score * 100}%` }}
                      transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
                    />
                  </div>
                </li>
              );
            })}
          </ul>
        )}
        <p className="text-muted-foreground">
          Each agent&apos;s question counts by how often such a question has proved right (a new kind of question counts 1 in 4 until
          officers have read enough of them); together they make the score: 1 − (1 − a)(1 − b)… Lines: {Math.round(s.lines.MEDIUM * 100)}{" "}
          medium, {Math.round(s.lines.HIGH * 100)} high.
        </p>
        <p className="rounded-xl bg-brand-50 px-3 py-2 font-semibold text-brand-950">{ex.decision}</p>
      </div>
    </div>
  );
}

function AfterSanction({ ex }: { ex: Filing }) {
  const tp = ex.time_plan;
  return (
    <section className="panel flex flex-wrap items-center gap-3 p-4 text-[13px] sm:p-5" aria-label="After sanction">
      <span className="grid size-8 place-items-center rounded-lg bg-muted">
        <Video className="size-4 text-muted-foreground" />
      </span>
      <p className="min-w-0 flex-1">
        <span className="font-semibold">The loop goes on after sanction.</span> Time &amp; Rules watches the window
        {tp ? ` (by ${day(tp.late)})` : ""}; Site Progress (placeholder) reads the monthly site videos; each new answer goes back into the
        score, and the officer sees it.
      </p>
    </section>
  );
}
