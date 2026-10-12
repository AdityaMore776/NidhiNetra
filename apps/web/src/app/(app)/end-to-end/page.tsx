"use client";

import { ArrowRight, Check, ClipboardCheck, Construction, Gauge, ListChecks, PenLine, Play, RotateCcw, Video, X } from "lucide-react";
import { motion, useReducedMotion } from "motion/react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useRef, useState } from "react";
import { BandBadge, EngineMark } from "@/components/nn/badges";
import { PageHeader } from "@/components/nn/layout-bits";
import { Button } from "@/components/ui/button";
import type { Trace } from "@/lib/explain";
import { agentMeta, inr } from "@/lib/format";
import FORM_HTML from "@/lib/forms/pre-sanction-work-intelligence-form";
import { FormMap } from "@/components/nn/form-map";
import { type AgentLine, agentLines, type Flag, markForm } from "@/lib/work-form-flags";
import { cn } from "@/lib/utils";
import { fillForm, fitFrame } from "@/lib/work-form-frame";

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

/** The Cost agent's reading of one estimate line (T138, end_to_end_examples.cost_lines). */
interface CostLine {
  n: number;
  // the form fields holding the line's rate and quantity (a BOQ line, or a labour row: T141)
  rate_field?: string;
  qty_field?: string;
  state: "rate" | "quantity_only" | "unread" | "no_data" | "whole_item" | "labour";
  level: "high" | "watch" | "ok" | "none";
  material?: string;
  unit?: string;
  extra: number;
  fair_rate?: number;
  pct?: number;
  range?: { low: number; high: number; agencies: number; forms: number } | null;
  where?: string;
  needed?: number;
  needed_low?: number;
  allowed?: number;
  fair_low?: number | null;
  fair_high?: number | null;
  p10?: number | null;
  p90?: number | null;
  qty_ratio?: number | null;
  over?: number;
  share?: number;
  forms?: number;
  agencies?: number;
  need?: string;
  per?: number;
  per_unit?: string;
  median?: number;
  works?: number;
  where_text?: string;
  limit?: number;
  situations: { label: string; applies: boolean; note: string }[];
}

interface CostReading {
  lines: CostLine[];
  summary: {
    verdict: "ASK" | "FAIR" | "CANT_CHECK" | null;
    grand: number;
    fair: number;
    fair_low?: number;
    fair_high?: number;
    gap: number;
    share: number;
    coverage: number;
    limit_share: number;
    limit_rs: number;
    qty_slack: number;
    unread_allowed: number;
    unexplained: Record<string, number>;
    lines_total: number;
    asks: boolean;
  };
}

interface Filing {
  id: string;
  title: string;
  story: string;
  flagged: boolean;
  form: Record<string, unknown>;
  typed: { section: string; fields: [string, string][] }[];
  boq: { n: number; item: string; unit: string; qty: number; rate: number; amount: number; source: string; rate_field?: string; qty_field?: string }[];
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
  cost?: CostReading;
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

/** The agents' flags for this filing, the Cost agent's marking every estimate line it reads as high
 *  (ex.cost), not only the three lines its sentence names. */
function filingFlags(ex: Filing): { lines: AgentLine[]; flags: Flag[] } {
  const lines = agentLines(ex.trace, ex.form);
  const flags = lines.flatMap((l) => l.flags);
  const cost = flags.find((f) => f.agent === "cost_estimate");
  if (cost && ex.cost) {
    const extra: Flag["fields"] = [];
    for (const l of ex.cost.lines) {
      if (l.level !== "high") continue;
      const rateField = l.rate_field ?? `boq_rate_${l.n}`;
      const qtyField = l.qty_field ?? `boq_qty_${l.n}`;
      if (l.state === "rate" && l.fair_rate !== undefined)
        extra.push({ name: rateField, label: `+${pctOf(l.pct ?? 0)} · others ${l.range ? span(l.range.low, l.range.high, rs) : rs(l.fair_rate)}` });
      if (l.state === "unread") extra.push({ name: qtyField, label: `${pctOf(l.share ?? 0)} of lines, unpriced` });
      if ((l.qty_ratio ?? 0) > 1 + ex.cost.summary.qty_slack)
        extra.push({ name: qtyField, label: `${(l.qty_ratio ?? 0).toFixed(1)}× · size takes ${span(l.needed_low, l.needed, num)}` });
    }
    const keep = cost.fields.filter((f) => !/^(boq|lab)_/.test(f.name) || !extra.some((e) => e.name === f.name));
    cost.fields = [...keep, ...extra];
  }
  return { lines, flags };
}

function FormStep({ ex }: { ex: Filing }) {
  const frame = useRef<HTMLIFrameElement>(null);
  const [mode, setMode] = useState<"sections" | "form">("sections");
  const unfit = useRef<() => void>(() => {});
  useEffect(() => () => unfit.current(), []);
  const y = ex.yardstick;
  const { lines, flags } = filingFlags(ex);

  // the one work intelligence form the agency fills (the same as /work-form), filled with this
  // filing through the form's own functions, the agents' flagged fields outlined
  function load() {
    if (fillForm(frame.current, ex.form)) markForm(frame.current?.contentDocument, flags);
    // below lg the form takes its full height, so a phone scrolls one page (T143)
    unfit.current();
    unfit.current = fitFrame(frame.current, "(min-width: 1024px)");
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <p className="min-w-0 flex-[1_1_16rem] text-[13px] text-muted-foreground">
          The agency&apos;s filing in the{" "}
          <Link href="/work-form" className="font-medium text-brand-700 underline-offset-2 hover:underline">
            work intelligence form
          </Link>
          : every section, what each agent reads, and every field an agent asks about, in its colour.
        </p>
        <div className="flex gap-1 rounded-xl bg-muted p-1 text-xs font-medium" role="tablist">
          {(
            [
              ["sections", "Section by section"],
              ["form", "The form as filed"],
            ] as const
          ).map(([id, label]) => (
            <button
              key={id}
              type="button"
              role="tab"
              aria-selected={mode === id}
              onClick={() => setMode(id)}
              className={cn(
                "rounded-lg px-2.5 py-1 transition-colors",
                mode === id ? "bg-white text-brand-950 shadow-sm" : "text-muted-foreground hover:text-foreground",
              )}
            >
              {label}
            </button>
          ))}
        </div>
      </div>
      {mode === "sections" && <FormMap form={ex.form} flags={flags} agents={lines} />}
      <div className={cn("overflow-hidden rounded-xl border", mode !== "form" && "hidden")}>
        <iframe
          ref={frame}
          title={`Work intelligence form: ${ex.title}`}
          srcDoc={FORM_HTML}
          onLoad={load}
          className="block h-[70svh] min-h-[560px] w-full border-0 bg-[#eef2f7]"
        />
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
    <div className="space-y-4">
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
      {ex.cost && <CostTable ex={ex} cost={ex.cost} />}
    </div>
  );
}

const LEVEL: Record<CostLine["level"], { fg: string; bg: string }> = {
  high: { fg: "var(--high)", bg: "var(--high-soft)" },
  watch: { fg: "var(--medium)", bg: "var(--medium-soft)" },
  ok: { fg: "var(--low)", bg: "var(--low-soft)" },
  none: { fg: "var(--muted-foreground)", bg: "var(--muted)" },
};
const SITUATION: Record<string, string> = {
  "Hard-to-reach site": "Remote site",
  "Agency's reason for this line": "Agency's reason",
  "Official rate cited": "Official rate",
};
const UNIT: Record<string, string> ={ m3: "m³", m2: "m²", nos: "piece" };
const unitOf = (u?: string) => (u ? (UNIT[u] ?? u) : "unit");
const pctOf = (v: number) => `${Math.round(Math.abs(v) * 100)}%`;
const lakh = (v: number) => (Math.abs(v) >= 1e5 ? `₹${(v / 1e5).toFixed(2)} lakh` : rs(v));
const num = (v: number) => Math.round(v).toLocaleString("en-IN");
/** T145: what a quantity or price should be, as a range; one figure when its ends meet. */
const span = (low: number | null | undefined, high: number | null | undefined, f: (v: number) => string) =>
  low == null || high == null || f(low) === f(high) ? f(high ?? low ?? 0) : `${f(low)}–${f(high)}`;

/** The agent's reading of one line: a coloured headline and a few short facts. */
function reading(l: CostLine, s: CostReading["summary"]): { badge: string; facts: string[] } {
  const u = unitOf(l.unit);
  const facts: string[] = [];
  let badge: string;
  if (l.state === "rate" && l.fair_rate !== undefined) {
    const pct = l.pct ?? 0;
    badge =
      pct > 0.005 ? `▲ ${pctOf(pct)} above the usual rate` : pct < -0.005 ? `▼ ${pctOf(pct)} below the usual rate` : "At the usual rate";
    facts.push(
      `Usual: ${rs(l.fair_rate)} a ${u}${l.where === "state" ? " (state-wide, 10% leeway)" : ""}` +
        (l.range ? ` · ${l.range.agencies} other agencies here charge ${rs(l.range.low)} to ${rs(l.range.high)}` : ""),
    );
  } else if (l.state === "labour" && l.fair_rate !== undefined) {
    // T141: a crew's day rate is asked about only at twice what others pay the trade here
    badge = "Within the trade's band";
    facts.push(
      `Others here pay ${span(l.fair_low ?? l.fair_rate, l.fair_high ?? l.fair_rate, rs)} a day for this trade (usual ${rs(l.fair_rate)}); asked only from ${rs(l.limit ?? 0)} (twice it)` +
        ((l.pct ?? 0) > 0.005 ? ` · this row is ${pctOf(l.pct ?? 0)} above` : ""),
    );
    facts.push("How many workers and days a work needs is the agency's call");
  } else if (l.state === "unread") {
    badge = l.level === "high" ? "Can't be priced, and too big a share" : "Not a standard item (small share: fine)";
    facts.push(
      `No price list covers this item. It is ${pctOf(l.share ?? 0)} of the lines; up to ${pctOf(s.unread_allowed)} may go unpriced`,
    );
    if (l.over) facts.push(`${lakh(l.over)} beyond that is counted as unexplained`);
  } else if (l.state === "no_data") {
    badge = "Not priced yet";
    facts.push(`Only ${l.forms ?? 0} recent forms from ${l.agencies ?? 0} agencies here; needs ${l.need}`);
    facts.push("Counted at the agency's own price, never guessed");
  } else if (l.state === "whole_item" && l.per !== undefined) {
    badge = l.level === "high" ? `▲ ${pctOf(l.pct ?? 0)} above real works` : "In line with real works";
    facts.push(
      `${rs(l.per)} a ${l.per_unit}; ${l.works} real works in ${l.where_text}` +
        (l.p10 != null && l.p90 != null ? `: 8 in 10 cost ${span(l.p10, l.p90, rs)}` : "") +
        `, median ${rs(l.median ?? 0)}`,
    );
    facts.push(`Asks only above ${rs(l.limit ?? 0)} a ${l.per_unit} and over 10% above the MP's amount`);
  } else {
    badge = "Quantity fits the size";
  }
  if (l.needed !== undefined && l.allowed !== undefined) {
    const many = (l.qty_ratio ?? 0) > 1 + s.qty_slack;
    facts.push(
      `${many ? `▲ ${(l.qty_ratio ?? 0).toFixed(1)}× what the size needs. ` : ""}Size takes ${span(l.needed_low, l.needed, num)} ${/[²³]$|^m$/.test(u) ? u : `${u}s`}; fine up to ${Math.round(l.allowed).toLocaleString("en-IN")} (+${pctOf(s.qty_slack)})`,
    );
    if (many && l.state !== "rate") badge = `▲ ${(l.qty_ratio ?? 0).toFixed(1)}× the quantity needed`;
  }
  if (l.extra > 0) facts.push(`Adds ${lakh(l.extra)} over the fair price`);
  return { badge, facts };
}

/** Step 3, the Cost agent line by line (T138): which lines are above the usual price and by how much,
 * the band it calls normal, and whether anything on the form could explain the difference. */
function CostTable({ ex, cost }: { ex: Filing; cost: CostReading }) {
  const color = agentMeta("cost_estimate").color;
  const s = cost.summary;
  const byN = new Map(cost.lines.map((l) => [l.n, l]));
  const over = Math.max(0, s.share);
  const scale = Math.max(s.limit_share * 2, over * 1.15, 0.01);
  return (
    <section className="space-y-3" aria-label="The Cost agent, line by line">
      <h4 className="flex items-center gap-2 text-sm font-semibold">
        <EngineMark id="cost_estimate" size={20} />
        What the Cost agent reads, line by line
      </h4>
      {/* T143: on a phone each line is a block: the item, its three numbers, then the agent's reading */}
      <div className="overflow-x-auto rounded-xl border">
        <table className="w-full text-[13px] max-sm:block sm:min-w-[920px]">
          <thead className="text-left text-[11px] uppercase tracking-wider text-muted-foreground max-sm:hidden">
            <tr className="bg-muted/60">
              <th className="px-3 py-2 font-semibold">E. Estimate line</th>
              <th className="px-3 py-2 text-right font-semibold">Quantity</th>
              <th className="px-3 py-2 text-right font-semibold">Rate</th>
              <th className="px-3 py-2 text-right font-semibold">Amount</th>
              <th
                className="w-[46%] border-l-4 px-3 py-2 font-semibold"
                style={{
                  borderColor: color,
                  background: `color-mix(in srgb, ${color} 12%, white)`,
                  color,
                }}
              >
                The agent&apos;s reading
              </th>
            </tr>
          </thead>
          <tbody className="max-sm:block">
            {ex.boq.map((r) => {
              const l = byN.get(r.n);
              if (!l) return null;
              const lv = LEVEL[l.level];
              const { badge, facts } = reading(l, s);
              const asked = l.level === "high" || l.level === "watch";
              const reason = l.situations.some((x) => x.applies && x.label !== "Official rate cited");
              return (
                <tr
                  key={r.n}
                  className="border-t align-top max-sm:grid max-sm:grid-cols-3 max-sm:first:border-t-0"
                  style={
                    asked
                      ? {
                          background: `color-mix(in srgb, ${lv.bg} 45%, white)`,
                        }
                      : undefined
                  }
                >
                  <td className="px-3 py-2 max-sm:col-span-3 max-sm:pb-0">
                    <span className={cn(asked && "font-semibold")}>{r.item}</span>
                    <span className="block text-[11px] text-muted-foreground">{r.source}</span>
                  </td>
                  <td className="num whitespace-nowrap px-3 py-2 text-right max-sm:text-left">
                    <span className="block text-[10px] text-muted-foreground sm:hidden">Quantity</span>
                    {r.qty.toLocaleString("en-IN")} {unitOf(r.unit)}
                  </td>
                  <td
                    className="num whitespace-nowrap px-3 py-2 text-right max-sm:text-left"
                    style={asked && l.state === "rate" ? { color: lv.fg, fontWeight: 600 } : undefined}
                  >
                    <span className="block text-[10px] font-normal text-muted-foreground sm:hidden">Rate</span>
                    {rs(r.rate)}
                  </td>
                  <td className="num whitespace-nowrap px-3 py-2 text-right max-sm:text-left">
                    <span className="block text-[10px] text-muted-foreground sm:hidden">Amount</span>
                    {rs(r.amount)}
                  </td>
                  <td
                    className="border-l-4 px-3 py-2 max-sm:col-span-3"
                    style={{
                      borderColor: color,
                      background: `color-mix(in srgb, ${color} 5%, white)`,
                    }}
                  >
                    <span
                      className="inline-block rounded-full px-2 py-0.5 text-[11px] font-semibold"
                      style={{ background: lv.bg, color: lv.fg }}
                    >
                      {badge}
                    </span>
                    <ul className="mt-1.5 space-y-0.5 text-[12px] leading-snug">
                      {facts.map((f) => (
                        <li key={f}>{f}</li>
                      ))}
                    </ul>
                    {asked && (
                      <div className="mt-2 space-y-1 border-t pt-1.5 text-[12px] leading-snug">
                        <div className="flex flex-wrap items-center gap-1">
                          <span className="mr-0.5 text-[11px] font-semibold text-muted-foreground">Could it be justified?</span>
                          {l.situations.map((x) => (
                            <span
                              key={x.label}
                              title={`${x.label}: ${x.note}`}
                              className={cn(
                                "inline-flex items-center gap-0.5 rounded-md border px-1.5 py-px text-[11px]",
                                x.applies ? "border-[var(--medium)] bg-[var(--medium-soft)] text-[var(--medium)]" : "text-muted-foreground",
                              )}
                            >
                              {x.applies ? <Check className="size-3" /> : <X className="size-3" />}
                              {SITUATION[x.label] ?? x.label}
                            </span>
                          ))}
                        </div>
                        {l.situations
                          .filter((x) => x.applies && x.label !== "Official rate cited")
                          .map((x) => (
                            <p key={x.label} className="text-muted-foreground">
                              {SITUATION[x.label] ?? x.label}: {x.note}
                            </p>
                          ))}
                        <p className="font-semibold" style={{ color: reason ? "var(--medium)" : "var(--high)" }}>
                          {reason ? "The form gives a reason: the officer weighs it" : "Nothing on the form explains it"}
                        </p>
                      </div>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      {s.verdict && s.verdict !== "CANT_CHECK" && (
        <div className="grid gap-3 rounded-xl border p-3 text-[13px] sm:grid-cols-[minmax(0,1fr)_auto] sm:items-center">
          <div className="min-w-0 space-y-1.5">
            <p>
              <span className="font-semibold">Whole estimate {lakh(s.grand)}</span> against a fair {lakh(s.fair)}
              {s.fair_low != null && s.fair_high != null && span(s.fair_low, s.fair_high, lakh) !== lakh(s.fair)
                ? ` (${span(s.fair_low, s.fair_high, lakh)} at the lowest and highest rates other agencies charge)`
                : ""}
              :{" "}
              <span className="font-semibold" style={{ color: s.asks ? "var(--high)" : "var(--low)" }}>
                {s.share >= 0 ? "+" : "−"}
                {pctOf(s.share)}
              </span>{" "}
              on the fair price of what could be priced ({pctOf(s.coverage)} of the money).
            </p>
            <div className="relative h-2.5 overflow-hidden rounded-full bg-muted" aria-hidden>
              <div
                className="h-full rounded-full"
                style={{
                  width: `${Math.min(100, (over / scale) * 100)}%`,
                  background: s.asks ? "var(--high)" : "var(--low)",
                }}
              />
              <div className="absolute inset-y-0 w-0.5 bg-foreground" style={{ left: `${(s.limit_share / scale) * 100}%` }} />
            </div>
            <p className="text-muted-foreground">
              Comfort limit (the black mark): the agent asks only when the whole estimate is more than {pctOf(s.limit_share)} and{" "}
              {rs(s.limit_rs)} above its fair price. One costly line can be honest; many lines a little high is a pattern.
            </p>
          </div>
          <span
            className="justify-self-start rounded-full px-3 py-1 text-xs font-semibold sm:justify-self-end"
            style={s.asks ? { background: "var(--high)", color: "white" } : { background: "var(--low-soft)", color: "var(--low)" }}
          >
            {s.asks ? "Over the limit: asks" : "Within the limit"}
          </span>
        </div>
      )}
    </section>
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
        {tp ? ` (by ${day(tp.late)})` : ""}; NidhiLens (Fine-Tuned Site Progress Model), a placeholder here, reads the monthly site videos; each new answer goes back into the
        score, and the officer sees it.
      </p>
    </section>
  );
}
