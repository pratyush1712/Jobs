import { cn } from "@/lib/utils";

interface SkillBadgeProps {
  label: string;
  variant?: "default" | "required" | "preferred" | "keyword";
  className?: string;
}

export function SkillBadge({
  label,
  variant = "default",
  className,
}: SkillBadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center px-2.5 py-1 rounded-md",
        "text-xs font-medium leading-none",
        {
          "bg-surface-3 text-text-secondary border border-divider":
            variant === "default",
          "bg-violet-muted text-violet border border-violet/20":
            variant === "required",
          "bg-blue-50 text-blue-700 border border-blue-200":
            variant === "preferred",
          "bg-gray-100 text-gray-500 border border-gray-200":
            variant === "keyword",
        },
        className,
      )}
    >
      {label}
    </span>
  );
}
