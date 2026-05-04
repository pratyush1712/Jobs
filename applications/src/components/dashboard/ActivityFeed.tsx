import { cn, timeAgo } from "@/lib/utils";
import { STATUS_META } from "@/lib/constants";
import type { ActivityItem } from "@/types";
import { FileText, ArrowRight, StickyNote, Edit, Download } from "lucide-react";

interface ActivityFeedProps {
  items: ActivityItem[];
  className?: string;
  compact?: boolean;
}

const KIND_ICONS = {
  note: StickyNote,
  status_change: ArrowRight,
  import: Download,
  edit: Edit,
} as const;

export function ActivityFeed({
  items,
  className,
  compact = false,
}: ActivityFeedProps) {
  if (items.length === 0) {
    return (
      <div className="flex items-center justify-center py-8">
        <p className="text-[12px] text-text-tertiary">No activity yet.</p>
      </div>
    );
  }

  return (
    <div className={cn("flex flex-col gap-0", className)}>
      {[...items].reverse().map((item, idx) => {
        const Icon = KIND_ICONS[item.kind] ?? FileText;

        return (
          <div key={item.id} className="flex gap-3 group">
            {/* Timeline line */}
            <div className="flex flex-col items-center">
              <div
                className={cn(
                  "flex items-center justify-center w-5 h-5 rounded-full shrink-0 mt-0.5",
                  item.kind === "status_change"
                    ? "bg-violet-muted"
                    : "bg-surface-3",
                )}
              >
                <Icon
                  className={cn(
                    "h-2.5 w-2.5",
                    item.kind === "status_change"
                      ? "text-violet"
                      : "text-text-tertiary",
                  )}
                />
              </div>
              {idx < items.length - 1 && (
                <div className="w-px flex-1 min-h-[16px] bg-divider mt-1 mb-1" />
              )}
            </div>

            {/* Content */}
            <div className={cn("flex-1", compact ? "pb-2" : "pb-3")}>
              <p className="text-[12px] text-text-primary leading-relaxed">
                {item.text}
                {item.kind === "status_change" &&
                  item.fromStatus &&
                  item.toStatus && (
                    <span className="ml-1.5">
                      <span
                        className={cn(
                          "inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium",
                          STATUS_META[item.fromStatus].bgColor,
                          STATUS_META[item.fromStatus].color,
                        )}
                      >
                        {STATUS_META[item.fromStatus].label}
                      </span>
                      <ArrowRight className="inline h-2.5 w-2.5 mx-1 text-text-tertiary" />
                      <span
                        className={cn(
                          "inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium",
                          STATUS_META[item.toStatus].bgColor,
                          STATUS_META[item.toStatus].color,
                        )}
                      >
                        {STATUS_META[item.toStatus].label}
                      </span>
                    </span>
                  )}
              </p>
              <p className="text-[11px] text-text-tertiary mt-0.5">
                {timeAgo(item.timestamp)}
              </p>
            </div>
          </div>
        );
      })}
    </div>
  );
}
