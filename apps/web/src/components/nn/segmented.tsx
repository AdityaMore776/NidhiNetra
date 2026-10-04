"use client";

import { motion } from "motion/react";
import { useId } from "react";
import { cn } from "@/lib/utils";

/** A row of options with a sliding highlight (the active one). */
export function Segmented<T extends string>({
  value,
  options,
  onChange,
  className,
}: {
  value: T;
  options: { value: T; label: React.ReactNode; dot?: string; count?: number | null }[];
  onChange: (v: T) => void;
  className?: string;
}) {
  const id = useId();
  return (
    <div className={cn("inline-flex rounded-xl border bg-muted/70 p-1", className)} role="tablist">
      {options.map((o) => {
        const active = o.value === value;
        return (
          <button
            key={o.value}
            role="tab"
            aria-selected={active}
            onClick={() => onChange(o.value)}
            className={cn(
              "relative flex items-center gap-2 rounded-lg px-3.5 py-1.5 text-sm font-medium transition-colors",
              active ? "text-brand-950" : "text-muted-foreground hover:text-foreground",
            )}
          >
            {active && (
              <motion.span
                layoutId={`seg-${id}`}
                className="absolute inset-0 rounded-lg bg-white shadow-[0_1px_2px_rgb(11_37_96/0.08),0_4px_12px_-6px_rgb(11_37_96/0.25)] ring-1 ring-border"
                transition={{ type: "spring", stiffness: 420, damping: 34 }}
              />
            )}
            {o.dot && <span className="relative size-2 rounded-full" style={{ background: o.dot }} />}
            <span className="relative">{o.label}</span>
            {o.count != null && <span className="num relative rounded-md bg-white/70 px-1.5 text-[11px] text-muted-foreground">{o.count.toLocaleString("en-IN")}</span>}
          </button>
        );
      })}
    </div>
  );
}
