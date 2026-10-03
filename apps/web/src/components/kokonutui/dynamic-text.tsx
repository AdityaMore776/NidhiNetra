"use client";

/**
 * @author: @dorianbaffier
 * @description: Dynamic Text
 * @version: 1.0.0
 * @date: 2025-06-26
 * @license: MIT
 * @website: https://kokonutui.com
 * @github: https://github.com/kokonut-labs/kokonutui
 *
 * Adapted for NidhiNetra: greetings in India's languages, settling on the last one; brand dot;
 * sized by the caller.
 */

import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { useEffect, useState } from "react";
import { cn } from "@/lib/utils";

interface Greeting {
  text: string;
  language: string;
}

const GREETINGS: Greeting[] = [
  { text: "வணக்கம்", language: "Tamil" },
  { text: "নমস্কার", language: "Bengali" },
  { text: "నమస్కారం", language: "Telugu" },
  { text: "નમસ્તે", language: "Gujarati" },
  { text: "ನಮಸ್ಕಾರ", language: "Kannada" },
  { text: "നമസ്കാരം", language: "Malayalam" },
  { text: "ସ୍ୱାଗତ", language: "Odia" },
  { text: "ਜੀ ਆਇਆਂ ਨੂੰ", language: "Punjabi" },
  { text: "Welcome", language: "English" },
  { text: "नमस्ते", language: "Hindi" },
];

export default function DynamicText({ className, greetings = GREETINGS }: { className?: string; greetings?: Greeting[] }) {
  const reduce = useReducedMotion();
  const [currentIndex, setCurrentIndex] = useState(reduce ? greetings.length - 1 : 0);
  const done = currentIndex >= greetings.length - 1;

  useEffect(() => {
    if (done) return;
    const t = setTimeout(() => setCurrentIndex((i) => i + 1), 260);
    return () => clearTimeout(t);
  }, [currentIndex, done]);

  return (
    <span className={cn("relative inline-flex h-[1.4em] min-w-40 items-center overflow-visible", className)} aria-label={greetings[greetings.length - 1].text}>
      <AnimatePresence mode="popLayout">
        <motion.span
          key={currentIndex}
          aria-hidden
          className="absolute inline-flex items-center gap-2 whitespace-nowrap"
          initial={{ y: 18, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          exit={{ y: -40, opacity: 0 }}
          transition={{ duration: 0.2, ease: "easeOut" }}
        >
          <span className="size-2 rounded-full bg-gradient-to-br from-brand-600 to-teal" />
          {greetings[currentIndex].text}
        </motion.span>
      </AnimatePresence>
    </span>
  );
}
