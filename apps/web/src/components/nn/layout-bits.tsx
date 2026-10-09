"use client";

import { motion, useReducedMotion } from "motion/react";
import { CountUp } from "@/components/motion/reveal";
import { cn } from "@/lib/utils";

const EASE = [0.22, 1, 0.36, 1] as const;

/** Top of a page: an eyebrow, a heading that can carry one serif-italic accent, and a lead. */
export function PageHeader({
  eyebrow,
  title,
  accent,
  lead,
  actions,
  className,
}: {
  eyebrow?: string;
  title: string;
  accent?: string;
  lead?: React.ReactNode;
  actions?: React.ReactNode;
  className?: string;
}) {
  const reduce = useReducedMotion();
  return (
    <div className={cn("flex flex-wrap items-end justify-between gap-6", className)}>
      <div className="max-w-3xl">
        {eyebrow && (
          <motion.div
            initial={reduce ? false : { opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, ease: EASE }}
            className="eyebrow flex items-center gap-2"
          >
            <span className="tricolor-rule w-6 rounded-full" />
            {eyebrow}
          </motion.div>
        )}
        <motion.h1
          initial={reduce ? false : { opacity: 0, y: 14, filter: "blur(8px)" }}
          animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
          transition={{ duration: 0.7, ease: EASE, delay: 0.05 }}
          className="mt-3 text-3xl font-semibold tracking-[-0.035em] text-brand-950 sm:text-[2.6rem] sm:leading-[1.05]"
        >
          {title}
          {accent && (
            <>
              {" "}
              <span className="display italic text-brand-gradient pr-1">{accent}</span>
            </>
          )}
        </motion.h1>
        {lead && (
          <motion.p
            initial={reduce ? false : { opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, ease: EASE, delay: 0.15 }}
            className="mt-3 max-w-2xl text-[15px] leading-relaxed text-muted-foreground"
          >
            {lead}
          </motion.p>
        )}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  );
}

/** Heading inside a panel or above a block. */
export function SectionHeader({
  eyebrow,
  title,
  description,
  actions,
  className,
}: {
  eyebrow?: string;
  title: React.ReactNode;
  description?: React.ReactNode;
  actions?: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("flex flex-wrap items-start justify-between gap-3", className)}>
      {/* grows from 16rem: on a phone the actions wrap under the text instead of squeezing it (T143) */}
      <div className="min-w-0 flex-[1_1_16rem]">
        {eyebrow && <div className="eyebrow mb-1.5">{eyebrow}</div>}
        <h2 className="text-lg font-semibold tracking-[-0.02em] text-brand-950">{title}</h2>
        {description && <p className="mt-1 max-w-2xl text-[13px] leading-relaxed text-muted-foreground">{description}</p>}
      </div>
      {actions && <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div>}
    </div>
  );
}

/** A headline figure: label, a counted-up value, an optional note and a small icon. */
export function StatTile({
  label,
  value,
  format,
  note,
  icon,
  tone = "var(--brand-600)",
  className,
  children,
}: {
  label: string;
  value: number;
  format?: (v: number) => string;
  note?: React.ReactNode;
  icon?: React.ReactNode;
  tone?: string;
  className?: string;
  children?: React.ReactNode;
}) {
  return (
    <div className={cn("panel group relative overflow-hidden p-5 transition-shadow duration-300 hover:shadow-lift", className)}>
      <div
        className="pointer-events-none absolute -right-10 -top-10 size-36 rounded-full opacity-[0.09] blur-2xl transition-opacity duration-500 group-hover:opacity-20"
        style={{ background: tone }}
      />
      <div className="flex items-center justify-between">
        <span className="text-[13px] font-medium text-muted-foreground">{label}</span>
        {icon && (
          <span
            className="grid size-8 place-items-center rounded-lg"
            style={{ background: `color-mix(in srgb, ${tone} 10%, white)`, color: tone }}
          >
            {icon}
          </span>
        )}
      </div>
      <div className="mt-3 text-[2rem] font-semibold leading-none tracking-[-0.04em] text-brand-950">
        <CountUp value={value} format={format} />
      </div>
      {note && <div className="mt-2 text-xs text-muted-foreground">{note}</div>}
      {children}
    </div>
  );
}

export function Pill({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <span className={cn("inline-flex items-center gap-1.5 rounded-full border bg-white/80 px-3 py-1 text-xs font-medium text-muted-foreground backdrop-blur", className)}>
      {children}
    </span>
  );
}

export function LiveDot({ className }: { className?: string }) {
  return (
    <span className={cn("relative inline-flex size-2", className)}>
      <span className="absolute inline-flex size-full animate-ping rounded-full bg-low opacity-60" />
      <span className="relative inline-flex size-2 rounded-full bg-low" />
    </span>
  );
}
