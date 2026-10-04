"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { AgentCard } from "@/components/AgentCard";
import { FusionPanel } from "@/components/FusionPanel";
import { useMe } from "@/components/me";
import { SourceBadge } from "@/components/ui";
import { api, ApiError, type WorkDetail } from "@/lib/api";
import { inr, workType } from "@/lib/format";

export default function WorkPage() {
  return (
    <Suspense fallback={<p className="text-muted text-sm">Loading…</p>}>
      <Work />
    </Suspense>
  );
}

function Work() {
  const id = useSearchParams().get("id") ?? "";
  const me = useMe();
  const [d, setD] = useState<WorkDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    api<WorkDetail>(`/works/${id}`)
      .then(setD)
      .catch((e: ApiError) => setError(e.status === 404 ? "This work is not in your area, or does not exist." : e.message));
  }, [id]);

  if (error) return <p className="text-sm text-high">{error}</p>;
  if (!d) return <p className="text-muted text-sm">Loading…</p>;
  const w = d.work;
  const a = d.assessment;

  return (
    <div className="space-y-5">
      <div className="card p-5 space-y-3">
        <div className="flex flex-wrap items-center gap-2">
          <SourceBadge source={w.source} />
          <span className="text-xs text-muted">{w.work_id}</span>
        </div>
        <h1 className="text-xl font-bold">{workType(w.work_type_code)}</h1>
        <p className="text-sm">{w.description}</p>
        <dl className="grid grid-cols-2 md:grid-cols-4 gap-x-6 gap-y-2 text-sm">
          <Field label="Amount" value={inr(w.amount)} />
          <Field label="Status" value={w.status} />
          <Field label="District" value={`${w.district_name ?? "—"}, ${w.state_name ?? ""}`} />
          <Field label="Constituency" value={w.house === "Rajya Sabha" ? `Rajya Sabha (whole of ${w.state_name ?? "the state"})` : w.constituency} />
          <Field label="Recommended" value={w.recommended_date} />
          <Field label="Completed" value={w.completed_date} />
          <Field label="House" value={[w.house, w.term !== w.house ? w.term : null].filter(Boolean).join(" · ")} />
          <Field label="Implementing agency" value={w.agency_name} />
        </dl>
        {me && me.role !== "PUBLIC" && (
          <Link
            href={`/capture?work=${encodeURIComponent(w.work_id)}`}
            className="inline-block rounded-lg border border-line px-3 py-1.5 text-sm font-semibold"
          >
            Film a site visit
          </Link>
        )}
      </div>

      <FusionPanel a={a} />

      {a.validation.length > 0 && (
        <section className="card p-5 space-y-2">
          <h2 className="font-semibold text-sm">Data Validation</h2>
          <ul className="space-y-2 text-sm">
            {a.validation.map((i) => (
              <li key={i.code} className="flex gap-2">
                <span
                  className="mt-0.5 rounded px-1.5 text-[10px] font-bold text-white h-fit"
                  style={{ background: i.severity === "WARN" ? "var(--medium)" : "var(--inputs)" }}
                >
                  {i.severity === "WARN" ? "CHECK" : "NOTE"}
                </span>
                <span>{i.message}</span>
              </li>
            ))}
          </ul>
        </section>
      )}

      <div className="grid lg:grid-cols-2 gap-4">
        {a.agents.map((r) => (
          <AgentCard key={r.agent} result={r} />
        ))}
      </div>

      <p className="text-xs text-muted">
        Assessed {new Date(a.assessed_at).toLocaleString("en-IN")}. Officer decisions and the audit trail arrive with the review
        workflow (milestone 4).
      </p>
    </div>
  );
}

function Field({ label, value }: { label: string; value: string | null | undefined }) {
  return (
    <div>
      <dt className="text-xs text-muted">{label}</dt>
      <dd>{value || "—"}</dd>
    </div>
  );
}
