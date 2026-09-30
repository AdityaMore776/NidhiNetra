"use client";

import { useState } from "react";
import type { WorkDetail } from "@/lib/api";
import { AGENTS, BAND_COLOR } from "@/lib/format";
import { BandBadge } from "./ui";

const SOURCE_COLOR: Record<string, string> = {
  ...Object.fromEntries(Object.entries(AGENTS).map(([k, v]) => [k, v.color])),
  validation: "var(--inputs)",
  floor: "var(--critical)",
};

/** Step 4 of the deck: how the checks combine. The parts add up exactly to the score. */
export function FusionPanel({ a }: { a: WorkDetail["assessment"] }) {
  const parts = a.parts.parts ?? [];
  const reasons = a.parts.reasons ?? [];
  const [hindi, setHindi] = useState(false);
  return (
    <section className="card p-5 space-y-4">
      <div className="flex items-center gap-3">
        <span className="rounded-full w-8 h-8 grid place-items-center text-white text-xs font-bold" style={{ background: "var(--fusion)" }}>
          RF
        </span>
        <div>
          <div className="font-semibold">Risk score</div>
          <div className="text-xs text-muted">Each check adds its signal times its fixed weight; the parts add up to the score</div>
        </div>
        <div className="ml-auto text-right">
          <div className="text-2xl font-bold" style={{ color: BAND_COLOR[a.band] }}>
            {Math.round(a.score * 100)}
            <span className="text-sm text-muted font-normal"> / 100</span>
          </div>
          <BandBadge band={a.band} limited={a.limited} />
        </div>
      </div>
      {reasons.length > 0 && (
        <div className="space-y-2">
          <div className="flex items-center">
            <div className="text-sm font-semibold">{hindi ? "मुख्य कारण" : "Top reasons"}</div>
            <button
              type="button"
              onClick={() => setHindi((h) => !h)}
              className="ml-auto rounded-md border border-line px-2 py-0.5 text-xs text-muted hover:text-foreground"
            >
              {hindi ? "English" : "हिंदी"}
            </button>
          </div>
          <ol className="space-y-2 text-sm">
            {reasons.map((r, i) => (
              <li key={r.source} className="flex gap-2">
                <span
                  className="mt-0.5 h-5 w-5 shrink-0 rounded-full grid place-items-center text-[11px] font-bold text-white"
                  style={{ background: SOURCE_COLOR[r.source] ?? "var(--muted)" }}
                >
                  {i + 1}
                </span>
                <span>
                  <span className="font-medium">{r.label}: </span>
                  {hindi ? r.text_hi : r.text_en}
                </span>
              </li>
            ))}
          </ol>
        </div>
      )}
      {parts.length > 0 ? (
        <div className="space-y-2">
          <div className="flex h-3 w-full overflow-hidden rounded-full bg-line">
            {parts.map((p) => (
              <div key={p.source} style={{ width: `${p.contribution * 100}%`, background: SOURCE_COLOR[p.source] }} title={p.label} />
            ))}
          </div>
          <ul className="grid sm:grid-cols-2 gap-x-6 gap-y-1 text-xs">
            {parts.map((p) => (
              <li key={p.source} className="flex items-center gap-2">
                <span className="h-2.5 w-2.5 rounded-sm" style={{ background: SOURCE_COLOR[p.source] }} />
                <span>{p.label}</span>
                <span className="ml-auto text-muted">+{Math.round(p.contribution * 100)}</span>
              </li>
            ))}
          </ul>
        </div>
      ) : (
        <p className="text-sm text-muted">No check found anything to weigh.</p>
      )}
      {a.limited && a.band === "LOW" && (
        <p className="text-xs text-muted">
          Limited evidence: at least one check could not look at this work, so a low score here is not a clean chit.
        </p>
      )}
    </section>
  );
}
