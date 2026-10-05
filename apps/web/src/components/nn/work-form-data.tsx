"use client";

import { Database } from "lucide-react";
import { EngineMark } from "@/components/nn/badges";
import { agentMeta, AGENT_ORDER, inr } from "@/lib/format";

/**
 * T134: the example data the work-form demo's agents compare with, in plain words. It is written by
 * data/trial/work_form_examples.py together with the engine's own copy
 * (apps/engine/drishti/reference/demo/work_form.json), so this tab shows exactly what was used.
 */

export interface FormData {
  where: string;
  rates: { item: string; unit: string; usual: number; low: number; high: number; forms: number; agencies: number }[];
  standard: { item: string; unit: string; usual: number; ask_above: number; works: number; where: string }[];
  rules: { agent: string; text: string }[];
  works: { id: string; what: string; agency: string; amount: number; state: string }[];
  filings: { id: string; what: string; agency: string; amount: number; filed: string }[];
  after: Record<string, string[]>;
  videos: Record<string, { visit: string; date: string; kind: string; reading: string }[]>;
}

const UNIT: Record<string, string> = { m3: "m³", m2: "m²", nos: "piece" };
const rs = (v: number) => `₹${Math.round(v).toLocaleString("en-IN")}`;

function Card({ agents, title, note, children }: { agents: string[]; title: string; note?: string; children: React.ReactNode }) {
  return (
    <section className="panel space-y-3 p-4 sm:p-5">
      <div className="flex items-center gap-2">
        {agents.map((a) => (
          <EngineMark key={a} id={a} size={22} />
        ))}
        <h3 className="font-semibold">{title}</h3>
      </div>
      {note && <p className="text-xs text-muted-foreground">{note}</p>}
      {children}
    </section>
  );
}

export function WorkFormData({ data, titles }: { data: FormData; titles: Record<string, string> }) {
  // only works that were sanctioned have an "after": the others are still before sanction
  const after = Object.entries(data.after).filter(([, lines]) => lines.some((l) => l.startsWith("Sanctioned")));
  return (
    <div className="space-y-4">
      <div className="panel flex flex-wrap items-start gap-3 p-4 sm:p-5">
        <Database className="mt-0.5 size-5 shrink-0 text-brand-600" />
        <div className="min-w-0 flex-1 space-y-1 text-sm">
          <p className="font-semibold">Example data used in this demo</p>
          <p className="text-muted-foreground">
            No agency has filed this form yet, so the agents compare each filing with made-up example data in {data.where}, plus the
            district&apos;s real eSAKSHI works. Once agencies file real forms, the same checks use theirs.
          </p>
        </div>
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        <Card agents={["cost_estimate"]} title="Prices other agencies filed" note={`From the example filings in ${data.where}. The usual price is the middle one.`}>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="text-left text-xs text-muted-foreground">
                <tr>
                  <th className="py-1 pr-3 font-medium">Item</th>
                  <th className="py-1 pr-3 font-medium">Usual price</th>
                  <th className="py-1 pr-3 font-medium">Range</th>
                  <th className="py-1 font-medium">Seen on</th>
                </tr>
              </thead>
              <tbody>
                {data.rates.map((r) => (
                  <tr key={r.item} className="border-t">
                    <td className="py-1.5 pr-3">{r.item}</td>
                    <td className="num whitespace-nowrap py-1.5 pr-3 font-medium">
                      {rs(r.usual)} <span className="font-normal text-muted-foreground">/ {UNIT[r.unit] ?? r.unit}</span>
                    </td>
                    <td className="num whitespace-nowrap py-1.5 pr-3 text-muted-foreground">
                      {r.low === r.high ? "same on all" : `${rs(r.low)} to ${rs(r.high)}`}
                    </td>
                    <td className="whitespace-nowrap py-1.5 text-muted-foreground">{r.forms} forms</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {data.standard.map((s) => (
            <p key={s.item} className="rounded-lg bg-muted/60 p-2.5 text-sm">
              <b>{s.item}</b>: usually <b className="num">{rs(s.usual)}</b> per {s.unit} ({s.works} {s.where}). Flagged above{" "}
              <span className="num">{rs(s.ask_above)}</span> when the estimate is also over the MP&apos;s amount.
            </p>
          ))}
          <details className="text-sm">
            <summary className="cursor-pointer text-xs font-medium text-brand-700">The {data.filings.length} other agencies&apos; road filings</summary>
            <ul className="mt-2 space-y-1 text-xs text-muted-foreground">
              {data.filings.map((f) => (
                <li key={f.id}>
                  <span className="font-mono text-foreground">{f.id}</span> · {f.agency} · {inr(f.amount)} · filed {f.filed}
                </li>
              ))}
            </ul>
          </details>
        </Card>

        <Card agents={["dup_split"]} title="Works already on record" note="Earlier works the examples are compared with.">
          <ul className="space-y-2 text-sm">
            {data.works.map((w) => (
              <li key={w.id} className="rounded-lg border p-2.5">
                <div className="flex flex-wrap items-baseline gap-x-2">
                  <span className="font-mono text-xs font-semibold">{w.id}</span>
                  <span className="text-xs text-muted-foreground">
                    {w.state} · {inr(w.amount)}
                  </span>
                </div>
                <p>{w.what}</p>
                <p className="text-xs text-muted-foreground">{w.agency}</p>
              </li>
            ))}
          </ul>
        </Card>

        <Card agents={["time_rules", "site_progress"]} title="After sanction" note="What the record and the monthly site videos show later.">
          <div className="space-y-3">
            {after.map(([id, lines]) => (
              <div key={id} className="rounded-lg border p-2.5 text-sm">
                <p className="font-medium">{titles[id] ?? id}</p>
                <ul className="mt-0.5 text-xs text-muted-foreground">
                  {lines.map((l) => (
                    <li key={l}>· {l}</li>
                  ))}
                </ul>
                {data.videos[id] && (
                  <table className="mt-2 w-full text-xs">
                    <tbody>
                      {data.videos[id].map((v) => (
                        <tr key={v.visit} className="border-t align-top">
                          <td className="py-1 pr-2 font-mono font-semibold">{v.visit}</td>
                          <td className="whitespace-nowrap py-1 pr-2 text-muted-foreground">{v.date}</td>
                          <td className="py-1">{v.reading}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            ))}
          </div>
        </Card>

        <Card agents={[...AGENT_ORDER]} title="Rules the agents use">
          <ul className="space-y-1.5 text-sm">
            {data.rules.map((r) => (
              <li key={r.text} className="flex gap-2">
                <span className="mt-1.5 size-2 shrink-0 rounded-full" style={{ background: agentMeta(r.agent).color }} />
                <span>
                  <b className="font-medium" style={{ color: agentMeta(r.agent).color }}>
                    {agentMeta(r.agent).name}:
                  </b>{" "}
                  {r.text}
                </span>
              </li>
            ))}
          </ul>
        </Card>
      </div>
    </div>
  );
}
