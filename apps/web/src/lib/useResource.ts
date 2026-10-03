"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError } from "./api";

export type ResourceState<T> =
  | { status: "loading" }
  | { status: "ready"; data: T; loadedAt: number }
  | { status: "error"; error: ApiError }
  | { status: "forbidden"; error: ApiError };

/**
 * One data-fetching hook for every screen, so no page can hang on a bare
 * "Loading…": the four outcomes an officer can meet are all explicit.
 *
 *   loading   nothing has come back yet
 *   ready     data is here
 *   error     the call failed (network, 500) — offer a retry
 *   forbidden the engine said this account may not see it (401/403)
 *
 * A 401 is deliberately *not* a forbidden state: it means the session ended,
 * and the shell handles that by sending the user to sign in again.
 */
export function useResource<T>(
  load: (signal: AbortSignal) => Promise<T>,
  deps: readonly unknown[],
): ResourceState<T> & { reload: () => void } {
  const [state, setState] = useState<ResourceState<T>>({ status: "loading" });
  const [nonce, setNonce] = useState(0);
  const reload = useCallback(() => setNonce((n) => n + 1), []);
  // The loader closes over props; keeping it in a ref means a new function
  // identity on every render does not re-fetch.
  const loader = useRef(load);
  loader.current = load;

  useEffect(() => {
    const ac = new AbortController();
    let live = true;
    setState({ status: "loading" });
    loader.current(ac.signal)
      .then((data) => {
        if (live) setState({ status: "ready", data, loadedAt: Date.now() });
      })
      .catch((e: unknown) => {
        if (!live || ac.signal.aborted) return;
        const error =
          e instanceof ApiError
            ? e
            : new ApiError(0, e instanceof Error ? e.message : "Could not reach the engine.");
        // A signed-out session is not a permission problem; let the shell redirect.
        if (error.status === 401) setState({ status: "loading" });
        else setState({ status: error.status === 403 ? "forbidden" : "error", error });
      });
    return () => {
      live = false;
      ac.abort();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, nonce]);

  return { ...state, reload };
}

/** Convenience: the data if it has arrived, otherwise null. */
export function useData<T>(state: ResourceState<T>): T | null {
  return state.status === "ready" ? state.data : null;
}
