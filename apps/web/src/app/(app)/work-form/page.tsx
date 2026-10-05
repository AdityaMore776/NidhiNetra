"use client";

import { ClipboardList, ExternalLink, FileSearch, FlaskConical, Loader2, Play } from "lucide-react";
import { motion } from "motion/react";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useRef, useState } from "react";
import { BandBadge, EngineMark } from "@/components/nn/badges";
import { PageHeader } from "@/components/nn/layout-bits";
import { Button } from "@/components/ui/button";
import { ApiError, apiPost } from "@/lib/api";
import type { Check, Trace } from "@/lib/explain";
import { agentMeta, AGENT_ORDER, inr } from "@/lib/format";
import FORM_HTML from "@/lib/forms/pre-sanction-work-intelligence-form";

/**
 * The Pre-Sanction Work Intelligence Form (forms/pre-sanction-work-intelligence-form.html), open to
 * everyone: it is shown exactly as written, in a frame, so the site's styles never touch it; its own
 * toolbar saves drafts in this browser, validates, exports JSON and prints.
 *
 * T134: example filings (made-up agencies, public/work-form/examples.json, built by
 * data/trial/work_form_examples.py through the real engines) fill the form through its own functions
 * and show what each agent said; "Check this form" sends what is in the form to
 * POST /api/v1/work-form/check, which stores nothing.
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
}

interface CheckResult {
  district: { district_lgd: string; name: string; state_name: string };
  form: { ready: boolean; work_type: string; grand_total: number; issues: { level: string; field: string; message: string }[] };
  trace: Trace;
}

type Shown =
  | { kind: "example"; ex: FormExample }
  | { kind: "own"; result: CheckResult }
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

const GROUPS: { agent: string | null; label: string }[] = [
  ...AGENT_ORDER.map((id) => ({ agent: id as string | null, label: agentMeta(id).name })),
  { agent: null, label: "Nothing to ask" },
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

  useEffect(() => {
    fetch("/work-form/examples.json")
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(String(r.status)))))
      .then(setFile)
      .catch(() => setFile(null));
  }, []);

  function pick(ex: FormExample) {
    setShown({ kind: "example", ex });
    fill(frame.current, ex.form);
  }

  // a link to /work-form?example=<id> opens with that filing, once the form and the file are in
  const linked = file && wanted ? file.examples.find((e) => e.id === wanted) : undefined;
  const view: Shown | null = shown ?? (linked ? { kind: "example", ex: linked } : null);
  useEffect(() => {
    if (ready && linked && shown === null) fill(frame.current, linked.form);
  }, [ready, linked, shown]);

  async function checkOwn() {
    const w = frame.current?.contentWindow as FormWindow | null | undefined;
    if (!w || typeof w.serialize !== "function") return;
    setShown({ kind: "checking" });
    try {
      const result = await apiPost<CheckResult>("/work-form/check", w.serialize());
      setShown({ kind: "own", result });
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

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Act · Before sanction"
        title="Work intelligence"
        accent="form."
        lead="The work's facts, collected once at sanction and in a form the agents can read: identity, site and map, duplicates and splits, the estimate line by line, timeline, clearances and the site-progress baseline."
        actions={
          <Button variant="outline" className="rounded-xl" onClick={openInNewTab}>
            <ExternalLink /> Open in a new tab
          </Button>
        }
      />

      <section className="panel space-y-3 p-4 sm:p-5" aria-label="Example filings">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <h2 className="font-semibold">Example filings</h2>
          <p className="text-xs text-muted-foreground">
            Made-up agencies and villages in the real district of Jaunpur, checked by the real agents
            {file ? ` against ${file.source.split(";")[0]}` : ""}.
          </p>
        </div>
        {!file && <p className="text-sm text-muted-foreground">Loading the examples…</p>}
        {file && (
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
            {GROUPS.map((g) => {
              const items = file.examples.filter((e) => e.agent === g.agent);
              if (!items.length) return null;
              const color = g.agent ? agentMeta(g.agent).color : "var(--muted-foreground)";
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
                            className={`w-full rounded-lg border px-2.5 py-1.5 text-left text-xs leading-snug transition-colors disabled:opacity-50 ${on ? "border-brand-600 bg-brand-50 font-medium" : "bg-white hover:bg-muted"}`}
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
        <div className="flex flex-wrap items-center gap-2 border-t pt-3 text-xs text-muted-foreground">
          <Button size="sm" className="rounded-xl" onClick={checkOwn} disabled={!ready}>
            <Play /> Check this form with the agents
          </Button>
          <span className="inline-flex items-center gap-1.5">
            <FlaskConical className="size-3.5 text-brand-600" />
            Fill it yourself or change an example, then check. Nothing is saved.
          </span>
          <span className="inline-flex items-center gap-1.5">
            <ClipboardList className="size-3.5 text-brand-600" />
            The form&apos;s own toolbar saves drafts in this browser, validates and exports.
          </span>
        </div>
      </section>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_400px]">
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
            <Verdict shown={view} />
          </div>
        </aside>
      </div>
    </div>
  );
}

function Verdict({ shown }: { shown: Shown | null }) {
  if (!shown)
    return (
      <div className="panel space-y-2 p-5 text-sm text-muted-foreground">
        <FileSearch className="size-5 text-brand-600" />
        <p>
          Pick an example filing to see the form as an agency filled it, and what each of the four agents said about it. Or fill
          the form yourself and press <b>Check this form with the agents</b>.
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
  if (shown.kind === "example") {
    const ex = shown.ex;
    return (
      <div className="panel space-y-4 p-5">
        <div className="space-y-1.5">
          <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Made-up example filing</p>
          <h3 className="font-semibold leading-snug text-balance">{ex.title}</h3>
          <p className="text-sm text-muted-foreground">{ex.story}</p>
          {ex.later.length > 0 && (
            <ul className="space-y-0.5 text-xs text-muted-foreground">
              {ex.later.map((l) => (
                <li key={l}>· {l}</li>
              ))}
            </ul>
          )}
        </div>
        <Agents trace={ex.trace} />
      </div>
    );
  }
  const { result } = shown;
  const fixes = result.form.issues.filter((i) => i.level === "fix");
  return (
    <div className="panel space-y-4 p-5">
      <div className="space-y-1.5">
        <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Your form</p>
        <h3 className="font-semibold">
          {result.district.name}, {result.district.state_name} · {inr(result.form.grand_total)}
        </h3>
        {fixes.length > 0 ? (
          <div className="space-y-1 text-xs">
            <p className="text-muted-foreground">
              The Cost check needs {fixes.length} more {fixes.length === 1 ? "answer" : "answers"} before it can judge the estimate:
            </p>
            <ul className="max-h-40 space-y-0.5 overflow-auto">
              {fixes.slice(0, 12).map((i) => (
                <li key={i.field + i.message}>· {i.message}</li>
              ))}
            </ul>
          </div>
        ) : (
          <p className="text-xs text-muted-foreground">Everything the agents read is filled in.</p>
        )}
      </div>
      <Agents trace={result.trace} />
    </div>
  );
}

const STATE: Record<Check["status"], string> = {
  ASSESSED: "Nothing to ask",
  NOT_APPLICABLE: "Does not apply yet",
  NOT_ASSESSABLE: "Could not check (not a pass)",
  NOT_BUILT: "Not run",
  ERROR: "Not run",
};

function Agents({ trace }: { trace: Trace }) {
  const r = trace.result;
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2 text-xs">
        <BandBadge band={r.band} score={r.score} />
        <span className="text-muted-foreground">{r.in_queue ? "goes to the review queue" : "not in the review queue"}</span>
      </div>
      <ul className="space-y-2.5">
        {trace.checks.map((c) => {
          const meta = agentMeta(c.id, c.name, c.question);
          const asked = c.findings.filter((f) => f.risk > 0);
          return (
            <li key={c.id} className="flex gap-2.5">
              <EngineMark id={c.id} size={26} />
              <div className="min-w-0 space-y-0.5">
                <p className="text-sm font-semibold" style={{ color: meta.color }}>
                  {meta.name}
                  <span className="ml-2 text-xs font-medium" style={{ color: asked.length ? "var(--high)" : "var(--muted-foreground)" }}>
                    {asked.length ? (asked.length === 1 ? "asks a question" : `asks ${asked.length} questions`) : STATE[c.status]}
                  </span>
                </p>
                {asked.length > 0
                  ? asked.map((f) => (
                      <p key={f.code} className="text-xs leading-relaxed">
                        {f.text}
                      </p>
                    ))
                  : c.status !== "ASSESSED"
                    ? <p className="text-xs leading-relaxed text-muted-foreground">{c.headline}</p>
                    : // checked what it could: say what it could not, so quiet never reads as a pass
                      c.limitations.slice(0, 2).map((l) => (
                        <p key={l} className="text-xs leading-relaxed text-muted-foreground">
                          {l}
                        </p>
                      ))}
              </div>
            </li>
          );
        })}
      </ul>
      <p className="text-[11px] text-muted-foreground">
        A question is for an officer to verify, never a finding of wrongdoing. &quot;Could not check&quot; is not a pass.
      </p>
    </div>
  );
}
