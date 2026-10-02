"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Logo } from "@/components/Logo";
import { supabase } from "@/lib/supabase";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const sb = supabase();

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!sb) {
      router.push("/");
      return;
    }
    setBusy(true);
    setError(null);
    const { error } = await sb.auth.signInWithPassword({ email, password });
    setBusy(false);
    if (error) setError("That email and password did not match an account.");
    else router.push("/");
  }

  return (
    <main className="min-h-screen grid place-items-center p-6">
      <form onSubmit={submit} className="card w-full max-w-sm p-8 space-y-5">
        <Logo />
        <p className="text-sm text-muted">
          Evidence-based monitoring for MPLADS works. Sign in with the account you were given.
        </p>
        {sb ? (
          <>
            <label className="block text-sm">
              <span className="text-muted">Email</span>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="mt-1 w-full rounded-lg border border-line px-3 py-2 outline-none focus:border-inputs"
              />
            </label>
            <label className="block text-sm">
              <span className="text-muted">Password</span>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="mt-1 w-full rounded-lg border border-line px-3 py-2 outline-none focus:border-inputs"
              />
            </label>
            {error && <p className="text-sm text-high">{error}</p>}
          </>
        ) : (
          <p className="text-sm rounded-lg bg-background p-3">Local development mode: no sign-in needed.</p>
        )}
        <button
          disabled={busy}
          className="w-full rounded-lg bg-navy py-2.5 text-white font-medium disabled:opacity-60"
        >
          {busy ? "Signing in…" : "Sign in"}
        </button>
        <Link href="/explain" className="block text-center text-sm text-navy hover:underline">
          See what DRISHTI does with one work, step by step (no sign-in)
        </Link>
      </form>
    </main>
  );
}
