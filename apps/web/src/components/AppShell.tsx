"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import type { ReactNode } from "react";
import type { Me } from "@/lib/api";
import { supabase } from "@/lib/supabase";
import type { Role } from "@/lib/tokens";
import { Button, Pill } from "./ui";
import { SearchCommand } from "./SearchCommand";

/**
 * Navigation, grouped by what an officer is trying to do, not by which service
 * answers. Every entry is reachable by keyboard and announced as a list of
 * links; the current page carries `aria-current`.
 */
const NAV: { group: string; items: { href: string; label: string; glyph: string; roles?: Me["role"][] }[] }[] = [
  {
    group: "Review",
    items: [
      { href: "/", label: "Overview", glyph: "▤" },
      { href: "/alerts", label: "Alerts", glyph: "◎" },
      { href: "/queue", label: "Review queue", glyph: "☰" },
      { href: "/works", label: "All works", glyph: "⌗" },
    ],
  },
  {
    group: "Plan",
    items: [
      { href: "/inspections", label: "Inspection planner", glyph: "◈", roles: ["MINISTRY", "STATE", "DISTRICT"] },
      { href: "/presanction", label: "Pre-sanction check", glyph: "◇" },
    ],
  },
  {
    group: "Patterns",
    items: [
      { href: "/how-it-works", label: "How it works", glyph: "?" },
      { href: "/explain", label: "Step by step", glyph: "▷" },
    ],
  },
];

const ROLE_LABEL: Record<Role, string> = {
  MINISTRY: "Ministry",
  STATE: "State officer",
  DISTRICT: "District officer",
  FIELD: "Field officer",
};

const ROLE_SCOPE: Record<Role, string> = {
  MINISTRY: "All districts",
  STATE: "One state",
  DISTRICT: "One district",
  FIELD: "One district · field",
};

function isActive(path: string, href: string): boolean {
  return href === "/" ? path === "/" : path.startsWith(href);
}

export function AppShell({ me, children }: { me: Me; children: ReactNode }) {
  const path = usePathname();
  const router = useRouter();
  const [navOpen, setNavOpen] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);

  const openSearch = useCallback(() => setSearchOpen(true), []);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        openSearch();
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [openSearch]);

  async function signOut() {
    await supabase()?.auth.signOut();
    router.replace("/login");
  }

  const items = NAV.flatMap((g) =>
    g.items
      .filter((i) => !i.roles || i.roles.includes(me.role))
      .map((i) => ({ ...i, group: g.group })),
  );
  const groups = NAV.map((g) => g.group).filter((g) => items.some((i) => i.group === g));

  return (
    <div className="min-h-screen">
      <a href="#workspace" className="skip-link">
        Skip to main content
      </a>

      {/* ---------------- top bar ---------------- */}
      <header
        className="sticky top-0 z-30 border-b border-line bg-surface"
        style={{ height: "var(--topbar-height)" }}
      >
        <div className="flex h-full items-center gap-3 px-3">
          <button
            type="button"
            className="rounded border border-line-strong px-2 py-1 text-sm lg:hidden"
            aria-expanded={navOpen}
            aria-controls="primary-nav"
            onClick={() => setNavOpen((v) => !v)}
          >
            <span aria-hidden>{navOpen ? "✕" : "☰"}</span>
            <span className="sr-only">Menu</span>
          </button>

          <Link href="/" className="flex shrink-0 items-center gap-2">
            <span aria-hidden className="text-navy">
              <svg width="20" height="20" viewBox="0 0 32 32" aria-hidden focusable="false">
                <path d="M2 16 C8 6, 24 6, 30 16 C24 26, 8 26, 2 16 Z" fill="none" stroke="var(--navy)" strokeWidth="3" />
                <circle cx="16" cy="16" r="5" fill="var(--inputs)" />
              </svg>
            </span>
            <span className="leading-none">
              <span className="block text-sm font-bold tracking-wide text-navy">DRISHTI</span>
              <span className="hidden text-2xs text-muted sm:block">MPLADS work monitoring</span>
            </span>
          </Link>

          <button
            type="button"
            onClick={openSearch}
            className="ml-auto flex min-w-0 max-w-md flex-1 items-center gap-2 rounded border border-line-strong bg-sunken px-2.5 py-1.5 text-left text-xs text-muted hover:bg-canvas"
          >
            <span aria-hidden>⌕</span>
            <span className="truncate">Search works, districts, checks</span>
            <kbd className="ml-auto hidden rounded border border-line-strong bg-surface px-1 text-2xs text-muted sm:inline">
              Ctrl K
            </kbd>
          </button>

          <div className="flex shrink-0 items-center gap-2">
            <span className="hidden md:inline">
              <Pill glyph="◉" title={`Signed in as ${me.role}. ${ROLE_SCOPE[me.role]}.`}>
                {ROLE_LABEL[me.role]}
              </Pill>
            </span>
            <Button size="sm" variant="ghost" onClick={signOut}>
              Sign out
            </Button>
          </div>
        </div>
      </header>

      <div className="mx-auto flex w-full max-w-[var(--content-max)] gap-0">
        {/* ---------------- side navigation ---------------- */}
        <nav
          id="primary-nav"
          aria-label="Primary"
          className={`${
            navOpen ? "block" : "hidden"
          } w-full shrink-0 border-b border-line bg-surface p-2 lg:sticky lg:top-[var(--topbar-height)] lg:block lg:h-[calc(100vh-var(--topbar-height))] lg:w-[var(--sidebar-width)] lg:overflow-y-auto lg:border-b-0 lg:border-r lg:p-3`}
        >
          {groups.map((g) => (
            <div key={g} className="mb-4">
              <div className="eyebrow px-2 pb-1">{g}</div>
              <ul className="space-y-0.5">
                {items
                  .filter((i) => i.group === g)
                  .map((i) => {
                    const active = isActive(path, i.href);
                    return (
                      <li key={i.href}>
                        <Link
                          href={i.href}
                          onClick={() => setNavOpen(false)}
                          aria-current={active ? "page" : undefined}
                          className={`flex items-center gap-2 rounded px-2 py-1.5 text-xs transition-colors ${
                            active
                              ? "bg-navy text-white"
                              : "text-secondary hover:bg-sunken hover:text-foreground"
                          }`}
                        >
                          <span aria-hidden className="w-3.5 text-center">
                            {i.glyph}
                          </span>
                          {i.label}
                        </Link>
                      </li>
                    );
                  })}
              </ul>
            </div>
          ))}

          <div className="mt-6 border-t border-line px-2 pt-3">
            <div className="eyebrow pb-1">Data</div>
            <dl className="space-y-1 text-2xs text-muted">
              <div className="flex justify-between gap-2">
                <dt>Snapshot</dt>
                <dd className="tnum text-secondary">{me.snapshot_date ?? "—"}</dd>
              </div>
              <div className="flex justify-between gap-2">
                <dt>Scope</dt>
                <dd className="text-secondary">{ROLE_SCOPE[me.role]}</dd>
              </div>
            </dl>
            <p className="mt-3 border-t border-line pt-2 text-2xs leading-relaxed text-muted">
              DRISHTI flags works that need verification. It never decides; officers do.
            </p>
          </div>
        </nav>

        {/* ---------------- workspace ---------------- */}
        <main id="workspace" className="min-w-0 flex-1 px-3 py-4 sm:px-4 lg:px-5">
          {children}
        </main>
      </div>

      {searchOpen && <SearchCommand onClose={() => setSearchOpen(false)} />}
    </div>
  );
}
