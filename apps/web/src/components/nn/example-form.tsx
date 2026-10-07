"use client";

import { CalendarClock, CheckCircle2, ClipboardList, ExternalLink, TriangleAlert } from "lucide-react";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { EngineMark } from "@/components/nn/badges";
import { FormMap } from "@/components/nn/form-map";
import { SectionHeader } from "@/components/nn/layout-bits";
import { Button } from "@/components/ui/button";
import type { Trace } from "@/lib/explain";
import { agentMeta } from "@/lib/format";
import FORM_HTML from "@/lib/forms/pre-sanction-work-intelligence-form";
import { type AgentLine, type AgentState, agentLines, markForm, showField } from "@/lib/work-form-flags";
import { fillForm, fitFrame } from "@/lib/work-form-frame";
import { cn } from "@/lib/utils";

/**
 * T142, on every prototype example's page: the work intelligence form the agency filed, and what the
 * four checks asked about it. The filing is the form page's example (public/work-form/examples.json,
 * built by data/trial/work_form_examples.py through the real engines), so this page, the dashboard and
 * /work-form show the same filing: section by section with each asked-about field marked in its
 * agent's colour, or the form itself, filled and outlined.
 */

interface Filing {
  id: string;
  title: string;
  form: Record<string, unknown>;
  form_ready: boolean;
  form_issues: string[];
  trace: Trace;
}

let filings: Promise<Filing[]> | null = null;

function loadFilings(): Promise<Filing[]> {
  filings ??= fetch("/work-form/examples.json")
    .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`filings ${r.status}`))))
    .then((f: { examples: Filing[] }) => f.examples);
  filings.catch(() => {
    filings = null;
  });
  return filings;
}

const CHIP: Record<AgentState, { label: string; className: string }> = {
  flagged: { label: "Asks", className: "bg-[var(--high)] text-white" },
  clear: { label: "Clear", className: "bg-[var(--low-soft)] text-[var(--low)]" },
  not_checked: { label: "Not checked", className: "bg-muted text-muted-foreground" },
  later: { label: "After sanction", className: "bg-muted text-muted-foreground" },
};

export function ExampleForm({ id, later }: { id: string; later?: string[] }) {
  const [ex, setEx] = useState<Filing | null | undefined>(undefined);
  const [mode, setMode] = useState<"sections" | "form">("sections");
  const frame = useRef<HTMLIFrameElement>(null);
  const unfit = useRef<() => void>(() => {});
  useEffect(() => () => unfit.current(), []);

  useEffect(() => {
    let live = true;
    loadFilings()
      .then((all) => live && setEx(all.find((e) => e.id === id) ?? null))
      .catch(() => live && setEx(null));
    return () => {
      live = false;
    };
  }, [id]);

  if (ex === undefined) return <div className="panel h-72 skeleton-shimmer" />;
  if (ex === null)
    return <div className="panel p-5 text-sm text-muted-foreground">The example form could not be loaded. Reload the page to try again.</div>;

  const lines = agentLines(ex.trace, ex.form);
  const flags = lines.flatMap((l) => l.flags);

  function load() {
    if (ex && fillForm(frame.current, ex.form)) markForm(frame.current?.contentDocument, flags);
    // below lg the form takes its full height, so a phone scrolls one page (T143)
    unfit.current();
    unfit.current = fitFrame(frame.current, "(min-width: 1024px)");
  }
  function show(field: string) {
    setMode("form");
    window.setTimeout(() => {
      frame.current?.scrollIntoView({ behavior: "smooth", block: "start" });
      showField(frame.current?.contentDocument, field);
    }, 60);
  }

  return (
    <section className="panel space-y-5 p-5 sm:p-6" aria-label="The example form">
      <SectionHeader
        eyebrow="The example form"
        title="What the agency filed, and what each check asked about it"
        description="The work intelligence form as this made-up agency filled it before sanction. Every field a check asks about is marked in that check's colour, with the reason."
        actions={
          <Button asChild variant="outline" className="rounded-xl">
            <Link href={`/work-form?example=${encodeURIComponent(id)}`}>
              <ExternalLink /> Open it in the live form
            </Link>
          </Button>
        }
      />

      <div className="grid gap-4 lg:grid-cols-12">
        <div className="space-y-3 lg:col-span-5">
          <p
            className={cn(
              "flex items-start gap-2 rounded-xl px-3 py-2 text-[13px]",
              ex.form_ready ? "bg-[var(--low-soft)] text-[var(--low)]" : "bg-amber-50 text-amber-900",
            )}
          >
            {ex.form_ready ? <CheckCircle2 className="mt-0.5 size-4 shrink-0" /> : <TriangleAlert className="mt-0.5 size-4 shrink-0" />}
            <span>
              {ex.form_ready
                ? "The form's own check: complete. Every answer the checks need is there, and the lines add up to the estimate."
                : `The form's own check: ${ex.form_issues.length} ${ex.form_issues.length === 1 ? "answer" : "answers"} still to fix before it can be judged.`}
            </span>
          </p>
          <ul className="space-y-2">
            {lines.map((l) => (
              <AgentRow key={l.id} line={l} onShow={show} />
            ))}
          </ul>
          {later && later.length > 0 && (
            <div className="rounded-xl border bg-white p-3">
              <div className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
                <CalendarClock className="size-3.5" /> After it was filed
              </div>
              <ul className="mt-1.5 space-y-1 text-[13px] leading-snug">
                {later.map((x) => (
                  <li key={x}>· {x}</li>
                ))}
              </ul>
            </div>
          )}
        </div>

        <div className="min-w-0 space-y-3 lg:col-span-7">
          <div className="flex flex-wrap items-center gap-2">
            <ClipboardList className="size-4 text-brand-600" />
            <span className="text-sm font-medium">The filing</span>
            <div className="ml-auto flex gap-1 rounded-xl bg-muted p-1 text-xs font-medium" role="tablist">
              {(
                [
                  ["sections", "Section by section"],
                  ["form", "The form as filed"],
                ] as const
              ).map(([m, label]) => (
                <button
                  key={m}
                  type="button"
                  role="tab"
                  aria-selected={mode === m}
                  onClick={() => setMode(m)}
                  className={cn(
                    "rounded-lg px-2.5 py-1 transition-colors",
                    mode === m ? "bg-white text-brand-950 shadow-sm" : "text-muted-foreground hover:text-foreground",
                  )}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>
          {mode === "sections" && <FormMap form={ex.form} flags={flags} agents={lines} />}
          <div className={cn("overflow-hidden rounded-xl border", mode !== "form" && "hidden")}>
            <iframe
              ref={frame}
              title={`Work intelligence form: ${ex.title}`}
              srcDoc={FORM_HTML}
              onLoad={load}
              className="block h-[72svh] min-h-[560px] w-full border-0 bg-[#eef2f7]"
            />
          </div>
        </div>
      </div>
    </section>
  );
}

function AgentRow({ line, onShow }: { line: AgentLine; onShow: (field: string) => void }) {
  const meta = agentMeta(line.id);
  const flagged = line.state === "flagged";
  return (
    <li
      className="rounded-xl border bg-white p-3"
      style={flagged ? { borderColor: meta.color, background: `color-mix(in srgb, ${meta.color} 6%, white)` } : undefined}
    >
      <div className="flex items-center gap-2">
        <EngineMark id={line.id} size={22} />
        <span className="text-sm font-semibold" style={{ color: flagged ? meta.color : undefined }}>
          {meta.name}
        </span>
        <span className={cn("ml-auto rounded-full px-2 py-0.5 text-[11px] font-semibold", CHIP[line.state].className)}>
          {CHIP[line.state].label}
        </span>
      </div>
      {line.flags.map((f) => (
        <div key={f.code} className="mt-2 flex items-start gap-2">
          <p className="min-w-0 flex-1 text-[13px] leading-snug">{f.why}</p>
          {f.fields.length > 0 && (
            <button
              type="button"
              onClick={() => onShow(f.fields[0].name)}
              className="shrink-0 rounded-md border bg-white px-1.5 py-0.5 text-[11px] font-medium text-brand-700 hover:bg-brand-50"
            >
              Show in form
            </button>
          )}
        </div>
      ))}
      {line.note && <p className="mt-1 text-xs text-muted-foreground">{line.note}</p>}
    </li>
  );
}
