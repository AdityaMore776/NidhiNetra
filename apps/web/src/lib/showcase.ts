import type { Band, DistrictRow, Me, Page, Summary, WorkDetail, WorkRow } from "./api";

/**
 * Prototype examples (T132, T142). The public view (no sign-in) shows example filings of the work
 * intelligence form instead of the engine's data: each one a form a made-up agency filed in a real
 * district, graded by the four checks (T142, the owner: "we are currently grading forms"; the
 * recommendations rated from their records alone are no longer shown). They are a static file
 * (public/showcase/examples.json, built by data/trial/showcase_examples.py from the form page's
 * filings), so the pages open without waiting for the engine. Each example's page shows its form
 * (components/nn/example-form). Signed-in staff still get every work from the engine.
 * NEXT_PUBLIC_SHOWCASE=0 turns it off.
 */
export const SHOWCASE_ON = process.env.NEXT_PUBLIC_SHOWCASE !== "0";

export interface ShowcaseMeta {
  n: number;
  key: string;
  title: string;
  /** the checks this example is about */
  agents: string[];
  shows: string;
  why: string;
  /** the Step by step page's example of the same made-up work */
  explain: string | null;
  /** T142: the work form filing it is (public/work-form/examples.json `id`) */
  form_example?: string;
  /** what happened after the form was filed (sanction, site videos) */
  later?: string[];
  form_ready?: boolean;
}

export type ShowcaseDetail = WorkDetail & { showcase?: ShowcaseMeta };

export interface ShowcaseExample {
  key: string;
  row: WorkRow;
  detail: ShowcaseDetail;
}

export interface ShowcaseFile {
  summary: Summary;
  /** the live engine's figures for every real work (T132 only; T142 shows filings, not records) */
  scale?: { works: number; amount: number; bands: Record<Band, number>; snapshot_date: string };
  examples: ShowcaseExample[];
}

/** Whether this viewer sees the prototype examples rather than the engine's data. */
export function isShowcase(me: Me | null | undefined): boolean {
  return SHOWCASE_ON && me?.role === "PUBLIC";
}

let file: Promise<ShowcaseFile> | null = null;

export function showcaseFile(): Promise<ShowcaseFile> {
  file ??= fetch("/showcase/examples.json").then((r) => (r.ok ? r.json() : Promise.reject(new Error(`examples ${r.status}`))));
  file.catch(() => {
    file = null;
  });
  return file;
}

export const NOT_FOUND = Symbol("not found");

const PUBLIC_ME: Me = { user_id: "public", role: "PUBLIC", district_lgd: null, name: "Public view" };
const PAGE = 25;

function page<T>(items: T[], n: number): Page<T> {
  return { total: items.length, page: n, page_size: PAGE, items: items.slice((n - 1) * PAGE, n * PAGE) };
}

function districts(f: ShowcaseFile): DistrictRow[] {
  const by = new Map<string, DistrictRow>();
  for (const { row } of f.examples) {
    if (!row.district_lgd) continue;
    const d = by.get(row.district_lgd) ?? { district_lgd: row.district_lgd, name: row.district_name ?? "", state: row.state_name ?? "", works: 0, amount: 0, review: 0, share: 0 };
    d.works += 1;
    d.amount += row.amount ?? 0;
    if (row.band === "HIGH" || row.band === "CRITICAL") d.review += 1;
    d.share = d.review / d.works;
    by.set(row.district_lgd, d);
  }
  return [...by.values()];
}

/**
 * The public view's answer to a GET, from the examples file: undefined when the engine must answer
 * (the pre-sanction options, the cost form catalogue), NOT_FOUND for a work that is not an example.
 */
export async function showcaseAnswer(path: string, params?: Record<string, string | number | undefined>): Promise<unknown> {
  if (path === "/me") return PUBLIC_ME;
  const routes = ["/dashboard/summary", "/dashboard/districts", "/dashboard/offices", "/dashboard/office-habits", "/queue", "/works"];
  if (!routes.includes(path) && !path.startsWith("/works/")) return undefined;
  const f = await showcaseFile();
  const n = Math.max(1, Number(params?.page ?? 1) || 1);
  const rows = f.examples.map((e) => e.row);
  switch (path) {
    case "/dashboard/summary":
      return f.summary;
    case "/dashboard/districts":
      return districts(f);
    case "/dashboard/offices":
    case "/dashboard/office-habits":
      return [];
    case "/queue": {
      const band = params?.band ? String(params.band) : null;
      const queue = rows.filter((r) => (r.band === "HIGH" || r.band === "CRITICAL") && (!band || r.band === band));
      return page([...queue].sort((a, b) => (b.priority ?? 0) - (a.priority ?? 0)), n);
    }
    case "/works": {
      const q = String(params?.q ?? "").toLowerCase();
      const hit = rows.filter(
        (r) =>
          (!q || (r.description ?? "").toLowerCase().includes(q) || r.work_id.toLowerCase().includes(q)) &&
          (!params?.type || r.work_type_code === params.type) &&
          (!params?.band || r.band === params.band) &&
          (!params?.district || r.district_lgd === params.district),
      );
      return page(hit, n);
    }
  }
  const id = decodeURIComponent(path.slice("/works/".length));
  return f.examples.find((e) => e.row.work_id === id)?.detail ?? NOT_FOUND;
}
