"use client";

import { useEffect, useState } from "react";
import { api, type Summary } from "@/lib/api";
import { AGENT_ORDER, agentMeta } from "@/lib/format";

const STEPS = [
  { n: 1, title: "Work enters DRISHTI", text: "Records, the agency's cost estimate form and monthly site videos come in.", color: "var(--inputs)" },
  { n: 2, title: "The checkers, in parallel", text: "Each independently checks for a different kind of problem.", color: "var(--navy)" },
  { n: 3, title: "Risk fusion", text: "Combine the checks into the chance a work is worth a look, using how often each kind of flag proved right when read by eye, with the top three reasons.", color: "var(--fusion)" },
  { n: 4, title: "Risk review", text: "Rank works Low, Medium, High or Critical, and queue High and Critical for a look.", color: "var(--medium)" },
  { n: 5, title: "Officer verification", text: "An officer reviews the evidence and makes the decision.", color: "var(--low)" },
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
