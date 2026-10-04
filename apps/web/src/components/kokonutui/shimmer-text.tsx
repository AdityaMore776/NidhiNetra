"use client";

/**
 * @author: @dorianbaffier
 * @description: Shimmer Text
 * @version: 1.0.0
 * @date: 2025-06-26
 * @license: MIT
 * @website: https://kokonutui.com
 * @github: https://github.com/kokonut-labs/kokonutui
 *
 * Adapted for NidhiNetra: brand gradient, inline (no wrapper padding), any element.
 */

import { motion } from "motion/react";
import { cn } from "@/lib/utils";

interface Text_01Props {
  text: string;
  className?: string;
}

export default function ShimmerText({ text, className }: Text_01Props) {
  return (
    <motion.span
      animate={{
        backgroundPosition: ["200% center", "-200% center"],
      }}
      className={cn(
        "inline-block bg-[length:200%_100%] bg-gradient-to-r from-brand-900 via-cyan to-brand-900 bg-clip-text text-transparent",
        className
      )}
      transition={{
        duration: 3.2,
        ease: "linear",
        repeat: Number.POSITIVE_INFINITY,
      }}
    >
      {text}
    </motion.span>
  );
}
