import { createBrowserClient } from "@supabase/ssr";
import type { SupabaseClient } from "@supabase/supabase-js";

let client: SupabaseClient | null = null;

/** The browser Supabase client, or null when running locally without Supabase (dev mode). */
export function supabase(): SupabaseClient | null {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  if (!url || !key) return null;
  if (!client) client = createBrowserClient(url, key);
  return client;
}

/** Dev mode: no Supabase configured, and a role named for local testing. */
export function devRole(): string | null {
  if (supabase()) return null;
  return process.env.NEXT_PUBLIC_DEV_ROLE ?? null;
}
