"use client";

import { useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { LayoutDashboard, Briefcase, Upload, Bookmark, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { useUIStore } from "@/lib/store";

interface CommandAction {
  id: string;
  label: string;
  icon: React.ElementType;
  shortcut?: string;
  action: () => void;
}

export function CommandBar() {
  const router = useRouter();
  const { commandOpen, setCommandOpen, setImportOpen } = useUIStore();

  const actions: CommandAction[] = [
    {
      id: "go-dashboard",
      label: "Go to Dashboard",
      icon: LayoutDashboard,
      shortcut: "G D",
      action: () => {
        router.push("/");
        setCommandOpen(false);
      },
    },
    {
      id: "go-jobs",
      label: "Go to Jobs",
      icon: Briefcase,
      shortcut: "G J",
      action: () => {
        router.push("/jobs");
        setCommandOpen(false);
      },
    },
    {
      id: "go-saved",
      label: "Go to Saved",
      icon: Bookmark,
      shortcut: "G S",
      action: () => {
        router.push("/saved");
        setCommandOpen(false);
      },
    },
    {
      id: "import",
      label: "Import Jobs",
      icon: Upload,
      shortcut: "G I",
      action: () => {
        router.push("/import");
        setCommandOpen(false);
        setImportOpen(true);
      },
    },
  ];

  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setCommandOpen(!commandOpen);
      }
      if (e.key === "Escape" && commandOpen) {
        setCommandOpen(false);
      }
    },
    [commandOpen, setCommandOpen],
  );

  useEffect(() => {
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [handleKeyDown]);

  if (!commandOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-[20vh]">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={() => setCommandOpen(false)}
      />

      {/* Panel */}
      <div
        className={cn(
          "relative z-10 w-full max-w-md",
          "bg-surface-2 border border-border rounded-lg",
          "shadow-2xl shadow-black/50",
          "overflow-hidden",
        )}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-border">
          <span className="text-[12px] font-medium text-text-secondary uppercase tracking-wider">
            Quick Actions
          </span>
          <button
            onClick={() => setCommandOpen(false)}
            className="text-text-tertiary hover:text-text-secondary transition-colors"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        </div>

        {/* Actions */}
        <div className="py-1.5">
          {actions.map((action) => {
            const Icon = action.icon;
            return (
              <button
                key={action.id}
                onClick={action.action}
                className={cn(
                  "flex items-center gap-3 w-full px-4 py-2.5",
                  "text-[13px] font-medium text-text-primary",
                  "hover:bg-surface-3 transition-colors text-left",
                )}
              >
                <Icon className="h-3.5 w-3.5 text-text-tertiary shrink-0" />
                <span className="flex-1">{action.label}</span>
                {action.shortcut && (
                  <kbd className="text-[10px] text-text-tertiary font-mono bg-surface-1 px-1.5 py-0.5 rounded">
                    {action.shortcut}
                  </kbd>
                )}
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
