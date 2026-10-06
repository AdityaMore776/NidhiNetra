import Image from "next/image";
import { cn } from "@/lib/utils";

/**
 * The NidhiNetra mark: the emblem (Sansad dome over an eye, circuit traces) and the wordmark.
 * "Nidhi" (the fund) in navy, "Netra" (the eye) in the brand gradient; निधिनेत्र underneath.
 */
export function Logo({
  compact = false,
  size = 36,
  className,
  tagline = "The eye on every MPLADS rupee",
}: {
  compact?: boolean;
  size?: number;
  className?: string;
  tagline?: string | null;
}) {
  return (
    <div className={cn("flex items-center gap-2.5", className)}>
      <Emblem size={size} />
      <div className="leading-none">
        <div className="flex items-baseline gap-1.5">
          <span className="text-[1.05rem] font-semibold tracking-[-0.03em] text-brand-900">
            Nidhi<span className="text-brand-gradient">Netra</span>
          </span>
          {!compact && <span className="font-deva-label text-[11px] font-medium text-muted-foreground">निधिनेत्र</span>}
        </div>
        {!compact && tagline && <div className="mt-1 text-[11px] text-muted-foreground">{tagline}</div>}
      </div>
    </div>
  );
}

export function Emblem({ size = 36, className, priority = false }: { size?: number; className?: string; priority?: boolean }) {
  return (
    <Image
      src="/brand/nidhinetra-emblem-256.webp"
      alt="NidhiNetra"
      width={size}
      height={Math.round(size * 0.947)}
      priority={priority}
      className={cn("shrink-0 select-none", className)}
      draggable={false}
    />
  );
}
