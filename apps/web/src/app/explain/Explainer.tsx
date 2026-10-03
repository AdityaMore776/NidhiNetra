"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { Logo } from "@/components/Logo";
import { api, apiPost, ApiError, type PreOptions } from "@/lib/api";
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
    title: "The work goes in",
    short: "Input",
    what: "A work record arrives from the eSAKSHI portal: what it is, what it says, how much, where, which office, and its dates.",
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
    what: "DRISHTI reads the words like an officer would: which name a place, a size, a construction or a purchase, and whether any is on the guidelines' not-allowed list. Each fact it finds lights up.",
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

const OWN = "own";

export default function Explainer() {
  const [file, setFile] = useState<ExamplesFile | null>(null);
  const [loadError, setLoadError] = useState(false);
  const [pick, setPick] = useState("two");
  const [own, setOwn] = useState<Trace | null>(null);
  const [step, setStep] = useState(0);
  const [run, setRun] = useState(0);
  const [playing, setPlaying] = useState(false);

  useEffect(() => {
    let live = true;
    fetch("/explain/examples.json")
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(String(r.status)))))
      .then((f: ExamplesFile) => live && setFile(f))
      .catch(() => live && setLoadError(true));
    return () => {
      live = false;
    };
  }, []);

  const example = file?.examples.find((e) => e.id === pick) ?? null;
  const trace = pick === OWN ? own : (example?.trace ?? null);

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
    setPlaying(id !== OWN || own !== null);
  }

  function playAll() {
    setStep(0);
    setRun((r) => r + 1);
    setPlaying(true);
  }

  function ranOwn(t: Trace) {
    setOwn(t);
    setStep(0);
    setRun((r) => r + 1);
    setPlaying(true);
  }

  const S = STEPS[step];

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-20 border-b border-line bg-surface">
        <div className="mx-auto flex h-14 max-w-6xl items-center gap-4 px-4">
          <Link href="/explain">
            <Logo compact />
          </Link>
          <span className="hidden text-sm font-semibold text-muted sm:inline">Visualization Engine</span>
          <nav className="ml-auto flex items-center gap-2 text-sm">
            <Link href="/" className="rounded-lg border border-line px-3 py-1.5 hover:bg-background">
              Open DRISHTI
            </Link>
          </nav>
        </div>
      </header>

      <main className="mx-auto max-w-6xl space-y-5 px-4 py-6">
        <section className="space-y-2">
          <h1 className="text-2xl font-bold sm:text-3xl">What DRISHTI does with one work, step by step</h1>
          <p className="max-w-3xl text-sm text-muted sm:text-base">
            Pick an example, or type your own, and watch it go through the same six steps as every one of the 2,09,993
            MPLADS works on the live site. Press any step to see it again. Every number on this page comes from the real
            engines.
          </p>
        </section>

        <section aria-label="Examples" className="flex flex-wrap gap-2">
          {(file?.examples ?? []).map((e) => (
            <button
              key={e.id}
              onClick={() => choose(e.id)}
              className={`rounded-full border px-2.5 py-1 text-xs sm:px-3 sm:py-1.5 sm:text-sm ${pick === e.id ? "border-navy bg-navy text-white" : "border-line bg-surface hover:bg-background"}`}
            >
              {e.title}
            </button>
          ))}
          <button
            onClick={() => choose(OWN)}
            className={`rounded-full border border-dashed px-2.5 py-1 text-xs sm:px-3 sm:py-1.5 sm:text-sm ${pick === OWN ? "border-navy bg-navy text-white" : "border-navy text-navy hover:bg-background"}`}
          >
            + Your own example
          </button>
        </section>

        {loadError && <p className="text-sm text-high">The examples could not be loaded. Please reload the page.</p>}
        {!file && !loadError && <p className="text-sm text-muted">Loading the examples…</p>}

        {pick === OWN && <OwnExample onTrace={ranOwn} />}
        {example && pick !== OWN && (
          <p className="text-sm">
            <span className="font-semibold">{example.title}.</span> {example.story}
          </p>
        )}

        {trace && (
          <>
            <Stepper step={step} onGo={go} />
            <div className="flex flex-wrap items-center gap-2">
              <button onClick={() => go(step - 1)} disabled={step === 0} className="rounded-lg border border-line px-3 py-1.5 text-sm disabled:opacity-40">
                ← Back
              </button>
              {playing ? (
                <button onClick={() => setPlaying(false)} className="rounded-lg bg-navy px-4 py-1.5 text-sm font-semibold text-white">
                  ❚❚ Pause
                </button>
              ) : (
                <button onClick={playAll} className="rounded-lg bg-navy px-4 py-1.5 text-sm font-semibold text-white">
                  ▶ Play all six steps
                </button>
              )}
              <button onClick={() => go(step)} className="rounded-lg border border-line px-3 py-1.5 text-sm">
                ↻ Replay this step
              </button>
              <button
                onClick={() => go(step + 1)}
                disabled={step === STEPS.length - 1}
                className="rounded-lg border border-line px-3 py-1.5 text-sm disabled:opacity-40"
              >
                Next →
              </button>
              <span className="ml-auto hidden text-xs text-muted sm:inline">Keys: ← →</span>
            </div>

            <section className="card overflow-hidden">
              <div className="h-1 bg-background">
                {playing && (
                  <div key={`${pick}-${step}-${run}`} className="x-progress h-full bg-inputs" style={{ "--dur": `${S.ms(trace)}ms` } as React.CSSProperties} />
                )}
              </div>
              <div className="space-y-4 p-4 sm:p-6">
                <div>
                  <div className="text-xs font-semibold uppercase tracking-wide text-muted">
                    Step {step + 1} of {STEPS.length}
                  </div>
                  <h2 className="text-xl font-bold">{S.title}</h2>
                  <p className="mt-1 max-w-3xl text-sm text-muted">{S.what}</p>
                </div>
                <div key={`${pick}-${step}-${run}`} className="x-stage">
                  <S.View t={trace} />
                </div>
              </div>
            </section>

            <ResultStrip t={trace} />
          </>
        )}

        <footer className="space-y-1 pb-8 pt-2 text-[11px] text-muted">
          {pick !== OWN && file && (
            <p>
              Built-in examples: made-up works placed in a real district and checked by the real engines against the {file.source}.
              The other works shown are real, with private names hidden.
            </p>
          )}
          <p>
            DRISHTI flags works that need verification. It never decides; officers do. SIH 2026 · SIH26102 · Team NeuralNexus.
          </p>
        </footer>
      </main>
    </div>
  );
}

function Stepper({ step, onGo }: { step: number; onGo: (i: number) => void }) {
  return (
    <ol className="grid grid-cols-6 gap-1">
      {STEPS.map((s, i) => {
        const state = i < step ? "done" : i === step ? "now" : "next";
        return (
          <li key={s.short} className="relative">
            {i > 0 && (
              <span
                className="absolute right-1/2 top-4 h-0.5 w-full -translate-y-1/2"
                style={{ background: i <= step ? "var(--navy)" : "var(--line)" }}
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
                className={`grid h-8 w-8 place-items-center rounded-full border-2 text-sm font-bold transition ${state === "now" ? "scale-110 border-navy bg-navy text-white shadow" : state === "done" ? "border-navy bg-surface text-navy" : "border-line bg-surface text-muted"}`}
              >
                {i + 1}
              </span>
              <span className={`text-center text-[11px] leading-tight ${state === "now" ? "font-semibold" : "text-muted"}`}>
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
    <div className="flex flex-wrap items-center gap-x-4 gap-y-1 rounded-xl border border-line bg-surface px-4 py-2 text-xs">
      <span className="text-muted">Where this work ends up:</span>
      <span className="rounded-full px-2.5 py-0.5 font-semibold text-white" style={{ background: BAND_COLOR[t.result.band] }}>
        {t.result.band}
      </span>
      <span>score {(t.result.score * 100).toFixed(0)}%</span>
      <span className="text-muted">{t.result.in_queue ? "in the review queue" : "not in the review queue"}</span>
      <span className="text-muted">
        {t.checks.filter((c) => c.status === "ASSESSED" && c.findings.some((f) => f.risk > 0) && c.counted).length} of{" "}
        {t.checks.length} checks raised a question
      </span>
    </div>
  );
}

// ---- your own example: the live engine, behind the demo sign-in -----------------------------

function OwnExample({ onTrace }: { onTrace: (t: Trace) => void }) {
  const [opts, setOpts] = useState<PreOptions | null>(null);
  const [gate, setGate] = useState<"loading" | "open" | "signin" | "error">("loading");
  const [district, setDistrict] = useState("");
  const [workType, setWorkType] = useState("");
  const [description, setDescription] = useState("");
  const [amount, setAmount] = useState("");
  const [status, setStatus] = useState("RECOMMENDED");
  const [rec, setRec] = useState("");
  const [sanc, setSanc] = useState("");
  const [done, setDone] = useState("");
  const [outside, setOutside] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let live = true;
    api<PreOptions>("/presanction/options")
      .then((o) => {
        if (!live) return;
        setOpts(o);
        setGate("open");
        if (o.districts.length === 1) setDistrict(o.districts[0].district_lgd);
      })
      .catch((e) => live && setGate(e instanceof ApiError && (e.status === 401 || e.status === 403) ? "signin" : "error"));
    return () => {
      live = false;
    };
  }, []);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const t = await apiPost<Trace>("/explain", {
        district_lgd: district,
        work_type_code: workType || null,
        description,
        amount: Number(amount) * 100_000,
        is_outside_constituency: outside,
        status,
        recommended_date: rec || null,
        sanction_date: status !== "RECOMMENDED" ? sanc || null : null,
        completed_date: status === "COMPLETED" ? done || null : null,
      });
      onTrace(t);
    } catch (err) {
      setError(err instanceof Error ? err.message : "The engine could not run this example.");
    } finally {
      setBusy(false);
    }
  }

  if (gate === "loading") return <p className="text-sm text-muted">Connecting to the live engine…</p>;
  if (gate === "signin" || gate === "error")
    return (
      <div className="rounded-xl border border-dashed border-navy bg-surface p-4 text-sm">
        <p className="font-semibold">Your own example runs on the live engine, so it needs the demo sign-in.</p>
        <p className="mt-1 text-muted">
          {gate === "signin"
            ? "Sign in with the demo account, then come back to this page. The seven examples above work without signing in."
            : "The live engine did not answer just now. The seven examples above still work."}
        </p>
        <Link href="/login" className="mt-3 inline-block rounded-lg bg-navy px-4 py-2 font-semibold text-white">
          Sign in
        </Link>
      </div>
    );

  const field = "w-full rounded-lg border border-line bg-surface px-3 py-2 text-sm";
  return (
    <form onSubmit={submit} className="space-y-3 rounded-xl border border-line bg-surface p-4">
      <p className="text-sm text-muted">
        Type a work as it would appear on eSAKSHI. It is checked against the real works of the district you choose.
        Nothing you type is saved.
      </p>
      <div className="grid gap-3 sm:grid-cols-2">
        <label className="space-y-1">
          <span className="text-sm font-medium">District</span>
          <select className={field} value={district} onChange={(e) => setDistrict(e.target.value)} required>
            <option value="">Choose a district</option>
            {opts?.districts.map((d) => (
              <option key={d.district_lgd} value={d.district_lgd}>
                {d.name}, {d.state_name}
              </option>
            ))}
          </select>
        </label>
        <label className="space-y-1">
          <span className="text-sm font-medium">Kind of work</span>
          <select className={field} value={workType} onChange={(e) => setWorkType(e.target.value)}>
            <option value="">Not sure (some checks then cannot run)</option>
            {opts?.work_types.map((w) => (
              <option key={w.code} value={w.code}>
                {w.name}
              </option>
            ))}
          </select>
        </label>
      </div>
      <label className="block space-y-1">
        <span className="text-sm font-medium">Description</span>
        <textarea
          className={field}
          rows={2}
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="e.g. Construction of CC road 300 mtr from the school to the panchayat office in village Sundarpur"
          required
          minLength={3}
          maxLength={2000}
        />
      </label>
      <div className="flex flex-wrap items-end gap-3">
        <label className="space-y-1">
          <span className="text-sm font-medium">Amount (Rs lakh)</span>
          <input className={`${field} w-32`} type="number" min="0.01" step="0.01" value={amount} onChange={(e) => setAmount(e.target.value)} required />
        </label>
        <label className="space-y-1">
          <span className="text-sm font-medium">Stage</span>
          <select className={field} value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="RECOMMENDED">Recommended</option>
            <option value="SANCTIONED">Sanctioned</option>
            <option value="COMPLETED">Completed</option>
          </select>
        </label>
        <label className="space-y-1">
          <span className="text-sm font-medium">Recommended on</span>
          <input className={field} type="date" value={rec} onChange={(e) => setRec(e.target.value)} />
        </label>
        {status !== "RECOMMENDED" && (
          <label className="space-y-1">
            <span className="text-sm font-medium">Sanctioned on</span>
            <input className={field} type="date" value={sanc} onChange={(e) => setSanc(e.target.value)} />
          </label>
        )}
        {status === "COMPLETED" && (
          <label className="space-y-1">
            <span className="text-sm font-medium">Completed on</span>
            <input className={field} type="date" value={done} onChange={(e) => setDone(e.target.value)} />
          </label>
        )}
        <label className="flex items-center gap-2 pb-2 text-sm">
          <input type="checkbox" checked={outside} onChange={(e) => setOutside(e.target.checked)} />
          Outside the MP&apos;s constituency
        </label>
      </div>
      <div className="flex items-center gap-3">
        <button type="submit" disabled={busy || !district} className="rounded-lg bg-navy px-4 py-2 text-sm font-semibold text-white disabled:opacity-50">
          {busy ? "Running…" : "Run it through DRISHTI"}
        </button>
        <span className="text-xs text-muted">Left empty, the recommended date is today.</span>
      </div>
      {error && <p className="text-sm" style={{ color: "var(--critical)" }}>{error}</p>}
    </form>
  );
}
