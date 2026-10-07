import type { SupabaseClient } from "@supabase/supabase-js";

const URL_ = process.env.NEXT_PUBLIC_SUPABASE_URL;
const KEY = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

/** Whether this build signs staff in with Supabase (false locally without it: dev mode). */
export const SUPABASE_ON = Boolean(URL_ && KEY);

let client: Promise<SupabaseClient> | null = null;

/**
 * The browser Supabase client, or null when running locally without Supabase (dev mode). Its code
 * (about 66 KB compressed) loads on first use (T143), so a visitor who never signs in never
 * downloads it.
 */
export function supabase(): Promise<SupabaseClient | null> {
  if (!SUPABASE_ON) return Promise.resolve(null);
  client ??= import("@supabase/ssr").then(({ createBrowserClient }) => createBrowserClient(URL_!, KEY!));
  client.catch(() => {
    client = null;
  });
  return client;
}

/**
 * Whether this browser may hold a sign-in. @supabase/ssr keeps the session in cookies named
 * `sb-<project-ref>-auth-token` (split into `.0`, `.1` when long); without one there is no session
 * to read, so the client need not load.
 */
export function mayHaveSession(): boolean {
  return typeof document !== "undefined" && /(?:^|;\s*)sb-[^=;]*-auth-token/.test(document.cookie);
}

/** Dev mode: no Supabase configured, and a role named for local testing. */
export function devRole(): string | null {
  if (SUPABASE_ON) return null;
  return process.env.NEXT_PUBLIC_DEV_ROLE ?? null;
}
