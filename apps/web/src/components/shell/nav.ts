import {
  Clapperboard,
  Database,
  Inbox,
  LayoutDashboard,
  type LucideIcon,
  ShieldCheck,
  Workflow,
} from "lucide-react";
import type { Me } from "@/lib/api";

export type NavItem = { href: string; label: string; icon: LucideIcon; hint: string };

export const NAV_GROUPS: { label: string; items: NavItem[] }[] = [
  {
    label: "Monitor",
    items: [
      { href: "/", label: "Dashboard", icon: LayoutDashboard, hint: "Where risk concentrates, at a glance" },
      { href: "/queue", label: "Review queue", icon: Inbox, hint: "Works to verify first" },
      { href: "/works", label: "All works", icon: Database, hint: "Search every work" },
    ],
  },
  {
    label: "Act",
    items: [{ href: "/presanction", label: "Pre-sanction check", icon: ShieldCheck, hint: "Check a recommendation before sanction" }],
  },
  {
    label: "Understand",
    items: [
      { href: "/how-it-works", label: "How it works", icon: Workflow, hint: "The engines and the score" },
      { href: "/explain", label: "Step by step", icon: Clapperboard, hint: "One work, animated" },
    ],
  },
];

export const NAV: NavItem[] = NAV_GROUPS.flatMap((g) => g.items);

export function navFor(path: string): NavItem | undefined {
  if (path === "/") return NAV[0];
  if (path.startsWith("/work?") || path === "/work") return { href: "/work", label: "Work", icon: Database, hint: "" };
  return NAV.find((n) => n.href !== "/" && path.startsWith(n.href));
}

export const ROLE_LABEL: Record<Me["role"], string> = {
  MINISTRY: "Ministry · all districts",
  DISTRICT: "District officer",
  FIELD: "Field officer",
};

export const ROLE_SHORT: Record<Me["role"], string> = {
  MINISTRY: "MoSPI",
  DISTRICT: "DA",
  FIELD: "FO",
};
