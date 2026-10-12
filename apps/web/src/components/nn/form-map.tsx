"use client";

import { Check, ChevronDown, Clock, Minus } from "lucide-react";
import { useMemo, useState } from "react";
import { EngineMark } from "@/components/nn/badges";
import { AGENT_ORDER, agentMeta } from "@/lib/format";
import FORM_HTML from "@/lib/forms/pre-sanction-work-intelligence-form";
import type { AgentLine, Flag } from "@/lib/work-form-flags";
import { cn } from "@/lib/utils";

/**
 * The work intelligence form, section by section (T139): every section of the website's form
 * (lib/forms/pre-sanction-work-intelligence-form, parsed in the browser, so it never drifts from the
 * form itself), with each field's answer, which agents read the section (the form's own chips), and
 * every field an agent asks about highlighted in that agent's colour with its reason.
 */

type Field = { name: string; label: string; kind: "text" | "check" | "date" | "number"; group: string | null };
type Table = { id: string; title: string; row: string; cols: { key: string; label: string }[] };
type Section = { key: string; letter: string; title: string; agents: string[]; fields: Field[]; tables: Table[] };

const CHIP_AGENT: Record<string, string> = { cost: "cost_estimate", dup: "dup_split", time: "time_rules", site: "site_progress" };

// the tables the form builds row by row (addBoqRow / addLabourRow / addMilestoneRow in its script);
// `row` names the field that numbers a table's rows
const TABLES: Record<string, Table> = {
  boqBody: {
    id: "boq",
    title: "Estimate lines (BOQ)",
    row: "boq_desc",
    cols: [
      { key: "code", label: "SoR code" },
      { key: "desc", label: "Item" },
      { key: "unit", label: "Unit" },
      { key: "qty", label: "Qty" },
      { key: "rate", label: "Rate ₹" },
      { key: "source", label: "Rate source" },
      { key: "measure_ref", label: "Measurement ref" },
      { key: "just", label: "Justification" },
      { key: "inclab", label: "Rate incl. workers" },
    ],
  },
  labourBody: {
    id: "lab",
    title: "Labour schedule (one row per trade)",
    row: "lab_trade",
    cols: [
      { key: "trade", label: "Trade" },
      { key: "name", label: "Name (if other)" },
      { key: "grade", label: "Grade" },
      { key: "workers", label: "Workers" },
      { key: "days", label: "Days each" },
      { key: "rate", label: "Day rate ₹" },
      { key: "task", label: "What they do" },
      { key: "lines", label: "BOQ lines" },
      { key: "source", label: "Rate source" },
    ],
  },
  milestoneBody: {
    id: "milestone",
    title: "Milestones",
    row: "milestone_name",
    cols: [
      { key: "name", label: "Milestone" },
      { key: "date", label: "Date" },
      { key: "pct", label: "% done" },
      { key: "evidence", label: "Evidence" },
    ],
  },
};

function parse(html: string): Section[] {
  const doc = new DOMParser().parseFromString(html, "text/html");
  return [...doc.querySelectorAll("section.section")].map((sec, i) => {
    const title = sec.querySelector("h2")?.textContent?.trim() ?? `Section ${i + 1}`;
    const letter = /^([A-Z])\./.exec(title)?.[1] ?? String(i + 1);
    const agents = [
      ...new Set(
        [...sec.querySelectorAll(".agentchips .chip")].flatMap((c) =>
          [...c.classList].map((k) => CHIP_AGENT[k]).filter((x): x is string => Boolean(x)),
        ),
      ),
    ];
    const seen = new Set<string>();
    const fields: Field[] = [];
    for (const el of sec.querySelectorAll<HTMLInputElement>("[name]")) {
      if (seen.has(el.name)) continue;
      seen.add(el.name);
      const check = el.type === "checkbox";
      const raw = check
        ? (el.closest("label")?.querySelector("span")?.textContent ?? el.name)
        : (el.closest(".field")?.querySelector("label")?.textContent ?? el.name);
      fields.push({
        name: el.name,
        label: raw.replace(/\*/g, "").replace(/\s+/g, " ").trim(),
        kind: check ? "check" : el.type === "date" ? "date" : el.type === "number" ? "number" : "text",
        group: el.closest(".dynamic")?.id ?? null,
      });
    }
    const tables = [...sec.querySelectorAll("tbody[id]")].map((b) => TABLES[b.id]).filter((t): t is Table => Boolean(t));
    return { key: `s${i}`, letter, title: title.replace(/^[A-Z]\.\s*/, ""), agents, fields, tables };
  });
}

type Mark = { agent: string; label: string; why: string };

const show = (v: unknown, kind: Field["kind"]): string => {
  if (kind === "check") return v === true || v === "true" || v === "on" ? "Yes" : "";
  if (v === null || v === undefined) return "";
  const s = String(v).trim();
  if (kind === "date" && /^\d{4}-\d{2}-\d{2}/.test(s))
    return new Date(`${s.slice(0, 10)}T00:00:00`).toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" });
  if (kind === "number" && s && !Number.isNaN(Number(s))) return Number(s).toLocaleString("en-IN");
  return s;
};

const rowNums = (form: Record<string, unknown>, prefix: string) =>
  Object.keys(form)
    .map((k) => new RegExp(`^${prefix}_(\\d+)$`).exec(k)?.[1])
    .filter((x): x is string => Boolean(x))
    .map(Number)
    .sort((a, b) => a - b);

/** Every section of the form with the agents' marks. `flags`: what the agents asked, and about which fields. */
export function FormMap({ form, flags, agents }: { form: Record<string, unknown>; flags: Flag[]; agents: AgentLine[] }) {
  // parsed in the browser (DOMParser); the page renders this only after its examples have loaded
  const [sections] = useState<Section[] | null>(() => (typeof window === "undefined" ? null : parse(FORM_HTML)));
  const [toggled, setToggled] = useState<Record<string, boolean>>({});
  const [all, setAll] = useState(false);

  const marks = useMemo(() => {
    const m = new Map<string, Mark[]>();
    for (const f of flags)
      for (const field of f.fields) m.set(field.name, [...(m.get(field.name) ?? []), { agent: f.agent, label: field.label, why: f.why }]);
    return m;
  }, [flags]);

  const view = useMemo(() => {
    if (!sections) return [];
    return sections.map((s) => {
      // section E carries one group of fields per work type: show the group this filing answers
      const groups = new Set(s.fields.filter((f) => f.group && show(form[f.name], f.kind)).map((f) => f.group));
      const fields = s.fields.filter((f) => !f.group || groups.has(f.group) || marks.has(f.name));
      const answered = fields.filter((f) => show(form[f.name], f.kind));
      const tableNames = s.tables.flatMap((t) => rowNums(form, t.row).flatMap((n) => t.cols.map((c) => `${t.id}_${c.key}_${n}`)));
      const names = new Set([...fields.map((f) => f.name), ...tableNames]);
      const sectionFlags = flags.filter((f) => f.fields.some((x) => names.has(x.name)));
      return { ...s, fields, answered, sectionFlags };
    });
  }, [sections, form, flags, marks]);

  if (!sections) return <p className="text-sm text-muted-foreground">Reading the form…</p>;
  const state = new Map(agents.map((a) => [a.id, a.state]));

  // a flagged section is open until closed; any other, closed until opened
  const isOpen = (key: string) => toggled[key] ?? view.some((s) => s.key === key && s.sectionFlags.length > 0);
  function toggle(key: string) {
    setToggled((t) => ({ ...t, [key]: !isOpen(key) }));
  }
  function jump(key: string) {
    setToggled((t) => ({ ...t, [key]: true }));
    window.setTimeout(() => document.getElementById(`form-${key}`)?.scrollIntoView({ behavior: "smooth", block: "start" }), 30);
  }

  return (
    <div className="space-y-4">
      {/* the map on a phone (T143): each section with the four agents as small marks */}
      <div className="overflow-hidden rounded-xl border sm:hidden">
        <div className="flex items-center gap-2 bg-muted/60 px-3 py-2 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
          <span className="flex-1">Form section</span>
          {AGENT_ORDER.map((id) => (
            <span key={id} className="grid w-7 place-items-center">
              <EngineMark id={id} size={16} />
            </span>
          ))}
        </div>
        <ul>
          {view.map((s) => (
            <li key={s.key} className="border-t">
              <button type="button" onClick={() => jump(s.key)} className="flex w-full items-center gap-2 px-3 py-2 text-left text-[13px] active:bg-muted/40">
                <span className="min-w-0 flex-1">
                  <span className="mr-1 font-semibold text-muted-foreground">{s.letter}.</span>
                  <span className={cn(s.sectionFlags.length > 0 && "font-semibold")}>{s.title}</span>
                  <span className="num ml-1.5 text-[11px] text-muted-foreground">
                    {s.fields.length ? `${s.answered.length}/${s.fields.length}` : s.tables.length ? "table" : ""}
                  </span>
                </span>
                {AGENT_ORDER.map((id) => (
                  <span key={id} className="grid w-7 place-items-center">
                    <AgentCell id={id} section={s} state={state.get(id)} compact />
                  </span>
                ))}
              </button>
            </li>
          ))}
        </ul>
      </div>

      {/* the map: every section against the four agents */}
      <div className="hidden overflow-x-auto rounded-xl border sm:block">
        <table className="w-full min-w-[640px] text-[13px]">
          <thead>
            <tr className="bg-muted/60 text-[11px] uppercase tracking-wider text-muted-foreground">
              <th className="px-3 py-2 text-left font-semibold">Form section</th>
              <th className="px-2 py-2 text-right font-semibold">Answered</th>
              {AGENT_ORDER.map((id) => (
                <th key={id} className="px-2 py-2 text-center font-semibold" style={{ color: agentMeta(id).color }}>
                  <span className="inline-flex items-center gap-1 normal-case tracking-normal">
                    <EngineMark id={id} size={16} /> {agentMeta(id).name}
                  </span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {view.map((s) => (
              <tr key={s.key} className="cursor-pointer border-t hover:bg-muted/40" onClick={() => jump(s.key)}>
                <td className="px-3 py-1.5">
                  <span className="mr-1.5 font-semibold text-muted-foreground">{s.letter}.</span>
                  <span className={cn(s.sectionFlags.length > 0 && "font-semibold")}>{s.title}</span>
                </td>
                <td className="num px-2 py-1.5 text-right text-muted-foreground">
                  {s.fields.length ? `${s.answered.length}/${s.fields.length}` : s.tables.length ? "table" : "—"}
                </td>
                {AGENT_ORDER.map((id) => (
                  <td key={id} className="px-2 py-1.5 text-center">
                    <AgentCell id={id} section={s} state={state.get(id)} />
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-foreground">
        <span>
          <Check className="inline size-3.5 text-[var(--low)]" /> read, nothing to ask
        </span>
        <span>
          <span className="rounded-full bg-[var(--high)] px-1.5 py-px text-[10px] font-semibold text-white">Asks</span> found something
          to check
        </span>
        <span>
          <Clock className="inline size-3" /> reads it after sanction
        </span>
        <span>
          <Minus className="inline size-3.5" /> does not use this section
        </span>
        <button type="button" className="more-toggle ml-auto" aria-expanded={all} onClick={() => setAll((a) => !a)}>
          {all ? "Hide blank fields" : "Show blank fields too"}
        </button>
      </p>

      {/* every section, with its answers and the agents' marks */}
      <div className="space-y-2">
        {view.map((s) => {
          const opened = isOpen(s.key);
          const tint = s.sectionFlags[0] ? agentMeta(s.sectionFlags[0].agent).color : null;
          const fields = all ? s.fields : s.answered.concat(s.fields.filter((f) => marks.has(f.name) && !s.answered.includes(f)));
          const blank = s.fields.length - s.answered.length;
          return (
            <section
              key={s.key}
              id={`form-${s.key}`}
              className="scroll-mt-24 overflow-hidden rounded-xl border"
              style={tint ? { borderColor: tint } : undefined}
            >
              <button
                type="button"
                onClick={() => toggle(s.key)}
                aria-expanded={opened}
                className="flex w-full flex-wrap items-center gap-2 px-3 py-2.5 text-left"
                style={tint ? { background: `color-mix(in srgb, ${tint} 7%, white)` } : undefined}
              >
                <span className="grid size-6 shrink-0 place-items-center rounded-md bg-brand-50 text-xs font-bold text-brand-800">{s.letter}</span>
                <span className="min-w-0 flex-1 text-sm font-semibold">{s.title}</span>
                <span className="flex items-center gap-1">
                  {s.agents.map((id) => (
                    <EngineMark key={id} id={id} size={16} />
                  ))}
                </span>
                {s.sectionFlags.length > 0 && (
                  <span className="rounded-full px-2 py-0.5 text-[11px] font-semibold text-white" style={{ background: tint ?? undefined }}>
                    {s.sectionFlags.length} to check
                  </span>
                )}
                <span className="grid size-6 shrink-0 place-items-center rounded-md border border-brand-200 bg-brand-50 text-brand-700">
                  <ChevronDown className={cn("size-4 transition-transform", opened && "rotate-180")} />
                </span>
              </button>
              {opened && (
                <div className="space-y-3 border-t px-3 py-3">
                  {s.sectionFlags.length > 0 && (
                    <ul className="space-y-1.5">
                      {s.sectionFlags.map((f) => {
                        const color = agentMeta(f.agent).color;
                        return (
                          <li
                            key={`${f.agent}-${f.code}`}
                            className="flex gap-2 rounded-lg border-l-4 px-2.5 py-1.5 text-[13px] leading-snug"
                            style={{ borderColor: color, background: `color-mix(in srgb, ${color} 7%, white)` }}
                          >
                            <EngineMark id={f.agent} size={18} />
                            <span>
                              <span className="font-semibold" style={{ color }}>
                                {agentMeta(f.agent).name} asks:
                              </span>{" "}
                              {f.why}
                            </span>
                          </li>
                        );
                      })}
                    </ul>
                  )}
                  {fields.length > 0 && (
                    <dl className="grid gap-1.5 sm:grid-cols-2 xl:grid-cols-3">
                      {fields.map((f) => (
                        <FieldBox key={f.name} field={f} value={show(form[f.name], f.kind)} marks={marks.get(f.name)} />
                      ))}
                    </dl>
                  )}
                  {s.tables.map((t) => (
                    <RowsTable key={t.id} table={t} form={form} marks={marks} />
                  ))}
                  {!all && blank > 0 && (
                    <p className="text-xs text-muted-foreground">
                      {blank} field{blank === 1 ? "" : "s"} left blank (optional for this work).
                    </p>
                  )}
                  {s.fields.length === 0 && !s.tables.length && (
                    <p className="text-xs text-muted-foreground">A guide for the agency: what each agent needs. Nothing to fill.</p>
                  )}
                </div>
              )}
            </section>
          );
        })}
      </div>
    </div>
  );
}

type SectionView = Section & { sectionFlags: Flag[] };

/** What one agent made of one section: asks, read and clear, reads it after sanction, or does not use it. */
function AgentCell({ id, section, state, compact = false }: { id: string; section: SectionView; state?: string; compact?: boolean }) {
  const asked = section.sectionFlags.filter((f) => f.agent === id);
  const reads = section.agents.includes(id) || asked.length > 0;
  const color = agentMeta(id).color;
  if (!reads) return <Minus className="mx-auto size-3.5 text-muted-foreground/40" aria-label="not read" />;
  if (asked.length)
    return compact ? (
      <span className="grid h-5 min-w-5 place-items-center rounded-full px-1 text-[10px] font-bold text-white" style={{ background: color }} aria-label="asks">
        {asked.length > 1 ? asked.length : "!"}
      </span>
    ) : (
      <span className="inline-flex rounded-full px-2 py-0.5 text-[11px] font-semibold text-white" style={{ background: color }}>
        Asks{asked.length > 1 ? ` ×${asked.length}` : ""}
      </span>
    );
  if (state === "later")
    return compact ? (
      <Clock className="mx-auto size-3.5 text-muted-foreground" aria-label="reads it after sanction" />
    ) : (
      <span className="inline-flex items-center gap-1 text-[11px] text-muted-foreground">
        <Clock className="size-3" /> later
      </span>
    );
  if (state === "clear" || state === "flagged") return <Check className="mx-auto size-4 text-[var(--low)]" aria-label="read, nothing to ask" />;
  return compact ? (
    <span className="text-[10px] text-muted-foreground" aria-label="not checked">
      ?
    </span>
  ) : (
    <span className="text-[11px] text-muted-foreground">not checked</span>
  );
}

function FieldBox({ field, value, marks }: { field: Field; value: string; marks?: Mark[] }) {
  const m = marks?.[0];
  const color = m ? agentMeta(m.agent).color : null;
  return (
    <div
      className={cn("min-w-0 rounded-lg border px-2.5 py-1.5", !m && "border-transparent bg-muted/40")}
      style={color ? { borderColor: color, borderWidth: 2, background: `color-mix(in srgb, ${color} 8%, white)` } : undefined}
    >
      <dt className="text-[11px] leading-snug text-muted-foreground">{field.label}</dt>
      <dd className={cn("text-[13px] font-medium break-words", !value && "font-normal text-muted-foreground/60")}>
        {value || "—"}
      </dd>
      {marks?.map((x) => (
        <span
          key={`${x.agent}-${x.label}`}
          className="mt-1 mr-1 inline-block rounded-full px-2 py-px text-[11px] font-semibold text-white"
          style={{ background: agentMeta(x.agent).color }}
          title={x.why}
        >
          {agentMeta(x.agent).name}: {x.label}
        </span>
      ))}
    </div>
  );
}

const NUMBER_COLS = ["qty", "rate", "pct", "workers", "days"];
// the labour schedule's choices are stored as ids ("bar_bender", "highly_skilled"): shown as words
const WORD_COLS = ["lab_trade", "lab_grade"];

function cellText(table: Table, key: string, v: unknown): string {
  const kind = key === "date" ? "date" : key === "inclab" ? "check" : NUMBER_COLS.includes(key) ? "number" : "text";
  const out = show(v, kind);
  return WORD_COLS.includes(`${table.id}_${key}`) ? out.replace(/_/g, " ") : out;
}

function RowsTable({ table, form, marks }: { table: Table; form: Record<string, unknown>; marks: Map<string, Mark[]> }) {
  const nums = rowNums(form, table.row);
  if (!nums.length) return null;
  return (
    <>
      {/* T143: on a phone each row is a card of its answered columns, the asked-about ones outlined */}
      <div className="overflow-hidden rounded-lg border sm:hidden">
        <p className="bg-muted/60 px-3 py-1.5 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">{table.title}</p>
        <ol>
          {nums.map((n) => {
            const rowMarks = table.cols.flatMap((c) => marks.get(`${table.id}_${c.key}_${n}`) ?? []);
            const rowColor = rowMarks[0] ? agentMeta(rowMarks[0].agent).color : null;
            const [head, ...rest] = table.cols.filter((c) => c.key !== "code");
            const code = cellText(table, "code", form[`${table.id}_code_${n}`]);
            return (
              <li
                key={n}
                className="border-t px-3 py-2"
                style={rowColor ? { background: `color-mix(in srgb, ${rowColor} 6%, white)` } : undefined}
              >
                <div className="text-[13px] font-semibold">
                  <span className="mr-1.5 font-normal text-muted-foreground">{n}.</span>
                  {cellText(table, head.key, form[`${table.id}_${head.key}_${n}`]) || "—"}
                  {code && <span className="ml-1.5 font-mono text-[11px] font-normal text-muted-foreground">{code}</span>}
                </div>
                <dl className="mt-1 grid grid-cols-2 gap-x-3 gap-y-1">
                  {rest.map((c) => {
                    const name = `${table.id}_${c.key}_${n}`;
                    const text = cellText(table, c.key, form[name]);
                    const m = marks.get(name)?.[0];
                    if (!text && !m) return null;
                    const color = m ? agentMeta(m.agent).color : null;
                    return (
                      <div
                        key={c.key}
                        className={cn("min-w-0 rounded-md", color && "col-span-2 px-2 py-1")}
                        style={color ? { boxShadow: `inset 0 0 0 2px ${color}`, background: `color-mix(in srgb, ${color} 10%, white)` } : undefined}
                      >
                        <dt className="text-[10.5px] text-muted-foreground">{c.label}</dt>
                        <dd className={cn("break-words text-[12.5px]", color && "font-semibold")} style={color ? { color } : undefined}>
                          {text || "—"}
                        </dd>
                        {m && (
                          <span className="mt-0.5 inline-block rounded-full px-1.5 py-px text-[10px] font-semibold text-white" style={{ background: color ?? undefined }}>
                            {m.label}
                          </span>
                        )}
                      </div>
                    );
                  })}
                </dl>
              </li>
            );
          })}
        </ol>
      </div>
      <div className="hidden overflow-x-auto rounded-lg border sm:block">
      <p className="bg-muted/60 px-3 py-1.5 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">{table.title}</p>
      <table className="w-full min-w-[720px] text-[12px]">
        <thead className="text-left text-[11px] text-muted-foreground">
          <tr>
            <th className="px-2 py-1 font-semibold">#</th>
            {table.cols.map((c) => (
              <th key={c.key} className="px-2 py-1 font-semibold">
                {c.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {nums.map((n) => {
            const rowMarks = table.cols.flatMap((c) => marks.get(`${table.id}_${c.key}_${n}`) ?? []);
            const rowColor = rowMarks[0] ? agentMeta(rowMarks[0].agent).color : null;
            return (
              <tr
                key={n}
                className="border-t align-top"
                style={rowColor ? { background: `color-mix(in srgb, ${rowColor} 6%, white)` } : undefined}
              >
                <td className="px-2 py-1 text-muted-foreground">{n}</td>
                {table.cols.map((c) => {
                  const name = `${table.id}_${c.key}_${n}`;
                  const m = marks.get(name)?.[0];
                  const color = m ? agentMeta(m.agent).color : null;
                  return (
                    <td
                      key={c.key}
                      className={cn("px-2 py-1", NUMBER_COLS.includes(c.key) && "num text-right")}
                      style={color ? { boxShadow: `inset 0 0 0 2px ${color}`, background: `color-mix(in srgb, ${color} 12%, white)` } : undefined}
                    >
                      <span className={cn(color && "font-semibold")} style={color ? { color } : undefined}>
                        {cellText(table, c.key, form[name]) || "—"}
                      </span>
                      {m && (
                        <span
                          className="mt-0.5 block w-max max-w-[180px] rounded-full px-1.5 py-px text-[10px] font-semibold whitespace-normal text-white"
                          style={{ background: color ?? undefined }}
                          title={m.why}
                        >
                          {m.label}
                        </span>
                      )}
                    </td>
                  );
                })}
              </tr>
            );
          })}
        </tbody>
      </table>
      </div>
    </>
  );
}
