"use client";

import { Languages } from "lucide-react";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { useState } from "react";
import type { WorkDetail } from "@/lib/api";
import { AGENTS, BAND_COLOR } from "@/lib/format";
import { BandBadge } from "./nn/badges";

const SOURCE_COLOR: Record<string, string> = {
  ...Object.fromEntries(Object.entries(AGENTS).map(([k, v]) => [k, v.color])),
  validation: "var(--brand-600)",
  floor: "var(--critical)",
};

/** The score as a gauge: an arc that draws itself to the score, in the band's colour. */
export function ScoreGauge({ score, band, size = 168 }: { score: number; band: WorkDetail["assessment"]["band"]; size?: number }) {
  const reduce = useReducedMotion();
  const v = Math.max(0, Math.min(1, score));
  const r = 70;
  const c = Math.PI * r; // half circle
  return (
    <div className="relative" style={{ width: size, height: size * 0.62 }}>
      <svg viewBox="0 0 180 104" className="size-full overflow-visible">
        <defs>
          <linearGradient id="gauge-track" x1="0" x2="1">
            <stop offset="0" stopColor="#eef3fa" />
            <stop offset="1" stopColor="#e3ebf6" />
          </linearGradient>
        </defs>
        <path d="M 20 92 A 70 70 0 0 1 160 92" fill="none" stroke="url(#gauge-track)" strokeWidth="14" strokeLinecap="round" />
        <motion.path
          d="M 20 92 A 70 70 0 0 1 160 92"
          fill="none"
          stroke={BAND_COLOR[band]}
          strokeWidth="14"
          strokeLinecap="round"
          strokeDasharray={c}
          initial={{ strokeDashoffset: reduce ? c * (1 - v) : c }}
          animate={{ strokeDashoffset: c * (1 - v) }}
          transition={{ duration: 1.4, ease: [0.16, 1, 0.3, 1], delay: 0.15 }}
        />
      </svg>
      <div className="absolute inset-x-0 bottom-0 text-center">
        <div className="num text-[2.6rem] font-semibold leading-none tracking-[-0.05em] text-brand-950">{Math.round(v * 100)}</div>
        <div className="mt-1 text-[11px] text-muted-foreground">risk score / 100</div>
      </div>
    </div>
  );
}

/** How the checks combine. The parts add up exactly to the score. */
export function FusionPanel({ a }: { a: WorkDetail["assessment"] }) {
  const parts = a.parts.parts ?? [];
  const reasons = a.parts.reasons ?? [];
  const [hindi, setHindi] = useState(false);
  const reduce = useReducedMotion();

  return (
    <section className="panel overflow-hidden">
      <div className="grid gap-6 p-5 sm:p-6 lg:grid-cols-[220px_1fr]">
        <div className="flex flex-col items-center justify-center gap-3 rounded-2xl bg-gradient-to-b from-brand-50 to-white p-4 ring-1 ring-border">
          <ScoreGauge score={a.score} band={a.band} />
          <BandBadge band={a.band} limited={a.limited} size="lg" />
        </div>

        <div className="min-w-0 space-y-5">
          <div className="flex items-start gap-3">
            <div className="min-w-0">
              <div className="eyebrow">Risk fusion</div>
              <h2 className="mt-1 text-lg font-semibold tracking-[-0.02em] text-brand-950">Why this work is ranked here</h2>
              <p className="mt-1 text-[13px] leading-relaxed text-muted-foreground">
                The chance this work is worth a look, from how often each kind of flag proved worth a look when read by eye. The parts add up
                to the score.
              </p>
            </div>
            {reasons.length > 0 && (
              <button
                type="button"
                onClick={() => setHindi((h) => !h)}
                className="ml-auto inline-flex shrink-0 items-center gap-1.5 rounded-lg border bg-white px-2.5 py-1.5 text-xs font-medium text-brand-900 transition-colors hover:border-brand-200 hover:bg-brand-50"
              >
                <Languages className="size-3.5" />
                <span className={hindi ? "" : "font-devanagari"}>{hindi ? "English" : "हिंदी"}</span>
              </button>
            )}
          </div>

          {parts.length > 0 ? (
            <div className="space-y-2.5">
              <div className="flex h-3.5 w-full gap-[2px] overflow-hidden rounded-full bg-muted">
                {parts.map((p, i) => (
                  <motion.div
                    key={p.source}
                    title={`${p.label}: +${Math.round(p.contribution * 100)}`}
                    className="h-full first:rounded-l-full last:rounded-r-full"
                    style={{ background: SOURCE_COLOR[p.source] ?? "var(--muted-foreground)" }}
                    initial={reduce ? false : { width: 0 }}
                    animate={{ width: `${p.contribution * 100}%` }}
                    transition={{ duration: 0.9, delay: 0.3 + i * 0.12, ease: [0.22, 1, 0.36, 1] }}
                  />
                ))}
              </div>
              <ul className="grid gap-x-6 gap-y-1.5 text-xs sm:grid-cols-2">
                {parts.map((p) => (
                  <li key={p.source} className="flex items-center gap-2">
                    <span className="size-2.5 rounded-sm" style={{ background: SOURCE_COLOR[p.source] ?? "var(--muted-foreground)" }} />
                    <span className="truncate">{p.label}</span>
                    <span className="num ml-auto font-semibold text-foreground">+{Math.round(p.contribution * 100)}</span>
                  </li>
                ))}
              </ul>
            </div>
          ) : (
            <p className="rounded-xl bg-muted/70 p-3 text-sm text-muted-foreground">No check found anything to weigh.</p>
          )}

          {reasons.length > 0 && (
            <div>
              <div className={`mb-2 text-sm font-semibold text-brand-950 ${hindi ? "font-devanagari" : ""}`}>{hindi ? "मुख्य कारण" : "Top reasons"}</div>
              <AnimatePresence mode="wait" initial={false}>
                <motion.ol
                  key={hindi ? "hi" : "en"}
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -6 }}
                  transition={{ duration: 0.25 }}
                  className="space-y-2.5"
                >
                  {reasons.map((r, i) => (
                    <li key={r.source} className="flex gap-3 rounded-xl border bg-white p-3 text-sm">
                      <span
                        className="num grid size-6 shrink-0 place-items-center rounded-lg text-[11px] font-bold text-white"
                        style={{ background: SOURCE_COLOR[r.source] ?? "var(--muted-foreground)" }}
                      >
                        {i + 1}
                      </span>
                      <span className={hindi ? "font-devanagari leading-relaxed" : "leading-relaxed"}>
                        <span className="font-semibold text-brand-950">{r.label}: </span>
                        {hindi ? r.text_hi : r.text_en}
                        {!hindi && r.basis === "measured" && r.read ? (
                          <span className="mt-1 block text-xs text-muted-foreground">
                            Flags like this read worth a look {r.read[0]} times in {r.read[1]}.
                          </span>
                        ) : null}
                        {!hindi && r.basis === "prior" ? (
                          <span className="mt-1 block text-xs text-muted-foreground">Not yet read by eye: counts as 1 in 4 until it is.</span>
                        ) : null}
                      </span>
                    </li>
                  ))}
                </motion.ol>
              </AnimatePresence>
            </div>
          )}

          {a.limited && a.band === "LOW" && (
            <p className="rounded-xl border border-dashed p-3 text-xs text-muted-foreground">
              Limited evidence: at least one check could not look at this work, so a low score here is not a clean chit.
            </p>
          )}
        </div>
      </div>
    </section>
  );
}
