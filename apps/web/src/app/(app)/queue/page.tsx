"use client";

import { Suspense, useEffect, useState } from "react";
import { api, type DistrictRow } from "@/lib/api";
import { BAND_ORDER } from "@/lib/tokens";
import { BAND_LABEL } from "@/lib/format";
import { WorkList, type ListOption } from "@/components/WorkList";
import { useUrlFilters } from "@/lib/useUrlFilters";

/**
 * The review queue.
 *
 * One row per case, not per work: a purchase filed as eleven works is one question
 * for an officer (migration 012). The band is shown with a word as well as a colour,
 * and the filters all sit in the address bar so a queue can be sent to a colleague.
 */
export default function QueuePage() {
  return (
    <Suspense fallback={null}>
      <Queue />
    </Suspense>
  );
}

function Queue() {
  const url = useUrlFilters({ district: "", band: "", finding: "", assess: "", evidence: "" });
  const [districts, setDistricts] = useState<ListOption[]>([]);
  const [findings, setFindings] = useState<ListOption[]>([]);

  useEffect(() => {
    api<DistrictRow[]>("/dashboard/districts")
      .then((rows) =>
        setDistricts(
          rows
            .slice()
            .sort((a, b) => (b.review ?? 0) - (a.review ?? 0))
            .map((d) => ({ value: d.district_lgd, label: `${d.name} (${d.state})` })),
        ),
      )
      .catch(() => setDistricts([]));
    api<{ agent: string; code: string; text: string; name: string }[]>("/dashboard/findings")
      .then((rows) => {
        const seen = new Set<string>();
        setFindings(
          rows
            .filter((r) => (seen.has(r.code) ? false : (seen.add(r.code), true)))
            .map((r) => ({ value: r.code, label: `${r.name}: ${truncate(r.text, 60)}` })),
        );
      })
      .catch(() => setFindings([]));
  }, []);

  const { set } = url;
  const bands = BAND_ORDER.map((b) => ({ value: b, label: BAND_LABEL[b] }));

  return (
    <WorkList
      path="/queue"
      url={url}
      title="Review queue"
      intro="Works the engines agree need a look, highest money-at-stake first. Each row is one case: a purchase filed as several works is asked about once."
      exportName="drishti-review-queue"
      emptyTitle="Nothing in the queue with these filters"
      emptyBody="That is a real answer, not an error. Widen the filters, or read the All works tab to see everything the engines looked at."
      options={{
        districts,
        bands,
        findings,
      }}
      extraFilters={
        <button
          type="button"
          className="btn btn-sm"
          onClick={() => set({ band: "CRITICAL" })}
          title="Show only the works with at least two serious findings on them."
        >
          Only critical
        </button>
      }
    />
  );
}

function truncate(s: string, n: number): string {
  return s.length > n ? `${s.slice(0, n - 1)}…` : s;
}

