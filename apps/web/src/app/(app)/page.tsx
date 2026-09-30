"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { IndiaMap } from "@/components/IndiaMap";
import { WorkTable } from "@/components/ui";
import { api, type DistrictRow, type OfficeRow, type Page, type Summary, type WorkRow } from "@/lib/api";
import { agentMeta, BAND_COLOR, count, inr } from "@/lib/format";

export default function Dashboard() {
  const [s, setS] = useState<Summary | null>(null);
  const [districts, setDistricts] = useState<DistrictRow[]>([]);
  const [top, setTop] = useState<WorkRow[]>([]);
  const [offices, setOffices] = useState<OfficeRow[]>([]);

  useEffect(() => {
    api<Summary>("/dashboard/summary").then(setS);
    api<DistrictRow[]>("/dashboard/districts").then(setDistricts);
    api<Page<WorkRow>>("/queue").then((p) => setTop(p.items.slice(0, 8)));
    api<OfficeRow[]>("/dashboard/offices").then(setOffices);
  }, []);

  if (!s) return <p className="text-muted text-sm">Loading…</p>;
  const review = (s.bands.CRITICAL ?? 0) + s.bands.HIGH;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">MPLADS works monitored</h1>
        <p className="text-sm text-muted">
          Real works from the eSAKSHI public export (data up to {s.snapshot_date}). DRISHTI ranks which ones an officer should verify
          first. It flags, it never accuses.
        </p>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
        <Kpi label="Works" value={count(s.works)} />
        <Kpi label="Money recommended" value={inr(s.amount)} />
        <Kpi label="Need review" value={count(review)} sub={`${((review / s.works) * 100).toFixed(2)}% of works`} color="var(--medium)" />
        <Kpi label="Critical" value={count(s.bands.CRITICAL ?? 0)} color={BAND_COLOR.CRITICAL} />
        <Kpi label="Record issues found" value={count(s.validation_alerts)} color="var(--inputs)" />
      </div>

      <div className="grid lg:grid-cols-5 gap-3">
        {s.agents.map((a) => {
          const meta = agentMeta(a.id, a.name, a.question);
          return (
            <div key={a.id} className={`card p-4 ${a.built ? "" : "opacity-70"}`}>
              <div className="flex items-center gap-2">
                <span className="rounded-full w-7 h-7 grid place-items-center text-white text-[11px] font-bold" style={{ background: meta.color }}>
                  {meta.n}
                </span>
                <span className="font-semibold text-sm">{meta.name}</span>
              </div>
              <p className="mt-2 text-xs text-muted">{a.question}</p>
              <div className="mt-3 text-sm">
                {a.built ? (
                  <>
                    <span className="text-xl font-bold" style={{ color: meta.color }}>
                      {count(a.alerts)}
                    </span>{" "}
                    works with a finding
                    {a.weight_note && <p className="mt-1 text-[11px] text-muted">{a.weight_note}</p>}
                  </>
                ) : (
                  <span className="rounded-md bg-background px-2 py-1 text-xs text-muted">In development</span>
                )}
              </div>
            </div>
          );
        })}
      </div>

      <div className="grid lg:grid-cols-5 gap-6">
        <section className="card p-4 lg:col-span-3">
          <h2 className="font-semibold mb-3">Where the works needing review are</h2>
          {districts.length > 0 && <IndiaMap rows={districts} />}
          <p className="mt-2 text-xs text-muted">Click a district to see its works.</p>
        </section>
        <section className="card p-4 lg:col-span-2 space-y-3 text-sm">
          <h2 className="font-semibold">What the published data can and cannot tell us</h2>
          <p>
            The eSAKSHI export gives each work&apos;s type, description, amount, dates and district. That is enough for the guideline,
            price, duplicate and delay checks, which run on every work today.
          </p>
          <p>
            It carries <b>no GPS location, no quantities and no site photos</b>. Those are what the Site Progress, Photo Forensics and
            Geo-Location checks need. eSAKSHI already publishes them for completed works, so those checks are being built on real
            evidence. Without a location, two works can only be matched by their wording, so every repeat is &quot;check&quot;, never proof.
          </p>
          <p className="text-muted text-xs">
            A work reaches High only when two checks agree. A low score where a check could not look at the work is marked
            &quot;limited evidence&quot;: it is not a clean chit.
          </p>
        </section>
      </div>

      {offices.length > 0 && (
        <section className="card p-4 space-y-3">
          <div>
            <h2 className="font-semibold">Offices whose completion dates need checking</h2>
            <p className="text-xs text-muted">
              These offices record many works as completed before they were recommended. That is a record-keeping habit, so it is
              listed here once per office instead of filling the review queue work by work.
            </p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-muted border-b border-line">
                  <th className="py-2 pr-4 font-medium">Implementing office</th>
                  <th className="py-2 pr-4 font-medium">District</th>
                  <th className="py-2 pr-4 font-medium text-right">Works dated before recommendation</th>
                  <th className="py-2 font-medium text-right">vs national rate</th>
                </tr>
              </thead>
              <tbody>
                {offices.slice(0, 8).map((o) => (
                  <tr key={o.agency_name} className="border-b border-line last:border-0">
                    <td className="py-2 pr-4">{o.agency_name}</td>
                    <td className="py-2 pr-4 whitespace-nowrap">
                      {o.district_name}
                      <span className="text-xs text-muted">, {o.state_name}</span>
                    </td>
                    <td className="py-2 pr-4 text-right whitespace-nowrap">
                      {count(o.bad)} of {count(o.completed)} ({(o.rate * 100).toFixed(1)}%)
                    </td>
                    <td className="py-2 text-right font-semibold whitespace-nowrap" style={{ color: "var(--medium)" }}>
                      {o.lift.toFixed(0)}× higher
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {offices.length > 8 && <p className="text-xs text-muted">and {offices.length - 8} more offices.</p>}
        </section>
      )}

      <section className="space-y-3">
        <div className="flex items-end justify-between">
          <h2 className="font-semibold">Top of the review queue</h2>
          <Link href="/queue" className="text-sm text-navy hover:underline">
            Open the full queue →
          </Link>
        </div>
        <WorkTable items={top} />
      </section>
    </div>
  );
}

function Kpi({ label, value, sub, color }: { label: string; value: string; sub?: string; color?: string }) {
  return (
    <div className="card p-4">
      <div className="text-xs text-muted">{label}</div>
      <div className="text-2xl font-bold mt-1" style={color ? { color } : undefined}>
        {value}
      </div>
      {sub && <div className="text-[11px] text-muted">{sub}</div>}
    </div>
  );
}
