export function Logo({ compact = false }: { compact?: boolean }) {
  return (
    <div className="flex items-center gap-2.5">
      <svg width="30" height="30" viewBox="0 0 32 32" aria-hidden>
        <path d="M2 16 C8 6, 24 6, 30 16 C24 26, 8 26, 2 16 Z" fill="none" stroke="var(--navy)" strokeWidth="2.4" />
        <circle cx="16" cy="16" r="5.5" fill="var(--inputs)" />
        <circle cx="16" cy="16" r="2.2" fill="var(--navy)" />
      </svg>
      <div className="leading-tight">
        <div className="font-bold tracking-wide text-navy">DRISHTI</div>
        {!compact && <div className="text-[11px] text-muted">Evidence-based monitoring for MPLADS</div>}
      </div>
    </div>
  );
}
