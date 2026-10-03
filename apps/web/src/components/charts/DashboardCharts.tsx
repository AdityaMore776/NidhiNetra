"use client";

import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  LabelList,
  Pie,
  PieChart,
  Scatter,
  ScatterChart,
  Treemap,
  XAxis,
  YAxis,
  ZAxis,
} from "recharts";
import { ChartContainer, ChartTooltip, type ChartConfig } from "@/components/ui/chart";
import type { AgentSummary, Band, DistrictRow, Summary } from "@/lib/api";
import { agentMeta, BAND_COLOR, BAND_LABEL, count, inr } from "@/lib/format";
import { cn } from "@/lib/utils";

const INK = "#0b1530";
const INK_2 = "#5b6478";
const GRID = "#eef1f6";

function TipBox({ title, rows, foot }: { title: React.ReactNode; rows: [React.ReactNode, React.ReactNode][]; foot?: React.ReactNode }) {
  return (
    <div className="min-w-44 rounded-xl border bg-white/95 px-3 py-2.5 text-xs shadow-lift backdrop-blur">
      <div className="mb-1.5 font-semibold text-brand-950">{title}</div>
      <div className="grid grid-cols-[auto_auto] gap-x-4 gap-y-0.5">
        {rows.map(([k, v], i) => (
          <div key={i} className="contents">
            <span className="text-muted-foreground">{k}</span>
            <span className="num text-right font-semibold text-foreground">{v}</span>
          </div>
        ))}
      </div>
      {foot && <div className="mt-1.5 max-w-60 text-[11px] leading-snug text-muted-foreground">{foot}</div>}
    </div>
  );
}

/* ----------------------------------------------------------------- what the engines found */
export function EngineFindings({ agents }: { agents: AgentSummary[] }) {
  const data = agents
    .filter((a) => a.built)
    .map((a) => {
      const m = agentMeta(a.id, a.name, a.question);
      return { id: a.id, name: m.name, n: m.n, alerts: a.alerts, color: m.color, counted: (a.weight ?? 1) > 0, note: a.weight_note, question: a.question };
    })
    .sort((a, b) => b.alerts - a.alerts);
  const config = { alerts: { label: "Works with a finding" } } satisfies ChartConfig;
  return (
    <ChartContainer config={config} className="aspect-auto w-full" style={{ height: Math.max(220, data.length * 40 + 20) }}>
      <BarChart data={data} layout="vertical" margin={{ left: 4, right: 64, top: 4, bottom: 4 }} barCategoryGap={10}>
        <CartesianGrid horizontal={false} stroke={GRID} />
        <XAxis type="number" hide domain={[0, "dataMax"]} />
        <YAxis
          type="category"
          dataKey="name"
          width={168}
          tickLine={false}
          axisLine={false}
          tick={{ fill: INK, fontSize: 12 }}
        />
        <ChartTooltip
          cursor={{ fill: "rgb(10 102 194 / 0.05)" }}
          content={({ active, payload }) => {
            const d = payload?.[0]?.payload as (typeof data)[number] | undefined;
            if (!active || !d) return null;
            return (
              <TipBox
                title={
                  <span className="flex items-center gap-2">
                    <span className="size-2.5 rounded-sm" style={{ background: d.color }} />
                    {d.name}
                  </span>
                }
                rows={[["Works with a finding", count(d.alerts)]]}
                foot={d.note || d.question}
              />
            );
          }}
        />
        <Bar dataKey="alerts" radius={[0, 4, 4, 0]} maxBarSize={22} animationDuration={1200}>
          {data.map((d) => (
            <Cell key={d.id} fill={d.color} fillOpacity={d.counted ? 1 : 0.4} />
          ))}
          <LabelList dataKey="alerts" position="right" offset={8} formatter={(v: unknown) => count(Number(v))} style={{ fill: INK, fontSize: 12, fontWeight: 600 }} />
        </Bar>
      </BarChart>
    </ChartContainer>
  );
}

/* ----------------------------------------------------------------- risk mix (flagged works) */
export function RiskMix({ summary }: { summary: Summary }) {
  const flagged: Band[] = ["CRITICAL", "HIGH", "MEDIUM"];
  const data = flagged.map((b) => ({ band: b, label: BAND_LABEL[b], value: summary.bands[b] ?? 0, color: BAND_COLOR[b] }));
  const total = data.reduce((s, d) => s + d.value, 0);
  const [hover, setHover] = useState<number | null>(null);
  const focus = hover != null ? data[hover] : null;
  const config = Object.fromEntries(data.map((d) => [d.band, { label: d.label, color: d.color }])) satisfies ChartConfig;
  return (
    <div className="grid items-center gap-4 sm:grid-cols-[200px_1fr]">
      <div className="relative mx-auto size-[200px]">
        <ChartContainer config={config} className="aspect-square size-[200px]">
          <PieChart>
            <Pie
              data={data}
              dataKey="value"
              nameKey="label"
              innerRadius={68}
              outerRadius={94}
              paddingAngle={2}
              cornerRadius={4}
              stroke="#fff"
              strokeWidth={2}
              startAngle={90}
              endAngle={-270}
              onMouseEnter={(_, i) => setHover(i)}
              onMouseLeave={() => setHover(null)}
              animationDuration={1100}
            >
              {data.map((d, i) => (
                <Cell key={d.band} fill={d.color} opacity={hover == null || hover === i ? 1 : 0.35} style={{ transition: "opacity .2s" }} />
              ))}
            </Pie>
          </PieChart>
        </ChartContainer>
        <div className="pointer-events-none absolute inset-0 grid place-items-center text-center">
          <div>
            <div className="num text-[1.7rem] font-semibold leading-none tracking-[-0.04em] text-brand-950">{count(focus ? focus.value : total)}</div>
            <div className="mt-1 text-[11px] text-muted-foreground">{focus ? focus.label : "works flagged"}</div>
          </div>
        </div>
      </div>
      <ul className="space-y-2.5">
        {data.map((d, i) => (
          <li
            key={d.band}
            onMouseEnter={() => setHover(i)}
            onMouseLeave={() => setHover(null)}
            className={cn("rounded-xl border p-3 transition-colors", hover === i ? "border-brand-200 bg-brand-50/60" : "bg-white")}
          >
            <div className="flex items-center gap-2 text-sm">
              <span className="size-2.5 rounded-full" style={{ background: d.color }} />
              <span className="font-medium">{d.label}</span>
              <span className="num ml-auto font-semibold">{count(d.value)}</span>
            </div>
            <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-muted">
              <div className="h-full rounded-full" style={{ width: `${total ? (d.value / total) * 100 : 0}%`, background: d.color }} />
            </div>
            <div className="num mt-1 text-[11px] text-muted-foreground">
              {total ? ((d.value / total) * 100).toFixed(1) : 0}% of flagged · {((d.value / summary.works) * 100).toFixed(2)}% of all works
            </div>
          </li>
        ))}
        <li className="px-1 text-[11px] text-muted-foreground">
          The other <span className="num font-medium text-foreground">{count(summary.bands.LOW)}</span> works are Low. High and Critical make the review queue.
        </li>
      </ul>
    </div>
  );
}

/* ----------------------------------------------------------------- states */
export type StateRow = { state: string; works: number; review: number; amount: number; districts: number; share: number };

export function statesOf(rows: DistrictRow[]): StateRow[] {
  const m = new Map<string, StateRow>();
  for (const r of rows) {
    const s = m.get(r.state) ?? { state: r.state, works: 0, review: 0, amount: 0, districts: 0, share: 0 };
    s.works += r.works;
    s.review += r.review;
    s.amount += r.amount;
    s.districts += 1;
    m.set(r.state, s);
  }
  return [...m.values()].map((s) => ({ ...s, share: s.works ? s.review / s.works : 0 }));
}

export function StatesBar({ rows, top = 12 }: { rows: DistrictRow[]; top?: number }) {
  const data = useMemo(() => statesOf(rows).sort((a, b) => b.review - a.review).slice(0, top), [rows, top]);
  const config = { review: { label: "Works needing review", color: "var(--brand-600)" } } satisfies ChartConfig;
  return (
    <ChartContainer config={config} className="aspect-auto w-full" style={{ height: data.length * 30 + 20 }}>
      <BarChart data={data} layout="vertical" margin={{ left: 4, right: 52, top: 2, bottom: 2 }} barCategoryGap={7}>
        <CartesianGrid horizontal={false} stroke={GRID} />
        <XAxis type="number" hide />
        <YAxis type="category" dataKey="state" width={138} tickLine={false} axisLine={false} tick={{ fill: INK, fontSize: 12 }} />
        <ChartTooltip
          cursor={{ fill: "rgb(10 102 194 / 0.05)" }}
          content={({ active, payload }) => {
            const d = payload?.[0]?.payload as StateRow | undefined;
            if (!active || !d) return null;
            return (
              <TipBox
                title={d.state}
                rows={[
                  ["Need review", count(d.review)],
                  ["Works", count(d.works)],
                  ["Share", `${(d.share * 100).toFixed(2)}%`],
                  ["Money", inr(d.amount)],
                  ["Districts", count(d.districts)],
                ]}
              />
            );
          }}
        />
        <Bar dataKey="review" fill="var(--color-review)" radius={[0, 4, 4, 0]} maxBarSize={18} animationDuration={1100}>
          <LabelList dataKey="review" position="right" offset={8} formatter={(v: unknown) => count(Number(v))} style={{ fill: INK_2, fontSize: 11, fontWeight: 600 }} />
        </Bar>
      </BarChart>
    </ChartContainer>
  );
}

/* ----------------------------------------------------------------- districts: size vs share */
export function DistrictScatter({ rows }: { rows: DistrictRow[] }) {
  const router = useRouter();
  const data = useMemo(
    () => rows.filter((r) => r.works > 0).map((r) => ({ ...r, sharePct: +(r.share * 100).toFixed(3), flagged: r.review > 0 })),
    [rows],
  );
  // clean 1-3-10 ticks across the districts' range, padded by a step either side
  const { domain, ticks } = useMemo(() => {
    const ws = data.map((d) => d.works);
    const lo = Math.max(1, Math.min(...ws, 10));
    const hi = Math.max(...ws, 10);
    const steps = [1, 3, 10, 30, 100, 300, 1000, 3000, 10000, 30000];
    const from = [...steps].reverse().find((s) => s <= lo) ?? 1;
    const to = steps.find((s) => s >= hi) ?? hi;
    return { domain: [from, to] as [number, number], ticks: steps.filter((s) => s >= from && s <= to) };
  }, [data]);
  const config = { district: { label: "District", color: "var(--brand-600)" } } satisfies ChartConfig;
  return (
    <ChartContainer config={config} className="aspect-auto h-[300px] w-full">
      <ScatterChart margin={{ left: 0, right: 12, top: 8, bottom: 8 }}>
        <CartesianGrid stroke={GRID} />
        <XAxis
          type="number"
          dataKey="works"
          scale="log"
          domain={domain}
          ticks={ticks}
          allowDataOverflow
          tickLine={false}
          axisLine={{ stroke: GRID }}
          tick={{ fill: INK_2, fontSize: 11 }}
          tickFormatter={(v) => count(Number(v))}
          label={{ value: "Works in the district (log scale)", position: "insideBottom", offset: -4, fill: INK_2, fontSize: 11 }}
          height={40}
        />
        <YAxis
          type="number"
          dataKey="sharePct"
          tickLine={false}
          axisLine={false}
          tick={{ fill: INK_2, fontSize: 11 }}
          tickFormatter={(v) => `${v}%`}
          width={44}
        />
        <ZAxis type="number" dataKey="amount" range={[18, 320]} />
        <ChartTooltip
          cursor={{ strokeDasharray: "0", stroke: "#c9d9ee" }}
          content={({ active, payload }) => {
            const d = payload?.[0]?.payload as (typeof data)[number] | undefined;
            if (!active || !d) return null;
            return (
              <TipBox
                title={`${d.name}, ${d.state}`}
                rows={[
                  ["Works", count(d.works)],
                  ["Need review", count(d.review)],
                  ["Share", `${d.sharePct.toFixed(2)}%`],
                  ["Money", inr(d.amount)],
                ]}
                foot="Click to open its works"
              />
            );
          }}
        />
        <Scatter
          data={data}
          onClick={(d: { payload?: DistrictRow }) => d?.payload && router.push(`/works?district=${d.payload.district_lgd}`)}
          className="cursor-pointer"
          animationDuration={1200}
        >
          {data.map((d) => (
            <Cell
              key={d.district_lgd}
              fill={d.flagged ? "var(--brand-600)" : "#b6cde9"}
              fillOpacity={d.flagged ? 0.72 : 0.5}
              stroke="#fff"
              strokeWidth={1.5}
            />
          ))}
        </Scatter>
      </ScatterChart>
    </ChartContainer>
  );
}

/* ----------------------------------------------------------------- money by state (treemap) */
const SEQ = ["#e3f0fc", "#bcdcf7", "#7fb8ec", "#3a8fdc", "#0a66c2", "#12337f"];
function seq(t: number): string {
  return SEQ[Math.max(0, Math.min(SEQ.length - 1, Math.floor(t * SEQ.length)))];
}

type TreeNode = { name: string; size: number; share: number; review: number; works: number; t: number };

function TreeCell(props: { x?: number; y?: number; width?: number; height?: number; name?: string; t?: number; size?: number }) {
  const { x = 0, y = 0, width = 0, height = 0, name = "", t = 0, size = 0 } = props;
  if (width < 2 || height < 2) return null;
  const fill = seq(t);
  const dark = t > 0.5;
  return (
    <g>
      <rect x={x + 1} y={y + 1} width={width - 2} height={height - 2} rx={6} fill={fill} stroke="#fff" strokeWidth={2} />
      {width > 70 && height > 34 && (
        <>
          <text x={x + 9} y={y + 19} fontSize={12} fontWeight={600} fill={dark ? "#fff" : INK}>
            {name.length > width / 7.5 ? `${name.slice(0, Math.max(3, Math.floor(width / 7.5) - 1))}…` : name}
          </text>
          {height > 52 && (
            <text x={x + 9} y={y + 36} fontSize={11} fill={dark ? "rgba(255,255,255,.85)" : INK_2}>
              {inr(size)}
            </text>
          )}
        </>
      )}
    </g>
  );
}

export function MoneyTreemap({ rows }: { rows: DistrictRow[] }) {
  const data = useMemo<TreeNode[]>(() => {
    const st = statesOf(rows).filter((s) => s.amount > 0);
    const maxShare = Math.max(1e-9, ...st.map((s) => s.share));
    return st
      .sort((a, b) => b.amount - a.amount)
      .map((s) => ({ name: s.state, size: s.amount, share: s.share, review: s.review, works: s.works, t: s.share / maxShare }));
  }, [rows]);
  const config = { size: { label: "Money recommended" } } satisfies ChartConfig;
  return (
    <div>
      <ChartContainer config={config} className="aspect-auto h-[320px] w-full">
        <Treemap data={data} dataKey="size" nameKey="name" content={<TreeCell />} isAnimationActive animationDuration={900} aspectRatio={1.6}>
          <ChartTooltip
            content={({ active, payload }) => {
              const d = payload?.[0]?.payload as TreeNode | undefined;
              if (!active || !d) return null;
              return (
                <TipBox
                  title={d.name}
                  rows={[
                    ["Money", inr(d.size)],
                    ["Works", count(d.works)],
                    ["Need review", count(d.review)],
                    ["Share", `${(d.share * 100).toFixed(2)}%`],
                  ]}
                />
              );
            }}
          />
        </Treemap>
      </ChartContainer>
      <div className="mt-3 flex items-center gap-3 text-[11px] text-muted-foreground">
        <span>Area: money recommended · Colour: share needing review</span>
        <span className="ml-auto flex items-center gap-1.5">
          low
          <span className="h-2 w-28 rounded-full" style={{ background: `linear-gradient(90deg, ${SEQ.join(",")})` }} />
          high
        </span>
      </div>
    </div>
  );
}
