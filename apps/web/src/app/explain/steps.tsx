"use client";

// The six steps of the Visualization Engine (T092). Each step draws one part of the trace
// (lib/explain.ts) and animates it with the classes in explain.css; the page replays a step by
// mounting it again. Nothing here computes a score: every number comes from the engine.

import type { CSSProperties, ReactNode } from "react";
import { BandBadge } from "@/components/ui";
import type { PreColour } from "@/lib/api";
import type { Check, Habit, Kind, Neighbour, Trace } from "@/lib/explain";
import { agentMeta, BAND_COLOR, BAND_LABEL, inr } from "@/lib/format";

/** Inline style carrying an animation delay (and any other custom properties). */
export function at(ms: number, extra: Record<string, string> = {}): CSSProperties {
  return { "--d": `${Math.round(ms)}ms`, ...extra } as CSSProperties;
}

const pct = (v: number, digits = 0) => `${(v * 100).toFixed(digits)}%`;
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

export function day(iso: string | null | undefined): string {
  if (!iso) return "-";
  const [y, m, d] = iso.split("-").map(Number);
  return `${d} ${MONTHS[m - 1]} ${y}`;
}

function epoch(iso: string): number {
  const [y, m, d] = iso.split("-").map(Number);
  return Date.UTC(y, m - 1, d) / 86_400_000;
}

const STAGE: Record<string, string> = {
  RECOMMENDED: "Recommended by the MP, waiting for sanction",
  SANCTIONED: "Sanctioned, work under way",
  COMPLETED: "Recorded as completed",
};

// ---- step 1: the work goes in -------------------------------------------------------------

export function InputStep({ t }: { t: Trace }) {
  const i = t.input;
  const dates = (
    [
      ["Recommended", i.recommended],
      ["Sanctioned", i.sanctioned],
      ["Completed", i.completed],
    ] as const
  )
    .filter(([, v]) => v)
    .map(([k, v]) => `${k} ${day(v)}`)
    .join(" · ");
  const rows: [string, ReactNode][] = [
    ["Kind of work", i.work_type_name ?? "Not given"],
    ["What it says", i.description ? <q>{i.description}</q> : <span className="text-muted">(nothing written)</span>],
    ["Amount", inr(i.amount)],
    ["Where", [i.district, i.state].filter(Boolean).join(", ") || "-"],
    ["Implementing office", i.office ?? "Not given"],
    ["Stage", STAGE[i.status ?? ""] ?? i.status ?? "-"],
    ["Dates", dates || "-"],
  ];
  return (
    <div className="grid items-center gap-6 md:grid-cols-[1fr_240px]">
      <div className="rounded-xl border border-line bg-surface p-4 shadow-sm">
        <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted">One work record</div>
        <dl className="space-y-2">
          {rows.map(([k, v], n) => (
            <div
              key={k}
              className="x-in grid grid-cols-[120px_1fr] gap-3 border-b border-line pb-2 text-sm last:border-0 sm:grid-cols-[150px_1fr]"
              style={at(200 + n * 330)}
            >
              <dt className="text-muted">{k}</dt>
              <dd className="font-medium break-words">{v}</dd>
            </div>
          ))}
        </dl>
      </div>
      <div className="text-center">
        <svg viewBox="0 0 260 150" className="mx-auto h-36 w-full max-w-[240px] overflow-hidden" aria-hidden>
          <line x1="50" y1="75" x2="180" y2="75" stroke="var(--line)" strokeWidth="3" strokeDasharray="6 6" />
          <g className="x-fly" style={at(2700, { "--fx": "150px" })}>
            <rect x="16" y="46" width="44" height="58" rx="5" fill="var(--surface)" stroke="var(--inputs)" strokeWidth="2.5" />
            {[60, 70, 80, 90].map((y) => (
              <line key={y} x1="24" y1={y} x2={y === 90 ? 42 : 52} y2={y} stroke="var(--inputs)" strokeWidth="2" />
            ))}
          </g>
          <g className="x-pulse" style={at(3600)}>
            <path d="M178 75 C192 50, 238 50, 252 75 C238 100, 192 100, 178 75 Z" fill="none" stroke="var(--navy)" strokeWidth="3" />
            <circle cx="215" cy="75" r="11" fill="var(--inputs)" />
            <circle cx="215" cy="75" r="4.5" fill="var(--navy)" />
          </g>
        </svg>
        <p className="x-in text-xs text-muted" style={at(3600)}>
          into DRISHTI. All 2,09,993 works on the live site go through these same steps.
        </p>
      </div>
    </div>
  );
}

// ---- step 2: private details are hidden ---------------------------------------------------

type Piece = { t: string; hidden: "name" | "phone" | "number" | null; at: number };

function pieces(text: string): Piece[] {
  const out: Piece[] = [];
  let pos = 0;
  for (const p of text.split(/(\[(?:name|phone|number)\]|\s+)/)) {
    if (!p) continue;
    const m = /^\[(name|phone|number)\]$/.exec(p);
    out.push({ t: p, hidden: m ? (m[1] as Piece["hidden"]) : null, at: pos });
    pos += p.length;
  }
  return out;
}

const HIDDEN_LABEL = { name: "name", phone: "phone no.", number: "account no." } as const;

export function PrivacyStep({ t }: { t: Trace }) {
  const text = t.input.description || "";
  const total = Math.max(1, text.length);
  const scan = 2400;
  const end = 400 + scan;
  const h = t.privacy.hidden;
  const any = h.name + h.phone + h.number > 0;
  return (
    <div className="space-y-5">
      <div className="rounded-xl border border-line bg-surface p-4 text-[15px] leading-8">
        <div className="mb-1 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-muted">
          <span className="x-pulse inline-block h-2.5 w-2.5 rounded-full bg-inputs" /> Scanning the description
        </div>
        {text ? (
          pieces(text).map((p, n) => {
            const when = 400 + (p.at / total) * scan;
            if (p.hidden)
              return (
                <span
                  key={n}
                  className="x-redact mx-0.5 inline-block rounded-md px-2 text-xs font-semibold leading-6"
                  style={at(when)}
                >
                  {HIDDEN_LABEL[p.hidden]} hidden
                </span>
              );
            if (/^\s+$/.test(p.t)) return <span key={n}>{p.t}</span>;
            return (
              <span key={n} className="x-scanword rounded" style={at(when)}>
                {p.t}
              </span>
            );
          })
        ) : (
          <span className="text-muted">(nothing written)</span>
        )}
      </div>
      <div className="grid grid-cols-3 gap-3">
        {(
          [
            ["name", "names of people"],
            ["phone", "phone numbers"],
            ["number", "bank account numbers"],
          ] as const
        ).map(([k, label], n) => (
          <div key={k} className="x-pop rounded-xl border border-line bg-surface p-3 text-center" style={at(end + n * 200)}>
            <div className="text-2xl font-bold" style={{ color: h[k] ? "var(--foreground)" : "var(--low)" }}>
              {h[k]}
            </div>
            <div className="text-xs text-muted">{label} hidden</div>
          </div>
        ))}
      </div>
      <p className="x-in text-sm" style={at(end + 700)}>
        {any
          ? "These details are covered before any check runs, and they never come back. "
          : "Nothing private in this one, so the text goes on as it is. "}
        The checks never need a person&apos;s name: they work on what was asked for, where, for how much and when. MPs
        are never scored.
      </p>
    </div>
  );
}

// ---- step 3: reading the description ------------------------------------------------------

export const KINDS: Record<Kind, { label: string; c: string }> = {
  place: { label: "a place", c: "var(--inputs)" },
  quantity: { label: "a size or count", c: "var(--statistical)" },
  build: { label: "a construction", c: "var(--fusion)" },
  goods: { label: "a purchase", c: "var(--reuse)" },
  not_allowed: { label: "on the not-allowed list", c: "var(--high)" },
  private: { label: "hidden detail", c: "var(--foreground)" },
};

function lit(kind: Kind): Record<string, string> {
  const c = KINDS[kind].c;
  return kind === "private"
    ? { "--bg": c, "--fg": "#fff", "--ring": c }
    : { "--bg": `color-mix(in srgb, ${c} 20%, white)`, "--fg": "var(--foreground)", "--ring": c };
}

/** The description as words (a coloured run stays whole); `i` counts words, -1 for spaces. */
type Token = { t: string; k: Kind | null; i: number };

function tokens(t: Trace): Token[] {
  const out: Token[] = [];
  let i = 0;
  for (const s of t.reading.segments) {
    const parts = s.k ? [s.t] : s.t.split(/(\s+)/);
    for (const w of parts) if (w) out.push({ t: w, k: s.k, i: w.trim() ? i++ : -1 });
  }
  return out;
}

export function ReadingStep({ t }: { t: Trace }) {
  const toks = tokens(t);
  const words = toks.filter((x) => x.i >= 0).length || 1;
  const gap = Math.min(110, 2600 / words);
  const f = t.reading.facts;
  const h = t.privacy.hidden;
  const hidden = h.name + h.phone + h.number;
  const neurons = [
    { label: "Place named", on: f.place_named, c: "var(--inputs)", note: f.place_named ? "a repeat can be looked for" : "a repeat can't be ruled out" },
    { label: "Length stated", on: f.length_m != null, c: "var(--statistical)", note: f.length_m != null ? `${f.length_m} m` : "none" },
    { label: "Units counted", on: !!f.count || f.single_unit, c: "var(--statistical)", note: f.count ? `${f.count} units` : f.single_unit ? "exactly one" : "none" },
    { label: "A purchase", on: f.what.startsWith("goods"), c: "var(--reuse)", note: f.what },
    { label: "Several sites or a bundle", on: f.several_sites || f.bundle, c: "var(--duplicate)", note: f.several_sites ? "several sites" : f.bundle ? "a bundle" : "one job" },
    { label: "Not-allowed word", on: !!f.not_allowed, c: "var(--high)", note: f.not_allowed ? `"${f.not_allowed.word}"` : "none" },
    { label: "Says nothing checkable", on: f.says_nothing, c: "var(--critical)", note: f.says_nothing ? "no size, no place" : "it says what" },
    { label: "Private detail", on: hidden > 0, c: "var(--foreground)", note: hidden ? `${hidden} hidden` : "none" },
  ];
  const start = 400 + words * gap + 300;
  const used = new Set(toks.map((x) => x.k).filter(Boolean) as Kind[]);
  return (
    <div className="space-y-6">
      <div className="rounded-xl border border-line bg-surface p-4 text-[15px] leading-9">
        {toks.length ? (
          toks.map((x, n) => {
            if (x.i < 0) return <span key={n}>{x.t}</span>;
            const when = 400 + x.i * gap;
            return x.k ? (
              <span key={n} className="x-light px-1 py-0.5 font-medium" style={at(when, lit(x.k))} title={KINDS[x.k].label}>
                {x.t}
              </span>
            ) : (
              <span key={n} className="x-word" style={at(when)}>
                {x.t}
              </span>
            );
          })
        ) : (
          <span className="text-muted">(nothing written)</span>
        )}
        <div className="mt-2 flex flex-wrap gap-2 text-[11px]">
          {(Object.keys(KINDS) as Kind[]).map((k) => (
            <span
              key={k}
              className="rounded-full border px-2 py-0.5"
              style={{ borderColor: KINDS[k].c, opacity: used.has(k) ? 1 : 0.35 }}
            >
              <span className="mr-1 inline-block h-2 w-2 rounded-full" style={{ background: KINDS[k].c }} />
              {KINDS[k].label}
            </span>
          ))}
        </div>
      </div>

      <div className="flex items-center gap-2 text-xs text-muted">
        <span className="h-px flex-1 bg-line" />
        what the reader found (a lit circle is a fact found)
        <span className="h-px flex-1 bg-line" />
      </div>

      <div className="grid grid-cols-4 gap-x-2 gap-y-4 sm:grid-cols-8">
        {neurons.map((n, k) => (
          <div key={n.label} className="x-in text-center" style={at(start + k * 160)}>
            <div
              className={`mx-auto grid h-11 w-11 place-items-center rounded-full border-2 text-sm font-bold text-white ${n.on ? "x-neuron" : ""}`}
              style={n.on ? at(start + k * 160 + 150, { "--c": n.c }) : { borderColor: "var(--line)", background: "var(--surface)" }}
            >
              {n.on ? "✓" : ""}
            </div>
            <div className="mt-1.5 text-[11px] font-medium leading-tight">{n.label}</div>
            <div className="text-[10px] leading-tight text-muted">{n.note}</div>
          </div>
        ))}
      </div>

      {f.not_allowed && (
        <p className="x-in rounded-lg border p-3 text-sm" style={at(start + 1500, { borderColor: "var(--high)" })}>
          <span className="font-semibold" style={{ color: "var(--high)" }}>
            &quot;{f.not_allowed.word}&quot;
          </span>{" "}
          matches the guidelines&apos; list of works MPLADS does not allow
          {f.not_allowed.item ? ` (Annexure-II item ${f.not_allowed.item})` : ""}: {f.not_allowed.rule}
        </p>
      )}
      {f.era && (
        <p className="x-in text-xs text-muted" style={at(start + 1700)}>
          Era: {f.era}. Works from before eSAKSHI went digital (2023) are only compared with works of their own era.
        </p>
      )}
    </div>
  );
}

// ---- step 4: the checks ---------------------------------------------------------------------

type Tone = "raised" | "quiet" | "clear" | "off";

export function checkState(c: Check): { label: string; tone: Tone } {
  if (c.status === "ASSESSED") {
    const raised = c.findings.some((f) => f.risk > 0);
    if (raised && c.counted) return { label: "Raises a question", tone: "raised" };
    if (raised) return { label: "Notes something (shown, not counted)", tone: "quiet" };
    return { label: "Nothing found", tone: "clear" };
  }
  if (c.status === "NOT_APPLICABLE") return { label: "Does not apply here", tone: "off" };
  if (c.status === "NOT_ASSESSABLE") return { label: "Could not check (not a pass)", tone: "off" };
  return { label: "Not run", tone: "off" };
}

const TONE: Record<Tone, string> = {
  raised: "var(--high)",
  quiet: "var(--medium)",
  clear: "var(--low)",
  off: "var(--muted)",
};

const DATE_RULES = new Set(["R01", "R02", "R06", "R13", "R14"]);

function Rules({ c, t, start }: { c: Check; t: Trace; start: number }) {
  const rules = c.picture?.rules ?? [];
  const dated = rules.some((r) => r.raised && r.id && DATE_RULES.has(r.id));
  return (
    <div className="space-y-2">
      <ul className="space-y-0.5 text-[11px]">
        {rules.map((r, n) => (
          <li key={r.id} className="x-in flex items-center gap-1.5" style={at(start + n * 110)}>
            <span
              className="grid h-4 w-4 shrink-0 place-items-center rounded-full text-[9px] font-bold text-white"
              style={{ background: r.raised ? "var(--high)" : "var(--low)" }}
            >
              {r.raised ? "!" : "✓"}
            </span>
            <span className={r.raised ? "font-semibold" : "text-muted"}>
              {r.id} {r.title}
            </span>
          </li>
        ))}
      </ul>
      {dated && (
        <Timeline
          start={start + rules.length * 110}
          points={[
            { label: "recommended", date: t.input.recommended, color: "var(--inputs)" },
            { label: "sanctioned", date: t.input.sanctioned, color: "var(--navy)" },
            { label: "completed", date: t.input.completed, color: "var(--high)" },
          ]}
          clocks={[]}
        />
      )}
    </div>
  );
}

function CostBar({ c, start }: { c: Check; start: number }) {
  const row = c.picture?.comparison?.[0];
  if (!row) return <p className="text-[11px] text-muted">{c.headline}</p>;
  const comfort = row.comfort_high ?? null;
  const vals = [row.typical_low, row.typical_high, row.this_work, row.median, comfort ?? row.typical_high].filter((v) => v > 0);
  const a = Math.min(...vals) / 1.8;
  const b = Math.max(...vals) * 1.8;
  const x = (v: number) => `${((Math.log(v) - Math.log(a)) / (Math.log(b) - Math.log(a))) * 100}%`;
  const raised = c.findings.some((f) => f.risk > 0);
  const n = c.picture?.cohort?.n;
  return (
    <div className="space-y-1.5">
      <div className="relative mt-5 h-9">
        <div className="absolute inset-x-0 top-1/2 h-px bg-line" />
        <div
          className="x-in absolute top-1.5 h-6 rounded"
          style={at(start, {
            left: x(row.typical_low),
            width: `calc(${x(row.typical_high)} - ${x(row.typical_low)} + 3px)`,
            background: "color-mix(in srgb, var(--statistical) 35%, white)",
          })}
          title="usual for similar works"
        />
        {comfort ? (
          <div
            className="x-in absolute -top-4 h-[52px] border-l-2 border-dashed"
            style={at(start + 300, { left: x(comfort), borderColor: "var(--statistical)" })}
          >
            <span className="absolute -top-0.5 left-1 whitespace-nowrap text-[9px] text-muted">comfort limit</span>
          </div>
        ) : null}
        <div
          className="x-slide absolute top-1/2 h-4 w-4 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-white shadow"
          style={at(start + 600, { "--x": x(row.this_work), background: raised ? "var(--high)" : "var(--navy)" })}
        />
      </div>
      <div className="flex justify-between text-[10px] text-muted">
        <span>cheaper</span>
        <span>costlier (each step = more times the price)</span>
      </div>
      <p className="x-in text-[11px]" style={at(start + 1500)}>
        Usual: <b>{inr(row.typical_low)}</b> to <b>{inr(row.typical_high)}</b>
        {n ? ` (${n.toLocaleString("en-IN")} ${c.picture?.cohort?.description ?? "similar works"})` : ""}. This work:{" "}
        <b style={{ color: raised ? "var(--high)" : undefined }}>{inr(row.this_work)}</b>
        {comfort ? `, comfort limit ${inr(comfort)}` : ""}.
      </p>
    </div>
  );
}

function Constellation({ c, start }: { c: Check; start: number }) {
  const p = c.picture;
  const near: Neighbour[] = p?.nearest ?? [];
  if (!p || !near.length) return <p className="text-[11px] text-muted">{c.headline}</p>;
  const r = (l: number) => 14 + (1 - Math.max(0, Math.min(1, l))) * 90;
  const flag = p.flag ?? 0.75;
  const pos = near.map((nb, n) => {
    const ang = ((-90 + n * (360 / near.length)) * Math.PI) / 180;
    return { nb, x: 110 + r(nb.likeness) * Math.cos(ang), y: 110 + r(nb.likeness) * Math.sin(ang) };
  });
  const top = near.find((n) => n.flagged) ?? near[0];
  return (
    <div className="space-y-1.5">
      <svg viewBox="0 0 220 220" className="mx-auto h-56 w-56 overflow-visible" aria-label="The most alike works of the district">
        <circle cx="110" cy="110" r={r(flag)} fill="none" stroke="var(--duplicate)" strokeDasharray="3 4" opacity="0.6" />
        <text x={110 + r(flag) + 3} y="113" fontSize="8" fill="var(--duplicate)">
          repeat line
        </text>
        {pos.map(({ nb, x, y }, n) => (
          <line
            key={nb.work_id}
            className="x-draw"
            pathLength={1}
            x1="110"
            y1="110"
            x2={x}
            y2={y}
            stroke={nb.flagged ? "var(--duplicate)" : "var(--muted)"}
            strokeWidth={1 + nb.likeness * 3}
            opacity={0.25 + nb.likeness * 0.75}
            style={at(start + 200 + n * 220)}
          />
        ))}
        {pos.map(({ nb, x, y }, n) => (
          <g key={nb.work_id} className="x-pop" style={at(start + 350 + n * 220)}>
            <title>{`${nb.description} (${pct(nb.likeness)} alike)`}</title>
            <circle cx={x} cy={y} r={nb.flagged ? 7 : 5} fill={nb.flagged ? "var(--duplicate)" : "var(--surface)"} stroke={nb.flagged ? "var(--duplicate)" : "var(--muted)"} strokeWidth="2" />
            <text x={x} y={y + (y < 110 ? -9 : 15)} textAnchor="middle" fontSize="9" fill="var(--foreground)">
              {pct(nb.likeness)}
            </text>
          </g>
        ))}
        <circle className="x-pop" style={at(start)} cx="110" cy="110" r="8" fill="var(--navy)" />
        <text x="110" y="128" textAnchor="middle" fontSize="8" fill="var(--navy)" className="x-in" style={at(start)}>
          this work
        </text>
      </svg>
      <p className="x-in text-[11px]" style={at(start + 1700)}>
        Compared with <b>{(p.compared ?? 0).toLocaleString("en-IN")}</b> works of the district; the {near.length} most
        alike are drawn (closer = more alike). Closest: <q className="text-muted">{top.description}</q> ({pct(top.likeness)}{" "}
        alike, {inr(top.amount)}, {day(top.date)}).
      </p>
    </div>
  );
}

function Timeline({
  points,
  clocks,
  start,
}: {
  points: { label: string; date: string | null | undefined; color: string }[];
  clocks: { from: string; days: number; label: string }[];
  start: number;
}) {
  const pts = points.filter((p): p is { label: string; date: string; color: string } => !!p.date);
  if (!pts.length) return null;
  const all = [...pts.map((p) => epoch(p.date)), ...clocks.map((c) => epoch(c.from) + c.days)];
  const lo = Math.min(...all);
  const hi = Math.max(...all);
  const span = Math.max(30, hi - lo);
  const xn = (e: number) => 4 + ((e - lo) / span) * 92;
  const x = (e: number) => `${xn(e)}%`;
  // a label near either end is aligned inwards, so it stays inside the card
  const align = (e: number) => (xn(e) < 18 ? "left-0" : xn(e) > 82 ? "right-0" : "left-1/2 -translate-x-1/2");
  return (
    <div className="relative h-24">
      <div className="absolute inset-x-0 top-12 h-0.5 bg-line" />
      {clocks.map((c, n) => (
        <div
          key={c.label}
          className="x-grow-w absolute h-2 rounded"
          style={at(start + n * 300, {
            left: x(epoch(c.from)),
            "--w": `${(c.days / span) * 92}%`,
            top: `${54 + n * 10}px`,
            background: "color-mix(in srgb, var(--site) 55%, white)",
          })}
          title={`${c.label}: ${c.days} days`}
        >
          <span className="absolute left-0 top-2 whitespace-nowrap text-[9px] text-muted">{c.label}</span>
        </div>
      ))}
      {pts.map((p, n) => (
        <div
          key={p.label}
          className="x-pop absolute top-12 -translate-x-1/2 -translate-y-1/2"
          style={at(start + 300 + n * 300, { left: x(epoch(p.date)) })}
        >
          <div className="h-3.5 w-3.5 rounded-full border-2 border-white shadow" style={{ background: p.color }} />
          <div
            className={`absolute whitespace-nowrap text-center text-[9px] leading-tight ${align(epoch(p.date))}`}
            style={{ top: n % 2 ? "14px" : "-26px" }}
          >
            <b>{p.label}</b>
            <br />
            {day(p.date)}
          </div>
        </div>
      ))}
    </div>
  );
}

function FundFlow({ c, start }: { c: Check; start: number }) {
  const p = c.picture;
  if (!p?.recommended) return <p className="text-[11px] text-muted">{c.headline}</p>;
  const clocks = [{ from: p.recommended, days: p.sanction_clock_days ?? 75, label: `sanction due within ${p.sanction_clock_days ?? 75} days` }];
  return (
    <div className="space-y-1">
      <Timeline
        start={start}
        points={[
          { label: "recommended", date: p.recommended, color: "var(--inputs)" },
          { label: "sanctioned", date: p.sanctioned, color: "var(--navy)" },
          { label: "completed", date: p.completed, color: "var(--low)" },
          { label: "today", date: p.as_of !== p.recommended ? p.as_of : null, color: "var(--muted)" },
        ]}
        clocks={clocks}
      />
      <p className="x-in text-[11px] text-muted" style={at(start + 1200)}>
        {c.headline}
      </p>
    </div>
  );
}

function HabitBars({ label, h, start }: { label: string; h: Habit; start: number }) {
  const top = Math.max(h.share, h.national_share, 0.01) * 1.25;
  return (
    <div className="space-y-0.5">
      <div className="text-[11px] font-medium">{label}</div>
      {(
        [
          ["this office", h.share, `${h.office.toLocaleString("en-IN")} of ${h.of.toLocaleString("en-IN")} (${pct(h.share, 1)})`, "var(--reuse)"],
          ["whole scheme", h.national_share, pct(h.national_share, 1), "var(--muted)"],
        ] as const
      ).map(([who, v, text, color], n) => (
        <div key={who} className="flex items-center gap-2 text-[10px]">
          <span className="w-20 shrink-0 text-muted">{who}</span>
          <div className="h-2.5 flex-1 rounded bg-background">
            <div className="x-grow-w h-full rounded" style={at(start + n * 250, { "--w": `${(v / top) * 100}%`, background: color })} />
          </div>
          <span className="w-24 shrink-0 text-right">{text}</span>
        </div>
      ))}
    </div>
  );
}

function OfficeHabits({ c, start }: { c: Check; start: number }) {
  const p = c.picture;
  const a = p?.priced_just_under_a_limit;
  const b = p?.built_within_a_week_of_sanction;
  if (!a && !b) return <p className="text-[11px] text-muted">{c.headline}</p>;
  return (
    <div className="space-y-2">
      {a && <HabitBars label="Works priced just under a Rs 5 or 10 lakh limit" h={a} start={start} />}
      {b && <HabitBars label="Constructions complete within a week of sanction" h={b} start={start + 500} />}
    </div>
  );
}

function Picture({ c, t, start }: { c: Check; t: Trace; start: number }) {
  if (c.status !== "ASSESSED") {
    return (
      <div className="grid place-items-center gap-1 rounded-lg border border-dashed border-line p-3 text-center text-[11px] text-muted">
        <span className="text-xl" aria-hidden>
          {c.id === "photo_evidence" ? "📷" : c.id === "paperwork" ? "📄" : "…"}
        </span>
        {c.headline}
      </div>
    );
  }
  if (c.id === "compliance") return <Rules c={c} t={t} start={start} />;
  if (c.id === "statistical") return <CostBar c={c} start={start} />;
  if (c.id === "dup_split") return <Constellation c={c} start={start} />;
  if (c.id === "delay") return <FundFlow c={c} start={start} />;
  if (c.id === "office_patterns") return <OfficeHabits c={c} start={start} />;
  return <p className="text-[11px] text-muted">{c.headline}</p>;
}

export const CHECK_GAP = 650;

export function ChecksStep({ t }: { t: Trace }) {
  return (
    <div className="space-y-3">
      <div className="x-in flex items-center gap-2 text-xs text-muted" style={at(0)}>
        <span className="h-px flex-1 bg-line" />
        the read work goes to every check at the same time
        <span className="h-px flex-1 bg-line" />
      </div>
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        {t.checks.map((c, n) => {
          const meta = agentMeta(c.id, c.name, c.question);
          const s = checkState(c);
          const start = 300 + n * CHECK_GAP;
          return (
            <div
              key={c.id}
              className={`rounded-xl ${s.tone === "raised" ? "x-glow" : ""}`}
              style={at(start + 900, { "--c": meta.color })}
            >
              <div
                className={`x-activate h-full rounded-xl border bg-surface p-3 ${s.tone === "off" ? "border-dashed" : ""}`}
                style={at(start, { borderColor: s.tone === "raised" ? meta.color : "var(--line)" })}
              >
                <div className="flex items-center gap-2">
                  <span className="rounded px-1.5 text-[10px] font-bold text-white" style={{ background: meta.color }}>
                    {meta.n}
                  </span>
                  <span className="text-sm font-semibold" style={{ color: meta.color }}>
                    {meta.name}
                  </span>
                  <span className="ml-auto text-[10px] text-muted">{c.counted ? "counted" : "shown, not counted"}</span>
                </div>
                <p className="mb-2 mt-0.5 text-[11px] text-muted">{c.question}</p>
                <Picture c={c} t={t} start={start + 300} />
                <div className="x-in mt-2 flex items-center gap-1.5 text-xs font-semibold" style={at(start + 700, { color: TONE[s.tone] })}>
                  <span className="inline-block h-2 w-2 rounded-full" style={{ background: TONE[s.tone] }} />
                  {s.label}
                </div>
                {s.tone === "raised" &&
                  c.findings
                    .filter((f) => f.risk > 0)
                    .slice(0, 1)
                    .map((f) => (
                      <p key={f.code} className="x-in mt-1 text-[11px]" style={at(start + 800)}>
                        {f.text}
                      </p>
                    ))}
              </div>
            </div>
          );
        })}
      </div>
      <p className="x-in text-xs text-muted" style={at(300 + t.checks.length * CHECK_GAP)}>
        A check that cannot look (no papers or photos attached here) says so. &quot;Could not check&quot; is a status,
        never a low score: it adds nothing either way.
      </p>
    </div>
  );
}

// ---- step 5: adding up the score ------------------------------------------------------------

const CODE_LABEL: Record<string, string> = {
  COST_ABOVE_PEERS: "Costs far more than similar works",
  FUNDED_AGAIN_AFTER_COMPLETION: "Reads like a work already done",
  PRICED_AT_LIMIT: "Priced just under a limit, by an office that often does",
};

function findingLabel(t: Trace, code: string): string {
  if (CODE_LABEL[code]) return CODE_LABEL[code];
  const comp = t.checks.find((c) => c.id === "compliance");
  const rule = comp?.findings.find((f) => f.code === code)?.rule;
  const title = comp?.picture?.rules?.find((r) => r.id === rule)?.title;
  if (title) return title;
  const s = code.replace(/_/g, " ").toLowerCase();
  return s.charAt(0).toUpperCase() + s.slice(1);
}

function Bar({ label, v, color, start, note }: { label: string; v: number; color: string; start: number; note?: string }) {
  return (
    <div className="grid grid-cols-[92px_1fr_44px] items-center gap-2 text-[11px]">
      <span className="text-muted">{label}</span>
      <div className="h-3 rounded bg-background">
        <div className="x-grow-w h-full rounded" style={at(start, { "--w": `${Math.max(0, Math.min(1, v)) * 100}%`, background: color })} />
      </div>
      <span className="x-in text-right font-semibold" style={at(start + 500)}>
        {pct(v)}
      </span>
      {note && <span className="col-span-3 -mt-1 text-[10px] text-muted">{note}</span>}
    </div>
  );
}

export const SCORE_ROW = 1300;

/** Each engine's slice of the meter: from the score before it to the score after it. */
function slices(chain: Trace["scoring"]["chain"]) {
  return chain.map((c, n) => ({ ...c, n, from: n ? chain[n - 1].score : 0 }));
}

export function ScoreStep({ t }: { t: Trace }) {
  const s = t.scoring;
  const rows = s.engines.flatMap((e) => e.findings.map((f) => ({ e, f })));
  const meterStart = 400 + rows.length * SCORE_ROW;
  const segs = slices(s.chain);
  const floorSeg = s.floor && s.score > s.raw ? { from: s.raw, to: s.score } : null;
  const after = meterStart + segs.length * 1100 + (floorSeg ? 900 : 0);
  const critLine = s.lines.CRITICAL;
  const oneEngine = s.chain.length < 2;
  return (
    <div className="grid gap-6 md:grid-cols-[1fr_200px]">
      <div className="space-y-4">
        {rows.length ? (
          rows.map(({ e, f }, n) => {
            const meta = agentMeta(e.engine, e.name);
            const start = 400 + n * SCORE_ROW;
            const read = f.read
              ? `${f.read[0]} of ${f.read[1]} such questions, read by eye, were worth a look (counted cautiously: ${f.read[0]}+1 out of ${f.read[1]}+4)`
              : f.basis === "design"
                ? "set by design: not yet read by eye"
                : "a cautious starting value: not yet read by eye";
            return (
              <div key={`${e.engine}-${f.code}`} className="x-in space-y-1.5 rounded-xl border border-line bg-surface p-3" style={at(start - 200)}>
                <div className="text-sm">
                  <span className="font-semibold" style={{ color: meta.color }}>
                    {meta.name}:
                  </span>{" "}
                  {findingLabel(t, f.code)}
                </div>
                <Bar label="Right before" v={f.hit_rate} color="var(--inputs)" start={start} note={read} />
                <Bar
                  label="Strength"
                  v={f.strength}
                  color="var(--statistical)"
                  start={start + 350}
                  note="how strong this one is, against a typical question of its kind"
                />
                <Bar label="= Chance" v={f.chance} color={meta.color} start={start + 700} note={`${pct(f.hit_rate)} × ${pct(f.strength)}`} />
              </div>
            );
          })
        ) : (
          <p className="x-in rounded-xl border border-line bg-surface p-4 text-sm" style={at(300)}>
            No check raised a question that counts, so there is nothing to add up: the score stays at 0 and the band is
            Low.
          </p>
        )}
        <div className="space-y-1 text-xs">
          <p className="x-in text-muted" style={at(meterStart - 200)}>
            The chances combine as &quot;at least one of them is right&quot;:
          </p>
          {segs.map((c) => {
            const meta = agentMeta(c.engine);
            return (
              <p key={c.engine} className="x-in font-mono" style={at(meterStart + c.n * 1100)}>
                <span style={{ color: meta.color }}>+ {meta.name}</span>{" "}
                {c.n === 0
                  ? `${pct(c.chance)} = ${pct(c.score)}`
                  : `1 - (1 - ${pct(c.from)}) × (1 - ${pct(c.chance)}) = ${pct(c.score)}`}
              </p>
            );
          })}
          {floorSeg && (
            <p className="x-in" style={at(meterStart + segs.length * 1100)}>
              A serious rule sets the lowest band this work can have: the score is lifted to {pct(floorSeg.to)}.
            </p>
          )}
          <p className="x-in pt-1 text-sm" style={at(after)}>
            Score <b>{pct(s.score)}</b>: band{" "}
            <b style={{ color: BAND_COLOR[s.band] }}>{BAND_LABEL[s.band]}</b>.{" "}
            {s.band === "CRITICAL"
              ? "Two different checks agree, so it can be Critical."
              : s.score >= critLine && oneEngine
                ? "It is above the Critical line, but Critical needs two different checks to agree, so it stays High."
                : ""}
          </p>
        </div>
      </div>

      <div className="mx-auto flex gap-3">
        <div className="relative h-64 w-14 overflow-hidden rounded-lg border border-line bg-background">
          {segs.map((c) => (
            <div
              key={c.engine}
              className="x-grow-h absolute inset-x-0"
              style={at(meterStart + c.n * 1100, {
                bottom: pct(c.from, 2),
                "--h": pct(c.score - c.from, 2),
                background: agentMeta(c.engine).color,
              })}
            />
          ))}
          {floorSeg && (
            <div
              className="x-grow-h absolute inset-x-0"
              style={at(meterStart + segs.length * 1100, {
                bottom: pct(floorSeg.from, 2),
                "--h": pct(floorSeg.to - floorSeg.from, 2),
                background: BAND_COLOR[s.band],
              })}
            />
          )}
          {(["MEDIUM", "HIGH", "CRITICAL"] as const).map((k) => (
            <div
              key={k}
              className="absolute inset-x-0 border-t-2 border-dashed shadow-[0_1px_0_white]"
              style={{ bottom: pct(s.lines[k], 2), borderColor: BAND_COLOR[k] }}
            />
          ))}
        </div>
        <div className="relative h-64 w-24 text-[10px]">
          {(["MEDIUM", "HIGH", "CRITICAL"] as const).map((k) => (
            <div key={k} className="absolute left-0 translate-y-1/2 font-semibold" style={{ bottom: pct(s.lines[k], 2), color: BAND_COLOR[k] }}>
              {BAND_LABEL[k]} {pct(s.lines[k])}
            </div>
          ))}
          <div className="absolute bottom-0 left-0 translate-y-1/2 text-muted">0</div>
          {s.score > 0 && (
            <div
              className="x-in absolute left-0 translate-y-1/2 text-xs font-bold"
              style={at(after, { bottom: pct(s.score, 2) })}
            >
              ← {pct(s.score)}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ---- step 6: what the officer gets ----------------------------------------------------------

const COLOUR: Record<PreColour, { label: string; color: string }> = {
  GREEN: { label: "Green: no question found", color: "var(--low)" },
  AMBER: { label: "Amber: check before sanction", color: "var(--medium)" },
  RED: { label: "Red: needs checking before sanction", color: "var(--critical)" },
};

export function ResultStep({ t }: { t: Trace }) {
  const r = t.result;
  return (
    <div className="grid gap-5 md:grid-cols-[1fr_260px]">
      <div className="x-pop space-y-3 rounded-xl border-2 bg-surface p-4" style={at(200, { borderColor: BAND_COLOR[r.band] })}>
        <div className="flex flex-wrap items-center gap-3">
          <span className="inline-block origin-left scale-125">
            <BandBadge band={r.band} limited={r.limited} />
          </span>
          <span className="ml-4 text-sm text-muted">score {pct(r.score)}</span>
        </div>
        <p className="x-in text-sm font-medium" style={at(700)}>
          {r.in_queue
            ? "Goes into the review queue, ranked by how likely it is to need checking."
            : "Not in the review queue: only High and Critical works go there. It stays on record with its reasons."}
        </p>
        {r.colour && (
          <div className="x-in flex flex-wrap items-center gap-2 text-sm" style={at(1000)}>
            <span className="rounded-full px-3 py-1 font-semibold text-white" style={{ background: COLOUR[r.colour].color }}>
              Pre-sanction check: {COLOUR[r.colour].label}
            </span>
            <span className="text-muted">{r.advice}</span>
          </div>
        )}
        {r.reasons.length ? (
          <ol className="space-y-2">
            {r.reasons.map((x, n) => (
              <li key={n} className="x-in rounded-lg border border-line p-3 text-sm" style={at(1300 + n * 400)}>
                <div className="flex flex-wrap items-baseline gap-2">
                  <span className="font-semibold">
                    {n + 1}. {x.engine}
                  </span>
                  {x.chance != null && (
                    <span className="text-xs text-muted">
                      {pct(x.chance)} chance it is worth a look
                      {x.read ? ` (${x.read[0]} of ${x.read[1]} such questions read by eye were)` : ""}
                    </span>
                  )}
                </div>
                <p className="mt-1">{x.text}</p>
              </li>
            ))}
          </ol>
        ) : (
          <p className="x-in text-sm" style={at(1300)}>
            Nothing to look at first. That is not a clean chit: the papers and the site were not seen here.
          </p>
        )}
      </div>
      <div className="space-y-3 text-sm">
        <div className="x-in rounded-xl bg-navy p-4 text-white" style={at(2000)}>
          <div className="text-lg font-bold">DRISHTI never decides.</div>
          <p className="mt-1 text-white/85">
            It shows the officer where to look first and why. The officer checks the papers and the site, and decides.
          </p>
        </div>
        <p className="x-in text-xs text-muted" style={at(2400)}>
          On the live site, 1,459 of 2,09,993 works (0.69%) are in the review queue (re-assessed 2 Oct 2026).
        </p>
      </div>
    </div>
  );
}
