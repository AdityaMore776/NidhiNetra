"use client";

import { ArrowRight, Clapperboard, ClipboardList, FlaskConical, Lightbulb, LogIn } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { BandBadge, EngineMark, SourceBadge } from "@/components/nn/badges";
import { inr, workType } from "@/lib/format";
import { type ShowcaseFile, type ShowcaseMeta, showcaseFile } from "@/lib/showcase";
import { cn } from "@/lib/utils";

/** The examples file, or null while it loads (it is fetched once and shared). */
export function useShowcase(on = true): ShowcaseFile | null {
  const [f, setF] = useState<ShowcaseFile | null>(null);
  useEffect(() => {
    if (!on) return;
    let live = true;
    showcaseFile()
      .then((x) => live && setF(x))
      .catch(() => undefined);
    return () => {
      live = false;
    };
  }, [on]);
  return f;
}

/** One line above every page of the public view: what the visitor is looking at. */
export function ShowcaseBanner() {
  const f = useShowcase();
  return (
    <div className="border-b bg-brand-50/70">
      {/* T143: on a phone one or two short lines, not a third of the screen */}
      <div className="mx-auto flex w-full max-w-[1440px] items-start gap-x-3 px-4 py-2 text-[12px] leading-snug sm:items-center sm:px-6 sm:text-[12.5px] lg:px-8">
        <FlaskConical className="mt-0.5 size-3.5 shrink-0 text-brand-700 sm:mt-0" />
        <span className="min-w-0 flex-1 text-brand-950">
          <b className="font-semibold">Prototype view:</b> {f ? `${f.examples.length} example filings` : "Example filings"}
          <span className="hidden sm:inline"> of the work intelligence form</span>, each graded by the four checks.
          <span className="hidden text-muted-foreground sm:inline"> Made-up agencies, compared with a real district&apos;s eSAKSHI works.</span>
        </span>
        {/* prefetch off: few visitors sign in, and prefetching the sign-in page cost every phone ~50 KB (T143) */}
        <Link
          href="/login"
          prefetch={false}
          className="-my-1 ml-auto inline-flex shrink-0 items-center gap-1 py-1 font-medium text-brand-700 hover:underline"
        >
          <LogIn className="size-3.5" /> <span className="sm:hidden">Sign in</span>
          <span className="hidden sm:inline">Staff sign in</span>
        </Link>
      </div>
    </div>
  );
}

/** T170 (owner): honest works first, then the unusual ones, then the schemes, each group explained */
const KINDS: { kind: NonNullable<ShowcaseMeta["kind"]>; title: string; note: string }[] = [
  { kind: "normal", title: "Normal works", note: "Honest filings: every check reads them and none asks. Most filings look like these." },
  {
    kind: "edge",
    title: "Edge cases",
    note: "Honest but unusual: on some measure each looks like a problem. The checks notice, say why it is fine, and at most ask for a follow-up.",
  },
  { kind: "suspected", title: "Suspected", note: "Schemes an agency could try, each caught a different way, with the reason an officer is given." },
];

/** The example filings as cards, grouped: what each one shows, and a way into its form and full page. */
export function ExampleGallery({ file }: { file: ShowcaseFile | null }) {
  if (!file)
    return (
      <div className="grid gap-4 md:grid-cols-2">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="h-52 rounded-2xl skeleton-shimmer" />
        ))}
      </div>
    );
  const kindOf = (m: ShowcaseMeta) => m.kind ?? (m.key === "clean" ? "normal" : "suspected");
  return (
    <div className="space-y-8">
      {KINDS.map((g) => {
        const items = file.examples.filter(({ detail }) => kindOf(detail.showcase as ShowcaseMeta) === g.kind);
        if (!items.length) return null;
        return (
          <section key={g.kind} className="space-y-3" aria-label={g.title}>
            <div>
              <h3 className="text-base font-semibold text-brand-950">
                {g.title} <span className="num text-sm font-normal text-muted-foreground">({items.length})</span>
              </h3>
              <p className="text-[13px] text-muted-foreground">{g.note}</p>
            </div>
            <ExampleCards items={items} />
          </section>
        );
      })}
    </div>
  );
}

function ExampleCards({ items }: { items: ShowcaseFile["examples"] }) {
  return (
    <ol className="grid gap-4 md:grid-cols-2">
      {items.map(({ row, detail }) => {
        const m = detail.showcase as ShowcaseMeta;
        return (
          <li key={row.work_id}>
            <Link
              href={`/work?id=${encodeURIComponent(row.work_id)}`}
              className="panel group flex h-full flex-col gap-3 p-5 transition-all hover:-translate-y-0.5 hover:border-brand-200 hover:shadow-lift"
            >
              <div className="flex flex-wrap items-center gap-2">
                <span className="num grid size-7 place-items-center rounded-lg bg-brand-950 font-mono text-[11px] font-semibold text-white">
                  {String(m.n).padStart(2, "0")}
                </span>
                <SourceBadge source={row.source} />
                <BandBadge band={row.band} score={row.score} size="sm" className="ml-auto" />
              </div>
              <div>
                <h3 className="text-[15px] font-semibold leading-snug tracking-[-0.01em] text-brand-950">{m.title}</h3>
                <p className="mt-1 text-[11.5px] text-muted-foreground">
                  {workType(row.work_type_code)} · {row.district_name}, {row.state_name} · <span className="num">{inr(row.amount)}</span>
                </p>
              </div>
              <p className="text-[13px] leading-relaxed text-foreground/85">{m.shows}</p>
              <div className="mt-auto flex items-center gap-2 pt-1">
                {m.agents.map((a) => (
                  <EngineMark key={a} id={a} size={24} />
                ))}
                <span className="ml-auto inline-flex items-center gap-1 text-xs font-medium text-brand-700">
                  {m.form_example ? "See the form and every check" : "See every check"}{" "}
                  <ArrowRight className="size-3.5 transition-transform group-hover:translate-x-0.5" />
                </span>
              </div>
            </Link>
          </li>
        );
      })}
    </ol>
  );
}

/** Under the gallery: fill the work intelligence form yourself (T134). */
export function FormExamplesCard() {
  return (
    <Link
      href="/work-form"
      className="panel group flex flex-wrap items-center gap-3 p-5 transition-all hover:border-brand-200 hover:shadow-lift"
    >
      <ClipboardList className="size-5 shrink-0 text-brand-600" />
      <div className="min-w-0 flex-[1_1_14rem]">
        <h3 className="text-[15px] font-semibold text-brand-950">Fill the work intelligence form yourself</h3>
        <p className="mt-0.5 text-[13px] text-muted-foreground">
          Start from any example, change a field (a rate, a quantity, the map pin) and see what the four checks ask now.
        </p>
      </div>
      <span className="inline-flex items-center gap-1 text-xs font-medium text-brand-700">
        Open the form <ArrowRight className="size-3.5 transition-transform group-hover:translate-x-0.5" />
      </span>
    </Link>
  );
}

/** On a work's page: why this work is one of the examples. */
export function ExampleNote({ meta, source, district, total }: { meta: ShowcaseMeta; source: string; district: string | null; total?: number }) {
  const madeUp = source === "SCENARIO";
  return (
    <section className={cn("panel relative overflow-hidden border-brand-200 p-5 sm:p-6")}>
      <div className="pointer-events-none absolute -left-16 -top-16 size-48 rounded-full bg-brand-gradient opacity-[0.08] blur-3xl" />
      <div className="flex flex-wrap items-center gap-2">
        <span className="eyebrow">
          {meta.form_example ? "Example filing" : "Prototype example"} {meta.n}
          {total ? ` of ${total}` : ""}
        </span>
        <span className="flex gap-1.5">
          {meta.agents.map((a) => (
            <EngineMark key={a} id={a} size={22} />
          ))}
        </span>
      </div>
      <h2 className="mt-2 text-xl font-semibold tracking-[-0.02em] text-brand-950">{meta.title}</h2>
      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <div>
          <div className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">What it shows</div>
          <p className="mt-1 text-sm leading-relaxed">{meta.shows}</p>
        </div>
        <div className="rounded-xl bg-brand-50/70 p-3.5">
          <div className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wide text-brand-700">
            <Lightbulb className="size-3.5" /> Why it is a textbook case
          </div>
          <p className="mt-1 text-sm leading-relaxed">{meta.why}</p>
        </div>
      </div>
      {madeUp && (
        <p className="mt-4 text-[12.5px] leading-relaxed text-muted-foreground">
          {meta.form_example ? (
            <>
              A filing of the work intelligence form by a made-up agency{district ? <> in a real district ({district})</> : null}, graded by the same
              four checks as the live form check: its prices against what other agencies in the district pay, its map pin against the district&apos;s
              sanctioned works, its dates against its own promise, and its site videos.
            </>
          ) : (
            <>
              A made-up work{district ? <> placed in a real district ({district})</> : null}, with the cost estimate form or site videos that no real
              work has yet. It went through the same engines as every real work.
            </>
          )}
        </p>
      )}
      {meta.explain && (
        <Link
          href={`/explain?example=${meta.explain}`}
          className="mt-3 inline-flex items-center gap-1.5 text-sm font-medium text-brand-700 hover:underline"
        >
          <Clapperboard className="size-4" /> Watch it go through the checks, step by step
        </Link>
      )}
    </section>
  );
}
