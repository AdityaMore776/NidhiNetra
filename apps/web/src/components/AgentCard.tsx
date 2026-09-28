import type { AgentResult } from "@/lib/api";
import { AGENTS } from "@/lib/format";
import { StatusLabel } from "./kit";
import { StatisticalEvidence } from "./StatisticalEvidence";

const STATUS: Record<
  AgentResult["status"],
  { label: string; tone: "high" | "medium" | "low" | "info" | "neutral" }
> = {
  ASSESSED: { label: "Assessed", tone: "neutral" },
  NOT_APPLICABLE: { label: "Not applicable", tone: "neutral" },
  NOT_ASSESSABLE: { label: "Could not assess", tone: "info" },
  NOT_BUILT: { label: "In development", tone: "neutral" },
  ERROR: { label: "Check did not run", tone: "info" },
};

/** Verdict shown for an assessed agent. Never a conclusion of wrongdoing. */
function verdictLabel(r: AgentResult): { label: string; tone: "high" | "medium" | "low" } {
  if (r.risk <= 0) return { label: "Pass", tone: "low" };
  if (r.hard || r.risk >= 0.6) return { label: "Flagged", tone: "high" };
  return { label: "Flagged", tone: "medium" };
}

export function AgentCard({ result }: { result: AgentResult }) {
  const meta = AGENTS[result.agent];
  const assessed = result.status === "ASSESSED";
  const status = STATUS[result.status];
  const verdict = assessed ? verdictLabel(result) : null;

  return (
    <section className={`flex flex-col border border-line bg-surface ${result.status === "NOT_BUILT" ? "opacity-70" : ""}`}>
      <header className="flex items-start gap-3 border-b border-line p-4">
        <span
          className="tnum mt-0.5 grid h-8 w-8 shrink-0 place-items-center border text-xs font-bold"
          style={{ borderColor: meta.color, color: meta.color }}
        >
          {meta.n}
        </span>
        <div className="min-w-0">
          <div className="text-sm font-semibold">{meta.name} Agent</div>
          <div className="text-xs text-muted">{meta.question}</div>
        </div>
        <div className="ml-auto flex shrink-0 flex-col items-end gap-1">
          {verdict ? (
            <StatusLabel tone={verdict.tone} solid>
              {verdict.label}
            </StatusLabel>
          ) : (
            <StatusLabel tone={status.tone}>{status.label}</StatusLabel>
          )}
          {assessed && (
            <span className="label text-[10px] text-muted">
              <span className="tnum">{result.risk > 0 ? `${Math.round(result.risk * 100)}/100` : "0/100"}</span> risk ·{" "}
              <span className="tnum">{Math.round(result.confidence * 100)}%</span> conf.
            </span>
          )}
        </div>
      </header>

      <div className="flex-1 space-y-4 p-4">
        <p className="text-sm">{result.headline}</p>

        {result.agent === "statistical" && assessed && <StatisticalEvidence result={result} />}

        {result.findings.length > 1 && (
          <ul className="space-y-1.5 text-sm">
            {result.findings.map((f) => (
              <li key={f.code} className="flex gap-2">
                <span
                  className="mt-1.5 h-2 w-2 shrink-0"
                  style={{ background: f.hard ? "var(--high)" : "var(--medium)" }}
                  aria-hidden
                />
                <span>{f.text}</span>
              </li>
            ))}
          </ul>
        )}

        {result.limitations.length > 0 && (
          <details className="border-t border-line pt-3 text-xs text-muted">
            <summary className="cursor-pointer font-semibold uppercase tracking-wider">
              What this check cannot tell ({result.limitations.length})
            </summary>
            <ul className="mt-2 list-disc space-y-1 pl-5">
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
