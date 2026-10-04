"use client";

/**
 * @author: @kokonutui
 * @description: AI Text Loading
 * @version: 1.0.0
 * @date: 2025-06-26
 * @license: MIT
 * @website: https://kokonutui.com
 * @github: https://github.com/kokonut-labs/kokonutui
 *
 * Adapted for NidhiNetra: brand gradient, sized by the caller, no outer padding.
 */

import { AnimatePresence, motion } from "motion/react";
import { useEffect, useState } from "react";
import { cn } from "@/lib/utils";

interface AITextLoadingProps {
  texts?: string[];
  className?: string;
  interval?: number;
}

export default function AITextLoading({
  texts = ["Loading…"],
  className,
  interval = 1500,
}: AITextLoadingProps) {
  const [currentTextIndex, setCurrentTextIndex] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentTextIndex((prevIndex) => (prevIndex + 1) % texts.length);
    }, interval);

    return () => clearInterval(timer);
  }, [interval, texts.length]);

  return (
    <div className="relative flex items-center justify-center">
      <AnimatePresence mode="wait">
        <motion.div
          animate={{
            opacity: 1,
            y: 0,
            backgroundPosition: ["200% center", "-200% center"],
          }}
          className={cn(
            "flex min-w-max justify-center whitespace-nowrap bg-[length:200%_100%] bg-gradient-to-r from-brand-900 via-brand-400 to-brand-900 bg-clip-text font-semibold text-base text-transparent",
            className
          )}
          exit={{ opacity: 0, y: -12 }}
          initial={{ opacity: 0, y: 12 }}
          key={currentTextIndex}
          transition={{
            opacity: { duration: 0.3 },
            y: { duration: 0.3 },
            backgroundPosition: {
              duration: 2.5,
              ease: "linear",
              repeat: Number.POSITIVE_INFINITY,
            },
          }}
        >
          {texts[currentTextIndex]}
        </motion.div>
      </AnimatePresence>
    </div>
  );
}
