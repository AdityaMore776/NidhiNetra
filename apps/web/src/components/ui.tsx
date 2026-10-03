import Link from "next/link";
import type { ReactNode } from "react";
import type { Band } from "@/lib/api";
import { BANDS } from "@/lib/tokens";

/* ==========================================================================
   Surfaces
   ========================================================================== */

export function Panel({
  children,
  className = "",
  as: Tag = "section",
}: {
  children: ReactNode;
  className?: string;
  as?: "section" | "div" | "aside" | "article";
}) {
  return <Tag className={`card ${className}`}>{children}</Tag>;
}

/**
 * A panel with a heading row. `hint` and `actions` sit on the same line as the
 * title so a table's controls never drift away from it.
 */
export function PanelHeader({
  title,
  eyebrow,
  hint,
  actions,
  id,
}: {
  title: ReactNode;
  eyebrow?: string;
  hint?: ReactNode;
  actions?: ReactNode;
  id?: string;
}) {
  return (
    <header className="flex flex-wrap items-start gap-x-4 gap-y-2 border-b border-line px-4 py-3">
      <div className="min-w-0 flex-1">
        {eyebrow && <div className="eyebrow">{eyebrow}</div>}
        <h2 id={id} className="text-md font-semibold leading-snug">
          {title}
        </h2>
        {hint && <p className="mt-0.5 text-xs text-muted">{hint}</p>}
      </div>
      {actions && <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div>}
    </header>
  );
}

/* ==========================================================================
   Buttons
   ========================================================================== */

type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";

const BUTTON: Record<ButtonVariant, string> = {
  primary: "bg-navy text-white border-navy hover:bg-navy-hover",
  secondary: "bg-surface text-foreground border-line-strong hover:bg-sunken",
  ghost: "bg-transparent text-secondary border-transparent hover:bg-sunken",
  danger: "bg-surface text-high-ink border-high-edge hover:bg-high-tint",
};

export function Button({
  children,
  variant = "secondary",
  size = "md",
  className = "",
  ...rest
}: React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant;
  size?: "sm" | "md";
}) {
  const pad = size === "sm" ? "px-2.5 py-1 text-xs" : "px-3 py-1.5";
  return (
    <button
      type="button"
      {...rest}
      className={`inline-flex items-center justify-center gap-1.5 rounded border font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-45 ${BUTTON[variant]} ${pad} ${className}`}
    >
      {children}
    </button>
  );
}

/** A link that looks like a button, for navigation to another screen. */
export function ButtonLink({
  children,
  href,
  variant = "secondary",
  size = "md",
  className = "",
}: {
  children: ReactNode;
  href: string;
  variant?: ButtonVariant;
  size?: "sm" | "md";
  className?: string;
}) {
  const pad = size === "sm" ? "px-2.5 py-1 text-xs" : "px-3 py-1.5";
  return (
    <Link
      href={href}
      className={`inline-flex items-center justify-center gap-1.5 rounded border font-medium transition-colors ${BUTTON[variant]} ${pad} ${className}`}
    >
      {children}
    </Link>
  );
}

/* ==========================================================================
   Status, shown as word + glyph + colour (never colour alone)
   ========================================================================== */

/**
 * A work's risk band. Colour, a shape and a word all carry it, so the meaning
 * survives a monochrome print-out and a colour-blind reader.
 *
 * `help` adds the plain-language reading of what the band means.
 */
export function BandBadge({
  band,
  limited,
  help,
  size = "md",
}: {
  band: Band | null;
  limited?: boolean | null;
  help?: boolean;
  size?: "sm" | "md";
}) {
  if (!band) {
    return (
      <span
        className="inline-flex items-center gap-1 whitespace-nowrap rounded border px-1.5 py-0.5 text-xs"
        style={{ color: "var(--muted)", borderColor: "var(--line-strong)", background: "var(--sunken)" }}
      >
        <span aria-hidden>○</span> Not assessed
      </span>
    );
  }
  const s = BANDS[band];
  const label = help ? s.label : s.short;
  return (
    <span className="inline-flex items-center gap-1.5 whitespace-nowrap">
      <span
        className={`inline-flex items-center gap-1 rounded border font-semibold ${
          size === "sm" ? "px-1.5 py-px text-2xs" : "px-2 py-0.5 text-xs"
        }`}
        style={{ color: s.ink, background: s.tint, borderColor: s.edge }}
      >
        <span aria-hidden>{s.glyph}</span>
        {label}
        <span className="sr-only"> risk band</span>
      </span>
      {limited && band === "LOW" && (
        <span
          className="rounded border px-1.5 py-px text-2xs font-medium"
          style={{
            color: "var(--medium-ink)",
            background: "var(--medium-tint)",
            borderColor: "var(--medium-edge)",
          }}
          title="At least one check could not look at this work, so a low band is not a clean chit."
        >
          <span aria-hidden>◐</span> limited evidence
        </span>
      )}
    </span>
  );
}

const SOURCE: Record<string, { label: string; ink: string; tint: string; edge: string; glyph: string }> = {
  REAL: {
    label: "Real eSAKSHI record",
    ink: "var(--inputs)",
    tint: "#eaf4fd",
    edge: "#c5dff5",
    glyph: "▣",
  },
  SCENARIO: {
    label: "Demo scenario",
    ink: "var(--reuse)",
    tint: "#f2ecfd",
    edge: "#ddcefa",
    glyph: "◇",
  },
  LIVE: {
    label: "Live submission",
    ink: "var(--fusion)",
    tint: "#e7f7f6",
    edge: "#bfe9e7",
    glyph: "◆",
  },
};

export function SourceBadge({ source }: { source: string }) {
  const s = SOURCE[source] ?? {
    label: source,
    ink: "var(--muted)",
    tint: "var(--sunken)",
    edge: "var(--line-strong)",
    glyph: "○",
  };
  return (
    <span
      className="inline-flex items-center gap-1 rounded border px-1.5 py-0.5 text-2xs font-medium"
      style={{ color: s.ink, background: s.tint, borderColor: s.edge }}
    >
      <span aria-hidden>{s.glyph}</span>
      {s.label}
    </span>
  );
}

/** A small pill for any labelled state: lifecycle, alert state, office habit. */
export function Pill({
  children,
  ink = "var(--secondary)",
  tint = "var(--sunken)",
  edge = "var(--line-strong)",
  glyph,
  title,
}: {
  children: ReactNode;
  ink?: string;
  tint?: string;
  edge?: string;
  glyph?: string;
  title?: string;
}) {
  return (
    <span
      className="inline-flex items-center gap-1 whitespace-nowrap rounded border px-1.5 py-0.5 text-2xs font-medium"
      style={{ color: ink, background: tint, borderColor: edge }}
      title={title}
    >
      {glyph && <span aria-hidden>{glyph}</span>}
      {children}
    </span>
  );
}

/* ==========================================================================
   Metrics
   ========================================================================== */

/**
 * One measured number.
 *
 * `source` says where the figure comes from and `hint` says what it does not
 * mean, so a reader is never left guessing. `pending` keeps the box at its
 * final height while the number is on its way.
 */
export function Metric({
  label,
  value,
  sub,
  source,
  hint,
  tone,
  glyph,
  pending,
  href,
}: {
  label: string;
  value: ReactNode;
  sub?: ReactNode;
  source?: string;
  hint?: string;
  tone?: Band | "neutral";
  glyph?: string;
  pending?: boolean;
  /** when given, the whole tile opens this list, so the number is a doorway */
  href?: string;
}) {
  const ink =
    tone && tone !== "neutral" ? BANDS[tone].ink : tone === "neutral" ? "var(--muted)" : undefined;
  const body = (
    <>
      <div className="flex items-start gap-1.5">
        {glyph && (
          <span aria-hidden className="mt-px text-xs" style={{ color: ink ?? "var(--muted)" }}>
            {glyph}
          </span>
        )}
        <span className="text-xs font-medium text-secondary">{label}</span>
        {hint && (
          <span className="ml-auto inline-flex items-center gap-1" title={hint}>
            <InfoDot />
            <span className="sr-only">— {hint}</span>
          </span>
        )}
      </div>
      <div className="flex items-baseline gap-2">
        <span
          className={`tnum text-xl font-semibold leading-none ${pending ? "opacity-35" : ""}`}
          style={ink ? { color: ink } : undefined}
        >
          {value}
        </span>
        {sub && <span className="text-xs text-muted">{sub}</span>}
      </div>
      {source && <div className="text-2xs leading-tight text-muted">{source}</div>}
    </>
  );
  const className =
    "card-flat flex flex-col justify-between gap-1 px-3 py-2.5" +
    (href ? " transition-colors hover:bg-raised" : "");
  // A metric that links is one control, not a tile with a hidden hotspot in it.
  return href ? (
    <Link href={href} className={className} aria-label={`${label}: ${String(value)}. Open the list.`}>
      {body}
    </Link>
  ) : (
    <div className={className}>{body}</div>
  );
}

/** A "?" mark. The explanation beside it carries the words, for a screen reader
 *  as well as for a mouse; this mark itself is decorative. */
export function InfoDot() {
  return (
    <span
      aria-hidden
      className="grid h-3.5 w-3.5 place-items-center rounded-full border text-[9px] leading-none text-muted"
      style={{ borderColor: "var(--line-emphasis)" }}
    >
      ?
    </span>
  );
}

/* ==========================================================================
   Screen states — every panel can be loading, empty, denied or failed
   ========================================================================== */

export function Loading({ label = "Loading", rows = 3 }: { label?: string; rows?: number }) {
  return (
    <div className="px-4 py-4" role="status" aria-live="polite" aria-busy="true">
      <span className="sr-only">{label}…</span>
      <div className="space-y-2" aria-hidden>
        {Array.from({ length: rows }, (_, i) => (
          <div
            key={i}
            className="h-3 animate-pulse rounded bg-sunken"
            style={{ width: `${90 - i * 14}%`, animationDelay: `${i * 90}ms` }}
          />
        ))}
      </div>
    </div>
  );
}

export function Empty({
  title,
  body,
  action,
  glyph = "○",
}: {
  title: string;
  body?: ReactNode;
  action?: ReactNode;
  glyph?: string;
}) {
  return (
    <div className="flex flex-col items-center gap-2 px-6 py-10 text-center">
      <span aria-hidden className="text-lg text-line-emphasis">
        {glyph}
      </span>
      <p className="text-base font-medium">{title}</p>
      {body && <p className="max-w-md text-xs text-muted">{body}</p>}
      {action}
    </div>
  );
}

export function ErrorState({
  title = "Could not load this",
  body,
  message,
  onRetry,
}: {
  title?: string;
  /** the plain-language explanation, shown under the title */
  body?: string;
  /** the engine's own words; shown only when there is no better explanation */
  message?: string;
  onRetry?: () => void;
}) {
  return (
    <div className="px-4 py-4" role="alert">
      <div className="flex items-start gap-2.5">
        <span
          aria-hidden
          className="mt-px grid h-5 w-5 shrink-0 place-items-center rounded-full text-2xs font-bold"
          style={{ color: "var(--high-ink)", background: "var(--high-tint)", border: "1px solid var(--high-edge)" }}
        >
          !
        </span>
        <div className="min-w-0">
          <p className="text-base font-medium">{title}</p>
          <p className="mt-0.5 text-xs text-muted">
            {body ?? message ?? "The engine did not answer. Nothing is wrong with the works on screen."}
          </p>
          {onRetry && (
            <Button size="sm" className="mt-2" onClick={onRetry}>
              Try again
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}

export function Denied({ message }: { message?: string }) {
  return (
    <div className="px-4 py-4" role="alert">
      <div className="flex items-start gap-2.5">
        <span
          aria-hidden
          className="mt-px grid h-5 w-5 shrink-0 place-items-center rounded-full text-2xs font-bold"
          style={{ color: "var(--medium-ink)", background: "var(--medium-tint)", border: "1px solid var(--medium-edge)" }}
        >
          ⌂
        </span>
        <div>
          <p className="text-base font-medium">Not available to this account</p>
          <p className="mt-0.5 text-xs text-muted">
            {message ?? "Your role does not cover this. Ask the DRISHTI owner if you believe it should."}
          </p>
        </div>
      </div>
    </div>
  );
}

/* ==========================================================================
   Definition rows — the compact metadata blocks on detail pages
   ========================================================================== */

export function Fields({ items }: { items: { label: string; value: ReactNode; hint?: string }[] }) {
  return (
    <dl className="grid grid-cols-2 gap-x-5 gap-y-2.5 sm:grid-cols-3 lg:grid-cols-4">
      {items.map((f) => (
        <div key={f.label} className="min-w-0">
          <dt className="text-2xs font-medium uppercase tracking-wide text-muted">{f.label}</dt>
          <dd className="truncate text-base" title={typeof f.value === "string" ? f.value : f.hint}>
            {f.value === null || f.value === undefined || f.value === "" ? (
              <span className="text-muted">Not recorded</span>
            ) : (
              f.value
            )}
          </dd>
        </div>
      ))}
    </dl>
  );
}

/* ==========================================================================
   Prose
   ========================================================================== */

export function Note({
  children,
  tone = "info",
  title,
}: {
  children: ReactNode;
  tone?: "info" | "caution" | "quiet";
  title?: string;
}) {
  const map = {
    info: { ink: "var(--inputs)", tint: "#eaf4fd", edge: "#c5dff5" },
    caution: { ink: "var(--medium-ink)", tint: "var(--medium-tint)", edge: "var(--medium-edge)" },
    quiet: { ink: "var(--muted)", tint: "var(--sunken)", edge: "var(--line-strong)" },
  }[tone];
  return (
    <div
      className="rounded border px-3 py-2 text-xs leading-relaxed"
      style={{ color: map.ink, background: map.tint, borderColor: map.edge }}
    >
      {title && <div className="mb-0.5 font-semibold">{title}</div>}
      {children}
    </div>
  );
}
