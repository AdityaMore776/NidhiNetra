"use client";

import { motion } from "motion/react";
import { useId } from "react";
import { cn } from "@/lib/utils";

/**
 * A row of options with a sliding highlight (the active one). Used wherever a button switches what
 * the page shows (a view, a filter, a language), so it is drawn in the brand colour, not grey:
 * a tinted track and a filled blue pill on the chosen option (T165).
 */
export function Segmented<T extends string>({
  value,
  options,
  onChange,
  label,
  size = "md",
  className,
}: {
  value: T;
  options: { value: T; label: React.ReactNode; icon?: React.ReactNode; dot?: string; count?: number | null }[];
  onChange: (v: T) => void;
  /** a short word in front of the options, e.g. "View" */
  label?: React.ReactNode;
  size?: "sm" | "md";
  className?: string;
}) {
  const id = useId();
  return (
    <div
      className={cn(
        "inline-flex items-center gap-0.5 rounded-xl border border-brand-200 bg-brand-50 p-1 shadow-[inset_0_1px_2px_rgb(11_37_96/0.06)]",
        className,
      )}
      role="tablist"
    >
      {label && (
        <span className={cn("shrink-0 pl-2 pr-1 font-semibold uppercase tracking-wide text-brand-700", size === "sm" ? "text-[10px]" : "text-[11px]")}>
          {label}
        </span>
      )}
      {options.map((o) => {
        const active = o.value === value;
        return (
          <button
            key={o.value}
            type="button"
            role="tab"
            aria-selected={active}
            onClick={() => onChange(o.value)}
            className={cn(
              "relative flex flex-1 items-center justify-center gap-1.5 rounded-lg font-semibold transition-colors sm:flex-none [&_svg]:size-4 [&_svg]:shrink-0",
              size === "sm" ? "px-3 py-1.5 text-xs" : "px-3.5 py-1.5 text-sm",
              active ? "text-white" : "text-brand-800 hover:bg-brand-100 hover:text-brand-950",
            )}
          >
            {active && (
              <motion.span
                layoutId={`seg-${id}`}
                className="absolute inset-0 rounded-lg bg-brand-600 shadow-[0_1px_2px_rgb(11_37_96/0.2),0_6px_14px_-6px_rgb(10_102_194/0.6)]"
                transition={{ type: "spring", stiffness: 420, damping: 34 }}
              />
            )}
            {o.dot && <span className={cn("relative size-2 rounded-full", active && "ring-2 ring-white/80")} style={{ background: o.dot }} />}
            {o.icon && <span className="relative flex">{o.icon}</span>}
            <span className="relative">{o.label}</span>
            {o.count != null && (
              <span className={cn("num relative rounded-md px-1.5 text-[11px]", active ? "bg-white/20 text-white" : "bg-white text-brand-800")}>
                {o.count.toLocaleString("en-IN")}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}
