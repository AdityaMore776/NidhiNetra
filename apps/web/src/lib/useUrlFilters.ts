"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback } from "react";

/**
 * Filter state that lives in the address bar.
 *
 * An officer's queue is something they send to a colleague, come back to after a
 * meeting, and open on a phone with one hand. Anything chosen here is therefore a
 * URL: bookmarkable, shareable, and back-button-safe. Nothing is hidden in React
 * state where a refresh would lose it.
 */
export function useUrlFilters<T extends string>(defaults: Record<string, T | undefined>) {
  const params = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();

  // Read straight out of the query string on every render: it is a handful of keys,
  // and deriving it here means there is exactly one source of truth for a filter.
  const values: Record<string, string> = {};
  for (const key of Object.keys(defaults)) values[key] = params.get(key) ?? defaults[key] ?? "";

  /** Merge a patch into the address bar. Empty values remove the key entirely. */
  const set = useCallback(
    (patch: Record<string, string | number | undefined>, opts?: { resetPage?: boolean }) => {
      const next = new URLSearchParams(params.toString());
      for (const [k, v] of Object.entries(patch)) {
        if (v === undefined || v === "" || v === 0) next.delete(k);
        else next.set(k, String(v));
      }
      if (opts?.resetPage !== false) next.delete("page");
      const qs = next.toString();
      router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
    },
    [params, pathname, router],
  );

  const page = Math.max(1, Number(params.get("page") ?? "1") || 1);
  const setPage = useCallback((p: number) => set({ page: p }, { resetPage: false }), [set]);

  /** True when the officer has narrowed the list in any way. */
  const filtered = Object.entries(values).some(([k, v]) => v && v !== (defaults[k] ?? ""));
  const clear = useCallback(() => set(Object.keys(defaults).reduce<Record<string, string>>(
    (acc, k) => ({ ...acc, [k]: "", page: "" }),
    {},
  )), [defaults, set]);

  return { values, set, page, setPage, filtered, clear };
}

/** Count of active filters, for the "3 filters" chip. */
export function countActive(values: Record<string, string>, except: string[] = []): number {
  return Object.entries(values).filter(([k, v]) => v && !except.includes(k)).length;
}