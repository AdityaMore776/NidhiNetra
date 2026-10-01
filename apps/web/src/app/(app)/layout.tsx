"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Logo } from "@/components/Logo";
import { MeContext } from "@/components/me";
import { api, type Me } from "@/lib/api";
import { supabase } from "@/lib/supabase";

const NAV = [
  { href: "/", label: "Dashboard" },
  { href: "/queue", label: "Review queue" },
  { href: "/works", label: "All works" },
  { href: "/presanction", label: "Pre-sanction check" },
  { href: "/how-it-works", label: "How it works" },
];

const ROLE_LABEL: Record<Me["role"], string> = {
  MINISTRY: "Ministry (all districts)",
  DISTRICT: "District officer",
  FIELD: "Field officer",
};

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const path = usePathname();
  const [me, setMe] = useState<Me | null>(null);

  useEffect(() => {
    api<Me>("/me")
      .then(setMe)
      .catch(() => router.replace("/login"));
  }, [router]);

  async function signOut() {
    await supabase()?.auth.signOut();
    router.replace("/login");
  }

  if (!me) {
    return <div className="min-h-screen grid place-items-center text-muted text-sm">Loading…</div>;
  }

  return (
    <MeContext.Provider value={me}>
      <header className="bg-surface border-b border-line sticky top-0 z-20">
        <div className="mx-auto max-w-7xl px-4 h-14 flex items-center gap-6">
          <Link href="/">
            <Logo compact />
          </Link>
          <nav className="flex gap-1 text-sm overflow-x-auto">
            {NAV.map((n) => {
              const active = n.href === "/" ? path === "/" : path.startsWith(n.href);
              return (
                <Link
                  key={n.href}
                  href={n.href}
                  className={`px-3 py-1.5 rounded-lg whitespace-nowrap ${active ? "bg-navy text-white" : "text-muted hover:bg-background"}`}
                >
                  {n.label}
                </Link>
              );
            })}
          </nav>
          <div className="ml-auto flex items-center gap-3 text-xs text-muted">
            <span className="hidden sm:inline">{ROLE_LABEL[me.role]}</span>
            <button onClick={signOut} className="rounded-lg border border-line px-2.5 py-1 hover:bg-background">
              Sign out
            </button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-4 py-6">{children}</main>
      <footer className="mx-auto max-w-7xl px-4 pb-8 text-[11px] text-muted">
        DRISHTI flags works that need verification. It never decides; officers do. SIH 2026 · SIH26102 · Team
        NeuralNexus.
      </footer>
    </MeContext.Provider>
  );
}
