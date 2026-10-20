"use client";

import { ArrowUpRight, Database, ExternalLink, FileSearch, FileText, Loader2, Play } from "lucide-react";
import { motion } from "motion/react";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useRef, useState } from "react";
import { BandBadge, EngineMark } from "@/components/nn/badges";
import { PageHeader } from "@/components/nn/layout-bits";
import { Segmented } from "@/components/nn/segmented";
import { type FormData, WorkFormData } from "@/components/nn/work-form-data";
import { Button } from "@/components/ui/button";
import { ApiError, apiPost } from "@/lib/api";
import type { Trace } from "@/lib/explain";
import { agentMeta, AGENT_ORDER, inr } from "@/lib/format";
import FORM_HTML from "@/lib/forms/pre-sanction-work-intelligence-form";
import { type AgentLine, type AgentState, agentLines, clearMarks, markForm, showField } from "@/lib/work-form-flags";
import { cn } from "@/lib/utils";
import { type FormWindow, fillForm as fill, fitFrame } from "@/lib/work-form-frame";

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
  /** T170: how the picker groups it (an older file has none: an agent means suspected) */
  kind?: Kind;
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

/** Outline in the framed form what the agents flagged. */
function mark(frame: HTMLIFrameElement | null, trace: Trace, form: Record<string, unknown>) {
  markForm(
    frame?.contentDocument,
    agentLines(trace, form).flatMap((l) => l.flags),
  );
}

type Kind = "normal" | "edge" | "suspected";

/** T170 (owner): the examples as judges should read them, honest first, then the unusual, then the schemes */
const KINDS: { kind: Kind; label: string; note: string; color: string }[] = [
  { kind: "normal", label: "Normal", note: "Honest works: every agent reads the form and none asks.", color: "var(--low)" },
  {
    kind: "edge",
    label: "Edge cases",
    note: "Honest but unusual: the agents notice, say why it is fine, and at most ask for a follow-up.",
    color: "var(--medium)",
  },
  { kind: "suspected", label: "Suspected", note: "Schemes an agency could try: each is caught, and the officer is told why.", color: "var(--high)" },
];

function kindOf(ex: FormExample): Kind {
  return ex.kind ?? (ex.agent ? "suspected" : "normal");
}

/** one group's examples, the suspected ones agent by agent */
function inKind(examples: FormExample[], kind: Kind): FormExample[] {
  const order = (ex: FormExample) => (ex.agent ? AGENT_ORDER.indexOf(ex.agent) : -1);
  const items = examples.filter((e) => kindOf(e) === kind);
  return kind === "suspected" ? [...items].sort((a, b) => order(a) - order(b)) : items;
}

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
  const [group, setGroup] = useState<Kind | null>(null);

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
  // below xl the form is under the verdict: it takes its full height, so the page scrolls as one (T143)
  useEffect(() => (ready ? fitFrame(frame.current, "(min-width: 1280px)") : undefined), [ready]);

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
  // the group on show: the one picked, else the shown example's, else the honest ones
  const active: Kind = group ?? (view?.kind === "example" ? kindOf(view.ex) : "normal");
  const activeKind = KINDS.find((k) => k.kind === active) ?? KINDS[0];

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
        {/* T143: on a phone the filings are one list to pick from, grouped as on a wide screen */}
        {file && (
          <label className="block md:hidden">
            <span className="sr-only">Example filing</span>
            <select
              className="h-11 w-full rounded-xl border bg-white px-3 text-sm disabled:opacity-50"
              value={view?.kind === "example" ? view.ex.id : ""}
              disabled={!ready}
              onChange={(e) => {
                const ex = file.examples.find((x) => x.id === e.target.value);
                if (ex) pick(ex);
              }}
            >
              <option value="" disabled>
                Pick an example filing…
              </option>
              {KINDS.map((g) => {
                const items = inKind(file.examples, g.kind);
                return items.length ? (
                  <optgroup key={g.kind} label={`${g.label} (${items.length})`}>
                    {items.map((ex) => (
                      <option key={ex.id} value={ex.id}>
                        {ex.title}
                      </option>
                    ))}
                  </optgroup>
                ) : null;
              })}
            </select>
          </label>
        )}
        {file && (
          <div className="hidden space-y-3 md:block">
            <div className="flex flex-wrap items-center gap-3">
              <Segmented<Kind>
                value={active}
                onChange={setGroup}
                options={KINDS.map((g) => ({ value: g.kind, label: g.label, dot: g.color, count: inKind(file.examples, g.kind).length }))}
              />
              <span className="text-xs text-muted-foreground">{activeKind.note}</span>
            </div>
            <ul className="grid gap-1.5 md:grid-cols-2 xl:grid-cols-4">
              {inKind(file.examples, active).map((ex) => {
                const on = view?.kind === "example" && view.ex.id === ex.id;
                return (
                  <li key={ex.id}>
                    <button
                      type="button"
                      onClick={() => pick(ex)}
                      disabled={!ready}
                      title={ex.agent ? `About ${agentMeta(ex.agent).name}` : "Every agent reads it"}
                      className={cn(
                        "flex h-full w-full items-start gap-2 rounded-lg border px-2.5 py-1.5 text-left text-xs leading-snug transition-colors disabled:opacity-50",
                        on ? "border-brand-600 bg-brand-50 font-medium" : "bg-white hover:bg-muted",
                      )}
                    >
                      {ex.agent && <EngineMark id={ex.agent} size={16} />}
                      <span className="min-w-0">{ex.title}</span>
                    </button>
                  </li>
                );
              })}
            </ul>
          </div>
        )}
        <div className="flex flex-wrap items-center gap-x-3 gap-y-2 border-t pt-3 text-xs text-muted-foreground">
          <Button size="sm" className="rounded-xl" onClick={checkOwn} disabled={!ready}>
            <Play /> Check this form with the agents
          </Button>
          <span>Change any field (say, the cement quantity) and check again. Nothing is saved.</span>
        </div>
      </section>

      <Segmented<"form" | "data">
        value={tab}
        onChange={setTab}
        label="View"
        className="w-full sm:w-fit"
        options={[
          { value: "form", label: "Form and flags", icon: <FileText /> },
          { value: "data", label: "Data the agents use", icon: <Database /> },
        ]}
      />

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
            <summary className="more-toggle">
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
