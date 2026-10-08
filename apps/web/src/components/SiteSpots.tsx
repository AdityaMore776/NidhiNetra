import type { AgentResult } from "@/lib/api";

// The spots of each site visit (T158): the claim judged at every spot, and the spots the work's
// size needs that were not filmed. From Site Progress's evidence.visits (agent.py, assess()).

type Verdict = "shown" | "not_shown" | "cant_tell";

interface VisitSpots {
  visit: string;
  kind: string;
  captured: string;
  spots?: { needed: number | null; filmed: number | null; verdicts: Record<string, Verdict> };
}

const WORDS: Record<Verdict, [string, string]> = {
  shown: ["✓ shown", "text-low"],
  not_shown: ["✗ not shown", "text-high"],
  cant_tell: ["can't tell", "text-muted-foreground"],
};

export function SiteSpots({ result }: { result: AgentResult }) {
  const visits = ((result.evidence as { visits?: VisitSpots[] }).visits ?? []).filter(
    (v) => v.spots && (Object.keys(v.spots.verdicts ?? {}).length > 0 || (v.spots.filmed ?? 0) < (v.spots.needed ?? 0)),
  );
  if (!visits.length) return null;
  return (
    <div className="space-y-1.5 rounded-lg bg-muted/60 px-3 py-2 text-xs">
      <div className="font-medium text-muted-foreground">The claim, spot by spot</div>
      {visits.map((v) => {
        const s = v.spots!;
        const missing = Math.max(0, (s.needed ?? 0) - (s.filmed ?? 0));
        return (
          <div key={v.visit} className="flex flex-wrap gap-x-2 gap-y-0.5">
            <span className="text-muted-foreground">
              {new Date(v.captured).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" })}:
            </span>
            {Object.entries(s.verdicts ?? {}).map(([id, verdict]) => (
              <span key={id} className={WORDS[verdict]?.[1]}>
                {id} {WORDS[verdict]?.[0] ?? verdict}
              </span>
            ))}
            {missing > 0 && (
              <span className="text-muted-foreground">
                · {missing} of {s.needed} spots not filmed
              </span>
            )}
          </div>
        );
      })}
    </div>
  );
}
