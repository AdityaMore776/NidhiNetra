"use client";

import type Lenis from "lenis";
import { usePathname } from "next/navigation";
import { createContext, useContext, useEffect, useRef, useState } from "react";

const LenisContext = createContext<Lenis | null>(null);

/** The page's Lenis instance (null before mount, on touch screens, or when the reader asked for reduced motion). */
export function useLenis(): Lenis | null {
  return useContext(LenisContext);
}

/**
 * Smooth, inertial page scrolling (Lenis), driven by GSAP's ticker so every ScrollTrigger
 * animation reads the same scroll position on the same frame. Elements that scroll on their own
 * (the map, tables, menus) carry `data-lenis-prevent` and keep native wheel behaviour.
 *
 * T143: it smooths the mouse wheel only, so a phone (no fine pointer) scrolls natively and never
 * downloads Lenis or GSAP; on a desktop both load after the page has painted.
 */
export function SmoothScroll({ children }: { children: React.ReactNode }) {
  const [lenis, setLenis] = useState<Lenis | null>(null);
  const path = usePathname();
  const first = useRef(true);
  const refresh = useRef<() => void>(() => {});

  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    if (!window.matchMedia("(pointer: fine)").matches) return;
    let stop = false;
    let cleanup = () => {};
    Promise.all([import("lenis"), import("gsap"), import("gsap/ScrollTrigger")]).then(([{ default: L }, { gsap }, { ScrollTrigger }]) => {
      if (stop) return;
      gsap.registerPlugin(ScrollTrigger);
      const l = new L({ lerp: 0.11, wheelMultiplier: 0.95, smoothWheel: true, anchors: true });
      l.on("scroll", ScrollTrigger.update);
      const tick = (time: number) => l.raf(time * 1000);
      gsap.ticker.add(tick);
      gsap.ticker.lagSmoothing(0);
      refresh.current = () => ScrollTrigger.refresh();
      setLenis(l);
      cleanup = () => {
        gsap.ticker.remove(tick);
        l.destroy();
        setLenis(null);
      };
    });
    return () => {
      stop = true;
      cleanup();
    };
  }, []);

  // a new page starts at its top, and its triggers measure the new layout
  useEffect(() => {
    if (first.current) {
      first.current = false;
      return;
    }
    lenis?.scrollTo(0, { immediate: true });
    const id = window.setTimeout(() => refresh.current(), 120);
    return () => window.clearTimeout(id);
  }, [path, lenis]);

  return <LenisContext.Provider value={lenis}>{children}</LenisContext.Provider>;
}
