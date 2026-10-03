"use client";

import { useEffect, useState } from "react";
import { api } from "./api";

type Params = Record<string, string | number | undefined>;

// One in-flight or recent answer per GET, so the shell and a page asking for the same thing share
// one request, and going back to a page shows its last answer at once. Kept for a minute.
const TTL_MS = 60_000;
const store = new Map<string, { at: number; p: Promise<unknown> }>();

function key(path: string, params?: Params): string {
  const q = Object.entries(params ?? {})
    .filter(([, v]) => v !== undefined && v !== "")
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([k, v]) => `${k}=${v}`)
    .join("&");
  return q ? `${path}?${q}` : path;
}

export function cachedApi<T>(path: string, params?: Params): Promise<T> {
  const k = key(path, params);
  const hit = store.get(k);
  if (hit && Date.now() - hit.at < TTL_MS) return hit.p as Promise<T>;
  const p = api<T>(path, params);
  store.set(k, { at: Date.now(), p });
  p.catch(() => store.delete(k));
  return p;
}

/** The answer for this path and params, or null while it loads. `error` is set if it failed. */
export function useApiData<T>(path: string | null, params?: Params): { data: T | null; error: Error | null; key: string } {
  const k = path ? key(path, params) : "";
  const [state, setState] = useState<{ key: string; data: T | null; error: Error | null }>({ key: "", data: null, error: null });

  useEffect(() => {
    if (!path) return;
    let live = true;
    cachedApi<T>(path, params)
      .then((data) => live && setState({ key: k, data, error: null }))
      .catch((error: Error) => live && setState({ key: k, data: null, error }));
    return () => {
      live = false;
    };
    // `k` carries path and params; a fresh params object each render must not refetch
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [k]);

  // an answer for an older query is never shown under a new one
  return state.key === k ? { data: state.data, error: state.error, key: k } : { data: null, error: null, key: k };
}
