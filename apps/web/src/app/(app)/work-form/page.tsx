"use client";

import { ArrowUpRight, Database, ExternalLink, FileSearch, FileText, Loader2, Play } from "lucide-react";
import { motion } from "motion/react";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useRef, useState } from "react";
import { BandBadge, EngineMark } from "@/components/nn/badges";
import { PageHeader } from "@/components/nn/layout-bits";
import { type FormData, WorkFormData } from "@/components/nn/work-form-data";
import { Button } from "@/components/ui/button";
import { ApiError, apiPost } from "@/lib/api";
import type { Trace } from "@/lib/explain";
import { agentMeta, AGENT_ORDER, inr } from "@/lib/format";
import FORM_HTML from "@/lib/forms/pre-sanction-work-intelligence-form";
import { type AgentLine, type AgentState, agentLines, clearMarks, markForm, showField } from "@/lib/work-form-flags";
import { cn } from "@/lib/utils";

/**
 * The Pre-Sanction Work Intelligence Form (forms/pre-sanction-work-intelligence-form.html), open to
 * everyone: it is shown exactly as written, in a frame, so the site's styles never touch it; its own
 * toolbar saves drafts in this browser, validates, exports JSON and prints.
 *
 * T134, a demonstration: example filings (made-up agencies, public/work-form/examples.json, built by
 * data/trial/work_form_examples.py through the real engines) fill the form; each agent says flagged,
 * clear or not checked, with one line on why, and the flagged fields are outlined in the form in the
 * agent's colour. "Check this form" sends what is in the form to POST /api/v1/work-form/check?demo=true,
 * which compares it with the same example data (the Data tab) and stores nothing.
 */

interface FormExample {
  id: string;
  agent: string | null;
  title: string;
  story: string;
  later: string[];
  form: Record<string, unknown>;
  form_ready: boolean;
  form_issues: string[];
  trace: Trace;
}

interface FormExamplesFile {
  source: string;
  as_of: string;
  examples: FormExample[];
  data: FormData;
}

interface CheckResult {
  district: { district_lgd: string; name: string; state_name: string };
  form: { ready: boolean; work_type: string; grand_total: number; issues: { level: string; field: string; message: string }[] };
  trace: Trace;
}

type Shown =
  | { kind: "example"; ex: FormExample }
  | { kind: "own"; result: CheckResult; form: Record<string, unknown>; title?: string }
  | { kind: "error"; message: string }
  | { kind: "checking" };

// the form's own functions (declared in its script, so global in the frame)
type FormWindow = Window & {
  restore?: (d: Record<string, unknown>) => void;
  serialize?: () => Record<string, unknown>;
  addBoqRow?: () => void;
  addMilestoneRow?: () => void;
};

function rowsIn(data: Record<string, unknown>, prefix: string): number {
  const re = new RegExp(`^${prefix}_(\\d+)$`);
  return Math.max(1, ...Object.keys(data).map((k) => Number(re.exec(k)?.[1] ?? 0)));
}

/** Fill the framed form with a filing, through the form's own functions; false if it is not ready. */
function fill(frame: HTMLIFrameElement | null, data: Record<string, unknown>): boolean {
  const w = frame?.contentWindow as FormWindow | null | undefined;
  const doc = frame?.contentDocument;
  if (!w || !doc || typeof w.restore !== "function") return false;
  (doc.getElementById("nidhinetraForm") as HTMLFormElement | null)?.reset();
  for (const id of ["boqBody", "milestoneBody"]) {
    const body = doc.getElementById(id);
    if (body) body.innerHTML = "";
  }
  for (let i = 0; i < rowsIn(data, "boq_desc"); i++) w.addBoqRow?.();
  for (let i = 0; i < rowsIn(data, "milestone_name"); i++) w.addMilestoneRow?.();
  w.restore({ ...data, __meta: { work_id: String(data.recommendation_ref ?? "EXAMPLE") } });
  const status = doc.getElementById("headerStatus");
  if (status) status.textContent = "EXAMPLE FILING";
  w.scrollTo({ top: 0 });
  return true;
}

/** Outline in the framed form what the agents flagged. */
function mark(frame: HTMLIFrameElement | null, trace: Trace, form: Record<string, unknown>) {
  markForm(
    frame?.contentDocument,
    agentLines(trace, form).flatMap((l) => l.flags),
  );
}

const GROUPS: { agent: string | null; label: string }[] = [
  ...AGENT_ORDER.map((id) => ({ agent: id as string | null, label: agentMeta(id).name })),
  { agent: null, label: "Nothing flagged" },
];

export default function WorkFormPage() {
  return (
    <Suspense fallback={null}>
      <WorkForm />
    </Suspense>
  );
}

function WorkForm() {
  const frame = useRef<HTMLIFrameElement>(null);
  const wanted = useSearchParams().get("example");
  const [file, setFile] = useState<FormExamplesFile | null>(null);
  const [shown, setShown] = useState<Shown | null>(null);
  const [ready, setReady] = useState(false);
  const [tab, setTab] = useState<"form" | "data">("form");

  useEffect(() => {
    fetch("/work-form/examples.json")
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(String(r.status)))))
      .then(setFile)
      .catch(() => setFile(null));
  }, []);

  function pick(ex: FormExample) {
    setTab("form");
    setShown({ kind: "example", ex });
    if (fill(frame.current, ex.form)) mark(frame.current, ex.trace, ex.form);
  }

  // a link to /work-form?example=<id> opens with that filing, once the form and the file are in
  const linked = file && wanted ? file.examples.find((e) => e.id === wanted) : undefined;
  const view: Shown | null = shown ?? (linked ? { kind: "example", ex: linked } : null);
  useEffect(() => {
    if (ready && linked && shown === null && fill(frame.current, linked.form)) mark(frame.current, linked.trace, linked.form);
  }, [ready, linked, shown]);

  async function checkOwn() {
    const w = frame.current?.contentWindow as FormWindow | null | undefined;
    if (!w || typeof w.serialize !== "function") return;
    const sent = w.serialize();
    // an example, changed or not, keeps its reference number
    const title = file?.examples.find((e) => e.form.recommendation_ref === sent.recommendation_ref)?.title;
    clearMarks(frame.current?.contentDocument);
    setShown({ kind: "checking" });
    try {
      const result = await apiPost<CheckResult>("/work-form/check?demo=true", sent);
      setShown({ kind: "own", result, form: sent, title });
      mark(frame.current, result.trace, sent);
    } catch (e) {
      const message =
        e instanceof ApiError && e.status === 422
          ? "Write the district in section C first: the agents compare the work with its district."
          : e instanceof ApiError && e.status === 404
            ? `${e.message}. Check the district name in section C.`
            : "The agents could not be reached. Please try again in a minute.";
      setShown({ kind: "error", message });
    }
  }

  function openInNewTab() {
    // a blob page has this site's origin, so the drafts saved here are there too
    const url = URL.createObjectURL(new Blob([FORM_HTML], { type: "text/html" }));
    window.open(url, "_blank", "noopener");
    window.setTimeout(() => URL.revokeObjectURL(url), 60_000);
  }

  const titles = Object.fromEntries((file?.examples ?? []).map((e) => [e.id, e.title]));

  return (
    <div className="space-y-5">
      <PageHeader
        eyebrow="Act · Before sanction"
        title="Work intelligence"
        accent="form."
        lead="The implementing agency fills this form before sanction. Four agents read it and flag what an officer should check."
        actions={
          <Button variant="outline" className="rounded-xl" onClick={openInNewTab}>
            <ExternalLink /> Open in a new tab
          </Button>
        }
      />

      <section className="panel space-y-3 p-4 sm:p-5" aria-label="Example filings">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <h2 className="font-semibold">Example filings</h2>
          <p className="text-xs text-muted-foreground">Pick one: the form fills in, and the flagged fields are outlined.</p>
        </div>
        {!file && <p className="text-sm text-muted-foreground">Loading the examples…</p>}
        {file && (
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
            {GROUPS.map((g) => {
              const items = file.examples.filter((e) => e.agent === g.agent);
              if (!items.length) return null;
              const color = g.agent ? agentMeta(g.agent).color : "var(--low)";
              return (
                <div key={g.label} className="min-w-0 space-y-1.5">
                  <div className="flex items-center gap-2 text-xs font-semibold" style={{ color }}>
                    {g.agent && <EngineMark id={g.agent} size={20} />}
                    {g.label}
                  </div>
                  <ul className="space-y-1">
                    {items.map((ex) => {
                      const on = view?.kind === "example" && view.ex.id === ex.id;
                      return (
                        <li key={ex.id}>
                          <button
                            type="button"
                            onClick={() => pick(ex)}
                            disabled={!ready}
                            className={cn(
                              "w-full rounded-lg border px-2.5 py-1.5 text-left text-xs leading-snug transition-colors disabled:opacity-50",
                              on ? "border-brand-600 bg-brand-50 font-medium" : "bg-white hover:bg-muted",
                            )}
                          >
                            {ex.title}
                          </button>
                        </li>
                      );
                    })}
                  </ul>
                </div>
              );
            })}
          </div>
        )}
        <div className="flex flex-wrap items-center gap-x-3 gap-y-2 border-t pt-3 text-xs text-muted-foreground">
          <Button size="sm" className="rounded-xl" onClick={checkOwn} disabled={!ready}>
            <Play /> Check this form with the agents
          </Button>
          <span>Change any field (say, the cement quantity) and check again. Nothing is saved.</span>
        </div>
      </section>

      <div className="flex gap-1 rounded-xl bg-muted p-1 text-sm font-medium sm:w-fit" role="tablist">
        {(
          [
            ["form", "Form and flags", FileText],
            ["data", "Data the agents use", Database],
          ] as const
        ).map(([id, label, Icon]) => (
          <button
            key={id}
            type="button"
            role="tab"
            aria-selected={tab === id}
            onClick={() => setTab(id)}
            className={cn(
              "inline-flex flex-1 items-center justify-center gap-1.5 rounded-lg px-3 py-1.5 transition-colors sm:flex-none",
              tab === id ? "bg-white text-brand-950 shadow-sm" : "text-muted-foreground hover:text-foreground",
            )}
          >
            <Icon className="size-4" /> {label}
          </button>
        ))}
      </div>

      {/* the form stays mounted on the Data tab, so a filled form is never lost */}
      <div className={cn("grid gap-5 xl:grid-cols-[minmax(0,1fr)_400px]", tab !== "form" && "hidden")}>
        <motion.div
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1], delay: 0.1 }}
          className="panel order-2 min-w-0 overflow-hidden xl:order-1"
        >
          <iframe
            ref={frame}
            title="NidhiNetra — Pre-Sanction Work Intelligence Form"
            srcDoc={FORM_HTML}
            onLoad={() => setReady(true)}
            className="block h-[calc(100svh-6rem)] min-h-[640px] w-full border-0 bg-[#eef2f7]"
          />
        </motion.div>
        <aside className="order-1 min-w-0 xl:order-2" aria-live="polite">
          <div className="xl:sticky xl:top-20">
            <Verdict shown={view} onShow={(name) => showField(frame.current?.contentDocument, name)} onData={() => setTab("data")} />
          </div>
        </aside>
      </div>
      {tab === "data" &&
        (file?.data ? <WorkFormData data={file.data} titles={titles} /> : <p className="text-sm text-muted-foreground">Loading the data…</p>)}
    </div>
  );
}

function Verdict({ shown, onShow, onData }: { shown: Shown | null; onShow: (field: string) => void; onData: () => void }) {
  if (!shown)
    return (
      <div className="panel space-y-2 p-5 text-sm text-muted-foreground">
        <FileSearch className="size-5 text-brand-600" />
        <p>
          Pick an example filing above. The form fills in, each agent says what it flagged and why, and the flagged fields are outlined
          in the form.
        </p>
      </div>
    );
  if (shown.kind === "checking")
    return (
      <div className="panel flex items-center gap-2 p-5 text-sm text-muted-foreground">
        <Loader2 className="size-4 animate-spin" /> The four agents are reading the form…
      </div>
    );
  if (shown.kind === "error") return <div className="panel p-5 text-sm text-destructive">{shown.message}</div>;

  const own = shown.kind === "own";
  const trace = own ? shown.result.trace : shown.ex.trace;
  const form = own ? shown.form : shown.ex.form;
  const lines = agentLines(trace, form);
  const fixes = own ? shown.result.form.issues.filter((i) => i.level === "fix") : [];
  return (
    <div className="panel space-y-4 p-5">
      <div className="space-y-1">
        <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
          {own ? "Your form, checked just now" : "Example filing"}
        </p>
        {own ? (
          <>
            {shown.title && <h3 className="font-semibold leading-snug text-balance">{shown.title}</h3>}
            <p className={shown.title ? "text-sm text-muted-foreground" : "font-semibold"}>
              {shown.result.district.name}, {shown.result.district.state_name} · {inr(shown.result.form.grand_total)}
            </p>
          </>
        ) : (
          <>
            <h3 className="font-semibold leading-snug text-balance">{shown.ex.title}</h3>
            <p className="text-sm text-muted-foreground">{shown.ex.story}</p>
          </>
        )}
        {fixes.length > 0 && (
          <details className="text-xs text-muted-foreground">
            <summary className="cursor-pointer">
              {fixes.length} {fixes.length === 1 ? "answer" : "answers"} missing for Cost
            </summary>
            <ul className="mt-1 max-h-32 space-y-0.5 overflow-auto">
              {fixes.slice(0, 12).map((i) => (
                <li key={i.field + i.message}>· {i.message}</li>
              ))}
            </ul>
          </details>
        )}
      </div>
      <ul className="space-y-2">
        {lines.map((l) => (
          <AgentRow key={l.id} line={l} onShow={onShow} />
        ))}
      </ul>
      <div className="flex flex-wrap items-center gap-2 border-t pt-3 text-xs text-muted-foreground">
        <BandBadge band={trace.result.band} score={trace.result.score} />
        <span>{trace.result.in_queue ? "Goes to the officers' review queue" : "An officer sees the flags before sanction"}</span>
      </div>
      <button type="button" onClick={onData} className="inline-flex items-center gap-1 text-xs font-medium text-brand-700 hover:underline">
        See the data the agents compared with <ArrowUpRight className="size-3.5" />
      </button>
    </div>
  );
}

const CHIP: Record<AgentState, { label: string; className: string }> = {
  flagged: { label: "Flagged", className: "bg-[var(--high)] text-white" },
  clear: { label: "Clear", className: "bg-[var(--low-soft)] text-[var(--low)]" },
  not_checked: { label: "Not checked", className: "bg-muted text-muted-foreground" },
  later: { label: "After sanction", className: "bg-muted text-muted-foreground" },
};

function AgentRow({ line, onShow }: { line: AgentLine; onShow: (field: string) => void }) {
  const meta = agentMeta(line.id);
  const flagged = line.state === "flagged";
  return (
    <li
      className="rounded-xl border p-3"
      style={flagged ? { borderColor: meta.color, background: `color-mix(in srgb, ${meta.color} 6%, transparent)` } : undefined}
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
