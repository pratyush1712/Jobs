import { cn } from "@/lib/utils";
import { STATUS_META } from "@/lib/constants";
import type { ApplicationStatus } from "@/types";

interface StatusBadgeProps {
  status: ApplicationStatus;
  className?: string;
  showDot?: boolean;
}

export function StatusBadge({
  status,
  className,
  showDot = true,
}: StatusBadgeProps) {
  const meta = STATUS_META[status];

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md",
        "text-xs font-semibold leading-none tracking-wide",
        meta.bgColor,
        meta.color,
        className,
      )}
    >
      {showDot && (
        <span
          className={cn("h-1.5 w-1.5 rounded-full shrink-0", meta.dotColor)}
        />
      )}
      {meta.label}
    </span>
  );
}
