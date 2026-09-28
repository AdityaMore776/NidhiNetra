"use client";

import { useEffect, useState } from "react";
import { Panel, StatusLabel } from "@/components/kit";
import { api, type Summary } from "@/lib/api";
import { AGENTS, AGENT_ORDER } from "@/lib/format";

const STEPS = [
  { n: 1, title: "Work enters DRISHTI", text: "Records, progress claims and site photos come in." },
  { n: 2, title: "Data validation", text: "Clean and check the record: impossible dates, missing fields, guideline notes." },
  { n: 3, title: "Four agents, in parallel", text: "Each independently checks for a different kind of problem." },
  { n: 4, title: "Risk fusion", text: "Combine the checks by their strength and confidence into one score." },
  { n: 5, title: "Risk review", text: "Rank works Low, Medium or High, and queue the ones that need a look." },
  { n: 6, title: "Officer verification", text: "An officer reviews the evidence and makes the decision." },
];

const FACETS: Record<string, string[]> = {
  site_progress: [
    "The officer writes, in their own words, what changed since the last visit",
    "AI checks each claim against the photos: shown, not shown, or can't tell",
    "GPS and photo time checked against the work's location and the reporting period",
  ],
  image_reuse: [
    "Every photo gets a visual fingerprint",
    "Search all photos nationally, even resized or cropped copies",
    "Photo data checked for editing, old dates and a location elsewhere",
  ],
  duplicate_project: [
    "The work's location becomes a DIGIPIN code (India Post's address grid)",
    "Find works already recorded in the same small squares nearby",
    "Compare the records: same type, similar amount, money still in flight",
  ],
  statistical: [
    "Compare the cost with works of the same type in the same district",
    "Price per metre for roads, against published rates",
    "Spot bulk orders, delays and guideline ceilings",
  ],
};

export default function HowItWorks() {
  const [s, setS] = useState<Summary | null>(null);
  useEffect(() => {
    api<Summary>("/dashboard/summary").then(setS).catch(() => setS(null));
  }, []);
  const built = new Set(s?.agents.filter((a) => a.built).map((a) => a.id) ?? []);

  return (
    <div className="space-y-8">
      <header className="border-b-2 border-strong pb-4">
        <h1 className="text-2xl font-bold tracking-tight md:text-3xl">How DRISHTI works</h1>
        <p className="mt-1.5 max-w-3xl text-sm leading-relaxed text-muted">
          The six steps from the team&apos;s design, and where each agent stands today.
        </p>
      </header>

      {/* Pipeline */}
      <section>
        <div className="label mb-3">Pipeline</div>
        <ol className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
          {STEPS.map((st) => (
            <li key={st.n} className="relative border border-line bg-surface p-4">
              <span className="tnum grid h-8 w-8 place-items-center border-2 border-strong text-sm font-bold">
                {st.n}
              </span>
              <div className="mt-2.5 text-sm font-semibold">{st.title}</div>
              <p className="mt-1 text-xs leading-relaxed text-muted">{st.text}</p>
            </li>
          ))}
        </ol>
      </section>

      {/* Agents */}
      <section className="space-y-3">
        <div className="label">The four agents</div>
        <div className="grid gap-4 md:grid-cols-2">
          {AGENT_ORDER.map((id) => {
            const meta = AGENTS[id];
            return (
              <Panel key={id} as="section">
                <header className="flex items-center gap-3 border-b border-line p-4">
                  <span
                    className="tnum grid h-8 w-8 shrink-0 place-items-center border text-xs font-bold"
                    style={{ borderColor: meta.color, color: meta.color }}
                  >
                    {meta.n}
                  </span>
                  <div className="min-w-0">
                    <div className="text-sm font-semibold">{meta.name} Agent</div>
                    <div className="text-xs text-muted">{meta.question}</div>
                  </div>
                  <span className="ml-auto">
                    {built.has(id) ? (
                      <StatusLabel tone="low">Live</StatusLabel>
                    ) : (
                      <StatusLabel tone="neutral">In development</StatusLabel>
                    )}
                  </span>
                </header>
                <ol className="space-y-2.5 p-4 text-sm">
                  {FACETS[id].map((f, i) => (
                    <li key={f} className="flex gap-3">
                      <span
                        className="tnum grid h-5 w-5 shrink-0 place-items-center border text-[11px] font-bold"
                        style={{ borderColor: meta.color, color: meta.color }}
                      >
                        {String.fromCharCode(65 + i)}
                      </span>
                      <span>{f}</span>
                    </li>
                  ))}
                </ol>
              </Panel>
            );
          })}
        </div>
      </section>

      <p className="border-t border-line pt-4 text-xs text-muted">
        DRISHTI never says &quot;fraud&quot;. Every finding is phrased as something to verify, with the evidence and the
        rule behind it. An officer always decides.
      </p>
    </div>
  );
}
