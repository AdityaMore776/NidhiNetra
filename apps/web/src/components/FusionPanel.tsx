import type { AgentResult, WorkDetail } from "@/lib/api";
import { AGENTS } from "@/lib/format";
import { Panel, PanelHeader } from "./kit";

const SOURCE_COLOR: Record<string, string> = {
  ...Object.fromEntries(Object.entries(AGENTS).map(([k, v]) => [k, v.color])),
  validation: "var(--info)",
};

/**
 * Risk Fusion attribution. The parts add up exactly to the score, so an officer
 * can see why a work sits where it does. `confidence` is shown from the matching
 * agent result where available; reliability is a fixed prior and is not shown as
 * a per-work figure it is not.
 */
export function FusionPanel({ a }: { a: WorkDetail["assessment"] }) {
  const parts = (a.parts.parts ?? []).filter((p) => p.weight > 0);
  const agentById = new Map<string, AgentResult>(a.agents.map((r) => [r.agent, r]));

  return (
    <Panel as="section">
      <PanelHeader
        title="Risk breakdown"
        desc="How the fusion engine combined each check into the final score"
      />
      <div className="space-y-4 p-4">
        {parts.length > 0 ? (
          <>
            {/* Stacked contribution bar */}
            <div>
              <div className="flex h-4 w-full overflow-hidden border border-line">
                {parts.map((p) => (
                  <div
                    key={p.source}
                    style={{ width: `${p.contribution * 100}%`, background: SOURCE_COLOR[p.source] ?? "var(--muted)" }}
                    title={`${p.label}: +${Math.round(p.contribution * 100)}`}
                  />
                ))}
              </div>
              <div className="mt-1 flex justify-between text-[11px] text-muted">
                <span>Contribution to the 0–100 score</span>
                <span className="tnum font-semibold text-foreground">= {Math.round(a.score * 100)}</span>
              </div>
            </div>

            {/* Attribution table */}
            <div className="scroll-thin overflow-x-auto border border-line">
              <table className="w-full text-sm">
                <thead className="bg-surface-2">
                  <tr className="border-b-2 border-strong">
                    <th className="label px-3 py-2 text-left">Check</th>
                    <th className="label px-3 py-2 text-right">Weight</th>
                    <th className="label px-3 py-2 text-right">Confidence</th>
                    <th className="label px-3 py-2 text-right">Contribution</th>
                  </tr>
                </thead>
                <tbody>
                  {parts.map((p, i) => {
                    const agent = agentById.get(p.source);
                    return (
                      <tr key={p.source} className="border-b border-line last:border-0">
                        <td className="px-3 py-2">
                          <span className="flex items-center gap-2">
                            <span
                              className="inline-block h-2.5 w-2.5"
                              style={{ background: SOURCE_COLOR[p.source] ?? "var(--muted)" }}
                              aria-hidden
                            />
                            {p.label}
                            {i === 0 && (
                              <span className="label text-[10px] text-muted">strongest</span>
                            )}
                            {i > 0 && <span className="label text-[10px] text-muted">corroborating</span>}
                          </span>
                        </td>
                        <td className="tnum px-3 py-2 text-right">{p.weight.toFixed(2)}</td>
                        <td className="tnum px-3 py-2 text-right text-muted">
                          {agent && agent.status === "ASSESSED" ? `${Math.round(agent.confidence * 100)}%` : "—"}
                        </td>
                        <td className="tnum px-3 py-2 text-right font-semibold">+{Math.round(p.contribution * 100)}</td>
                      </tr>
                    );
                  })}
                </tbody>
                <tfoot>
                  <tr className="border-t-2 border-strong bg-surface-2">
                    <td className="label px-3 py-2 text-left">Final score</td>
                    <td />
                    <td />
                    <td className="tnum px-3 py-2 text-right text-base font-bold">{Math.round(a.score * 100)}</td>
                  </tr>
                </tfoot>
              </table>
            </div>
            <p className="text-[11px] leading-relaxed text-muted">
              The strongest check sets the base; each additional independent check adds a fraction of its weight
              (corroboration). Contributions sum exactly to the score.
            </p>
          </>
        ) : (
          <p className="text-sm text-muted">No check found anything to weigh for this work.</p>
        )}

        {a.limited && a.band === "LOW" && (
          <p className="border-t border-line pt-3 text-[11px] leading-relaxed text-muted">
            <strong className="text-foreground">Limited evidence:</strong> two or more checks could not look at this work
            yet, so a low score here is not a clean chit.
          </p>
        )}
      </div>
    </Panel>
  );
}
