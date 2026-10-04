import { Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Kbd } from "@/components/ui/kbd";
import { cn } from "@/lib/utils";

/**
 * @author: @dorianbaffier
 * @description: Command Button
 * @version: 1.0.0
 * @date: 2025-06-26
 * @license: MIT
 * @website: https://kokonutui.com
 * @github: https://github.com/kokonut-labs/kokonutui
 *
 * Adapted for NidhiNetra: a search field-shaped trigger with the shortcut, brand sheen on hover.
 */

export default function CommandButton({
  className,
  children,
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & {
  children?: React.ReactNode;
}) {
  return (
    <Button
      variant="outline"
      {...props}
      className={cn(
        "group relative h-9 justify-start gap-2 overflow-hidden rounded-xl border-border bg-white/80 px-3 font-normal text-muted-foreground shadow-none backdrop-blur",
        "hover:border-brand-200 hover:bg-white hover:text-foreground",
        className
      )}
    >
      <Search className="size-4 transition-transform duration-300 group-hover:-rotate-6 group-hover:scale-110" />
      <span className="truncate text-sm">{children || "Search"}</span>
      <span className="ml-auto hidden items-center gap-1 sm:flex">
        <Kbd>Ctrl</Kbd>
        <Kbd>K</Kbd>
      </span>
      <span className="absolute inset-0 -translate-x-full bg-gradient-to-r from-brand-500/0 via-brand-500/10 to-brand-500/0 transition-transform duration-700 ease-out group-hover:translate-x-full" />
    </Button>
  );
}
