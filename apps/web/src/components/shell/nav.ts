import {
  Clapperboard,
  ClipboardList,
  Database,
  Inbox,
  LayoutDashboard,
  type LucideIcon,
  Route,
  Workflow,
} from "lucide-react";
import type { Me } from "@/lib/api";

/** `signedIn`: shown only to staff who signed in, never to the public view (role PUBLIC). */
export type NavItem = { href: string; label: string; icon: LucideIcon; hint: string; signedIn?: boolean };

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
    items: [
      // T142: the check before sanction is the form (the record-only pre-sanction check is retired)
      {
        href: "/work-form",
        label: "Work intelligence form",
        icon: ClipboardList,
        hint: "The check before sanction: fill the form, see what each check asks",
      },
    ],
  },
  {
    label: "Understand",
    items: [
      { href: "/how-it-works", label: "How it works", icon: Workflow, hint: "The engines and the score" },
      { href: "/explain", label: "Step by step", icon: Clapperboard, hint: "One filing, animated" },
      { href: "/end-to-end", label: "Form to risk score", icon: Route, hint: "Five filings, end to end" },
    ],
  },
];

export const NAV: NavItem[] = NAV_GROUPS.flatMap((g) => g.items);

/** The items this viewer may see: the public view does not get the signed-in ones. */
export function visibleTo(items: NavItem[], role: Me["role"] | undefined): NavItem[] {
  return items.filter((n) => !n.signedIn || (role !== undefined && role !== "PUBLIC"));
}

export function navFor(path: string): NavItem | undefined {
  if (path === "/") return NAV[0];
  if (path.startsWith("/work?") || path === "/work") return { href: "/work", label: "Work", icon: Database, hint: "" };
  return NAV.find((n) => n.href !== "/" && path.startsWith(n.href));
}

export const ROLE_LABEL: Record<Me["role"], string> = {
  PUBLIC: "Public view · all districts",
  MINISTRY: "Ministry · all districts",
  DISTRICT: "District officer",
  FIELD: "Field officer",
};

export const ROLE_SHORT: Record<Me["role"], string> = {
  PUBLIC: "IN",
  MINISTRY: "MoSPI",
  DISTRICT: "DA",
  FIELD: "FO",
};
