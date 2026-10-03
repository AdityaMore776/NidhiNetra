"use client";

import { useEffect, useRef, useState } from "react";

/** Whether the element is (nearly) on screen, so a 3D scene can stop drawing when it is not. */
export function useOnScreen<T extends Element>(margin = "120px"): [React.RefObject<T | null>, boolean] {
  const ref = useRef<T>(null);
  const [on, setOn] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const io = new IntersectionObserver(([e]) => setOn(e.isIntersecting), { rootMargin: margin });
    io.observe(el);
    return () => io.disconnect();
  }, [margin]);
  return [ref, on];
}
