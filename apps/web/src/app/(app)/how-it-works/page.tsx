"use client";

import { useEffect, useState } from "react";
import { api, type Summary } from "@/lib/api";
import { AGENTS, AGENT_ORDER } from "@/lib/format";

const STEPS = [
  { n: 1, title: "Work enters DRISHTI", text: "Records, progress claims and site photos come in.", color: "var(--inputs)" },
  { n: 2, title: "Data validation", text: "Clean and check the record: impossible dates, missing fields, guideline notes.", color: "var(--inputs)" },
  { n: 3, title: "Four agents, in parallel", text: "Each independently checks for a different kind of problem.", color: "var(--navy)" },
  { n: 4, title: "Risk fusion", text: "Combine the checks by their strength and confidence into one score.", color: "var(--fusion)" },
  { n: 5, title: "Risk review", text: "Rank works Low, Medium or High, and queue the ones that need a look.", color: "var(--medium)" },
  { n: 6, title: "Officer verification", text: "An officer reviews the evidence and makes the decision.", color: "var(--low)" },
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
    api<Summary>("/dashboard/summary").then(setS);
  }, []);
  const built = new Set(s?.agents.filter((a) => a.built).map((a) => a.id) ?? []);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">How DRISHTI works</h1>
        <p className="text-sm text-muted">The six steps from the team&apos;s design, and where each agent stands today.</p>
      </div>
      <ol className="grid md:grid-cols-3 lg:grid-cols-6 gap-3">
        {STEPS.map((st) => (
          <li key={st.n} className="card p-4">
            <span className="rounded-full w-7 h-7 grid place-items-center text-white text-xs font-bold" style={{ background: st.color }}>
              {st.n}
            </span>
            <div className="mt-2 font-semibold text-sm">{st.title}</div>
            <p className="mt-1 text-xs text-muted">{st.text}</p>
          </li>
        ))}
      </ol>
      <div className="grid md:grid-cols-2 gap-4">
        {AGENT_ORDER.map((id) => {
          const meta = AGENTS[id];
          return (
            <section key={id} className="card overflow-hidden">
              <header className="flex items-center gap-3 px-5 py-3" style={{ background: `color-mix(in srgb, ${meta.color} 14%, white)` }}>
                <span className="rounded-full w-8 h-8 grid place-items-center text-white text-xs font-bold" style={{ background: meta.color }}>
                  {meta.n}
                </span>
                <div>
                  <div className="font-semibold">{meta.name} Agent</div>
                  <div className="text-xs text-muted">{meta.question}</div>
                </div>
                <span className={`ml-auto rounded-md px-2 py-1 text-[11px] font-medium ${built.has(id) ? "bg-low text-white" : "bg-background text-muted"}`}>
                  {built.has(id) ? "Live" : "In development"}
                </span>
              </header>
              <ol className="px-5 py-4 space-y-2 text-sm">
                {FACETS[id].map((f, i) => (
                  <li key={f} className="flex gap-2">
                    <span className="font-bold" style={{ color: meta.color }}>
                      {String.fromCharCode(65 + i)}
                    </span>
                    <span>{f}</span>
                  </li>
                ))}
              </ol>
            </section>
          );
        })}
      </div>
    </div>
  );
}
