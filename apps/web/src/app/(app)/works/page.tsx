"use client";

import { Suspense, useEffect, useMemo, useState } from "react";
import { api, type DistrictRow } from "@/lib/api";
import { BAND_ORDER } from "@/lib/tokens";
import { BAND_LABEL } from "@/lib/format";
import { WORK_TYPES } from "@/lib/format";
import { WorkList, type ListOption } from "@/components/WorkList";
import { useUrlFilters } from "@/lib/useUrlFilters";

/**
 * Every work the engines have looked at, not only the queue.
 *
 * This is where an officer checks the denominator: a district with 40 works in the
 * queue is a different story from one with 40 works in total. The "couldn't check"
 * and "nothing attached" filters are here because they are the honest limits of
 * what the engines could see — never as a low risk.
 */
export default function WorksPage() {
  return (
    <Suspense fallback={null}>
      <Works />
    </Suspense>
  );
}

function Works() {
  const url = useUrlFilters({
    q: "",
    district: "",
    type: "",
    band: "",
    status: "",
    finding: "",
    assess: "",
    evidence: "",
  });
  const { values } = url;
  const [rows, setRows] = useState<DistrictRow[]>([]);

  useEffect(() => {
    api<DistrictRow[]>("/dashboard/districts").then(setRows).catch(() => setRows([]));
  }, []);

  const districts: ListOption[] = useMemo(
    () =>
      rows
        .slice()
        .sort((a, b) => b.works - a.works)
        .map((d) => ({ value: d.district_lgd, label: `${d.name} (${d.state})` })),
    [rows],
  );
  const one = rows.find((d) => d.district_lgd === values.district);

  return (
    <WorkList
      path="/works"
      url={url}
      title="All works"
      intro={
        one
          ? `Every work the engines looked at in ${one.name}, ${one.state}. ${one.works.toLocaleString("en-IN")} works in this district in total.`
          : "Every work the engines have looked at, in the area you are cleared to see."
      }
      searchPlaceholder="Search a village, a road, a work ID…"
      exportName="drishti-works"
      emptyTitle="No work matches these filters"
      emptyBody="Every filter is shown at the top of this page; clearing one widens the search. DRISHTI hides nothing it has assessed."
      options={{
        districts,
        types: Object.entries(WORK_TYPES).map(([value, label]) => ({ value, label })),
        bands: BAND_ORDER.map((b) => ({ value: b, label: BAND_LABEL[b] })),
        statuses: [
          { value: "RECOMMENDED", label: "Recommended" },
          { value: "SANCTIONED", label: "Sanctioned" },
          { value: "COMPLETED", label: "Completed" },
          { value: "GEO_TAGGED", label: "Geo-tagged" },
        ],
      }}
    />
  );
}