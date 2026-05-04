import { cn } from "@/lib/utils";

interface KpiCardProps {
  label: string;
  value: number;
  icon?: React.ElementType;
  accentColor?: string;
  trend?: {
    value: number;
    label: string;
  };
  className?: string;
}

export function KpiCard({
  label,
  value,
  icon: Icon,
  accentColor,
  trend,
  className,
}: KpiCardProps) {
  return (
    <div
      className={cn(
        "relative flex flex-col gap-3 p-5 rounded-xl",
        "bg-white border border-border shadow-sm",
        "transition-shadow hover:shadow-md",
        className,
      )}
    >
      {/* Top row */}
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold text-text-tertiary uppercase tracking-widest">
          {label}
        </span>
        {Icon && (
          <div
            className="flex items-center justify-center w-8 h-8 rounded-lg"
            style={
              accentColor
                ? { background: `${accentColor}18`, color: accentColor }
                : undefined
            }
          >
            <Icon className="h-4 w-4" />
          </div>
        )}
      </div>

      {/* Value */}
      <div className="flex items-end gap-2">
        <span
          className="text-3xl font-bold tracking-tight text-text-primary tabular-nums"
          style={accentColor ? { color: accentColor } : undefined}
        >
          {value.toLocaleString()}
        </span>
        {trend && (
          <span className="mb-1 text-xs text-text-tertiary">{trend.label}</span>
        )}
      </div>
    </div>
  );
}
