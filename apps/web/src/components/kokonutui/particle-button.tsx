"use client";

/**
 * @author: @dorianbaffier
 * @description: Particle Button
 * @version: 1.0.0
 * @date: 2025-06-26
 * @license: MIT
 * @website: https://kokonutui.com
 * @github: https://github.com/kokonut-labs/kokonutui
 *
 * Adapted for NidhiNetra: the click still reaches the caller (so it can submit a form),
 * brand-coloured particles in fixed directions (no random values during render), no extra icon.
 */

import { AnimatePresence, motion } from "motion/react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

type ParticleButtonProps = React.ComponentProps<typeof Button> & {
  successDuration?: number;
};

const BURST = [
  { x: -46, y: -38, c: "var(--brand-600)" },
  { x: 40, y: -52, c: "var(--teal)" },
  { x: -24, y: -64, c: "var(--cyan)" },
  { x: 58, y: -26, c: "var(--brand-400)" },
  { x: -62, y: -14, c: "var(--saffron)" },
  { x: 18, y: -70, c: "var(--india-green)" },
  { x: 70, y: -48, c: "var(--brand-600)" },
  { x: -36, y: -58, c: "var(--teal)" },
];

function SuccessParticles({ centerX, centerY }: { centerX: number; centerY: number }) {
  return (
    <AnimatePresence>
      {BURST.map((p, i) => (
        <motion.div
          key={i}
          className="pointer-events-none fixed z-50 size-1.5 rounded-full"
          style={{ left: centerX, top: centerY, background: p.c }}
          initial={{ scale: 0, x: 0, y: 0 }}
          animate={{ scale: [0, 1.2, 0], x: [0, p.x], y: [0, p.y] }}
          transition={{ duration: 0.7, delay: i * 0.04, ease: "easeOut" }}
        />
      ))}
    </AnimatePresence>
  );
}

export default function ParticleButton({ children, onClick, successDuration = 900, className, ...props }: ParticleButtonProps) {
  // where the burst starts, taken from the button at the moment of the click
  const [origin, setOrigin] = useState<{ x: number; y: number } | null>(null);

  const handleClick = (e: React.MouseEvent<HTMLButtonElement>) => {
    const r = e.currentTarget.getBoundingClientRect();
    setOrigin({ x: r.left + r.width / 2, y: r.top + r.height / 2 });
    setTimeout(() => setOrigin(null), successDuration);
    onClick?.(e);
  };

  return (
    <>
      {origin && <SuccessParticles centerX={origin.x} centerY={origin.y} />}
      <Button
        className={cn("relative transition-transform duration-100 active:scale-[0.98]", className)}
        onClick={handleClick}
        {...props}
      >
        {children}
      </Button>
    </>
  );
}
