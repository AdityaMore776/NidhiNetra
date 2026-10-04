"use client";

import { gsap } from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import Lenis from "lenis";
import { usePathname } from "next/navigation";
import { createContext, useContext, useEffect, useRef, useState } from "react";

gsap.registerPlugin(ScrollTrigger);

const LenisContext = createContext<Lenis | null>(null);

/** The page's Lenis instance (null before mount, or when the reader asked for reduced motion). */
export function useLenis(): Lenis | null {
  return useContext(LenisContext);
}

/**
 * Smooth, inertial page scrolling (Lenis), driven by GSAP's ticker so every ScrollTrigger
 * animation reads the same scroll position on the same frame. Elements that scroll on their own
 * (the map, tables, menus) carry `data-lenis-prevent` and keep native wheel behaviour.
 */
export function SmoothScroll({ children }: { children: React.ReactNode }) {
  const [lenis, setLenis] = useState<Lenis | null>(null);
  const path = usePathname();
  const first = useRef(true);

  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const l = new Lenis({ lerp: 0.11, wheelMultiplier: 0.95, smoothWheel: true, anchors: true });
    l.on("scroll", ScrollTrigger.update);
    const tick = (time: number) => l.raf(time * 1000);
    gsap.ticker.add(tick);
    gsap.ticker.lagSmoothing(0);
    // eslint-disable-next-line react-hooks/set-state-in-effect -- Lenis needs the DOM; this publishes it once
    setLenis(l);
    return () => {
      gsap.ticker.remove(tick);
      l.destroy();
      setLenis(null);
    };
  }, []);

  // a new page starts at its top, and its triggers measure the new layout
  useEffect(() => {
    if (first.current) {
      first.current = false;
      return;
    }
    lenis?.scrollTo(0, { immediate: true });
    const id = window.setTimeout(() => ScrollTrigger.refresh(), 120);
    return () => window.clearTimeout(id);
  }, [path, lenis]);

  return <LenisContext.Provider value={lenis}>{children}</LenisContext.Provider>;
}
