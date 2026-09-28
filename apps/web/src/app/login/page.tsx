"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { Button, Field, TextInput } from "@/components/kit";
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
    <main className="grid min-h-screen lg:grid-cols-2">
      {/* Brand panel */}
      <section className="hidden flex-col justify-between border-r-2 border-strong bg-strong p-10 text-white lg:flex">
        <Logo invert />
        <div className="max-w-md">
          <h1 className="text-4xl font-bold leading-tight tracking-tight">
            The AI-eye on every MPLADS rupee.
          </h1>
          <p className="mt-4 text-sm leading-relaxed text-white/70">
            DRISHTI checks every MPLADS work, ranks what an officer should verify first, and explains why — with the
            evidence and the guideline behind each flag. It flags; it never accuses.
          </p>
        </div>
        <div className="text-[11px] uppercase tracking-[0.14em] text-white/50">
          SIH 2026 · SIH26102 · Team NeuralNexus
        </div>
      </section>

      {/* Form panel */}
      <section className="flex items-center justify-center p-6">
        <div className="w-full max-w-sm">
          <div className="mb-6 lg:hidden">
            <Logo />
          </div>
          <div className="border-2 border-strong bg-surface">
            <div className="border-b-2 border-strong px-6 py-4">
              <h2 className="text-lg font-bold">Sign in</h2>
              <p className="mt-0.5 text-xs text-muted">Use the account you were given.</p>
            </div>
            <form onSubmit={submit} className="space-y-4 p-6">
              {sb ? (
                <>
                  <Field label="Email" htmlFor="email">
                    <TextInput
                      id="email"
                      type="email"
                      autoComplete="email"
                      required
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                    />
                  </Field>
                  <Field label="Password" htmlFor="password">
                    <TextInput
                      id="password"
                      type="password"
                      autoComplete="current-password"
                      required
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                    />
                  </Field>
                  {error && (
                    <p role="alert" className="border-l-2 border-high bg-high-bg px-3 py-2 text-sm text-high">
                      {error}
                    </p>
                  )}
                </>
              ) : (
                <p className="border border-line bg-surface-2 p-3 text-sm text-muted">
                  Local development mode: no sign-in needed.
                </p>
              )}
              <Button variant="primary" type="submit" disabled={busy} className="w-full">
                {busy ? "Signing in…" : "Sign in"}
              </Button>
            </form>
          </div>
        </div>
      </section>
    </main>
  );
}
