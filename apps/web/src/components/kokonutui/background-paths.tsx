"use client";

/**
 * @author: @dorianbaffier
 * @description: Background Paths
 * @version: 1.0.0
 * @date: 2025-06-26
 * @license: MIT
 * @website: https://kokonutui.com
 * @github: https://github.com/kokonut-labs/kokonutui
 *
 * Adapted for NidhiNetra: a background layer only (no title), the brand's navy-blue-teal
 * gradient, and ids from useId so server and browser render the same markup.
 */

import { motion } from "motion/react";
import { memo, useId, useMemo } from "react";
import { cn } from "@/lib/utils";

interface Point {
  x: number;
  y: number;
}

interface PathData {
  d: string;
  opacity: number;
  width: number;
}

function generateAestheticPath(index: number, position: number, type: "primary" | "secondary" | "accent"): string {
  const baseAmplitude = type === "primary" ? 150 : type === "secondary" ? 100 : 60;
  const phase = index * 0.2;
  const points: Point[] = [];
  const segments = type === "primary" ? 10 : type === "secondary" ? 8 : 6;

  const startX = 2400;
  const startY = 800;
  const endX = -2400;
  const endY = -800 + index * 25;

  for (let i = 0; i <= segments; i++) {
    const progress = i / segments;
    const eased = 1 - (1 - progress) ** 2;
    const baseX = startX + (endX - startX) * eased;
    const baseY = startY + (endY - startY) * eased;
    const amplitudeFactor = 1 - eased * 0.3;
    const wave1 = Math.sin(progress * Math.PI * 3 + phase) * (baseAmplitude * 0.7 * amplitudeFactor);
    const wave2 = Math.cos(progress * Math.PI * 4 + phase) * (baseAmplitude * 0.3 * amplitudeFactor);
    const wave3 = Math.sin(progress * Math.PI * 2 + phase) * (baseAmplitude * 0.2 * amplitudeFactor);
    points.push({ x: baseX * position, y: baseY + wave1 + wave2 + wave3 });
  }

  // rounded: Node and the browser disagree in the last digits of sin/cos, which would make the
  // server's markup differ from the client's (a hydration mismatch)
  const r = (v: number) => Math.round(v * 100) / 100;
  return points
    .map((point, i) => {
      if (i === 0) return `M ${r(point.x)} ${r(point.y)}`;
      const prev = points[i - 1];
      const tension = 0.4;
      const cp1x = prev.x + (point.x - prev.x) * tension;
      const cp2x = prev.x + (point.x - prev.x) * (1 - tension);
      return `C ${r(cp1x)} ${r(prev.y)}, ${r(cp2x)} ${r(point.y)}, ${r(point.x)} ${r(point.y)}`;
    })
    .join(" ");
}

const GROUPS = [
  { type: "primary" as const, n: 12, op: (i: number) => 0.15 + i * 0.02, w: (i: number) => 4 + i * 0.3, dy: -15, dur: 8, alpha: 1 },
  { type: "secondary" as const, n: 15, op: (i: number) => 0.12 + i * 0.015, w: (i: number) => 3 + i * 0.25, dy: -10, dur: 6, alpha: 0.8 },
  { type: "accent" as const, n: 10, op: (i: number) => 0.08 + i * 0.06, w: (i: number) => 2 + i * 0.2, dy: -5, dur: 4, alpha: 0.6 },
];

/** Slow, flowing brand-coloured lines. Put it in a `relative` parent; it fills it. */
export const FloatingPaths = memo(function FloatingPaths({
  position = 1,
  className,
  intensity = 1,
}: {
  position?: number;
  className?: string;
  intensity?: number;
}) {
  const gid = useId().replace(/:/g, "");
  const groups = useMemo(
    () =>
      GROUPS.map((g) => ({
        ...g,
        paths: Array.from({ length: g.n }, (_, i): PathData => ({
          d: generateAestheticPath(i, position, g.type),
          opacity: g.op(i),
          width: g.w(i),
        })),
      })),
    [position],
  );

  return (
    <div className={cn("pointer-events-none absolute inset-0 overflow-hidden", className)} style={{ opacity: intensity }}>
      <svg className="h-full w-full" fill="none" preserveAspectRatio="xMidYMid slice" viewBox="-2400 -800 4800 1600" aria-hidden>
        <defs>
          <linearGradient id={`nn-paths-${gid}`} x1="0%" x2="100%" y1="0%" y2="0%">
            <stop offset="0%" stopColor="rgba(11, 37, 96, 0.45)" />
            <stop offset="50%" stopColor="rgba(10, 102, 194, 0.42)" />
            <stop offset="100%" stopColor="rgba(10, 180, 168, 0.42)" />
          </linearGradient>
        </defs>
        {groups.map((g) => (
          <g key={g.type} style={{ opacity: g.alpha }}>
            {g.paths.map((p, i) => (
              <motion.path
                key={`${g.type}-${i}`}
                d={p.d}
                stroke={`url(#nn-paths-${gid})`}
                strokeLinecap="round"
                strokeWidth={p.width}
                style={{ opacity: p.opacity }}
                initial={{ pathLength: 0.2, opacity: 0 }}
                animate={{ pathLength: 1, opacity: p.opacity, y: [0, g.dy, 0] }}
                transition={{
                  pathLength: { duration: 2.4, ease: "easeInOut" },
                  opacity: { duration: 1 },
                  y: { duration: g.dur, repeat: Number.POSITIVE_INFINITY, ease: "easeInOut", repeatType: "reverse" },
                }}
              />
            ))}
          </g>
        ))}
      </svg>
    </div>
  );
});

export default FloatingPaths;
