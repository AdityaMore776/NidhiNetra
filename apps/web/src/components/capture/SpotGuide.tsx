"use client";

// The same spot every month (T158, docs/plans/T158-same-spot-filming.md §B): a radar to the box a
// viewpoint was first filmed from, the turn to face the same way, and the arc to pan across.
// Guidance only: nothing here stops the person filming (the owner's choice); the engine reads the
// raw GPS and compass log and the pictures decide.

import type { Anchor, Facing } from "@/lib/api";
import { COVER_GOOD, FACING_TOL_DEG, toBox, turnBy, type GpsFix } from "@/lib/capture";

const COMPASS = ["north", "north-east", "east", "south-east", "south", "south-west", "west", "north-west"];

function compassWord(deg: number): string {
  return COMPASS[Math.round(deg / 45) % 8];
}

function sideWord(rel: number): string {
  const a = Math.abs(rel);
  const side = rel > 0 ? "right" : "left";
  if (a <= 25) return "ahead";
  if (a <= 70) return `ahead, to your ${side}`;
  if (a <= 110) return `to your ${side}`;
  if (a <= 155) return `behind you, to your ${side}`;
  return "behind you";
}

/** A point at `deg` (0 = up, clockwise) and radius r around (c, c). */
function at(c: number, r: number, deg: number): [number, number] {
  const a = (deg * Math.PI) / 180;
  return [c + r * Math.sin(a), c - r * Math.cos(a)];
}

function arcPath(c: number, r: number, from: number, width: number): string {
  const [x0, y0] = at(c, r, from);
  const [x1, y1] = at(c, r, from + width);
  return `M ${x0} ${y0} A ${r} ${r} 0 ${width > 180 ? 1 : 0} 1 ${x1} ${y1}`;
}

/** Where the box is from here: up is the way the phone faces (north without a compass). */
export function SpotRadar({
  id,
  anchor,
  fix,
  heading,
  weakAbove,
}: {
  id: string;
  anchor: Anchor;
  fix: GpsFix | null;
  heading: number | null;
  weakAbove: number;
}) {
  if (!fix) return <p className="text-xs text-muted-foreground">Waiting for GPS, to guide you to spot {id}…</p>;
  if (fix.accuracy > weakAbove)
    // a fix this poor would point the wrong way (found in the browser run: "150 m behind you")
    return (
      <p className="text-xs text-muted-foreground">
        GPS is too weak to guide you to spot {id} (±{Math.round(fix.accuracy)} m): line up the faint picture instead.
      </p>
    );
  const box = toBox(anchor, fix);
  const rel = heading === null ? box.bearing : turnBy(heading, box.bearing);
  const range = Math.max(30, box.metres * 1.3);
  const S = 132, C = S / 2, R = C - 10;
  const [x, y] = at(C, (Math.min(1, box.metres / range) * R), rel);
  const colour = box.inside ? "var(--low)" : "var(--medium)";
  return (
    <div className="flex items-center gap-3">
      <svg width={S} height={S} viewBox={`0 0 ${S} ${S}`} role="img" aria-label={`Spot ${id}`}>
        <circle cx={C} cy={C} r={R} fill="none" stroke="var(--border)" />
        <circle cx={C} cy={C} r={R / 2} fill="none" stroke="var(--border)" strokeDasharray="2 3" />
        <text x={C} y={8} textAnchor="middle" fontSize={9} fill="currentColor" opacity={0.6}>
          {heading === null ? "N" : "ahead"}
        </text>
        {!box.inside && <line x1={C} y1={C} x2={x} y2={y} stroke={colour} strokeDasharray="3 3" />}
        <circle cx={x} cy={y} r={Math.max(5, (anchor.box_m / range) * R)} fill={colour} fillOpacity={0.25} stroke={colour} />
        <circle cx={C} cy={C} r={4.5} fill="currentColor" />
      </svg>
      <div className="text-sm">
        <p className={box.inside ? "font-semibold text-low" : "font-semibold"}>
          {box.inside
            ? `You are in the box for spot ${id}.`
            : `Spot ${id}: ${Math.round(box.metres)} m ${heading === null ? compassWord(box.bearing) : sideWord(rel)}.`}
        </p>
        <p className="text-xs text-muted-foreground">
          GPS ±{Math.round(fix.accuracy)} m. The box is where this view was first filmed; the faint picture lines it up exactly.
        </p>
      </div>
    </div>
  );
}

/** Which way to turn, and how much of last time's arc has been panned across. */
export function FacingGuide({ facing, heading, covered }: { facing: Facing; heading: number | null; covered: number | null }) {
  if (heading === null)
    return (
      <p className="text-xs text-muted-foreground">
        No compass on this phone: line up the faint picture, then pan across the same view as last time.
      </p>
    );
  const turn = turnBy(heading, facing.mid);
  const inArc = turnBy(facing.from, heading) >= 0 && turnBy(facing.from, heading) <= facing.width;
  const right = Math.abs(turn) <= FACING_TOL_DEG || inArc;
  const S = 112, C = S / 2, R = C - 8;
  const share = covered ?? 0;
  return (
    <div className="flex items-center gap-3">
      <svg width={S} height={S} viewBox={`0 0 ${S} ${S}`} role="img" aria-label="Facing">
        <circle cx={C} cy={C} r={R} fill="none" stroke="var(--border)" strokeWidth={8} />
        <path
          d={facing.width >= 359 ? "" : arcPath(C, R, facing.from - heading, Math.max(facing.width, 4))}
          fill="none"
          stroke={share >= COVER_GOOD ? "var(--low)" : "#9aa3b2"}
          strokeWidth={8}
          strokeLinecap="round"
        />
        <line x1={C} y1={C} x2={C} y2={10} stroke="currentColor" strokeWidth={2.5} strokeLinecap="round" />
        <circle cx={C} cy={C} r={4} fill="currentColor" />
      </svg>
      <div className="text-sm">
        <p className={right ? "font-semibold text-low" : "font-semibold"}>
          {right
            ? "Facing the right way: pan slowly across the grey band, from one end to the other."
            : `Turn ${turn > 0 ? "right" : "left"} about ${Math.max(5, Math.round(Math.abs(turn) / 5) * 5)}°.`}
        </p>
        <p className={share >= COVER_GOOD ? "text-xs text-low" : "text-xs text-muted-foreground"}>
          Panned across {Math.round(share * 100)}% of last time&apos;s view.
        </p>
      </div>
    </div>
  );
}

/** Last time's three pictures across the pan, to show the same areas again. */
export function PanStrip({ urls }: { urls: string[] }) {
  if (!urls.length) return null;
  return (
    <div>
      <p className="mb-1 text-xs text-muted-foreground">Last time, from this spot (left, middle, right of the pan):</p>
      <div className="grid grid-cols-3 gap-1.5">
        {urls.map((u) => (
          // eslint-disable-next-line @next/next/no-img-element
          <img key={u} src={u} alt="" className="aspect-video w-full rounded-md object-cover" />
        ))}
      </div>
    </div>
  );
}
