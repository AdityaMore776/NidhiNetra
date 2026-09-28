"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import {
  IconClose,
  IconDashboard,
  IconInfo,
  IconLogout,
  IconMap,
  IconMenu,
  IconQueue,
  IconReport,
  IconSettings,
  IconUser,
  IconWorks,
} from "@/components/icons";
import { Logo } from "@/components/Logo";
import { MeContext } from "@/components/me";
import { api, type Me } from "@/lib/api";
import { supabase } from "@/lib/supabase";

type NavItem = { href: string; label: string; icon: (p: { className?: string }) => React.ReactElement };

const NAV: NavItem[] = [
  { href: "/", label: "Dashboard", icon: IconDashboard },
  { href: "/queue", label: "Review Queue", icon: IconQueue },
  { href: "/works", label: "Works", icon: IconWorks },
  { href: "/districts", label: "Districts", icon: IconMap },
  { href: "/reports", label: "Reports", icon: IconReport },
  { href: "/how-it-works", label: "How it works", icon: IconInfo },
  { href: "/settings", label: "Settings", icon: IconSettings },
];

const ROLE_LABEL: Record<Me["role"], string> = {
  MINISTRY: "Ministry — all districts",
  DISTRICT: "District officer",
  FIELD: "Field officer",
};

function isActive(path: string, href: string) {
  return href === "/" ? path === "/" : path === href || path.startsWith(`${href}/`);
}

function NavList({ path, onNavigate }: { path: string; onNavigate?: () => void }) {
  return (
    <nav aria-label="Primary" className="flex flex-col p-2">
      {NAV.map((n) => {
        const active = isActive(path, n.href);
        const Icon = n.icon;
        return (
          <Link
            key={n.href}
            href={n.href}
            onClick={onNavigate}
            aria-current={active ? "page" : undefined}
            className={`mb-0.5 flex items-center gap-3 border px-3 py-2 text-sm font-semibold transition-colors ${
              active
                ? "border-strong bg-strong text-white"
                : "border-transparent text-muted hover:border-line hover:bg-surface-2 hover:text-foreground"
            }`}
          >
            <Icon className={active ? "text-white" : "text-faint"} />
            {n.label}
          </Link>
        );
      })}
    </nav>
  );
}

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const path = usePathname();
  const [me, setMe] = useState<Me | null>(null);
  const [failed, setFailed] = useState(false);
  const [drawer, setDrawer] = useState(false);

  useEffect(() => {
    api<Me>("/me")
      .then(setMe)
      .catch(() => {
        setFailed(true);
        router.replace("/login");
      });
  }, [router]);

  async function signOut() {
    await supabase()?.auth.signOut();
    router.replace("/login");
  }

  if (!me) {
    return (
      <div className="grid min-h-screen place-items-center text-sm text-muted">
        {failed ? "Redirecting to sign in…" : "Loading DRISHTI…"}
      </div>
    );
  }

  return (
    <MeContext.Provider value={me}>
      <div className="flex min-h-screen flex-col">
        {/* Top bar */}
        <header className="sticky top-0 z-30 border-b-2 border-strong bg-surface print:hidden">
          <div className="flex h-14 items-center gap-3 px-3 md:px-4">
            <button
              type="button"
              onClick={() => setDrawer(true)}
              aria-label="Open navigation menu"
              className="grid h-9 w-9 place-items-center border border-line text-foreground hover:bg-surface-2 md:hidden"
            >
              <IconMenu />
            </button>
            <Link href="/" aria-label="DRISHTI home">
              <Logo compact />
            </Link>
            <span className="label ml-2 hidden border-l border-line pl-3 lg:inline">Risk Intelligence System</span>
            <div className="ml-auto flex items-center gap-2">
              <span className="hidden items-center gap-2 border border-line px-2.5 py-1.5 text-xs font-semibold text-foreground sm:flex">
                <IconUser className="text-faint" width={15} height={15} />
                {ROLE_LABEL[me.role]}
              </span>
              <button
                type="button"
                onClick={signOut}
                className="flex items-center gap-1.5 border border-strong bg-surface px-2.5 py-1.5 text-xs font-semibold text-foreground hover:bg-surface-2"
              >
                <IconLogout width={15} height={15} />
                <span className="hidden sm:inline">Sign out</span>
              </button>
            </div>
          </div>
        </header>

        <div className="flex flex-1">
          {/* Desktop sidebar */}
          <aside className="sticky top-14 hidden h-[calc(100vh-3.5rem)] w-56 shrink-0 overflow-y-auto border-r border-line bg-surface md:block print:hidden">
            <NavList path={path} />
            <div className="mt-auto p-3">
              <p className="border-t border-line pt-3 text-[11px] leading-relaxed text-muted">
                Flags works that <strong className="text-foreground">need verification</strong>. It never decides — an
                officer does.
              </p>
            </div>
          </aside>

          {/* Main */}
          <main id="main" className="min-w-0 flex-1">
            <div className="mx-auto w-full max-w-[1760px] px-4 py-6 md:px-6 md:py-8">{children}</div>
            <footer className="mx-auto w-full max-w-[1760px] px-4 pb-8 md:px-6 print:hidden">
              <div className="border-t border-line pt-4 text-[11px] text-muted">
                DRISHTI · Risk-intelligence layer for MPLADS on eSAKSHI. Findings are leads for an officer to check, not
                rulings. SIH 2026 · SIH26102 · Team NeuralNexus.
              </div>
            </footer>
          </main>
        </div>
      </div>

      {/* Mobile drawer */}
      {drawer && (
        <div className="fixed inset-0 z-40 md:hidden">
          <button
            aria-label="Close navigation menu"
            className="absolute inset-0 bg-black/50"
            onClick={() => setDrawer(false)}
          />
          <div className="absolute left-0 top-0 flex h-full w-72 max-w-[85vw] flex-col border-r-2 border-strong bg-surface">
            <div className="flex h-14 items-center justify-between border-b-2 border-strong px-3">
              <Logo compact />
              <button
                type="button"
                onClick={() => setDrawer(false)}
                aria-label="Close navigation menu"
                className="grid h-9 w-9 place-items-center border border-line hover:bg-surface-2"
              >
                <IconClose />
              </button>
            </div>
            <div className="overflow-y-auto">
              <NavList path={path} onNavigate={() => setDrawer(false)} />
            </div>
            <div className="mt-auto border-t border-line p-3 text-xs text-muted">{ROLE_LABEL[me.role]}</div>
          </div>
        </div>
      )}
    </MeContext.Provider>
  );
}
