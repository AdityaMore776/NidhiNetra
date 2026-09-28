"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { AgentCard } from "@/components/AgentCard";
import { FusionPanel } from "@/components/FusionPanel";
import { IconArrowRight } from "@/components/icons";
import { EmptyState, ErrorState, LoadingState, Panel, PanelHeader, StatusLabel } from "@/components/kit";
import { RiskScore } from "@/components/RiskScore";
import { SourceBadge } from "@/components/ui";
import { api, ApiError, type WorkDetail } from "@/lib/api";
import { inr, workType } from "@/lib/format";

export default function WorkPage() {
  return (
    <Suspense fallback={<LoadingState label="Loading work" />}>
      <WorkGate />
    </Suspense>
  );
}

function WorkGate() {
  const id = useSearchParams().get("id") ?? "";
  // Key by id so all per-work state resets cleanly when navigating between works.
  return <Work key={id} id={id} />;
}

function Work({ id }: { id: string }) {
  const [d, setD] = useState<WorkDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notFound, setNotFound] = useState(false);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    if (!id) return;
    let alive = true;
    api<WorkDetail>(`/works/${id}`)
      .then((r) => {
        if (alive) setD(r);
      })
      .catch((e: ApiError) => {
        if (!alive) return;
        if (e.status === 404) setNotFound(true);
        else setError(e.message);
      });
    return () => {
      alive = false;
    };
  }, [id, tick]);

  const reload = () => {
    setD(null);
    setError(null);
    setNotFound(false);
    setTick((t) => t + 1);
  };

  if (!id)
    return <EmptyState title="No work selected" message="Open a work from the queue or the works list." />;
  if (notFound)
    return (
      <EmptyState
        title="Work not found"
        message="This work is not in your area, or does not exist."
        action={
          <Link href="/works" className="text-sm font-semibold text-info underline-offset-2 hover:underline">
            Back to all works
          </Link>
        }
      />
    );
  if (error) return <ErrorState message={error} onRetry={reload} />;
  if (!d) return <LoadingState label="Loading assessment" />;

  const w = d.work;
  const a = d.assessment;

  const fields: { label: string; value: string | null | undefined }[] = [
    { label: "Work ID", value: w.work_id },
    { label: "Work type", value: workType(w.work_type_code) },
    { label: "Sanction amount", value: inr(w.amount) },
    { label: "Status", value: w.status },
    { label: "District", value: [w.district_name, w.state_name].filter(Boolean).join(", ") || null },
    {
      label: "Constituency",
      value:
        w.house === "Rajya Sabha" ? `Rajya Sabha (whole of ${w.state_name ?? "the state"})` : w.constituency,
    },
    { label: "House / term", value: [w.house, w.term !== w.house ? w.term : null].filter(Boolean).join(" · ") || null },
    { label: "Implementing agency", value: w.agency_name },
    { label: "Recommended", value: w.recommended_date },
    { label: "Completed", value: w.completed_date },
  ];

  return (
    <div className="space-y-6">
      {/* Breadcrumb + header */}
      <div>
        <nav aria-label="Breadcrumb" className="mb-3 flex items-center gap-1.5 text-xs text-muted">
          <Link href="/queue" className="hover:text-foreground hover:underline">
            Review queue
          </Link>
          <IconArrowRight width={12} height={12} />
          <span className="tnum text-foreground">{w.work_id}</span>
        </nav>
        <div className="flex flex-col gap-4 border-b-2 border-strong pb-5 lg:flex-row lg:items-start lg:justify-between">
          <div className="max-w-3xl">
            <div className="flex flex-wrap items-center gap-2">
              <SourceBadge source={w.source} />
              <span className="tnum text-xs text-muted">{w.work_id}</span>
            </div>
            <h1 className="mt-2 text-2xl font-bold tracking-tight md:text-3xl">{workType(w.work_type_code)}</h1>
            {w.description && <p className="mt-1.5 text-sm leading-relaxed text-muted">{w.description}</p>}
          </div>
          <div className="w-full max-w-xs lg:w-72">
            <RiskScore score={a.score} band={a.band} limited={a.limited} />
          </div>
        </div>
      </div>

      {/* Work information */}
      <Panel as="section">
        <PanelHeader title="Work information" />
        <dl className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4">
          {fields.map((f, i) => (
            <div
              key={f.label}
              className={`border-line p-4 ${i % 2 === 0 ? "sm:border-r" : ""} lg:border-r ${
                i < fields.length - 1 ? "border-b" : ""
              }`}
            >
              <dt className="label">{f.label}</dt>
              <dd className={`mt-1 text-sm ${f.label === "Work ID" ? "tnum" : ""}`}>{f.value || "—"}</dd>
            </div>
          ))}
        </dl>
      </Panel>

      {/* Risk breakdown */}
      <FusionPanel a={a} />

      {/* Data validation */}
      {a.validation.length > 0 && (
        <Panel as="section">
          <PanelHeader title="Data validation" desc="Record checks run before the agents" />
          <ul className="divide-y divide-line">
            {a.validation.map((i) => (
              <li key={i.code} className="flex items-start gap-3 p-4 text-sm">
                <StatusLabel tone={i.severity === "BLOCK" ? "high" : i.severity === "WARN" ? "medium" : "info"}>
                  {i.severity === "BLOCK" ? "Block" : i.severity === "WARN" ? "Check" : "Note"}
                </StatusLabel>
                <div>
                  <span>{i.message}</span>
                  {i.clause && <div className="mt-0.5 text-xs text-muted">Guideline: {i.clause}</div>}
                </div>
              </li>
            ))}
          </ul>
        </Panel>
      )}

      {/* Agent findings */}
      <section className="space-y-3">
        <h2 className="text-base font-semibold">Agent findings</h2>
        <div className="grid gap-4 lg:grid-cols-2">
          {a.agents.map((r) => (
            <AgentCard key={r.agent} result={r} />
          ))}
        </div>
      </section>

      <p className="border-t border-line pt-4 text-xs text-muted">
        Assessed {new Date(a.assessed_at).toLocaleString("en-IN")}. Officer decisions and the audit trail arrive with the
        review workflow (milestone 4).
      </p>
    </div>
  );
}
