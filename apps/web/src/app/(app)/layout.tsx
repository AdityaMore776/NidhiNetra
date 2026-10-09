"use client";

import { motion } from "motion/react";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import AITextLoading from "@/components/kokonutui/ai-text-loading";
import { Emblem } from "@/components/Logo";
import { MeContext } from "@/components/me";
import { ShowcaseBanner } from "@/components/nn/showcase";
import { AppSidebar } from "@/components/shell/AppSidebar";
import { Topbar } from "@/components/shell/Topbar";
import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar";
import { api, type Me, type Summary } from "@/lib/api";
import { cachedApi } from "@/lib/cache";
import { isShowcase } from "@/lib/showcase";
import { supabase } from "@/lib/supabase";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const path = usePathname();
  const [me, setMe] = useState<Me | null>(null);
  const [summary, setSummary] = useState<Summary | null>(null);

  // Open to view (T130): no sign-in needed. The engine answers a visitor as the public viewer;
  // if it can't be reached the pages still render and show their own errors.
  useEffect(() => {
    api<Me>("/me")
      .then(setMe)
      .catch(() => setMe({ user_id: "public", role: "PUBLIC", district_lgd: null, name: null }));
  }, []);

  useEffect(() => {
    if (!me) return;
    cachedApi<Summary>("/dashboard/summary")
      .then(setSummary)
      .catch(() => setSummary(null));
  }, [me]);

  async function signOut() {
    await (await supabase())?.auth.signOut();
    router.replace("/");
    window.location.reload();
  }

  if (!me) return <ShellLoading />;
  const review = summary ? (summary.bands.CRITICAL ?? 0) + summary.bands.HIGH : null;

  return (
    <MeContext.Provider value={me}>
      <SidebarProvider>
        <AppSidebar me={me} review={review} onSignOut={signOut} />
        <SidebarInset className="min-w-0 overflow-x-clip">
          <Topbar snapshot={summary?.snapshot_date ?? null} />
          {isShowcase(me) && <ShowcaseBanner />}
          {/* entry-only: an exit keyed on the route would play with the next page's content inside it */}
          <motion.main
            key={path}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
            className="mx-auto w-full max-w-[1440px] flex-1 px-4 py-6 sm:px-6 lg:px-8 lg:py-8"
          >
            {children}
          </motion.main>
          <footer className="mx-auto flex w-full max-w-[1440px] flex-wrap items-center justify-between gap-2 border-t px-4 py-5 text-[11px] text-muted-foreground sm:px-6 lg:px-8">
            <span>NidhiNetra flags works that need verification. It never decides; officers do.</span>
            <span className="font-mono tracking-wide">SIH 2026 · SIH26102 · MoSPI · Team NeuralNexus</span>
          </footer>
        </SidebarInset>
      </SidebarProvider>
    </MeContext.Provider>
  );
}

function ShellLoading() {
  return (
    <div className="grid min-h-screen place-items-center bg-white">
      <div className="flex flex-col items-center gap-5">
        <div className="relative">
          <motion.div
            className="absolute inset-0 -m-6 rounded-full bg-brand-gradient opacity-20 blur-2xl"
            animate={{ scale: [0.9, 1.15, 0.9], opacity: [0.15, 0.3, 0.15] }}
            transition={{ duration: 2.4, repeat: Infinity, ease: "easeInOut" }}
          />
          <motion.div animate={{ y: [0, -6, 0] }} transition={{ duration: 2.4, repeat: Infinity, ease: "easeInOut" }}>
            <Emblem size={84} priority />
          </motion.div>
        </div>
        <AITextLoading texts={["Loading the works…", "Opening NidhiNetra…"]} interval={1400} className="text-sm" />
      </div>
    </div>
  );
}
