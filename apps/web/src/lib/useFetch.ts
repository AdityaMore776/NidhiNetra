"use client";

import { useCallback, useEffect, useState } from "react";
import { ApiError } from "./api";

/**
 * Fetch-in-effect helper. State is only ever set inside async callbacks (never
 * synchronously in the effect body), which keeps the strict react-hooks rules
 * happy while still giving loading / error / retry handling.
 *
 * `deps` are the primitive values the fetcher depends on (query params etc.).
 * On dependency change the resource refetches, keeping the previous data visible
 * until the new data arrives. `reload()` (for a Retry button) clears and refetches.
 */
export function useFetch<T>(fetcher: () => Promise<T>, deps: readonly unknown[]) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    let alive = true;
    fetcher()
      .then((d) => {
        if (alive) {
          setData(d);
          setError(null);
        }
      })
      .catch((e: unknown) => {
        if (alive) setError(e instanceof ApiError ? e.message : "The request could not be completed.");
      });
    return () => {
      alive = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, tick]);

  const reload = useCallback(() => {
    setData(null);
    setError(null);
    setTick((t) => t + 1);
  }, []);

  return { data, error, loading: data === null && error === null, reload };
}
