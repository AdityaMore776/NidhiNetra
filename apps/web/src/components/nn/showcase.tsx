"use client";

import { ArrowRight, Clapperboard, ClipboardList, FlaskConical, Lightbulb, LogIn } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { BandBadge, EngineMark, SourceBadge } from "@/components/nn/badges";
import { count, inr, workType } from "@/lib/format";
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
  const real = f?.examples.filter((e) => e.row.source === "REAL").length;
  return (
    <div className="border-b bg-brand-50/70">
      <div className="mx-auto flex w-full max-w-[1440px] flex-wrap items-center gap-x-3 gap-y-1 px-4 py-2 text-[12.5px] sm:px-6 lg:px-8">
        <FlaskConical className="size-3.5 shrink-0 text-brand-700" />
        <span className="text-brand-950">
          <b className="font-semibold">Prototype view:</b> {f ? f.examples.length : 10} worked examples of the four checks
          {f && real != null ? ` (${real} real eSAKSHI works, ${f.examples.length - real} made-up)` : ""}.
        </span>
        <span className="text-muted-foreground">
          The engine has assessed all {f ? count(f.scale.works) : "2,09,993"} real works; staff see them after signing in.
        </span>
        <Link href="/login" className="ml-auto inline-flex items-center gap-1 font-medium text-brand-700 hover:underline">
          <LogIn className="size-3.5" /> Staff sign in
        </Link>
      </div>
    </div>
  );
}

/** The ten examples as cards: what each one shows, and a way into its full page. */
export function ExampleGallery({ file }: { file: ShowcaseFile | null }) {
  if (!file)
    return (
      <div className="grid gap-4 md:grid-cols-2">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="h-52 rounded-2xl skeleton-shimmer" />
        ))}
      </div>
    );
  return (
    <ol className="grid gap-4 md:grid-cols-2">
      {file.examples.map(({ row, detail }) => {
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
                  See every check <ArrowRight className="size-3.5 transition-transform group-hover:translate-x-0.5" />
                </span>
              </div>
            </Link>
          </li>
        );
      })}
    </ol>
  );
}

/** Under the gallery: the example filings of the work intelligence form (T134). */
export function FormExamplesCard() {
  return (
    <Link
      href="/work-form"
      className="panel group flex flex-wrap items-center gap-3 p-5 transition-all hover:border-brand-200 hover:shadow-lift"
    >
      <ClipboardList className="size-5 shrink-0 text-brand-600" />
      <div className="min-w-0 flex-1">
        <h3 className="text-[15px] font-semibold text-brand-950">Twelve example filings of the work intelligence form</h3>
        <p className="mt-0.5 text-[13px] text-muted-foreground">
          Made-up agencies fill the form; each filing is caught by one of the four agents (one honest road passes all four). Load one into the
          form, or fill it yourself and check it.
        </p>
      </div>
      <span className="inline-flex items-center gap-1 text-xs font-medium text-brand-700">
        Open the form <ArrowRight className="size-3.5 transition-transform group-hover:translate-x-0.5" />
      </span>
    </Link>
  );
}

/** On a work's page: why this work is one of the examples. */
export function ExampleNote({ meta, source, district }: { meta: ShowcaseMeta; source: string; district: string | null }) {
  const madeUp = source === "SCENARIO";
  return (
    <section className={cn("panel relative overflow-hidden border-brand-200 p-5 sm:p-6")}>
      <div className="pointer-events-none absolute -left-16 -top-16 size-48 rounded-full bg-brand-gradient opacity-[0.08] blur-3xl" />
      <div className="flex flex-wrap items-center gap-2">
        <span className="eyebrow">Prototype example {meta.n} of 10</span>
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
          A made-up work{district ? <> placed in a real district ({district})</> : null}, with the cost estimate form or site videos that no real
          work has yet. It went through the same engines as every real work.
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
