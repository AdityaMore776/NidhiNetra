import type { WorkDetail } from "@/lib/api";
import { AGENTS, BAND_COLOR } from "@/lib/format";
import { BandBadge } from "./ui";

const SOURCE_COLOR: Record<string, string> = {
  ...Object.fromEntries(Object.entries(AGENTS).map(([k, v]) => [k, v.color])),
  validation: "var(--inputs)",
};

/** Step 4 of the deck: how the checks combine. The parts add up exactly to the score. */
export function FusionPanel({ a }: { a: WorkDetail["assessment"] }) {
  const parts = a.parts.parts ?? [];
  return (
    <section className="card p-5 space-y-4">
      <div className="flex items-center gap-3">
        <span className="rounded-full w-8 h-8 grid place-items-center text-white text-xs font-bold" style={{ background: "var(--fusion)" }}>
          RF
        </span>
        <div>
          <div className="font-semibold">Risk Fusion</div>
          <div className="text-xs text-muted">Combines every check by its strength and confidence</div>
        </div>
        <div className="ml-auto text-right">
          <div className="text-2xl font-bold" style={{ color: BAND_COLOR[a.band] }}>
            {Math.round(a.score * 100)}
            <span className="text-sm text-muted font-normal"> / 100</span>
          </div>
          <BandBadge band={a.band} limited={a.limited} />
        </div>
      </div>
      {parts.length > 0 ? (
        <div className="space-y-2">
          <div className="flex h-3 w-full overflow-hidden rounded-full bg-line">
            {parts.map((p) => (
              <div key={p.source} style={{ width: `${p.contribution * 100}%`, background: SOURCE_COLOR[p.source] }} title={p.label} />
            ))}
          </div>
          <ul className="grid sm:grid-cols-2 gap-x-6 gap-y-1 text-xs">
            {parts.map((p, i) => (
              <li key={p.source} className="flex items-center gap-2">
                <span className="h-2.5 w-2.5 rounded-sm" style={{ background: SOURCE_COLOR[p.source] }} />
                <span>{p.label}</span>
                <span className="ml-auto text-muted">
                  +{Math.round(p.contribution * 100)} {i > 0 && "(corroborating)"}
                </span>
              </li>
            ))}
          </ul>
        </div>
      ) : (
        <p className="text-sm text-muted">No check found anything to weigh.</p>
      )}
      {a.limited && a.band === "LOW" && (
        <p className="text-xs text-muted">
          Limited evidence: two or more checks could not look at this work yet, so a low score here is not a clean chit.
        </p>
      )}
    </section>
  );
}
