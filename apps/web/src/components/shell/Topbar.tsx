"use client";

import { CalendarDays, CornerDownLeft, Search, Tag } from "lucide-react";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import CommandButton from "@/components/kokonutui/command-button";
import { LiveDot } from "@/components/nn/layout-bits";
import { Breadcrumb, BreadcrumbItem, BreadcrumbList, BreadcrumbPage, BreadcrumbSeparator } from "@/components/ui/breadcrumb";
import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
} from "@/components/ui/command";
import { Separator } from "@/components/ui/separator";
import { SidebarTrigger } from "@/components/ui/sidebar";
import { BAND_COLOR, WORK_TYPES } from "@/lib/format";
import { useMe } from "@/components/me";
import { NAV, navFor, visibleTo } from "./nav";

export function Topbar({ snapshot }: { snapshot: string | null }) {
  const path = usePathname();
  const me = useMe();
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");
  const here = navFor(path);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.key === "k" || e.key === "K") && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setOpen((o) => !o);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  function go(href: string) {
    setOpen(false);
    setQ("");
    router.push(href);
  }

  return (
    <header className="sticky top-0 z-30 flex h-14 shrink-0 items-center gap-2 rounded-t-xl border-b bg-white/75 px-3 backdrop-blur-xl sm:px-4">
      <SidebarTrigger className="-ml-1 text-muted-foreground" />
      <Separator orientation="vertical" className="mr-1 data-[orientation=vertical]:h-4" />
      <Breadcrumb>
        <BreadcrumbList>
          <BreadcrumbItem className="hidden sm:block">
            <span className="font-medium text-brand-900">NidhiNetra</span>
          </BreadcrumbItem>
          <BreadcrumbSeparator className="hidden sm:block" />
          <BreadcrumbItem>
            <BreadcrumbPage className="font-medium">{here?.label ?? "Overview"}</BreadcrumbPage>
          </BreadcrumbItem>
        </BreadcrumbList>
      </Breadcrumb>

      <div className="ml-auto flex items-center gap-2">
        {snapshot && (
          <span className="hidden items-center gap-2 rounded-full border bg-white px-3 py-1 text-xs text-muted-foreground lg:inline-flex">
            <LiveDot />
            <CalendarDays className="size-3.5" />
            eSAKSHI data to <span className="num font-medium text-foreground">{snapshot}</span>
          </span>
        )}
        <CommandButton onClick={() => setOpen(true)} className="w-40 sm:w-64">
          Search works, pages…
        </CommandButton>
      </div>

      <CommandDialog open={open} onOpenChange={setOpen} title="Search NidhiNetra" description="Search works, open a page or a risk band">
        <CommandInput placeholder="Type a village, a road, a work id, or a page…" value={q} onValueChange={setQ} />
        <CommandList data-lenis-prevent>
          <CommandEmpty>Press Enter to search every work for “{q}”.</CommandEmpty>
          {q.trim().length > 1 && (
            <CommandGroup heading="Works">
              <CommandItem value={`search ${q}`} onSelect={() => go(`/works?q=${encodeURIComponent(q.trim())}`)}>
                <Search className="text-brand-600" />
                Search every work for <span className="font-semibold">“{q.trim()}”</span>
                <CornerDownLeft className="ml-auto size-3.5 text-muted-foreground" />
              </CommandItem>
            </CommandGroup>
          )}
          <CommandGroup heading="Pages">
            {visibleTo(NAV, me?.role).map((n) => (
              <CommandItem key={n.href} value={`${n.label} ${n.hint}`} onSelect={() => go(n.href)}>
                <n.icon className="text-brand-600" />
                <span>{n.label}</span>
                <span className="ml-2 truncate text-xs text-muted-foreground">{n.hint}</span>
              </CommandItem>
            ))}
          </CommandGroup>
          <CommandSeparator />
          <CommandGroup heading="Review queue">
            {(["CRITICAL", "HIGH"] as const).map((b) => (
              <CommandItem key={b} value={`band ${b}`} onSelect={() => go(`/queue?band=${b}`)}>
                <span className="size-2.5 rounded-full" style={{ background: BAND_COLOR[b] }} />
                {b === "CRITICAL" ? "Critical works" : "High-risk works"}
              </CommandItem>
            ))}
          </CommandGroup>
          <CommandSeparator />
          <CommandGroup heading="Work types">
            {Object.entries(WORK_TYPES).map(([code, name]) => (
              <CommandItem key={code} value={`type ${name}`} onSelect={() => go(`/works?type=${code}`)}>
                <Tag className="text-muted-foreground" />
                {name}
              </CommandItem>
            ))}
          </CommandGroup>
        </CommandList>
      </CommandDialog>
    </header>
  );
}
