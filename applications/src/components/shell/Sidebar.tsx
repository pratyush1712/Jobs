"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Briefcase,
  Upload,
  Bookmark,
  Settings,
  Keyboard,
  Sun,
  Moon,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useUIStore } from "@/lib/store";
import { useTheme } from "@/lib/theme";

interface NavItem {
  href: string;
  label: string;
  icon: React.ElementType;
}

const NAV_ITEMS: NavItem[] = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/jobs", label: "Jobs", icon: Briefcase },
  { href: "/saved", label: "Saved", icon: Bookmark },
  { href: "/import", label: "Import", icon: Upload },
];

export function Sidebar() {
  const pathname = usePathname();
  const setCommandOpen = useUIStore((s) => s.setCommandOpen);
  const { theme, toggle } = useTheme();

  return (
    <aside
      className={cn(
        "flex flex-col h-screen w-[220px] shrink-0",
        "bg-sidebar border-r border-sidebar-border",
        "select-none",
      )}
    >
      {/* Logo */}
      <div className="flex items-center gap-3 px-5 h-14 border-b border-sidebar-border">
        <div
          className={cn(
            "flex items-center justify-center w-7 h-7 rounded-lg",
            "bg-violet text-white",
            "text-xs font-bold tracking-tight",
          )}
        >
          JT
        </div>
        <span className="text-[15px] font-semibold text-sidebar-foreground tracking-tight">
          Job Tracker
        </span>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        {NAV_ITEMS.map((item) => {
          const isActive =
            item.href === "/"
              ? pathname === "/"
              : pathname.startsWith(item.href);
          const Icon = item.icon;

          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "group flex items-center gap-3 px-3 py-2 rounded-md",
                "text-sm font-medium transition-colors",
                isActive
                  ? "bg-sidebar-accent text-sidebar-accent-foreground"
                  : "text-sidebar-foreground/60 hover:bg-sidebar-accent/60 hover:text-sidebar-accent-foreground",
              )}
            >
              <Icon
                className={cn(
                  "h-4 w-4 shrink-0 transition-colors",
                  isActive
                    ? "text-violet"
                    : "text-sidebar-foreground/40 group-hover:text-sidebar-foreground/70",
                )}
              />
              {item.label}
            </Link>
          );
        })}
      </nav>

      {/* Bottom */}
      <div className="px-3 pb-4 space-y-1 border-t border-sidebar-border pt-4">
        <button
          onClick={() => setCommandOpen(true)}
          className={cn(
            "flex items-center gap-3 w-full px-3 py-2 rounded-md",
            "text-sm font-medium text-sidebar-foreground/50",
            "hover:bg-sidebar-accent/60 hover:text-sidebar-accent-foreground",
            "transition-colors",
          )}
        >
          <Keyboard className="h-4 w-4 shrink-0 text-sidebar-foreground/30" />
          Quick actions
          <kbd className="ml-auto text-xs text-sidebar-foreground/30 font-mono bg-sidebar-border/40 px-1.5 py-0.5 rounded">
            ⌘K
          </kbd>
        </button>

        {/* Theme toggle */}
        <button
          onClick={toggle}
          className={cn(
            "flex items-center gap-3 w-full px-3 py-2 rounded-md",
            "text-sm font-medium text-sidebar-foreground/50",
            "hover:bg-sidebar-accent/60 hover:text-sidebar-accent-foreground",
            "transition-colors",
          )}
        >
          {theme === "dark" ? (
            <Sun className="h-4 w-4 shrink-0 text-sidebar-foreground/30" />
          ) : (
            <Moon className="h-4 w-4 shrink-0 text-sidebar-foreground/30" />
          )}
          {theme === "dark" ? "Light mode" : "Dark mode"}
        </button>

        <Link
          href="/settings"
          className={cn(
            "flex items-center gap-3 w-full px-3 py-2 rounded-md",
            "text-sm font-medium text-sidebar-foreground/50",
            "hover:bg-sidebar-accent/60 hover:text-sidebar-accent-foreground",
            "transition-colors",
          )}
        >
          <Settings className="h-4 w-4 shrink-0 text-sidebar-foreground/30" />
          Settings
        </Link>
      </div>
    </aside>
  );
}
