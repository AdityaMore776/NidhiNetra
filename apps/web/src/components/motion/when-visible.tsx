"use client";

import { useEffect, useRef, useState } from "react";

/**
 * Mounts its children only once the box comes near the screen, and, with `idle`, once the page
 * has loaded and the browser is idle (T143). Heavy parts (the 3D scenes, the charts) then
 * download after the page's own text has painted, and on a phone not at all unless scrolled to.
 * Until then the box shows `fallback`, sized by `className`.
 */
export function WhenVisible({
  children,
  fallback = null,
  className,
  margin = "300px",
  idle = false,
}: {
  children: React.ReactNode;
  fallback?: React.ReactNode;
  className?: string;
  margin?: string;
  idle?: boolean;
}) {
  const box = useRef<HTMLDivElement>(null);
  const [show, setShow] = useState(false);

  useEffect(() => {
    const el = box.current;
    if (!el) return;
    let cancel = () => {};
    const mount = () => {
      if (!idle) return setShow(true);
      const later = () => {
        if ("requestIdleCallback" in window) {
          const id = window.requestIdleCallback(() => setShow(true), { timeout: 2000 });
          cancel = () => window.cancelIdleCallback(id);
        } else {
          const id = setTimeout(() => setShow(true), 300);
          cancel = () => clearTimeout(id);
        }
      };
      if (document.readyState === "complete") later();
      else {
        window.addEventListener("load", later, { once: true });
        cancel = () => window.removeEventListener("load", later);
      }
    };
    const io = new IntersectionObserver(
      (entries) => {
        if (entries.some((e) => e.isIntersecting)) {
          io.disconnect();
          mount();
        }
      },
      { rootMargin: margin },
    );
    io.observe(el);
    return () => {
      io.disconnect();
      cancel();
    };
  }, [idle, margin]);

  return (
    <div ref={box} className={className}>
      {show ? children : fallback}
    </div>
  );
}
