"use client";

import { ChevronsUpDown, LogOut, Scale } from "lucide-react";
import { motion } from "motion/react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Emblem, Logo } from "@/components/Logo";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuBadge,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarRail,
  useSidebar,
} from "@/components/ui/sidebar";
import type { Me } from "@/lib/api";
import { NAV_GROUPS, ROLE_LABEL, ROLE_SHORT } from "./nav";

export function AppSidebar({ me, review, onSignOut }: { me: Me; review: number | null; onSignOut: () => void }) {
  const path = usePathname();
  const { state } = useSidebar();
  const collapsed = state === "collapsed";

  return (
    <Sidebar variant="inset" collapsible="icon">
      <SidebarHeader className="px-2 pt-3">
        <Link href="/" className="flex items-center rounded-xl px-1.5 py-1 transition-colors hover:bg-sidebar-accent">
          {collapsed ? <Emblem size={30} /> : <Logo size={38} tagline="Every MPLADS rupee, watched" />}
        </Link>
      </SidebarHeader>

      <SidebarContent className="mt-2">
        {NAV_GROUPS.map((g) => (
          <SidebarGroup key={g.label}>
            <SidebarGroupLabel className="font-mono text-[10px] uppercase tracking-[0.14em]">{g.label}</SidebarGroupLabel>
            <SidebarGroupContent>
              <SidebarMenu>
                {g.items.map((n) => {
                  const active = n.href === "/" ? path === "/" : path.startsWith(n.href);
                  return (
                    <SidebarMenuItem key={n.href} className="relative">
                      {active && (
                        <motion.span
                          layoutId="nav-active"
                          className="absolute inset-0 rounded-lg bg-white shadow-[0_1px_2px_rgb(11_37_96/0.06),0_6px_18px_-10px_rgb(11_37_96/0.35)] ring-1 ring-border"
                          transition={{ type: "spring", stiffness: 420, damping: 34 }}
                        />
                      )}
                      <SidebarMenuButton
                        asChild
                        isActive={active}
                        tooltip={n.label}
                        className="relative h-9 data-[active=true]:bg-transparent data-[active=true]:font-semibold data-[active=true]:text-brand-900"
                      >
                        <Link href={n.href}>
                          <n.icon className={active ? "text-brand-600" : "text-muted-foreground"} />
                          <span>{n.label}</span>
                        </Link>
                      </SidebarMenuButton>
                      {n.href === "/queue" && review != null && review > 0 && (
                        <SidebarMenuBadge className="num rounded-full bg-high/10 px-1.5 text-[10px] font-semibold text-high">
                          {review.toLocaleString("en-IN")}
                        </SidebarMenuBadge>
                      )}
                    </SidebarMenuItem>
                  );
                })}
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        ))}
      </SidebarContent>

      <SidebarFooter className="gap-3 pb-3">
        {!collapsed && (
          <div className="relative overflow-hidden rounded-xl border bg-white p-3 text-[11.5px] leading-relaxed text-muted-foreground">
            <div className="tricolor-rule absolute inset-x-0 top-0" />
            <div className="mb-1 flex items-center gap-1.5 font-semibold text-brand-900">
              <Scale className="size-3.5 text-brand-600" /> It flags. Officers decide.
            </div>
            Every entry asks for a look. None is a finding of wrongdoing, and no Member of Parliament is ever scored.
          </div>
        )}
        <SidebarMenu>
          <SidebarMenuItem>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <SidebarMenuButton size="lg" className="data-[state=open]:bg-sidebar-accent">
                  <Avatar className="size-8 rounded-lg">
                    <AvatarFallback className="rounded-lg bg-brand-gradient text-[10px] font-semibold text-white">
                      {ROLE_SHORT[me.role]}
                    </AvatarFallback>
                  </Avatar>
                  <div className="grid flex-1 text-left leading-tight">
                    <span className="truncate text-sm font-semibold text-brand-950">{me.name ?? ROLE_LABEL[me.role].split(" · ")[0]}</span>
                    <span className="truncate text-[11px] text-muted-foreground">{ROLE_LABEL[me.role]}</span>
                  </div>
                  <ChevronsUpDown className="ml-auto size-4 text-muted-foreground" />
                </SidebarMenuButton>
              </DropdownMenuTrigger>
              <DropdownMenuContent side="top" align="start" className="w-(--radix-dropdown-menu-trigger-width) min-w-56 rounded-xl">
                <DropdownMenuLabel className="font-normal">
                  <div className="text-xs text-muted-foreground">Signed in as</div>
                  <div className="text-sm font-semibold">{ROLE_LABEL[me.role]}</div>
                  {me.district_lgd && <div className="text-xs text-muted-foreground">District code {me.district_lgd}</div>}
                </DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={onSignOut} className="text-high focus:text-high">
                  <LogOut /> Sign out
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarFooter>
      <SidebarRail />
    </Sidebar>
  );
}
