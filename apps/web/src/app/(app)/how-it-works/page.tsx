"use client";

import { useEffect, useState } from "react";
import { api, type Summary } from "@/lib/api";
import { AGENT_ORDER, agentMeta } from "@/lib/format";

const STEPS = [
  { n: 1, title: "Work enters DRISHTI", text: "Records, progress claims and site photos come in.", color: "var(--inputs)" },
  { n: 2, title: "Seven checkers, in parallel", text: "Each independently checks for a different kind of problem.", color: "var(--navy)" },
  { n: 3, title: "Risk fusion", text: "Combine the checks into the chance a work is worth a look, using how often each kind of flag proved right when read by eye, with the top three reasons.", color: "var(--fusion)" },
  { n: 4, title: "Risk review", text: "Rank works Low, Medium, High or Critical, and queue High and Critical for a look.", color: "var(--medium)" },
  { n: 5, title: "Officer verification", text: "An officer reviews the evidence and makes the decision.", color: "var(--low)" },
];

const FACETS: Record<string, string[]> = {
  compliance: [
    "Each MPLADS guideline rule written as a check with its paragraph number",
    "Late sanctions, overdue works, impossible dates, missing key data, big sums that do not say what or where, buildings \"finished\" in days",
    "Works that may not be allowed under the guidelines are marked \"verify\"",
  ],
  statistical: [
    "Compare the cost with the same kind of work (a library building with library buildings, books with books)",
    "Price per metre for roads with a stated length, against published rates",
    "Undescribed or many-site sanctions are set aside, not scored as a mark-up",
  ],
  dup_split: [
    "Find works that describe the same asset again, even when reworded",
    "Find one job cut into several works just under a limit",
    "Every match says \"verify\": two works can be alike for good reasons",
  ],
  delay: [
    "Works recommended under a Lok Sabha term that has ended and still not sanctioned",
    "Offices holding far more unsanctioned recommendations than their district",
    "Counts from the record only: no forecasts",
  ],
  office_patterns: [
    "An office that prices most of its works just under the Rs 5 or 10 lakh limit",
    "An office that records constructions complete within a week of their sanction",
    "A habit of the office, never of an MP: it adds weight to a work's own findings",
  ],
  paperwork: [
    "Read the work's own utilisation certificates: sanction date, payments, status",
    "Sanctioned late or before the recommendation; papers of another work",
    "The vendor's share of the district's certified works, by vendor code (a fact)",
  ],
  photo_evidence: [
    "The same photo or paper attached to another work",
    "The photo's printed GPS stamp inside the work's own district",
    "A photo dated before the MP recommended the work",
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
        <p className="text-sm text-muted">The five steps from the team&apos;s design, and where each agent stands today.</p>
      </div>
      <ol className="grid md:grid-cols-3 lg:grid-cols-5 gap-3">
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
          const meta = agentMeta(id);
          return (
            <section key={id} className="card overflow-hidden">
              <header className="flex items-center gap-3 px-5 py-3" style={{ background: `color-mix(in srgb, ${meta.color} 14%, white)` }}>
                <span className="rounded-full w-8 h-8 grid place-items-center text-white text-xs font-bold" style={{ background: meta.color }}>
                  {meta.n}
                </span>
                <div>
                  <div className="font-semibold">{meta.name}</div>
                  <div className="text-xs text-muted">{meta.question}</div>
                </div>
                <span className={`ml-auto rounded-md px-2 py-1 text-[11px] font-medium ${built.has(id) ? "bg-low text-white" : "bg-background text-muted"}`}>
                  {built.has(id) ? "Live" : "In development"}
                </span>
              </header>
              <ol className="px-5 py-4 space-y-2 text-sm">
                {(FACETS[id] ?? []).map((f, i) => (
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
