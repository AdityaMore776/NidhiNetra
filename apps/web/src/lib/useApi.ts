"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "./api";

export type ApiState<T> =
  | { status: "loading"; data: null; error: null }
  | { status: "ready"; data: T; error: null }
  | { status: "error"; data: null; error: unknown };

export type ApiResult<T> = ApiState<T> & {
  /** Re-run the same query, e.g. after an officer moved something. */
  reload: () => void;
  /** True while a newer query is on the way, so old rows are never shown under new filters. */
  refetching: boolean;
};

/**
 * One GET against the engine, with loading / ready / error as three explicit states.
 *
 * "Is it loading?" is answered by asking whether the answer on hand belongs to the
 * query now on screen, not by a second piece of state. That is what keeps a filter
 * change from leaving yesterday's rows under today's labels, and it keeps the
 * component free of the cascading render an extra setState would cause.
 */
export function useApi<T>(
  path: string,
  params?: Record<string, string | number | undefined>,
): ApiResult<T> {
  const [nonce, setNonce] = useState(0);
  const key = `${JSON.stringify([path, params ?? {}])}#${nonce}`;
  const [held, setHeld] = useState<{ key: string } & ApiState<T>>({
    key: "",
    status: "loading",
    data: null,
    error: null,
  });

  useEffect(() => {
    const ac = new AbortController();
    api<T>(path, params, ac.signal).then(
      (data) => {
        if (!ac.signal.aborted) setHeld({ key, status: "ready", data, error: null });
      },
      (error: unknown) => {
        if (!ac.signal.aborted) setHeld({ key, status: "error", data: null, error });
      },
    );
    return () => ac.abort();
    // `key` is built from the path, every parameter and the reload counter, so it
    // is a superset of the other two: depending on them as well would refetch on
    // every render, because callers pass their parameters as a fresh object.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);

  const reload = useCallback(() => setNonce((n) => n + 1), []);
  const settled = held.key === key;
  const state: ApiState<T> = settled
    ? (held as ApiState<T>)
    : { status: "loading", data: null, error: null };
  return {
    ...state,
    reload,
    refetching: !settled && held.status === "ready",
  };
}