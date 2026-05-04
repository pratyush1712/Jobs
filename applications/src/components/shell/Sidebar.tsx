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
  PanelLeftClose,
  PanelLeftOpen,
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
  const sidebarCollapsed = useUIStore((s) => s.sidebarCollapsed);
  const setSidebarCollapsed = useUIStore((s) => s.setSidebarCollapsed);
  const { theme, toggle } = useTheme();

  return (
    <aside
      className={cn(
        "flex flex-col h-screen shrink-0",
        "bg-sidebar border-r border-sidebar-border",
        "select-none overflow-hidden",
        "transition-all duration-200 ease-in-out",
        sidebarCollapsed ? "w-[56px]" : "w-[220px]",
      )}
    >
      {/* Logo row — clicking the JT badge expands when collapsed */}
      <div
        className={cn(
          "flex items-center h-14 shrink-0 border-b border-sidebar-border",
          sidebarCollapsed ? "justify-center" : "gap-3 px-5",
        )}
      >
        {sidebarCollapsed ? (
          <button
            onClick={() => setSidebarCollapsed(false)}
            title="Expand sidebar"
            className={cn(
              "flex items-center justify-center w-7 h-7 rounded-lg",
              "bg-violet text-white text-xs font-bold tracking-tight",
              "hover:opacity-80 transition-opacity",
            )}
          >
            JT
          </button>
        ) : (
          <>
            <div
              className={cn(
                "flex items-center justify-center w-7 h-7 rounded-lg shrink-0",
                "bg-violet text-white",
                "text-xs font-bold tracking-tight",
              )}
            >
              JT
            </div>
            <span className="flex-1 text-[15px] font-semibold text-sidebar-foreground tracking-tight">
              Job Tracker
            </span>
            <button
              onClick={() => setSidebarCollapsed(true)}
              title="Collapse sidebar"
              className={cn(
                "p-1.5 rounded-md",
                "text-sidebar-foreground/30 hover:text-sidebar-foreground/60",
                "hover:bg-sidebar-accent/60 transition-colors",
              )}
            >
              <PanelLeftClose className="h-4 w-4" />
            </button>
          </>
        )}
      </div>

      {/* Nav */}
      <nav
        className={cn(
          "flex-1 py-4 space-y-1 overflow-y-auto",
          sidebarCollapsed ? "px-2 flex flex-col items-center" : "px-3",
        )}
      >
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
              title={sidebarCollapsed ? item.label : undefined}
              className={cn(
                "group flex items-center rounded-md text-sm font-medium transition-colors",
                sidebarCollapsed
                  ? "justify-center w-10 h-10"
                  : "gap-3 px-3 py-2 w-full",
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
              {!sidebarCollapsed && item.label}
            </Link>
          );
        })}
      </nav>

      {/* Bottom */}
      <div
        className={cn(
          "pb-4 space-y-1 border-t border-sidebar-border pt-4",
          sidebarCollapsed ? "px-2 flex flex-col items-center" : "px-3",
        )}
      >
        {/* Quick actions */}
        <button
          onClick={() => setCommandOpen(true)}
          title={sidebarCollapsed ? "Quick actions (⌘K)" : undefined}
          className={cn(
            "group flex items-center rounded-md text-sm font-medium text-sidebar-foreground/50",
            "hover:bg-sidebar-accent/60 hover:text-sidebar-accent-foreground transition-colors",
            sidebarCollapsed
              ? "justify-center w-10 h-10"
              : "gap-3 w-full px-3 py-2",
          )}
        >
          <Keyboard
            className={cn(
              "h-4 w-4 shrink-0 transition-colors",
              "text-sidebar-foreground/30 group-hover:text-sidebar-foreground/60",
            )}
          />
          {!sidebarCollapsed && (
            <>
              Quick actions
              <kbd className="ml-auto text-xs text-sidebar-foreground/30 font-mono bg-sidebar-border/40 px-1.5 py-0.5 rounded">
                ⌘K
              </kbd>
            </>
          )}
        </button>

        {/* Theme toggle */}
        <button
          onClick={toggle}
          title={
            sidebarCollapsed
              ? theme === "dark"
                ? "Light mode"
                : "Dark mode"
              : undefined
          }
          className={cn(
            "group flex items-center rounded-md text-sm font-medium text-sidebar-foreground/50",
            "hover:bg-sidebar-accent/60 hover:text-sidebar-accent-foreground transition-colors",
            sidebarCollapsed
              ? "justify-center w-10 h-10"
              : "gap-3 w-full px-3 py-2",
          )}
        >
          {theme === "dark" ? (
            <Sun
              className={cn(
                "h-4 w-4 shrink-0 transition-colors",
                "text-sidebar-foreground/30 group-hover:text-sidebar-foreground/60",
              )}
            />
          ) : (
            <Moon
              className={cn(
                "h-4 w-4 shrink-0 transition-colors",
                "text-sidebar-foreground/30 group-hover:text-sidebar-foreground/60",
              )}
            />
          )}
          {!sidebarCollapsed && (theme === "dark" ? "Light mode" : "Dark mode")}
        </button>

        {/* Settings */}
        <Link
          href="/settings"
          title={sidebarCollapsed ? "Settings" : undefined}
          className={cn(
            "group flex items-center rounded-md text-sm font-medium text-sidebar-foreground/50",
            "hover:bg-sidebar-accent/60 hover:text-sidebar-accent-foreground transition-colors",
            sidebarCollapsed
              ? "justify-center w-10 h-10"
              : "gap-3 w-full px-3 py-2",
          )}
        >
          <Settings
            className={cn(
              "h-4 w-4 shrink-0 transition-colors",
              "text-sidebar-foreground/30 group-hover:text-sidebar-foreground/60",
            )}
          />
          {!sidebarCollapsed && "Settings"}
        </Link>

        {/* Expand button — only shown in collapsed state as a secondary affordance */}
        {sidebarCollapsed && (
          <button
            onClick={() => setSidebarCollapsed(false)}
            title="Expand sidebar"
            className={cn(
              "group flex items-center justify-center w-10 h-10 rounded-md",
              "text-sidebar-foreground/30 hover:text-sidebar-foreground/60",
              "hover:bg-sidebar-accent/60 transition-colors",
            )}
          >
            <PanelLeftOpen className="h-4 w-4" />
          </button>
        )}
      </div>
    </aside>
  );
}
