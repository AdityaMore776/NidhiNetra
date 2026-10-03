"use client";

import { createContext, useContext } from "react";
import type { Me } from "@/lib/api";

/**
 * The signed-in principal, read once by the shell and shared with every screen.
 *
 * A null value means "not known yet"; the shell shows an access message rather
 * than rendering half a page, so no screen can quietly look like it has no data
 * when the truth is that the request failed.
 */
export const MeContext = createContext<Me | null>(null);

export function useMe(): Me | null {
  return useContext(MeContext);
}

/** Works for both roles: convenience overloads so pages read naturally. */
export function useIsMinistry(): boolean {
  return useMe()?.role === "MINISTRY";
}