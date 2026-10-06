"use client";

import { ArrowRight, ChevronLeft, ChevronRight, ClipboardList, Pause, Play, RotateCcw } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { FloatingPaths } from "@/components/kokonutui/background-paths";
import { Logo } from "@/components/Logo";
import type { ExamplesFile, Trace } from "@/lib/explain";
import { BAND_COLOR } from "@/lib/format";
import { ChecksStep, CHECK_GAP, InputStep, PrivacyStep, ReadingStep, ResultStep, SCORE_ROW, ScoreStep } from "./steps";

type StepDef = {
  title: string;
  short: string;
  what: string;
  ms: (t: Trace) => number;
  View: (p: { t: Trace }) => React.ReactElement;
};

const STEPS: StepDef[] = [
  {
    title: "The form goes in",
    short: "Input",
    what: "The implementing agency files the work intelligence form before sanction: what the work is, what it says, how much, where, which office, its estimate line by line, its labour and its dates.",
    ms: () => 5200,
    View: InputStep,
  },
  {
    title: "Private details are hidden",
    short: "Privacy",
    what: "Before anything else, names of private people, phone numbers and bank account numbers are covered up.",
    ms: () => 5200,
    View: PrivacyStep,
  },
  {
    title: "Reading the description",
    short: "Reading",
    what: "NidhiNetra reads the words like an officer would: which name a place, a size, a construction or a purchase, and whether any is on the guidelines' not-allowed list. Each fact it finds lights up.",
    ms: (t) => 4200 + Math.min(2600, t.reading.segments.length * 60) + 1800,
    View: ReadingStep,
  },
  {
    title: "Every check looks at it at once",
    short: "Checks",
    what: "Like the channels of a picture, every check asks its own question at the same time. A check that finds something lights up; one that cannot look says so instead of guessing.",
    ms: (t) => 1800 + t.checks.length * CHECK_GAP + 2200,
    View: ChecksStep,
  },
  {
    title: "Adding up the score",
    short: "Score",
    what: "Each question becomes a chance: how often that kind of question was worth a look when officers read past cases, times how strong this one is. The chances combine into one score.",
    ms: (t) => {
      const rows = t.scoring.engines.reduce((n, e) => n + e.findings.length, 0);
      return 1800 + rows * SCORE_ROW + t.scoring.chain.length * 1100 + 2400;
    },
    View: ScoreStep,
  },
  {
    title: "What the officer gets",
    short: "Result",
    what: "The officer sees the band, whether the work is in the review queue, and the top reasons in plain words.",
    ms: () => 6000,
    View: ResultStep,
  },
];

export default function Explainer() {
  const [file, setFile] = useState<ExamplesFile | null>(null);
  const [loadError, setLoadError] = useState(false);
  const [pick, setPick] = useState("time_fast");
  const [step, setStep] = useState(0);
  const [run, setRun] = useState(0);
  const [playing, setPlaying] = useState(false);

  useEffect(() => {
    let live = true;
    // T142: the filings of the work intelligence form, the same as /work-form and the dashboard
    fetch("/work-form/examples.json")
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(String(r.status)))))
      .then((f: ExamplesFile) => {
        if (!live) return;
        setFile(f);
        // a prototype example's page links here with ?example=<id> (T132)
        const asked = new URLSearchParams(window.location.search).get("example");
        if (asked && f.examples.some((e) => e.id === asked)) setPick(asked);
      })
      .catch(() => live && setLoadError(true));
    return () => {
      live = false;
    };
  }, []);

  const example = file?.examples.find((e) => e.id === pick) ?? null;
  const trace = example?.trace ?? null;
  const ref = typeof example?.form?.recommendation_ref === "string" ? example.form.recommendation_ref : null;

  // Play all: each step hands over to the next when its animation has played.
  useEffect(() => {
    if (!playing || !trace) return;
    const id = window.setTimeout(() => {
      if (step >= STEPS.length - 1) setPlaying(false);
      else {
        setStep(step + 1);
        setRun((r) => r + 1);
      }
    }, STEPS[step].ms(trace));
    return () => window.clearTimeout(id);
  }, [playing, step, run, trace]);

  const go = useCallback((i: number) => {
    setPlaying(false);
    setStep(Math.max(0, Math.min(STEPS.length - 1, i)));
    setRun((r) => r + 1);
  }, []);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if ((e.target as HTMLElement | null)?.closest("input, textarea, select")) return;
      if (e.key === "ArrowRight") {
        setPlaying(false);
        setStep((s) => Math.min(STEPS.length - 1, s + 1));
        setRun((r) => r + 1);
      } else if (e.key === "ArrowLeft") {
        setPlaying(false);
        setStep((s) => Math.max(0, s - 1));
        setRun((r) => r + 1);
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  function choose(id: string) {
    setPick(id);
    setStep(0);
    setRun((r) => r + 1);
    setPlaying(true);
  }

  function playAll() {
    setStep(0);
    setRun((r) => r + 1);
    setPlaying(true);
  }

  const S = STEPS[step];

  return (
    <div className="min-h-screen bg-white">
      <header className="sticky top-0 z-20 border-b bg-white/75 backdrop-blur-xl">
        <div className="mx-auto flex h-16 max-w-6xl items-center gap-4 px-4">
          <Link href="/explain">
            <Logo size={34} tagline="Visualization Engine" />
          </Link>
          <nav className="ml-auto flex items-center gap-2 text-sm">
            <Link
              href="/"
              className="inline-flex items-center gap-1.5 rounded-xl bg-brand-900 px-4 py-2 font-medium text-white shadow-[0_8px_20px_-10px_rgb(11_37_96/0.9)] transition hover:bg-brand-800"
            >
              Open NidhiNetra <ArrowRight className="size-4" />
            </Link>
          </nav>
        </div>
      </header>

      <main className="mx-auto max-w-6xl space-y-6 px-4 py-8">
        <section className="relative overflow-hidden rounded-3xl border bg-gradient-to-br from-brand-50 via-white to-white p-6 sm:p-8">
          <FloatingPaths intensity={0.35} />
          <div className="relative">
            <div className="eyebrow flex items-center gap-2">
              <span className="tricolor-rule w-6 rounded-full" />
              Visualization Engine · no sign-in
            </div>
            <h1 className="mt-3 text-3xl font-semibold tracking-[-0.035em] text-brand-950 sm:text-[2.5rem] sm:leading-[1.08]">
              What NidhiNetra does with one work, <span className="display pr-1 italic text-brand-gradient">step by step.</span>
            </h1>
            <p className="mt-3 max-w-3xl text-[15px] leading-relaxed text-muted-foreground">
              Pick a filing of the work intelligence form and watch it go through the same six steps as every form checked on the
              live site. Press any step to see it again. Every number on this page comes from the real engines.
            </p>
          </div>
        </section>

        <section aria-label="Examples" className="flex flex-wrap gap-2">
          {(file?.examples ?? []).map((e) => (
            <button
              key={e.id}
              onClick={() => choose(e.id)}
              className={`rounded-full border px-3 py-1.5 text-xs font-medium transition-all sm:text-sm ${pick === e.id ? "border-transparent bg-brand-gradient text-white shadow-[0_8px_20px_-10px_rgb(10_102_194/0.9)]" : "bg-white text-foreground hover:border-brand-200 hover:bg-brand-50"}`}
            >
              {e.title}
            </button>
          ))}
          <Link
            href="/work-form"
            className="rounded-full border border-dashed border-brand-400 px-3 py-1.5 text-xs font-medium text-brand-700 transition-all hover:bg-brand-50 sm:text-sm"
          >
            + Check your own form
          </Link>
        </section>

        {loadError && <p className="text-sm text-high">The examples could not be loaded. Please reload the page.</p>}
        {!file && !loadError && <p className="text-sm text-muted-foreground">Loading the examples…</p>}

        {example && (
          <p className="rounded-xl border-l-2 border-brand-400 bg-muted/60 px-4 py-3 text-sm leading-relaxed">
            <span className="font-semibold text-brand-950">{example.title}.</span> {example.story}
            {ref && (
              <Link
                href={`/work?id=${encodeURIComponent(ref)}`}
                className="ml-2 inline-flex items-center gap-1 font-medium text-brand-700 underline-offset-2 hover:underline"
              >
                <ClipboardList className="size-3.5" /> See the form as filed
              </Link>
            )}
          </p>
        )}

        {trace && (
          <>
            <Stepper step={step} onGo={go} />
            <div className="flex flex-wrap items-center gap-2">
              <button onClick={() => go(step - 1)} disabled={step === 0} className={CTRL}>
                <ChevronLeft className="size-4" /> Back
              </button>
              {playing ? (
                <button onClick={() => setPlaying(false)} className={PRIMARY}>
                  <Pause className="size-4" /> Pause
                </button>
              ) : (
                <button onClick={playAll} className={PRIMARY}>
                  <Play className="size-4" /> Play all six steps
                </button>
              )}
              <button onClick={() => go(step)} className={CTRL}>
                <RotateCcw className="size-4" /> Replay this step
              </button>
              <button onClick={() => go(step + 1)} disabled={step === STEPS.length - 1} className={CTRL}>
                Next <ChevronRight className="size-4" />
              </button>
              <span className="ml-auto hidden items-center gap-1 text-xs text-muted-foreground sm:inline-flex">
                Keys <kbd className="rounded border bg-muted px-1.5 font-mono text-[10px]">←</kbd>
                <kbd className="rounded border bg-muted px-1.5 font-mono text-[10px]">→</kbd>
              </span>
            </div>

            <section className="panel overflow-hidden">
              <div className="h-1 bg-muted">
                {playing && (
                  <div key={`${pick}-${step}-${run}`} className="x-progress h-full bg-brand-gradient" style={{ "--dur": `${S.ms(trace)}ms` } as React.CSSProperties} />
                )}
              </div>
              <div className="space-y-5 p-5 sm:p-7">
                <div>
                  <div className="eyebrow">
                    Step {step + 1} of {STEPS.length}
                  </div>
                  <h2 className="mt-1 text-xl font-semibold tracking-[-0.02em] text-brand-950 sm:text-2xl">{S.title}</h2>
                  <p className="mt-1.5 max-w-3xl text-sm leading-relaxed text-muted-foreground">{S.what}</p>
                </div>
                <div key={`${pick}-${step}-${run}`} className="x-stage">
                  <S.View t={trace} />
                </div>
              </div>
            </section>

            <ResultStrip t={trace} />
          </>
        )}

        <footer className="space-y-1 border-t pb-8 pt-5 text-[11px] text-muted-foreground">
          {file && (
            <p>
              Built-in examples: forms filed by made-up agencies in a real district, checked by the real engines against the {file.source}.
              The other works shown are real, with private names hidden.
            </p>
          )}
          <p>
            NidhiNetra flags works that need verification. It never decides; officers do. SIH 2026 · SIH26102 · Team NeuralNexus.
          </p>
        </footer>
      </main>
    </div>
  );
}

const CTRL =
  "inline-flex items-center gap-1.5 rounded-xl border bg-white px-3.5 py-2 text-sm font-medium transition-colors hover:border-brand-200 hover:bg-brand-50 disabled:pointer-events-none disabled:opacity-40";
const PRIMARY =
  "inline-flex items-center gap-1.5 rounded-xl bg-brand-gradient px-4 py-2 text-sm font-semibold text-white shadow-[0_8px_20px_-10px_rgb(10_102_194/0.9)] transition hover:opacity-95";

function Stepper({ step, onGo }: { step: number; onGo: (i: number) => void }) {
  return (
    <ol className="grid grid-cols-6 gap-1">
      {STEPS.map((s, i) => {
        const state = i < step ? "done" : i === step ? "now" : "next";
        return (
          <li key={s.short} className="relative">
            {i > 0 && (
              <span
                className="absolute right-1/2 top-[18px] h-0.5 w-full -translate-y-1/2"
                style={{ background: i <= step ? "linear-gradient(90deg, var(--brand-700), var(--brand-500))" : "var(--line)" }}
                aria-hidden
              />
            )}
            <button
              onClick={() => onGo(i)}
              className="relative z-10 mx-auto flex flex-col items-center gap-1"
              aria-current={state === "now" ? "step" : undefined}
              title={`Step ${i + 1}: ${s.title} (press to play it again)`}
            >
              <span
                className={`grid h-9 w-9 place-items-center rounded-xl border-2 font-mono text-sm font-bold transition ${state === "now" ? "scale-110 border-transparent bg-brand-gradient text-white shadow-[0_8px_20px_-8px_rgb(10_102_194/0.9)]" : state === "done" ? "border-brand-600 bg-white text-brand-700" : "border-line bg-white text-muted-foreground"}`}
              >
                {i + 1}
              </span>
              <span className={`text-center text-[11px] leading-tight ${state === "now" ? "font-semibold" : "text-muted-foreground"}`}>
                <span className="sm:hidden">{s.short}</span>
                <span className="hidden sm:inline">{s.title}</span>
              </span>
            </button>
          </li>
        );
      })}
    </ol>
  );
}

/** The answer, always in view below the steps, so a judge can jump around and still see where it lands. */
function ResultStrip({ t }: { t: Trace }) {
  return (
    <div className="panel flex flex-wrap items-center gap-x-4 gap-y-1 px-4 py-3 text-xs">
      <span className="text-muted-foreground">Where this work ends up:</span>
      <span className="rounded-full px-2.5 py-0.5 font-semibold text-white" style={{ background: BAND_COLOR[t.result.band] }}>
        {t.result.band}
      </span>
      <span>score {(t.result.score * 100).toFixed(0)}%</span>
      <span className="text-muted-foreground">{t.result.in_queue ? "in the review queue" : "not in the review queue"}</span>
      <span className="text-muted-foreground">
        {t.checks.filter((c) => c.status === "ASSESSED" && c.findings.some((f) => f.risk > 0) && c.counted).length} of{" "}
        {t.checks.length} checks raised a question
      </span>
    </div>
  );
}
