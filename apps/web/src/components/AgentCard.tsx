import type { AgentResult } from "@/lib/api";
import { AGENTS } from "@/lib/format";
import { StatisticalEvidence } from "./StatisticalEvidence";

const STATUS_NOTE: Record<AgentResult["status"], string> = {
  ASSESSED: "",
  NOT_APPLICABLE: "Not applicable yet",
  NOT_ASSESSABLE: "Could not be assessed",
  NOT_BUILT: "In development",
  ERROR: "Check did not run",
};

export function AgentCard({ result }: { result: AgentResult }) {
  const meta = AGENTS[result.agent];
  const quiet = result.status !== "ASSESSED";
  return (
    <section className={`card overflow-hidden ${result.status === "NOT_BUILT" ? "opacity-70" : ""}`}>
      <header className="flex items-center gap-3 px-5 py-3 border-b border-line" style={{ background: `color-mix(in srgb, ${meta.color} 12%, white)` }}>
        <span className="rounded-full w-8 h-8 grid place-items-center text-white text-xs font-bold" style={{ background: meta.color }}>
          {meta.n}
        </span>
        <div>
          <div className="font-semibold">{meta.name} Agent</div>
          <div className="text-xs text-muted">{meta.question}</div>
        </div>
        <div className="ml-auto text-right">
          {quiet ? (
            <span className="text-xs text-muted">{STATUS_NOTE[result.status]}</span>
          ) : (
            <>
              <div className="text-xs text-muted">Risk from this check</div>
              <div className="font-semibold" style={{ color: result.risk > 0 ? meta.color : "var(--low)" }}>
                {result.risk > 0 ? `${Math.round(result.risk * 100)} / 100` : "None found"}
              </div>
            </>
          )}
        </div>
      </header>
      <div className="px-5 py-4 space-y-4">
        <p className="text-sm">{result.headline}</p>
        {result.agent === "statistical" && result.status === "ASSESSED" && <StatisticalEvidence result={result} />}
        {result.findings.length > 1 && (
          <ul className="space-y-1.5 text-sm">
            {result.findings.map((f) => (
              <li key={f.code} className="flex gap-2">
                <span className="mt-1.5 h-2 w-2 shrink-0 rounded-full" style={{ background: f.hard ? "var(--high)" : "var(--medium)" }} />
                <span>{f.text}</span>
              </li>
            ))}
          </ul>
        )}
        {result.limitations.length > 0 && (
          <details className="text-xs text-muted">
            <summary className="cursor-pointer">What this check cannot tell ({result.limitations.length})</summary>
            <ul className="mt-2 list-disc pl-5 space-y-1">
              {result.limitations.map((l) => (
                <li key={l}>{l}</li>
              ))}
            </ul>
          </details>
        )}
      </div>
    </section>
  );
}
