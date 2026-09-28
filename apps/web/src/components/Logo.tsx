/** DRISHTI wordmark — a flat, sharp "eye" glyph in a square, no gradients. */
export function Logo({ compact = false, invert = false }: { compact?: boolean; invert?: boolean }) {
  const fg = invert ? "#ffffff" : "var(--foreground)";
  const box = invert ? "#ffffff" : "var(--foreground)";
  return (
    <div className="flex items-center gap-2.5">
      <svg width="30" height="30" viewBox="0 0 32 32" aria-hidden className="shrink-0">
        <rect x="1" y="1" width="30" height="30" fill="none" stroke={box} strokeWidth="2" />
        <path d="M5 16 C9 9, 23 9, 27 16 C23 23, 9 23, 5 16 Z" fill="none" stroke={fg} strokeWidth="2" />
        <rect x="13" y="13" width="6" height="6" fill={invert ? "#ffffff" : "var(--info)"} />
      </svg>
      <div className="leading-tight">
        <div className={`font-bold tracking-[0.12em] ${invert ? "text-white" : "text-foreground"}`}>DRISHTI</div>
        {!compact && (
          <div className={`text-[10px] uppercase tracking-[0.14em] ${invert ? "text-white/70" : "text-muted"}`}>
            Risk Intelligence System
          </div>
        )}
      </div>
    </div>
  );
}
